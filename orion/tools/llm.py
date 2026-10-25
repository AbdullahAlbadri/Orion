"""LLM calls used by the ordering graph.

Nodes depend on the `Consultant` protocol, not on a model, so tests can pass a fake.
"""

import json
from typing import Literal, Optional, Protocol

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
    lang: Literal["ar", "en"] = "en"


class AnswerUpdate(BaseModel):
    id: str = Field(description="Question id from the list, or a new short snake_case id for a detail not covered")
    value: str = Field(description="The customer's answer as plain text. Size tables as 'S:20, M:30'.")


class FollowUpQuestion(BaseModel):
    id: str = Field(description="Short English snake_case id; reuse a known question id to correct an earlier answer")
    prompt: str = Field(description="The question, in the customer's language")
    section: Literal["design", "quantity", "quality"]
    choices: list[str] = Field(
        description="3-6 short answer options in the customer's language, including one like "
                    "'Not sure, use the factory standard'. The customer can also type their own answer."
    )
    multiple: bool = Field(False, description="True if several options can apply at once")


class DeepDiveTurn(BaseModel):
    updates: list[AnswerUpdate] = Field(
        description="Concrete details from the customer's latest answers or messages that should be recorded"
    )
    intro: str = Field(description="One short sentence shown above the questions, in the customer's language")
    questions: list[FollowUpQuestion] = Field(description="At most 5 follow-up questions; empty if nothing is left")
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
        f"Customer language: {'Arabic' if ctx.lang == 'ar' else 'English'} (write intro, questions and choices in it)",
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


class OpenRouterModel:
    """Creates the chat model on first use, so processes that never call the LLM run without a key."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: Optional[str] = None,
    ):
        """reasoning_effort ("low" / "medium" / "high"): for models that think before answering, so the
        thinking does not use up max_tokens. Passed to OpenRouter's `reasoning` option."""
        extra = {"reasoning": {"effort": reasoning_effort}} if reasoning_effort else None
        self._args = dict(
            extra_body=extra,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            # Always cap output: without it OpenRouter reserves the model's maximum against the key's budget
            max_tokens=max_tokens,
            timeout=60,
            max_retries=2,
        )
        self._llm = None

    def structured(self, schema: type[BaseModel]):
        if self._llm is None:
            if not self._args["api_key"]:
                raise RuntimeError("OPENROUTER_API_KEY is empty in .env")
            self._llm = ChatOpenAI(**self._args)
        # json_schema (constrained JSON output). Claude Sonnet 5.5 rejects the forced tool_choice
        # that method="function_calling" sends.
        return self._llm.with_structured_output(schema, method="json_schema")


class OpenRouterConsultant:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._model = OpenRouterModel(api_key, base_url, model, temperature=0.3, max_tokens=1500)

    async def deep_dive(self, ctx: ConsultContext) -> DeepDiveTurn:
        return await self._model.structured(DeepDiveTurn).ainvoke(
            [SystemMessage(CONSULTANT_SYSTEM), HumanMessage(render_context(ctx))]
        )

    async def check_completeness(self, ctx: ConsultContext) -> CompletenessReport:
        # Separate prompt and no chat history: the asker does not grade itself.
        return await self._model.structured(CompletenessReport).ainvoke(
            [SystemMessage(COMPLETENESS_SYSTEM), HumanMessage(render_context(ctx, include_chat=False))]
        )
