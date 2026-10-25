"""The pre-receipt, built in code from the spec (never by the LLM): it must show exactly what will be frozen.

- `build_summary`: structured, in the customer's language, for the website's visual receipt.
- `render_pre_receipt`: plain text of the same content, for the team console, terminal and audit trail.
"""

from typing import Any, Optional

from orion.config.markets import Market
from orion.spec import QUANTITY_ID, SIZE_TABLE_ID, ProductSpec, Question, format_answer, localize_answer

TEXT = {
    "en": {
        "title": "PRE-RECEIPT (product summary, not a price quote)", "product": "Product", "total": "Total quantity",
        "not_set": "not set", "sizes": "Sizes", "details": "Details", "extra": "Additional details",
        "files": "Files", "open": "Still open (the Orion team will follow up)",
    },
    "ar": {
        "title": "ملخص المنتج (ليس عرض سعر)", "product": "المنتج", "total": "الكمية الإجمالية",
        "not_set": "غير محددة", "sizes": "المقاسات", "details": "التفاصيل", "extra": "تفاصيل إضافية",
        "files": "الملفات", "open": "نقاط مفتوحة (سيتابعها فريق أوريون)",
    },
}
SKIP = {QUANTITY_ID, SIZE_TABLE_ID}


def _humanize(question_id: str) -> str:
    return question_id.replace("_", " ").capitalize()


def label(question_id: str, question: Optional[Question], spec: ProductSpec, lang: str) -> str:
    """Short label: the question's own wording without the question mark."""
    if question is not None:
        text = question.prompt_ar if lang == "ar" and question.prompt_ar else question.prompt
        return text.rstrip("?؟:. ").split(",")[0].split("،")[0]
    return spec.labels.get(question_id) or _humanize(question_id)


_QUALITY_WORDS = ("fabric", "material", "gsm", "weight", "thread", "stitch", "lining", "wash", "finish", "label",
                  "tag", "packag", "care", "quality", "sample", "certif", "قماش", "خام", "وزن", "ملصق", "تغليف", "عينة")
_QUANTITY_WORDS = ("quantity", "qty", "pieces", "size", "deadline", "date", "deliver", "timeline", "when",
                   "كمية", "قطع", "مقاس", "موعد", "تاريخ", "متى")


def guess_section(question_id: str, text: str) -> str:
    """Section for a detail recorded without one (older orders, free-text changes)."""
    words = f"{question_id} {text}".lower()
    if any(w in words for w in _QUANTITY_WORDS):
        return "quantity"
    if any(w in words for w in _QUALITY_WORDS):
        return "quality"
    return "design"


def build_summary(spec: ProductSpec, market: Market, questions: list[Question], lang: str) -> dict[str, Any]:
    option = market.options[spec.option]
    by_id = {q.id: q for q in questions}
    sections: dict[str, list[dict]] = {"design": [], "quantity": [], "quality": []}
    for q in questions:
        if q.id in SKIP or q.id not in spec.answers:
            continue
        value = spec.answers[q.id]
        sections[q.section].append({
            "id": q.id,
            "type": q.type,
            "label": label(q.id, q, spec, lang),
            "value": localize_answer(q, value, lang),
            "raw": value,   # English values / placement data, for swatches and the drawing
        })
    # Details the AI asked about go in their own section, after the form's questions
    for qid, value in spec.answers.items():
        if qid in by_id or qid in SKIP:
            continue
        text = label(qid, None, spec, lang)
        section = spec.sections.get(qid) or guess_section(qid, text)
        sections[section if section in sections else "design"].append(
            {"id": qid, "type": "text", "label": text, "value": format_answer(value), "raw": value}
        )
    extras: list[dict] = []   # kept for older clients; every detail now has a section
    return {
        "lang": lang,
        "product": option.name_ar if lang == "ar" else option.name,
        "option": spec.option,
        "market": market.name_ar if lang == "ar" else market.name,
        "mockup": option.mockup,
        "quantity": spec.quantity,
        "sizes": spec.answers.get(SIZE_TABLE_ID) or {},
        "sections": [{"id": sid, "items": items} for sid, items in sections.items() if items],
        "extras": extras,
        "files": [f.model_dump() for f in spec.files],
        "open_gaps": spec.open_gaps,
    }


def render_pre_receipt(spec: ProductSpec, market: Market, questions: list[Question], lang: str = "en") -> str:
    """Plain-text version of the summary."""
    s = build_summary(spec, market, questions, lang)
    w = TEXT["ar" if lang == "ar" else "en"]
    # English text keeps id-based labels (stable for the team and the factory side)
    names = {q.id: (label(q.id, q, spec, lang) if lang == "ar" else _humanize(q.id)) for q in questions}
    lines = [
        w["title"],
        f"{w['product']}: {s['product']} ({s['market']})",
        f"{w['total']}: {s['quantity'] if s['quantity'] is not None else w['not_set']}",
    ]
    if s["sizes"]:
        lines += ["", f"{w['sizes']}:"] + [f"  {size:<6} {qty}" for size, qty in s["sizes"].items()]
    details = [item for section in s["sections"] for item in section["items"]]
    if details:
        lines += ["", f"{w['details']}:"] + [f"- {names.get(i['id'], i['label'])}: {i['value']}" for i in details]
    if s["extras"]:
        lines += ["", f"{w['extra']}:"] + [f"- {i['label']}: {i['value']}" for i in s["extras"]]
    if s["files"]:
        lines += ["", f"{w['files']}:"] + [f"- {f['kind']}: {f['url']}" for f in s["files"]]
    if s["open_gaps"]:
        lines += ["", f"{w['open']}:"] + [f"- {gap}" for gap in s["open_gaps"]]
    return "\n".join(lines)
