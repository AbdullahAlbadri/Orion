"""Login routes: email one-time code (or link), Google / Apple ID token, refresh, logout, me."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr

from orion.api.context import ApiContext, ctx, current_customer
from orion.api.security import (
    ACCESS_TTL,
    CODES_PER_HOUR,
    REFRESH_TTL,
    Audience,
    TokenClaims,
    hash_login_code,
    issue_access_token,
    new_login_code,
    normalize_email,
)
from orion.db.accounts import RefreshReuse

log = logging.getLogger("orion.api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


def cookie_name(audience: Audience) -> str:
    return f"orion_refresh_{audience}"


class EmailStart(BaseModel):
    email: EmailStr
    audience: Audience = "customer"


class EmailVerify(BaseModel):
    email: EmailStr
    code: str
    audience: Audience = "customer"


class IdTokenLogin(BaseModel):
    id_token: str


class RefreshRequest(BaseModel):
    audience: Audience = "customer"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


async def _session(c: ApiContext, response: Response, audience: Audience, user: dict) -> TokenResponse:
    """Issue an access token and set the rotating refresh cookie."""
    subject = str(user["id"])
    claims = TokenClaims(sub=subject, aud=audience, role=user.get("role"), email=user["email"])
    refresh = await c.accounts.issue_refresh(subject, audience)
    _set_refresh_cookie(c, response, audience, refresh)
    await c.accounts.touch_login(audience, subject)
    return TokenResponse(
        access_token=issue_access_token(c.jwt_secret, claims),
        expires_in=int(ACCESS_TTL.total_seconds()),
        user={"id": subject, "email": user["email"], "name": user.get("name"), "role": user.get("role")},
    )


def _set_refresh_cookie(c: ApiContext, response: Response, audience: Audience, token: str) -> None:
    response.set_cookie(
        cookie_name(audience), token,
        max_age=int(REFRESH_TTL[audience].total_seconds()),
        httponly=True, secure=c.settings.cookie_secure, samesite="lax", path="/auth",
    )


@router.post("/email/start", status_code=status.HTTP_202_ACCEPTED)
async def email_start(body: EmailStart, c: ApiContext = Depends(ctx)) -> dict:
    """Send a one-time code. Always answers the same way, so it never reveals who has an account."""
    email = normalize_email(body.email)
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    if await c.accounts.codes_sent_since(email, body.audience, since) >= CODES_PER_HOUR:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many codes requested, try again later")

    if body.audience == "team" and not await c.accounts.team_member_by_email(email):
        log.info("team login requested for unknown email")
        return {"sent": True}

    code = new_login_code()
    await c.accounts.save_code(email, body.audience, hash_login_code(c.code_secret, email, body.audience, code))
    link = f"{c.settings.app_base_url}/login/verify?{urlencode({'email': email, 'code': code})}"
    await c.email.send(
        email,
        f"Your Orion login code: {code}",
        f"Your Orion login code is {code}\nرمز الدخول إلى أوريون: {code}\n\n"
        f"Or open this link: {link}\n\nThe code expires in 10 minutes. If you did not ask for it, ignore this email.",
    )
    return {"sent": True}


@router.post("/email/verify")
async def email_verify(body: EmailVerify, response: Response, c: ApiContext = Depends(ctx)) -> TokenResponse:
    if not await c.accounts.consume_code(c.code_secret, body.email, body.audience, body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired code")
    if body.audience == "team":
        user = await c.accounts.team_member_by_email(body.email)
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired code")
    else:
        user = await c.accounts.customer_by_email(body.email, create=True)
    return await _session(c, response, body.audience, user)


async def _id_token_login(provider: str, body: IdTokenLogin, response: Response, c: ApiContext) -> TokenResponse:
    verifier = c.verifiers.get(provider)
    if verifier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{provider} sign-in is not configured")
    try:
        identity = await verifier.verify(body.id_token)
    except Exception as e:
        log.warning("%s sign-in rejected: %s: %s", provider, type(e).__name__, e)   # the reason, never the token
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid {provider} token") from None
    if not identity.email or not identity.email_verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"{provider} account has no verified email")
    user = await c.accounts.customer_from_identity(provider, identity.subject, identity.email, identity.name)
    return await _session(c, response, "customer", user)


@router.post("/google")
async def google_login(body: IdTokenLogin, response: Response, c: ApiContext = Depends(ctx)) -> TokenResponse:
    return await _id_token_login("google", body, response, c)


@router.post("/apple")
async def apple_login(body: IdTokenLogin, response: Response, c: ApiContext = Depends(ctx)) -> TokenResponse:
    return await _id_token_login("apple", body, response, c)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest, request: Request, response: Response, c: ApiContext = Depends(ctx)
) -> TokenResponse:
    token = request.cookies.get(cookie_name(body.audience))
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no session")
    try:
        subject, new_token = await c.accounts.rotate_refresh(token, body.audience)
    except RefreshReuse as e:
        log.warning("refresh token reuse for %s %s: all sessions revoked", body.audience, e)
        response.delete_cookie(cookie_name(body.audience), path="/auth")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session expired, please log in again") from None
    except LookupError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session expired, please log in again") from None

    user = await (c.accounts.customer(subject) if body.audience == "customer" else c.accounts.team_member(subject))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "account not found")
    _set_refresh_cookie(c, response, body.audience, new_token)
    claims = TokenClaims(sub=subject, aud=body.audience, role=user.get("role"), email=user["email"])
    return TokenResponse(
        access_token=issue_access_token(c.jwt_secret, claims),
        expires_in=int(ACCESS_TTL.total_seconds()),
        user={"id": subject, "email": user["email"], "name": user.get("name"), "role": user.get("role")},
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, request: Request, response: Response, c: ApiContext = Depends(ctx)) -> None:
    token: Optional[str] = request.cookies.get(cookie_name(body.audience))
    if token:
        await c.accounts.revoke_refresh(token)
    response.delete_cookie(cookie_name(body.audience), path="/auth")


@router.get("/me")
async def me(claims: TokenClaims = Depends(current_customer)) -> dict:
    return {"id": claims.sub, "email": claims.email}
