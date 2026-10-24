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


def test_every_product_has_a_quantity_question():
    for market in MARKETS.values():
        for option_id, option in market.options.items():
            if option.questions:
                sections = {q.section for q in get_questions(market.id, option_id)}
                assert "quantity" in sections, f"{market.id}/{option_id} has no quantity question"


def test_custom_option_has_no_fixed_questions():
    assert get_questions("apparel", "custom") == []
