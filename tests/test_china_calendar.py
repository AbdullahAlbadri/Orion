from datetime import datetime, timezone

from orion.config.china_calendar import CHINA_TZ, add_working_days, is_working_day


def _china(y, m, d, h=10):
    return datetime(y, m, d, h, tzinfo=CHINA_TZ)


def test_weekend_is_skipped():
    # Friday 23 Oct 2026 + 3 working days -> Wednesday 28 Oct, same local time
    due = add_working_days(_china(2026, 10, 23), 3)
    assert due.astimezone(CHINA_TZ) == _china(2026, 10, 28)
    assert due.tzinfo == timezone.utc


def test_spring_festival_pauses_the_clock():
    # Thu 12 Feb: Fri 13 (1), Sat 14 make-up workday (2), 15-23 holiday, Tue 24 (3)
    assert add_working_days(_china(2026, 2, 12), 3).astimezone(CHINA_TZ) == _china(2026, 2, 24)


def test_national_day_and_make_up_saturday():
    # Tue 29 Sep: Wed 30 (1), 1-7 Oct holiday, Thu 8 (2), Fri 9 (3)
    assert add_working_days(_china(2026, 9, 29), 3).astimezone(CHINA_TZ) == _china(2026, 10, 9)
    assert is_working_day(_china(2026, 10, 10).date())       # Saturday make-up day
    assert not is_working_day(_china(2026, 10, 11).date())   # normal Sunday


def test_utc_input_uses_china_date():
    # 20:00 UTC Friday is already Saturday 04:00 in China
    start = datetime(2026, 10, 23, 20, tzinfo=timezone.utc)
    assert add_working_days(start, 1).astimezone(CHINA_TZ) == _china(2026, 10, 26, 4)
