"""Team routes (console): orders needing a human, outbox, pasted manufacturer replies, manufacturers, members,
and customer help requests."""

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, EmailStr, Field

from orion.api.context import ApiContext, ctx, team_member
from orion.api.files import file_response
from orion.api.security import TokenClaims
from orion.api.views import team_order_view
from orion.config.policy import Policy
from orion.config.pricing import PRICING
from orion.db.stores import Manufacturer
from orion.graph.graph import OrderNotWaiting, get_order, waiting_on
from orion.runtime import manual_event_id, resolve_human_tasks, send_event
from orion.tools.customer_quote import build_customer_quote
from orion.tools.mail import is_email

router = APIRouter(prefix="/team", tags=["team"])
agent = team_member("agent")
admin = team_member("admin")


class ManufacturerReply(BaseModel):
    manufacturer_id: str
    text: str


class NewManufacturer(BaseModel):
    id: str
    name: str
    contact: Optional[str] = None
    channel: Literal["manual_relay", "email"] = "manual_relay"   # email: contact must be an email address
    market: str
    option: Optional[str] = None     # None = every option in the market
    rank: int = 1


class NewMember(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: Literal["admin", "agent"] = "agent"


@router.get("/orders")
async def orders(
    needs_human: Optional[bool] = None, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent)
) -> list[dict]:
    return await c.accounts.team_orders(needs_human)


@router.get("/orders/{order_id}")
async def order(order_id: str, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent)) -> dict:
    state = await get_order(c.graph, order_id)
    if not state:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    return team_order_view(state, await waiting_on(c.graph, order_id))


@router.post("/orders/{order_id}/manufacturer-replies")
async def manufacturer_reply(
    order_id: str, body: ManufacturerReply, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent)
) -> dict:
    text = body.text.strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "empty message")
    event = {
        "type": "manufacturer_reply",
        # Pasting the same text twice is processed once
        "event_id": manual_event_id(order_id, body.manufacturer_id, text),
        "manufacturer_id": body.manufacturer_id,
        "text": text,
    }
    try:
        await send_event(c.graph, c.pool, order_id, event)
    except OrderNotWaiting as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None
    return team_order_view(await get_order(c.graph, order_id), await waiting_on(c.graph, order_id))


class SendQuote(BaseModel):
    send_anyway: bool = False     # send although the calculation raised warnings (the team checked them)


@router.get("/orders/{order_id}/quote-preview")
async def quote_preview(order_id: str, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent)) -> dict:
    """The customer quote as it would be sent now, with how it was calculated and any problems. Changes nothing."""
    state = await get_order(c.graph, order_id)
    if not state:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    return build_customer_quote(state.get("quotes", []), state.get("spec") or {}, PRICING,
                                Policy().quote_validity_days, datetime.now(timezone.utc))


@router.post("/orders/{order_id}/send-quote")
async def send_quote(
    order_id: str, body: SendQuote, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(agent)
) -> dict:
    """Calculate the quote again (in the graph, from the recorded prices) and show it to the customer."""
    event = {"type": "send_quote", "event_id": f"send_quote:{uuid.uuid4().hex}", "send_anyway": body.send_anyway,
             "sent_by": claims.email}
    try:
        await send_event(c.graph, c.pool, order_id, event)
    except OrderNotWaiting as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None
    state = await get_order(c.graph, order_id)
    if state.get("stage") != "quote_review":
        raise HTTPException(status.HTTP_409_CONFLICT, state.get("needs_human") or "quote not sent")
    return team_order_view(state, await waiting_on(c.graph, order_id))


@router.post("/orders/{order_id}/resolve")
async def resolve(order_id: str, c: ApiContext = Depends(ctx), member: TokenClaims = Depends(agent)) -> dict:
    """The team handled everything flagged on this order."""
    try:
        state = await resolve_human_tasks(c.graph, c.pool, order_id, member.email)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found") from None
    return team_order_view(state, await waiting_on(c.graph, order_id))


@router.get("/orders/{order_id}/files/{file_id}")
async def order_file(order_id: str, file_id: str, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent)) -> Response:
    """Download a customer's uploaded file (e.g. to send the logo to the factory)."""
    return await file_response(c, order_id, file_id)


@router.get("/outbox")
async def outbox(c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent)) -> list[dict]:
    return await c.deps.channel.pending()


@router.post("/outbox/{message_id}/sent")
async def mark_sent(message_id: str, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent)) -> dict:
    if not await c.deps.channel.mark_sent(message_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no pending message with that id")
    return {"id": message_id, "status": "sent"}


@router.get("/manufacturers")
async def manufacturers(c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent)) -> list[dict]:
    return await c.deps.directory.all()


@router.post("/manufacturers", status_code=status.HTTP_201_CREATED)
async def add_manufacturer(body: NewManufacturer, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(admin)) -> dict:
    if body.channel == "email" and not is_email(body.contact):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "an email manufacturer needs an email address")
    await c.deps.directory.add(Manufacturer(id=body.id, name=body.name, contact=body.contact, channel=body.channel))
    await c.deps.directory.assign(body.id, body.market, body.option, body.rank)
    return body.model_dump()


@router.get("/members")
async def members(c: ApiContext = Depends(ctx), _: TokenClaims = Depends(admin)) -> list[dict]:
    return await c.accounts.list_team_members()


@router.post("/members", status_code=status.HTTP_201_CREATED)
async def add_member(body: NewMember, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(admin)) -> dict:
    return await c.accounts.add_team_member(body.email, body.name, body.role)


# --- help requests from customers ----------------------------------------------------

class SupportReply(BaseModel):
    body: str = Field("", max_length=4000)      # empty = only change the status
    status: Literal["open", "waiting_customer", "resolved"] = "waiting_customer"


@router.get("/support")
async def support_requests(
    status_filter: Optional[Literal["open", "waiting_customer", "resolved"]] = Query(None, alias="status"),
    c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent),
) -> list[dict]:
    return await c.inbox.team_requests(status_filter)


@router.get("/support/{request_id}")
async def support_request(request_id: str, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(agent)) -> dict:
    row = await c.inbox.request(None, request_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    return row


@router.post("/support/{request_id}/reply")
async def reply_support(
    request_id: str, body: SupportReply, c: ApiContext = Depends(ctx), member: TokenClaims = Depends(agent)
) -> dict:
    """Answer a customer. The reply also shows in their Messages. Never promise a price or a change here
    that the team has not agreed (rule 1)."""
    row = await c.inbox.team_reply(request_id, member.email, body.body.strip(), body.status)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    return row
