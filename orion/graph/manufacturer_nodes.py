"""Manufacturer-side nodes. Plain functions: state in, partial state update out. No LangGraph imports.

The flow after the spec is frozen:
translate_spec → contact_manufacturer → (wait) → handle_manufacturer_event → (wait | contact next)

handle_manufacturer_event takes two event types:
- manufacturer_reply: {"type", "event_id", "manufacturer_id", "text"}
- timeout:            {"type", "event_id", "kind", "ref"} fired by the worker from the deadlines table
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from orion.config.china_calendar import KNOWN_YEARS, add_working_days
from orion.config.markets import MARKETS, get_questions
from orion.config.policy import Policy
from orion.db.stores import ManufacturerDirectory, PriceRecord, PriceStore, Scheduler
from orion.graph.manufacturer_request import NOT_TRANSLATED, render_reminder, render_request
from orion.graph.state import OrderState
from orion.spec import QUANTITY_ID, ProductSpec, format_answer
from orion.tools.channel import BlockedMessage, Channel, OutgoingMessage, send_to_manufacturer
from orion.tools.manufacturer_llm import ManufacturerAgent
from orion.tools.price_guard import find_negotiation
from orion.tools.prices import check_price

log = logging.getLogger(__name__)

STILL_WAITING = ("waiting", "clarifying")   # attempt outcomes where the reply clock is running


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _spec(state: OrderState) -> ProductSpec:
    return ProductSpec.model_validate(state["spec"])


def _with_tasks(state: OrderState, reasons: list[str | dict], **context) -> dict:
    """Append human tasks and point `needs_human` at the latest one.
    A reason is text, or {"reason": ..., **details} for tasks with structured details (spec mismatches)."""
    if not reasons:
        return {}
    items = [r if isinstance(r, dict) else {"reason": r} for r in reasons]
    tasks = list(state.get("human_tasks", []))
    tasks += [{**item, "at": _now().isoformat(), **context} for item in items]
    return {"human_tasks": tasks, "needs_human": items[-1]["reason"]}


def _reply_deadline(days: int) -> tuple[datetime, list[str]]:
    due = add_working_days(_now(), days)
    tasks = []
    if due.year not in KNOWN_YEARS:
        tasks.append(f"China holiday calendar for {due.year} is missing; deadline counts weekends only")
    return due, tasks


async def translate_spec(state: OrderState, agent: ManufacturerAgent) -> dict:
    """Translate the frozen spec once. Code checks every answer is covered."""
    spec = _spec(state)
    option = MARKETS[spec.market].options[spec.option]
    translation = await agent.translate_spec(spec, option.name)

    by_id = {f.id: f for f in translation.fields}
    fields = []
    for qid, value in spec.answers.items():
        if qid in NOT_TRANSLATED:
            continue
        f = by_id.get(qid)
        if f and f.value_zh.strip():
            fields.append({"id": qid, "label_zh": f.label_zh, "value_zh": f.value_zh})
        else:
            # Never drop a spec detail: fall back to the original wording.
            fields.append({"id": qid, "label_zh": qid, "value_zh": format_answer(value)})
    return {"spec_zh": {"product_zh": translation.product_zh or option.name, "fields": fields}}


async def contact_manufacturer(
    state: OrderState, directory: ManufacturerDirectory, channel: Channel, scheduler: Scheduler, policy: Policy
) -> dict:
    """Send the quote request to the next manufacturer on the ranked list and start its reply clock."""
    spec = _spec(state)
    attempts = list(state.get("manufacturer_attempts", []))
    contacted = {a["manufacturer_id"] for a in attempts}
    candidates = await directory.ranked_for(spec.market, spec.option)
    manufacturer = next((m for m in candidates if m.id not in contacted), None)

    if manufacturer is None:
        return {
            "current_manufacturer": None,
            **_with_tasks(state, [f"No manufacturer left to contact for {spec.market}/{spec.option}"]),
        }

    due, tasks = _reply_deadline(policy.manufacturer_timeout_days)
    attempt = {
        "manufacturer_id": manufacturer.id,
        "name": manufacturer.name,
        "contacted_at": _now().isoformat(),
        "deadline_at": due.isoformat(),
        "reminded": False,
        "outcome": "waiting",
    }
    message = OutgoingMessage(
        id=f"{state['order_id']}:request:{manufacturer.id}",
        order_id=state["order_id"],
        manufacturer_id=manufacturer.id,
        text=render_request(spec, state["spec_zh"]),
    )
    try:
        await send_to_manufacturer(channel, message)
        await scheduler.schedule(state["order_id"], "manufacturer_reply", manufacturer.id, due)
    except BlockedMessage as e:
        attempt["outcome"] = "blocked"
        tasks.append(f"Quote request to {manufacturer.name} blocked by the price guard ({e}); check the spec")

    return {
        "stage": "quote_received" if state.get("quotes") else "sourcing",
        "manufacturer_attempts": attempts + [attempt],
        "current_manufacturer": manufacturer.id if attempt["outcome"] == "waiting" else None,
        **_with_tasks(state, tasks, manufacturer_id=manufacturer.id),
    }


def _ignored(state: OrderState, event: dict) -> bool:
    """Rule 7: idempotent, and only events this order can act on."""
    if not isinstance(event, dict) or not event.get("event_id"):
        return True
    if event["event_id"] in state.get("processed_events", []):
        return True
    if event.get("type") == "timeout":
        return event.get("kind") not in ("manufacturer_reply", "quote_expiry") or not event.get("ref")
    contacted = {a["manufacturer_id"] for a in state.get("manufacturer_attempts", [])}
    return (
        event.get("type") != "manufacturer_reply"
        or event.get("manufacturer_id") not in contacted
        or not str(event.get("text") or "").strip()
    )


async def handle_manufacturer_event(
    state: OrderState,
    agent: ManufacturerAgent,
    channel: Channel,
    prices: PriceStore,
    scheduler: Scheduler,
    policy: Policy,
) -> dict:
    event = state.get("event") or {}
    if _ignored(state, event):
        log.info("order %s ignored event %r", state.get("order_id"), event)
        return {"event": None, "manufacturer_next": "wait"}

    update = {
        "event": None,
        "manufacturer_next": "wait",
        "processed_events": list(state.get("processed_events", [])) + [event["event_id"]],
    }
    if event["type"] == "timeout":
        update.update(await _handle_timeout(state, event, channel, scheduler, policy))
    else:
        update.update(await _handle_reply(state, event, agent, channel, prices, scheduler, policy))
    return update


async def _handle_timeout(
    state: OrderState, event: dict, channel: Channel, scheduler: Scheduler, policy: Policy
) -> dict:
    order_id, kind, ref = state["order_id"], event["kind"], event["ref"]

    if kind == "quote_expiry":
        quotes = [dict(q) for q in state.get("quotes", [])]
        quote = next((q for q in quotes if q.get("quote_id") == ref), None)
        if quote is None or quote.get("expired"):
            return {}
        quote["expired"] = True
        return {
            "quotes": quotes,
            **_with_tasks(state, [f"Quote from {quote['manufacturer_id']} expired before the customer decided"],
                          manufacturer_id=quote["manufacturer_id"]),
        }

    # manufacturer_reply: no usable reply in time
    attempts = [dict(a) for a in state.get("manufacturer_attempts", [])]
    attempt = next((a for a in attempts if a["manufacturer_id"] == ref), None)
    if attempt is None or attempt["outcome"] not in STILL_WAITING:
        return {}   # the clock already stopped (quote, decline...)

    if not attempt.get("reminded"):
        # One reminder before escalating
        due, tasks = _reply_deadline(policy.manufacturer_reminder_days)
        attempt.update(reminded=True, deadline_at=due.isoformat())
        try:
            await send_to_manufacturer(channel, OutgoingMessage(
                id=f"{order_id}:reminder:{ref}",
                order_id=order_id,
                manufacturer_id=ref,
                text=render_reminder(state["spec_zh"]),
            ))
            await scheduler.schedule(order_id, "manufacturer_reply", ref, due)
        except BlockedMessage as e:
            tasks.append(f"Reminder to {attempt['name']} blocked by the price guard ({e})")
        return {"manufacturer_attempts": attempts, **_with_tasks(state, tasks, manufacturer_id=ref)}

    # Already reminded: move on, but keep this manufacturer open (nothing is committed yet)
    attempt["outcome"] = "no_reply"
    update = {"manufacturer_attempts": attempts}
    if state.get("current_manufacturer") == ref:
        update["current_manufacturer"] = None
        update["manufacturer_next"] = "contact_next"
    return update


async def _handle_reply(
    state: OrderState,
    event: dict,
    agent: ManufacturerAgent,
    channel: Channel,
    prices: PriceStore,
    scheduler: Scheduler,
    policy: Policy,
) -> dict:
    order_id, event_id, manufacturer_id = state["order_id"], event["event_id"], event["manufacturer_id"]
    text = str(event["text"]).strip()
    await channel.record_incoming(event_id, order_id, manufacturer_id, text)

    spec = _spec(state)
    analysis = await agent.analyze_reply(spec, state["spec_zh"], text)
    tasks: list[str | dict] = []
    update: dict = {}

    # Negotiation: never answered by the AI. Code check plus the model's flag.
    if find_negotiation(text) or analysis.mentions_negotiation:
        tasks.append("Manufacturer raised pricing or negotiation; the team must reply")

    # Prices: code decides what is trusted (rule 2)
    file_questions = {q.id for q in get_questions(spec.market, spec.option) if q.type == "file"}
    attributes = {k: v for k, v in spec.answers.items() if k not in file_questions}
    recorded = []
    for i, price in enumerate(analysis.prices):
        check = check_price(price, text)
        if not check.trusted_text:
            tasks.append(f"Could not verify a price in the message: {'; '.join(check.problems)}")
            continue
        await prices.append(PriceRecord(
            source_key=f"{event_id}:{i}",
            manufacturer_id=manufacturer_id,
            order_id=order_id,
            market=spec.market,
            option=spec.option,
            attributes=attributes,
            quantity=price.quantity,
            unit_price=price.unit_price,
            currency=check.currency,
            unit=price.unit,
            incoterm=price.incoterm,
            shipping_included=price.shipping_included,
            tax_included=price.tax_included,
            source="order",
            source_message_id=event_id,
            quoted_text=price.quoted_text,
            original_text=text,
            status=check.status,
            problems=check.problems,
        ))
        recorded.append({
            "unit_price": price.unit_price, "currency": check.currency, "quantity": price.quantity,
            "status": check.status,
        })
        if check.status != "verified":
            tasks.append(f"Unverified price {price.unit_price} {price.currency or ''}: {', '.join(check.problems)}")

    # Verify loop: differences from the frozen spec are never accepted silently
    known_fields = set(spec.answers) | {QUANTITY_ID}
    for m in analysis.mismatches:
        if m.field_id in known_fields and _squash(m.quoted_text) and _squash(m.quoted_text) in _squash(text):
            tasks.append({
                "reason": f"Manufacturer differs from the spec on '{m.field_id}': {m.manufacturer_says}",
                "kind": "mismatch", "field_id": m.field_id,
            })

    attempts = [dict(a) for a in state.get("manufacturer_attempts", [])]
    attempt = next(a for a in attempts if a["manufacturer_id"] == manufacturer_id)
    now = _now()

    if analysis.kind == "decline":
        attempt["outcome"] = "declined"
        await scheduler.cancel(order_id, "manufacturer_reply", manufacturer_id)
        if state.get("current_manufacturer") == manufacturer_id:
            update["current_manufacturer"] = None
            update["manufacturer_next"] = "contact_next"
    elif analysis.kind == "quote":
        # The clock stops only on a message with what we asked for, not on "received"
        attempt.update(outcome="quoted", answered_at=now.isoformat())
        await scheduler.cancel(order_id, "manufacturer_reply", manufacturer_id)
        if recorded:
            expires_at = now + timedelta(days=policy.quote_validity_days)
            await scheduler.schedule(order_id, "quote_expiry", event_id, expires_at)
            update["stage"] = "quote_received"
            update["quotes"] = list(state.get("quotes", [])) + [{
                "quote_id": event_id,
                "manufacturer_id": manufacturer_id,
                "prices": recorded,
                "moq": analysis.moq,
                "lead_time_days": analysis.lead_time_days,
                "sample_terms": analysis.sample_terms,
                "summary": analysis.summary_en,
                "expires_at": expires_at.isoformat(),
                "expired": False,
            }]
            # TODO(decide): customer quote document (fee, shipping, customs) is not designed yet
            tasks.append("Quote received: prepare the customer quote")
        elif not analysis.prices:
            tasks.append("Manufacturer sent a quote but no price could be extracted")
    elif analysis.questions and attempt["outcome"] == "waiting":
        attempt["outcome"] = "clarifying"
        if state.get("stage") == "sourcing":
            update["stage"] = "clarifying"

    if analysis.questions and analysis.kind != "decline":
        tasks += await _answer_questions(state, agent, channel, spec, analysis.questions, event_id, manufacturer_id)

    update["manufacturer_attempts"] = attempts
    update.update(_with_tasks(state, tasks, manufacturer_id=manufacturer_id, event_id=event_id))
    return update


async def _answer_questions(
    state: OrderState,
    agent: ManufacturerAgent,
    channel: Channel,
    spec: ProductSpec,
    questions: list[str],
    event_id: str,
    manufacturer_id: str,
) -> list[str]:
    """Answer from the frozen spec only. Anything else goes to a human. Returns new human tasks."""
    drafts = await agent.answer_questions(spec, state["spec_zh"], questions)
    answered = [d for d in drafts.answers if d.answerable and d.answer_zh.strip()]
    if len(answered) < len(questions):
        open_questions = [d.question for d in drafts.answers if d not in answered] or questions
        return ["Manufacturer questions need a human: " + "; ".join(open_questions)]

    message = OutgoingMessage(
        id=f"{state['order_id']}:answer:{event_id}",
        order_id=state["order_id"],
        manufacturer_id=manufacturer_id,
        text="\n".join(f"{i}. {d.answer_zh}" for i, d in enumerate(answered, start=1)),
    )
    try:
        await send_to_manufacturer(channel, message)
    except BlockedMessage as e:
        return [f"Drafted answer to the manufacturer was blocked by the price guard ({e})"]
    return []


def route_after_manufacturer_event(state: OrderState) -> str:
    return "contact_manufacturer" if state.get("manufacturer_next") == "contact_next" else "wait_for_manufacturer"
