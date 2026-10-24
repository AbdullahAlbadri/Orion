"""Open the graph against Postgres (checkpointer + business tables) for CLIs, the worker, and later the API."""

import hashlib
from contextlib import asynccontextmanager
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from orion.config.settings import Settings
from orion.db.postgres import make_pool
from orion.deps import Deps, postgres_deps
from orion.graph.graph import build_graph, on_event


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
        return await on_event(app, order_id, event)


def manual_event_id(order_id: str, manufacturer_id: str, text: str) -> str:
    """Pasting the same reply twice gives the same id, so it is only processed once."""
    digest = hashlib.sha256(f"{order_id}\n{manufacturer_id}\n{text.strip()}".encode()).hexdigest()[:16]
    return f"relay-{digest}"
