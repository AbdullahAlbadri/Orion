"""API tests against the real `orion_test` Postgres (skipped when it is not running), with fake LLMs."""

import re
import uuid

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from conftest import HOODIE_ANSWERS, ScriptedManufacturerAgent
from orion.api.app import create_app
from orion.api.context import ApiContext
from orion.api.oidc import Identity
from orion.api.security import TokenClaims, issue_access_token
from orion.config.settings import Settings
from orion.db.accounts import AccountStore
from orion.db.postgres import ManualRelayChannel, PostgresDirectory, PostgresPriceStore, PostgresScheduler, make_pool
from orion.db.stores import Manufacturer
from orion.deps import Deps
from orion.graph.graph import build_graph
from orion.tools.email import ConsoleEmailSender
from orion.tools.llm import CompletenessReport, DeepDiveTurn
from orion.tools.manufacturer_llm import ReplyAnalysis
from orion.tools.prices import ExtractedPrice

QUOTE_TEXT = "单价45元/件，含税，FOB深圳"


class DoneConsultant:
    """Fake customer LLM: says the spec is complete straight away."""

    async def deep_dive(self, ctx):
        return DeepDiveTurn(updates=[], message="Thanks, preparing your summary.", ready_for_review=True)

    async def check_completeness(self, ctx):
        return CompletenessReport(gaps=[])


class FakeVerifier:
    def __init__(self, email_verified=True):
        self.email_verified = email_verified

    async def verify(self, id_token: str) -> Identity:
        if not id_token.startswith("good:"):
            raise ValueError("bad signature")
        sub = id_token.split(":", 1)[1]
        return Identity(provider="google", subject=sub, email=f"{sub}@gmail.com",
                        email_verified=self.email_verified, name="G User")


@pytest.fixture
async def api(pg_url):
    run = uuid.uuid4().hex[:8]
    settings = Settings(
        openrouter_api_key="unused", consultant_model="x", manufacturer_model="x", classifier_model="x",
        database_url=pg_url, jwt_secret="j" * 48, login_code_secret="c" * 48,
    )
    async with make_pool(pg_url) as pool:
        directory = PostgresDirectory(pool)
        manufacturer = Manufacturer(id=f"api-{run}", name="API Factory")
        await directory.add(manufacturer)
        market_key = f"apparel-{run}"
        await directory.assign(manufacturer.id, market_key, None, 1)

        class Directory:   # route this run's orders to this run's manufacturer only
            async def ranked_for(self, market, option):
                return await directory.ranked_for(market_key, option)

            def __getattr__(self, name):
                return getattr(directory, name)

        agent = ScriptedManufacturerAgent(analyses=[ReplyAnalysis(
            kind="quote", summary_en="quote",
            prices=[ExtractedPrice(unit_price=45, currency="元", unit="piece", incoterm="FOB",
                                   tax_included=True, quoted_text="单价45元/件")],
        ), ReplyAnalysis(kind="acknowledgement", summary_en="ok")])
        deps = Deps(
            consultant=DoneConsultant(), manufacturer_agent=agent, directory=Directory(),
            prices=PostgresPriceStore(pool), channel=ManualRelayChannel(pool), scheduler=PostgresScheduler(pool),
        )
        email = ConsoleEmailSender()
        context = ApiContext(
            graph=build_graph(deps, InMemorySaver()), deps=deps, pool=pool, settings=settings,
            accounts=AccountStore(pool), email=email, verifiers={},
        )
        app = create_app(context)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            client.ctx, client.run, client.manufacturer = context, run, manufacturer
            yield client


def _code(client) -> str:
    return re.search(r"\b(\d{6})\b", client.ctx.email.sent[-1]["subject"]).group(1)


async def _login(client, email: str, audience="customer") -> str:
    assert (await client.post("/auth/email/start", json={"email": email, "audience": audience})).status_code == 202
    r = await client.post("/auth/email/verify", json={"email": email, "code": _code(client), "audience": audience})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# --- login ------------------------------------------------------------------------

async def test_email_code_login(api):
    email = f"Customer-{api.run}@Example.com"
    assert (await api.post("/auth/email/start", json={"email": email})).status_code == 202
    sent = api.ctx.email.sent[-1]
    assert sent["to"] == email.lower() and "login/verify?" in sent["text"]

    bad = await api.post("/auth/email/verify", json={"email": email, "code": "000000"})
    assert bad.status_code == 401
    good = await api.post("/auth/email/verify", json={"email": email, "code": _code(api)})
    assert good.status_code == 200
    body = good.json()
    assert body["user"]["email"] == email.lower() and body["expires_in"] == 900
    assert "orion_refresh_customer" in api.cookies

    me = await api.get("/auth/me", headers=_auth(body["access_token"]))
    assert me.json()["email"] == email.lower()

    # A code works once
    again = await api.post("/auth/email/verify", json={"email": email, "code": _code(api)})
    assert again.status_code == 401


async def test_code_attempt_limit_and_rate_limit(api):
    email = f"limits-{api.run}@example.com"
    await api.post("/auth/email/start", json={"email": email})
    code = _code(api)
    for _ in range(5):
        await api.post("/auth/email/verify", json={"email": email, "code": "111111" if code != "111111" else "222222"})
    assert (await api.post("/auth/email/verify", json={"email": email, "code": code})).status_code == 401

    for _ in range(4):
        await api.post("/auth/email/start", json={"email": email})
    assert (await api.post("/auth/email/start", json={"email": email})).status_code == 429


async def test_refresh_rotates_and_reuse_revokes_everything(api):
    await _login(api, f"refresh-{api.run}@example.com")
    first = api.cookies.get("orion_refresh_customer")

    r = await api.post("/auth/refresh", json={"audience": "customer"})
    assert r.status_code == 200 and r.json()["access_token"]
    second = api.cookies.get("orion_refresh_customer")
    assert second and second != first

    async def refresh_with(token):
        api.cookies.clear()
        api.cookies.set("orion_refresh_customer", token)
        return (await api.post("/auth/refresh", json={"audience": "customer"})).status_code

    # Replaying the old token = theft signal: it fails AND the newest session is revoked too
    assert await refresh_with(first) == 401
    assert await refresh_with(second) == 401


async def test_forged_and_wrong_audience_tokens_are_rejected(api):
    forged = issue_access_token("not-the-real-secret-but-long-enough-0123456789", TokenClaims(sub=str(uuid.uuid4()), aud="customer", email="x@y.z"))
    assert (await api.get("/auth/me", headers=_auth(forged))).status_code == 401
    customer = await _login(api, f"aud-{api.run}@example.com")
    assert (await api.get("/team/orders", headers=_auth(customer))).status_code == 401
    assert (await api.get("/auth/me")).status_code == 401


async def test_google_login(api):
    assert (await api.post("/auth/google", json={"id_token": "good:x"})).status_code == 404   # not configured

    api.ctx.verifiers["google"] = FakeVerifier()
    r = await api.post("/auth/google", json={"id_token": f"good:g{api.run}"})
    assert r.status_code == 200 and r.json()["user"]["email"] == f"g{api.run}@gmail.com"
    same = await api.post("/auth/google", json={"id_token": f"good:g{api.run}"})
    assert same.json()["user"]["id"] == r.json()["user"]["id"]
    assert (await api.post("/auth/google", json={"id_token": "forged"})).status_code == 401

    api.ctx.verifiers["google"] = FakeVerifier(email_verified=False)
    assert (await api.post("/auth/google", json={"id_token": f"good:u{api.run}"})).status_code == 401


# --- team -------------------------------------------------------------------------

async def test_console_is_served_with_strict_headers(api):
    page = await api.get("/console/")
    assert page.status_code == 200 and "console.js" in page.text
    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    script = await api.get("/console/console.js")
    assert script.status_code == 200 and "innerHTML" not in script.text.replace("never innerHTML", "")

async def test_team_login_and_roles(api):
    admin_email, agent_email = f"admin-{api.run}@orion-team.com", f"agent-{api.run}@orion-team.com"
    await api.ctx.accounts.add_team_member(admin_email, "Admin", "admin")
    await api.ctx.accounts.add_team_member(agent_email, "Agent", "agent")

    sent_before = len(api.ctx.email.sent)
    r = await api.post("/auth/email/start", json={"email": f"stranger-{api.run}@x.com", "audience": "team"})
    assert r.status_code == 202 and len(api.ctx.email.sent) == sent_before   # same answer, nothing sent

    admin = await _login(api, admin_email, "team")
    agent = await _login(api, agent_email, "team")
    new = {"id": f"m-{api.run}", "name": "New Factory", "market": "apparel"}
    assert (await api.post("/team/manufacturers", json=new, headers=_auth(agent))).status_code == 403
    assert (await api.post("/team/manufacturers", json=new, headers=_auth(admin))).status_code == 201
    assert (await api.get("/team/members", headers=_auth(agent))).status_code == 403
    assert (await api.get("/team/members", headers=_auth(admin))).status_code == 200


# --- orders -----------------------------------------------------------------------

async def _order_to_sourcing(api, token) -> str:
    r = await api.post("/orders", headers=_auth(token))
    assert r.status_code == 201
    order = r.json()
    order_id = order["order_id"]
    assert order["prompt"]["step"] == "select_market" and order["status"]["ar"]

    # The fake directory serves this run's manufacturer for its own market key; point the order there
    for reply in ({"choice": "apparel"}, {"choice": "hoodie"}, {"answers": HOODIE_ANSWERS}):
        r = await api.post(f"/orders/{order_id}/reply", json={"reply": reply}, headers=_auth(token))
        assert r.status_code == 200, r.text
    assert r.json()["prompt"]["kind"] == "confirm"
    r = await api.post(f"/orders/{order_id}/reply", json={"reply": {"confirm": True}}, headers=_auth(token))
    assert r.json()["waiting_on"] == "manufacturer" and r.json()["prompt"] is None
    return order_id


async def test_customer_order_flow_and_privacy(api):
    alice = await _login(api, f"alice-{api.run}@example.com")
    bob = await _login(api, f"bob-{api.run}@example.com")
    order_id = await _order_to_sourcing(api, alice)

    view = (await api.get(f"/orders/{order_id}", headers=_auth(alice))).json()
    assert view["stage"] == "sourcing" and view["spec"]["frozen"]
    for internal in ("human_tasks", "needs_human", "manufacturer_attempts", "quotes", "spec_zh"):
        assert internal not in view
    assert [o["id"] for o in (await api.get("/orders", headers=_auth(alice))).json()] == [order_id]

    # Bob can't see or answer Alice's order
    assert (await api.get(f"/orders/{order_id}", headers=_auth(bob))).status_code == 404
    assert (await api.post(f"/orders/{order_id}/reply", json={"reply": {}}, headers=_auth(bob))).status_code == 404
    # While the manufacturer has the turn, customer replies are refused
    r = await api.post(f"/orders/{order_id}/reply", json={"reply": {"message": "hi"}}, headers=_auth(alice))
    assert r.status_code == 409


async def test_team_relays_a_manufacturer_quote(api):
    customer = await _login(api, f"carol-{api.run}@example.com")
    order_id = await _order_to_sourcing(api, customer)
    await api.ctx.accounts.add_team_member(f"relay-{api.run}@orion-team.com", None, "agent")
    agent = await _login(api, f"relay-{api.run}@orion-team.com", "team")

    outbox = [m for m in (await api.get("/team/outbox", headers=_auth(agent))).json() if m["order_id"] == order_id]
    assert len(outbox) == 1 and "卫衣" in outbox[0]["text"]
    assert (await api.post(f"/team/outbox/{outbox[0]['id']}/sent", headers=_auth(agent))).status_code == 200

    body = {"manufacturer_id": api.manufacturer.id, "text": QUOTE_TEXT}
    r = await api.post(f"/team/orders/{order_id}/manufacturer-replies", json=body, headers=_auth(agent))
    assert r.status_code == 200 and r.json()["stage"] == "quote_received"

    flagged = (await api.get("/team/orders", params={"needs_human": True}, headers=_auth(agent))).json()
    row = next(o for o in flagged if o["id"] == order_id)
    assert row["stage"] == "quote_received" and row["customer_email"] == f"carol-{api.run}@example.com"
    # The customer sees progress, not the price
    view = (await api.get(f"/orders/{order_id}", headers=_auth(customer))).json()
    assert view["status"]["en"] == "Preparing your quote" and "45" not in str(view)

    # The team resolves the flags: off the list, history kept, and the order still waits for replies
    r = await api.post(f"/team/orders/{order_id}/resolve", headers=_auth(agent))
    assert r.status_code == 200 and r.json()["needs_human"] is None
    assert all(t["resolved_by"] == f"relay-{api.run}@orion-team.com" for t in r.json()["human_tasks"])
    flagged = (await api.get("/team/orders", params={"needs_human": True}, headers=_auth(agent))).json()
    assert order_id not in [o["id"] for o in flagged]
    body = {"manufacturer_id": api.manufacturer.id, "text": "收到"}
    r = await api.post(f"/team/orders/{order_id}/manufacturer-replies", json=body, headers=_auth(agent))
    assert r.status_code == 200 and r.json()["waiting"]["waiting_on"] == "manufacturer"
