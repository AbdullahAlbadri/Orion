"""The customer's quote, calculated in code from the manufacturers' recorded prices (rule 2).

Problems are of two kinds: blocking (nothing can be calculated, e.g. no verified product price) and warnings
(the quote can be calculated but a person should look first, e.g. the factory's minimum order is above the
order quantity). The team sends a quote with warnings only by saying so explicitly.
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from orion.config.pricing import Pricing

CENT = Decimal("0.01")


def _sar(amount: float, currency: Optional[str], pricing: Pricing, fee: bool) -> Optional[Decimal]:
    rate = pricing.to_sar.get(currency or "")
    if rate is None:
        return None
    value = Decimal(str(amount)) * Decimal(str(rate))
    if fee:
        value *= 1 + Decimal(str(pricing.fee_rate))
    return value.quantize(CENT, ROUND_HALF_UP)


def _charge(price: dict) -> str:
    return price.get("charge") or "product"    # quotes recorded before charges were told apart


def _latest_per_manufacturer(quotes: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for q in quotes:
        if not q.get("expired"):
            latest[q["manufacturer_id"]] = q     # quotes are appended in the order they arrive
    return list(latest.values())


def _product_price(quote: dict, quantity: Optional[int]) -> Optional[dict]:
    """The verified per-piece product price; with quantity tiers, the one for the order's quantity."""
    prices = [p for p in quote.get("prices", []) if _charge(p) == "product" and p.get("status") == "verified"
              and p.get("unit", "piece") == "piece"]
    fitting = [p for p in prices if not p.get("quantity") or (quantity and p["quantity"] <= quantity)]
    pool = fitting or prices
    return max(pool, key=lambda p: p.get("quantity") or 0) if pool else None


def wants_sample(answers: dict) -> bool:
    return str(answers.get("sample", "")).lower().startswith("yes")


def build_customer_quote(quotes: list[dict], spec: dict, pricing: Pricing, validity_days: int,
                         now: datetime) -> dict:
    """{"quote": what the customer sees or None, "basis": how it was calculated (team only),
    "blocking": [...], "warnings": [...]}"""
    quantity = spec.get("quantity")
    blocking, warnings = [], []
    if not quantity:
        blocking.append("the order has no quantity")

    # Cheapest verified product price (in SAR) across the factories that quoted
    options = []
    for q in _latest_per_manufacturer(quotes):
        price = _product_price(q, quantity)
        if price is None:
            continue
        unit = _sar(price["unit_price"], price.get("currency"), pricing, fee=True)
        if unit is None:
            warnings.append(f"{q['manufacturer_id']}: no fixed rate for {price.get('currency')}")
            continue
        options.append((unit, q, price))
    if not options:
        blocking.append("no verified per-piece product price in a usable currency")
    if blocking:
        return {"quote": None, "basis": None, "blocking": blocking, "warnings": warnings}

    unit_sar, quote, price = min(options, key=lambda o: o[0])
    others = [p for p in quote.get("prices", []) if p.get("status") == "verified"]
    if quote.get("moq") and quote["moq"] > quantity:
        warnings.append(f"factory minimum order is {quote['moq']} pieces; the order is {quantity}")
    if any(_charge(p) == "other" for p in quote.get("prices", [])):
        warnings.append("the factory listed an extra charge (mould, setup...); decide how to include it")

    # Shipping: the factory's figure, approximate, no fee
    shipping_sar = None
    shipping = next((p for p in others if _charge(p) == "shipping"), None)
    if shipping is None:
        warnings.append("no shipping price from the factory; the customer sees shipping as to be confirmed")
    else:
        amount = _sar(shipping["unit_price"], shipping.get("currency"), pricing, fee=False)
        if amount is None:
            warnings.append(f"no fixed rate for the shipping currency {shipping.get('currency')}")
        elif shipping.get("unit") in ("order", None):
            shipping_sar = amount
        elif shipping.get("unit") == "piece":
            shipping_sar = amount * quantity
        else:
            warnings.append(f"shipping is priced per {shipping.get('unit')}; work out the total by hand")

    sample_sar = None
    if wants_sample(spec.get("answers") or {}):
        sample = next((p for p in others if _charge(p) == "sample"), None)
        if sample is None:
            warnings.append("the customer wants a sample but the factory gave no sample price")
        else:
            sample_sar = _sar(sample["unit_price"], sample.get("currency"), pricing, fee=True)

    products_total = unit_sar * quantity
    production_days, shipping_days = quote.get("lead_time_days"), quote.get("shipping_days")
    return {
        "quote": {
            "currency": "SAR",
            "quantity": quantity,
            "unit_price": str(unit_sar),
            "products_total": str(products_total),
            "shipping": str(shipping_sar) if shipping_sar is not None else None,   # approximate
            "total": str(products_total + (shipping_sar or 0)),
            "sample_price": str(sample_sar) if sample_sar is not None else None,   # paid separately
            "production_days": production_days,
            "shipping_days": shipping_days,
            "valid_until": (now + timedelta(days=validity_days)).isoformat(),
        },
        "basis": {
            "manufacturer_id": quote["manufacturer_id"], "quote_id": quote.get("quote_id"),
            "factory_unit_price": price["unit_price"], "currency": price.get("currency"),
            "rate_to_sar": pricing.to_sar.get(price.get("currency") or ""), "fee_rate": pricing.fee_rate,
            "rates_checked": pricing.rates_checked,
        },
        "blocking": [],
        "warnings": warnings,
    }
