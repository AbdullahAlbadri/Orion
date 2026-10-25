"""Shared API state and the auth dependencies every route uses."""

from dataclasses import dataclass, field
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg_pool import AsyncConnectionPool

from orion.api.limits import SlidingWindowLimit
from orion.api.oidc import IdTokenVerifier
from orion.tools.assist import Assistant
from orion.tools.files import FileStore
from orion.api.security import InvalidToken, TokenClaims, decode_access_token
from orion.config.settings import Settings
from orion.db.accounts import AccountStore
from orion.db.inbox import InboxStore
from orion.db.products import ProductStore
from orion.db.profile import ProfileStore
from orion.deps import Deps
from orion.tools.email import EmailSender


@dataclass
class ApiContext:
    graph: object                  # compiled LangGraph app
    deps: Deps
    pool: AsyncConnectionPool
    settings: Settings
    accounts: AccountStore
    email: EmailSender
    verifiers: dict[str, IdTokenVerifier] = field(default_factory=dict)   # "google" / "apple" when configured
    assistant: Optional[Assistant] = None
    files: Optional[FileStore] = None
    assist_limit: SlidingWindowLimit = field(default_factory=lambda: SlidingWindowLimit(30, 3600))
    support_limit: SlidingWindowLimit = field(default_factory=lambda: SlidingWindowLimit(10, 3600))

    def __post_init__(self):
        self.profile = ProfileStore(self.pool)
        self.inbox = InboxStore(self.pool)
        self.products = ProductStore(self.pool)

    @property
    def jwt_secret(self) -> str:
        return self.settings.jwt_secret.get_secret_value()

    @property
    def code_secret(self) -> str:
        return self.settings.login_code_secret.get_secret_value()


def ctx(request: Request) -> ApiContext:
    return request.app.state.ctx


_bearer = HTTPBearer(auto_error=False)


def _claims(
    audience: str, request: Request, credentials: Optional[HTTPAuthorizationCredentials]
) -> TokenClaims:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        return decode_access_token(ctx(request).jwt_secret, credentials.credentials, audience)
    except InvalidToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token") from None


def current_customer(request: Request, credentials=Depends(_bearer)) -> TokenClaims:
    return _claims("customer", request, credentials)


ROLE_RANK = {"agent": 1, "admin": 2}


def team_member(min_role: str = "agent"):
    def dependency(request: Request, credentials=Depends(_bearer)) -> TokenClaims:
        claims = _claims("team", request, credentials)
        if ROLE_RANK.get(claims.role or "", 0) < ROLE_RANK[min_role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"requires role {min_role}")
        return claims
    return dependency
