"""Open the graph against Postgres (checkpointer + business tables) for CLIs, and later the API/worker."""

import hashlib
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from orion.config.settings import Settings
from orion.db.postgres import make_pool
from orion.deps import Deps, postgres_deps
from orion.graph.graph import build_graph


@asynccontextmanager
async def open_postgres_app(settings: Settings):
    """Yields (app, deps). Run `alembic upgrade head` first for the business tables."""
    async with make_pool(settings.database_url) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()   # LangGraph's own checkpoint tables
        deps: Deps = postgres_deps(settings, pool)
        yield build_graph(deps, checkpointer), deps


def manual_event_id(order_id: str, manufacturer_id: str, text: str) -> str:
    """Pasting the same reply twice gives the same id, so it is only processed once."""
    digest = hashlib.sha256(f"{order_id}\n{manufacturer_id}\n{text.strip()}".encode()).hexdigest()[:16]
    return f"relay-{digest}"
