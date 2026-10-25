"""Customers, team members, login codes, refresh tokens and the orders table (Postgres)."""

from datetime import datetime, timezone
from typing import Optional

from psycopg_pool import AsyncConnectionPool

from orion.api.security import (
    CODE_MAX_ATTEMPTS,
    CODE_TTL,
    REFRESH_TTL,
    REUSE_GRACE,
    Audience,
    codes_match,
    hash_refresh_token,
    new_refresh_token,
    normalize_email,
)
from orion.config.status_labels import STAGE_UPDATES, UNSUBMITTED, stage_owner


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
                if row["revoked_at"] is not None and _now() - row["revoked_at"] < REUSE_GRACE:
                    # Two tabs refreshing at once, not a stolen token: this one just fails
                    raise LookupError("refresh token was just rotated")
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

    async def create_order(self, order_id: str, customer_id: str, reorder_of: Optional[str] = None) -> None:
        async with self.pool.connection() as conn, conn.transaction():
            await conn.execute(
                "INSERT INTO orders (id, customer_id, stage, reorder_of) VALUES (%s, %s, 'draft', %s)",
                (order_id, customer_id, reorder_of),
            )
            await conn.execute(
                "INSERT INTO order_stage_events (order_id, stage, waiting_on) VALUES (%s, 'draft', %s)",
                (order_id, stage_owner("draft")),
            )

    async def order(self, order_id: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,))).fetchone()

    async def customer_orders(self, customer_id: str) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id, stage, market, option, quantity, product_id, reorder_of, revisions, mismatches_caught, "
                "created_at, updated_at FROM orders "
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

    async def order_files(self, order_ids: list[str]) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id::text AS id, order_id, name, content_type, size, created_at FROM order_files "
                "WHERE order_id = ANY(%s) ORDER BY created_at DESC",
                (order_ids,),
            )).fetchall()

    async def copy_files(self, source_order: str, target_order: str, customer_id: str) -> dict[str, str]:
        """Reorder: the new order gets its own rows for the earlier order's files (same stored bytes).
        Returns old file id -> new file id."""
        async with self.pool.connection() as conn:
            rows = await (await conn.execute(
                """
                INSERT INTO order_files (order_id, customer_id, name, content_type, size, storage_key)
                SELECT %(t)s, customer_id, name, content_type, size, storage_key FROM order_files
                WHERE order_id = %(s)s AND customer_id = %(c)s
                RETURNING id::text AS id, storage_key
                """,
                {"t": target_order, "s": source_order, "c": customer_id},
            )).fetchall()
            old = await (await conn.execute(
                "SELECT id::text AS id, storage_key FROM order_files WHERE order_id = %s", (source_order,)
            )).fetchall()
        new_by_key = {r["storage_key"]: r["id"] for r in rows}
        return {r["id"]: new_by_key[r["storage_key"]] for r in old if r["storage_key"] in new_by_key}

    async def file_ids(self, order_id: str) -> set[str]:
        async with self.pool.connection() as conn:
            rows = await (await conn.execute(
                "SELECT id::text AS id FROM order_files WHERE order_id = %s", (order_id,)
            )).fetchall()
            return {r["id"] for r in rows}

    # --- AI mockups (illustrations; kept apart from the order's files) -------------------

    async def add_mockup(self, order_id: str, customer_id: str, storage_key: str, content_type: str, model: str,
                         cost: Optional[float]) -> dict:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "INSERT INTO order_mockups (order_id, customer_id, storage_key, content_type, model, cost) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id::text AS mockup_id, created_at",
                (order_id, customer_id, storage_key, content_type, model, cost),
            )).fetchone()

    async def mockups(self, order_id: str) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id::text AS mockup_id, created_at FROM order_mockups WHERE order_id = %s ORDER BY created_at DESC",
                (order_id,),
            )).fetchall()

    async def mockup(self, order_id: str, mockup_id: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT id::text AS mockup_id, storage_key, content_type, created_at FROM order_mockups "
                "WHERE order_id = %s AND id::text = %s",
                (order_id, mockup_id),
            )).fetchone()
        return {**row, "name": f"mockup-{row['mockup_id'][:8]}.png"} if row else None

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
    """Copy what the team and stats page query from the graph state into the business tables (rule 12).

    On a stage change it also records the stage history (with who the order now waits on), sends the
    customer an update for stages they did not cause themselves, and saves the product once the summary
    is confirmed. Runs in one transaction with the order row locked, so two processes can't double up.
    """
    if not state.get("order_id"):
        return
    order_id = state["order_id"]
    spec = state.get("spec") or {}
    stage = state.get("stage", "draft")
    tasks = state.get("human_tasks") or []
    mismatches = sum(1 for t in tasks if t.get("kind") == "mismatch")
    revisions = max(len(state.get("spec_versions") or []) - 1, 0)
    async with pool.connection() as conn, conn.transaction():
        before = await (await conn.execute(
            "SELECT stage, customer_id, reorder_of, product_id FROM orders WHERE id = %s FOR UPDATE", (order_id,)
        )).fetchone()
        await conn.execute(
            """
            INSERT INTO orders (id, stage, needs_human, market, option, quantity, revisions, mismatches_caught, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE SET stage = EXCLUDED.stage, needs_human = EXCLUDED.needs_human,
                market = EXCLUDED.market, option = EXCLUDED.option, quantity = EXCLUDED.quantity,
                revisions = EXCLUDED.revisions, mismatches_caught = EXCLUDED.mismatches_caught, updated_at = now()
            """,
            (order_id, stage, state.get("needs_human"), state.get("market"), spec.get("option"),
             spec.get("quantity"), revisions, mismatches),
        )
        if before is None or before["stage"] != stage:
            await conn.execute(
                "INSERT INTO order_stage_events (order_id, stage, waiting_on) VALUES (%s, %s, %s)",
                (order_id, stage, stage_owner(stage)),
            )
            customer = before["customer_id"] if before else None
            if customer and (update := STAGE_UPDATES.get(stage)):
                await conn.execute(
                    """
                    INSERT INTO notifications (customer_id, order_id, kind, event, title_en, title_ar, body_en, body_ar, href)
                    VALUES (%s, %s, 'status', %s, %s, %s, %s, %s, %s)
                    """,
                    (customer, order_id, stage, update["title_en"], update["title_ar"],
                     update.get("body_en"), update.get("body_ar"), f"/orders/{order_id}"),
                )
        if before and before["customer_id"] and before["product_id"] is None and stage not in UNSUBMITTED \
                and state.get("market") and spec.get("option"):
            await _save_product(conn, order_id, before, state["market"], spec["option"])


async def _save_product(conn, order_id: str, row: dict, market: str, option: str) -> None:
    """A confirmed order is a product; a reorder belongs to the product it was made from."""
    product_id = None
    if row["reorder_of"]:
        source = await (await conn.execute(
            "SELECT product_id FROM orders WHERE id = %s AND customer_id = %s", (row["reorder_of"], row["customer_id"])
        )).fetchone()
        product_id = source["product_id"] if source else None
    if product_id is None:
        await conn.execute(
            "INSERT INTO products (id, customer_id, market, option) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (order_id, row["customer_id"], market, option),
        )
        product_id = order_id
    await conn.execute("UPDATE orders SET product_id = %s WHERE id = %s", (product_id, order_id))
