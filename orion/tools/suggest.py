"""Product ideas for the Overview page, from what the customer wrote about their business.

The model only proposes which of our product types could suit the business and why. Code then keeps only
known product types, trims lengths and drops any idea that mentions prices, amounts or discounts (rule 1).
"""

import hashlib
import json
from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from orion.config.markets import CUSTOM_OPTION, MARKETS
from orion.tools.llm import OpenRouterModel
from orion.tools.price_guard import price_violation
from orion.tools.prompts import SUGGEST_SYSTEM

PROMPT_VERSION = 1
MAX_IDEAS = 3


class ProductIdea(BaseModel):
    option: str = Field(description="One product type id from the list, or 'custom' for something not on it")
    title: str = Field(description="Short name of the product idea, in the customer's language (max 6 words)")
    why: str = Field(description="One sentence: why it suits this business, in the customer's language")
    details: str = Field(description="One short line of suggested details (material, decoration, use), no prices")


class IdeaList(BaseModel):
    ideas: list[ProductIdea] = Field(description=f"Up to {MAX_IDEAS} ideas, best first")


class Suggester(Protocol):
    async def ideas(self, business: dict, catalogue: list[dict], made: list[str], lang: str) -> list[ProductIdea]: ...


def catalogue() -> list[dict]:
    """Product types customers can order today (live markets only)."""
    return [
        {"market": m.id, "option": o.id, "name": o.name, "name_ar": o.name_ar}
        for m in MARKETS.values() for o in m.options.values()
    ]


def fingerprint(business: dict, made: list[str], lang: str) -> str:
    """Same inputs, same ideas: regenerate only when the profile, past products, language or prompt change."""
    raw = json.dumps({"b": business, "m": sorted(made), "l": lang, "v": PROMPT_VERSION,
                      "c": [c["option"] for c in catalogue()]}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def clean(ideas: list[ProductIdea]) -> list[dict]:
    """Code decides what is shown: known product types only, short texts, nothing about money."""
    by_option = {c["option"]: c for c in catalogue()}
    out = []
    for idea in ideas:
        text = f"{idea.title}\n{idea.why}\n{idea.details}"
        if price_violation(text) or not idea.title.strip():
            continue
        option = idea.option if idea.option in by_option else CUSTOM_OPTION
        out.append({
            "market": by_option.get(option, {}).get("market") or next(iter(MARKETS)),
            "option": option,
            "title": idea.title.strip()[:80],
            "why": idea.why.strip()[:240],
            "details": idea.details.strip()[:200],
        })
        if len(out) == MAX_IDEAS:
            break
    return out


class OpenRouterSuggester:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._model = OpenRouterModel(api_key, base_url, model, temperature=0.7, max_tokens=1500)

    async def ideas(self, business: dict, catalogue: list[dict], made: list[str], lang: str) -> list[ProductIdea]:
        result = await self._model.structured(IdeaList).ainvoke([
            SystemMessage(SUGGEST_SYSTEM),
            HumanMessage(
                f"Reply language: {'Arabic' if lang == 'ar' else 'English'}\n"
                f"Product types we make:\n{json.dumps(catalogue, ensure_ascii=False, indent=1)}\n"
                f"Already ordered by this customer: {', '.join(made) or 'nothing yet'}\n\n"
                f"<business_profile>\n{json.dumps(business, ensure_ascii=False, indent=1)}\n</business_profile>"
            ),
        ])
        return result.ideas
