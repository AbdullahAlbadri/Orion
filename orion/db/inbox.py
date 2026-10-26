"""Customer notifications and help requests with the team (Postgres).

Help requests are answered by people only: nothing here calls a model, so price or change questions are
never answered by the AI (rule 1).
"""

from typing import Optional

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

NOTIFICATION_SELECT = (
    "id::text AS id, order_id, kind, event, title_en, title_ar, body_en, body_ar, href, emailed, created_at, read_at"
)
REQUEST_SELECT = (
    "r.id::text AS id, r.ref, r.order_id, r.topic, r.status, r.created_at, r.updated_at, "
    "(SELECT body FROM support_messages m WHERE m.request_id = r.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) "
    "AS last_message, "
    "(SELECT author FROM support_messages m WHERE m.request_id = r.id ORDER BY m.created_at DESC, m.id DESC LIMIT 1) "
    "AS last_author"
)


class InboxStore:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    # --- notifications -------------------------------------------------------------

    async def notifications(self, customer_id: str, limit: int = 100) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                f"SELECT {NOTIFICATION_SELECT} FROM notifications WHERE customer_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (customer_id, limit),
            )).fetchall()

    async def order_updates(self, customer_id: str, order_id: str, limit: int = 30) -> list[dict]:
        """The updates sent about one order, newest first (the top of the order page)."""
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                f"SELECT {NOTIFICATION_SELECT} FROM notifications WHERE customer_id = %s AND order_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (customer_id, order_id, limit),
            )).fetchall()

    async def unread_count(self, customer_id: str) -> int:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT count(*) AS n FROM notifications WHERE customer_id = %s AND read_at IS NULL", (customer_id,)
            )).fetchone()
            return row["n"]

    async def mark_read(self, customer_id: str, ids: Optional[list[str]] = None) -> int:
        """Mark the given notifications (or all of them) as read. Other customers' ids are ignored."""
        async with self.pool.connection() as conn:
            if ids is None:
                cur = await conn.execute(
                    "UPDATE notifications SET read_at = now() WHERE customer_id = %s AND read_at IS NULL",
                    (customer_id,),
                )
            else:
                cur = await conn.execute(
                    "UPDATE notifications SET read_at = now() "
                    "WHERE customer_id = %s AND read_at IS NULL AND id::text = ANY(%s)",
                    (customer_id, ids),
                )
            return cur.rowcount

    # --- help requests: customer side ---------------------------------------------------

    async def open_request(self, customer_id: str, topic: str, body: str, order_id: Optional[str],
                           context: dict) -> dict:
        async with self.pool.connection() as conn, conn.transaction():
            row = await (await conn.execute(
                "INSERT INTO support_requests (customer_id, order_id, topic, context) VALUES (%s, %s, %s, %s) "
                "RETURNING id",
                (customer_id, order_id, topic, Jsonb(context)),
            )).fetchone()
            await conn.execute(
                "INSERT INTO support_messages (request_id, author, body) VALUES (%s, 'customer', %s)", (row["id"], body)
            )
        return await self.request(customer_id, str(row["id"]))

    async def requests(self, customer_id: str) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                f"SELECT {REQUEST_SELECT} FROM support_requests r WHERE r.customer_id = %s ORDER BY r.updated_at DESC",
                (customer_id,),
            )).fetchall()

    async def request(self, customer_id: Optional[str], request_id: str) -> Optional[dict]:
        """One request with its messages. customer_id None = team access."""
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                f"SELECT {REQUEST_SELECT}, r.context, r.customer_id::text AS customer_id, c.email AS customer_email "
                "FROM support_requests r JOIN customers c ON c.id = r.customer_id "
                "WHERE r.id::text = %(id)s AND (%(c)s::uuid IS NULL OR r.customer_id = %(c)s::uuid)",
                {"id": request_id, "c": customer_id},
            )).fetchone()
            if row is None:
                return None
            row["messages"] = await (await conn.execute(
                "SELECT author, body, created_at FROM support_messages WHERE request_id = %s ORDER BY created_at, id",
                (request_id,),
            )).fetchall()
            if customer_id is not None:
                row.pop("customer_email")   # the customer knows their own email; keep the shape small
            return row

    async def customer_reply(self, customer_id: str, request_id: str, body: str) -> Optional[dict]:
        """A reply from the customer reopens the request for the team."""
        async with self.pool.connection() as conn, conn.transaction():
            updated = await (await conn.execute(
                "UPDATE support_requests SET status = 'open', updated_at = now() "
                "WHERE id::text = %s AND customer_id = %s RETURNING id",
                (request_id, customer_id),
            )).fetchone()
            if updated is None:
                return None
            await conn.execute(
                "INSERT INTO support_messages (request_id, author, body) VALUES (%s, 'customer', %s)",
                (updated["id"], body),
            )
        return await self.request(customer_id, request_id)

    async def awaiting_customer(self, customer_id: str) -> int:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT count(*) AS n FROM support_requests WHERE customer_id = %s AND status = 'waiting_customer'",
                (customer_id,),
            )).fetchone()
            return row["n"]

    # --- help requests: team side ---------------------------------------------------------

    async def team_requests(self, status: Optional[str] = None, limit: int = 100) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                f"SELECT {REQUEST_SELECT}, c.email AS customer_email FROM support_requests r "
                "JOIN customers c ON c.id = r.customer_id "
                "WHERE %(s)s::text IS NULL OR r.status = %(s)s ORDER BY r.updated_at DESC LIMIT %(n)s",
                {"s": status, "n": limit},
            )).fetchall()

    async def team_reply(self, request_id: str, member_email: str, body: str, status: str) -> Optional[dict]:
        """The team answers: the message goes on the thread and to the customer's Messages page."""
        async with self.pool.connection() as conn, conn.transaction():
            row = await (await conn.execute(
                "UPDATE support_requests SET status = %s, updated_at = now() WHERE id::text = %s "
                "RETURNING id, ref, customer_id, order_id",
                (status, request_id),
            )).fetchone()
            if row is None:
                return None
            if body:
                await conn.execute(
                    "INSERT INTO support_messages (request_id, author, author_email, body) VALUES (%s, 'team', %s, %s)",
                    (row["id"], member_email, body),
                )
                await conn.execute(
                    """
                    INSERT INTO notifications (customer_id, order_id, kind, event, title_en, title_ar, body_en, body_ar, href)
                    VALUES (%s, %s, 'team', %s, %s, %s, %s, %s, %s)
                    """,
                    (row["customer_id"], row["order_id"], str(row["id"]),
                     f"The Orion team replied to request #{row['ref']}", f"رد فريق أوريون على طلبك رقم {row['ref']}",
                     body, body, f"/help?request={row['id']}"),
                )
        return await self.request(None, request_id)
