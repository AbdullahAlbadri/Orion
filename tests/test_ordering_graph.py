from conftest import HOODIE_ANSWERS, ScriptedConsultant, turn
from orion.config.policy import Policy
from orion.graph.graph import get_order, send_reply, start_order
from orion.tools.llm import CompletenessReport


async def _through_form(app, order_id, answers=HOODIE_ANSWERS):
    prompt = await start_order(app, order_id)
    assert prompt["kind"] == "choice" and prompt["step"] == "select_market"
    prompt = await send_reply(app, order_id, {"choice": "apparel"})
    assert prompt["step"] == "pick_option"
    prompt = await send_reply(app, order_id, {"choice": "Hoodie"})
    assert prompt["kind"] == "form"
    return await send_reply(app, order_id, {"answers": answers})


async def test_happy_path_freezes_spec(make_app):
    consultant = ScriptedConsultant(
        turns=[
            turn("Should the hood have drawstrings?"),
            turn("Thanks, preparing your summary.", ready=True, drawstrings="yes, flat black cotton"),
        ],
        reports=[CompletenessReport(gaps=[])],
    )
    app = make_app(consultant)

    prompt = await _through_form(app, "order-1")
    assert prompt == {"step": "deep_dive", "kind": "chat", "message": "Should the hood have drawstrings?"}

    prompt = await send_reply(app, "order-1", {"message": "Yes, flat black ones"})
    assert prompt["kind"] == "confirm"
    assert "Total quantity: 150" in prompt["pre_receipt"]
    assert "Drawstrings: yes, flat black cotton" in prompt["pre_receipt"]

    prompt = await send_reply(app, "order-1", {"confirm": True})
    assert prompt["waiting_on"] == "manufacturer"
    order = await get_order(app, "order-1")
    assert order["stage"] == "sourcing"
    assert order["spec"]["frozen"] and order["spec"]["version"] == 1
    assert order["spec"]["answers"]["fabric_gsm"] == 350
    assert len(order["spec_versions"]) == 1
    # The customer's chat reached the LLM
    assert consultant.deep_dive_calls[1].messages[-1] == {"role": "customer", "content": "Yes, flat black ones"}


async def test_invalid_form_is_re_asked_and_keeps_valid_answers(make_app):
    app = make_app(ScriptedConsultant(turns=[turn("Anything else?")], reports=[]))
    bad = {**HOODIE_ANSWERS, "fabric_gsm": "heavy", "size_breakdown": ""}
    prompt = await _through_form(app, "order-2", bad)

    assert prompt["kind"] == "form"
    assert set(prompt["errors"]) == {"fabric_gsm", "size_breakdown"}
    assert prompt["values"]["fabric"] == "cotton fleece"

    prompt = await send_reply(app, "order-2", {"answers": {"fabric_gsm": 320, "size_breakdown": {"M": 10}}})
    assert prompt["kind"] == "chat"
    assert (await get_order(app, "order-2"))["spec"]["quantity"] == 10


async def test_completeness_gaps_send_ai_back_to_customer(make_app):
    consultant = ScriptedConsultant(
        turns=[
            turn("All set!", ready=True),
            turn("All set!", ready=True),  # ignored: gaps are open and the customer hasn't answered yet
            turn("Done.", ready=True, cuff_style="ribbed"),
        ],
        reports=[CompletenessReport(gaps=["What cuff style?"]), CompletenessReport(gaps=[])],
    )
    app = make_app(consultant)

    prompt = await _through_form(app, "order-3")
    assert prompt["kind"] == "chat"  # the AI was forced to ask instead of looping
    assert consultant.deep_dive_calls[1].spec.open_gaps == ["What cuff style?"]

    prompt = await send_reply(app, "order-3", {"message": "ribbed cuffs"})
    assert prompt["kind"] == "confirm"
    assert "Cuff style: ribbed" in prompt["pre_receipt"]


async def test_requested_changes_loop_back_to_deep_dive(make_app):
    consultant = ScriptedConsultant(
        turns=[turn("Done.", ready=True), turn("Updated.", ready=True, colors="navy")],
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
        turns=[turn("Done.", ready=True), turn("What cuffs?"), turn("Done.", ready=True)],
        reports=[CompletenessReport(gaps=["What cuff style?"])] * 2,
    )
    app = make_app(consultant, policy=Policy(max_gap_rounds=2))
    prompt = await _through_form(app, "order-5")
    prompt = await send_reply(app, "order-5", {"message": "not sure"})

    assert prompt["kind"] == "confirm"
    assert "Still open" in prompt["pre_receipt"]
    assert (await get_order(app, "order-5"))["needs_human"]


async def test_llm_updates_are_validated(make_app):
    consultant = ScriptedConsultant(
        turns=[turn("Done.", ready=True, fabric_gsm="very thick", quantity="999")],
        reports=[],
    )
    app = make_app(consultant)
    await _through_form(app, "order-6")
    spec = (await get_order(app, "order-6"))["spec"]
    assert spec["answers"]["fabric_gsm"] == 350   # invalid LLM value rejected
    assert spec["quantity"] == 150                # quantity comes from the size table, not the LLM


async def test_custom_option_skips_form(make_app):
    consultant = ScriptedConsultant(
        turns=[turn("What garment are you thinking of?"), turn("Great.", ready=True, quantity="200", garment="bucket hat")],
        reports=[],
    )
    app = make_app(consultant)
    await start_order(app, "order-7")
    await send_reply(app, "order-7", {"choice": "apparel"})
    prompt = await send_reply(app, "order-7", {"choice": "custom"})
    assert prompt["kind"] == "chat"

    prompt = await send_reply(app, "order-7", {"message": "200 bucket hats"})
    assert prompt["kind"] == "confirm"
    assert "Total quantity: 200" in prompt["pre_receipt"]
