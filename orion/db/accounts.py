"""Customers, team members, login codes, refresh tokens and the orders table (Postgres)."""

from datetime import datetime, timezone
from typing import Optional

from psycopg_pool import AsyncConnectionPool

from orion.api.security import (
    CODE_MAX_ATTEMPTS,
    CODE_TTL,
    REFRESH_TTL,
    Audience,
    codes_match,
    hash_refresh_token,
    new_refresh_token,
    normalize_email,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RefreshReuse(Exception):
    """A refresh token that was already rotated was used again: treat as stolen."""


class AccountStore:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    # --- login codes ------------------------------------------------------------

    async def codes_sent_since(self, email: str, audience: Audience, since: datetime) -> int:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT count(*) AS n FROM login_codes WHERE email = %s AND audience = %s AND created_at > %s",
                (normalize_email(email), audience, since),
            )).fetchone()
            return row["n"]

    async def save_code(self, email: str, audience: Audience, code_hash: str) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO login_codes (email, audience, code_hash, expires_at) VALUES (%s, %s, %s, %s)",
                (normalize_email(email), audience, code_hash, _now() + CODE_TTL),
            )

    async def consume_code(self, secret: str, email: str, audience: Audience, code: str) -> bool:
        """Check the newest unused code for this email. Wrong guesses count; a used code never works again."""
        email = normalize_email(email)
        async with self.pool.connection() as conn, conn.transaction():
            row = await (await conn.execute(
                """
                SELECT id, code_hash, attempts FROM login_codes
                WHERE email = %s AND audience = %s AND used_at IS NULL AND expires_at > now()
                ORDER BY created_at DESC LIMIT 1 FOR UPDATE
                """,
                (email, audience),
            )).fetchone()
            if row is None or row["attempts"] >= CODE_MAX_ATTEMPTS:
                return False
            if not codes_match(row["code_hash"], secret, email, audience, code):
                await conn.execute("UPDATE login_codes SET attempts = attempts + 1 WHERE id = %s", (row["id"],))
                return False
            await conn.execute("UPDATE login_codes SET used_at = now() WHERE id = %s", (row["id"],))
            return True

    # --- customers and team -----------------------------------------------------

    async def customer_by_email(self, email: str, create: bool = False) -> Optional[dict]:
        email = normalize_email(email)
        async with self.pool.connection() as conn:
            if create:
                await conn.execute(
                    "INSERT INTO customers (email) VALUES (%s) ON CONFLICT (email) DO NOTHING", (email,)
                )
            return await (await conn.execute(
                "SELECT id, email, name FROM customers WHERE email = %s", (email,)
            )).fetchone()

    async def customer_from_identity(self, provider: str, subject: str, email: str, name: Optional[str]) -> dict:
        """Find by provider id, else link to (or create) the customer with this verified email."""
        column = {"google": "google_sub", "apple": "apple_sub"}[provider]
        email = normalize_email(email)
        async with self.pool.connection() as conn, conn.transaction():
            row = await (await conn.execute(
                f"SELECT id, email, name FROM customers WHERE {column} = %s", (subject,)
            )).fetchone()
            if row:
                return row
            return await (await conn.execute(
                f"""
                INSERT INTO customers (email, name, {column}) VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET {column} = EXCLUDED.{column},
                    name = COALESCE(customers.name, EXCLUDED.name)
                RETURNING id, email, name
                """,
                (email, name, subject),
            )).fetchone()

    async def customer(self, customer_id: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id, email, name FROM customers WHERE id = %s", (customer_id,)
            )).fetchone()

    async def team_member_by_email(self, email: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id, email, name, role FROM team_members WHERE email = %s AND active",
                (normalize_email(email),),
            )).fetchone()

    async def team_member(self, member_id: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id, email, name, role FROM team_members WHERE id = %s AND active", (member_id,)
            )).fetchone()

    async def add_team_member(self, email: str, name: Optional[str], role: str) -> dict:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                """
                INSERT INTO team_members (email, name, role) VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET name = COALESCE(EXCLUDED.name, team_members.name),
                    role = EXCLUDED.role, active = true
                RETURNING id, email, name, role
                """,
                (normalize_email(email), name, role),
            )).fetchone()

    async def list_team_members(self) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id, email, name, role, active, last_login_at FROM team_members ORDER BY created_at"
            )).fetchall()

    async def touch_login(self, audience: Audience, subject_id: str) -> None:
        table = "customers" if audience == "customer" else "team_members"
        async with self.pool.connection() as conn:
            await conn.execute(f"UPDATE {table} SET last_login_at = now() WHERE id = %s", (subject_id,))

    # --- refresh tokens ---------------------------------------------------------

    async def issue_refresh(self, subject_id: str, audience: Audience) -> str:
        token, token_hash = new_refresh_token()
        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO refresh_tokens (token_hash, subject_id, audience, expires_at) VALUES (%s, %s, %s, %s)",
                (token_hash, subject_id, audience, _now() + REFRESH_TTL[audience]),
            )
        return token

    async def rotate_refresh(self, token: str, audience: Audience) -> tuple[str, str]:
        """Swap a valid refresh token for a new one. Returns (subject_id, new token).

        Raises RefreshReuse (and revokes every session of that subject) if the token was already used.
        Raises LookupError if it is unknown or expired.
        """
        token_hash = hash_refresh_token(token)
        reused_by = None
        async with self.pool.connection() as conn:
            async with conn.transaction():
                row = await (await conn.execute(
                    "SELECT id, subject_id, expires_at, revoked_at FROM refresh_tokens "
                    "WHERE token_hash = %s AND audience = %s FOR UPDATE",
                    (token_hash, audience),
                )).fetchone()
                if row is None or row["expires_at"] <= _now():
                    raise LookupError("unknown or expired refresh token")
                if row["revoked_at"] is not None:
                    await conn.execute(
                        "UPDATE refresh_tokens SET revoked_at = now() "
                        "WHERE subject_id = %s AND audience = %s AND revoked_at IS NULL",
                        (row["subject_id"], audience),
                    )
                    reused_by = row["subject_id"]
                else:
                    await conn.execute("UPDATE refresh_tokens SET revoked_at = now() WHERE id = %s", (row["id"],))
                    new_token, new_hash = new_refresh_token()
                    await conn.execute(
                        "INSERT INTO refresh_tokens (token_hash, subject_id, audience, expires_at) "
                        "VALUES (%s, %s, %s, %s)",
                        (new_hash, row["subject_id"], audience, _now() + REFRESH_TTL[audience]),
                    )
        # Raise only after the transaction committed, or the revocation above would be rolled back
        if reused_by is not None:
            raise RefreshReuse(reused_by)
        return str(row["subject_id"]), new_token

    async def revoke_refresh(self, token: str) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                "UPDATE refresh_tokens SET revoked_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
                (hash_refresh_token(token),),
            )

    # --- orders -----------------------------------------------------------------

    async def create_order(self, order_id: str, customer_id: str) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO orders (id, customer_id, stage) VALUES (%s, %s, 'draft')", (order_id, customer_id)
            )

    async def order(self, order_id: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,))).fetchone()

    async def customer_orders(self, customer_id: str) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id, stage, market, option, quantity, created_at, updated_at FROM orders "
                "WHERE customer_id = %s AND stage <> 'cancelled' ORDER BY updated_at DESC",
                (customer_id,),
            )).fetchall()

    # --- uploaded files -----------------------------------------------------------

    async def add_file(self, order_id: str, customer_id: str, name: str, content_type: str, size: int,
                       storage_key: str) -> dict:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "INSERT INTO order_files (order_id, customer_id, name, content_type, size, storage_key) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, name, content_type, size, created_at",
                (order_id, customer_id, name, content_type, size, storage_key),
            )).fetchone()

    async def count_files(self, order_id: str) -> int:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT count(*) AS n FROM order_files WHERE order_id = %s", (order_id,)
            )).fetchone()
            return row["n"]

    async def order_file(self, order_id: str, file_id: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id, name, content_type, size, storage_key FROM order_files "
                "WHERE order_id = %s AND id::text = %s",
                (order_id, file_id),
            )).fetchone()

    async def file_ids(self, order_id: str) -> set[str]:
        async with self.pool.connection() as conn:
            rows = await (await conn.execute(
                "SELECT id::text AS id FROM order_files WHERE order_id = %s", (order_id,)
            )).fetchall()
            return {r["id"] for r in rows}

    # --- customer stats --------------------------------------------------------------

    async def customer_activity(self, customer_id: str) -> dict:
        """Counts from the business tables for one customer's orders (cancelled ones excluded)."""
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                """
                WITH mine AS (
                    SELECT id, stage, quantity, created_at FROM orders
                    WHERE customer_id = %(c)s AND stage <> 'cancelled'
                ),
                msgs AS (
                    SELECT m.order_id, m.manufacturer_id, m.direction, m.status, m.created_at
                    FROM manufacturer_messages m JOIN mine ON mine.id = m.order_id
                ),
                first_request AS (
                    SELECT order_id, min(created_at) AS at FROM msgs WHERE direction = 'out' GROUP BY order_id
                ),
                first_quote AS (
                    SELECT p.order_id, min(p.created_at) AS at FROM price_records p
                    JOIN mine ON mine.id = p.order_id GROUP BY p.order_id
                )
                SELECT
                    (SELECT count(*) FROM mine WHERE stage NOT IN ('draft', 'pre_receipt_review')) AS submitted,
                    (SELECT count(*) FROM mine WHERE stage IN ('delivered', 'completed')) AS delivered,
                    (SELECT coalesce(sum(quantity), 0) FROM mine
                        WHERE stage NOT IN ('draft', 'pre_receipt_review')) AS pieces,
                    (SELECT count(DISTINCT (order_id, manufacturer_id)) FROM msgs WHERE direction = 'out') AS factories,
                    (SELECT count(*) FROM msgs WHERE status <> 'blocked') AS messages,
                    (SELECT count(*) FROM first_quote) AS quoted_orders,
                    (SELECT avg(extract(epoch FROM q.at - r.at)) / 3600.0 FROM first_quote q
                        JOIN first_request r USING (order_id) WHERE q.at > r.at) AS hours_to_first_quote
                """,
                {"c": customer_id},
            )).fetchone()

    async def team_orders(self, needs_human: Optional[bool] = None, limit: int = 100) -> list[dict]:
        where = {True: "WHERE needs_human IS NOT NULL", False: "WHERE needs_human IS NULL", None: ""}[needs_human]
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                f"SELECT o.*, c.email AS customer_email FROM orders o LEFT JOIN customers c ON c.id = o.customer_id "
                f"{where} ORDER BY o.updated_at DESC LIMIT %s",
                (limit,),
            )).fetchall()


async def sync_order_row(pool: AsyncConnectionPool, state: dict) -> None:
    """Copy what the team and stats page query from the graph state into the orders table (rule 12)."""
    if not state.get("order_id"):
        return
    spec = state.get("spec") or {}
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO orders (id, stage, needs_human, market, option, quantity, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE SET stage = EXCLUDED.stage, needs_human = EXCLUDED.needs_human,
                market = EXCLUDED.market, option = EXCLUDED.option, quantity = EXCLUDED.quantity, updated_at = now()
            """,
            (state["order_id"], state.get("stage", "draft"), state.get("needs_human"),
             state.get("market"), spec.get("option"), spec.get("quantity")),
        )
