"""AI mockups: the prompt is written in code from the form, the logo goes in as a reference image, and the
pictures are kept apart from the order's files. A fake image model; nothing is paid for."""

import io

from PIL import Image, ImageDraw

from orion.config.markets import get_questions
from orion.tools.brief import mockup_brief
from orion.tools.mockup import MockupImage, artwork_guide, artwork_prompt, compose_artwork, mockup_prompt, target_boxes
from test_api import PNG, _auth, _login, api  # noqa: F401  (api is a fixture)

LOGO_AT_LEFT_CHEST = [{"kind": "logo", "view": "front", "x": 0.63, "y": 0.3, "width_cm": 9, "height_cm": 7}]


class FakeMaker:
    model = "fake/image"

    def __init__(self, data=PNG):
        self.data, self.calls = data, []

    async def make(self, prompt, references, aspect_ratio, model=None):
        self.calls.append({"prompt": prompt, "references": references, "aspect": aspect_ratio, "model": model})
        return MockupImage(self.data, "image/png", 0.01)


def test_prompt_describes_the_look_and_the_logo_position_not_the_logistics():
    questions = get_questions("apparel", "hoodie")
    answers = {"colors": ["black"], "decoration_method": "embroidery", "fabric": "cotton fleece",
               "decoration_placement": LOGO_AT_LEFT_CHEST, "needed_by": "flexible", "packaging": ["branded box"]}
    prompt, aspect = mockup_prompt("Hoodie", questions, answers)
    assert "custom Hoodie" in prompt and "black" in prompt and "embroidery" in prompt and "cotton fleece" in prompt
    assert "completely blank" in prompt and "pure white" in prompt and "OVERRIDE" in prompt        # the real artwork is added in code
    assert "flexible" not in prompt and "branded box" not in prompt and aspect == "1:1"

    back = LOGO_AT_LEFT_CHEST + [{"kind": "logo", "view": "back", "x": 0.5, "y": 0.45, "width_cm": 30, "height_cm": 36}]
    prompt, aspect = mockup_prompt("Hoodie", questions, {"decoration_placement": back})
    assert "front and back views side by side" in prompt and aspect == "16:9"


def _studio_photo(two_views: bool) -> bytes:
    """A dark hoodie shape on white, like the image model's blank product photo."""
    w, h = (1600, 900) if two_views else (900, 900)
    image = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(image)
    views = [(0, w // 2 if two_views else w)] + ([(w // 2, w)] if two_views else [])
    for left, right in views:
        gw, gh = (right - left) * 0.8, h * 0.9                 # the garment: 80% of the view's width, 90% of its height
        x0, y0 = left + (right - left) * 0.1, h * 0.05
        draw.rectangle((x0, y0, x0 + gw, y0 + gh), fill=(40, 40, 44))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def test_the_real_pictures_are_drawn_on_the_photo_at_the_placed_spot_and_size():
    red = io.BytesIO()
    Image.new("RGB", (100, 100), (255, 0, 0)).save(red, "PNG")
    placements = [{"kind": "logo", "view": "front", "x": 0.5, "y": 0.5, "width_cm": 29, "height_cm": 29,
                   "file_id": "red"}]
    out = Image.open(io.BytesIO(compose_artwork(_studio_photo(False), "hoodie", placements, {"red": red.getvalue()})))
    assert out.getpixel((450, 450))[:3] == (255, 0, 0)   # centred on the garment
    assert out.getpixel((450, 60))[0] < 80                                                      # the rest is untouched
    # a back placement lands in the right-hand half only
    both = placements + [{**placements[0], "view": "back", "y": 0.4}]
    out = Image.open(io.BytesIO(compose_artwork(_studio_photo(True), "hoodie", both, {"red": red.getvalue()})))
    assert out.getpixel((400, 450))[1] < 80 and out.getpixel((1200, 380))[1] < 80
    assert compose_artwork(_studio_photo(False), "hoodie", [], {})                                # nothing to draw is fine


async def test_customer_makes_mockups_from_the_form_with_their_logo(api):
    token, other = await _login(api, f"mock-{api.run}@example.com"), await _login(api, f"mock2-{api.run}@example.com")
    api.ctx.mockups = fake = FakeMaker()
    order = (await api.post("/orders", json={"option": "hoodie"}, headers=_auth(token))).json()["order_id"]
    logo = (await api.post(f"/orders/{order}/files", files={"file": ("logo.png", PNG, "image/png")},
                           headers=_auth(token))).json()
    answers = {"colors": ["black"], "decoration_method": "embroidery", "artwork": [logo],
               "decoration_placement": [{**LOGO_AT_LEFT_CHEST[0], "file_id": logo["file_id"]}]}

    r = await api.post(f"/orders/{order}/mockups", json={"answers": answers}, headers=_auth(token))
    assert r.status_code == 201 and r.json()["logo_used"] and r.json()["remaining"] == 4
    assert fake.calls[0]["references"] == [] and "completely blank" in fake.calls[0]["prompt"]   # artwork added in code
    got = await api.get(f"/orders/{order}/mockups/{r.json()['mockup_id']}", headers=_auth(token))
    assert got.content[1:4] == b"PNG" and "sandbox" in got.headers["content-security-policy"]
    assert (await api.get(f"/orders/{order}/mockups/{r.json()['mockup_id']}", headers=_auth(other))).status_code == 404
    # Mockups are not order files: nothing new for the factory or the documents list
    assert await api.ctx.accounts.file_ids(order) == {logo["file_id"]}

    # A file from another order is not used as the logo
    foreign = (await api.post("/orders", json={"option": "hoodie"}, headers=_auth(other))).json()["order_id"]
    their = (await api.post(f"/orders/{foreign}/files", files={"file": ("x.png", PNG, "image/png")},
                            headers=_auth(other))).json()
    r = await api.post(f"/orders/{order}/mockups", json={"answers": {"artwork": [their]}}, headers=_auth(token))
    assert r.status_code == 201 and not r.json()["logo_used"]

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


def test_the_brief_is_a_numbered_markdown_file_that_overrides_the_product_name():
    questions = get_questions("apparel", "hoodie")
    brief, back = mockup_brief("Hoodie", questions, {"hoodie_style": "zip-up", "collar": "crew neck, no hood",
                                                     "needed_by": "flexible", "decoration_placement": LOGO_AT_LEFT_CHEST})
    assert brief.startswith("# Product brief: custom Hoodie") and not back
    assert "1. **Hoodie style** (Type): zip-up" in brief and "(Collar): crew neck, no hood" in brief
    assert "OVERRIDE" in brief and "no hood" in brief and "flexible" not in brief
    assert "Check the picture against requirements 1 to 2" in brief


def test_the_editing_pass_gets_a_numbered_guide_and_a_written_instruction():
    placements = [{"kind": "logo", "view": "front", "x": 0.5, "y": 0.4, "width_cm": 20, "height_cm": 10, "file_id": "a"},
                  {"kind": "label", "view": "back", "x": 0.5, "y": 0.2, "width_cm": 5, "height_cm": 2.5, "file_id": "b"}]
    photo = _studio_photo(True)
    boxes = target_boxes(photo, "hoodie", placements)
    assert [p["file_id"] for p, _ in boxes] == ["a", "b"]
    (_, front), (_, back) = boxes
    assert front[0] < front[2] <= 800 and back[0] >= 800                    # each box is in its own half
    assert (front[2] - front[0]) > (back[2] - back[0]) * 3                  # 20 cm is much wider than 5 cm
    guide = Image.open(io.BytesIO(artwork_guide(photo, boxes))).convert("RGB")
    assert guide.getpixel((front[0], (front[1] + front[3]) // 2)) == (255, 0, 200)   # the box outline
    prompt = artwork_prompt(boxes, [3, 4], "embroidery")
    assert "Box 1 (front view, 20 x 10 cm logo): artwork = image 3" in prompt
    assert "Box 2 (back view, 5 x 2.5 cm label): artwork = image 4" in prompt
    assert "really embroidery" in prompt and "Remove the magenta boxes" in prompt
