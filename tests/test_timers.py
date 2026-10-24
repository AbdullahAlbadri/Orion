import pytest
from test_manufacturer_flow import QUOTE, _outgoing, _quote_analysis, _reply, _to_sourcing

from orion.graph.graph import OrderNotWaiting, get_order, on_event, start_order
from orion.tools.manufacturer_llm import ReplyAnalysis


def _timeout(ref="factory-a", kind="manufacturer_reply", n=1):
    return {"type": "timeout", "event_id": f"timeout:{kind}:{ref}:{n}", "kind": kind, "ref": ref}


async def test_first_timeout_sends_one_reminder(make_order):
    app, deps = await _to_sourcing(make_order)
    first_due = deps.scheduler.pending("o1")[("manufacturer_reply", "factory-a")]

    await on_event(app, "o1", _timeout())

    reminder = deps.channel.messages["o1:reminder:factory-a"]
    assert reminder["status"] == "pending_send" and "跟进" in reminder["text"]
    order = await get_order(app, "o1")
    attempt = order["manufacturer_attempts"][0]
    assert attempt["reminded"] and attempt["outcome"] == "waiting"
    assert order["current_manufacturer"] == "factory-a"
    assert deps.scheduler.pending("o1")[("manufacturer_reply", "factory-a")] != first_due


async def test_second_timeout_moves_on_but_keeps_first_open(make_order):
    app, deps = await _to_sourcing(make_order, analyses=[_quote_analysis()])
    await on_event(app, "o1", _timeout(n=1))
    await on_event(app, "o1", _timeout(n=2))

    order = await get_order(app, "o1")
    assert [a["outcome"] for a in order["manufacturer_attempts"]] == ["no_reply", "waiting"]
    assert order["current_manufacturer"] == "factory-b"
    assert ("manufacturer_reply", "factory-b") in deps.scheduler.pending("o1")

    # Factory A answers late: still accepted, nothing was committed elsewhere
    await on_event(app, "o1", _reply(QUOTE, manufacturer_id="factory-a"))
    order = await get_order(app, "o1")
    assert order["manufacturer_attempts"][0]["outcome"] == "quoted"
    assert order["stage"] == "quote_received"


async def test_timeouts_until_nobody_is_left(make_order):
    app, deps = await _to_sourcing(make_order)
    for ref in ("factory-a", "factory-b"):
        await on_event(app, "o1", _timeout(ref, n=1))
        await on_event(app, "o1", _timeout(ref, n=2))

    order = await get_order(app, "o1")
    assert order["current_manufacturer"] is None
    assert "No manufacturer left" in order["needs_human"]


async def test_quote_stops_the_clock_and_schedules_expiry(make_order):
    app, deps = await _to_sourcing(make_order, analyses=[_quote_analysis()])
    await on_event(app, "o1", _reply())

    pending = deps.scheduler.pending("o1")
    assert ("manufacturer_reply", "factory-a") not in pending
    assert ("quote_expiry", "evt-1") in pending

    # A late timeout for the stopped clock does nothing
    await on_event(app, "o1", _timeout())
    assert "o1:reminder:factory-a" not in deps.channel.messages

    await on_event(app, "o1", _timeout("evt-1", kind="quote_expiry"))
    order = await get_order(app, "o1")
    assert order["quotes"][0]["expired"]
    assert "expired" in order["needs_human"]


async def test_acknowledgement_does_not_stop_the_clock(make_order):
    ack = ReplyAnalysis(kind="acknowledgement", summary_en="received")
    app, deps = await _to_sourcing(make_order, analyses=[ack])
    await on_event(app, "o1", _reply("收到"))
    assert ("manufacturer_reply", "factory-a") in deps.scheduler.pending("o1")


async def test_decline_cancels_its_deadline(make_order):
    app, deps = await _to_sourcing(make_order, analyses=[ReplyAnalysis(kind="decline", summary_en="no")])
    await on_event(app, "o1", _reply("做不了"))
    pending = deps.scheduler.pending("o1")
    assert ("manufacturer_reply", "factory-a") not in pending
    assert ("manufacturer_reply", "factory-b") in pending


async def test_duplicate_timeout_is_ignored(make_order):
    app, deps = await _to_sourcing(make_order)
    await on_event(app, "o1", _timeout(n=1))
    await on_event(app, "o1", _timeout(n=1))   # same event id: must not escalate
    order = await get_order(app, "o1")
    assert order["manufacturer_attempts"][0]["outcome"] == "waiting"
    assert len(order["manufacturer_attempts"]) == 1


async def test_timeout_for_order_waiting_on_customer_is_rejected(make_order):
    app, _ = make_order()
    await start_order(app, "o2")
    with pytest.raises(OrderNotWaiting):
        await on_event(app, "o2", _timeout())
