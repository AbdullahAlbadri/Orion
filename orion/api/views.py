"""What each audience may see of an order. Customers never see manufacturer data, prices or internal flags."""

from typing import Optional

from orion.config.status_labels import status_label


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
        "summary": state.get("summary"),
        "spec": {k: spec.get(k) for k in ("market", "option", "quantity", "answers", "version", "frozen")} if spec else None,
    }


def team_order_view(state: dict, waiting: Optional[dict]) -> dict:
    """Everything, for the team console."""
    return {**state, "waiting": waiting}
