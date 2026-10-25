"""Customer quote: calculated in code from recorded factory prices (+5%, fixed rate to SAR, shipping as given),
sent by the team, accepted or declined by the customer."""

from datetime import datetime, timezone

import pytest

from orion.config.pricing import Pricing
from orion.graph.graph import OrderNotWaiting, get_order, on_event, send_reply
from orion.tools.customer_quote import build_customer_quote
from orion.tools.manufacturer_llm import ReplyAnalysis
from orion.tools.prices import ExtractedPrice
from test_manufacturer_flow import _reply, _to_sourcing

NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)
PRICING = Pricing(fee_rate=0.05, to_sar={"SAR": 1.0, "CNY": 0.55})
SPEC = {"quantity": 150, "answers": {"sample": "yes, sample first"}}


def _price(charge, amount, unit="piece", status="verified", currency="CNY", **extra):
    return {"charge": charge, "unit_price": amount, "currency": currency, "unit": unit, "status": status, **extra}


def _quote(manufacturer="factory-a", prices=None, **extra):
    prices = prices if prices is not None else [
        _price("product", 45), _price("sample", 200, unit="order"), _price("shipping", 800, unit="order")]
    return {"quote_id": f"q-{manufacturer}", "manufacturer_id": manufacturer, "prices": prices, "moq": 100,
            "lead_time_days": 25, "shipping_days": 30, **extra}


def test_quote_adds_the_fee_converts_to_sar_and_keeps_shipping_as_given():
    result = build_customer_quote([_quote()], SPEC, PRICING, 7, NOW)
    q = result["quote"]
    assert result["blocking"] == [] and result["warnings"] == []
    assert q["unit_price"] == "25.99"                       # 45 x 1.05 x 0.55 = 25.9875
    assert q["products_total"] == "3898.50"                 # the rounded unit price x 150
    assert q["shipping"] == "440.00"                        # 800 x 0.55, no fee
    assert q["total"] == "4338.50"
    assert q["sample_price"] == "115.50"                    # the customer asked for a sample: 200 x 1.05 x 0.55
    assert q["production_days"] == 25 and q["shipping_days"] == 30
    assert q["valid_until"].startswith("2026-11-01")
    # What the customer sees never names the factory, its own price or the fee
    assert not {"manufacturer_id", "fee_rate", "factory_unit_price"} & set(q)
    assert result["basis"]["manufacturer_id"] == "factory-a" and result["basis"]["factory_unit_price"] == 45


def test_cheapest_factory_wins_and_older_quotes_without_charges_still_count():
    older = _quote("factory-b", prices=[{"unit_price": 40, "currency": "CNY", "status": "verified"}])
    result = build_customer_quote([_quote(), older], SPEC, PRICING, 7, NOW)
    assert result["basis"]["manufacturer_id"] == "factory-b" and result["quote"]["unit_price"] == "23.10"
    assert any("no shipping price" in w for w in result["warnings"])


def test_problems_block_or_warn():
    unverified = _quote(prices=[_price("product", 45, status="extracted")])
    assert build_customer_quote([unverified], SPEC, PRICING, 7, NOW)["blocking"]
    assert build_customer_quote([_quote(expired=True)], SPEC, PRICING, 7, NOW)["blocking"]
    warnings = build_customer_quote([_quote(moq=500)], SPEC, PRICING, 7, NOW)["warnings"]
    assert any("minimum order is 500" in w for w in warnings)
    per_kg = _quote(prices=[_price("product", 45), _price("shipping", 20, unit="kg")])
    assert any("per kg" in w for w in build_customer_quote([per_kg], SPEC, PRICING, 7, NOW)["warnings"])


QUOTE_REPLY = "单价45元/件，含税，FOB深圳。打样费200元。海运到利雅得运费800元，约25-30天到门。"


def _full_quote(moq=100):
    return ReplyAnalysis(kind="quote", moq=moq, lead_time_days=25, shipping_days=30, summary_en="Quote", prices=[
        ExtractedPrice(unit_price=45, currency="元", unit="piece", incoterm="FOB", tax_included=True,
                       quoted_text="单价45元/件"),
        ExtractedPrice(charge="sample", unit_price=200, currency="元", unit="order", quoted_text="打样费200元"),
        ExtractedPrice(charge="shipping", unit_price=800, currency="元", unit="order", quoted_text="海运到利雅得运费800元"),
    ])


async def test_team_sends_the_quote_and_the_customer_accepts(make_order):
    app, _ = await _to_sourcing(make_order, analyses=[_full_quote()])
    await on_event(app, "o1", _reply(QUOTE_REPLY))
    prompt = await on_event(app, "o1", {"type": "send_quote", "event_id": "s1", "sent_by": "team@orion"})

    assert prompt["kind"] == "quote" and prompt["step"] == "quote_review"
    assert prompt["quote"]["unit_price"] == "25.99" and prompt["quote"]["shipping"] == "440.00"
    order = await get_order(app, "o1")
    assert order["stage"] == "quote_review" and order["customer_quote"]["sent_by"] == "team@orion"

    prompt = await send_reply(app, "o1", {"accept": "maybe"})                 # not a yes or no
    assert prompt["kind"] == "quote" and prompt["error"]
    await send_reply(app, "o1", {"accept": True})
    order = await get_order(app, "o1")
    assert order["stage"] == "awaiting_payment" and order["customer_quote"]["accepted_at"]
    assert "payment link" in order["needs_human"]


async def test_warnings_stop_the_quote_until_the_team_sends_anyway_and_a_decline_goes_back(make_order):
    app, _ = await _to_sourcing(make_order, analyses=[_full_quote(moq=1000)])
    await on_event(app, "o1", _reply(QUOTE_REPLY))

    await on_event(app, "o1", {"type": "send_quote", "event_id": "s1"})
    order = await get_order(app, "o1")
    assert order["stage"] == "quote_received" and "minimum order is 1000" in order["needs_human"]

    prompt = await on_event(app, "o1", {"type": "send_quote", "event_id": "s2", "send_anyway": True})
    assert prompt["kind"] == "quote"
    with pytest.raises(OrderNotWaiting):                                      # it is the customer's turn now
        await on_event(app, "o1", {"type": "send_quote", "event_id": "s3"})

    await send_reply(app, "o1", {"accept": False, "reason": "too expensive"})
    order = await get_order(app, "o1")
    assert order["stage"] == "quote_received" and order["needs_human"].endswith("too expensive")
    # The team can send a new quote from here
    assert (await on_event(app, "o1", {"type": "send_quote", "event_id": "s4", "send_anyway": True}))["kind"] == "quote"
