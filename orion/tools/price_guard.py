"""Hard rule 1 in code: no prices, amounts or negotiation language in messages to manufacturers.

Asking for a quote is allowed ("请报价"); stating or discussing an amount is not.
"""

import re
from typing import Optional

_NUMBER = r"\d[\d,.]*"
_CURRENCY = (
    r"(?:¥|￥|\$|€|£|元|块|美元|人民币|rmb|cny|usd|sar|eur|yuan|dollars?|riyals?|ريال|ر\.س)"
)

_CURRENCY_AMOUNT = re.compile(
    rf"(?:{_CURRENCY}\s*{_NUMBER})|(?:{_NUMBER}\s*{_CURRENCY})", re.IGNORECASE
)
# A price word with a number close by on the same line, e.g. "单价 28" or "price: 4.5"
_PRICE_NEAR_NUMBER = re.compile(r"(?:price|cost|单价|价格|价钱|سعر)[^\n\d]{0,10}\d", re.IGNORECASE)
_PERCENT_OFF = re.compile(r"\d+\s*%\s*(?:off|discount)|\d+\s*折", re.IGNORECASE)

NEGOTIATION_TERMS = [
    # English
    "discount", "cheaper", "lower price", "lower the price", "best price", "reduce the price", "budget",
    "negotiat", "price increase", "increase the price", "rebate", "target price",
    # Chinese
    "折扣", "打折", "优惠", "便宜", "降价", "涨价", "预算", "砍价", "最低价", "让利", "议价", "还价", "目标价",
    # Arabic
    "خصم", "تخفيض", "ميزانية", "أرخص", "تفاوض",
]


def find_negotiation(text: str) -> Optional[str]:
    lowered = text.lower()
    for term in NEGOTIATION_TERMS:
        if term in lowered:
            return term
    return None


def price_violation(text: str) -> Optional[str]:
    """Return why `text` may not be sent to a manufacturer, or None if it is clean."""
    if match := _CURRENCY_AMOUNT.search(text):
        return f"contains an amount: '{match.group(0)}'"
    if match := _PRICE_NEAR_NUMBER.search(text):
        return f"contains a price: '{match.group(0)}'"
    if match := _PERCENT_OFF.search(text):
        return f"contains a discount: '{match.group(0)}'"
    if term := find_negotiation(text):
        return f"contains negotiation language: '{term}'"
    return None
