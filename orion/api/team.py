"""Team routes (console): orders needing a human, outbox, pasted manufacturer replies, manufacturers, members."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from orion.api.context import ApiContext, ctx, team_member
from orion.api.security import TokenClaims
from orion.api.views import team_order_view
from orion.db.stores import Manufacturer
from orion.graph.graph import OrderNotWaiting, get_order, waiting_on
from orion.runtime import manual_event_id, send_event

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
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty message")
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
    await c.deps.directory.add(Manufacturer(id=body.id, name=body.name, contact=body.contact))
    await c.deps.directory.assign(body.id, body.market, body.option, body.rank)
    return body.model_dump()


@router.get("/members")
async def members(c: ApiContext = Depends(ctx), _: TokenClaims = Depends(admin)) -> list[dict]:
    return await c.accounts.list_team_members()


@router.post("/members", status_code=status.HTTP_201_CREATED)
async def add_member(body: NewMember, c: ApiContext = Depends(ctx), _: TokenClaims = Depends(admin)) -> dict:
    return await c.accounts.add_team_member(body.email, body.name, body.role)
