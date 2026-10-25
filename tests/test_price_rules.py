import pytest

from orion.tools.price_guard import price_violation
from orion.tools.prices import ExtractedPrice, check_price, normalize_currency


@pytest.mark.parametrize(
    "text",
    [
        "单价 28元",
        "Can you do ¥25?",
        "Our budget is limited",
        "能不能便宜一点",
        "please give 10% off",
        "打9折可以吗",
        "price: 4.5 per piece",
        "USD 3.20 FOB",
        "هل يوجد خصم",
        "target price 20",
    ],
)
def test_guard_blocks_prices_and_negotiation(text):
    assert price_violation(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        "您好！请报价，并告知起订量、打样费用和交期。",
        "总数量：150 件\n尺码数量：S 20, M 50, L 50, XL 30",
        "面料克重：350 GSM，左胸刺绣 8cm",
        "Please quote unit price, currency and lead time for 500 pcs.",
        "1) 单价、币种、是否含税、是否含运费（或贸易条款 EXW/FOB 等）",
    ],
)
def test_guard_allows_quote_requests_and_quantities(text):
    assert price_violation(text) is None


MESSAGE = "您好，卫衣 500件 单价28.5元/件，含税，FOB深圳。打样费200元，交期25天。"


def _price(**overrides):
    base = dict(
        unit_price=28.5, currency="元", unit="piece", quantity=500,
        shipping_included=None, incoterm="FOB", tax_included=True, quoted_text="单价28.5元/件",
    )
    return ExtractedPrice(**(base | overrides))


def test_clear_price_is_verified():
    check = check_price(_price(), MESSAGE)
    assert check.status == "verified" and check.currency == "CNY" and check.problems == []


def test_number_not_in_message_is_untrusted():
    check = check_price(_price(unit_price=18.5, quoted_text="单价18.5元/件"), MESSAGE)
    assert not check.trusted_text


def test_number_not_in_quote_is_untrusted():
    check = check_price(_price(unit_price=25), MESSAGE)
    assert not check.trusted_text


@pytest.mark.parametrize(
    "overrides",
    [{"unit": "carton"}, {"currency": None}, {"tax_included": None}, {"incoterm": None}],
)
def test_ambiguous_price_is_unverified(overrides):
    check = check_price(_price(**overrides), MESSAGE)
    assert check.trusted_text and check.status == "extracted" and check.problems


def test_currency_normalization():
    assert normalize_currency("RMB") == "CNY"
    assert normalize_currency("US$") == "USD"
    assert normalize_currency("gold coins") is None


def test_sample_and_shipping_prices_are_checked_by_their_own_rules():
    message = "单价45元/件，含税，FOB深圳。打样费200元。海运到利雅得运费800元，约25-30天到门。开模费500元"
    sample = ExtractedPrice(charge="sample", unit_price=200, currency="元", unit="order", quoted_text="打样费200元")
    shipping = ExtractedPrice(charge="shipping", unit_price=800, currency="元", unit="order",
                              quoted_text="海运到利雅得运费800元")
    mould = ExtractedPrice(charge="other", unit_price=500, currency="元", unit="order", quoted_text="开模费500元")
    # No per-piece / tax / shipping questions for a sample or freight amount
    assert check_price(sample, message).status == "verified"
    assert check_price(shipping, message).status == "verified"
    # Other charges are kept but always go to the team
    other = check_price(mould, message)
    assert other.trusted_text and other.status == "extracted"
    # A product price still has to be per piece
    per_order = ExtractedPrice(unit_price=45, currency="元", unit="order", tax_included=True, incoterm="FOB",
                               quoted_text="单价45元/件")
    assert "not per piece" in " ".join(check_price(per_order, message).problems)
