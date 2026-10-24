"""China working-day calendar for manufacturer deadlines.

Source: 国务院办公厅关于2026年部分节假日安排的通知 (State Council, 2025-11-04),
https://www.news.cn/20251104/76de5bdd2fb249b6a35c83b96115df8b/c.html
The notice for each next year is published around November: add it here when it is out.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

CHINA_TZ = ZoneInfo("Asia/Shanghai")


def _days(start: date, end: date) -> set[date]:
    return {start + timedelta(days=i) for i in range((end - start).days + 1)}


# Official days off (放假)
HOLIDAYS: set[date] = (
    _days(date(2026, 1, 1), date(2026, 1, 3))       # 元旦
    | _days(date(2026, 2, 15), date(2026, 2, 23))   # 春节
    | _days(date(2026, 4, 4), date(2026, 4, 6))     # 清明节
    | _days(date(2026, 5, 1), date(2026, 5, 5))     # 劳动节
    | _days(date(2026, 6, 19), date(2026, 6, 21))   # 端午节
    | _days(date(2026, 9, 25), date(2026, 9, 27))   # 中秋节
    | _days(date(2026, 10, 1), date(2026, 10, 7))   # 国庆节
)

# Weekend days that are official make-up working days (调休上班)
EXTRA_WORKDAYS: set[date] = {
    date(2026, 1, 4),
    date(2026, 2, 14), date(2026, 2, 28),
    date(2026, 5, 9),
    date(2026, 9, 20), date(2026, 10, 10),
}

KNOWN_YEARS = {2026}


def is_working_day(day: date, holidays: set[date] = HOLIDAYS, extra: set[date] = EXTRA_WORKDAYS) -> bool:
    if day in extra:
        return True
    return day.weekday() < 5 and day not in holidays


def add_working_days(
    start: datetime,
    days: int,
    holidays: set[date] = HOLIDAYS,
    extra: set[date] = EXTRA_WORKDAYS,
) -> datetime:
    """The moment `days` China working days after `start`, at the same China local time (returned in UTC).

    Days are counted from the next calendar day, so a message sent on Friday with days=3 is due
    on Wednesday, and one sent during Spring Festival starts counting after the holiday.
    """
    local = start.astimezone(CHINA_TZ)
    day, counted = local.date(), 0
    while counted < days:
        day += timedelta(days=1)
        if is_working_day(day, holidays, extra):
            counted += 1
    due = datetime.combine(day, time(local.hour, local.minute, local.second), tzinfo=CHINA_TZ)
    return due.astimezone(timezone.utc)
