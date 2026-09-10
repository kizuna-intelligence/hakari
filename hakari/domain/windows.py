from datetime import date, timedelta

from hakari.contract.model import Landing, Window
from hakari.platform.dates import day_span, to_local_date


def recent_window(as_of: date, days: int) -> Window:
    start, end = day_span(as_of, days)
    return Window(start=start, end=end, days=days)


def previous_window(recent: Window) -> Window:
    end = recent.start - timedelta(days=1)
    start = end - timedelta(days=recent.days - 1)
    return Window(start=start, end=end, days=recent.days)


def hotspot_window(as_of: date, days: int) -> Window:
    start, end = day_span(as_of, days)
    return Window(start=start, end=end, days=days)


def window_details(window: Window) -> dict:
    return {"start": window.start.isoformat(), "end": window.end.isoformat(), "days": window.days}


def in_window(landing: Landing, window: Window, tz_name: str) -> bool:
    return window.contains(to_local_date(landing.author_at, tz_name))
