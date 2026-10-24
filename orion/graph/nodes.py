"""Ordering-flow nodes. Plain functions: state in, partial state update out. No LangGraph imports.

Interactive nodes follow one pattern:
- no `reply` in state  -> return a `pending` prompt (the graph then waits for the customer)
- `reply` present      -> validate it, consume it (`reply: None`), and either move on or re-ask with an error
"""

import logging
from typing import Any

from orion.config.markets import MARKETS, Market, get_questions
from orion.config.policy import Policy
from orion.graph.pre_receipt import render_pre_receipt
from orion.graph.state import OrderState
from orion.spec import QUANTITY_ID, SIZE_TABLE_ID, InvalidAnswer, ProductSpec, Question, validate_answer
from orion.tools.llm import AnswerUpdate, Consultant, ConsultContext

log = logging.getLogger(__name__)

WAIT = "wait_for_customer"
_QUANTITY_QUESTION = Question(id=QUANTITY_ID, prompt="Total quantity", type="number")


# --- helpers --------------------------------------------------------------------

def _reply_value(reply: Any, key: str) -> Any:
    """Replies are dicts like {"choice": ...}; a bare value is accepted as shorthand."""
    return reply.get(key) if isinstance(reply, dict) else reply


def _spec(state: OrderState) -> ProductSpec:
    return ProductSpec.model_validate(state["spec"])


def _market(state: OrderState) -> Market:
    return MARKETS[state["market"]]


def _context(state: OrderState, spec: ProductSpec, messages: list[dict]) -> ConsultContext:
    market = _market(state)
    return ConsultContext(
        market_name=market.name,
        option_name=market.options[spec.option].name,
        questions=get_questions(market.id, spec.option),
        spec=spec,
        messages=messages,
        compliance_notes=market.compliance_notes,
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

def select_market(state: OrderState) -> dict:
    options = {m.id: m.name for m in MARKETS.values()}
    reply = state.get("reply")
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
            "options": [{"id": k, "name": v} for k, v in options.items()],
            "error": "Please pick one of the options." if reply is not None else None,
        },
    }


def pick_option(state: OrderState) -> dict:
    market = _market(state)
    options = {o.id: o.name for o in market.options.values()}
    reply = state.get("reply")
    if reply is not None:
        option_id = _match_choice(_reply_value(reply, "choice"), options)
        if option_id:
            spec = ProductSpec(market=market.id, option=option_id)
            return {"spec": spec.model_dump(), "reply": None, "pending": None}
    return {
        "reply": None,
        "pending": {
            "step": "pick_option",
            "kind": "choice",
            "prompt": "What would you like to make?",
            "options": [{"id": k, "name": v} for k, v in options.items()],
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
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                if q.required and q.id not in spec.answers:
                    errors[q.id] = "This answer is required."
                continue
            try:
                spec.set_answer(q.id, validate_answer(q, raw))
            except InvalidAnswer as e:
                errors[q.id] = str(e)
        if not errors:
            return {"spec": spec.model_dump(), "reply": None, "pending": None}

    return {
        "spec": spec.model_dump(),
        "reply": None,
        "pending": {
            "step": "mandatory_questions",
            "kind": "form",
            "prompt": "A few details every manufacturer needs:",
            "questions": [q.model_dump() for q in questions],
            "values": spec.answers,
            "errors": errors,
        },
    }


async def deep_dive(state: OrderState, consultant: Consultant) -> dict:
    """The AI asks follow-up questions and records answers until it has nothing left to ask."""
    spec = _spec(state)
    messages = list(state.get("messages", []))
    reply = state.get("reply")
    if reply is not None:
        text = str(_reply_value(reply, "message") or "").strip()
        if text:
            messages.append({"role": "customer", "content": text})

    ctx = _context(state, spec, messages)
    turn = await consultant.deep_dive(ctx)
    apply_updates(spec, ctx.questions, turn.updates)

    message = turn.message.strip()
    # Guard against a loop with no customer in it: right after the completeness check found gaps,
    # the AI must ask the customer something rather than declaring itself done again.
    ready = turn.ready_for_review and not (reply is None and spec.open_gaps)
    if not ready and (turn.ready_for_review or not message):
        gaps = spec.open_gaps or ["Anything else the manufacturer should know?"]
        message = "Just a few more details the manufacturer will need:\n" + "\n".join(f"- {g}" for g in gaps)
    if message:
        messages.append({"role": "orion", "content": message})

    update = {"spec": spec.model_dump(), "messages": messages, "reply": None, "pending": None}
    if not ready:
        update["pending"] = {"step": "deep_dive", "kind": "chat", "message": message}
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
    text = render_pre_receipt(spec, market, get_questions(market.id, spec.option))
    return {"pre_receipt": text, "stage": "pre_receipt_review"}


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
            "pre_receipt": state["pre_receipt"],
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
