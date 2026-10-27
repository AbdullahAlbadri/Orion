import io

from PIL import Image

from orion.graph.manufacturer_request import PLACEMENT_DIAGRAM, placement_diagram, render_request
from orion.spec import ProductSpec
from orion.tools import placement_diagram as drawing

PLACEMENTS = [
    {"kind": "logo", "view": "front", "x": 0.63, "y": 0.3, "width_cm": 9, "height_cm": 7, "file_id": "f1"},
    {"kind": "label", "view": "back", "x": 0.5, "y": 0.17, "width_cm": 5, "height_cm": 2.5, "file_id": "f2"},
]


def _picture() -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", (50, 50), (255, 0, 0, 255)).save(out, "PNG")
    return out.getvalue()


def test_the_drawing_shows_each_view_with_a_placement_and_the_customer_picture():
    png = drawing.render("hoodie", PLACEMENTS, {"f1": _picture()})
    image = Image.open(io.BytesIO(png))
    assert image.format == "PNG" and image.width > image.height * 0.8
    assert (255, 0, 0) in {p[:3] for p in image.convert("RGB").getdata()}      # the logo's own colour is on the garment
    only_front = Image.open(io.BytesIO(drawing.render("hoodie", PLACEMENTS[:1], {})))
    assert only_front.width < image.width                          # no back view when nothing is placed there


def test_nothing_to_draw_without_placements_and_an_unreadable_picture_still_draws_the_box():
    assert drawing.render("tee", [], {}) is None
    assert drawing.render("tee", PLACEMENTS, {"f1": b"not an image"})


def test_the_request_mentions_the_drawing_only_when_there_are_placements():
    spec = ProductSpec(market="apparel", option="hoodie")
    assert placement_diagram(spec) is None
    spec.answers["decoration_placement"] = PLACEMENTS
    assert placement_diagram(spec)["placements"] == PLACEMENTS and placement_diagram(spec)["mockup"]
    zh = {"product_zh": "卫衣", "fields": []}
    assert PLACEMENT_DIAGRAM in render_request(spec, zh, "ord_1")
    spec.answers.pop("decoration_placement")
    assert PLACEMENT_DIAGRAM not in render_request(spec, zh, "ord_1")
