"""Open the graph against Postgres (checkpointer + business tables) for CLIs, the worker, and later the API."""

import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from orion.config.settings import Settings
from orion.db.accounts import sync_order_row
from orion.db.postgres import make_pool
from orion.deps import Deps, postgres_deps
from orion.graph.graph import (
    INTERACTIVE_STEPS,
    OrderNotWaiting,
    build_graph,
    get_order,
    on_event,
    send_reply,
    start_order,
    update_paused_order,
    waiting_on,
)


@asynccontextmanager
async def open_postgres_app(settings: Settings):
    """Yields (app, deps, pool). Run `alembic upgrade head` first for the business tables."""
    async with make_pool(settings.database_url) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()   # LangGraph's own checkpoint tables
        deps: Deps = postgres_deps(settings, pool)
        yield build_graph(deps, checkpointer), deps, pool


@asynccontextmanager
async def order_lock(pool: AsyncConnectionPool, order_id: str):
    """One event at a time per order, across all processes (Postgres advisory lock)."""
    async with pool.connection() as conn:
        await conn.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (order_id,))
        try:
            yield
        finally:
            await conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (order_id,))


async def send_event(app, pool: AsyncConnectionPool, order_id: str, event: dict) -> Optional[dict]:
    """on_event under the order lock. Use this from every process that resumes orders."""
    async with order_lock(pool, order_id):
        try:
            return await on_event(app, order_id, event)
        finally:
            await sync_order_row(pool, await get_order(app, order_id))


async def start_customer_order(app, pool: AsyncConnectionPool, order_id: str) -> Optional[dict]:
    async with order_lock(pool, order_id):
        try:
            return await start_order(app, order_id)
        finally:
            await sync_order_row(pool, await get_order(app, order_id))


async def send_customer_reply(app, pool: AsyncConnectionPool, order_id: str, reply) -> Optional[dict]:
    """The customer's answer to the prompt the order is paused on. Raises OrderNotWaiting otherwise."""
    async with order_lock(pool, order_id):
        waiting = await waiting_on(app, order_id)
        if not waiting or waiting.get("step") not in INTERACTIVE_STEPS:
            raise OrderNotWaiting(f"order {order_id} is not waiting for the customer")
        try:
            return await send_reply(app, order_id, reply)
        finally:
            await sync_order_row(pool, await get_order(app, order_id))


async def resolve_human_tasks(app, pool: AsyncConnectionPool, order_id: str, resolved_by: str) -> dict:
    """Mark every open human task on the order as handled and clear needs_human. Tasks are kept as history."""
    async with order_lock(pool, order_id):
        state = await get_order(app, order_id)
        if not state:
            raise LookupError(order_id)
        now = datetime.now(timezone.utc).isoformat()
        tasks = [
            t if t.get("resolved_at") else {**t, "resolved_at": now, "resolved_by": resolved_by}
            for t in state.get("human_tasks", [])
        ]
        await update_paused_order(app, order_id, {"human_tasks": tasks, "needs_human": None})
        state = await get_order(app, order_id)
        await sync_order_row(pool, state)
        return state


def manual_event_id(order_id: str, manufacturer_id: str, text: str) -> str:
    """Pasting the same reply twice gives the same id, so it is only processed once."""
    digest = hashlib.sha256(f"{order_id}\n{manufacturer_id}\n{text.strip()}".encode()).hexdigest()[:16]
    return f"relay-{digest}"
