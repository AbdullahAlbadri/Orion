"""Manufacturer channel interface. Implementations: manual relay (now), email and WeCom (later).

`send_to_manufacturer` is the only way nodes send anything, so the price guard cannot be skipped.
"""

from typing import Protocol

from pydantic import BaseModel

from orion.tools.price_guard import price_violation


class OutgoingMessage(BaseModel):
    id: str                 # deterministic, so a retried send is a no-op
    order_id: str
    manufacturer_id: str
    text: str


class Channel(Protocol):
    async def deliver(self, message: OutgoingMessage) -> None: ...

    async def record_blocked(self, message: OutgoingMessage, reason: str) -> None: ...

    async def record_incoming(self, message_id: str, order_id: str, manufacturer_id: str, text: str) -> None: ...


class BlockedMessage(Exception):
    pass


async def send_to_manufacturer(channel: Channel, message: OutgoingMessage) -> None:
    if reason := price_violation(message.text):
        await channel.record_blocked(message, reason)
        raise BlockedMessage(reason)
    await channel.deliver(message)
