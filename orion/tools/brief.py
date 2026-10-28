"""The order brief: one Markdown file per order, written in code from the customer's answers, that tells the
image model exactly what to draw. Every answer is a numbered requirement, the product name is only a category, and
the model must check the list before finishing.
"""

from typing import Any

from orion.spec import Question, format_answer, is_file_list, is_placement_list

# Answers that don't change how the product looks
NOT_VISUAL = {"quantity", "size_breakdown", "size_standard", "needed_by", "sample", "packaging", "labels", "fit_reference"}
SECTIONS = {"design": "Design and construction", "quality": "Material and quality", "quantity": "Other details"}


def visual_answers(questions: list[Question], answers: dict[str, Any]) -> tuple[list[tuple[Question, str]], list[dict]]:
    """The answers that change how the product looks (question, plain text), and the placements."""
    rows, placements = [], []
    for q in questions:
        value = answers.get(q.id)
        if q.id in NOT_VISUAL or value in (None, "", []) or is_file_list(value) or q.type == "file":
            continue
        if is_placement_list(value):
            placements = value
            continue
        if q.type == "placement":
            continue
        rows.append((q, format_answer(value)[:200]))
    return rows, placements


def mockup_brief(product: str, questions: list[Question], answers: dict[str, Any]) -> tuple[str, bool]:
    """(the Markdown brief, whether it shows front and back)."""
    rows, placements = visual_answers(questions, answers)
    back = any(p.get("view") == "back" for p in placements)
    lines = [f"# Product brief: custom {product}", "",
             f"Draw ONE photorealistic e-commerce photo of this exact product: a plain, blank {product.lower()}.", "",
             "## Rules",
             f"- The name \"{product}\" is only a category. The requirements below are the product and OVERRIDE the "
             "name and your usual idea of it. If a requirement removes or changes a standard part (for example no "
             "hood, no zipper, a different neckline or sleeve), draw it changed or removed, never the usual version.",
             "- Follow every numbered requirement. Do not add, drop or change anything.",
             "- The garment is completely blank: no logo, no print, no embroidery, no text, no label, no pattern or "
             "graphic of any kind on the fabric (the customer's artwork is added afterwards).",
             "- When a requirement gives a colour for a part of the garment (body, sleeves, cuffs, hem, collar, hood...), "
             "that whole part is exactly that colour. The parts keep their natural shapes and seams.",
             "- No people, no hands, no extra props."]
    n = 0
    for section in ("design", "quality", "quantity"):
        group = [(q, v) for q, v in rows if q.section == section]
        if not group:
            continue
        lines += ["", f"## {SECTIONS[section]}"]
        for q, v in group:
            n += 1
            lines.append(f"{n}. **{q.id.replace('_', ' ').capitalize()}** ({q.prompt.rstrip('?؟:. ')}): {v}")
    lines += ["", "## Photo",
              ("- Show the front and back views side by side, each facing the camera straight on and centred in its "
               "own half of the picture." if back else
               "- Show the front view, facing the camera straight on and centred."),
              "- Invisible mannequin, seamless pure white studio background, soft even lighting.",
              "", "## Before you finish",
              f"Check the picture against requirements 1 to {n}. Redraw anything that does not match."]
    return "\n".join(lines) + "\n", back
