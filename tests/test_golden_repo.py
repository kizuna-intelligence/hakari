from datetime import date

from hakari.app import MeasureRequest, measure
from hakari.external.git_history import read_creations, read_history

from tests.repo_builder import AS_OF, build_golden_repo, build_merge_repo


def test_golden_metrics_are_hand_counted(tmp_path):
    root = build_golden_repo(str(tmp_path / "golden"))
    document = measure(MeasureRequest(root, AS_OF))
    fixes = document["metrics"]["fixes"]
    total = fixes["total"]
    assert fixes["window"] == {
        "start": "2026-07-25",
        "end": "2026-08-23",
        "days": 30,
    }
    # #4-#16, #20, #21 touch production files in the recent window: 15 landings.
    assert total["landings"] == 15
    # Six fix plus two hotfix landings are fix types: 8 / 15.
    assert total["fix_share"] == 0.533
    # The eight fix-type landings are against three feat landings.
    assert total["fix_to_feat"] == 2.667
    # #8 and the branch-derived #10 are typed hotfixes.
    assert total["hotfix_count"] == 2
    assert total["hotfix_typed"] == 2
    # #11 is both a revert type and a Revert subject.
    assert total["revert_count"] == 1
    assert total["unknown_share"] == 0.067
    assert total["by_type"] == {
        "fix": 6,
        "hotfix": 2,
        "feat": 3,
        "refactor": 0,
        "test": 0,
        "chore": 2,
        "docs": 0,
        "revert": 1,
        "other": 0,
        "unknown": 1,
    }
    assert fixes["components"]["a"]["touching"]["landings"] == 10
    assert fixes["components"]["a"]["exclusive"]["landings"] == 7
    assert fixes["cross"]["landings"] == 2
    assert fixes["cross"]["pairs"] == [{"a": "a", "b": "b", "landings": 2}]
    # Hand count: #16 has raw candidates {a/app.py, b/pyproject.toml}, then {a} after exclusion.
    # Hand count: #21 has raw candidates {a/__init__.py, b/__init__.py}, then {} after exclusion.
    assert fixes["cross"]["version_only_excluded"] == 2
    assert document["metrics"]["hotspots"]["files"] == [
        {
            "path": "a/app.py",
            "component": "a",
            "lines": 1000,
            "commits": 11,
            "churn": 1540,
            "created_lines": 0,
            "rework": 1540,
        },
    ]
    assert document["metrics"]["hotspots"]["near"] == [
        {
            "path": "b/main.go",
            "component": "b",
            "lines": 900,
            "commits": 7,
            "churn": 980,
            "created_lines": 0,
            "rework": 980,
        }
    ]


def test_read_creations_returns_additions_and_respects_since_window(tmp_path):
    root = build_golden_repo(str(tmp_path / "golden-creations"))
    all_creations = read_creations(root, "main", date(2026, 4, 1), "Asia/Tokyo")
    history = read_history(root, "main", date(2026, 4, 1), "Asia/Tokyo").landings()
    assert history
    initial_sha = history[-1].sha
    assert (initial_sha, "a/app.py") in all_creations
    assert (initial_sha, "b/main.go") in all_creations
    for landing in history:
        if landing.sha == initial_sha:
            continue
        for path in ("a/app.py", "b/main.go"):
            if any(change.path == path for change in landing.files):
                assert (landing.sha, path) not in all_creations

    recent_creations = read_creations(root, "main", date(2026, 8, 1), "Asia/Tokyo")
    assert not any(item[1] in {"a/app.py", "b/main.go"} for item in recent_creations)


def test_merge_commit_numstat_counts_as_landing(tmp_path):
    root = build_merge_repo(str(tmp_path / "merge"))
    history = read_history(root, "main", date(2026, 8, 1), "Asia/Tokyo")

    landings = history.landings()
    assert len(landings) == 1
    assert landings[0].subject == "Merge branch 'feature'"
    assert [(change.path, change.added, change.deleted) for change in landings[0].files] == [
        ("app/app.py", 1, 0)
    ]

    document = measure(MeasureRequest(root, date(2026, 8, 23)))
    assert document["metrics"]["fixes"]["total"]["landings"] == 1
