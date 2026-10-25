"""Ordering-flow nodes. Plain functions: state in, partial state update out. No LangGraph imports.

Interactive nodes follow one pattern:
- no `reply` in state  -> return a `pending` prompt (the graph then waits for the customer)
- `reply` present      -> validate it, consume it (`reply: None`), and either move on or re-ask with an error
"""

import logging
import re
from typing import Any

from orion.config.markets import CUSTOM_OPTION, MARKETS, Market, get_questions
from orion.config.policy import Policy
from orion.graph.pre_receipt import build_summary, render_pre_receipt
from orion.graph.state import OrderState
from orion.spec import (
    QUANTITY_ID,
    SIZE_TABLE_ID,
    InvalidAnswer,
    ProductSpec,
    Question,
    format_answer,
    is_blank,
    is_file_list,
    validate_answer,
)
from orion.tools.llm import AnswerUpdate, Consultant, ConsultContext, DeepDiveTurn

log = logging.getLogger(__name__)

WAIT = "wait_for_customer"
_QUANTITY_QUESTION = Question(id=QUANTITY_ID, prompt="Total quantity", type="number")
MAX_FOLLOW_UPS = 5
MAX_FOLLOW_UPS_CUSTOM = 8      # a custom product starts from a description, so the first rounds ask more
FOLLOW_UP_INTRO = {"en": "A few more details to get your product right:", "ar": "بعض التفاصيل الإضافية لنصنع منتجك بدقة:"}


# --- helpers --------------------------------------------------------------------

def _reply_value(reply: Any, key: str) -> Any:
    """Replies are dicts like {"choice": ...}; a bare value is accepted as shorthand."""
    return reply.get(key) if isinstance(reply, dict) else reply


def _lang(reply: Any) -> dict:
    """The website sends the customer's language with each answer; remember it for the AI."""
    lang = reply.get("lang") if isinstance(reply, dict) else None
    return {"lang": lang} if lang in ("ar", "en") else {}


def _spec(state: OrderState) -> ProductSpec:
    return ProductSpec.model_validate(state["spec"])


def _market(state: OrderState) -> Market:
    return MARKETS[state["market"]]


def _images(spec: ProductSpec) -> list[dict]:
    """Uploaded pictures in the answers, for the AI to look at."""
    return [
        {"file_id": f["file_id"], "content_type": f.get("content_type", "")}
        for value in spec.answers.values() if is_file_list(value)
        for f in value if str(f.get("content_type", "")).startswith("image/")
    ]


def _context(state: OrderState, spec: ProductSpec, messages: list[dict]) -> ConsultContext:
    market = _market(state)
    custom = spec.option == CUSTOM_OPTION
    return ConsultContext(
        order_id=state.get("order_id", ""),
        business=state.get("business") or {},
        images=_images(spec),
        custom=custom,
        max_questions=MAX_FOLLOW_UPS_CUSTOM if custom else MAX_FOLLOW_UPS,
        market_name=market.name,
        option_name=market.options[spec.option].name,
        questions=get_questions(market.id, spec.option),
        spec=spec,
        messages=messages,
        compliance_notes=market.compliance_notes,
        lang=state.get("lang", "en"),
    )


def _match_choice(value: Any, options: dict[str, str]) -> str | None:
    """Match a reply against {id: name} by id, name, or 1-based number."""
    text = str(value or "").strip().lower()
    for i, (oid, name) in enumerate(options.items(), start=1):
        if text in (oid.lower(), name.lower(), str(i)):
            return oid
    return None


def apply_updates(spec: ProductSpec, questions: list[Question], updates: list[AnswerUpdate]) -> list[str]:
    """Apply LLM-proposed answers through code validation. Returns the ids that were rejected."""
    by_id = {q.id: q for q in questions}
    has_size_table = SIZE_TABLE_ID in by_id
    rejected = []
    for update in updates:
        qid = update.id.strip().lower().replace(" ", "_")
        if qid == QUANTITY_ID and has_size_table:
            rejected.append(qid)  # quantity is derived from the size table
            continue
        question = by_id.get(qid) or (_QUANTITY_QUESTION if qid == QUANTITY_ID else None)
        if question is None:
            question = Question(id=qid, prompt=qid, type="text")
        try:
            spec.set_answer(qid, validate_answer(question, update.value))
        except InvalidAnswer as e:
            log.warning("rejected LLM update %s=%r: %s", qid, update.value, e)
            rejected.append(qid)
    return rejected


# --- nodes ----------------------------------------------------------------------

def _prefilled_spec(market: Market, option_id: str, prefill: dict) -> ProductSpec:
    """A reorder starts from the earlier order's answers. Answers that no longer validate are dropped,
    so a changed question list never carries a stale value into the new order."""
    spec = ProductSpec(market=market.id, option=option_id)
    questions = {q.id: q for q in get_questions(market.id, option_id)}
    labels, sections = prefill.get("labels") or {}, prefill.get("sections") or {}
    for qid, raw in (prefill.get("answers") or {}).items():
        question = questions.get(qid)
        if question is None:
            # A detail the AI asked about last time: keep it, with its wording and section
            if isinstance(raw, (str, int, float)) and not is_blank(raw):
                spec.set_answer(qid, raw)
                if qid in labels:
                    spec.labels[qid] = labels[qid]
                if sections.get(qid):
                    spec.sections[qid] = sections[qid]
            continue
        try:
            spec.set_answer(qid, validate_answer(question, raw))
        except InvalidAnswer as e:
            log.info("reorder: dropped %s=%r: %s", qid, raw, e)
    return spec


def select_market(state: OrderState) -> dict:
    options = {m.id: m.name for m in MARKETS.values()}
    names_ar = {m.id: m.name_ar for m in MARKETS.values()}
    reply = state.get("reply")
    prefill = state.get("prefill") or {}
    if reply is None and prefill.get("market") in options:
        return {"market": prefill["market"], "pending": None}
    if reply is not None:
        market_id = _match_choice(_reply_value(reply, "choice"), options)
        if market_id:
            return {"market": market_id, "reply": None, "pending": None}
    return {
        "reply": None,
        "pending": {
            "step": "select_market",
            "kind": "choice",
            "prompt": "Which market is your product in?",
            "prompt_ar": "في أي مجال منتجك؟",
            "options": [{"id": k, "name": v, "name_ar": names_ar[k]} for k, v in options.items()],
            "error": "Please pick one of the options." if reply is not None else None,
        },
    }


def pick_option(state: OrderState) -> dict:
    market = _market(state)
    options = {o.id: o.name for o in market.options.values()}
    names_ar = {o.id: o.name_ar for o in market.options.values()}
    reply = state.get("reply")
    prefill = state.get("prefill") or {}
    if reply is None and prefill.get("option") in options:
        spec = _prefilled_spec(market, prefill["option"], prefill)
        return {"spec": spec.model_dump(), "pending": None, "prefill": None, **_lang(prefill)}
    if reply is not None:
        option_id = _match_choice(_reply_value(reply, "choice"), options)
        if option_id:
            spec = ProductSpec(market=market.id, option=option_id)
            return {"spec": spec.model_dump(), "reply": None, "pending": None, **_lang(reply)}
    return {
        "reply": None,
        "pending": {
            "step": "pick_option",
            "kind": "choice",
            "prompt": "What would you like to make?",
            "prompt_ar": "ماذا تريد أن تصنع؟",
            "options": [{"id": k, "name": v, "name_ar": names_ar[k]} for k, v in options.items()],
            "error": "Please pick one of the options." if reply is not None else None,
        },
    }


def mandatory_questions(state: OrderState) -> dict:
    spec = _spec(state)
    questions = get_questions(spec.market, spec.option)
    if not questions:
        return {"pending": None}  # custom: the deep dive works out what to ask

    errors: dict[str, str] = {}
    reply = state.get("reply")
    if reply is not None:
        raw_answers = _reply_value(reply, "answers") or {}
        for q in questions:
            raw = raw_answers.get(q.id)
            if is_blank(raw):
                if q.required and q.id not in spec.answers:
                    errors[q.id] = "This answer is required."
                continue
            try:
                spec.set_answer(q.id, validate_answer(q, raw))
            except InvalidAnswer as e:
                errors[q.id] = str(e)
        if not errors:
            return {"spec": spec.model_dump(), "reply": None, "pending": None, **_lang(reply)}

    return {
        "spec": spec.model_dump(),
        "reply": None,
        "pending": {
            "step": "mandatory_questions",
            "kind": "form",
            "prompt": "A few details every manufacturer needs:",
            "prompt_ar": "تفاصيل يحتاجها كل مصنع:",
            "questions": [q.model_dump() for q in questions],
            "values": spec.answers,
            "errors": errors,
        },
    }


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def _follow_ups(turn: DeepDiveTurn, market_questions: list[Question], limit: int = MAX_FOLLOW_UPS) -> list[Question]:
    """The AI's questions, checked in code: unique ids, no size/quantity, at most `limit`."""
    covered_by_form = {SIZE_TABLE_ID, QUANTITY_ID} | {q.id for q in market_questions if q.type == "size_table"}
    out: list[Question] = []
    for f in turn.questions:
        qid = _slug(f.id)
        if not qid or qid in covered_by_form or any(q.id == qid for q in out) or not f.prompt.strip():
            continue
        choices = list(dict.fromkeys(c.strip() for c in f.choices if c.strip()))[:8]
        out.append(Question(
            id=qid, prompt=f.prompt.strip(), section=f.section, required=True,
            type="choice" if choices else "text", choices=choices,
            allow_other=True, multiple=bool(f.multiple and choices),
        ))
        if len(out) == limit:
            break
    return out


def _gap_questions(spec: ProductSpec) -> list[Question]:
    """Fallback when the AI should ask but returned nothing usable: ask the open gaps as text questions."""
    gaps = spec.open_gaps[:MAX_FOLLOW_UPS] or ["Anything else the manufacturer should know?"]
    return [
        Question(id=_slug(g) or f"detail_{i}", prompt=g, type="text", required=False, section="design")
        for i, g in enumerate(gaps, start=1)
    ]


async def deep_dive(state: OrderState, consultant: Consultant) -> dict:
    """The AI's follow-up questions, asked as more form questions (same style as the first form)
    until it has nothing left to ask."""
    spec = _spec(state)
    messages = list(state.get("messages", []))
    reply = state.get("reply")
    pending = state.get("pending") or {}
    lang_update = _lang(reply)
    lang = lang_update.get("lang") or state.get("lang", "en")
    market_questions = get_questions(spec.market, spec.option)

    if reply is not None and pending.get("step") == "deep_dive" and pending.get("kind") == "form":
        # Answers to our last round of questions: validated in code before anything is recorded
        asked = [Question.model_validate(q) for q in pending["questions"]]
        by_market_id = {q.id: q for q in market_questions}
        raw_answers = _reply_value(reply, "answers") or {}
        errors, lines = {}, []
        for q in asked:
            raw = raw_answers.get(q.id)
            if is_blank(raw):
                if q.required:
                    errors[q.id] = "This answer is required."
                continue
            try:
                value = validate_answer(q, raw)
                if q.id in by_market_id:   # correcting a form answer: keep that question's type (e.g. a number)
                    original = by_market_id[q.id]
                    value = validate_answer(original, value if original.type == "choice" else format_answer(value))
                spec.set_answer(q.id, value)
                if q.id not in by_market_id:   # the AI's own question: keep its wording and section for the receipt
                    spec.labels[q.id] = q.prompt.rstrip("?؟:. ")
                    spec.sections[q.id] = q.section
                lines.append(f"{q.prompt} → {format_answer(value)}")
            except InvalidAnswer as e:
                errors[q.id] = str(e)
        if errors:
            return {
                "spec": spec.model_dump(), "reply": None, **lang_update,
                "pending": {**pending, "values": raw_answers, "errors": errors},
            }
        if lines:
            messages.append({"role": "customer", "content": "\n".join(lines)})
    elif reply is not None:
        text = str(_reply_value(reply, "message") or "").strip()
        if text:
            messages.append({"role": "customer", "content": text})

    ctx = _context(state, spec, messages).model_copy(update={"lang": lang})
    turn = await consultant.deep_dive(ctx)
    apply_updates(spec, ctx.questions, turn.updates)
    questions = _follow_ups(turn, market_questions, ctx.max_questions)

    # Guard against a loop with no customer in it: right after the completeness check found gaps,
    # the AI must ask the customer something rather than declaring itself done again.
    ready = turn.ready_for_review and not (reply is None and spec.open_gaps)
    if not ready and not questions:
        questions = _gap_questions(spec)

    update = {"spec": spec.model_dump(), "messages": messages, "reply": None, "pending": None, **lang_update}
    if not ready:
        intro = turn.intro.strip() or FOLLOW_UP_INTRO[lang]
        messages.append({"role": "orion", "content": intro + "\n" + "\n".join(f"- {q.prompt}" for q in questions)})
        update["pending"] = {
            "step": "deep_dive",
            "kind": "form",
            "prompt": intro,
            "questions": [q.model_dump() for q in questions],
            "values": {},
            "errors": {},
        }
    return update


async def completeness_check(state: OrderState, consultant: Consultant, policy: Policy) -> dict:
    """A separate check of the spec: what would a manufacturer still have to ask?"""
    spec = _spec(state)
    questions = get_questions(spec.market, spec.option)

    # Code checks first: these never depend on the LLM.
    gaps = [q.prompt for q in questions if q.required and q.id not in spec.answers]
    if spec.quantity is None:
        gaps.append("How many pieces in total?")

    report = await consultant.check_completeness(_context(state, spec, []))
    gaps += [g for g in report.gaps if g.strip()]
    spec.open_gaps = gaps

    rounds = state.get("gap_rounds", 0) + 1 if gaps else 0
    update = {"spec": spec.model_dump(), "gap_rounds": rounds}
    if gaps and rounds >= policy.max_gap_rounds:
        update["needs_human"] = f"Spec still has {len(gaps)} open gap(s) after {rounds} rounds"
    return update


def build_pre_receipt(state: OrderState) -> dict:
    spec = _spec(state)
    market = _market(state)
    questions = get_questions(market.id, spec.option)
    lang = state.get("lang", "en")
    return {
        "pre_receipt": render_pre_receipt(spec, market, questions, lang),
        "summary": build_summary(spec, market, questions, lang),
        "stage": "pre_receipt_review",
    }


def customer_confirm(state: OrderState) -> dict:
    reply = state.get("reply")
    error = None
    if reply is not None:
        confirmed = bool(reply.get("confirm")) if isinstance(reply, dict) else False
        changes = str(reply.get("changes") or "").strip() if isinstance(reply, dict) else str(reply).strip()
        if confirmed:
            return {"confirmed": True, "reply": None, "pending": None}
        if changes:
            messages = list(state.get("messages", []))
            messages.append({"role": "customer", "content": f"I'd like to change: {changes}"})
            return {
                **_lang(reply),
                "confirmed": False,
                "messages": messages,
                "stage": "draft",
                "gap_rounds": 0,
                "needs_human": None,
                "reply": None,
                "pending": None,
            }
        error = "Please confirm, or tell us what to change."
    return {
        "reply": None,
        "pending": {
            "step": "customer_confirm",
            "kind": "confirm",
            "prompt": "Please review your product summary.",
            "prompt_ar": "راجع ملخص منتجك.",
            "pre_receipt": state["pre_receipt"],
            "summary": state.get("summary"),
            "error": error,
        },
    }


def freeze_spec(state: OrderState) -> dict:
    spec = _spec(state)
    spec.frozen = True
    versions = list(state.get("spec_versions", []))
    spec.version = len(versions) + 1
    versions.append(spec.model_dump())
    return {"spec": spec.model_dump(), "spec_versions": versions, "stage": "spec_frozen", "pending": None}


# --- routing --------------------------------------------------------------------

def wait_or(next_node: str):
    def route(state: OrderState) -> str:
        return WAIT if state.get("pending") else next_node
    return route


def resume_step(state: OrderState) -> str:
    return state["pending"]["step"]


def route_after_completeness(state: OrderState) -> str:
    if state["spec"]["open_gaps"] and not state.get("needs_human"):
        return "deep_dive"
    return "build_pre_receipt"


def route_after_confirm(state: OrderState) -> str:
    if state.get("pending"):
        return WAIT
    return "freeze_spec" if state.get("confirmed") else "deep_dive"
