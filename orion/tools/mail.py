"""Manufacturer email: send through SMTP, read replies through IMAP (Gmail with an app password for now).

Replies are matched to an order by the tag in the subject ("[ord_...]", kept by every mail client's
"Re:") and to a manufacturer by the sender address. Email is untrusted input: the text only ever reaches
the graph as a manufacturer_reply event, the same path as a reply a team member pastes.
"""

import asyncio
import email
import html
import imaplib
import logging
import re
import smtplib
import socket
import ssl
from contextlib import contextmanager
from dataclasses import dataclass
from email.message import EmailMessage
from email.policy import default as default_policy
from email.utils import formataddr, make_msgid, parseaddr
from typing import Optional, Protocol

log = logging.getLogger("orion.mail")

MAX_TEXT = 8000                     # longer replies are cut; the full mail stays in the mailbox
TAG = re.compile(r"\[(ord_[0-9a-f]{12})\]")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Where the quoted earlier conversation starts in a reply (Gmail, Outlook, QQ / 163 mail, English and Chinese)
QUOTE_START = re.compile(
    r"^(On [^\n]*(\n[^\n]*)?wrote:\s*$"
    r"|.*写道[:：]\s*$"
    r"|-{2,}.*(Original Message|原始邮件).*$"
    r"|(From|发件人)[:：].*$)",
    re.MULTILINE,
)


def subject_for(order_id: str) -> str:
    return f"Orion 询价 / Quote request [{order_id}]"


def order_tag(subject: str) -> Optional[str]:
    match = TAG.search(subject or "")
    return match.group(1) if match else None


def is_email(value: Optional[str]) -> bool:
    return bool(value and EMAIL.match(value.strip()))


def reply_text(body: str) -> str:
    """The new part of a reply: quoted history and '>' lines removed, cut to MAX_TEXT."""
    match = QUOTE_START.search(body)
    if match:
        body = body[:match.start()]
    lines = [line for line in body.splitlines() if not line.lstrip().startswith(">")]
    return "\n".join(lines).strip()[:MAX_TEXT]


def body_text(msg: EmailMessage) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    content = part.get_content()
    if part.get_content_type() == "text/html":
        content = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", content)
        content = html.unescape(re.sub(r"<[^>]+>", "", content))
    return content.replace("\xa0", " ")


def authenticated(msg: EmailMessage) -> bool:
    """The receiving server's own check of the sender (the first Authentication-Results header is the one
    our mail server added). A forged From address fails SPF and DKIM."""
    results = (msg.get_all("Authentication-Results") or [""])[0].lower()
    return any(check in results for check in ("dmarc=pass", "dkim=pass", "spf=pass"))


@dataclass
class IncomingMail:
    uid: str
    message_id: str
    sender: str          # address only, lower case
    subject: str
    text: str            # the reply itself, without the quoted history
    authenticated: bool


def parse(uid: str, raw: bytes) -> IncomingMail:
    msg = email.message_from_bytes(raw, policy=default_policy)
    return IncomingMail(
        uid=uid,
        message_id=str(msg.get("Message-ID") or f"uid-{uid}").strip(),
        sender=parseaddr(str(msg.get("From") or ""))[1].lower(),
        subject=str(msg.get("Subject") or ""),
        text=reply_text(body_text(msg)),
        authenticated=authenticated(msg),
    )


Attachment = tuple[str, bytes, str]   # (file name, content, content type)


class Mailer(Protocol):
    async def send(self, to: str, subject: str, text: str, attachments: list[Attachment] = ()) -> None: ...


class Inbox(Protocol):
    async def unread(self, limit: int = 20) -> list[IncomingMail]: ...

    async def done(self, uid: str, flag: bool = False) -> None: ...   # mark read; flag = star it for the team


def _connect_ipv4(host: str, port: int, timeout: float) -> socket.socket:
    """Connect over IPv4 only. The server's containers have no IPv6 route, and Gmail's address list starts with
    IPv6, which made every connection fail with "Network is unreachable"."""
    last: Exception = OSError(f"no IPv4 address for {host}")
    for *_, address in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
        try:
            return socket.create_connection(address, timeout)
        except OSError as e:
            last = e
    raise last


class _SMTP4(smtplib.SMTP_SSL):
    def _get_socket(self, host, port, timeout):
        return self.context.wrap_socket(_connect_ipv4(host, port, timeout), server_hostname=self._host)


class _SMTPStartTLS(smtplib.SMTP):
    """Port 587: connect in the clear, then upgrade (STARTTLS). Hetzner blocks outgoing port 465."""

    def _get_socket(self, host, port, timeout):
        return _connect_ipv4(host, port, timeout)


@contextmanager
def _smtp(host: str, port: int):
    """A logged-out SMTP connection: implicit TLS on 465, STARTTLS on anything else (587)."""
    if port == 465:
        with _SMTP4(host, port, timeout=30) as smtp:
            yield smtp
    else:
        with _SMTPStartTLS(host, port, timeout=30) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            yield smtp


class _IMAP4(imaplib.IMAP4_SSL):
    def _create_socket(self, timeout):
        return self.ssl_context.wrap_socket(_connect_ipv4(self.host, self.port, timeout or 30), server_hostname=self.host)


class GmailMailbox:
    """SMTP + IMAP on one mailbox. The blocking libraries run in a thread."""

    def __init__(self, address: str, app_password: str, smtp_host: str, smtp_port: int, imap_host: str):
        self.address, self._password = address, app_password
        self.smtp_host, self.smtp_port, self.imap_host = smtp_host, smtp_port, imap_host

    async def send(self, to: str, subject: str, text: str, attachments: list[Attachment] = ()) -> None:
        msg = EmailMessage()
        msg["From"] = formataddr(("Orion", self.address))
        msg["To"] = to
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid(domain=self.address.split("@")[-1])
        msg.set_content(text)
        for name, data, content_type in attachments:
            maintype, _, subtype = content_type.partition("/")
            msg.add_attachment(data, maintype=maintype or "application", subtype=subtype or "octet-stream", filename=name)
        await asyncio.to_thread(self._send, msg)

    def _send(self, msg: EmailMessage) -> None:
        with _smtp(self.smtp_host, self.smtp_port) as smtp:
            smtp.login(self.address, self._password)
            smtp.send_message(msg)

    async def check(self) -> str:
        """Log in to both servers without sending or reading anything."""
        return await asyncio.to_thread(self._check)

    def _check(self) -> str:
        with _smtp(self.smtp_host, self.smtp_port) as smtp:
            smtp.login(self.address, self._password)
        imap = self._imap()
        try:
            _, data = imap.uid("SEARCH", None, "UNSEEN")
        finally:
            imap.logout()
        return f"{self.address}: sending and reading work, {len(data[0].split())} unread"

    async def unread(self, limit: int = 20) -> list[IncomingMail]:
        return await asyncio.to_thread(self._unread, limit)

    def _imap(self) -> imaplib.IMAP4_SSL:
        imap = _IMAP4(self.imap_host, timeout=30)
        imap.login(self.address, self._password)
        imap.select("INBOX")
        return imap

    def _unread(self, limit: int) -> list[IncomingMail]:
        imap = self._imap()
        try:
            _, data = imap.uid("SEARCH", None, "UNSEEN")
            mails = []
            for uid in data[0].split()[:limit]:
                _, parts = imap.uid("FETCH", uid, "(BODY.PEEK[])")   # PEEK: stays unread until handled
                raw = next((p[1] for p in parts if isinstance(p, tuple)), None)
                if raw:
                    mails.append(parse(uid.decode(), raw))
            return mails
        finally:
            imap.logout()

    async def done(self, uid: str, flag: bool = False) -> None:
        await asyncio.to_thread(self._done, uid, flag)

    def _done(self, uid: str, flag: bool) -> None:
        imap = self._imap()
        try:
            imap.uid("STORE", uid, "+FLAGS", r"(\Seen \Flagged)" if flag else r"(\Seen)")
        finally:
            imap.logout()
