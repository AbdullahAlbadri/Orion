"""The customer's own data: account settings, business profile, addresses and sign-in sessions (Postgres)."""

from typing import Any, Optional

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

SETTINGS_COLUMNS = ("name", "phone", "lang", "calendar", "currency", "notify")
BUSINESS_COLUMNS = ("name", "business_type", "store_platform", "store_url", "description", "contacts")
ADDRESS_COLUMNS = ("label", "contact_name", "phone", "city", "district", "street", "building", "postal_code", "notes")
ADDRESS_SELECT = "id::text AS id, " + ", ".join(ADDRESS_COLUMNS) + ", is_default, created_at, updated_at"


def _json(value: Any) -> Any:
    return Jsonb(value) if isinstance(value, (dict, list)) else value


class ProfileStore:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    # --- account settings ------------------------------------------------------------

    async def settings(self, customer_id: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT id::text AS id, email, name, phone, lang, calendar, currency, notify, onboarded_at, created_at "
                "FROM customers WHERE id = %s",
                (customer_id,),
            )).fetchone()

    async def update_settings(self, customer_id: str, fields: dict) -> dict:
        fields = {k: v for k, v in fields.items() if k in SETTINGS_COLUMNS}
        if fields:
            sets = ", ".join(f"{k} = %({k})s" for k in fields)
            async with self.pool.connection() as conn:
                await conn.execute(
                    f"UPDATE customers SET {sets} WHERE id = %(id)s",
                    {**{k: _json(v) for k, v in fields.items()}, "id": customer_id},
                )
        return await self.settings(customer_id)

    async def mark_onboarded(self, customer_id: str) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                "UPDATE customers SET onboarded_at = coalesce(onboarded_at, now()) WHERE id = %s", (customer_id,)
            )

    # --- business profile --------------------------------------------------------------

    async def business(self, customer_id: str) -> dict:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT " + ", ".join(BUSINESS_COLUMNS) + ", updated_at FROM business_profiles WHERE customer_id = %s",
                (customer_id,),
            )).fetchone()
        return row or {**{k: None for k in BUSINESS_COLUMNS}, "contacts": [], "updated_at": None}

    async def save_business(self, customer_id: str, fields: dict) -> dict:
        fields = {k: v for k, v in fields.items() if k in BUSINESS_COLUMNS}
        if fields:
            columns = ", ".join(fields)
            values = ", ".join(f"%({k})s" for k in fields)
            sets = ", ".join(f"{k} = EXCLUDED.{k}" for k in fields)
            async with self.pool.connection() as conn:
                await conn.execute(
                    f"INSERT INTO business_profiles (customer_id, {columns}) VALUES (%(customer_id)s, {values}) "
                    f"ON CONFLICT (customer_id) DO UPDATE SET {sets}, updated_at = now()",
                    {**{k: _json(v) for k, v in fields.items()}, "customer_id": customer_id},
                )
        return await self.business(customer_id)

    async def business_for_ai(self, customer_id: str) -> dict:
        """Only what helps the consultant suggest options. No contacts, phones or identifiers."""
        b = await self.business(customer_id)
        return {k: b.get(k) for k in ("name", "business_type", "store_platform", "description") if b.get(k)}

    # --- addresses ---------------------------------------------------------------------

    async def addresses(self, customer_id: str) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                f"SELECT {ADDRESS_SELECT} FROM addresses WHERE customer_id = %s AND deleted_at IS NULL "
                "ORDER BY is_default DESC, created_at",
                (customer_id,),
            )).fetchall()

    async def add_address(self, customer_id: str, fields: dict, make_default: bool = False) -> dict:
        fields = {k: fields.get(k) for k in ADDRESS_COLUMNS}
        async with self.pool.connection() as conn, conn.transaction():
            first = not await (await conn.execute(
                "SELECT 1 FROM addresses WHERE customer_id = %s AND deleted_at IS NULL LIMIT 1", (customer_id,)
            )).fetchone()
            if make_default and not first:
                await self._clear_default(conn, customer_id)
            columns = ", ".join(ADDRESS_COLUMNS)
            values = ", ".join(f"%({k})s" for k in ADDRESS_COLUMNS)
            return await (await conn.execute(
                f"INSERT INTO addresses (customer_id, is_default, {columns}) "
                f"VALUES (%(customer_id)s, %(is_default)s, {values}) RETURNING {ADDRESS_SELECT}",
                {**fields, "customer_id": customer_id, "is_default": make_default or first},
            )).fetchone()

    async def update_address(self, customer_id: str, address_id: str, fields: dict) -> Optional[dict]:
        fields = {k: fields.get(k) for k in ADDRESS_COLUMNS}
        sets = ", ".join(f"{k} = %({k})s" for k in ADDRESS_COLUMNS)
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                f"UPDATE addresses SET {sets}, updated_at = now() "
                "WHERE id::text = %(id)s AND customer_id = %(customer_id)s AND deleted_at IS NULL "
                f"RETURNING {ADDRESS_SELECT}",
                {**fields, "id": address_id, "customer_id": customer_id},
            )).fetchone()

    async def delete_address(self, customer_id: str, address_id: str) -> bool:
        """Soft delete: orders that already used the address keep pointing at it. The oldest one left
        becomes the default if the default was removed."""
        async with self.pool.connection() as conn, conn.transaction():
            row = await (await conn.execute(
                "UPDATE addresses SET deleted_at = now(), is_default = false "
                "WHERE id::text = %s AND customer_id = %s AND deleted_at IS NULL RETURNING id",
                (address_id, customer_id),
            )).fetchone()
            if row is None:
                return False
            await conn.execute(
                """
                UPDATE addresses SET is_default = true WHERE id = (
                    SELECT id FROM addresses WHERE customer_id = %(c)s AND deleted_at IS NULL ORDER BY created_at LIMIT 1
                ) AND NOT EXISTS (
                    SELECT 1 FROM addresses WHERE customer_id = %(c)s AND deleted_at IS NULL AND is_default
                )
                """,
                {"c": customer_id},
            )
            return True

    async def set_default_address(self, customer_id: str, address_id: str) -> bool:
        async with self.pool.connection() as conn, conn.transaction():
            exists = await (await conn.execute(
                "SELECT 1 FROM addresses WHERE id::text = %s AND customer_id = %s AND deleted_at IS NULL",
                (address_id, customer_id),
            )).fetchone()
            if not exists:
                return False
            await self._clear_default(conn, customer_id)
            await conn.execute("UPDATE addresses SET is_default = true WHERE id::text = %s", (address_id,))
            return True

    @staticmethod
    async def _clear_default(conn, customer_id: str) -> None:
        await conn.execute(
            "UPDATE addresses SET is_default = false WHERE customer_id = %s AND is_default", (customer_id,)
        )

    # --- product ideas -----------------------------------------------------------------

    async def suggestions(self, customer_id: str, lang: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT fingerprint, items, created_at FROM customer_suggestions WHERE customer_id = %s AND lang = %s",
                (customer_id, lang),
            )).fetchone()

    async def save_suggestions(self, customer_id: str, lang: str, fingerprint: str, items: list[dict]) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO customer_suggestions (customer_id, lang, fingerprint, items) VALUES (%s, %s, %s, %s)
                ON CONFLICT (customer_id, lang) DO UPDATE SET fingerprint = EXCLUDED.fingerprint,
                    items = EXCLUDED.items, created_at = now()
                """,
                (customer_id, lang, fingerprint, Jsonb(items)),
            )

    # --- sessions ----------------------------------------------------------------------

    async def sessions(self, customer_id: str) -> list[dict]:
        """Signed-in devices: each live refresh token chain (only the newest token of a chain is unrevoked)."""
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                "SELECT created_at, expires_at FROM refresh_tokens WHERE subject_id = %s AND audience = 'customer' "
                "AND revoked_at IS NULL AND expires_at > now() ORDER BY created_at DESC",
                (customer_id,),
            )).fetchall()

    async def revoke_sessions(self, customer_id: str) -> int:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE refresh_tokens SET revoked_at = now() WHERE subject_id = %s AND audience = 'customer' "
                "AND revoked_at IS NULL",
                (customer_id,),
            )
            return cur.rowcount

    # --- data export -------------------------------------------------------------------

    async def export(self, customer_id: str) -> dict:
        """Everything stored about the customer in the business tables (Settings → download my data)."""
        async with self.pool.connection() as conn:
            async def rows(sql: str) -> list[dict]:
                return await (await conn.execute(sql, (customer_id,))).fetchall()

            return {
                "account": (await rows(
                    "SELECT email, name, phone, lang, calendar, currency, notify, created_at, onboarded_at "
                    "FROM customers WHERE id = %s"
                ) or [None])[0],
                "business": (await rows(
                    "SELECT " + ", ".join(BUSINESS_COLUMNS) + " FROM business_profiles WHERE customer_id = %s"
                ) or [None])[0],
                "addresses": await rows(
                    "SELECT " + ", ".join(ADDRESS_COLUMNS) + ", is_default, created_at, deleted_at "
                    "FROM addresses WHERE customer_id = %s"
                ),
                "orders": await rows(
                    "SELECT id, stage, market, option, quantity, created_at, updated_at FROM orders "
                    "WHERE customer_id = %s ORDER BY created_at"
                ),
                "files": await rows(
                    "SELECT order_id, name, content_type, size, created_at FROM order_files WHERE customer_id = %s"
                ),
                "support_requests": await rows(
                    "SELECT r.ref, r.topic, r.status, r.order_id, r.created_at, "
                    "coalesce(json_agg(json_build_object('author', m.author, 'body', m.body, 'at', m.created_at) "
                    "ORDER BY m.created_at) FILTER (WHERE m.id IS NOT NULL), '[]') AS messages "
                    "FROM support_requests r LEFT JOIN support_messages m ON m.request_id = r.id "
                    "WHERE r.customer_id = %s GROUP BY r.id"
                ),
            }
