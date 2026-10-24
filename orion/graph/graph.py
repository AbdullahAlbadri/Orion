"""Ordering graph wiring. Business logic lives in nodes.py; this file only connects it.

select_market → pick_option → mandatory_questions → deep_dive ⇄ completeness_check
  → build_pre_receipt → customer_confirm ──(changes)──► deep_dive
  → freeze_spec → END

Every interactive node routes to `wait_for_customer`, which pauses the graph with interrupt()
and routes the reply back to the node that asked.
"""

from typing import Any, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from orion.config.policy import POLICY_VERSION, Policy
from orion.graph import nodes
from orion.graph.state import OrderState
from orion.tools.llm import Consultant

INTERACTIVE_STEPS = ["select_market", "pick_option", "mandatory_questions", "deep_dive", "customer_confirm"]


def wait_for_customer(state: OrderState) -> dict:
    # Pauses here; the value passed to Command(resume=...) becomes `reply`.
    reply = interrupt(state["pending"])
    return {"reply": reply}


def build_graph(consultant: Consultant, checkpointer: BaseCheckpointSaver, policy: Optional[Policy] = None):
    policy = policy or Policy()

    async def deep_dive(state: OrderState) -> dict:
        return await nodes.deep_dive(state, consultant)

    async def completeness_check(state: OrderState) -> dict:
        return await nodes.completeness_check(state, consultant, policy)

    g = StateGraph(OrderState)
    g.add_node("select_market", nodes.select_market)
    g.add_node("pick_option", nodes.pick_option)
    g.add_node("mandatory_questions", nodes.mandatory_questions)
    g.add_node("deep_dive", deep_dive)
    g.add_node("completeness_check", completeness_check)
    g.add_node("build_pre_receipt", nodes.build_pre_receipt)
    g.add_node("customer_confirm", nodes.customer_confirm)
    g.add_node("freeze_spec", nodes.freeze_spec)
    g.add_node(nodes.WAIT, wait_for_customer)

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
    g.add_edge("freeze_spec", END)
    g.add_conditional_edges(nodes.WAIT, nodes.resume_step, INTERACTIVE_STEPS)

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
    }
    return _pending(await app.ainvoke(initial, _config(order_id)))


async def send_reply(app, order_id: str, reply: Any) -> Optional[dict]:
    """Resume the order with the customer's reply. Returns the next prompt, or None when the graph finished."""
    return _pending(await app.ainvoke(Command(resume=reply), _config(order_id)))


async def get_order(app, order_id: str) -> OrderState:
    return (await app.aget_state(_config(order_id))).values
