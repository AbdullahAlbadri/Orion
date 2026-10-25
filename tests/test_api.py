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
from orion.api.security import TokenClaims, hash_refresh_token, issue_access_token
from orion.config.settings import Settings
from orion.db.accounts import AccountStore
from orion.db.postgres import ManualRelayChannel, PostgresDirectory, PostgresPriceStore, PostgresScheduler, make_pool
from orion.db.stores import Manufacturer
from orion.deps import Deps
from orion.graph.graph import build_graph
from orion.tools.email import ConsoleEmailSender
from orion.tools.files import LocalFileStore
from orion.tools.llm import CompletenessReport, DeepDiveTurn
from orion.tools.manufacturer_llm import ReplyAnalysis
from orion.tools.prices import ExtractedPrice

QUOTE_TEXT = "单价45元/件，含税，FOB深圳"


class DoneConsultant:
    """Fake customer LLM: says the spec is complete straight away."""

    async def deep_dive(self, ctx):
        return DeepDiveTurn(updates=[], intro="", questions=[], ready_for_review=True)

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
async def api(pg_url, tmp_path):
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
            files=LocalFileStore(str(tmp_path / "uploads")),
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

    # Replayed within seconds (two tabs refreshing together): it fails, but the newest session lives on
    assert await refresh_with(first) == 401
    api.cookies.clear()
    api.cookies.set("orion_refresh_customer", second)
    r = await api.post("/auth/refresh", json={"audience": "customer"})
    assert r.status_code == 200
    third = r.cookies.get("orion_refresh_customer")

    # Replayed later = theft signal: it fails AND the newest session is revoked too
    async with api.ctx.pool.connection() as conn:
        await conn.execute("UPDATE refresh_tokens SET revoked_at = now() - interval '1 minute' WHERE token_hash = %s",
                           (hash_refresh_token(first),))
    assert await refresh_with(first) == 401
    assert await refresh_with(third) == 401


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


# --- "Ask Orion" on form sections ---------------------------------------------------

class FakeAssistant:
    def __init__(self, answer="Most hoodies use 320-380 GSM cotton fleece."):
        self.answer, self.calls = answer, []

    async def help(self, product, section, questions, answers, question, lang):
        self.calls.append({"product": product, "section": section, "ids": [q.id for q in questions],
                           "answers": answers, "question": question, "lang": lang})
        return self.answer


async def test_assist_explains_a_section(api):
    from orion.api.limits import SlidingWindowLimit

    token = await _login(api, f"assist-{api.run}@example.com")
    order_id = (await api.post("/orders", headers=_auth(token))).json()["order_id"]
    api.ctx.assistant = FakeAssistant()
    body = {"section": "quality", "question": "Which weight for summer?", "answers": {"fabric_gsm": "280", "fabric": "jersey knit", "x": 1}, "lang": "en"}

    # Before a product is chosen there is nothing to explain
    assert (await api.post(f"/orders/{order_id}/assist", json=body, headers=_auth(token))).status_code == 409
    for reply in ({"choice": "apparel"}, {"choice": "hoodie"}):
        await api.post(f"/orders/{order_id}/reply", json={"reply": reply}, headers=_auth(token))

    r = await api.post(f"/orders/{order_id}/assist", json=body, headers=_auth(token))
    assert r.status_code == 200 and r.json()["answer"].startswith("Most hoodies")
    call = api.ctx.assistant.calls[-1]
    assert call["product"] == "Hoodie" and call["section"] == "quality"
    assert set(call["ids"]) == {"fabric_gsm", "labels", "packaging", "sample"} and call["answers"] == {"fabric_gsm": "280"}

    # Rule 1: an answer that talks money never reaches the customer
    api.ctx.assistant = FakeAssistant("Cotton fleece costs about 45 SAR per piece")
    r = await api.post(f"/orders/{order_id}/assist", json={**body, "lang": "ar"}, headers=_auth(token))
    assert "45" not in r.json()["answer"] and "عرض السعر" in r.json()["answer"]

    other = await _login(api, f"assist-other-{api.run}@example.com")
    assert (await api.post(f"/orders/{order_id}/assist", json=body, headers=_auth(other))).status_code == 404

    api.ctx.assist_limit = SlidingWindowLimit(1, 3600)
    assert (await api.post(f"/orders/{order_id}/assist", json=body, headers=_auth(token))).status_code == 200
    assert (await api.post(f"/orders/{order_id}/assist", json=body, headers=_auth(token))).status_code == 429


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


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
SVG_WITH_SCRIPT = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


async def test_logo_upload_download_and_privacy(api):
    alice = await _login(api, f"files-a-{api.run}@example.com")
    bob = await _login(api, f"files-b-{api.run}@example.com")
    order = (await api.post("/orders", headers=_auth(alice))).json()["order_id"]
    bobs_order = (await api.post("/orders", headers=_auth(bob))).json()["order_id"]

    r = await api.post(f"/orders/{order}/files", files={"file": ("logo.png", PNG, "image/png")}, headers=_auth(alice))
    assert r.status_code == 201
    logo = r.json()
    assert logo["content_type"] == "image/png" and logo["name"] == "logo.png"

    # The type comes from the bytes, not the name
    fake = await api.post(f"/orders/{order}/files", files={"file": ("logo.png", b"hello world", "image/png")},
                          headers=_auth(alice))
    assert fake.status_code == 415
    big = await api.post(f"/orders/{order}/files", files={"file": ("big.png", PNG + b"\x00" * (10 * 1024 * 1024), "image/png")},
                         headers=_auth(alice))
    assert big.status_code == 413

    got = await api.get(f"/orders/{order}/files/{logo['file_id']}", headers=_auth(alice))
    assert got.status_code == 200 and got.content == PNG and got.headers["content-type"] == "image/png"
    assert (await api.get(f"/orders/{order}/files/{logo['file_id']}", headers=_auth(bob))).status_code == 404

    # SVG is allowed but served so that its script can never run
    svg = (await api.post(f"/orders/{order}/files", files={"file": ("a.svg", SVG_WITH_SCRIPT, "image/svg+xml")},
                          headers=_auth(alice))).json()
    got = await api.get(f"/orders/{order}/files/{svg['file_id']}", headers=_auth(alice))
    assert "default-src 'none'" in got.headers["content-security-policy"] and got.headers["x-content-type-options"] == "nosniff"

    # Answers may only reference files of the same order
    for reply in ({"choice": "apparel"}, {"choice": "hoodie"}):
        await api.post(f"/orders/{bobs_order}/reply", json={"reply": reply}, headers=_auth(bob))
    stolen = {"answers": {"artwork": [{"file_id": logo["file_id"], "name": "x"}]}}
    assert (await api.post(f"/orders/{bobs_order}/reply", json={"reply": stolen}, headers=_auth(bob))).status_code == 422

    # Through to the receipt with the logo as an answer; the team can download it
    for reply in ({"choice": "apparel"}, {"choice": "hoodie"}):
        await api.post(f"/orders/{order}/reply", json={"reply": reply}, headers=_auth(alice))
    answers = {**HOODIE_ANSWERS, "artwork": [logo]}
    r = await api.post(f"/orders/{order}/reply", json={"reply": {"answers": answers}}, headers=_auth(alice))
    assert r.json()["prompt"]["kind"] == "confirm"
    design = next(s for s in r.json()["summary"]["sections"] if s["id"] == "design")["items"]
    artwork = next(i for i in design if i["id"] == "artwork")
    assert artwork["value"] == "logo.png" and artwork["raw"][0]["file_id"] == logo["file_id"]

    await api.ctx.accounts.add_team_member(f"files-team-{api.run}@orion-team.com", None, "agent")
    agent = await _login(api, f"files-team-{api.run}@orion-team.com", "team")
    got = await api.get(f"/team/orders/{order}/files/{logo['file_id']}", headers=_auth(agent))
    assert got.status_code == 200 and got.content == PNG


async def test_customer_stats_count_real_work_and_estimate_time(api):
    token = await _login(api, f"stats-{api.run}@example.com")
    empty = (await api.get("/orders/stats", headers=_auth(token))).json()
    assert empty["orders_submitted"] == 0 and empty["time_saved_hours"] == 0 and empty["money_saved"] is None

    order_id = await _order_to_sourcing(api, token)
    await api.ctx.accounts.add_team_member(f"stats-team-{api.run}@orion-team.com", None, "agent")
    agent = await _login(api, f"stats-team-{api.run}@orion-team.com", "team")
    body = {"manufacturer_id": api.manufacturer.id, "text": QUOTE_TEXT}
    await api.post(f"/team/orders/{order_id}/manufacturer-replies", json=body, headers=_auth(agent))

    s = (await api.get("/orders/stats", headers=_auth(token))).json()
    assert s["orders_submitted"] == 1 and s["pieces_ordered"] == 150
    assert s["factories_contacted"] == 1 and s["messages_handled"] == 2       # our request + their reply
    assert s["orders_quoted"] == 1 and s["hours_to_first_quote"] is not None
    assert s["time_saved_hours"] == 2.0 + 1.5 + 2 * 0.25                      # spec + factory + 2 messages
    # Another customer's numbers are their own
    other = await _login(api, f"stats-other-{api.run}@example.com")
    assert (await api.get("/orders/stats", headers=_auth(other))).json()["factories_contacted"] == 0


async def test_new_order_clicks_do_not_pile_up_empty_drafts(api):
    token = await _login(api, f"clicks-{api.run}@example.com")
    new = lambda: api.post("/orders", headers=_auth(token))   # noqa: E731

    first = (await new()).json()["order_id"]
    assert (await new()).json()["order_id"] == first                     # untouched draft reused
    assert (await api.get("/orders", headers=_auth(token))).json() == []  # nothing filled: not counted

    # Product picked but nothing answered: cleared so a different product can be chosen
    for reply in ({"choice": "apparel"}, {"choice": "hoodie"}):
        await api.post(f"/orders/{first}/reply", json={"reply": reply}, headers=_auth(token))
    second = (await new()).json()
    assert second["order_id"] != first and second["prompt"]["step"] == "select_market"
    assert (await api.get(f"/orders/{first}", headers=_auth(token))).json()["stage"] == "cancelled"

    # A draft with answers is kept and counted; "new order" starts a separate one
    for reply in ({"choice": "apparel"}, {"choice": "hoodie"}):
        await api.post(f"/orders/{second['order_id']}/reply", json={"reply": reply}, headers=_auth(token))
    await api.post(f"/orders/{second['order_id']}/reply",
                   json={"reply": {"answers": {"colors": ["black"]}}}, headers=_auth(token))   # partial, with errors
    third = (await new()).json()["order_id"]
    assert third not in (first, second["order_id"])
    listed = [o["id"] for o in (await api.get("/orders", headers=_auth(token))).json()]
    assert listed == [second["order_id"]]


async def test_customer_can_discard_unsubmitted_drafts_only(api):
    token = await _login(api, f"discard-{api.run}@example.com")
    submitted = await _order_to_sourcing(api, token)
    draft = (await api.post("/orders", headers=_auth(token))).json()["order_id"]

    assert (await api.post(f"/orders/{draft}/discard", headers=_auth(token))).status_code == 200
    assert (await api.post(f"/orders/{submitted}/discard", headers=_auth(token))).status_code == 409
    assert [o["id"] for o in (await api.get("/orders", headers=_auth(token))).json()] == [submitted]
    # A discarded draft no longer accepts answers
    r = await api.post(f"/orders/{draft}/reply", json={"reply": {"choice": "apparel"}}, headers=_auth(token))
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
    assert view["status"]["en"] == "Preparing your quote"
    assert "quotes" not in view and "单价" not in str(view) and "unit_price" not in str(view)

    # The team resolves the flags: off the list, history kept, and the order still waits for replies
    r = await api.post(f"/team/orders/{order_id}/resolve", headers=_auth(agent))
    assert r.status_code == 200 and r.json()["needs_human"] is None
    assert all(t["resolved_by"] == f"relay-{api.run}@orion-team.com" for t in r.json()["human_tasks"])
    flagged = (await api.get("/team/orders", params={"needs_human": True}, headers=_auth(agent))).json()
    assert order_id not in [o["id"] for o in flagged]
    body = {"manufacturer_id": api.manufacturer.id, "text": "收到"}
    r = await api.post(f"/team/orders/{order_id}/manufacturer-replies", json=body, headers=_auth(agent))
    assert r.status_code == 200 and r.json()["waiting"]["waiting_on"] == "manufacturer"


async def test_team_previews_and_sends_the_customer_quote_which_the_customer_accepts(api):
    customer = await _login(api, f"quote-{api.run}@example.com")
    order_id = await _order_to_sourcing(api, customer)
    await api.ctx.accounts.add_team_member(f"quoter-{api.run}@orion-team.com", None, "agent")
    agent = await _login(api, f"quoter-{api.run}@orion-team.com", "team")
    body = {"manufacturer_id": api.manufacturer.id, "text": QUOTE_TEXT}
    await api.post(f"/team/orders/{order_id}/manufacturer-replies", json=body, headers=_auth(agent))

    preview = (await api.get(f"/team/orders/{order_id}/quote-preview", headers=_auth(agent))).json()
    assert preview["quote"]["unit_price"] == "25.99" and any("shipping" in w for w in preview["warnings"])
    assert (await api.get(f"/team/orders/{order_id}/quote-preview", headers=_auth(customer))).status_code == 401

    # A warning (no shipping price) stops it until the team sends anyway
    r = await api.post(f"/team/orders/{order_id}/send-quote", json={}, headers=_auth(agent))
    assert r.status_code == 409 and "shipping" in r.json()["detail"]
    r = await api.post(f"/team/orders/{order_id}/send-quote", json={"send_anyway": True}, headers=_auth(agent))
    assert r.status_code == 200 and r.json()["stage"] == "quote_review"

    # The customer sees riyals only: no factory, no yuan, no fee
    view = (await api.get(f"/orders/{order_id}", headers=_auth(customer))).json()
    assert view["prompt"]["kind"] == "quote" and view["prompt"]["quote"]["total"] == "3898.50"
    assert "元" not in str(view) and "manufacturer" not in str(view["prompt"]) and "fee" not in str(view["prompt"])

    r = await api.post(f"/orders/{order_id}/reply", json={"reply": {"accept": True}}, headers=_auth(customer))
    assert r.status_code == 200 and r.json()["stage"] == "awaiting_payment"
    assert r.json()["waiting_on"] == "payment" and r.json()["prompt"] is None
