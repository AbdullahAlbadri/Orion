"""Saved products (one per confirmed order that was not a reorder) and their order history (Postgres)."""

from typing import Optional

from psycopg_pool import AsyncConnectionPool

PRODUCT_SELECT = """
    SELECT p.id, p.market, p.option, p.notes, p.archived_at, p.created_at,
        count(o.id) AS orders,
        max(o.created_at) AS last_ordered_at,
        (array_agg(o.quantity ORDER BY o.created_at DESC))[1] AS last_quantity,
        (array_agg(o.id ORDER BY o.created_at DESC))[1] AS latest_order_id,
        (array_agg(o.stage ORDER BY o.created_at DESC))[1] AS latest_stage
    FROM products p JOIN orders o ON o.product_id = p.id
"""


class ProductStore:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def products(self, customer_id: str, archived: bool = False) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                PRODUCT_SELECT
                + " WHERE p.customer_id = %s AND (p.archived_at IS NOT NULL) = %s GROUP BY p.id "
                  "ORDER BY max(o.created_at) DESC",
                (customer_id, archived),
            )).fetchall()

    async def product(self, customer_id: str, product_id: str) -> Optional[dict]:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                PRODUCT_SELECT + " WHERE p.customer_id = %s AND p.id = %s GROUP BY p.id", (customer_id, product_id)
            )).fetchone()
            if row is None:
                return None
            row["history"] = await (await conn.execute(
                """
                SELECT o.id, o.stage, o.quantity, o.revisions, o.mismatches_caught, o.created_at, o.updated_at,
                    (SELECT min(e.at) FROM order_stage_events e
                        WHERE e.order_id = o.id AND e.stage IN ('delivered', 'completed')) AS delivered_at
                FROM orders o WHERE o.product_id = %s ORDER BY o.created_at DESC
                """,
                (product_id,),
            )).fetchall()
            return row

    async def update(self, customer_id: str, product_id: str, notes: Optional[str] = None,
                     archived: Optional[bool] = None) -> bool:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                """
                UPDATE products SET
                    notes = CASE WHEN %(set_notes)s THEN %(notes)s ELSE notes END,
                    archived_at = CASE WHEN %(archived)s::boolean IS NULL THEN archived_at
                                       WHEN %(archived)s THEN coalesce(archived_at, now()) ELSE NULL END
                WHERE id = %(id)s AND customer_id = %(c)s
                """,
                {"set_notes": notes is not None, "notes": notes, "archived": archived, "id": product_id,
                 "c": customer_id},
            )
            return cur.rowcount == 1
