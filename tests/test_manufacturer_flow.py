from datetime import datetime

from conftest import HOODIE_ANSWERS, ScriptedConsultant, ScriptedManufacturerAgent, turn
from orion.config.china_calendar import add_working_days
from orion.graph.graph import get_order, on_event, send_reply, start_order
from orion.graph.manufacturer_request import render_request, request_files
from orion.spec import ProductSpec
from orion.tools.price_guard import price_violation
from orion.tools.manufacturer_llm import DraftAnswer, DraftAnswers, ReplyAnalysis, SpecMismatch
from orion.tools.prices import ExtractedPrice

QUOTE = "卫衣 150件 单价45元/件，含税，FOB深圳。起订量100件，交期20天。"


def _quote_analysis(**price_overrides) -> ReplyAnalysis:
    price = dict(
        unit_price=45, currency="元", unit="piece", quantity=150, shipping_included=None,
        incoterm="FOB", tax_included=True, quoted_text="单价45元/件",
    ) | price_overrides
    return ReplyAnalysis(
        kind="quote", prices=[ExtractedPrice(**price)], moq=100, lead_time_days=20, summary_en="Quote 45 CNY"
    )


async def _to_sourcing(make_order, answers=HOODIE_ANSWERS, order_id="o1", **agent_kwargs):
    """Drive a hoodie order to the point where it waits on the first manufacturer."""
    app, deps = make_order(
        consultant=ScriptedConsultant([turn("Done.", ready=True)], []),
        manufacturer_agent=ScriptedManufacturerAgent(**agent_kwargs),
    )
    await start_order(app, order_id)
    await send_reply(app, order_id, {"choice": "apparel"})
    await send_reply(app, order_id, {"choice": "hoodie"})
    await send_reply(app, order_id, {"answers": answers})
    prompt = await send_reply(app, order_id, {"confirm": True})
    assert prompt["waiting_on"] == "manufacturer"
    return app, deps


def _reply(text=QUOTE, event_id="evt-1", manufacturer_id="factory-a"):
    return {"type": "manufacturer_reply", "event_id": event_id, "manufacturer_id": manufacturer_id, "text": text}


def _outgoing(deps):
    return [m for m in deps.channel.messages.values() if m["direction"] == "out"]


async def test_frozen_spec_sends_request_to_first_manufacturer(make_order):
    app, deps = await _to_sourcing(make_order)
    order = await get_order(app, "o1")

    [request] = _outgoing(deps)
    assert request["manufacturer_id"] == "factory-a" and request["status"] == "pending_send"
    assert "总数量：150 件" in request["text"] and "M × 50" in request["text"]
    assert "中-embroidery" in request["text"]
    assert order["stage"] == "sourcing" and order["current_manufacturer"] == "factory-a"
    attempt = order["manufacturer_attempts"][0]
    contacted = datetime.fromisoformat(attempt["contacted_at"])
    assert attempt["deadline_at"] == add_working_days(contacted, 3).isoformat()
    assert deps.scheduler.pending("o1") == {("manufacturer_reply", "factory-a"): add_working_days(contacted, 3)}


async def test_missing_translation_falls_back_to_original(make_order):
    app, deps = await _to_sourcing(make_order, skip_ids={"labels"})
    assert "woven neck label" in _outgoing(deps)[0]["text"]


async def test_verified_quote_is_recorded(make_order):
    app, deps = await _to_sourcing(make_order, analyses=[_quote_analysis()])
    prompt = await on_event(app, "o1", _reply())
    assert prompt["waiting_on"] == "manufacturer"

    [record] = deps.prices.records.values()
    assert record.status == "verified" and record.currency == "CNY" and record.unit_price == 45
    assert record.original_text == QUOTE and record.attributes["fabric_gsm"] == 350
    order = await get_order(app, "o1")
    assert order["stage"] == "quote_received"
    assert order["quotes"][0]["moq"] == 100
    assert order["manufacturer_attempts"][0]["outcome"] == "quoted"
    assert "customer quote" in order["needs_human"]


async def test_duplicate_and_unknown_events_are_ignored(make_order):
    app, deps = await _to_sourcing(make_order, analyses=[_quote_analysis()])
    await on_event(app, "o1", _reply())
    await on_event(app, "o1", _reply())                                   # same event id again
    await on_event(app, "o1", _reply(event_id="evt-2", manufacturer_id="stranger"))
    await send_reply(app, "o1", {"message": "customer typing while we wait"})

    assert deps.manufacturer_agent.analyzed == [QUOTE]
    assert len(deps.prices.records) == 1


async def test_ambiguous_price_is_stored_unverified_and_flagged(make_order):
    app, deps = await _to_sourcing(make_order, analyses=[_quote_analysis(tax_included=None)])
    await on_event(app, "o1", _reply())

    [record] = deps.prices.records.values()
    assert record.status == "extracted"
    tasks = [t["reason"] for t in (await get_order(app, "o1"))["human_tasks"]]
    assert any("Unverified product price" in t and "tax" in t for t in tasks)


async def test_hallucinated_price_is_not_stored(make_order):
    app, deps = await _to_sourcing(make_order, analyses=[_quote_analysis(unit_price=39, quoted_text="单价39元/件")])
    await on_event(app, "o1", _reply())

    assert deps.prices.records == {}
    assert "Could not verify a price" in (await get_order(app, "o1"))["needs_human"]


async def test_negotiation_is_flagged_even_if_llm_misses_it(make_order):
    text = "量大可以优惠，你们预算多少？"
    analysis = ReplyAnalysis(kind="other", mentions_negotiation=False, summary_en="asks budget")
    app, deps = await _to_sourcing(make_order, analyses=[analysis])
    await on_event(app, "o1", _reply(text))

    assert "negotiation" in (await get_order(app, "o1"))["needs_human"]
    assert len(_outgoing(deps)) == 1  # nothing sent back


async def test_decline_moves_to_next_manufacturer_then_flags_when_exhausted(make_order):
    decline = ReplyAnalysis(kind="decline", summary_en="cannot make it")
    app, deps = await _to_sourcing(make_order, analyses=[decline, decline])

    await on_event(app, "o1", _reply("做不了", event_id="e1"))
    order = await get_order(app, "o1")
    assert order["current_manufacturer"] == "factory-b"
    assert [m["manufacturer_id"] for m in _outgoing(deps)] == ["factory-a", "factory-b"]

    await on_event(app, "o1", _reply("不做", event_id="e2", manufacturer_id="factory-b"))
    order = await get_order(app, "o1")
    assert order["current_manufacturer"] is None
    assert "No manufacturer left" in order["needs_human"]


async def test_answerable_questions_get_a_reply_from_the_spec(make_order):
    questions = ReplyAnalysis(kind="questions", questions=["Which neck label?"], summary_en="asks label")
    drafts = DraftAnswers(answers=[DraftAnswer(question="Which neck label?", answerable=True, answer_zh="织唛领标")])
    app, deps = await _to_sourcing(make_order, analyses=[questions], drafts=[drafts])
    await on_event(app, "o1", _reply("领标用什么？"))

    answer = _outgoing(deps)[-1]
    assert answer["id"] == "o1:answer:evt-1" and answer["text"] == "1. 织唛领标"
    order = await get_order(app, "o1")
    assert order["stage"] == "clarifying" and not order.get("needs_human")


async def test_unanswerable_questions_go_to_a_human(make_order):
    questions = ReplyAnalysis(kind="questions", questions=["Delivery address?"], summary_en="asks address")
    drafts = DraftAnswers(answers=[DraftAnswer(question="Delivery address?", answerable=False, answer_zh="")])
    app, deps = await _to_sourcing(make_order, analyses=[questions], drafts=[drafts])
    await on_event(app, "o1", _reply("送货地址？"))

    assert len(_outgoing(deps)) == 1
    assert "Delivery address?" in (await get_order(app, "o1"))["needs_human"]


async def test_drafted_answer_with_price_is_blocked(make_order):
    questions = ReplyAnalysis(kind="questions", questions=["Sample?"], summary_en="asks sample")
    drafts = DraftAnswers(answers=[DraftAnswer(question="Sample?", answerable=True, answer_zh="样品费100元可以")])
    app, deps = await _to_sourcing(make_order, analyses=[questions], drafts=[drafts])
    await on_event(app, "o1", _reply("需要样品吗？"))

    assert deps.channel.messages["o1:answer:evt-1"]["status"] == "blocked"
    assert "blocked by the price guard" in (await get_order(app, "o1"))["needs_human"]


async def test_spec_with_a_price_blocks_the_request(make_order):
    app, deps = await _to_sourcing(make_order, answers={**HOODIE_ANSWERS, "colors": "black, max ¥20 each"})

    [request] = _outgoing(deps)
    assert request["status"] == "blocked"
    order = await get_order(app, "o1")
    assert order["manufacturer_attempts"][0]["outcome"] == "blocked"
    assert "price guard" in order["needs_human"]


async def test_spec_mismatch_needs_real_quote_text(make_order):
    text = "我们只有300克的面料，可以吗？"
    analysis = ReplyAnalysis(
        kind="other",
        mismatches=[
            SpecMismatch(field_id="fabric_gsm", manufacturer_says="300 GSM only", quoted_text="只有300克的面料"),
            SpecMismatch(field_id="colors", manufacturer_says="grey", quoted_text="灰色"),  # not in message
        ],
        summary_en="offers 300gsm",
    )
    app, deps = await _to_sourcing(make_order, analyses=[analysis])
    await on_event(app, "o1", _reply(text))

    tasks = [t["reason"] for t in (await get_order(app, "o1"))["human_tasks"]]
    assert any("fabric_gsm" in t for t in tasks)
    assert not any("colors" in t for t in tasks)
    # Recorded with the field, for the customer's "mismatches caught" and the stats page
    mismatches = [t for t in (await get_order(app, "o1"))["human_tasks"] if t.get("kind") == "mismatch"]
    assert [m["field_id"] for m in mismatches] == ["fabric_gsm"]


async def test_acknowledgement_keeps_waiting(make_order):
    ack = ReplyAnalysis(kind="acknowledgement", summary_en="received")
    app, deps = await _to_sourcing(make_order, analyses=[ack])
    await on_event(app, "o1", _reply("收到，稍后回复"))

    order = await get_order(app, "o1")
    assert order["manufacturer_attempts"][0]["outcome"] == "waiting"
    assert order["stage"] == "sourcing" and not order.get("needs_human")


def test_request_is_grouped_bilingual_with_files_attached_and_placement_in_words():
    spec = ProductSpec(market="apparel", option="hoodie", answers={
        **{k: v for k, v in HOODIE_ANSWERS.items() if k != "size_breakdown"},
        "colors": ["black"],
        "artwork": [{"file_id": "f-1", "name": "logo.png", "content_type": "image/png"}],
        "decoration_placement": [{"kind": "logo", "view": "front", "x": 0.5, "y": 0.35, "width_cm": 12.5, "height_cm": 11.5}],
        "zip_colour": "أسود",                                         # an AI question, answered in Arabic
    }, labels={"zip_colour": "لون السحاب"}, sections={"zip_colour": "design"})
    spec.set_answer("size_breakdown", {"M": 50, "L": 50})
    spec_zh = {"product_zh": "卫衣", "fields": [
        {"id": "colors", "label_zh": "颜色", "value_zh": "黑色"},
        {"id": "artwork", "label_zh": "图案文件", "value_zh": "logo.png（文件ID：f-1）"},   # older translations
        {"id": "zip_colour", "label_zh": "拉链颜色", "value_zh": "黑色", "value_en": "black"},
    ]}
    text = render_request(spec, spec_zh, "ord_0123456789ab")

    assert "【询价单】卫衣（订单号 ord_0123456789ab）" in text and "尺码分配：M × 50，L × 50" in text
    assert "一、款式与设计" in text and "三、面料、工艺与包装" in text
    assert "颜色：黑色" in text and "附件1 (logo.png)" in text and "附件1：logo.png" in text
    assert "Logo：正面胸部，居中，宽 12.5 × 高 11.5 厘米" in text
    assert "f-1" not in text and "x：" not in text                                    # no ids or raw coordinates
    assert "English version" in text and "Attachment 1: logo.png" in text and "logo, front, centre chest" in text
    assert "拉链颜色：黑色" in text and "Zip colour: black" in text and "أسود" not in text
    assert "A. Design" in text and "Decoration placement: logo, front" in text
    assert price_violation(text) is None
    assert request_files(spec) == [{"file_id": "f-1", "name": "logo.png", "content_type": "image/png"}]


def test_each_placed_picture_keeps_its_file_and_the_factory_sees_which_attachment_goes_where():
    from orion.config.markets import get_questions
    from orion.spec import validate_answer

    placement = next(q for q in get_questions("apparel", "hoodie") if q.id == "decoration_placement")
    placed = validate_answer(placement, [
        {"kind": "logo", "view": "front", "x": 0.63, "y": 0.3, "width_cm": 9, "height_cm": 7, "file_id": "f-2"},
        {"kind": "label", "view": "back", "x": 0.5, "y": 0.12, "width_cm": 5, "height_cm": 2.5},
    ])
    assert placed[0]["file_id"] == "f-2" and "file_id" not in placed[1]

    files = [{"file_id": "f-1", "name": "label.png", "content_type": "image/png"},
             {"file_id": "f-2", "name": "logo.png", "content_type": "image/png"}]
    spec = ProductSpec(market="apparel", option="hoodie", answers={"artwork": files, "decoration_placement": placed})
    spec.set_answer("size_breakdown", {"M": 10})
    text = render_request(spec, {"product_zh": "卫衣", "fields": []}, "ord_0123456789ab")
    assert "Logo：正面胸部，穿着者左侧，宽 9 × 高 7 厘米 (附件2)" in text
    assert "logo, front, wearer's left chest, 9 x 7 cm (attachment 2)" in text
