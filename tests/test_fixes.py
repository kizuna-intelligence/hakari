from datetime import date, datetime, timezone

from hakari.contract.model import FileChange, Landing
from hakari.domain.fixes import compute_fixes, prepare
from hakari.domain.windows import previous_window, recent_window
from hakari.contract.defaults import DEFAULTS


def _landing(sha, subject, paths, day, body=""):
    return Landing(
        sha,
        datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc),
        subject,
        body,
        tuple(FileChange(path, 1, 1) for path in paths),
    )


def _config():
    import copy

    return copy.deepcopy(DEFAULTS)


def test_prepare_drops_nonproduction_and_marks_cross_demotion():
    config = _config()
    landings = [
        _landing("a", "fix: app", ["a/app.py"], date(2026, 8, 1)),
        _landing("b", "docs: docs", ["docs/readme.md"], date(2026, 8, 1)),
        _landing(
            "c",
            "chore: version",
            ["a/__init__.py", "b/__init__.py"],
            date(2026, 8, 2),
        ),
        _landing("d", "chore: version", ["a/__init__.py"], date(2026, 8, 3)),
        _landing(
            "e",
            "chore: release",
            ["a/app.py", "b/pyproject.toml"],
            date(2026, 8, 4),
        ),
    ]
    prepared = prepare(landings, config)
    assert [item.landing.sha for item in prepared] == ["a", "c", "d", "e"]
    assert prepared[1].demoted_from_cross
    assert prepared[1].components == frozenset({"a", "b"})
    assert prepared[1].cross_components == frozenset()
    assert not prepared[2].demoted_from_cross
    assert prepared[3].demoted_from_cross
    assert prepared[3].components == frozenset({"a"})
    assert prepared[3].cross_components == frozenset({"a"})


def test_excluded_version_file_does_not_demote_cross_landing():
    config = _config()
    landing = _landing(
        "vendor",
        "chore: update vendor",
        ["app/app.py", "cli/example/_vendor/example_package/__init__.py"],
        date(2026, 8, 5),
    )

    prepared = prepare([landing], config)

    assert prepared[0].prod_paths == ("app/app.py",)
    assert prepared[0].cross_components == frozenset({"app"})
    assert not prepared[0].demoted_from_cross

    recent = recent_window(date(2026, 8, 10), 30)
    result = compute_fixes(prepared, recent, previous_window(recent), config)
    assert result.details["cross"]["landings"] == 0
    assert result.details["cross"]["version_only_excluded"] == 0


def test_fix_statistics_count_each_landing_once_and_make_cross_matrix():
    config = _config()
    config["components"] = {"a": ["a/**"], "b": ["b/**"]}
    landings = [
        _landing("fix", "fix: x", ["a/app.py"], date(2026, 8, 1)),
        _landing("feat", "feat: x", ["b/main.go"], date(2026, 8, 2)),
        _landing("cross", "fix: cross", ["a/app.py", "b/main.go"], date(2026, 8, 3)),
        _landing("version", "chore: version", ["a/__init__.py", "b/__init__.py"], date(2026, 8, 4)),
    ]
    prepared = prepare(landings, config)
    recent = recent_window(date(2026, 8, 10), 30)
    result = compute_fixes(prepared, recent, previous_window(recent), config)
    total = result.details["total"]
    assert total["landings"] == 4
    assert total["fix_share"] == 0.5
    assert total["fix_to_feat"] == 2.0
    assert total["by_type"]["fix"] == 2
    assert result.details["components"]["a"]["touching"]["landings"] == 3
    assert result.details["components"]["a"]["exclusive"]["landings"] == 1
    # The two-component version landing is the sole demotion; it is not a
    # cross landing because excluding version files leaves no components.
    assert result.details["cross"] == {
        "landings": 1,
        "share": 0.25,
        "version_only_excluded": 1,
        "pairs": [{"a": "a", "b": "b", "landings": 1}],
    }
