"""LLM calls for the manufacturer side.

Manufacturer messages are untrusted input: the model only fills a schema (no tools), and
nodes re-check every field in code before acting on it.
"""

import json
from typing import Literal, Optional, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from orion.spec import ProductSpec
from orion.tools.llm import OpenRouterModel
from orion.tools.prices import ExtractedPrice
from orion.tools.prompts import ANALYZE_REPLY_SYSTEM, ANSWER_QUESTIONS_SYSTEM, TRANSLATE_SPEC_SYSTEM


class TranslatedField(BaseModel):
    id: str
    label_zh: str
    value_zh: str
    value_en: str = Field("", description="The same value in plain English (copied if it is already English)")


class SpecTranslation(BaseModel):
    product_zh: str = Field(description="Product name in Chinese")
    fields: list[TranslatedField]


class SpecMismatch(BaseModel):
    field_id: str = Field(description="Spec field id the manufacturer contradicts")
    manufacturer_says: str = Field(description="What the manufacturer offers instead, in English")
    quoted_text: str = Field(description="Exact text from the message")


class ReplyAnalysis(BaseModel):
    kind: Literal["quote", "questions", "acknowledgement", "decline", "other"]
    prices: list[ExtractedPrice] = []
    questions: list[str] = Field([], description="Questions the manufacturer asks us, in English")
    mismatches: list[SpecMismatch] = []
    mentions_negotiation: bool = Field(
        False, description="Discounts, price increases, budget, or quantity-for-price offers"
    )
    moq: Optional[int] = None
    lead_time_days: Optional[int] = None
    sample_terms: Optional[str] = Field(None, description="Sample cost/time terms, in English")
    summary_en: str = Field(description="One or two sentence summary in English")


class DraftAnswer(BaseModel):
    question: str
    answerable: bool = Field(description="False if the spec does not contain the answer")
    answer_zh: str = Field(description="Answer in Chinese, empty if not answerable")


class DraftAnswers(BaseModel):
    answers: list[DraftAnswer]


class ManufacturerAgent(Protocol):
    async def translate_spec(self, spec: ProductSpec, product_name: str) -> SpecTranslation: ...

    async def analyze_reply(self, spec: ProductSpec, spec_zh: dict, message: str) -> ReplyAnalysis: ...

    async def answer_questions(self, spec: ProductSpec, spec_zh: dict, questions: list[str]) -> DraftAnswers: ...


def _spec_json(spec: ProductSpec) -> str:
    return spec.model_dump_json(include={"option", "quantity", "answers"}, indent=1)


class OpenRouterManufacturerAgent:
    def __init__(self, api_key: str, base_url: str, model: str, reasoning_effort: Optional[str] = None):
        self._model = OpenRouterModel(
            api_key, base_url, model, temperature=0, max_tokens=8000, reasoning_effort=reasoning_effort
        )

    async def translate_spec(self, spec: ProductSpec, product_name: str) -> SpecTranslation:
        return await self._model.structured(SpecTranslation).ainvoke([
            SystemMessage(TRANSLATE_SPEC_SYSTEM),
            HumanMessage(f"Product: {product_name}\n\nSpec:\n{_spec_json(spec)}"),
        ])

    async def analyze_reply(self, spec: ProductSpec, spec_zh: dict, message: str) -> ReplyAnalysis:
        return await self._model.structured(ReplyAnalysis).ainvoke([
            SystemMessage(ANALYZE_REPLY_SYSTEM),
            HumanMessage(
                f"Our spec:\n{_spec_json(spec)}\n\n"
                f"<manufacturer_message>\n{message}\n</manufacturer_message>"
            ),
        ])

    async def answer_questions(self, spec: ProductSpec, spec_zh: dict, questions: list[str]) -> DraftAnswers:
        return await self._model.structured(DraftAnswers).ainvoke([
            SystemMessage(ANSWER_QUESTIONS_SYSTEM),
            HumanMessage(
                f"Spec:\n{_spec_json(spec)}\n\nChinese spec:\n{json.dumps(spec_zh, ensure_ascii=False, indent=1)}"
                f"\n\nQuestions:\n" + "\n".join(f"- {q}" for q in questions)
            ),
        ])
