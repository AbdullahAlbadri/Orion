"""Order graph wiring. Business logic lives in nodes.py / manufacturer_nodes.py; this file only connects it.

Ordering:
select_market → pick_option → mandatory_questions → deep_dive ⇄ completeness_check
  → build_pre_receipt → customer_confirm ──(changes)──► deep_dive
  → freeze_spec
Manufacturer:
  → translate_spec → contact_manufacturer → wait_for_manufacturer ⇄ handle_manufacturer_event
                          ▲                                              │ (declined)
                          └──────────────────────────────────────────────┘

Wait nodes pause the graph with interrupt(); the value passed to Command(resume=...) is the
customer's reply or the event that resumed the order.
"""

from typing import Any, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import START, StateGraph
from langgraph.types import Command, interrupt

from orion.config.policy import POLICY_VERSION, Policy
from orion.deps import Deps
from orion.graph import manufacturer_nodes as mfr
from orion.graph import nodes
from orion.graph.state import OrderState

INTERACTIVE_STEPS = ["select_market", "pick_option", "mandatory_questions", "deep_dive", "customer_confirm"]
WAIT_MANUFACTURER = "wait_for_manufacturer"


def wait_for_customer(state: OrderState) -> dict:
    reply = interrupt(state["pending"])
    return {"reply": reply}


def wait_for_manufacturer(state: OrderState) -> dict:
    event = interrupt({"step": WAIT_MANUFACTURER, "kind": "waiting", "waiting_on": "manufacturer"})
    return {"event": event}


def build_graph(deps: Deps, checkpointer: BaseCheckpointSaver, policy: Optional[Policy] = None):
    policy = policy or Policy()

    async def deep_dive(state: OrderState) -> dict:
        return await nodes.deep_dive(state, deps.consultant)

    async def completeness_check(state: OrderState) -> dict:
        return await nodes.completeness_check(state, deps.consultant, policy)

    async def translate_spec(state: OrderState) -> dict:
        return await mfr.translate_spec(state, deps.manufacturer_agent)

    async def contact_manufacturer(state: OrderState) -> dict:
        return await mfr.contact_manufacturer(state, deps.directory, deps.channel, policy)

    async def handle_manufacturer_event(state: OrderState) -> dict:
        return await mfr.handle_manufacturer_event(state, deps.manufacturer_agent, deps.channel, deps.prices)

    g = StateGraph(OrderState)
    # Ordering
    g.add_node("select_market", nodes.select_market)
    g.add_node("pick_option", nodes.pick_option)
    g.add_node("mandatory_questions", nodes.mandatory_questions)
    g.add_node("deep_dive", deep_dive)
    g.add_node("completeness_check", completeness_check)
    g.add_node("build_pre_receipt", nodes.build_pre_receipt)
    g.add_node("customer_confirm", nodes.customer_confirm)
    g.add_node("freeze_spec", nodes.freeze_spec)
    g.add_node(nodes.WAIT, wait_for_customer)
    # Manufacturer
    g.add_node("translate_spec", translate_spec)
    g.add_node("contact_manufacturer", contact_manufacturer)
    g.add_node(WAIT_MANUFACTURER, wait_for_manufacturer)
    g.add_node("handle_manufacturer_event", handle_manufacturer_event)

    g.add_edge(START, "select_market")
    g.add_conditional_edges("select_market", nodes.wait_or("pick_option"), [nodes.WAIT, "pick_option"])
    g.add_conditional_edges("pick_option", nodes.wait_or("mandatory_questions"), [nodes.WAIT, "mandatory_questions"])
    g.add_conditional_edges("mandatory_questions", nodes.wait_or("deep_dive"), [nodes.WAIT, "deep_dive"])
    g.add_conditional_edges("deep_dive", nodes.wait_or("completeness_check"), [nodes.WAIT, "completeness_check"])
    g.add_conditional_edges(
        "completeness_check", nodes.route_after_completeness, ["deep_dive", "build_pre_receipt"]
    )
    g.add_edge("build_pre_receipt", "customer_confirm")
    g.add_conditional_edges("customer_confirm", nodes.route_after_confirm, [nodes.WAIT, "freeze_spec", "deep_dive"])
    g.add_conditional_edges(nodes.WAIT, nodes.resume_step, INTERACTIVE_STEPS)

    g.add_edge("freeze_spec", "translate_spec")
    g.add_edge("translate_spec", "contact_manufacturer")
    g.add_edge("contact_manufacturer", WAIT_MANUFACTURER)
    g.add_edge(WAIT_MANUFACTURER, "handle_manufacturer_event")
    g.add_conditional_edges(
        "handle_manufacturer_event",
        mfr.route_after_manufacturer_event,
        ["contact_manufacturer", WAIT_MANUFACTURER],
    )

    return g.compile(checkpointer=checkpointer)


# --- driving an order (the API will call these later) ---------------------------

def _config(order_id: str) -> dict:
    return {"configurable": {"thread_id": order_id}}


def _pending(result: dict) -> Optional[dict]:
    interrupts = result.get("__interrupt__")
    return interrupts[0].value if interrupts else None


async def start_order(app, order_id: str) -> Optional[dict]:
    """Start a new order thread. Returns the first prompt for the customer."""
    initial: OrderState = {
        "order_id": order_id,
        "stage": "draft",
        "policy_version": POLICY_VERSION,
        "messages": [],
        "gap_rounds": 0,
        "spec_versions": [],
        "human_tasks": [],
        "manufacturer_attempts": [],
        "processed_events": [],
        "quotes": [],
    }
    return _pending(await app.ainvoke(initial, _config(order_id)))


async def send_reply(app, order_id: str, reply: Any) -> Optional[dict]:
    """Resume the order with the customer's reply. Returns what the order is waiting on next, or None."""
    return _pending(await app.ainvoke(Command(resume=reply), _config(order_id)))


EVENT_WAITS = {"manufacturer_reply": WAIT_MANUFACTURER}


class OrderNotWaiting(Exception):
    pass


async def on_event(app, order_id: str, event: dict) -> Optional[dict]:
    """Resume the order with an outside event, e.g.
    {"type": "manufacturer_reply", "event_id": ..., "manufacturer_id": ..., "text": ...}.

    Raises OrderNotWaiting if the order is not paused at the wait point for this event type.
    """
    waiting = await waiting_on(app, order_id)
    if not waiting or waiting.get("step") != EVENT_WAITS.get(event.get("type")):
        raise OrderNotWaiting(f"order {order_id} is not waiting for {event.get('type')} (waiting on: {waiting})")
    return _pending(await app.ainvoke(Command(resume=event), _config(order_id)))


async def get_order(app, order_id: str) -> OrderState:
    return (await app.aget_state(_config(order_id))).values


async def waiting_on(app, order_id: str) -> Optional[dict]:
    """The prompt the order is currently paused on, if any."""
    snapshot = await app.aget_state(_config(order_id))
    for task in snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None
