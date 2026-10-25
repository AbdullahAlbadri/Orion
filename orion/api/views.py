"""What each audience may see of an order. Customers never see manufacturer data, prices or internal flags."""

from typing import Optional

from orion.config.markets import MARKETS, get_questions
from orion.config.status_labels import status_label
from orion.graph.pre_receipt import build_summary
from orion.spec import ProductSpec


def _summary(state: dict) -> Optional[dict]:
    """The structured receipt; built from the spec for orders confirmed before receipts were stored."""
    if state.get("summary"):
        return state["summary"]
    spec, market_id = state.get("spec"), state.get("market")
    if not spec or not spec.get("option") or market_id not in MARKETS or not state.get("pre_receipt"):
        return None
    product = ProductSpec.model_validate(spec)
    return build_summary(product, MARKETS[market_id], get_questions(market_id, product.option), state.get("lang", "en"))


def summary_for_version(state: dict, version: Optional[int], lang: str) -> Optional[dict]:
    """The receipt of a confirmed spec version (1-based), rebuilt from that frozen spec, or the current one."""
    if version is None:
        return _summary(state)
    versions = state.get("spec_versions") or []
    market_id = state.get("market")
    if not 1 <= version <= len(versions) or market_id not in MARKETS:
        return None
    product = ProductSpec.model_validate(versions[version - 1])
    return build_summary(product, MARKETS[market_id], get_questions(market_id, product.option), lang)


def _field_label(state: dict, field_id: str) -> dict:
    """A spec detail's name in both languages: the form question, or the wording the AI used."""
    spec = state.get("spec") or {}
    if spec.get("option") and state.get("market") in MARKETS:
        for q in get_questions(state["market"], spec["option"]):
            if q.id == field_id:
                return {"en": q.prompt, "ar": q.prompt_ar or q.prompt}
    text = (spec.get("labels") or {}).get(field_id) or field_id.replace("_", " ")
    return {"en": text, "ar": text}


def order_title(state: dict, limit: int = 60) -> Optional[str]:
    """A custom product's name for lists: the start of the customer's own description."""
    answers = (state.get("spec") or {}).get("answers") or {}
    text = " ".join(str(answers.get("description") or "").split())
    if not text:
        return None
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def customer_order_view(state: dict, waiting: Optional[dict]) -> dict:
    spec = state.get("spec") or {}
    waiting_on = None
    if waiting:
        waiting_on = "manufacturer" if waiting.get("waiting_on") == "manufacturer" else "customer"
    return {
        "order_id": state.get("order_id"),
        "stage": state.get("stage"),
        "status": status_label(state.get("stage", "")),
        "waiting_on": waiting_on,
        # The prompt to render (choice / form / chat / confirm), only when it is the customer's turn
        "prompt": waiting if waiting_on == "customer" else None,
        "messages": state.get("messages", []),
        "pre_receipt": state.get("pre_receipt"),
        "summary": _summary(state),
        "spec": {k: spec.get(k) for k in ("market", "option", "quantity", "answers", "version", "frozen")} if spec else None,
        "title": order_title(state),
        "versions": len(state.get("spec_versions") or []),
        # Differences a factory reply had from the confirmed summary: which detail, and whether the team
        # has dealt with it. What the factory said stays internal.
        "checks": [
            {"field_id": t.get("field_id"), "label": _field_label(state, t.get("field_id") or ""),
             "resolved": bool(t.get("resolved_at")), "at": t.get("at")}
            for t in state.get("human_tasks", []) if t.get("kind") == "mismatch"
        ],
    }


def team_order_view(state: dict, waiting: Optional[dict]) -> dict:
    """Everything, for the team console."""
    return {**state, "waiting": waiting}
