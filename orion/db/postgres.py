"""Postgres implementations of the stores and the manufacturer channels (manual relay, email)."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from orion.db.stores import DeadlineKind, Manufacturer, PriceRecord
from orion.tools.channel import OutgoingMessage
from orion.tools.mail import Mailer, is_email, subject_for

log = logging.getLogger("orion.channel")


def make_pool(database_url: str) -> AsyncConnectionPool:
    """Open with `async with make_pool(url) as pool:`. Settings match what LangGraph's AsyncPostgresSaver needs."""
    return AsyncConnectionPool(
        database_url,
        min_size=1,
        max_size=10,   # an order lock holds one connection while the graph runs
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
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, contact = EXCLUDED.contact,
                    channel = EXCLUDED.channel
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


class PostgresScheduler:
    """Deadlines table. Nodes call schedule/cancel; the worker calls claim_due/finish/retry."""

    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def schedule(self, order_id: str, kind: DeadlineKind, ref: str, due_at: datetime) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO deadlines (order_id, kind, ref, due_at) VALUES (%s, %s, %s, %s)
                ON CONFLICT (order_id, kind, ref) DO UPDATE SET
                    due_at = EXCLUDED.due_at, status = 'pending', generation = deadlines.generation + 1,
                    tries = 0, last_error = NULL, claimed_at = NULL, fired_at = NULL
                """,
                (order_id, kind, ref, due_at),
            )

    async def cancel(self, order_id: str, kind: DeadlineKind, ref: str) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                "UPDATE deadlines SET status = 'cancelled' "
                "WHERE order_id = %s AND kind = %s AND ref = %s AND status = 'pending'",
                (order_id, kind, ref),
            )

    async def claim_due(self, limit: int = 20) -> list[dict]:
        """Mark due rows as firing and return them. SKIP LOCKED lets several workers run safely."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                """
                UPDATE deadlines SET status = 'firing', tries = tries + 1, claimed_at = now()
                WHERE id IN (
                    SELECT id FROM deadlines WHERE status = 'pending' AND due_at <= now()
                    ORDER BY due_at LIMIT %s FOR UPDATE SKIP LOCKED
                )
                RETURNING id, order_id, kind, ref, due_at, generation, tries
                """,
                (limit,),
            )
            return await cur.fetchall()

    async def finish(self, deadline: dict, status: str, error: Optional[str] = None) -> None:
        """fired / skipped / failed. No-op if the deadline was rescheduled while firing."""
        async with self.pool.connection() as conn:
            await conn.execute(
                "UPDATE deadlines SET status = %s, fired_at = now(), last_error = %s "
                "WHERE id = %s AND status = 'firing' AND generation = %s",
                (status, error, deadline["id"], deadline["generation"]),
            )

    async def retry(self, deadline: dict, delay: timedelta, error: str) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                "UPDATE deadlines SET status = 'pending', due_at = now() + %s, last_error = %s, claimed_at = NULL "
                "WHERE id = %s AND status = 'firing' AND generation = %s",
                (delay, error, deadline["id"], deadline["generation"]),
            )

    async def release_stuck(self, older_than: timedelta) -> int:
        """Rows left 'firing' by a worker that crashed go back to pending."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE deadlines SET status = 'pending', claimed_at = NULL "
                "WHERE status = 'firing' AND claimed_at < now() - %s",
                (older_than,),
            )
            return cur.rowcount


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


class EmailRelayChannel(ManualRelayChannel):
    """Every message is recorded in the outbox first. For manufacturers whose channel is "email" it is then
    emailed and marked sent; if sending fails it simply stays in the outbox for the team to send by hand."""

    def __init__(self, pool: AsyncConnectionPool, mailer: Optional[Mailer]):
        super().__init__(pool)
        self.mailer = mailer

    async def deliver(self, message: OutgoingMessage) -> None:
        await super().deliver(message)
        if self.mailer is None:
            return
        async with self.pool.connection() as conn:
            row = await (await conn.cursor(row_factory=dict_row).execute(
                "SELECT m.contact, msg.status FROM manufacturers m "
                "JOIN manufacturer_messages msg ON msg.manufacturer_id = m.id "
                "WHERE m.id = %s AND msg.id = %s AND m.channel = 'email'",
                (message.manufacturer_id, message.id),
            )).fetchone()
        if row is None or row["status"] != "pending_send":     # not an email manufacturer, or already sent
            return
        if not is_email(row["contact"]):
            log.warning("manufacturer %s has channel email but no valid address; left in the outbox",
                        message.manufacturer_id)
            return
        try:
            await self.mailer.send(row["contact"].strip(), subject_for(message.order_id), message.text)
        except Exception:
            log.exception("emailing %s failed; left in the outbox for the team", message.id)
            return
        await self.mark_sent(message.id)

    async def manufacturer_for_email(self, address: str) -> Optional[str]:
        async with self.pool.connection() as conn:
            row = await (await conn.cursor(row_factory=dict_row).execute(
                "SELECT id FROM manufacturers WHERE channel = 'email' AND active AND lower(trim(contact)) = lower(%s) "
                "ORDER BY id LIMIT 1",
                (address.strip(),),
            )).fetchone()
        return row["id"] if row else None
