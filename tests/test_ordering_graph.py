from conftest import HOODIE_ANSWERS, ScriptedConsultant, ask, turn
from orion.config.policy import Policy
from orion.graph.graph import get_order, send_reply, start_order
from orion.tools.llm import CompletenessReport


async def _through_form(app, order_id, answers=HOODIE_ANSWERS, lang="en"):
    prompt = await start_order(app, order_id)
    assert prompt["kind"] == "choice" and prompt["step"] == "select_market"
    prompt = await send_reply(app, order_id, {"choice": "apparel"})
    assert prompt["step"] == "pick_option"
    prompt = await send_reply(app, order_id, {"choice": "Hoodie"})
    assert prompt["kind"] == "form"
    return await send_reply(app, order_id, {"answers": answers, "lang": lang})


async def test_follow_ups_are_form_questions_and_spec_freezes(make_app):
    consultant = ScriptedConsultant(
        turns=[
            turn("هل نسيت شيئًا؟", questions=[
                ask("drawstrings", "Hood drawstrings?", ["flat cotton", "round cord", "none"]),
                ask("pocket", "Pocket?", ["kangaroo pocket", "no pocket"], section="design"),
            ]),
            turn(ready=True),
        ],
        reports=[CompletenessReport(gaps=[])],
    )
    app = make_app(consultant)

    prompt = await _through_form(app, "order-1", lang="ar")
    assert prompt["step"] == "deep_dive" and prompt["kind"] == "form"
    assert prompt["prompt"] == "هل نسيت شيئًا؟"
    q = {x["id"]: x for x in prompt["questions"]}
    assert q["drawstrings"]["choices"] == ["flat cotton", "round cord", "none"]
    assert q["drawstrings"]["allow_other"] and q["drawstrings"]["section"] == "design"
    assert consultant.deep_dive_calls[0].lang == "ar"   # the AI writes in the customer's language

    # "Other" answer (own text) and a listed choice
    prompt = await send_reply(app, "order-1", {"answers": {"drawstrings": "flat black cotton, metal tips", "pocket": "kangaroo pocket"}})
    assert prompt["kind"] == "confirm"
    # The customer chose Arabic: the receipt is Arabic, choice values shown with their Arabic labels
    assert "الكمية الإجمالية: 150" in prompt["pre_receipt"]
    assert "حبال القلنسوة: flat black cotton, metal tips" in prompt["pre_receipt"]
    assert "ما ألوان القطعة: أسود، Pantone Black C" in prompt["pre_receipt"]
    summary = prompt["summary"]
    assert summary["product"] == "هودي" and summary["quantity"] == 150 and summary["sizes"]["M"] == 50
    design = next(s for s in summary["sections"] if s["id"] == "design")["items"]
    colors = next(i for i in design if i["id"] == "colors")
    assert colors["value"] == "أسود، Pantone Black C" and colors["raw"] == ["black", "Pantone Black C"]

    prompt = await send_reply(app, "order-1", {"confirm": True})
    assert prompt["waiting_on"] == "manufacturer"
    order = await get_order(app, "order-1")
    assert order["stage"] == "sourcing" and order["spec"]["frozen"] and order["spec"]["version"] == 1
    assert order["spec"]["answers"]["fabric_gsm"] == 350
    assert order["spec"]["answers"]["colors"] == ["black", "Pantone Black C"]
    # The answers reached the AI as history
    assert "Hood drawstrings? → flat black cotton, metal tips" in consultant.deep_dive_calls[1].messages[-1]["content"]


async def test_follow_up_answers_are_validated_without_calling_the_ai(make_app):
    consultant = ScriptedConsultant(turns=[turn(questions=[ask("drawstrings")]), turn(ready=True)], reports=[])
    app = make_app(consultant)
    await _through_form(app, "order-1b")

    prompt = await send_reply(app, "order-1b", {"answers": {}})   # required question left empty
    assert prompt["kind"] == "form" and set(prompt["errors"]) == {"drawstrings"}
    assert len(consultant.deep_dive_calls) == 1

    prompt = await send_reply(app, "order-1b", {"answers": {"drawstrings": "yes"}})
    assert prompt["kind"] == "confirm"


async def test_ai_cannot_ask_sizes_or_bad_ids(make_app):
    consultant = ScriptedConsultant(turns=[turn(questions=[
        ask("size_breakdown"), ask("quantity"), ask("Cuff Style!", "Cuffs?"), ask("cuff_style", "Again?"),
        ask("a"), ask("b"), ask("c"), ask("d"),
    ])], reports=[])
    app = make_app(consultant)
    prompt = await _through_form(app, "order-1c")
    ids = [q["id"] for q in prompt["questions"]]
    assert ids == ["cuff_style", "a", "b", "c", "d"]   # slugged, deduped, no sizes/quantity, at most 5


async def test_correcting_a_form_answer_keeps_its_type(make_app):
    consultant = ScriptedConsultant(
        turns=[turn(questions=[ask("fabric_gsm", "Heavier fabric?", ["320", "380"], section="quality")]), turn(ready=True)],
        reports=[],
    )
    app = make_app(consultant)
    await _through_form(app, "order-1d")
    prompt = await send_reply(app, "order-1d", {"answers": {"fabric_gsm": "heavy please"}})
    assert prompt["kind"] == "form" and "fabric_gsm" in prompt["errors"]   # must still be a number
    await send_reply(app, "order-1d", {"answers": {"fabric_gsm": "380"}})
    assert (await get_order(app, "order-1d"))["spec"]["answers"]["fabric_gsm"] == 380


async def test_invalid_form_is_re_asked_and_keeps_valid_answers(make_app):
    app = make_app(ScriptedConsultant(turns=[turn(questions=[ask("x")])], reports=[]))
    bad = {**HOODIE_ANSWERS, "fabric_gsm": "heavy", "size_breakdown": ""}
    prompt = await _through_form(app, "order-2", bad)

    assert prompt["kind"] == "form" and prompt["step"] == "mandatory_questions"
    assert set(prompt["errors"]) == {"fabric_gsm", "size_breakdown"}
    assert prompt["values"]["fabric"] == "cotton fleece"

    prompt = await send_reply(app, "order-2", {"answers": {"fabric_gsm": 320, "size_breakdown": {"M": 10}}})
    assert prompt["step"] == "deep_dive"
    assert (await get_order(app, "order-2"))["spec"]["quantity"] == 10


async def test_unknown_choice_rejected_unless_other_allowed(make_app):
    app = make_app(ScriptedConsultant(turns=[turn(ready=True)], reports=[]))
    prompt = await _through_form(app, "order-2b", {**HOODIE_ANSWERS, "hoodie_style": "poncho", "fabric": "bamboo fleece"})
    assert set(prompt["errors"]) == {"hoodie_style"}     # fixed choices only
    assert prompt["values"]["fabric"] == "bamboo fleece"  # "Other" allowed for fabric


async def test_completeness_gaps_become_questions(make_app):
    consultant = ScriptedConsultant(
        turns=[
            turn(ready=True),
            turn(ready=True),  # ignored: gaps are open and the customer hasn't answered yet
            turn(ready=True),
        ],
        reports=[CompletenessReport(gaps=["What cuff style?"]), CompletenessReport(gaps=[])],
    )
    app = make_app(consultant)

    prompt = await _through_form(app, "order-3")
    assert prompt["kind"] == "form"   # the AI was forced to ask instead of looping
    assert [q["prompt"] for q in prompt["questions"]] == ["What cuff style?"]
    assert consultant.deep_dive_calls[1].spec.open_gaps == ["What cuff style?"]

    prompt = await send_reply(app, "order-3", {"answers": {prompt["questions"][0]["id"]: "ribbed"}})
    assert prompt["kind"] == "confirm"
    assert "What cuff style: ribbed" in prompt["pre_receipt"]


async def test_requested_changes_loop_back_to_deep_dive(make_app):
    consultant = ScriptedConsultant(
        turns=[turn(ready=True), turn(ready=True, colors="navy")],
        reports=[],
    )
    app = make_app(consultant)
    prompt = await _through_form(app, "order-4")
    assert prompt["kind"] == "confirm"

    prompt = await send_reply(app, "order-4", {"confirm": False, "changes": "make it navy"})
    assert prompt["kind"] == "confirm"
    assert "Colors: navy" in prompt["pre_receipt"]
    assert consultant.deep_dive_calls[1].messages[-1]["content"] == "I'd like to change: make it navy"


async def test_gap_cap_flags_human(make_app):
    consultant = ScriptedConsultant(
        turns=[turn(ready=True), turn(questions=[ask("cuffs")]), turn(ready=True)],
        reports=[CompletenessReport(gaps=["What cuff style?"])] * 2,
    )
    app = make_app(consultant, policy=Policy(max_gap_rounds=2))
    await _through_form(app, "order-5")
    prompt = await send_reply(app, "order-5", {"answers": {"cuffs": "Not sure, use the factory standard"}})

    assert prompt["kind"] == "confirm"
    assert "Still open" in prompt["pre_receipt"]
    assert (await get_order(app, "order-5"))["needs_human"]


async def test_llm_updates_are_validated(make_app):
    consultant = ScriptedConsultant(
        turns=[turn(ready=True, fabric_gsm="very thick", quantity="999")],
        reports=[],
    )
    app = make_app(consultant)
    await _through_form(app, "order-6")
    spec = (await get_order(app, "order-6"))["spec"]
    assert spec["answers"]["fabric_gsm"] == 350   # invalid LLM value rejected
    assert spec["quantity"] == 150                # quantity comes from the size table, not the LLM


async def test_custom_product_starts_from_a_description_and_pictures(make_app):
    many = [ask(f"detail_{i}") for i in range(10)]
    consultant = ScriptedConsultant(
        turns=[turn("نحتاج بعض التفاصيل", questions=many), turn(ready=True)],
        reports=[],
    )
    app = make_app(consultant)
    await start_order(app, "order-7")
    await send_reply(app, "order-7", {"choice": "apparel"})
    prompt = await send_reply(app, "order-7", {"choice": "custom", "lang": "ar"})
    # First the customer describes it, can add pictures, and says how many
    assert prompt["kind"] == "form" and prompt["step"] == "mandatory_questions"
    assert [q["id"] for q in prompt["questions"]] == ["description", "reference_images", "quantity", "needed_by"]
    assert prompt["questions"][0]["multiline"]

    picture = {"file_id": "f-1", "name": "sketch.png", "content_type": "image/png"}
    prompt = await send_reply(app, "order-7", {"answers": {
        "description": "Bucket hats in sand colour with a small embroidered logo",
        "reference_images": [picture], "quantity": "200", "needed_by": "flexible",
    }})
    ctx = consultant.deep_dive_calls[0]
    assert ctx.custom and ctx.lang == "ar" and ctx.images == [{"file_id": "f-1", "content_type": "image/png"}]
    # A custom product gets a bigger first round of questions
    assert prompt["step"] == "deep_dive" and len(prompt["questions"]) == 8

    prompt = await send_reply(app, "order-7", {"answers": {q["id"]: "yes" for q in prompt["questions"]}})
    assert prompt["kind"] == "confirm"
    assert "الكمية الإجمالية: 200" in prompt["pre_receipt"]
    assert "sketch.png" in prompt["pre_receipt"]


async def test_consultant_sends_pictures_as_images():
    from orion.spec import ProductSpec
    from orion.tools.llm import ConsultContext, OpenRouterConsultant

    async def load(order_id, file_id):
        return (b"\x89PNG fake", "image/png") if file_id == "f-1" else None

    consultant = OpenRouterConsultant("unused", "http://unused", "x", load_image=load)
    ctx = ConsultContext(
        market_name="m", option_name="o", questions=[], spec=ProductSpec(market="apparel", option="custom"),
        order_id="o1", custom=True,
        images=[{"file_id": "f-1", "content_type": "image/png"}, {"file_id": "f-2", "content_type": "application/pdf"}],
    )
    content = await consultant._content(ctx)
    assert content[0]["type"] == "text" and "CUSTOM product" in content[0]["text"]
    assert [c["type"] for c in content[1:]] == ["image_url"]   # the PDF is not sent as an image
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")