"""Login primitives: one-time codes, access tokens (JWT), refresh tokens. No passwords anywhere.

- Codes: 6 digits, stored only as an HMAC peppered with LOGIN_CODE_SECRET, short-lived, few attempts.
- Access tokens: HS256 JWT, 15 minutes, audience "customer" or "team".
- Refresh tokens: random, stored only as SHA-256, rotated on every use (see db/accounts.py).
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import jwt
from pydantic import BaseModel

Audience = Literal["customer", "team"]
ISSUER = "orion"
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = {"customer": timedelta(days=30), "team": timedelta(days=7)}
CODE_TTL = timedelta(minutes=10)
CODE_MAX_ATTEMPTS = 5
CODES_PER_HOUR = 5


class TokenClaims(BaseModel):
    sub: str
    aud: Audience
    role: Optional[str] = None
    email: str


class InvalidToken(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def new_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_login_code(secret: str, email: str, audience: Audience, code: str) -> str:
    message = f"{audience}\n{normalize_email(email)}\n{code.strip()}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def codes_match(expected_hash: str, secret: str, email: str, audience: Audience, code: str) -> bool:
    return hmac.compare_digest(expected_hash, hash_login_code(secret, email, audience, code))


def issue_access_token(secret: str, claims: TokenClaims, now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    payload = {**claims.model_dump(exclude_none=True), "iss": ISSUER, "iat": now, "exp": now + ACCESS_TTL}
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(secret: str, token: str, audience: Audience) -> TokenClaims:
    try:
        payload = jwt.decode(
            token, secret, algorithms=["HS256"], audience=audience, issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError as e:
        raise InvalidToken(str(e)) from None
    return TokenClaims(**{k: payload.get(k) for k in ("sub", "aud", "role", "email")})


def new_refresh_token() -> tuple[str, str]:
    """Returns (token for the cookie, hash for the database)."""
    token = secrets.token_urlsafe(32)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
