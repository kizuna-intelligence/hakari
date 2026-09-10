from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def to_local_date(dt: datetime, tz_name: str) -> date:
    return dt.astimezone(ZoneInfo(tz_name)).date()


def day_span(end: date, days: int) -> tuple[date, date]:
    return end - timedelta(days=days - 1), end
