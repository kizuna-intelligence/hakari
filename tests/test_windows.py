from datetime import date, datetime, timezone

from hakari.contract.model import FileChange, Landing
from hakari.domain.windows import (
    hotspot_window,
    in_window,
    previous_window,
    recent_window,
)


def test_windows_and_boundaries():
    recent = recent_window(date(2026, 8, 23), 30)
    assert recent.start == date(2026, 7, 25)
    assert recent.end == date(2026, 8, 23)
    assert previous_window(recent).end == date(2026, 7, 24)
    assert previous_window(recent).start == date(2026, 6, 25)
    assert hotspot_window(date(2026, 8, 23), 90).start == date(2026, 5, 26)
    landing = Landing(
        "sha",
        datetime(2026, 7, 25, tzinfo=timezone.utc),
        "fix: edge",
        "",
        (FileChange("a.py", 1, 0),),
    )
    assert in_window(landing, recent, "Asia/Tokyo")
