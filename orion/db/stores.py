"""Business data the team and stats page query: manufacturers, price dataset, message log.

Each store is a Protocol with an in-memory implementation (tests, quick local runs);
Postgres implementations live in orion/db/postgres.py.
"""

from typing import Any, Literal, Optional, Protocol

from pydantic import BaseModel

from orion.tools.channel import OutgoingMessage
from orion.tools.prices import PriceStatus


class Manufacturer(BaseModel):
    id: str
    name: str
    contact: Optional[str] = None
    channel: str = "manual_relay"
    language: str = "zh"


class PriceRecord(BaseModel):
    source_key: str                     # "<event_id>:<n>", unique: the same quote is never recorded twice
    manufacturer_id: str
    order_id: Optional[str]
    market: str
    option: str
    attributes: dict[str, Any]          # key spec attributes the price depends on
    quantity: Optional[int]
    unit_price: float
    currency: Optional[str]
    unit: str
    incoterm: Optional[str]
    shipping_included: Optional[bool]
    tax_included: Optional[bool]
    source: Literal["order", "weekly_check"]
    source_message_id: str
    quoted_text: str
    original_text: str
    status: PriceStatus
    problems: list[str] = []


class ManufacturerDirectory(Protocol):
    async def ranked_for(self, market: str, option: str) -> list[Manufacturer]: ...


class PriceStore(Protocol):
    async def append(self, record: PriceRecord) -> bool: ...   # False if already recorded


# --- in-memory implementations ------------------------------------------------------

class InMemoryDirectory:
    def __init__(self, ranked: dict[tuple[str, Optional[str]], list[Manufacturer]]):
        """`ranked` maps (market, option) to an ordered list; option None means any option in the market."""
        self.ranked = ranked

    async def ranked_for(self, market: str, option: str) -> list[Manufacturer]:
        specific = self.ranked.get((market, option), [])
        general = [m for m in self.ranked.get((market, None), []) if m not in specific]
        return specific + general


class InMemoryPriceStore:
    def __init__(self):
        self.records: dict[str, PriceRecord] = {}

    async def append(self, record: PriceRecord) -> bool:
        if record.source_key in self.records:
            return False
        self.records[record.source_key] = record
        return True


class InMemoryOutbox:
    """Manual relay channel kept in memory: a list a human would copy messages from."""

    def __init__(self):
        self.messages: dict[str, dict] = {}

    async def deliver(self, message: OutgoingMessage) -> None:
        self.messages.setdefault(message.id, {**message.model_dump(), "direction": "out", "status": "pending_send"})

    async def record_blocked(self, message: OutgoingMessage, reason: str) -> None:
        self.messages.setdefault(
            message.id, {**message.model_dump(), "direction": "out", "status": "blocked", "reason": reason}
        )

    async def record_incoming(self, message_id: str, order_id: str, manufacturer_id: str, text: str) -> None:
        self.messages.setdefault(message_id, {
            "id": message_id, "order_id": order_id, "manufacturer_id": manufacturer_id,
            "text": text, "direction": "in", "status": "received",
        })

    def pending(self) -> list[dict]:
        return [m for m in self.messages.values() if m["status"] == "pending_send"]
