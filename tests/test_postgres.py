"""Integration test against a real Postgres `orion_test` database. Skipped when Postgres is not running."""

import uuid

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from conftest import HOODIE_ANSWERS, ScriptedConsultant, ScriptedManufacturerAgent, turn
from orion.config.settings import get_settings
from orion.db.postgres import ManualRelayChannel, PostgresDirectory, PostgresPriceStore, make_pool
from orion.db.stores import Manufacturer
from orion.deps import Deps
from orion.graph.graph import OrderNotWaiting, build_graph, get_order, on_event, send_reply, start_order
from orion.tools.manufacturer_llm import ReplyAnalysis
from orion.tools.prices import ExtractedPrice

QUOTE = "单价45元/件，含税，FOB深圳，起订量100件"


@pytest.fixture(scope="module")
def pg_url():
    try:
        base = get_settings().database_url
        with psycopg.connect(base, autocommit=True, connect_timeout=3) as conn:
            # Fresh database every run so earlier runs' rows never affect results
            conn.execute("DROP DATABASE IF EXISTS orion_test WITH (FORCE)")
            conn.execute("CREATE DATABASE orion_test")
    except Exception as e:  # no settings or no server
        pytest.skip(f"Postgres not available: {e}")

    url = make_conninfo(**(conninfo_to_dict(base) | {"dbname": "orion_test"}))
    url = "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(**conninfo_to_dict(url))
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    return url


async def test_order_through_postgres(pg_url):
    run = uuid.uuid4().hex[:8]
    order_id = f"pg-{run}"
    a = Manufacturer(id=f"pg-{run}-a", name="PG Factory A")
    b = Manufacturer(id=f"pg-{run}-b", name="PG Factory B")
    quote = ReplyAnalysis(
        kind="quote",
        prices=[ExtractedPrice(unit_price=45, currency="元", unit="piece", quantity=150, incoterm="FOB",
                               tax_included=True, quoted_text="单价45元/件")],
        summary_en="45 CNY",
    )

    async with make_pool(pg_url) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        directory, channel = PostgresDirectory(pool), ManualRelayChannel(pool)
        await directory.add(b)
        await directory.add(a)
        await directory.assign(b.id, "apparel", None, 1)       # market-wide
        await directory.assign(a.id, "apparel", "hoodie", 5)   # option-specific wins
        assert [m.id for m in await directory.ranked_for("apparel", "hoodie") if m.id.startswith(f"pg-{run}")] \
            == [a.id, b.id]

        agent = ScriptedManufacturerAgent(analyses=[quote])
        deps = Deps(
            consultant=ScriptedConsultant([turn("Done.", ready=True)], []),
            manufacturer_agent=agent,
            directory=directory,
            prices=PostgresPriceStore(pool),
            channel=channel,
        )
        app = build_graph(deps, checkpointer)

        await start_order(app, order_id)
        await send_reply(app, order_id, {"choice": "apparel"})
        await send_reply(app, order_id, {"choice": "hoodie"})
        await send_reply(app, order_id, {"answers": HOODIE_ANSWERS})
        await send_reply(app, order_id, {"confirm": True})

        # The request sits in the outbox until a human sends it
        [request] = [m for m in await channel.pending() if m["order_id"] == order_id]
        assert request["manufacturer_id"] in (a.id, b.id) and "卫衣" in request["text"]
        assert await channel.mark_sent(request["id"]) and not await channel.mark_sent(request["id"])

        contacted = (await get_order(app, order_id))["current_manufacturer"]
        event = {"type": "manufacturer_reply", "event_id": f"{order_id}-e1", "manufacturer_id": contacted,
                 "text": QUOTE}
        await on_event(app, order_id, event)
        await on_event(app, order_id, event)    # duplicate: ignored
        assert agent.analyzed == [QUOTE]

        async with pool.connection() as conn:
            rows = await (await conn.execute(
                "SELECT status, currency, unit_price FROM price_records WHERE order_id = %s", (order_id,)
            )).fetchall()
            assert rows == [{"status": "verified", "currency": "CNY", "unit_price": 45}]
            with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
                await conn.execute("UPDATE price_records SET unit_price = 1 WHERE order_id = %s", (order_id,))

            incoming = await (await conn.execute(
                "SELECT direction, status FROM manufacturer_messages WHERE id = %s", (event["event_id"],)
            )).fetchone()
            assert incoming == {"direction": "in", "status": "received"}

        assert (await get_order(app, order_id))["stage"] == "quote_received"


async def test_event_for_order_waiting_on_customer_is_rejected(make_order):
    app, _ = make_order()
    await start_order(app, "o-wait")
    with pytest.raises(OrderNotWaiting):
        await on_event(app, "o-wait", {"type": "manufacturer_reply", "event_id": "x", "manufacturer_id": "factory-a",
                                       "text": "hi"})
