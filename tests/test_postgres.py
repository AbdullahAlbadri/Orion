"""Integration test against a real Postgres `orion_test` database. Skipped when Postgres is not running."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from conftest import HOODIE_ANSWERS, ScriptedConsultant, ScriptedManufacturerAgent, turn
from orion.db.postgres import (
    ManualRelayChannel,
    PostgresDirectory,
    PostgresPriceStore,
    PostgresScheduler,
    make_pool,
)
from orion.db.stores import Manufacturer
from orion.deps import Deps
from orion.graph.graph import OrderNotWaiting, build_graph, get_order, on_event, send_reply, start_order
from orion.tools.manufacturer_llm import ReplyAnalysis
from orion.tools.prices import ExtractedPrice
from orion.worker import fire_due

QUOTE = "单价45元/件，含税，FOB深圳，起订量100件"


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
            scheduler=PostgresScheduler(pool),
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


async def test_worker_fires_deadlines(pg_url):
    run = uuid.uuid4().hex[:8]
    order_id = f"pgw-{run}"
    market = f"m-{run}"   # own market so other tests' manufacturers never match

    async with make_pool(pg_url) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        directory, scheduler, channel = PostgresDirectory(pool), PostgresScheduler(pool), ManualRelayChannel(pool)
        for i, name in enumerate(["a", "b"], start=1):
            await directory.add(Manufacturer(id=f"{order_id}-{name}", name=name))
            await directory.assign(f"{order_id}-{name}", market, None, i)

        # Route this order's market to our manufacturers
        class Directory:
            async def ranked_for(self, _market, option):
                return await directory.ranked_for(market, option)

        deps = Deps(
            consultant=ScriptedConsultant([turn("Done.", ready=True)], []),
            manufacturer_agent=ScriptedManufacturerAgent(),
            directory=Directory(),
            prices=PostgresPriceStore(pool),
            channel=channel,
            scheduler=scheduler,
        )
        app = build_graph(deps, checkpointer)
        await start_order(app, order_id)
        await send_reply(app, order_id, {"choice": "apparel"})
        await send_reply(app, order_id, {"choice": "hoodie"})
        await send_reply(app, order_id, {"answers": HOODIE_ANSWERS})
        await send_reply(app, order_id, {"confirm": True})

        async def deadline(ref):
            async with pool.connection() as conn:
                return await (await conn.execute(
                    "SELECT status, generation FROM deadlines WHERE order_id = %s AND ref = %s", (order_id, ref)
                )).fetchone()

        async def make_due(ref):
            async with pool.connection() as conn:
                await conn.execute(
                    "UPDATE deadlines SET due_at = now() - interval '1 minute' WHERE order_id = %s AND ref = %s",
                    (order_id, ref),
                )

        a, b = f"{order_id}-a", f"{order_id}-b"
        assert await deadline(a) == {"status": "pending", "generation": 1}
        assert (await fire_due(app, scheduler, pool))["fired"] == 0          # not due yet

        # 1st timeout: reminder, and the same deadline is rescheduled (generation 2) rather than closed
        await make_due(a)
        assert (await fire_due(app, scheduler, pool))["fired"] == 1
        assert await deadline(a) == {"status": "pending", "generation": 2}
        assert any(m["id"] == f"{order_id}:reminder:{a}" for m in await channel.pending())

        # 2nd timeout: move on to b; a's deadline is done. Two workers at once fire it only once.
        await make_due(a)
        results = await asyncio.gather(fire_due(app, scheduler, pool), fire_due(app, scheduler, pool))
        assert sum(r["fired"] for r in results) == 1
        assert await deadline(a) == {"status": "fired", "generation": 2}
        assert await deadline(b) == {"status": "pending", "generation": 1}
        order = await get_order(app, order_id)
        assert [x["outcome"] for x in order["manufacturer_attempts"]] == ["no_reply", "waiting"]

        # A deadline for an order that is not waiting on a manufacturer is skipped, not retried forever
        await scheduler.schedule(f"ghost-{run}", "manufacturer_reply", "x", datetime.now(timezone.utc) - timedelta(minutes=1))
        assert (await fire_due(app, scheduler, pool))["skipped"] == 1


async def test_event_for_order_waiting_on_customer_is_rejected(make_order):
    app, _ = make_order()
    await start_order(app, "o-wait")
    with pytest.raises(OrderNotWaiting):
        await on_event(app, "o-wait", {"type": "manufacturer_reply", "event_id": "x", "manufacturer_id": "factory-a",
                                       "text": "hi"})
