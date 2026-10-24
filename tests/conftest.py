import pytest
from langgraph.checkpoint.memory import InMemorySaver

from orion.graph.graph import build_graph
from orion.tools.llm import AnswerUpdate, CompletenessReport, ConsultContext, DeepDiveTurn


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


@pytest.fixture
def make_app():
    def _make(consultant, **kwargs):
        return build_graph(consultant, InMemorySaver(), **kwargs)
    return _make
