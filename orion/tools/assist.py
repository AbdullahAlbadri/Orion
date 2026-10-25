"""'Ask Orion' help on one form section (design / quantity / quality).

Advice only: it never changes the order. Answers mentioning prices are replaced in code (hard rule 1).
"""

import json
from typing import Literal, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from orion.spec import Question
from orion.tools.llm import OpenRouterModel
from orion.tools.price_guard import price_violation
from orion.tools.prompts import ASSIST_SYSTEM

PRICE_FALLBACK = {
    "en": "Prices depend on the manufacturer. Our team will send you a quote after checking with factories.",
    "ar": "الأسعار تعتمد على المصنع، وسيرسل لك فريقنا عرض السعر بعد التواصل مع المصانع.",
}


class AssistAnswer(BaseModel):
    answer: str = Field(description="Short, practical advice for the customer, in their language")


class Assistant(Protocol):
    async def help(
        self, product: str, section: str, questions: list[Question], answers: dict, question: str, lang: str
    ) -> str: ...


class OpenRouterAssistant:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._model = OpenRouterModel(api_key, base_url, model, temperature=0.3, max_tokens=1000)

    async def help(
        self, product: str, section: str, questions: list[Question], answers: dict, question: str, lang: str
    ) -> str:
        fields = [{"id": q.id, "question": q.prompt, "choices": q.choices, "hint": q.hint} for q in questions]
        result = await self._model.structured(AssistAnswer).ainvoke([
            SystemMessage(ASSIST_SYSTEM),
            HumanMessage(
                f"Reply language: {'Arabic' if lang == 'ar' else 'English'}\n"
                f"Product: {product}\nSection: {section}\n"
                f"Questions in this section:\n{json.dumps(fields, ensure_ascii=False, indent=1)}\n"
                f"Customer's answers so far:\n{json.dumps(answers, ensure_ascii=False)}\n\n"
                f"<customer_question>\n{question}\n</customer_question>"
            ),
        ])
        return result.answer


def safe_answer(answer: str, lang: Literal["en", "ar"]) -> str:
    """Never show the customer an answer that talks about prices, amounts or discounts."""
    return PRICE_FALLBACK[lang] if price_violation(answer) else answer.strip()
