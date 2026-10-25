import asyncio

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from orion.db.stores import InMemoryDirectory, InMemoryOutbox, InMemoryPriceStore, InMemoryScheduler, Manufacturer
from orion.deps import Deps
from orion.graph.graph import build_graph
from orion.spec import ProductSpec
from orion.tools.llm import AnswerUpdate, CompletenessReport, ConsultContext, DeepDiveTurn, FollowUpQuestion
from orion.tools.manufacturer_llm import DraftAnswers, ReplyAnalysis, SpecTranslation, TranslatedField


@pytest.fixture(scope="session")
def pg_url():
    """A fresh, migrated `orion_test` database per test run. Skips the test when Postgres is not running."""
    import psycopg
    from alembic import command
    from alembic.config import Config
    from psycopg.conninfo import conninfo_to_dict

    from orion.config.settings import get_settings

    try:
        base = get_settings().database_url
        with psycopg.connect(base, autocommit=True, connect_timeout=3) as conn:
            conn.execute("DROP DATABASE IF EXISTS orion_test WITH (FORCE)")
            conn.execute("CREATE DATABASE orion_test")
    except Exception as e:  # no settings or no server
        pytest.skip(f"Postgres not available: {e}")

    url = "postgresql://{user}:{password}@{host}:{port}/orion_test".format(**conninfo_to_dict(base))
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    return url


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


def ask(qid: str, prompt: str | None = None, choices=("yes", "no", "Not sure, use the factory standard"),
        section: str = "design", multiple: bool = False) -> FollowUpQuestion:
    """A follow-up question the fake AI asks."""
    return FollowUpQuestion(id=qid, prompt=prompt or f"{qid}?", section=section, choices=list(choices), multiple=multiple)


def turn(intro: str = "", ready: bool = False, questions=(), **updates: str) -> DeepDiveTurn:
    return DeepDiveTurn(
        updates=[AnswerUpdate(id=k, value=v) for k, v in updates.items()],
        intro=intro,
        questions=list(questions),
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
    "drawstrings": "flat cotton",
    "pocket": "kangaroo pocket",
    "size_standard": "US/EU sizing",
    "needed_by": "in 1-2 months",
    "packaging": ["individual polybag"],
    "sample": "yes, sample first",
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
        scheduler=InMemoryScheduler(),
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
