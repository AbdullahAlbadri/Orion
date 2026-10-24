"""Render the pre-receipt from the spec. Code, not LLM: it must show exactly what will be frozen."""

from orion.config.markets import Market
from orion.spec import QUANTITY_ID, SIZE_TABLE_ID, ProductSpec, Question


def _label(question_id: str) -> str:
    return question_id.replace("_", " ").capitalize()


def render_pre_receipt(spec: ProductSpec, market: Market, questions: list[Question]) -> str:
    option = market.options[spec.option]
    known_ids = [q.id for q in questions]
    lines = [
        "PRE-RECEIPT (product summary, not a price quote)",
        f"Product: {option.name} ({market.name})",
        f"Total quantity: {spec.quantity if spec.quantity is not None else 'not set'}",
    ]

    sizes = spec.answers.get(SIZE_TABLE_ID)
    if sizes:
        lines.append("")
        lines.append("Sizes:")
        lines += [f"  {size:<6} {qty}" for size, qty in sizes.items()]

    skip = {QUANTITY_ID, SIZE_TABLE_ID}
    known = [(qid, spec.answers[qid]) for qid in known_ids if qid in spec.answers and qid not in skip]
    extra = [(qid, v) for qid, v in spec.answers.items() if qid not in known_ids and qid not in skip]

    if known:
        lines += ["", "Details:"] + [f"- {_label(qid)}: {value}" for qid, value in known]
    if extra:
        lines += ["", "Additional details:"] + [f"- {_label(qid)}: {value}" for qid, value in extra]
    if spec.files:
        lines += ["", "Files:"] + [f"- {f.kind}: {f.url}" for f in spec.files]
    if spec.open_gaps:
        lines += ["", "Still open (the Orion team will follow up):"] + [f"- {gap}" for gap in spec.open_gaps]
    return "\n".join(lines)
