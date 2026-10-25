"""Product spec schema: the structured source of truth for an order.

Receipts, translations and manufacturer checks all read from ProductSpec,
never from chat history.
"""

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

QuestionType = Literal["choice", "number", "text", "file", "size_table", "placement"]
# Form sections shown to the customer (one tab each)
Section = Literal["design", "quantity", "quality"]

# Question ids with special meaning in the spec (everything else lives in `answers`)
QUANTITY_ID = "quantity"
SIZE_TABLE_ID = "size_breakdown"


class Question(BaseModel):
    id: str
    prompt: str
    type: QuestionType
    choices: list[str] = []
    required: bool = True
    hint: Optional[str] = None
    section: Section = "design"
    allow_other: bool = False      # choice: the customer may type their own answer ("Other")
    multiple: bool = False         # choice: the customer may pick several (answer is a list)
    mockup: Optional[str] = None   # placement: garment drawing to place logos/labels on (set per product)


class FileRef(BaseModel):
    url: str
    kind: Literal["image", "document"]
    note: Optional[str] = None
    extracted: dict[str, Any] = {}


class ProductSpec(BaseModel):
    market: str
    option: str                    # option id or "custom"
    quantity: Optional[int] = None
    answers: dict[str, Any] = {}   # question id -> answer
    files: list[FileRef] = []
    open_gaps: list[str] = []
    version: int = 1
    frozen: bool = False

    def set_answer(self, question_id: str, value: Any) -> None:
        self.answers[question_id] = value
        if question_id == QUANTITY_ID:
            self.quantity = value
        elif question_id == SIZE_TABLE_ID:
            self.quantity = sum(value.values())


class InvalidAnswer(ValueError):
    pass


MAX_OTHER_LENGTH = 300


def is_blank(raw: Any) -> bool:
    return raw is None or (isinstance(raw, str) and not raw.strip()) or (isinstance(raw, (list, dict)) and not raw)


def format_answer(value: Any) -> str:
    """Human-readable answer for receipts and messages."""
    if isinstance(value, list) and value and all(isinstance(v, dict) and "view" in v for v in value):
        return "; ".join(describe_placement(v) for v in value)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


def validate_answer(question: Question, raw: Any) -> Any:
    """Coerce a raw answer (from a form or the LLM) into the question's type, or raise InvalidAnswer."""
    if is_blank(raw):
        raise InvalidAnswer("an answer is required")

    if question.type == "choice":
        return _validate_choice(question, raw)

    if question.type == "number":
        try:
            number = float(str(raw).replace(",", "").strip())
        except ValueError:
            raise InvalidAnswer("must be a number") from None
        if number <= 0:
            raise InvalidAnswer("must be greater than zero")
        return int(number) if number.is_integer() else number

    if question.type == "size_table":
        return _parse_size_table(raw)

    if question.type == "placement":
        return _validate_placements(raw)

    # text and file (file is a reference/URL until object storage exists)
    return str(raw).strip()


def _validate_choice(question: Question, raw: Any) -> Any:
    """A known choice (canonical spelling), or the customer's own text when "Other" is allowed.
    Multiple-choice answers are lists; a string is split on commas (LLM updates)."""
    if isinstance(raw, list):
        items = raw
    elif question.multiple:
        items = str(raw).split(",")
    else:
        items = [raw]

    picked: list[str] = []
    for item in items:
        value = str(item).strip()
        if not value:
            continue
        match = next((c for c in question.choices if c.lower() == value.lower()), None)
        if match is None:
            if not question.allow_other:
                raise InvalidAnswer(f"must be one of: {', '.join(question.choices)}")
            match = value[:MAX_OTHER_LENGTH]
        if match not in picked:
            picked.append(match)
    if not picked:
        raise InvalidAnswer("an answer is required")
    if not question.multiple and len(picked) > 1:
        raise InvalidAnswer("pick one option")
    return picked if question.multiple else picked[0]


MAX_PLACEMENTS = 10


def _validate_placements(raw: Any) -> Any:
    """Logos/labels placed on the garment drawing: [{kind, view, x, y, width_cm, height_cm}].
    x/y are the centre as a fraction of the drawing (0-1, as seen from the front of the picture).
    A plain text description is also accepted (terminal, AI updates)."""
    if isinstance(raw, str):
        return raw.strip()
    if not isinstance(raw, list) or not raw:
        raise InvalidAnswer("place at least one logo or label")
    if len(raw) > MAX_PLACEMENTS:
        raise InvalidAnswer(f"at most {MAX_PLACEMENTS} placements")
    out = []
    for item in raw:
        try:
            kind, view = str(item["kind"]), str(item["view"])
            x, y = float(item["x"]), float(item["y"])
            w, h = float(item["width_cm"]), float(item["height_cm"])
        except (KeyError, TypeError, ValueError):
            raise InvalidAnswer("each placement needs kind, view, position and size") from None
        if kind not in ("logo", "label") or view not in ("front", "back"):
            raise InvalidAnswer("unknown placement kind or view")
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise InvalidAnswer("placement is outside the garment")
        if not (0.5 <= w <= 60 and 0.5 <= h <= 60):
            raise InvalidAnswer("logo/label size must be between 0.5 and 60 cm")
        out.append({"kind": kind, "view": view, "x": round(x, 3), "y": round(y, 3),
                    "width_cm": round(w, 1), "height_cm": round(h, 1)})
    return out


def describe_placement(p: dict) -> str:
    """Words a factory understands. 'Left' means the wearer's left: on the front view that is the right
    side of the picture, on the back view the left side."""
    x, y = p["x"], p["y"]
    wearer_left = x > 0.56 if p["view"] == "front" else x < 0.44
    wearer_right = x < 0.44 if p["view"] == "front" else x > 0.56
    side = "wearer's left " if wearer_left else "wearer's right " if wearer_right else "centre "
    area = "neck" if y < 0.2 else "chest" if y < 0.42 else "middle" if y < 0.65 else "lower"
    return f"{p['kind']}, {p['view']}, {side}{area}, {p['width_cm']:g} x {p['height_cm']:g} cm"


_SIZE_PAIR = re.compile(r"^\s*([A-Za-z0-9/.\- ]+?)\s*[:=x×]\s*(\d+)\s*$")


def _parse_size_table(raw: Any) -> dict[str, int]:
    """Accept {"S": 20, "M": 30} or "S:20, M:30" and return {size: pieces}."""
    if isinstance(raw, dict):
        pairs = raw.items()
    else:
        pairs = []
        for part in re.split(r"[,\n;]", str(raw)):
            if not part.strip():
                continue
            match = _SIZE_PAIR.match(part)
            if not match:
                raise InvalidAnswer(f"could not read '{part.strip()}', use SIZE:QTY like 'M:50'")
            pairs.append((match.group(1), match.group(2)))

    table: dict[str, int] = {}
    for size, qty in pairs:
        size = str(size).strip().upper()
        try:
            count = int(qty)
        except (TypeError, ValueError):
            raise InvalidAnswer(f"quantity for {size} must be a whole number") from None
        if count < 0:
            raise InvalidAnswer(f"quantity for {size} cannot be negative")
        if count:
            table[size] = table.get(size, 0) + count
    if not table:
        raise InvalidAnswer("enter at least one size with a quantity")
    return table
