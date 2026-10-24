"""FastAPI app. Run locally with:  uv run python -m orion.api   (docs at http://localhost:8000/docs)"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orion.api import auth, orders, team
from orion.api.context import ApiContext
from orion.api.oidc import apple_verifier, google_verifier
from orion.config.settings import Settings, get_settings
from orion.db.accounts import AccountStore
from orion.runtime import open_postgres_app
from orion.tools.email import ConsoleEmailSender

log = logging.getLogger("orion.api")


def _check_secrets(settings: Settings) -> None:
    missing = [n for n in ("jwt_secret", "login_code_secret") if not getattr(settings, n).get_secret_value()]
    if missing:
        raise RuntimeError(f"Set {', '.join(m.upper() for m in missing)} in .env before starting the API")


def create_app(context: Optional[ApiContext] = None, settings: Optional[Settings] = None) -> FastAPI:
    """Pass `context` in tests; otherwise the app opens Postgres and the graph on startup."""
    settings = settings or (context.settings if context else get_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if context is not None:
            app.state.ctx = context
            yield
            return
        _check_secrets(settings)
        async with open_postgres_app(settings) as (graph, deps, pool):
            verifiers = {}
            if settings.google_client_id:
                verifiers["google"] = google_verifier(settings.google_client_id)
            if settings.apple_client_id:
                verifiers["apple"] = apple_verifier(settings.apple_client_id)
            # TODO(decide): email provider (Resend / Postmark / SES); console until then
            app.state.ctx = ApiContext(
                graph=graph, deps=deps, pool=pool, settings=settings,
                accounts=AccountStore(pool), email=ConsoleEmailSender(), verifiers=verifiers,
            )
            log.info("API ready (sign-in: email%s)", "".join(f", {p}" for p in verifiers))
            yield

    app = FastAPI(title="Orion API", version="0.1.0", lifespan=lifespan)
    if context is not None:
        app.state.ctx = context   # usable without running the lifespan (tests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,          # the refresh cookie
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(auth.router)
    app.include_router(orders.router)
    app.include_router(team.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        async with app.state.ctx.pool.connection() as conn:
            await conn.execute("SELECT 1")
        return {"ok": True}

    return app
