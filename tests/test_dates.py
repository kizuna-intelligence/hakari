from datetime import date, datetime, timezone

from hakari.platform.dates import day_span, to_local_date


def test_utc_late_night_is_next_day_in_tokyo():
    value = datetime(2026, 8, 23, 23, 30, tzinfo=timezone.utc)
    assert to_local_date(value, "Asia/Tokyo") == date(2026, 8, 24)


def test_day_span_is_inclusive():
    end = date(2026, 8, 23)
    assert day_span(end, 30) == (date(2026, 7, 25), end)
    assert day_span(end, 90) == (date(2026, 5, 26), end)
