"""Customer order routes. A customer only ever sees their own orders, through customer_order_view."""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from orion.api.context import ApiContext, ctx, current_customer
from orion.api.security import TokenClaims
from orion.api.views import customer_order_view
from orion.config.markets import MARKETS, get_questions
from orion.spec import Section
from orion.tools.assist import safe_answer
from orion.graph.graph import OrderNotWaiting, get_order, waiting_on
from orion.runtime import send_customer_reply, start_customer_order

router = APIRouter(prefix="/orders", tags=["orders"])


class Reply(BaseModel):
    """The customer's answer to the current prompt:
    choice -> {"choice": "hoodie"}, form -> {"answers": {...}}, chat -> {"message": "..."},
    confirm -> {"confirm": true} or {"confirm": false, "changes": "..."}"""

    reply: dict[str, Any]


async def _owned(c: ApiContext, order_id: str, claims: TokenClaims) -> None:
    row = await c.accounts.order(order_id)
    if row is None or str(row["customer_id"]) != claims.sub:
        # Same answer for "missing" and "not yours"
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")


async def _view(c: ApiContext, order_id: str) -> dict:
    return customer_order_view(await get_order(c.graph, order_id), await waiting_on(c.graph, order_id))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    await c.accounts.create_order(order_id, claims.sub)
    await start_customer_order(c.graph, c.pool, order_id)
    return await _view(c, order_id)


@router.get("")
async def list_orders(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> list[dict]:
    return await c.accounts.customer_orders(claims.sub)


@router.get("/{order_id}")
async def get_customer_order(
    order_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    await _owned(c, order_id, claims)
    return await _view(c, order_id)


class AssistRequest(BaseModel):
    section: Section
    question: str = Field("", max_length=1000)     # empty = "explain this section"
    answers: dict[str, Any] = {}                    # what the customer has filled in so far (not saved)
    lang: Literal["en", "ar"] = "ar"


@router.post("/{order_id}/assist")
async def assist(
    order_id: str, body: AssistRequest, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    """'Ask Orion' about one section of the details form. Advice only; the order is not changed."""
    await _owned(c, order_id, claims)
    if c.assistant is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "assistant not available")
    state = await get_order(c.graph, order_id)
    spec = state.get("spec")
    if not spec:
        raise HTTPException(status.HTTP_409_CONFLICT, "pick a product first")
    questions = [q for q in get_questions(spec["market"], spec["option"]) if q.section == body.section]
    if not questions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no questions in this section")
    if not c.assist_limit.allow(claims.sub):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many questions, try again later")

    known = {q.id for q in questions}
    answers = {k: v for k, v in body.answers.items() if k in known}
    product = MARKETS[spec["market"]].options[spec["option"]].name
    question = body.question.strip() or "Help me with this section."
    answer = await c.assistant.help(product, body.section, questions, answers, question, body.lang)
    return {"section": body.section, "answer": safe_answer(answer, body.lang)}


@router.post("/{order_id}/reply")
async def reply(
    order_id: str, body: Reply, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    await _owned(c, order_id, claims)
    try:
        await send_customer_reply(c.graph, c.pool, order_id, body.reply)
    except OrderNotWaiting:
        raise HTTPException(status.HTTP_409_CONFLICT, "this order is not waiting for your answer") from None
    return await _view(c, order_id)
