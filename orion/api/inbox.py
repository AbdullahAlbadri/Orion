"""Messages (notifications) and Help requests for the signed-in customer.

Help requests go to people in the team console. No model answers them, so a price or change question is
never discussed by the AI: the customer is told the team will review it (rule 1).
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from orion.api.context import ApiContext, ctx, current_customer
from orion.api.security import TokenClaims
from orion.config.status_labels import status_label
from orion.graph.graph import get_order

router = APIRouter(tags=["inbox"])

Topic = Literal["order", "change", "price", "delivery", "account", "other"]


@router.get("/notifications")
async def notifications(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    return {
        "items": await c.inbox.notifications(claims.sub),
        "unread": await c.inbox.unread_count(claims.sub),
    }


class MarkRead(BaseModel):
    ids: Optional[list[str]] = Field(None, max_length=200)   # None = mark all as read


@router.post("/notifications/read")
async def mark_read(body: MarkRead, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    await c.inbox.mark_read(claims.sub, body.ids)
    return {"unread": await c.inbox.unread_count(claims.sub)}


class NewRequest(BaseModel):
    topic: Topic
    order_id: Optional[str] = None
    body: str = Field(min_length=1, max_length=4000)


class RequestReply(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


@router.get("/support")
async def my_requests(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> list[dict]:
    return await c.inbox.requests(claims.sub)


@router.post("/support", status_code=status.HTTP_201_CREATED)
async def open_request(
    body: NewRequest, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    """Open a help request. The order's stage and spec version are attached so the team need not ask."""
    if not c.support_limit.allow(claims.sub):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many requests, try again later")
    context: dict = {}
    if body.order_id:
        row = await c.accounts.order(body.order_id)
        if row is None or str(row["customer_id"]) != claims.sub:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
        state = await get_order(c.graph, body.order_id)
        spec = state.get("spec") or {}
        context = {
            "stage": state.get("stage"),
            "status": status_label(state.get("stage", ""))["en"],
            "option": spec.get("option"),
            "spec_version": spec.get("version"),
            "frozen": bool(spec.get("frozen")),
        }
    return await c.inbox.open_request(claims.sub, body.topic, body.body.strip(), body.order_id, context)


@router.get("/support/{request_id}")
async def get_request(request_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    row = await c.inbox.request(claims.sub, request_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    return row


@router.post("/support/{request_id}/messages")
async def reply_to_request(
    request_id: str, body: RequestReply, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    if not c.support_limit.allow(claims.sub):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many messages, try again later")
    row = await c.inbox.customer_reply(claims.sub, request_id, body.body.strip())
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    return row
