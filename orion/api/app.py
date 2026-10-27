"""FastAPI app. Run locally with:  uv run python -m orion.api   (docs at http://localhost:8000/docs)"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from orion import deps as deps_module   # the startup code below has its own variable called deps
from orion.api import auth, inbox, me, orders, products, team
from orion.api.context import ApiContext
from orion.api.oidc import apple_verifier, google_verifier
from orion.config.settings import Settings, get_settings
from orion.db.accounts import AccountStore
from orion.runtime import open_postgres_app
from orion.tools.assist import OpenRouterAssistant
from orion.tools.email import ConsoleEmailSender
from orion.tools.files import LocalFileStore
from orion.tools.mockup import OpenRouterMockupMaker
from orion.tools.suggest import OpenRouterSuggester

log = logging.getLogger("orion.api")

CONSOLE_DIR = Path(__file__).parent / "console"
# Only our own script, styles and API calls; no inline script; cannot be framed
CONSOLE_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


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
            # Login codes go out through the Orion mailbox when it is set (Gmail limits it to about 500 a day);
            # otherwise they are printed to the log. TODO(decide): email provider (Resend / Postmark / SES)
            login_mail = deps_module.mailbox(settings)
            log.info("login codes: %s", "emailed" if login_mail else "printed to the log (no mailbox set)")
            assistant = OpenRouterAssistant(
                settings.openrouter_api_key.get_secret_value(), settings.openrouter_base_url, settings.assist_model
            )
            app.state.ctx = ApiContext(
                graph=graph, deps=deps, pool=pool, settings=settings,
                accounts=AccountStore(pool), email=login_mail or ConsoleEmailSender(), verifiers=verifiers, assistant=assistant,
                # TODO(step 7): S3-compatible object storage on Hetzner
                files=LocalFileStore(settings.upload_dir),
                # Product ideas on the Overview: the same small, cheap model as "Ask Orion"
                suggester=OpenRouterSuggester(
                    settings.openrouter_api_key.get_secret_value(), settings.openrouter_base_url, settings.assist_model
                ),
                mockups=OpenRouterMockupMaker(
                    settings.openrouter_api_key.get_secret_value(), settings.openrouter_base_url, settings.mockup_model,
                    settings.mockup_fallback_model,
                ),
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
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(auth.router)
    app.include_router(orders.router)
    app.include_router(products.router)
    app.include_router(me.router)
    app.include_router(inbox.router)
    app.include_router(team.router)

    # Team console: static page using the team API from the same origin
    app.mount("/console", StaticFiles(directory=CONSOLE_DIR, html=True), name="console")

    @app.middleware("http")
    async def console_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/console"):
            response.headers["Content-Security-Policy"] = CONSOLE_CSP
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        async with app.state.ctx.pool.connection() as conn:
            await conn.execute("SELECT 1")
        return {"ok": True}

    return app
