"""Customer order routes. A customer only ever sees their own orders, through customer_order_view."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field

from orion.api.context import ApiContext, ctx, current_customer
from orion.api.files import file_ids_in, file_response, store_upload
from orion.api.security import TokenClaims
from orion.api.views import customer_order_view, order_title, summary_for_version
from orion.config.markets import MARKETS, get_questions
from orion.config.stats import HOURS_PER_FACTORY, HOURS_PER_MESSAGE, HOURS_PER_SPEC
from orion.config.status_labels import UNSUBMITTED, stage_owner, status_label
from orion.db.insights import order_rows, stage_segments, summarize_orders, summarize_time
from orion.spec import Section
from orion.tools.assist import safe_answer
from orion.tools.files import MAX_FILES_PER_ORDER
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


class NewOrder(BaseModel):
    """Optional: start with a product already chosen (e.g. from a product idea on the Overview)."""
    option: Optional[str] = Field(None, max_length=60)
    description: Optional[str] = Field(None, max_length=600)   # custom products: the idea, as a starting text
    lang: Literal["en", "ar"] = "ar"


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(
    body: Optional[NewOrder] = None, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    """Start an order. Clicking "new order" again does not pile up empty drafts: an untouched draft is
    reused, and an empty draft that already has a product picked is cleared so a new product can be chosen.
    Drafts with answers are kept and a separate order is started."""
    market = next((m for m in MARKETS.values() if body and body.option in m.options), None)
    for row in await c.accounts.customer_orders(claims.sub):
        if row["stage"] != "draft":
            continue
        state = await get_order(c.graph, row["id"])
        if has_details(state):
            continue
        if not state.get("spec") and not state.get("market") and market is None:
            return await _view(c, row["id"])          # nothing chosen yet: just continue it
        await discard_order(c.graph, c.pool, row["id"])
    prefill = None
    if market is not None:
        # The customer still sees and answers every question; only the product choice is made for them
        answers = {"description": body.description.strip()} if body.option == "custom" and body.description else {}
        prefill = {"market": market.id, "option": body.option, "answers": answers, "lang": body.lang}
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    await c.accounts.create_order(order_id, claims.sub)
    await start_customer_order(
        c.graph, c.pool, order_id, business=await c.profile.business_for_ai(claims.sub), prefill=prefill
    )
    return await _view(c, order_id)


def _remap_files(answers: dict, new_ids: dict[str, str]) -> dict:
    """Point a copied order's file answers at the new order's copies; drop files that were not copied."""
    out = {}
    for qid, value in answers.items():
        if isinstance(value, list) and value and all(isinstance(v, dict) and "file_id" in v for v in value):
            value = [{**v, "file_id": new_ids[str(v["file_id"])]} for v in value if str(v["file_id"]) in new_ids]
            if not value:
                continue
        out[qid] = value
    return out


async def reorder(c: ApiContext, customer_id: str, source_order_id: str) -> dict:
    """A new order pre-filled from an earlier one. TODO(decide): which steps a reorder may skip; for now
    none: the customer reviews the form, answers any new questions and confirms a new summary."""
    source = await get_order(c.graph, source_order_id)
    spec = source.get("spec") or {}
    if not spec.get("frozen"):
        raise HTTPException(status.HTTP_409_CONFLICT, "only confirmed orders can be reordered")
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    await c.accounts.create_order(order_id, customer_id, reorder_of=source_order_id)
    new_ids = await c.accounts.copy_files(source_order_id, order_id, customer_id)
    prefill = {
        "market": source.get("market"),
        "option": spec.get("option"),
        "answers": _remap_files(spec.get("answers") or {}, new_ids),
        "labels": spec.get("labels") or {},
        "sections": spec.get("sections") or {},
        "lang": source.get("lang"),
    }
    await start_customer_order(
        c.graph, c.pool, order_id, business=await c.profile.business_for_ai(customer_id), prefill=prefill
    )
    return await _view(c, order_id)


@router.get("")
async def list_orders(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> list[dict]:
    """The customer's orders; drafts only count once something has been filled in."""
    rows = await c.accounts.customer_orders(claims.sub)
    out = []
    for row in rows:
        state = None
        if row["stage"] == "draft" or row["option"] == "custom":
            state = await get_order(c.graph, row["id"])
            if row["stage"] == "draft" and not has_details(state):
                continue
        out.append({
            **row,
            "title": order_title(state) if state else None,     # custom products: the customer's own words
            "status": status_label(row["stage"]),
            "waiting_on": stage_owner(row["stage"]),
        })
    return out


RANGES = {"month": timedelta(days=31), "quarter": timedelta(days=92), "year": timedelta(days=366)}


@router.get("/stats")
async def stats(
    range: Literal["month", "quarter", "year", "all"] = "all",
    c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer),
) -> dict:
    """What Orion has done for this customer. Counts are real; time saved is an estimate (see config/stats.py).
    `orders`, `time` and `order_list` follow the date range (orders created in it); the rest is all-time."""
    since = datetime.now(timezone.utc) - RANGES[range] if range in RANGES else None
    rows = await order_rows(c.pool, claims.sub, since)
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
        "spend": None,         # TODO(decide): payment provider; spend, cost breakdown, landed cost come from payments
        "range": range,
        "orders": summarize_orders(rows),
        "time": summarize_time(await stage_segments(c.pool, claims.sub, since)),
        "order_list": [
            {"id": r["id"], "option": r["option"], "market": r["market"], "stage": r["stage"],
             "status": status_label(r["stage"]), "quantity": r["quantity"], "revisions": r["revisions"],
             "mismatches_caught": r["mismatches_caught"], "created_at": r["created_at"]}
            for r in rows if r["stage"] not in UNSUBMITTED
        ],
    }


@router.get("/documents")
async def documents(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> list[dict]:
    """Every pre-receipt version and uploaded file across the customer's orders. Orion-made documents
    (quotes, invoices, shipping and customs paperwork) join this list as those stages are built."""
    rows = await c.accounts.customer_orders(claims.sub)
    docs: list[dict] = []
    for row in rows:
        if row["stage"] not in UNSUBMITTED or row["stage"] == "pre_receipt_review":
            state = await get_order(c.graph, row["id"])
            title = order_title(state)
            versions = state.get("spec_versions") or []
            for i, _ in enumerate(versions, start=1):
                docs.append({"kind": "pre_receipt", "order_id": row["id"], "option": row["option"], "title": title,
                             "version": i, "status": "confirmed", "created_at": row["created_at"]})
            if row["stage"] == "pre_receipt_review":
                docs.append({"kind": "pre_receipt", "order_id": row["id"], "option": row["option"], "title": title,
                             "version": None, "status": "needs_review", "created_at": row["updated_at"]})
    by_order = {r["id"]: r for r in rows}
    for f in await c.accounts.order_files(list(by_order)):
        docs.append({"kind": "upload", "order_id": f["order_id"], "option": by_order[f["order_id"]]["option"],
                     "file_id": f["id"], "name": f["name"], "content_type": f["content_type"], "size": f["size"],
                     "created_at": f["created_at"]})
    return docs


@router.get("/{order_id}")
async def get_customer_order(
    order_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    await _owned(c, order_id, claims)
    return await _view(c, order_id)


@router.get("/{order_id}/receipt")
async def receipt(
    order_id: str, version: Optional[int] = None, lang: Literal["ar", "en"] = "ar",
    c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer),
) -> dict:
    """A pre-receipt: a confirmed version (1, 2, ...) or, without `version`, the current one."""
    await _owned(c, order_id, claims)
    summary = summary_for_version(await get_order(c.graph, order_id), version, lang)
    if summary is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no pre-receipt for this version")
    return summary


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


@router.post("/{order_id}/files/from-profile/{logo_id}", status_code=status.HTTP_201_CREATED)
async def use_saved_logo(
    order_id: str, logo_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    """Add a logo saved on the business profile to this order. The order gets its own file row (same stored
    bytes), so removing the logo from the profile later doesn't touch the order."""
    await _owned(c, order_id, claims)
    logo = await c.profile.brand_logo(claims.sub, logo_id)
    if logo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "logo not found")
    if await c.accounts.count_files(order_id) >= MAX_FILES_PER_ORDER:
        raise HTTPException(status.HTTP_409_CONFLICT, f"at most {MAX_FILES_PER_ORDER} files per order")
    row = await c.accounts.add_file(order_id, claims.sub, logo["name"], logo["content_type"], logo["size"],
                                    logo["storage_key"])
    return {"file_id": str(row["id"]), "name": row["name"], "content_type": row["content_type"], "size": row["size"]}


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
