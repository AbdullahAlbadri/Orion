"""AI mockups: the prompt is written in code from the form, the logo goes in as a reference image, and the
pictures are kept apart from the order's files. A fake image model; nothing is paid for."""

from orion.config.markets import get_questions
from orion.tools.mockup import MockupImage, mockup_prompt
from test_api import PNG, _auth, _login, api  # noqa: F401  (api is a fixture)

LOGO_AT_LEFT_CHEST = [{"kind": "logo", "view": "front", "x": 0.63, "y": 0.3, "width_cm": 9, "height_cm": 7}]


class FakeMaker:
    model = "fake/image"

    def __init__(self, data=PNG):
        self.data, self.calls = data, []

    async def make(self, prompt, references, aspect_ratio):
        self.calls.append({"prompt": prompt, "references": references, "aspect": aspect_ratio})
        return MockupImage(self.data, "image/png", 0.01)


def test_prompt_describes_the_look_and_the_logo_position_not_the_logistics():
    questions = get_questions("apparel", "hoodie")
    answers = {"colors": ["black"], "decoration_method": "embroidery", "fabric": "cotton fleece",
               "decoration_placement": LOGO_AT_LEFT_CHEST, "needed_by": "flexible", "packaging": ["branded box"]}
    prompt, aspect = mockup_prompt("Hoodie", questions, answers, has_logo=True)
    assert "custom Hoodie" in prompt and "black" in prompt and "embroidery" in prompt and "cotton fleece" in prompt
    assert "logo, front, wearer's left chest, 9 x 7 cm" in prompt and "Use the attached image as the logo" in prompt
    assert "flexible" not in prompt and "branded box" not in prompt and aspect == "1:1"

    back = LOGO_AT_LEFT_CHEST + [{"kind": "logo", "view": "back", "x": 0.5, "y": 0.45, "width_cm": 30, "height_cm": 36}]
    prompt, aspect = mockup_prompt("Hoodie", questions, {"decoration_placement": back}, has_logo=True)
    assert "front and back views side by side" in prompt and aspect == "16:9"
    prompt, _ = mockup_prompt("Hoodie", questions, {"colors": ["navy"]}, has_logo=False)
    assert "without any logo" in prompt


async def test_customer_makes_mockups_from_the_form_with_their_logo(api):
    token, other = await _login(api, f"mock-{api.run}@example.com"), await _login(api, f"mock2-{api.run}@example.com")
    api.ctx.mockups = fake = FakeMaker()
    order = (await api.post("/orders", json={"option": "hoodie"}, headers=_auth(token))).json()["order_id"]
    logo = (await api.post(f"/orders/{order}/files", files={"file": ("logo.png", PNG, "image/png")},
                           headers=_auth(token))).json()
    answers = {"colors": ["black"], "decoration_method": "embroidery", "artwork": [logo],
               "decoration_placement": LOGO_AT_LEFT_CHEST}

    r = await api.post(f"/orders/{order}/mockups", json={"answers": answers}, headers=_auth(token))
    assert r.status_code == 201 and r.json()["logo_used"] and r.json()["remaining"] == 4
    assert fake.calls[0]["references"] == [(PNG, "image/png")] and "wearer's left chest" in fake.calls[0]["prompt"]
    got = await api.get(f"/orders/{order}/mockups/{r.json()['mockup_id']}", headers=_auth(token))
    assert got.content == PNG and "sandbox" in got.headers["content-security-policy"]
    assert (await api.get(f"/orders/{order}/mockups/{r.json()['mockup_id']}", headers=_auth(other))).status_code == 404
    # Mockups are not order files: nothing new for the factory or the documents list
    assert await api.ctx.accounts.file_ids(order) == {logo["file_id"]}

    # A file from another order is not used as the logo
    foreign = (await api.post("/orders", json={"option": "hoodie"}, headers=_auth(other))).json()["order_id"]
    their = (await api.post(f"/orders/{foreign}/files", files={"file": ("x.png", PNG, "image/png")},
                            headers=_auth(other))).json()
    r = await api.post(f"/orders/{order}/mockups", json={"answers": {"artwork": [their]}}, headers=_auth(token))
    assert r.status_code == 201 and not r.json()["logo_used"] and fake.calls[-1]["references"] == []

    # Something that isn't an image is never stored
    api.ctx.mockups = FakeMaker(b"<html>error</html>")
    assert (await api.post(f"/orders/{order}/mockups", json={}, headers=_auth(token))).status_code == 502

    api.ctx.mockups = fake
    for _ in range(3):
        assert (await api.post(f"/orders/{order}/mockups", json={}, headers=_auth(token))).status_code == 201
    r = await api.post(f"/orders/{order}/mockups", json={}, headers=_auth(token))
    assert r.status_code == 409                                       # 5 per order
    listed = (await api.get(f"/orders/{order}/mockups", headers=_auth(token))).json()
    assert len(listed["mockups"]) == 5 and listed["remaining"] == 0
