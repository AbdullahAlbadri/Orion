"""Verify Google / Apple ID tokens (signed JWTs from the provider's sign-in button)."""

import asyncio
from typing import Optional, Protocol

import jwt
from pydantic import BaseModel


class Identity(BaseModel):
    provider: str
    subject: str            # stable user id at the provider
    email: Optional[str]
    email_verified: bool
    name: Optional[str] = None


class IdTokenVerifier(Protocol):
    async def verify(self, id_token: str) -> Identity: ...


class OidcVerifier:
    def __init__(self, provider: str, jwks_url: str, issuers: list[str], client_id: str):
        self.provider, self.issuers, self.client_id = provider, issuers, client_id
        self._jwks = jwt.PyJWKClient(jwks_url, cache_keys=True)

    def _verify(self, id_token: str) -> Identity:
        key = self._jwks.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token, key.key, algorithms=["RS256", "ES256"], audience=self.client_id,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
        if claims["iss"] not in self.issuers:
            raise jwt.InvalidIssuerError(f"unexpected issuer {claims['iss']}")
        verified = claims.get("email_verified") in (True, "true")
        return Identity(
            provider=self.provider, subject=claims["sub"], email=claims.get("email"),
            email_verified=verified, name=claims.get("name"),
        )

    async def verify(self, id_token: str) -> Identity:
        # PyJWKClient fetches keys over the network (cached); keep it off the event loop
        return await asyncio.to_thread(self._verify, id_token)


def google_verifier(client_id: str) -> OidcVerifier:
    return OidcVerifier(
        "google", "https://www.googleapis.com/oauth2/v3/certs",
        ["https://accounts.google.com", "accounts.google.com"], client_id,
    )


def apple_verifier(client_id: str) -> OidcVerifier:
    return OidcVerifier("apple", "https://appleid.apple.com/auth/keys", ["https://appleid.apple.com"], client_id)
