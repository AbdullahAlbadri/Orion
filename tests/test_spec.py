import pytest

from orion.config.markets import MARKETS, get_questions
from orion.spec import QUANTITY_ID, SIZE_TABLE_ID, InvalidAnswer, ProductSpec, Question, validate_answer


def test_size_table_from_text_sets_quantity():
    q = Question(id="size_breakdown", prompt="", type="size_table")
    table = validate_answer(q, "s:20, M=50\nxl x 30")
    assert table == {"S": 20, "M": 50, "XL": 30}

    spec = ProductSpec(market="apparel", option="hoodie")
    spec.set_answer("size_breakdown", table)
    assert spec.quantity == 100


@pytest.mark.parametrize("raw", ["", "S:abc", "S:0", "large please"])
def test_size_table_rejects_bad_input(raw):
    with pytest.raises(InvalidAnswer):
        validate_answer(Question(id="size_breakdown", prompt="", type="size_table"), raw)


def test_choice_is_case_insensitive_and_strict():
    q = Question(id="x", prompt="", type="choice", choices=["Embroidery", "none"])
    assert validate_answer(q, " embroidery ") == "Embroidery"
    with pytest.raises(InvalidAnswer):
        validate_answer(q, "sequins")


def test_number():
    q = Question(id="gsm", prompt="", type="number")
    assert validate_answer(q, "1,200") == 1200
    assert validate_answer(q, "2.5") == 2.5
    for bad in ["heavy", "-3", "0"]:
        with pytest.raises(InvalidAnswer):
            validate_answer(q, bad)


def test_market_config_is_consistent():
    for market in MARKETS.values():
        for option_id in market.options:
            ids = [q.id for q in get_questions(market.id, option_id)]
            assert len(ids) == len(set(ids)), f"duplicate question ids in {market.id}/{option_id}"
            for q in get_questions(market.id, option_id):
                if q.type == "choice":
                    assert q.choices, f"{q.id} has no choices"


PLACEMENT = Question(id="decoration_placement", prompt="", type="placement")


def test_placements_are_validated():
    good = [{"kind": "logo", "view": "front", "x": 0.6234, "y": 0.3, "width_cm": 9.04, "height_cm": 6}]
    assert validate_answer(PLACEMENT, good) == [
        {"kind": "logo", "view": "front", "x": 0.623, "y": 0.3, "width_cm": 9.0, "height_cm": 6.0}
    ]
    assert validate_answer(PLACEMENT, "left chest 8cm") == "left chest 8cm"   # text still accepted
    for bad in (
        [{"kind": "logo", "view": "front", "x": 1.4, "y": 0.3, "width_cm": 9, "height_cm": 6}],    # off the garment
        [{"kind": "logo", "view": "front", "x": 0.5, "y": 0.3, "width_cm": 90, "height_cm": 6}],   # too big
        [{"kind": "sticker", "view": "front", "x": 0.5, "y": 0.3, "width_cm": 9, "height_cm": 6}],
        [{"kind": "logo", "view": "side", "x": 0.5, "y": 0.3, "width_cm": 9, "height_cm": 6}],
        [{"kind": "logo"}],
        [],
    ):
        with pytest.raises(InvalidAnswer):
            validate_answer(PLACEMENT, bad)


def test_placement_words_use_the_wearers_left():
    from orion.spec import describe_placement, format_answer

    front_right_of_picture = {"kind": "logo", "view": "front", "x": 0.65, "y": 0.3, "width_cm": 9, "height_cm": 6}
    back_left_of_picture = {"kind": "logo", "view": "back", "x": 0.3, "y": 0.5, "width_cm": 9, "height_cm": 6}
    assert describe_placement(front_right_of_picture) == "logo, front, wearer's left chest, 9 x 6 cm"
    assert describe_placement(back_left_of_picture) == "logo, back, wearer's left middle, 9 x 6 cm"
    label = {"kind": "label", "view": "back", "x": 0.5, "y": 0.1, "width_cm": 5, "height_cm": 2.5}
    assert format_answer([front_right_of_picture, label]) == (
        "logo, front, wearer's left chest, 9 x 6 cm; label, back, centre neck, 5 x 2.5 cm"
    )


def test_placement_questions_get_the_products_drawing():
    for option in ("hoodie", "oversized_tee", "abaya", "tote_bag", "corporate_uniform"):
        placements = [q for q in get_questions("apparel", option) if q.type == "placement"]
        assert len(placements) == 1 and placements[0].mockup


def test_every_question_has_arabic_and_aligned_choices():
    for market in MARKETS.values():
        assert market.name_ar
        for option_id, option in market.options.items():
            assert option.name_ar, option_id
            for q in get_questions(market.id, option_id):
                assert q.prompt_ar, f"{option_id}/{q.id} has no Arabic prompt"
                assert not q.hint or q.hint_ar, f"{option_id}/{q.id} has no Arabic hint"
                if q.type == "choice":
                    assert len(q.choices_ar) == len(q.choices), f"{option_id}/{q.id} Arabic choices misaligned"
                    assert not q.cost_tiers or len(q.cost_tiers) == len(q.choices)
                    assert all(0 <= tier <= 3 for tier in q.cost_tiers)


def test_every_product_has_a_quantity_question():
    for market in MARKETS.values():
        for option_id, option in market.options.items():
            if option.questions:
                sections = {q.section for q in get_questions(market.id, option_id)}
                assert "quantity" in sections, f"{market.id}/{option_id} has no quantity question"


def test_custom_option_asks_for_a_description_first():
    ids = [q.id for q in get_questions("apparel", "custom")]
    assert ids[:2] == ["description", "reference_images"] and "quantity" in ids


def test_details_without_a_section_are_sorted_by_wording():
    from orion.graph.pre_receipt import guess_section

    assert guess_section("lining_material", "Lining material") == "quality"
    assert guess_section("delivery_date", "Delivery date") == "quantity"
    assert guess_section("hood_shape", "Hood shape") == "design"
    assert guess_section("x", "نوع القماش") == "quality"

def test_color_zones_are_checked_against_the_garment_and_read_as_plain_colour_names():
    from orion.config.markets import get_questions
    from orion.spec import InvalidAnswer, format_answer, is_color_zones, validate_answer

    q = next(x for x in get_questions("apparel", "hoodie") if x.type == "color_zones")
    assert {z["id"] for z in q.zones} == {"body", "sleeves", "hood", "cuffs", "pocket"}
    value = validate_answer(q, {"body": "#1B2A4A", "hood": "#FFFFFF"})
    assert value == {"body": "#1b2a4a", "hood": "#ffffff"} and is_color_zones(value)
    assert format_answer(value) == "body: navy (#1b2a4a); hood: white (#ffffff)"
    for bad in ({"wheels": "#111111"}, {"body": "navy"}, {"body": "#12345"}, {}):
        try:
            validate_answer(q, bad)
        except InvalidAnswer:
            continue
        raise AssertionError(f"{bad} should be refused")


def test_the_manufacturer_drawing_shows_the_part_colours_even_without_logos():
    import io

    from PIL import Image

    from orion.graph.manufacturer_request import placement_diagram
    from orion.spec import ProductSpec
    from orion.tools import placement_diagram as drawing

    spec = ProductSpec(market="apparel", option="hoodie")
    assert placement_diagram(spec) is None
    spec.answers["color_zones"] = {"hood": "#8a1c2b"}
    d = placement_diagram(spec)
    assert d["colors"] == {"hood": "#8a1c2b"} and d["placements"] == []
    png = Image.open(io.BytesIO(drawing.render(d["mockup"], d["placements"], {}, d["colors"]))).convert("RGB")
    assert (0x8a, 0x1c, 0x2b) in {png.getpixel((x, y)) for x in range(0, png.width, 3) for y in range(0, 300, 3)}


def test_a_colour_patch_is_placed_like_a_logo_and_described_with_its_colour():
    import io

    from PIL import Image

    from orion.config.markets import get_questions
    from orion.spec import InvalidAnswer, describe_placement, validate_answer
    from orion.tools import placement_diagram as drawing
    from orion.tools.mockup import artwork_prompt, target_boxes

    q = next(x for x in get_questions("apparel", "hoodie") if x.type == "placement")
    patch = {"kind": "color", "view": "front", "x": 0.5, "y": 0.6, "width_cm": 30, "height_cm": 4, "color": "#C81E28"}
    value = validate_answer(q, [patch])
    assert value[0]["color"] == "#c81e28" and "file_id" not in value[0]
    assert describe_placement(value[0]) .startswith("colour patch red (#c81e28), front")
    try:
        validate_answer(q, [{**patch, "color": "red"}])
        raise AssertionError("a patch without a HEX colour must be refused")
    except InvalidAnswer:
        pass

    png = Image.open(io.BytesIO(drawing.render("hoodie", value, {}))).convert("RGB")
    assert (0xc8, 0x1e, 0x28) in {png.getpixel((x, y)) for x in range(0, png.width, 3) for y in range(300, 700, 3)}
    photo = Image.new("RGB", (900, 900), "white")
    photo.paste((40, 40, 44), (90, 45, 810, 855))
    buf = io.BytesIO()
    photo.save(buf, "PNG")
    boxes = target_boxes(buf.getvalue(), "hoodie", value)
    assert "re-colour the garment's fabric inside this box to red, exactly #c81e28" in artwork_prompt(boxes, [None])


# --- every market's questions ---------------------------------------------------------

def test_every_market_has_clean_questions_in_both_languages():
    from orion.config.markets import MARKETS, get_questions

    assert {"apparel", "ecom_packaging", "tech_accessories"} <= set(MARKETS)
    for market in MARKETS.values():
        for option_id in market.options:
            questions = get_questions(market.id, option_id)
            ids = [q.id for q in questions]
            assert len(ids) == len(set(ids)), (market.id, option_id, "duplicate question ids")
            assert any(q.id == QUANTITY_ID or q.id == SIZE_TABLE_ID for q in questions), (market.id, option_id)
            for q in questions:
                assert q.prompt and q.prompt_ar, (market.id, option_id, q.id)
                if q.type == "choice":
                    assert len(q.choices) == len(q.choices_ar) >= 2, (market.id, option_id, q.id)
                    assert not q.cost_tiers or len(q.cost_tiers) == len(q.choices), (market.id, option_id, q.id)


def test_new_markets_do_not_borrow_garment_drawings():
    from orion.config.markets import MARKETS

    for key in ("ecom_packaging", "tech_accessories"):
        assert all(o.mockup is None for o in MARKETS[key].options.values())
