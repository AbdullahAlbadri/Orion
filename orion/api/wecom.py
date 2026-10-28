"""WeCom callback URL. WeCom checks it when the URL is saved in its console (GET), then sends events to it (POST).
The events carry no message text; the worker pulls the messages (step: WeChat channel)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from orion.api.context import ApiContext, ctx
from orion.tools.wecom import BadSignature, CallbackCrypto

log = logging.getLogger("orion.wecom")
router = APIRouter(prefix="/webhooks/wecom", tags=["webhooks"])


def _crypto(c: ApiContext) -> CallbackCrypto:
    s = c.settings
    key = s.wecom_encoding_aes_key.get_secret_value()
    if not (s.wecom_corp_id and s.wecom_callback_token and key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")      # off until configured
    return CallbackCrypto(s.wecom_callback_token, key, s.wecom_corp_id)


@router.get("/callback", response_class=PlainTextResponse)
async def verify_url(msg_signature: str, timestamp: str, nonce: str, echostr: str, c: ApiContext = Depends(ctx)) -> str:
    """WeCom's URL check: prove we hold the token and key by returning the decrypted `echostr`."""
    crypto = _crypto(c)
    try:
        crypto.verify(msg_signature, timestamp, nonce, echostr)
        return crypto.decrypt(echostr)
    except BadSignature:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "bad signature") from None


@router.post("/callback", response_class=PlainTextResponse)
async def receive(request: Request, msg_signature: str, timestamp: str, nonce: str, c: ApiContext = Depends(ctx)) -> str:
    """An event. Only signed, decryptable events are accepted (rule 5: it is outside input)."""
    crypto = _crypto(c)
    try:
        event = crypto.open_post(await request.body(), msg_signature, timestamp, nonce)
    except BadSignature:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "bad signature") from None
    # TODO(step 7): kf_msg_or_event -> pull the messages and resume the order (worker)
    log.info("wecom event %s/%s", event.get("MsgType"), event.get("Event"))
    return "success"
