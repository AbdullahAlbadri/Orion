"""Postgres implementations of the stores and the manual relay channel."""

from typing import Optional

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from orion.db.stores import Manufacturer, PriceRecord
from orion.tools.channel import OutgoingMessage


def make_pool(database_url: str) -> AsyncConnectionPool:
    """Open with `async with make_pool(url) as pool:`. Settings match what LangGraph's AsyncPostgresSaver needs."""
    return AsyncConnectionPool(
        database_url,
        min_size=1,
        max_size=5,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )


class PostgresDirectory:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def ranked_for(self, market: str, option: str) -> list[Manufacturer]:
        async with self.pool.connection() as conn:
            cur = await conn.cursor(row_factory=dict_row).execute(
                """
                SELECT DISTINCT ON (m.id) m.id, m.name, m.contact, m.channel, m.language,
                       (p.option IS NULL) AS general, p.rank
                FROM manufacturer_products p JOIN manufacturers m ON m.id = p.manufacturer_id
                WHERE m.active AND p.market = %s AND (p.option = %s OR p.option IS NULL)
                ORDER BY m.id, (p.option IS NULL), p.rank
                """,
                (market, option),
            )
            rows = await cur.fetchall()
        rows.sort(key=lambda r: (r["general"], r["rank"]))   # option-specific first, then by rank
        return [Manufacturer(**{k: r[k] for k in ("id", "name", "contact", "channel", "language")}) for r in rows]

    async def add(self, manufacturer: Manufacturer) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO manufacturers (id, name, contact, channel, language) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, contact = EXCLUDED.contact
                """,
                (manufacturer.id, manufacturer.name, manufacturer.contact, manufacturer.channel, manufacturer.language),
            )

    async def assign(self, manufacturer_id: str, market: str, option: Optional[str], rank: int) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO manufacturer_products (manufacturer_id, market, option, rank) VALUES (%s, %s, %s, %s)
                ON CONFLICT (manufacturer_id, market, option) DO UPDATE SET rank = EXCLUDED.rank
                """,
                (manufacturer_id, market, option, rank),
            )

    async def all(self) -> list[dict]:
        async with self.pool.connection() as conn:
            cur = await conn.cursor(row_factory=dict_row).execute(
                """
                SELECT m.id, m.name, m.contact, m.active, p.market, p.option, p.rank
                FROM manufacturers m LEFT JOIN manufacturer_products p ON p.manufacturer_id = m.id
                ORDER BY p.market, p.option NULLS LAST, p.rank, m.id
                """
            )
            return await cur.fetchall()


class PostgresPriceStore:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def append(self, record: PriceRecord) -> bool:
        data = record.model_dump()
        data["attributes"] = Jsonb(data["attributes"])
        data["problems"] = Jsonb(data["problems"])
        columns = list(data)
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                f"INSERT INTO price_records ({', '.join(columns)}) "
                f"VALUES ({', '.join('%(' + c + ')s' for c in columns)}) "
                "ON CONFLICT (source_key) DO NOTHING",
                data,
            )
            return cur.rowcount == 1


class ManualRelayChannel:
    """Outgoing messages wait in manufacturer_messages until a team member sends them by hand."""

    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def _insert(self, id, order_id, manufacturer_id, direction, text, status, reason=None) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO manufacturer_messages (id, order_id, manufacturer_id, direction, text, status, blocked_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING
                """,
                (id, order_id, manufacturer_id, direction, text, status, reason),
            )

    async def deliver(self, message: OutgoingMessage) -> None:
        await self._insert(message.id, message.order_id, message.manufacturer_id, "out", message.text, "pending_send")

    async def record_blocked(self, message: OutgoingMessage, reason: str) -> None:
        await self._insert(message.id, message.order_id, message.manufacturer_id, "out", message.text, "blocked", reason)

    async def record_incoming(self, message_id: str, order_id: str, manufacturer_id: str, text: str) -> None:
        await self._insert(message_id, order_id, manufacturer_id, "in", text, "received")

    async def pending(self) -> list[dict]:
        async with self.pool.connection() as conn:
            cur = await conn.cursor(row_factory=dict_row).execute(
                """
                SELECT msg.id, msg.order_id, msg.manufacturer_id, m.name AS manufacturer, m.contact, msg.text,
                       msg.created_at
                FROM manufacturer_messages msg JOIN manufacturers m ON m.id = msg.manufacturer_id
                WHERE msg.status = 'pending_send' ORDER BY msg.created_at
                """
            )
            return await cur.fetchall()

    async def mark_sent(self, message_id: str) -> bool:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE manufacturer_messages SET status = 'sent', sent_at = now() "
                "WHERE id = %s AND status = 'pending_send'",
                (message_id,),
            )
            return cur.rowcount == 1
