"""The signed-in customer's own account: settings, business profile, addresses, sessions, data export.

Addresses and customs details are never changed by the AI; only these routes (the customer) change them.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, field_validator

from orion.api.auth import cookie_name
from orion.api.context import ApiContext, ctx, current_customer
from orion.api.files import read_upload, serve_file
from orion.api.security import TokenClaims
from orion.config.status_labels import CLOSED, UNSUBMITTED
from orion.graph.graph import get_order
from orion.tools.files import ALLOWED
from orion.tools.suggest import catalogue, clean, fingerprint

log = logging.getLogger("orion.api.me")
router = APIRouter(tags=["account"])

PHONE = r"^\+?[0-9][0-9 \-]{6,18}$"
NOTIFY_EVENTS = ("quote_ready", "payment_received", "sample_update", "shipped", "delivered", "delay", "problem")
NOTIFY_CHANNELS = ("email", "in_app")
BUSINESS_TYPES = ("online_store", "shop", "food", "brand", "company", "other")
STORE_PLATFORMS = ("salla", "zid", "shopify", "instagram", "other", "none")
MAX_BRAND_LOGOS = 5


# --- account settings --------------------------------------------------------------

class SettingsUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=PHONE)
    lang: Optional[Literal["ar", "en"]] = None
    calendar: Optional[Literal["gregorian", "hijri", "both"]] = None
    currency: Optional[Literal["SAR", "USD"]] = None      # TODO(decide): currencies shown to customers
    notify: Optional[dict[str, dict[str, bool]]] = None   # event -> channel -> on/off

    @field_validator("notify")
    @classmethod
    def known_events(cls, v):
        if v is None:
            return v
        if not set(v) <= set(NOTIFY_EVENTS) or any(not set(ch) <= set(NOTIFY_CHANNELS) for ch in v.values()):
            raise ValueError("unknown notification event or channel")
        return v


def _settings_view(row: dict) -> dict:
    notify = {e: {ch: (row["notify"] or {}).get(e, {}).get(ch, True) for ch in NOTIFY_CHANNELS} for e in NOTIFY_EVENTS}
    return {**row, "notify": notify, "onboarded": row["onboarded_at"] is not None}


@router.get("/me")
async def get_me(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    row = await c.profile.settings(claims.sub)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "account not found")
    return _settings_view(row)


@router.put("/me")
async def update_me(
    body: SettingsUpdate, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    fields = body.model_dump(exclude_unset=True)
    if "notify" in fields:
        current = (await c.profile.settings(claims.sub))["notify"] or {}
        fields["notify"] = {**current, **{e: {**current.get(e, {}), **ch} for e, ch in fields["notify"].items()}}
    return _settings_view(await c.profile.update_settings(claims.sub, fields))


@router.post("/me/onboarded")
async def onboarded(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    """The customer finished (or skipped) the /start steps; don't show them again."""
    await c.profile.mark_onboarded(claims.sub)
    return _settings_view(await c.profile.settings(claims.sub))


@router.get("/me/sessions")
async def sessions(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> list[dict]:
    return await c.profile.sessions(claims.sub)


@router.post("/me/sessions/revoke")
async def sign_out_everywhere(
    response: Response, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    """Ends every session, this one included. Access tokens already issued expire within 15 minutes."""
    revoked = await c.profile.revoke_sessions(claims.sub)
    response.delete_cookie(cookie_name("customer"), path="/auth")
    return {"revoked": revoked}


@router.get("/me/export")
async def export(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> Response:
    """Download my data: the business tables plus each order's product details."""
    data = await c.profile.export(claims.sub)
    for order in data["orders"]:
        spec = (await get_order(c.graph, order["id"])).get("spec") or {}
        order["details"] = {k: spec.get(k) for k in ("option", "quantity", "answers", "version")}
    return Response(
        json.dumps(jsonable_encoder(data), ensure_ascii=False, indent=1),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="orion-my-data.json"'},
    )


# --- business profile ----------------------------------------------------------------

class Contact(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern=PHONE)
    role: Literal["sign", "receive", "both"] = "both"


class BrandColor(BaseModel):
    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    name: Optional[str] = Field(None, max_length=40)   # e.g. "Gold", "main colour"

    @field_validator("hex")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper()


class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    business_type: Optional[Literal[BUSINESS_TYPES]] = None
    store_platform: Optional[Literal[STORE_PLATFORMS]] = None
    store_url: Optional[str] = Field(None, max_length=300, pattern=r"^(https?://\S+)?$")
    description: Optional[str] = Field(None, max_length=600)
    contacts: Optional[list[Contact]] = Field(None, max_length=10)
    brand_colors: Optional[list[BrandColor]] = Field(None, max_length=8)


class AddressIn(BaseModel):
    label: Optional[str] = Field(None, max_length=60)
    contact_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=PHONE)
    city: str = Field(min_length=1, max_length=80)
    district: Optional[str] = Field(None, max_length=80)
    street: str = Field(min_length=1, max_length=200)
    building: Optional[str] = Field(None, max_length=60)
    postal_code: Optional[str] = Field(None, pattern=r"^(\d{5}(-?\d{4})?)?$")
    notes: Optional[str] = Field(None, max_length=300)
    is_default: bool = False


def completeness(business: dict, addresses: list[dict]) -> dict:
    """What is still missing, grouped by when it is needed. Customs fields are not listed until the real
    forms are mapped (TODO(decide): exact customs field list, from a customs broker)."""
    default = next((a for a in addresses if a["is_default"]), None)
    items = [
        {"id": "business_name", "group": "first_order", "done": bool(business.get("name"))},
        {"id": "description", "group": "first_order", "done": bool(business.get("description"))},
        {"id": "shipping_address", "group": "first_shipment", "done": default is not None},
        {"id": "receiver", "group": "first_shipment",
         "done": bool(default and default["contact_name"] and default["phone"])},
    ]
    done = sum(i["done"] for i in items)
    return {"items": items, "done": done, "total": len(items), "customs_fields_ready": False}


async def _live_orders(c: ApiContext, customer_id: str) -> int:
    rows = await c.accounts.customer_orders(customer_id)
    return sum(1 for r in rows if r["stage"] not in UNSUBMITTED and r["stage"] not in CLOSED)


async def _business_view(c: ApiContext, customer_id: str) -> dict:
    business = await c.profile.business(customer_id)
    addresses = await c.profile.addresses(customer_id)
    return {
        "profile": business,
        "addresses": addresses,
        "logos": await c.profile.brand_logos(customer_id),
        "completeness": completeness(business, addresses),
        # Orders with factories now: address changes for these go through the team, never the AI
        "live_orders": await _live_orders(c, customer_id),
    }


@router.get("/business")
async def get_business(c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    return await _business_view(c, claims.sub)


@router.put("/business")
async def update_business(
    body: BusinessUpdate, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    fields = body.model_dump(exclude_unset=True)
    for key in ("name", "description", "store_url"):
        if isinstance(fields.get(key), str):
            fields[key] = fields[key].strip() or None
    if fields.get("brand_colors") is not None:
        seen, colors = set(), []
        for color in fields["brand_colors"]:
            if color["hex"] not in seen:
                seen.add(color["hex"])
                colors.append({"hex": color["hex"], "name": (color.get("name") or "").strip() or None})
        fields["brand_colors"] = colors
    await c.profile.save_business(claims.sub, fields)
    return await _business_view(c, claims.sub)


@router.post("/business/addresses", status_code=status.HTTP_201_CREATED)
async def add_address(
    body: AddressIn, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    if len(await c.profile.addresses(claims.sub)) >= 10:
        raise HTTPException(status.HTTP_409_CONFLICT, "at most 10 addresses")
    await c.profile.add_address(claims.sub, body.model_dump(exclude={"is_default"}), body.is_default)
    return await _business_view(c, claims.sub)


@router.put("/business/addresses/{address_id}")
async def update_address(
    address_id: str, body: AddressIn, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    if await c.profile.update_address(claims.sub, address_id, body.model_dump(exclude={"is_default"})) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "address not found")
    if body.is_default:
        await c.profile.set_default_address(claims.sub, address_id)
    return await _business_view(c, claims.sub)


@router.delete("/business/addresses/{address_id}")
async def delete_address(
    address_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    if not await c.profile.delete_address(claims.sub, address_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "address not found")
    return await _business_view(c, claims.sub)


@router.post("/business/addresses/{address_id}/default")
async def default_address(
    address_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    if not await c.profile.set_default_address(claims.sub, address_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "address not found")
    return await _business_view(c, claims.sub)


# --- brand logos (offered on the logo question of every new order) -------------------------

@router.post("/business/logos", status_code=status.HTTP_201_CREATED)
async def add_logo(file: UploadFile, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> dict:
    if len(await c.profile.brand_logos(claims.sub)) >= MAX_BRAND_LOGOS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"at most {MAX_BRAND_LOGOS} logos")
    name, content_type, data = await read_upload(c, file)
    await c.profile.add_brand_logo(claims.sub, name, content_type, len(data), c.files.save(data, ALLOWED[content_type]))
    return await _business_view(c, claims.sub)


@router.get("/business/logos/{file_id}")
async def get_logo(file_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)) -> Response:
    return serve_file(c, await c.profile.brand_logo(claims.sub, file_id))


@router.delete("/business/logos/{file_id}")
async def delete_logo(
    file_id: str, c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    if not await c.profile.delete_brand_logo(claims.sub, file_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "logo not found")
    return await _business_view(c, claims.sub)


# --- product ideas (Overview) ---------------------------------------------------------

async def _ideas(c: ApiContext, customer_id: str, lang: str, force: bool) -> dict:
    """Ideas from the business profile, kept until the profile, past products or language change.
    A model call happens only when there is nothing current to show (or the customer asks for new ones)."""
    business = await c.profile.business_for_ai(customer_id)
    if not business.get("description") and not business.get("name"):
        return {"status": "no_profile", "items": []}
    made = sorted({p["option"] for p in await c.products.products(customer_id)})
    fp = fingerprint(business, made, lang)
    cached = await c.profile.suggestions(customer_id, lang)
    if cached and cached["fingerprint"] == fp and not force:
        return {"status": "ok", "items": cached["items"], "generated_at": cached["created_at"]}
    if c.suggester is None or not c.suggest_limit.allow(customer_id):
        if cached:   # better an older list than none
            return {"status": "stale", "items": cached["items"], "generated_at": cached["created_at"]}
        return {"status": "unavailable", "items": []}
    try:
        items = clean(await c.suggester.ideas(business, catalogue(), made, lang))
    except Exception:
        log.exception("product ideas failed")
        return {"status": "unavailable", "items": cached["items"] if cached else []}
    await c.profile.save_suggestions(customer_id, lang, fp, items)
    return {"status": "ok", "items": items, "generated_at": datetime.now(timezone.utc)}


@router.get("/me/suggestions")
async def suggestions(
    lang: Literal["ar", "en"] = "ar", c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    return await _ideas(c, claims.sub, lang, force=False)


@router.post("/me/suggestions/refresh")
async def refresh_suggestions(
    lang: Literal["ar", "en"] = "ar", c: ApiContext = Depends(ctx), claims: TokenClaims = Depends(current_customer)
) -> dict:
    return await _ideas(c, claims.sub, lang, force=True)