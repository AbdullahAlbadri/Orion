"""Customer order routes. A customer only ever sees their own orders, through customer_order_view."""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field

from orion.api.context import ApiContext, ctx, current_customer
from orion.api.files import file_ids_in, file_response, store_upload
from orion.api.security import TokenClaims
from orion.api.views import customer_order_view
from orion.config.markets import MARKETS, get_questions
from orion.config.stats import HOURS_PER_FACTORY, HOURS_PER_MESSAGE, HOURS_PER_SPEC
from orion.spec import Section
from orion.tools.assist import safe_answer
from orion.graph.graph import OrderNotWaiting, get_order, waiting_on
from orion.runtime import discard_order, send_customer_reply, start_customer_order

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


def has_details(state: dict) -> bool:
    """An order counts once the customer has submitted at least one answer."""
    return bool((state.get("spec") or {}).get("answers"))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    """Start an order. Clicking "new order" again does not pile up empty drafts: an untouched draft is
    reused, and an empty draft that already has a product picked is cleared so a new product can be chosen.
    Drafts with answers are kept and a separate order is started."""
    for row in await c.accounts.customer_orders(claims.sub):
        if row["stage"] != "draft":
            continue
        state = await get_order(c.graph, row["id"])
        if has_details(state):
            continue
        if not state.get("spec") and not state.get("market"):
            return await _view(c, row["id"])          # nothing chosen yet: just continue it
        await discard_order(c.graph, c.pool, row["id"])
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    await c.accounts.create_order(order_id, claims.sub)
    await start_customer_order(c.graph, c.pool, order_id)
    return await _view(c, order_id)


@router.get("")
async def list_orders(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> list[dict]:
    """The customer's orders; drafts only count once something has been filled in."""
    rows = await c.accounts.customer_orders(claims.sub)
    out = []
    for row in rows:
        if row["stage"] == "draft" and not has_details(await get_order(c.graph, row["id"])):
            continue
        out.append(row)
    return out


@router.get("/stats")
async def stats(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    """What Orion has done for this customer. Counts are real; time saved is an estimate (see config/stats.py)."""
    a = await c.accounts.customer_activity(claims.sub)
    specs = a["submitted"]
    hours = specs * HOURS_PER_SPEC + a["factories"] * HOURS_PER_FACTORY + a["messages"] * HOURS_PER_MESSAGE
    return {
        "orders_submitted": specs,
        "orders_delivered": a["delivered"],
        "pieces_ordered": int(a["pieces"]),
        "factories_contacted": a["factories"],
        "messages_handled": a["messages"],
        "orders_quoted": a["quoted_orders"],
        "hours_to_first_quote": round(float(a["hours_to_first_quote"]), 1) if a["hours_to_first_quote"] else None,
        "time_saved_hours": round(hours, 1),
        "time_saved_basis": {"per_spec": HOURS_PER_SPEC, "per_factory": HOURS_PER_FACTORY, "per_message": HOURS_PER_MESSAGE},
        "money_saved": None,   # TODO(decide): needs priced orders and a baseline (config/stats.py)
    }


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


@router.post("/{order_id}/discard")
async def discard(order_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    """Drop a draft that was never submitted (before the summary is confirmed)."""
    await _owned(c, order_id, claims)
    if not await discard_order(c.graph, c.pool, order_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "this order was already submitted and can't be discarded")
    return {"order_id": order_id, "stage": "cancelled"}


@router.post("/{order_id}/files", status_code=status.HTTP_201_CREATED)
async def upload_file(
    order_id: str, file: UploadFile, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    """Upload a logo/artwork file. Returns {file_id, name, content_type, size} to put in the answer."""
    await _owned(c, order_id, claims)
    return await store_upload(c, order_id, claims.sub, file)


@router.get("/{order_id}/files/{file_id}")
async def get_file(
    order_id: str, file_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> Response:
    await _owned(c, order_id, claims)
    return await file_response(c, order_id, file_id)


@router.post("/{order_id}/reply")
async def reply(
    order_id: str, body: Reply, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    await _owned(c, order_id, claims)
    answers = body.reply.get("answers")
    if isinstance(answers, dict) and (referenced := file_ids_in(answers)):
        # Only files uploaded to this order can be part of its answers
        if not referenced <= await c.accounts.file_ids(order_id):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unknown file in answers")
    try:
        await send_customer_reply(c.graph, c.pool, order_id, body.reply)
    except OrderNotWaiting:
        raise HTTPException(status.HTTP_409_CONFLICT, "this order is not waiting for your answer") from None
    return await _view(c, order_id)
