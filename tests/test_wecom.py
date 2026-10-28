"""WeCom customer-service channel: callback crypto, the callback URL, sending and pulling (no network)."""

import base64
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from orion.api import wecom as wecom_routes
from orion.api.context import ctx
from orion.config.settings import Settings
from orion.tools.wecom import BadSignature, CallbackCrypto, WeComClient, WeComError, signature, split_text

KEY = base64.b64encode(bytes(range(32))).decode().rstrip("=")      # a 43-character EncodingAESKey
TOKEN, CORP = "tok123", "ww_corp"


def crypto() -> CallbackCrypto:
    return CallbackCrypto(TOKEN, KEY, CORP)


def envelope(c: CallbackCrypto, inner: str, ts="1700000000", nonce="n1") -> tuple[bytes, dict]:
    encrypted = c.encrypt(inner)
    body = f"<xml><ToUserName>{CORP}</ToUserName><Encrypt>{encrypted}</Encrypt></xml>".encode()
    return body, {"msg_signature": signature(TOKEN, ts, nonce, encrypted), "timestamp": ts, "nonce": nonce}


def test_encrypt_then_decrypt_round_trips_chinese_text():
    c = crypto()
    assert c.decrypt(c.encrypt("你好 factory 😀")) == "你好 factory 😀"


def test_a_payload_for_another_company_is_refused():
    other = CallbackCrypto(TOKEN, KEY, "someone_else")
    with pytest.raises(BadSignature):
        crypto().decrypt(other.encrypt("hi"))


def test_a_wrong_signature_is_refused():
    body, q = envelope(crypto(), "<xml><Event>kf_msg_or_event</Event></xml>")
    with pytest.raises(BadSignature):
        crypto().open_post(body, "0" * 40, q["timestamp"], q["nonce"])


def test_xml_with_entities_is_refused():
    with pytest.raises(BadSignature):
        crypto().open_post(b'<!DOCTYPE x [<!ENTITY a "b">]><xml><Encrypt>&a;</Encrypt></xml>', "x", "1", "2")


def test_split_text_keeps_each_piece_under_the_byte_limit_and_loses_nothing():
    text = "\n".join(f"第{i}行：这是一个很长的中文句子，用来测试拆分。" for i in range(200))
    pieces = split_text(text, 500)
    assert len(pieces) > 1 and all(len(p.encode()) <= 500 for p in pieces)
    assert "".join(pieces).replace("\n", "") == text.replace("\n", "")
    assert split_text("short") == ["short"]


def app_for(settings: Settings) -> FastAPI:
    app = FastAPI()
    app.include_router(wecom_routes.router)
    app.dependency_overrides[ctx] = lambda: SimpleNamespace(settings=settings)
    return app


def settings(**extra) -> Settings:
    return Settings(openrouter_api_key="x", consultant_model="x", manufacturer_model="x", classifier_model="x",
                    database_url="postgresql://x", **extra)


async def call(app, method, path, **kw):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        return await client.request(method, path, **kw)


CONFIGURED = dict(wecom_corp_id=CORP, wecom_callback_token=TOKEN, wecom_encoding_aes_key=KEY)


async def test_the_callback_is_off_until_configured():
    assert (await call(app_for(settings()), "GET", "/webhooks/wecom/callback",
                       params={"msg_signature": "a", "timestamp": "1", "nonce": "2", "echostr": "x"})).status_code == 404


async def test_url_verification_returns_the_decrypted_echostr():
    c = crypto()
    echo = c.encrypt("1616140317555161061")
    r = await call(app_for(settings(**CONFIGURED)), "GET", "/webhooks/wecom/callback", params={
        "msg_signature": signature(TOKEN, "1", "2", echo), "timestamp": "1", "nonce": "2", "echostr": echo})
    assert r.status_code == 200 and r.text == "1616140317555161061"


async def test_url_verification_with_a_bad_signature_is_403():
    r = await call(app_for(settings(**CONFIGURED)), "GET", "/webhooks/wecom/callback", params={
        "msg_signature": "bad", "timestamp": "1", "nonce": "2", "echostr": crypto().encrypt("x")})
    assert r.status_code == 403


async def test_a_signed_event_is_accepted_and_an_unsigned_one_is_not():
    body, q = envelope(crypto(), "<xml><MsgType>event</MsgType><Event>kf_msg_or_event</Event><Token>t</Token></xml>")
    app = app_for(settings(**CONFIGURED))
    ok = await call(app, "POST", "/webhooks/wecom/callback", params=q, content=body)
    assert ok.status_code == 200 and ok.text == "success"
    bad = await call(app, "POST", "/webhooks/wecom/callback", params={**q, "msg_signature": "0" * 40}, content=body)
    assert bad.status_code == 403


def client_with(handler) -> WeComClient:
    return WeComClient(CORP, "secret", "kf1", httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def api_handler(calls: list, responses: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/cgi-bin/", 1)[1]
        calls.append((path, request.url.params.get("access_token"), request.content))
        return httpx.Response(200, json=responses[path].pop(0) if isinstance(responses[path], list) else responses[path])
    return handler


async def test_send_text_gets_a_token_once_and_posts_the_message():
    calls: list = []
    client = client_with(api_handler(calls, {"gettoken": {"errcode": 0, "access_token": "T1", "expires_in": 7200},
                                             "kf/send_msg": {"errcode": 0, "msgid": "m1"}}))
    await client.send_text("wm_factory", "你好", "m1")
    await client.send_text("wm_factory", "再见", "m2")
    assert [c[0] for c in calls] == ["gettoken", "kf/send_msg", "kf/send_msg"]
    assert calls[1][1] == "T1" and b'"touser":"wm_factory"' in calls[1][2].replace(b" ", b"") and b"kf1" in calls[1][2]


async def test_an_expired_token_is_refreshed_once():
    calls: list = []
    client = client_with(api_handler(calls, {
        "gettoken": [{"errcode": 0, "access_token": "old", "expires_in": 7200},
                     {"errcode": 0, "access_token": "new", "expires_in": 7200}],
        "kf/send_msg": [{"errcode": 42001, "errmsg": "expired"}, {"errcode": 0, "msgid": "m1"}]}))
    await client.send_text("u", "hi", "m1")
    assert [c[1] for c in calls if c[0] == "kf/send_msg"] == ["old", "new"]


async def test_an_api_error_is_raised():
    client = client_with(api_handler([], {"gettoken": {"errcode": 0, "access_token": "T", "expires_in": 7200},
                                          "kf/send_msg": {"errcode": 95001, "errmsg": "limit"}}))
    with pytest.raises(WeComError):
        await client.send_text("u", "hi", "m1")


async def test_pull_follows_has_more_and_keeps_only_messages_from_people():
    calls: list = []
    page1 = {"errcode": 0, "next_cursor": "c1", "has_more": 1, "msg_list": [
        {"msgid": "a", "origin": 3, "open_kfid": "kf1", "external_userid": "wm1", "send_time": 5, "msgtype": "text",
         "text": {"content": "报价 单价45元"}},
        {"msgid": "b", "origin": 5, "msgtype": "text", "text": {"content": "sent by staff"}}]}
    page2 = {"errcode": 0, "next_cursor": "c2", "has_more": 0, "msg_list": [
        {"msgid": "c", "msgtype": "event", "event": {"event_type": "enter_session", "open_kfid": "kf1",
                                                     "external_userid": "wm2", "scene": "factory-a"}}]}
    client = client_with(api_handler(calls, {"gettoken": {"errcode": 0, "access_token": "T", "expires_in": 7200},
                                             "kf/sync_msg": [page1, page2]}))
    messages, cursor = await client.pull("c0", token="cbtoken")
    assert cursor == "c2" and [m.msgid for m in messages] == ["a", "c"]
    assert messages[0].text == "报价 单价45元" and messages[1].scene == "factory-a" and messages[1].external_userid == "wm2"
