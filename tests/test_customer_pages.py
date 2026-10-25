"""Routes behind the signed-in website pages: settings, business profile, messages, help, products, stats,
documents. Same real `orion_test` Postgres and fake LLMs as test_api.py."""

from datetime import datetime, timedelta, timezone

from conftest import HOODIE_ANSWERS
from orion.db.insights import summarize_time
from orion.graph.graph import get_order
from test_api import PNG, _auth, _login, _order_to_sourcing, api  # noqa: F401  (api is a fixture)


# --- settings and sessions -------------------------------------------------------------

async def test_settings_defaults_update_and_onboarding(api):
    token = await _login(api, f"settings-{api.run}@example.com")
    me = (await api.get("/me", headers=_auth(token))).json()
    assert me["lang"] == "ar" and me["calendar"] == "gregorian" and not me["onboarded"]
    assert me["notify"]["shipped"] == {"email": True, "in_app": True}

    r = await api.put("/me", json={"name": "Sara", "lang": "en", "notify": {"shipped": {"email": False}}},
                      headers=_auth(token))
    assert r.status_code == 200
    me = r.json()
    assert me["name"] == "Sara" and me["lang"] == "en"
    assert me["notify"]["shipped"] == {"email": False, "in_app": True}   # merged, not replaced

    assert (await api.put("/me", json={"phone": "call me"}, headers=_auth(token))).status_code == 422
    assert (await api.put("/me", json={"notify": {"spam": {"email": True}}}, headers=_auth(token))).status_code == 422
    assert (await api.post("/me/onboarded", headers=_auth(token))).json()["onboarded"]


async def test_sign_out_everywhere_ends_refresh_sessions(api):
    token = await _login(api, f"sessions-{api.run}@example.com")
    assert len((await api.get("/me/sessions", headers=_auth(token))).json()) == 1
    r = await api.post("/me/sessions/revoke", headers=_auth(token))
    assert r.status_code == 200 and r.json()["revoked"] == 1
    api.cookies.clear()
    assert (await api.post("/auth/refresh", json={"audience": "customer"})).status_code == 401


# --- business profile -------------------------------------------------------------------

ADDRESS = {"contact_name": "Warehouse", "phone": "+966 50 123 4567", "city": "Riyadh", "street": "King Fahd Rd",
           "postal_code": "12345"}


async def test_business_profile_addresses_and_completeness(api):
    token = await _login(api, f"biz-{api.run}@example.com")
    view = (await api.get("/business", headers=_auth(token))).json()
    assert view["completeness"]["done"] == 0 and view["addresses"] == []

    r = await api.put("/business", json={"name": "  Qahwa Co ", "business_type": "food", "store_platform": "salla",
                                         "description": "Specialty coffee shop"}, headers=_auth(token))
    assert r.status_code == 200 and r.json()["profile"]["name"] == "Qahwa Co"
    assert (await api.put("/business", json={"store_url": "javascript:alert(1)"}, headers=_auth(token))).status_code == 422
    assert (await api.put("/business", json={"business_type": "casino"}, headers=_auth(token))).status_code == 422

    first = (await api.post("/business/addresses", json=ADDRESS, headers=_auth(token))).json()
    assert first["addresses"][0]["is_default"]                     # the first address is the default
    assert first["completeness"]["done"] == first["completeness"]["total"]
    second = (await api.post("/business/addresses", json={**ADDRESS, "label": "Shop", "is_default": True},
                             headers=_auth(token))).json()
    defaults = [a for a in second["addresses"] if a["is_default"]]
    assert len(defaults) == 1 and defaults[0]["label"] == "Shop"

    bad = {**ADDRESS, "postal_code": "abc"}
    assert (await api.post("/business/addresses", json=bad, headers=_auth(token))).status_code == 422

    # Another customer can't touch these addresses
    other = await _login(api, f"biz-other-{api.run}@example.com")
    shop_id = defaults[0]["id"]
    assert (await api.delete(f"/business/addresses/{shop_id}", headers=_auth(other))).status_code == 404
    assert (await api.put(f"/business/addresses/{shop_id}", json=ADDRESS, headers=_auth(other))).status_code == 404

    # Deleting the default makes the remaining address the default
    after = (await api.delete(f"/business/addresses/{shop_id}", headers=_auth(token))).json()
    assert len(after["addresses"]) == 1 and after["addresses"][0]["is_default"]


async def test_new_orders_carry_the_business_profile_for_the_ai(api):
    token = await _login(api, f"ai-biz-{api.run}@example.com")
    await api.put("/business", json={"name": "Qahwa Co", "description": "Coffee shop uniforms"}, headers=_auth(token))
    await api.post("/business/addresses", json=ADDRESS, headers=_auth(token))
    order_id = (await api.post("/orders", headers=_auth(token))).json()["order_id"]
    business = (await get_order(api.ctx.graph, order_id))["business"]
    assert business == {"name": "Qahwa Co", "description": "Coffee shop uniforms"}   # no phones or addresses


# --- stage history and messages ------------------------------------------------------------

async def test_stage_changes_are_recorded_and_notify_the_customer(api):
    token = await _login(api, f"notify-{api.run}@example.com")
    order_id = await _order_to_sourcing(api, token)

    async with api.ctx.pool.connection() as conn:
        stages = [r["stage"] for r in await (await conn.execute(
            "SELECT stage FROM order_stage_events WHERE order_id = %s ORDER BY at, id", (order_id,)
        )).fetchall()]
    assert stages[0] == "draft" and stages[-1] == "sourcing" and "pre_receipt_review" in stages

    inbox = (await api.get("/notifications", headers=_auth(token))).json()
    assert inbox["unread"] == 1
    assert [n["event"] for n in inbox["items"]] == ["sourcing"]     # nothing for the customer's own steps
    assert inbox["items"][0]["href"] == f"/orders/{order_id}"

    other = await _login(api, f"notify-other-{api.run}@example.com")
    await api.post("/notifications/read", json={"ids": [inbox["items"][0]["id"]]}, headers=_auth(other))
    assert (await api.get("/notifications", headers=_auth(token))).json()["unread"] == 1   # not theirs to mark
    assert (await api.post("/notifications/read", json={}, headers=_auth(token))).json()["unread"] == 0


# --- help requests ---------------------------------------------------------------------------

async def test_help_request_goes_to_the_team_and_back(api):
    token = await _login(api, f"help-{api.run}@example.com")
    order_id = await _order_to_sourcing(api, token)
    r = await api.post("/support", json={"topic": "price", "order_id": order_id, "body": "Can it be cheaper?"},
                       headers=_auth(token))
    assert r.status_code == 201
    request = r.json()
    assert request["status"] == "open" and request["context"]["stage"] == "sourcing"
    assert request["messages"][0]["author"] == "customer"

    other = await _login(api, f"help-other-{api.run}@example.com")
    assert (await api.get(f"/support/{request['id']}", headers=_auth(other))).status_code == 404
    r = await api.post("/support", json={"topic": "order", "order_id": order_id, "body": "x"}, headers=_auth(other))
    assert r.status_code == 404

    await api.ctx.accounts.add_team_member(f"help-agent-{api.run}@orion-team.com", None, "agent")
    agent = await _login(api, f"help-agent-{api.run}@orion-team.com", "team")
    queue = (await api.get("/team/support", params={"status": "open"}, headers=_auth(agent))).json()
    assert request["id"] in [q["id"] for q in queue]
    assert (await api.get("/team/support", headers=_auth(token))).status_code == 401   # customers can't

    r = await api.post(f"/team/support/{request['id']}/reply",
                       json={"body": "The team is reviewing your request.", "status": "waiting_customer"},
                       headers=_auth(agent))
    assert r.status_code == 200 and r.json()["status"] == "waiting_customer"
    inbox = (await api.get("/notifications", headers=_auth(token))).json()
    team = [n for n in inbox["items"] if n["kind"] == "team"]
    assert len(team) == 1 and team[0]["body_en"] == "The team is reviewing your request."

    r = await api.post(f"/support/{request['id']}/messages", json={"body": "Thanks"}, headers=_auth(token))
    assert r.json()["status"] == "open" and [m["author"] for m in r.json()["messages"]] == ["customer", "team", "customer"]


# --- products and reorder --------------------------------------------------------------------

async def test_confirmed_order_becomes_a_product_and_reorders_prefilled(api):
    token = await _login(api, f"reorder-{api.run}@example.com")
    assert (await api.get("/products", headers=_auth(token))).json() == []

    order_id = (await api.post("/orders", headers=_auth(token))).json()["order_id"]
    for reply in ({"choice": "apparel"}, {"choice": "hoodie"}):
        await api.post(f"/orders/{order_id}/reply", json={"reply": reply}, headers=_auth(token))
    logo = (await api.post(f"/orders/{order_id}/files", files={"file": ("logo.png", PNG, "image/png")},
                           headers=_auth(token))).json()
    answers = {**HOODIE_ANSWERS, "artwork": [logo]}
    await api.post(f"/orders/{order_id}/reply", json={"reply": {"answers": answers}}, headers=_auth(token))
    # Not a product until the summary is confirmed
    assert (await api.get("/products", headers=_auth(token))).json() == []
    await api.post(f"/orders/{order_id}/reply", json={"reply": {"confirm": True}}, headers=_auth(token))

    products = (await api.get("/products", headers=_auth(token))).json()
    assert [(p["id"], p["orders"]) for p in products] == [(order_id, 1)]
    detail = (await api.get(f"/products/{order_id}", params={"lang": "en"}, headers=_auth(token))).json()
    assert detail["summary"]["product"] and len(detail["history"]) == 1

    other = await _login(api, f"reorder-other-{api.run}@example.com")
    assert (await api.post(f"/products/{order_id}/reorder", headers=_auth(other))).status_code == 404

    r = await api.post(f"/products/{order_id}/reorder", headers=_auth(token))
    assert r.status_code == 201
    new = r.json()
    prompt = new["prompt"]
    assert new["order_id"] != order_id and prompt["step"] == "mandatory_questions"   # no product choice again
    assert prompt["values"]["fabric"] == HOODIE_ANSWERS["fabric"]
    copied = prompt["values"]["artwork"][0]
    assert copied["file_id"] != logo["file_id"]                                      # the new order's own copy
    assert (await api.get(f"/orders/{new['order_id']}/files/{copied['file_id']}", headers=_auth(token))).content == PNG

    # The customer reviews, changes the quantity and confirms: the product now has two orders
    changed = {**prompt["values"], "size_breakdown": "M:100"}
    r = await api.post(f"/orders/{new['order_id']}/reply", json={"reply": {"answers": changed}}, headers=_auth(token))
    assert r.status_code == 200, r.text
    await api.post(f"/orders/{new['order_id']}/reply", json={"reply": {"confirm": True}}, headers=_auth(token))
    products = (await api.get("/products", headers=_auth(token))).json()
    assert [(p["id"], p["orders"], p["last_quantity"]) for p in products] == [(order_id, 2, 100)]

    stats = (await api.get("/orders/stats", headers=_auth(token))).json()
    assert stats["orders"]["submitted"] == 2 and stats["orders"]["reorders"] == 1
    assert stats["orders"]["reorder_rate"] == 0.5 and stats["spend"] is None

    # Archive hides it from the main list
    await api.put(f"/products/{order_id}", json={"archived": True, "notes": "Winter run"}, headers=_auth(token))
    assert (await api.get("/products", headers=_auth(token))).json() == []
    archived = (await api.get("/products", params={"archived": True}, headers=_auth(token))).json()
    assert archived[0]["notes"] == "Winter run"


# --- documents --------------------------------------------------------------------------------

async def test_documents_list_receipt_versions_and_uploads(api):
    token = await _login(api, f"docs-{api.run}@example.com")
    order_id = await _order_to_sourcing(api, token)
    docs = (await api.get("/orders/documents", headers=_auth(token))).json()
    assert [(d["kind"], d["version"], d["status"]) for d in docs] == [("pre_receipt", 1, "confirmed")]

    r = await api.get(f"/orders/{order_id}/receipt", params={"version": 1, "lang": "en"}, headers=_auth(token))
    assert r.status_code == 200 and r.json()["lang"] == "en"
    assert (await api.get(f"/orders/{order_id}/receipt", params={"version": 9}, headers=_auth(token))).status_code == 404
    other = await _login(api, f"docs-other-{api.run}@example.com")
    assert (await api.get(f"/orders/{order_id}/receipt", headers=_auth(other))).status_code == 404


async def test_export_has_orders_with_their_details(api):
    token = await _login(api, f"export-{api.run}@example.com")
    order_id = await _order_to_sourcing(api, token)
    r = await api.get("/me/export", headers=_auth(token))
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["account"]["email"] == f"export-{api.run}@example.com"
    order = next(o for o in data["orders"] if o["id"] == order_id)
    assert order["details"]["answers"]["fabric"] == HOODIE_ANSWERS["fabric"]


# --- stats maths -------------------------------------------------------------------------------

def test_time_per_phase_counts_finished_phases_and_who_orders_waited_on():
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    h = lambda n: t0 + timedelta(hours=n)  # noqa: E731

    def seg(order, stage, owner, start, end):
        return {"order_id": order, "stage": stage, "waiting_on": owner, "at": h(start), "until": end and h(end)}

    segments = [
        # Delivered order: 10h specification, 30h quote, then delivered
        seg("a", "draft", "customer", 0, 8), seg("a", "pre_receipt_review", "customer", 8, 10),
        seg("a", "sourcing", "factory", 10, 40), seg("a", "delivered", None, 40, None),
        # Still with factories: its quote phase is not finished, so it doesn't count yet
        seg("b", "draft", "customer", 0, 4), seg("b", "sourcing", "factory", 4, None),
        # Unsent draft: no "waiting on you" time
        seg("c", "draft", "customer", 0, None),
    ]
    out = summarize_time(segments, now=h(50))
    phases = {p["phase"]: p for p in out["phases"]}
    assert phases["specification"] == {"phase": "specification", "avg_hours": 7.0, "orders": 2}
    assert phases["quote"] == {"phase": "quote", "avg_hours": 30.0, "orders": 1}
    assert out["waiting_hours"] == {"customer": 14.0, "factory": 76.0}
    assert out["order_to_delivery_hours"] == 30.0 and out["delivered_orders"] == 1
