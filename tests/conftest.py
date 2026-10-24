import asyncio

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from orion.db.stores import InMemoryDirectory, InMemoryOutbox, InMemoryPriceStore, Manufacturer
from orion.deps import Deps
from orion.graph.graph import build_graph
from orion.spec import ProductSpec
from orion.tools.llm import AnswerUpdate, CompletenessReport, ConsultContext, DeepDiveTurn
from orion.tools.manufacturer_llm import DraftAnswers, ReplyAnalysis, SpecTranslation, TranslatedField


def pytest_asyncio_loop_factories(config, item):
    # psycopg's async mode needs a selector event loop; Windows defaults to proactor.
    return {"selector": asyncio.SelectorEventLoop}


class ScriptedConsultant:
    """Fake LLM: returns queued turns in order and records what it was shown."""

    def __init__(self, turns: list[DeepDiveTurn], reports: list[CompletenessReport]):
        self.turns = list(turns)
        self.reports = list(reports)
        self.deep_dive_calls: list[ConsultContext] = []
        self.completeness_calls: list[ConsultContext] = []

    async def deep_dive(self, ctx: ConsultContext) -> DeepDiveTurn:
        self.deep_dive_calls.append(ctx.model_copy(deep=True))
        return self.turns.pop(0)

    async def check_completeness(self, ctx: ConsultContext) -> CompletenessReport:
        self.completeness_calls.append(ctx.model_copy(deep=True))
        return self.reports.pop(0) if self.reports else CompletenessReport(gaps=[])


class ScriptedManufacturerAgent:
    """Fake manufacturer-side LLM: echo translation, queued analyses and drafted answers."""

    def __init__(self, analyses: list[ReplyAnalysis] = (), drafts: list[DraftAnswers] = (), skip_ids=()):
        self.analyses = list(analyses)
        self.drafts = list(drafts)
        self.skip_ids = set(skip_ids)        # ids the "translation" leaves out
        self.analyzed: list[str] = []

    async def translate_spec(self, spec: ProductSpec, product_name: str) -> SpecTranslation:
        return SpecTranslation(
            product_zh="卫衣",
            fields=[
                TranslatedField(id=k, label_zh=f"中-{k}", value_zh=f"中-{v}")
                for k, v in spec.answers.items() if k not in self.skip_ids
            ],
        )

    async def analyze_reply(self, spec, spec_zh, message: str) -> ReplyAnalysis:
        self.analyzed.append(message)
        return self.analyses.pop(0)

    async def answer_questions(self, spec, spec_zh, questions) -> DraftAnswers:
        return self.drafts.pop(0)


def turn(message: str = "", ready: bool = False, **updates: str) -> DeepDiveTurn:
    return DeepDiveTurn(
        updates=[AnswerUpdate(id=k, value=v) for k, v in updates.items()],
        message=message,
        ready_for_review=ready,
    )


HOODIE_ANSWERS = {
    "colors": "black, Pantone Black C",
    "decoration_method": "embroidery",
    "decoration_placement": "left chest 8cm",
    "fabric": "cotton fleece",
    "fabric_gsm": "350",
    "hoodie_style": "pullover",
    "size_breakdown": "S:20, M:50, L:50, XL:30",
    "labels": "woven neck label",
}

FACTORY_A = Manufacturer(id="factory-a", name="Factory A")
FACTORY_B = Manufacturer(id="factory-b", name="Factory B")


def make_deps(consultant=None, manufacturer_agent=None, manufacturers=(FACTORY_A, FACTORY_B)) -> Deps:
    return Deps(
        consultant=consultant or ScriptedConsultant([], []),
        manufacturer_agent=manufacturer_agent or ScriptedManufacturerAgent(),
        directory=InMemoryDirectory({("apparel", "hoodie"): list(manufacturers)}),
        prices=InMemoryPriceStore(),
        channel=InMemoryOutbox(),
    )


@pytest.fixture
def make_app():
    def _make(consultant, **kwargs):
        return build_graph(make_deps(consultant), InMemorySaver(), **kwargs)
    return _make


@pytest.fixture
def make_order():
    """Build an app from Deps; returns (app, deps) so tests can inspect stores."""
    def _make(**deps_kwargs):
        deps = make_deps(**deps_kwargs)
        return build_graph(deps, InMemorySaver()), deps
    return _make
