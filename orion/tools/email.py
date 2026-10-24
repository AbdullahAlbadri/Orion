"""Outgoing email to customers and team. Console sender until an email service is chosen."""

import logging
from typing import Protocol

log = logging.getLogger("orion.email")


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, text: str) -> None: ...


class ConsoleEmailSender:
    """Prints emails instead of sending them (development). Keeps them for tests."""

    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, to: str, subject: str, text: str) -> None:
        self.sent.append({"to": to, "subject": subject, "text": text})
        log.warning("EMAIL (not sent, console mode) to=%s subject=%s\n%s", to, subject, text)
