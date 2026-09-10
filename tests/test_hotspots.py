import copy
from datetime import date, datetime, timezone

from hakari.contract.defaults import DEFAULTS
from hakari.contract.history import InMemoryTree
from hakari.contract.model import FileChange, Landing
from hakari.domain.fixes import prepare
from hakari.domain.hotspots import compute_hotspots
from hakari.domain.windows import hotspot_window


def test_hotspots_use_lines_min_and_rework_boundaries_and_zero_lines_is_safe():
    config = copy.deepcopy(DEFAULTS)
    config["hotspot"]["min_lines"] = 800
    config["hotspot"]["min_rework"] = 1000
    landings = [
        Landing(
            "create-only",
            datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
            "fix: created only",
            "",
            (
                FileChange("created-only.py", 1000, 0),
            ),
        ),
        Landing(
            "create-plus",
            datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
            "fix: create plus",
            "",
            (
                FileChange("created-plus.py", 1000, 0),
            ),
        ),
        Landing(
            "create-plus-fix",
            datetime(2026, 8, 3, 12, tzinfo=timezone.utc),
            "fix: create plus fixed",
            "",
            (
                FileChange("created-plus.py", 1200, 0),
            ),
        ),
        Landing(
            "preexisting",
            datetime(2026, 8, 4, 12, tzinfo=timezone.utc),
            "fix: old file",
            "",
            (
                FileChange("preexisting.py", 1700, 0),
            ),
        ),
        Landing(
            "near-min",
            datetime(2026, 8, 5, 12, tzinfo=timezone.utc),
            "fix: near min",
            "",
            (
                FileChange("near-min.py", 500, 0),
            ),
        ),
        Landing(
            "near-max",
            datetime(2026, 8, 6, 12, tzinfo=timezone.utc),
            "fix: near max",
            "",
            (
                FileChange("near-max.py", 999, 0),
            ),
        ),
        Landing(
            "boundary",
            datetime(2026, 8, 7, 12, tzinfo=timezone.utc),
            "fix: boundary",
            "",
            (
                FileChange("boundary-min.py", 2000, 0),
            ),
        ),
        Landing(
            "zero",
            datetime(2026, 8, 8, 12, tzinfo=timezone.utc),
            "fix: zero",
            "",
            (
                FileChange("zero.py", 120, 0),
            ),
        ),
    ]

    result = compute_hotspots(
        prepare(landings, config),
        InMemoryTree(
            {
                "created-only.py": 1000,
                "created-plus.py": 1000,
                "preexisting.py": 1000,
                "near-min.py": 1000,
                "near-max.py": 1000,
                "boundary-min.py": 800,
                "zero.py": 0,
            }
        ),
        hotspot_window(date(2026, 8, 10), 90),
        config,
        frozenset({("create-only", "created-only.py"), ("create-plus", "created-plus.py")}),
    )

    assert result.value == 2
    assert result.details["total"] == {
        "count": 2,
        "files_over_min_lines": 5,
        "max_file_lines": 1000,
        "below_min_rework": 3,
    }
    assert result.details["files"] == [
        {
            "path": "preexisting.py",
            "component": "(root)",
            "lines": 1000,
            "commits": 1,
            "churn": 1700,
            "created_lines": 0,
            "rework": 1700,
        },
        {
            "path": "created-plus.py",
            "component": "(root)",
            "lines": 1000,
            "commits": 2,
            "churn": 2200,
            "created_lines": 1000,
            "rework": 1200,
        },
    ]
    assert result.details["near"] == [
        {
            "path": "near-max.py",
            "component": "(root)",
            "lines": 1000,
            "commits": 1,
            "churn": 999,
            "created_lines": 0,
            "rework": 999,
        },
        {
            "path": "near-min.py",
            "component": "(root)",
            "lines": 1000,
            "commits": 1,
            "churn": 500,
            "created_lines": 0,
            "rework": 500,
        },
    ]
    included_paths = {item["path"] for item in result.details["files"] + result.details["near"]}
    assert "created-only.py" not in included_paths
    assert "boundary-min.py" not in included_paths
    assert "zero.py" not in included_paths


def test_hotspot_sort_is_rework_first_then_lines_then_path():
    config = copy.deepcopy(DEFAULTS)
    config["hotspot"]["min_rework"] = 1000
    landings = [
        Landing(
            "steady",
            datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
            "fix: steady",
            "",
            (
                FileChange("x/steady.py", 2000, 0),
            ),
        ),
        Landing(
            "created",
            datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
            "fix: created-heavy",
            "",
            (FileChange("y/created-heavy.py", 3100, 0),),
        ),
        Landing(
            "created-fix",
            datetime(2026, 8, 3, 12, tzinfo=timezone.utc),
            "fix: created-heavy again",
            "",
            (FileChange("y/created-heavy.py", 1900, 0),),
        ),
    ]

    result = compute_hotspots(
        prepare(landings, config),
        InMemoryTree({"x/steady.py": 1000, "y/created-heavy.py": 1000}),
        hotspot_window(date(2026, 8, 10), 90),
        config,
        frozenset({("created", "y/created-heavy.py")}),
    )

    assert [item["path"] for item in result.details["files"]] == [
        "x/steady.py",
        "y/created-heavy.py",
    ]
    assert result.details["files"][0]["rework"] == 2000
    assert result.details["files"][1]["rework"] == 1900
    assert result.details["files"][0]["created_lines"] == 0
    assert result.details["files"][1]["created_lines"] == 3100


def test_hotspots_lines_boundary_and_zero_line_file_is_safe():
    config = copy.deepcopy(DEFAULTS)
    config["hotspot"]["min_lines"] = 10
    config["hotspot"]["min_rework"] = 1000
    result = compute_hotspots(
        prepare(
            [
                Landing(
                    "a",
                    datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
                    "fix: boundary",
                    "",
                    (FileChange("small.py", 1200, 0), FileChange("zero.py", 10, 0)),
                )
            ],
            config,
        ),
        InMemoryTree({"small.py": 10, "zero.py": 0}),
        hotspot_window(date(2026, 8, 10), 90),
        config,
        frozenset(),
    )
    assert result.value == 0
    assert result.details["near"] == []
