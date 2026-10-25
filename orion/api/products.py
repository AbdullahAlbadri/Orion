"""My Products: what the customer has made before, its order history, and reorder.

Which factory made a product is not shown (TODO(decide): whether customers may see it).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from orion.api.context import ApiContext, ctx, current_customer
from orion.api.orders import reorder
from orion.api.security import TokenClaims
from orion.api.views import order_title, summary_for_version
from orion.config.status_labels import status_label
from orion.graph.graph import get_order
from orion.spec import is_file_list

router = APIRouter(prefix="/products", tags=["products"])


class ProductUpdate(BaseModel):
    notes: Optional[str] = Field(None, max_length=2000)
    archived: Optional[bool] = None


async def _card(c: ApiContext, row: dict) -> dict:
    """List entry, with the customer's name for a custom product and its first reference picture."""
    state = await get_order(c.graph, row["id"])
    answers = (state.get("spec") or {}).get("answers") or {}
    picture = next(
        ({"order_id": row["id"], "file_id": f["file_id"]}
         for v in answers.values() if is_file_list(v) for f in v
         if str(f.get("content_type", "")).startswith("image/")),
        None,
    )
    return {**row, "title": order_title(state), "picture": picture, "status": status_label(row["latest_stage"])}


@router.get("")
async def products(
    archived: bool = False, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> list[dict]:
    return [await _card(c, row) for row in await c.products.products(claims.sub, archived)]


@router.get("/{product_id}")
async def product(
    product_id: str, lang: str = "ar", c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    row = await c.products.product(claims.sub, product_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    latest = await get_order(c.graph, row["latest_order_id"])
    history = [{**h, "status": status_label(h["stage"])} for h in row.pop("history")]
    files = await c.accounts.order_files([h["id"] for h in history])
    return {
        **await _card(c, row),
        # The latest confirmed specification is what a reorder starts from
        "summary": summary_for_version(latest, len(latest.get("spec_versions") or []) or None, "ar" if lang == "ar" else "en"),
        "history": history,
        "files": files,
    }


@router.put("/{product_id}")
async def update_product(
    product_id: str, body: ProductUpdate, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    if not await c.products.update(claims.sub, product_id, body.notes, body.archived):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    return {"ok": True}


@router.post("/{product_id}/reorder", status_code=status.HTTP_201_CREATED)
async def reorder_product(
    product_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    """Start a new order from the product's latest confirmed order. Returns the new order."""
    row = await c.products.product(claims.sub, product_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    source = next((h["id"] for h in row["history"] if h["stage"] not in ("draft", "pre_receipt_review")), None)
    if source is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "nothing to reorder yet")
    return await reorder(c, claims.sub, source)
