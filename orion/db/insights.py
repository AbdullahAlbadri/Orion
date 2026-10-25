"""Numbers for the customer's Stats page, from the business tables only (orders and stage history).

Every figure here can be traced to rows the customer can see: their orders and when each changed stage.
Spend, cost breakdown and landed cost wait for payments (TODO(decide): payment provider).
"""

from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Optional

from psycopg_pool import AsyncConnectionPool

from orion.config.status_labels import CLOSED, PHASES, STAGE_PHASE, UNSUBMITTED


async def stage_segments(pool: AsyncConnectionPool, customer_id: str, since: Optional[datetime]) -> list[dict]:
    """Each stage an order was in: (order_id, stage, waiting_on, at, until); until is NULL for the current one."""
    async with pool.connection() as conn:
        return await (await conn.execute(
            """
            SELECT e.order_id, e.stage, e.waiting_on, e.at,
                lead(e.at) OVER (PARTITION BY e.order_id ORDER BY e.at, e.id) AS until
            FROM order_stage_events e JOIN orders o ON o.id = e.order_id
            WHERE o.customer_id = %(c)s AND o.stage <> 'cancelled'
                AND (%(since)s::timestamptz IS NULL OR o.created_at >= %(since)s)
            ORDER BY e.order_id, e.at, e.id
            """,
            {"c": customer_id, "since": since},
        )).fetchall()


async def order_rows(pool: AsyncConnectionPool, customer_id: str, since: Optional[datetime]) -> list[dict]:
    async with pool.connection() as conn:
        return await (await conn.execute(
            """
            SELECT id, stage, market, option, quantity, product_id, reorder_of, revisions, mismatches_caught,
                created_at, updated_at
            FROM orders WHERE customer_id = %(c)s AND stage <> 'cancelled'
                AND (%(since)s::timestamptz IS NULL OR created_at >= %(since)s)
            ORDER BY created_at DESC
            """,
            {"c": customer_id, "since": since},
        )).fetchall()


def _hours(start: datetime, end: datetime) -> float:
    return max((end - start).total_seconds(), 0) / 3600


def summarize_time(segments: list[dict], now: Optional[datetime] = None) -> dict:
    """Time per phase (finished phases only), who orders waited on, and confirmation-to-delivery time.

    - A phase counts once the order has moved past it, so averages are not pulled down by work in progress.
    - "Waiting on" covers submitted orders only, including the current stage up to now; an unsent draft
      would otherwise count as weeks of "waiting on you".
    """
    now = now or datetime.now(timezone.utc)
    by_order: dict[str, list[dict]] = defaultdict(list)
    for s in segments:
        by_order[s["order_id"]].append(s)

    phase_hours: dict[str, list[float]] = defaultdict(list)
    waiting: dict[str, float] = defaultdict(float)
    to_delivery: list[float] = []
    per_order: dict[str, dict] = {}
    for order_id, segs in by_order.items():
        submitted = any(s["stage"] not in UNSUBMITTED for s in segs)
        totals: dict[str, float] = defaultdict(float)
        current_phase = STAGE_PHASE.get(segs[-1]["stage"]) if segs[-1]["until"] is None else None
        for s in segs:
            phase = STAGE_PHASE.get(s["stage"])
            end = s["until"] or (None if s["stage"] in CLOSED else now)
            if end is None:
                continue
            hours = _hours(s["at"], end)
            if phase:
                totals[phase] += hours
            if submitted and s["waiting_on"]:
                waiting[s["waiting_on"]] += hours
        for phase, hours in totals.items():
            if phase != current_phase:
                phase_hours[phase].append(hours)
        confirmed = next((s["at"] for s in segs if s["stage"] not in UNSUBMITTED), None)
        delivered = next((s["at"] for s in segs if s["stage"] in ("delivered", "completed")), None)
        if confirmed and delivered:
            to_delivery.append(_hours(confirmed, delivered))
        per_order[order_id] = {
            "phases": {p: round(h, 1) for p, h in totals.items()},
            "to_delivery_hours": round(_hours(confirmed, delivered), 1) if confirmed and delivered else None,
        }

    return {
        "phases": [
            {"phase": p, "avg_hours": round(mean(phase_hours[p]), 1), "orders": len(phase_hours[p])}
            for p in PHASES if phase_hours[p]
        ],
        "waiting_hours": {k: round(v, 1) for k, v in waiting.items()},
        "order_to_delivery_hours": round(mean(to_delivery), 1) if to_delivery else None,
        "delivered_orders": len(to_delivery),
        "per_order": per_order,
    }


def summarize_orders(rows: list[dict]) -> dict:
    """Counts by status and market, reorder rate, revisions and mismatches caught, over submitted orders."""
    submitted = [r for r in rows if r["stage"] not in UNSUBMITTED]
    by_stage: dict[str, int] = defaultdict(int)
    by_market: dict[str, int] = defaultdict(int)
    for r in submitted:
        by_stage[r["stage"]] += 1
        by_market[r["market"] or "unknown"] += 1
    reorders = sum(1 for r in submitted if r["reorder_of"])
    return {
        "submitted": len(submitted),
        "drafts": len(rows) - len(submitted),
        "pieces": sum(r["quantity"] or 0 for r in submitted),
        "by_stage": dict(by_stage),
        "by_market": dict(by_market),
        "reorders": reorders,
        "reorder_rate": round(reorders / len(submitted), 3) if submitted else None,
        "revisions": sum(r["revisions"] for r in submitted),
        "mismatches_caught": sum(r["mismatches_caught"] for r in submitted),
        "orders_with_mismatches": sum(1 for r in submitted if r["mismatches_caught"]),
    }
