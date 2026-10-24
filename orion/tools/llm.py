"""LLM calls used by the ordering graph.

Nodes depend on the `Consultant` protocol, not on a model, so tests can pass a fake.
"""

import json
from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from orion.spec import ProductSpec, Question
from orion.tools.prompts import COMPLETENESS_SYSTEM, CONSULTANT_SYSTEM


class ConsultContext(BaseModel):
    market_name: str
    option_name: str
    questions: list[Question]
    spec: ProductSpec
    messages: list[dict] = []      # {"role": "customer" | "orion", "content": str}
    compliance_notes: list[str] = []


class AnswerUpdate(BaseModel):
    id: str = Field(description="Question id from the list, or a new short snake_case id for a detail not covered")
    value: str = Field(description="The customer's answer as plain text. Size tables as 'S:20, M:30'.")


class DeepDiveTurn(BaseModel):
    updates: list[AnswerUpdate] = Field(description="Details the customer gave in their latest message(s)")
    message: str = Field(description="What to say to the customer next, in their language")
    ready_for_review: bool = Field(description="True only if nothing is left to ask")


class CompletenessReport(BaseModel):
    gaps: list[str] = Field(description="Questions a manufacturer would still have to ask. Empty if none.")


class Consultant(Protocol):
    async def deep_dive(self, ctx: ConsultContext) -> DeepDiveTurn: ...

    async def check_completeness(self, ctx: ConsultContext) -> CompletenessReport: ...


def render_context(ctx: ConsultContext, include_chat: bool = True) -> str:
    questions = [
        {"id": q.id, "prompt": q.prompt, "type": q.type, "choices": q.choices, "required": q.required}
        for q in ctx.questions
    ]
    parts = [
        f"Product: {ctx.option_name} ({ctx.market_name})",
        f"Known questions:\n{json.dumps(questions, ensure_ascii=False, indent=1)}",
        f"Current spec:\n{ctx.spec.model_dump_json(include={'quantity', 'answers', 'open_gaps'}, indent=1)}",
    ]
    if ctx.compliance_notes:
        parts.append("Compliance notes (unverified, do not promise anything):\n- " + "\n- ".join(ctx.compliance_notes))
    if include_chat:
        chat = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in ctx.messages) or "(no messages yet)"
        parts.append(f"Conversation so far:\n{chat}")
    return "\n\n".join(parts)


class OpenRouterConsultant:
    def __init__(self, api_key: str, base_url: str, model: str):
        llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=0.3)
        # function_calling is the most widely supported structured-output method on OpenRouter
        self._deep_dive = llm.with_structured_output(DeepDiveTurn, method="function_calling")
        self._completeness = llm.with_structured_output(CompletenessReport, method="function_calling")

    async def deep_dive(self, ctx: ConsultContext) -> DeepDiveTurn:
        return await self._deep_dive.ainvoke(
            [SystemMessage(CONSULTANT_SYSTEM), HumanMessage(render_context(ctx))]
        )

    async def check_completeness(self, ctx: ConsultContext) -> CompletenessReport:
        # Separate prompt and no chat history: the asker does not grade itself.
        return await self._completeness.ainvoke(
            [SystemMessage(COMPLETENESS_SYSTEM), HumanMessage(render_context(ctx, include_chat=False))]
        )
