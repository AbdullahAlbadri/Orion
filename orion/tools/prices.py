"""Hard rule 2 in code: the LLM proposes a price and the exact text; code decides whether to trust it."""

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

PriceStatus = Literal["verified", "extracted"]   # extracted = unverified, needs a human


class ExtractedPrice(BaseModel):
    charge: Literal["product", "sample", "shipping", "other"] = Field(
        "product", description="What the price is for: the product itself, a sample, shipping to Saudi Arabia, "
                               "or something else (mould, setup, plate...)",
    )
    unit_price: float = Field(description="The price number exactly as written in the message")
    currency: Optional[str] = Field(None, description="Currency as written (¥, 元, RMB, USD...), null if not stated")
    unit: Literal["piece", "carton", "set", "kg", "order", "other", "unknown"] = Field(
        description="What one price unit buys; 'order' = one amount for the whole order or shipment"
    )
    quantity: Optional[int] = Field(None, description="Order quantity / tier this price applies to, if stated")
    shipping_included: Optional[bool] = Field(None, description="null if the message does not say")
    incoterm: Optional[str] = Field(None, description="EXW, FOB, CIF, DDP... if stated")
    tax_included: Optional[bool] = Field(None, description="null if the message does not say")
    quoted_text: str = Field(description="The exact sentence or phrase from the message containing the price")


class PriceCheck(BaseModel):
    trusted_text: bool          # quoted text is really in the message and contains the number
    status: PriceStatus
    currency: Optional[str]     # normalized ISO code
    problems: list[str]


_CURRENCIES = {
    "CNY": ["¥", "￥", "元", "块", "rmb", "cny", "人民币", "yuan"],
    "USD": ["usd", "us$", "$", "美元", "dollar"],
    "SAR": ["sar", "ريال", "riyal"],
    "EUR": ["eur", "€", "欧元"],
}
_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def normalize_currency(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    value = raw.strip().lower()
    for code, aliases in _CURRENCIES.items():
        if value == code.lower() or any(alias in value for alias in aliases):
            return code
    return None


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _parse_number(token: str) -> float:
    # "1,200" / "1,200.50" -> thousands separator; "28,5" -> decimal comma
    if "," in token and "." not in token and re.fullmatch(r"\d+,\d{1,2}", token):
        token = token.replace(",", ".")
    return float(token.replace(",", ""))


def check_price(price: ExtractedPrice, message: str) -> PriceCheck:
    problems = []
    in_message = bool(price.quoted_text.strip()) and _squash(price.quoted_text) in _squash(message)
    numbers = [_parse_number(t) for t in _NUM.findall(price.quoted_text)]
    has_number = any(abs(n - price.unit_price) < 1e-9 for n in numbers)
    if not in_message:
        problems.append("quoted text not found in the message")
    if not has_number:
        problems.append(f"{price.unit_price} does not appear in the quoted text")

    currency = normalize_currency(price.currency)
    if currency is None:
        problems.append("currency unclear")
    if price.charge == "product":
        if price.unit != "piece":
            problems.append(f"price is per {price.unit}, not per piece")
        if price.shipping_included is None and not price.incoterm:
            problems.append("unclear whether shipping is included")
        if price.tax_included is None:
            problems.append("unclear whether tax is included")
    elif price.charge == "sample" and price.unit not in ("piece", "set", "order"):
        problems.append(f"sample price is per {price.unit}")
    elif price.charge == "shipping" and price.unit not in ("order", "kg", "piece", "carton"):
        problems.append(f"shipping price is per {price.unit}")
    elif price.charge == "other":
        problems.append("extra charge: the team decides how it is quoted")

    trusted = in_message and has_number
    return PriceCheck(
        trusted_text=trusted,
        status="verified" if trusted and not problems else "extracted",
        currency=currency,
        problems=problems,
    )
