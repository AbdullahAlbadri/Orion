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
    multiline: bool = False        # text: a long answer (a description), shown as a large box
    # Offer the brand kit saved on the business profile here: its colours (choice) or its logos (file).
    # Only a suggestion; nothing is filled in until the customer taps it.
    brand: Optional[Literal["colors", "logo"]] = None
    # Arabic wording for the website. Answers are always stored with the English choice values.
    prompt_ar: Optional[str] = None
    hint_ar: Optional[str] = None
    choices_ar: list[str] = []     # same order as `choices`
    # Relative cost of each choice within this question: 0 = none shown, 1 = $, 2 = $$, 3 = $$$.
    # A hint set by the team in config, never an amount (prices only come from manufacturer quotes).
    cost_tiers: list[int] = []


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
    labels: dict[str, str] = {}    # question id -> wording, for questions the AI added (not in the config)
    sections: dict[str, str] = {}  # question id -> section, for questions the AI added
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
    if is_placement_list(value):
        return "; ".join(describe_placement(v) for v in value)
    if is_file_list(value):
        return ", ".join(v["name"] for v in value)
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

    if question.type == "file":
        return _validate_files(raw)

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


MAX_FILE_ANSWERS = 10


def _validate_files(raw: Any) -> Any:
    """Uploaded files: [{file_id, name, content_type}]. The API checks the ids belong to the order;
    here only the shape is checked. A plain link (older orders, terminal) is still accepted."""
    if isinstance(raw, str):
        return raw.strip()
    if not isinstance(raw, list) or not raw or len(raw) > MAX_FILE_ANSWERS:
        raise InvalidAnswer("upload at least one file")
    out = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("file_id"):
            raise InvalidAnswer("unknown file")
        out.append({"file_id": str(item["file_id"]), "name": str(item.get("name") or "file")[:200],
                    "content_type": str(item.get("content_type") or "")})
    return out


def is_file_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(v, dict) and "file_id" in v for v in value)


def is_placement_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(v, dict) and "view" in v for v in value)


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


_PLACEMENT_WORDS = {
    "en": {"logo": "logo", "label": "label", "front": "front", "back": "back", "left": "wearer's left ",
           "right": "wearer's right ", "centre": "centre ", "neck": "neck", "chest": "chest", "middle": "middle",
           "lower": "lower", "cm": "cm"},
    "ar": {"logo": "شعار", "label": "ملصق", "front": "الأمام", "back": "الخلف", "left": "يسار اللابس، ",
           "right": "يمين اللابس، ", "centre": "الوسط، ", "neck": "الرقبة", "chest": "الصدر", "middle": "المنتصف",
           "lower": "الأسفل", "cm": "سم"},
    "zh": {"logo": "Logo", "label": "标签", "front": "正面", "back": "背面", "left": "穿着者左侧",
           "right": "穿着者右侧", "centre": "居中", "neck": "领口", "chest": "胸部", "middle": "衣身中部",
           "lower": "下摆", "cm": "厘米"},
}


def describe_placement(p: dict, lang: str = "en") -> str:
    """Words a factory understands. 'Left' means the wearer's left: on the front view that is the right
    side of the picture, on the back view the left side."""
    w = _PLACEMENT_WORDS.get(lang, _PLACEMENT_WORDS["en"])
    x, y = p["x"], p["y"]
    wearer_left = x > 0.56 if p["view"] == "front" else x < 0.44
    wearer_right = x < 0.44 if p["view"] == "front" else x > 0.56
    side = w["left"] if wearer_left else w["right"] if wearer_right else w["centre"]
    area = w["neck"] if y < 0.2 else w["chest"] if y < 0.42 else w["middle"] if y < 0.65 else w["lower"]
    if lang == "zh":
        return f"{w[p['kind']]}：{w[p['view']]}{area}，{side}，宽 {p['width_cm']:g} × 高 {p['height_cm']:g} {w['cm']}"
    return f"{w[p['kind']]}, {w[p['view']]}, {side}{area}, {p['width_cm']:g} x {p['height_cm']:g} {w['cm']}"


def localize_answer(question: Optional[Question], value: Any, lang: str) -> str:
    """An answer in the customer's language: English choice values shown with their Arabic labels."""
    if lang == "ar" and question is not None:
        if is_placement_list(value):
            return "؛ ".join(describe_placement(v, "ar") for v in value)
        if question.choices_ar:
            names = dict(zip(question.choices, question.choices_ar))
            items = value if isinstance(value, list) else [value]
            return "، ".join(names.get(str(v), str(v)) for v in items)
    return format_answer(value)


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
