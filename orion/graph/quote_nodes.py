"""Customer quote nodes. Plain functions: state in, partial state update out. No LangGraph imports.

After a factory quotes, the order waits (at wait_for_manufacturer) for more replies or for the team:
send_quote event → send_customer_quote → (customer) quote_review → accepted: wait_for_payment
                                                                 → declined: back to the team
"""

from datetime import datetime, timezone

from orion.config.policy import Policy
from orion.config.pricing import Pricing
from orion.graph.state import OrderState
from orion.tools.customer_quote import build_customer_quote

QUOTE_PROMPT = {"en": "Your quote is ready", "ar": "عرض السعر جاهز"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _task(state: OrderState, reason: str) -> dict:
    tasks = list(state.get("human_tasks", [])) + [{"reason": reason, "at": _now().isoformat()}]
    return {"human_tasks": tasks, "needs_human": reason}


def send_customer_quote(state: OrderState, policy: Policy, pricing: Pricing) -> dict:
    """The team asked to send the quote. It is calculated here, in code, from the recorded prices; the team
    never types a price. Warnings stop it unless the team chose to send anyway."""
    event = state.get("event") or {}
    if not event.get("event_id") or event["event_id"] in state.get("processed_events", []):
        return {"event": None}
    update: dict = {"event": None, "processed_events": list(state.get("processed_events", [])) + [event["event_id"]]}
    result = build_customer_quote(state.get("quotes", []), state.get("spec") or {}, pricing,
                                  policy.quote_validity_days, _now())
    if result["blocking"] or (result["warnings"] and not event.get("send_anyway")):
        problems = result["blocking"] + result["warnings"]
        return {**update, **_task(state, "Quote not sent to the customer: " + "; ".join(problems))}
    lang = state.get("lang", "en")
    return {
        **update,
        "stage": "quote_review",
        "customer_quote": {**result, "sent_at": _now().isoformat(), "sent_by": event.get("sent_by"),
                           "warnings_accepted": result["warnings"]},
        "pending": {"step": "quote_review", "kind": "quote", "prompt": QUOTE_PROMPT["en"],
                    "prompt_ar": QUOTE_PROMPT["ar"], "quote": result["quote"], "error": None, "lang": lang},
    }


def quote_review(state: OrderState) -> dict:
    """The customer accepts ({"accept": true}) or declines ({"accept": false, "reason": "..."}) the quote."""
    pending, reply = state["pending"], state.get("reply")
    if not isinstance(reply, dict) or not isinstance(reply.get("accept"), bool):
        return {"reply": None, "pending": {**pending, "error": "Accept or decline the quote."}}
    quote = dict(state["customer_quote"])
    if reply["accept"]:
        if datetime.fromisoformat(quote["quote"]["valid_until"]) < _now():
            # Prices may have changed: the team sends a fresh quote
            quote["expired_at"] = _now().isoformat()
            return {"reply": None, "pending": None, "stage": "quote_received", "customer_quote": quote,
                    **_task(state, "The customer tried to accept an expired quote: send a new one")}
        quote["accepted_at"] = _now().isoformat()
        return {"reply": None, "pending": None, "stage": "awaiting_payment", "customer_quote": quote,
                # TODO(decide): payment provider; until then the team sends the payment link
                **_task(state, "The customer accepted the quote: send the payment link")}
    reason = str(reply.get("reason") or "").strip()[:500]
    quote.update(declined_at=_now().isoformat(), decline_reason=reason)
    return {"reply": None, "pending": None, "stage": "quote_received", "customer_quote": quote,
            **_task(state, "The customer declined the quote" + (f": {reason}" if reason else ""))}


def route_after_send(state: OrderState) -> str:
    return "quote_review" if state.get("stage") == "quote_review" and state.get("pending") else "back"


def route_after_review(state: OrderState) -> str:
    if state.get("pending"):
        return "ask_again"
    return "paid_next" if state.get("stage") == "awaiting_payment" else "back"
