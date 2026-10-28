"""WeCom (企业微信) "WeChat Customer Service" (微信客服) client: the official way to talk to people on WeChat.

How it works, checked against developer.work.weixin.qq.com:
- A person starts a conversation by opening the customer-service account's link. Orion can only reply after that.
- After each message from them there is a 48-hour window in which Orion may send up to 5 messages (2048 bytes each).
- WeCom calls our callback URL with an encrypted, signed event; the event carries no text. We pull the messages
  with `sync_msg`.
Messages Orion sends can't be read back through the API, so Orion records them itself.
"""

import base64
import hashlib
import hmac
import logging
import struct
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

import httpx
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

log = logging.getLogger("orion.wecom")

API = "https://qyapi.weixin.qq.com/cgi-bin"
MAX_TEXT_BYTES = 2000        # the API allows 2048 and truncates beyond it
MAX_MESSAGES = 5             # per 48-hour window


class WeComError(Exception):
    pass


class BadSignature(WeComError):
    pass


# --- callback signature and encryption (the scheme WeCom uses for every callback) ---------------------------------

def signature(token: str, timestamp: str, nonce: str, encrypted: str) -> str:
    return hashlib.sha1("".join(sorted([token, timestamp, nonce, encrypted])).encode()).hexdigest()


class CallbackCrypto:
    """Checks callback signatures and decrypts callback payloads. `encoding_aes_key` is the 43-character key
    from the WeCom console; the payload is AES-256-CBC with the key's first 16 bytes as IV."""

    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.token, self.corp_id = token, corp_id
        self.key = base64.b64decode(encoding_aes_key + "=")
        if len(self.key) != 32:
            raise ValueError("EncodingAESKey must be 43 characters")

    def verify(self, msg_signature: str, timestamp: str, nonce: str, encrypted: str) -> None:
        if not hmac.compare_digest(signature(self.token, timestamp, nonce, encrypted), msg_signature):
            raise BadSignature("callback signature does not match")

    def decrypt(self, encrypted: str) -> str:
        try:
            raw = Cipher(algorithms.AES(self.key), modes.CBC(self.key[:16])).decryptor()
            data = raw.update(base64.b64decode(encrypted)) + raw.finalize()
            unpadder = padding.PKCS7(256).unpadder()
            data = unpadder.update(data) + unpadder.finalize()
            length = struct.unpack(">I", data[16:20])[0]
            message, receiver = data[20:20 + length], data[20 + length:].decode()
        except Exception as e:
            raise BadSignature("callback payload can't be decrypted") from e
        if receiver != self.corp_id:
            raise BadSignature("callback is for a different company")
        return message.decode()

    def encrypt(self, text: str, random16: bytes = b"0123456789abcdef") -> str:
        """Used by tests (and passive replies): the inverse of `decrypt`."""
        body = random16 + struct.pack(">I", len(text.encode())) + text.encode() + self.corp_id.encode()
        padder = padding.PKCS7(256).padder()
        enc = Cipher(algorithms.AES(self.key), modes.CBC(self.key[:16])).encryptor()
        return base64.b64encode(enc.update(padder.update(body) + padder.finalize()) + enc.finalize()).decode()

    def open_post(self, body: bytes, msg_signature: str, timestamp: str, nonce: str) -> dict[str, str]:
        """A callback POST: the signed envelope in, the decrypted event's fields out."""
        encrypted = _fields(body).get("Encrypt", "")
        self.verify(msg_signature, timestamp, nonce, encrypted)
        return _fields(self.decrypt(encrypted).encode())


def _fields(xml: bytes) -> dict[str, str]:
    """The flat fields of a WeCom XML message. Documents that declare entities or DTDs are refused."""
    if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
        raise BadSignature("unexpected XML")
    try:
        return {child.tag: (child.text or "") for child in ET.fromstring(xml)}
    except ET.ParseError as e:
        raise BadSignature("not valid XML") from e


# --- text limits ---------------------------------------------------------------------------------------------------

def split_text(text: str, limit: int = MAX_TEXT_BYTES) -> list[str]:
    """Pieces of at most `limit` UTF-8 bytes, cut at a line break when there is one, never inside a character."""
    pieces, rest = [], text.strip()
    while rest:
        if len(rest.encode()) <= limit:
            pieces.append(rest)
            break
        cut = len(rest.encode()[:limit].decode(errors="ignore"))
        newline = rest.rfind("\n", 0, cut)
        cut = newline if newline > cut // 2 else cut
        pieces.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    return pieces


# --- the API ------------------------------------------------------------------------------------------------------

@dataclass
class Incoming:
    msgid: str
    open_kfid: str
    external_userid: str
    send_time: int
    msgtype: str
    text: str            # for text messages; empty for other kinds
    scene: str = ""      # for the "entered the conversation" event: the scene value of the link they opened


class WeComClient:
    def __init__(self, corp_id: str, secret: str, open_kfid: str, http: Optional[httpx.AsyncClient] = None):
        self.corp_id, self._secret, self.open_kfid = corp_id, secret, open_kfid
        self._http = http or httpx.AsyncClient(timeout=20)
        self._token, self._token_until = "", 0.0

    async def _access_token(self, refresh: bool = False) -> str:
        if refresh or time.monotonic() >= self._token_until:
            data = (await self._http.get(f"{API}/gettoken", params={"corpid": self.corp_id, "corpsecret": self._secret})).json()
            if data.get("errcode") != 0:
                raise WeComError(f"gettoken failed: {data.get('errcode')} {data.get('errmsg')}")
            self._token = data["access_token"]
            self._token_until = time.monotonic() + max(60, int(data.get("expires_in", 7200)) - 300)
        return self._token

    async def _post(self, path: str, body: dict) -> dict:
        for attempt in (0, 1):
            token = await self._access_token(refresh=attempt == 1)
            data = (await self._http.post(f"{API}/{path}", params={"access_token": token}, json=body)).json()
            if data.get("errcode") in (40014, 42001) and attempt == 0:      # token invalid or expired: get a new one
                continue
            if data.get("errcode") != 0:
                raise WeComError(f"{path} failed: {data.get('errcode')} {data.get('errmsg')}")
            return data
        raise WeComError(f"{path} failed")

    async def send_text(self, external_userid: str, text: str, msgid: str) -> str:
        """One text message (at most 2048 bytes). `msgid` must be unique for the account, so a retry is not sent twice."""
        data = await self._post("kf/send_msg", {
            "touser": external_userid, "open_kfid": self.open_kfid, "msgid": msgid, "msgtype": "text",
            "text": {"content": text},
        })
        return data.get("msgid", msgid)

    async def pull(self, cursor: str = "", token: str = "") -> tuple[list[Incoming], str]:
        """Everything new since `cursor` as (messages from people, the cursor to save). Keeps pulling while has_more."""
        out: list[Incoming] = []
        while True:
            body = {"open_kfid": self.open_kfid, "limit": 1000, **({"cursor": cursor} if cursor else {}),
                    **({"token": token} if token else {})}
            data = await self._post("kf/sync_msg", body)
            for m in data.get("msg_list", []):
                if m.get("origin") == 3 or (m.get("msgtype") == "event" and m.get("event", {}).get("event_type") == "enter_session"):
                    event = m.get("event") or {}
                    out.append(Incoming(
                        msgid=m["msgid"], open_kfid=m.get("open_kfid") or event.get("open_kfid", ""),
                        external_userid=m.get("external_userid") or event.get("external_userid", ""),
                        send_time=int(m.get("send_time", 0)), msgtype=m["msgtype"],
                        text=(m.get("text") or {}).get("content", "") if m["msgtype"] == "text" else "",
                        scene=event.get("scene", ""),
                    ))
            cursor = data.get("next_cursor", cursor)
            if not data.get("has_more"):
                return out, cursor
