"""Product spec schema: the structured source of truth for an order.

Receipts, translations and manufacturer checks all read from ProductSpec,
never from chat history.
"""

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

QuestionType = Literal["choice", "number", "text", "file", "size_table"]
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


def validate_answer(question: Question, raw: Any) -> Any:
    """Coerce a raw answer (from a form or the LLM) into the question's type, or raise InvalidAnswer."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise InvalidAnswer("an answer is required")

    if question.type == "choice":
        value = str(raw).strip()
        for choice in question.choices:
            if value.lower() == choice.lower():
                return choice
        raise InvalidAnswer(f"must be one of: {', '.join(question.choices)}")

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

    # text and file (file is a reference/URL until object storage exists)
    return str(raw).strip()


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
