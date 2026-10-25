import pytest

from orion.config.markets import MARKETS, get_questions
from orion.spec import InvalidAnswer, ProductSpec, Question, validate_answer


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


def test_every_product_has_a_quantity_question():
    for market in MARKETS.values():
        for option_id, option in market.options.items():
            if option.questions:
                sections = {q.section for q in get_questions(market.id, option_id)}
                assert "quantity" in sections, f"{market.id}/{option_id} has no quantity question"


def test_custom_option_has_no_fixed_questions():
    assert get_questions("apparel", "custom") == []
