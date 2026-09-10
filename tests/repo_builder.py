import os
import subprocess
from datetime import date
from pathlib import Path


AS_OF = date(2026, 8, 23)


def _run(root: Path, *args: str, env: dict | None = None) -> None:
    subprocess.run([*args], cwd=root, check=True, env=env, capture_output=True)


def _commit(root: Path, when: str, subject: str, body: str = "") -> None:
    _run(root, "git", "add", "-A")
    environment = os.environ.copy()
    environment["GIT_AUTHOR_DATE"] = when
    environment["GIT_COMMITTER_DATE"] = when
    command = ["git", "commit", "-m", subject]
    if body:
        command.extend(["-m", body])
    _run(root, *command, env=environment)


def _append(root: Path, relative: str, line: str = "change\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _rewrite(root: Path, relative: str, count: int, marker: str) -> None:
    """先頭 count 行を marker で置き換える。ファイルの行数は変わらない。"""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    marker_line = marker if marker.endswith("\n") else f"{marker}\n"
    replacement = [marker_line] * min(count, len(lines))
    if replacement:
        lines[: len(replacement)] = replacement
        path.write_text("".join(lines), encoding="utf-8")


def build_golden_repo(dest: str) -> str:
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True)
    _run(root, "git", "-c", "init.defaultBranch=main", "init")
    _run(root, "git", "config", "user.name", "Golden Test")
    _run(root, "git", "config", "user.email", "golden@example.test")

    (root / "a").mkdir()
    (root / "b").mkdir()
    (root / "a/app.py").write_text("line\n" * 1000, encoding="utf-8")
    (root / "b/main.go").write_text("line\n" * 900, encoding="utf-8")
    _commit(root, "2026-05-01T10:00:00+09:00", "chore: init")

    commits = [
        ("2026-07-20T10:00:00+09:00", "feat(a): old feature", "a/app.py", ""),
        ("2026-07-24T10:00:00+09:00", "fix(a): before window", "a/app.py", ""),
        ("2026-07-25T10:00:00+09:00", "fix(a): window start edge", "a/app.py", ""),
        ("2026-07-28T14:30:00+09:00", "feat(a): add x", "a/app.py", ""),
        ("2026-08-01T09:00:00+09:00", "feat(b): add y", "b/main.go", ""),
        ("2026-08-02T09:00:00+09:00", "fix(b): y is broken", "b/main.go", ""),
        ("2026-08-03T09:00:00+09:00", "hotfix(b): urgent", "b/main.go", ""),
        (
            "2026-08-04T09:00:00+09:00",
            "Merge pull request #12 from org/fix/z",
            "a/app.py",
            "fix(a): via merge body",
        ),
        (
            "2026-08-05T09:00:00+09:00",
            "Merge pull request #13 from org/hotfix/w",
            "b/main.go",
            "",
        ),
        (
            "2026-08-06T09:00:00+09:00",
            'Revert "feat(a): add x"',
            "a/app.py",
            "",
        ),
        ("2026-08-07T09:00:00+09:00", "いろいろ直した(bug)", "a/app.py", ""),
        ("2026-08-08T09:00:00+09:00", "雑多な更新", "a/app.py", ""),
        ("2026-08-09T09:00:00+09:00", "feat: cross change", "a/app.py", "b/main.go"),
        ("2026-08-10T09:00:00+09:00", "fix: cross fix", "a/app.py", "b/main.go"),
    ]
    for index, (when, subject, first, second) in enumerate(commits):
        marker = f"commit {index}: {subject}"
        first_rewrite = first in {"a/app.py", "b/main.go"}
        if first_rewrite:
            _rewrite(root, first, 70, marker)
        else:
            _append(root, first)
        if second:
            second_rewrite = second in {"a/app.py", "b/main.go"}
            if second_rewrite:
                _rewrite(root, second, 70, marker)
            else:
                _append(root, second)
        _commit(root, when, subject, "" if not subject.startswith("Merge") else ("fix(a): via merge body" if "#12" in subject else ""))

    _rewrite(root, "a/app.py", 70, "chore release commit")
    _append(root, "b/pyproject.toml", "[project]\nversion = \"0.0.1\"\n")
    _commit(root, "2026-08-11T09:00:00+09:00", "chore(release): bump")

    _append(root, "a/tests/test_app.py", "def test_app():\n    pass\n")
    _commit(root, "2026-08-12T09:00:00+09:00", "test(a): add tests")

    _append(root, "docs/readme.md", "# readme\n")
    _commit(root, "2026-08-13T09:00:00+09:00", "docs: readme")

    _append(root, "a/node_modules/lib.js", "module.exports = {};\n")
    _commit(root, "2026-08-14T09:00:00+09:00", "chore: vendored")

    _append(root, "a/__init__.py", "__version__ = \"0.0.1\"\n")
    _append(root, "b/__init__.py", "__version__ = \"0.0.1\"\n")
    _commit(root, "2026-08-15T09:00:00+09:00", "chore: bump version")

    _rewrite(root, "b/main.go", 70, "late night fix")
    _commit(root, "2026-08-22T23:30:00+00:00", "fix(b): utc late night")

    (root / "hakari.toml").write_text(
        "[hakari.hotspot]\nmin_rework = 1000\n", encoding="utf-8"
    )
    return str(root)


def build_merge_repo(dest: str) -> str:
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True)
    _run(root, "git", "-c", "init.defaultBranch=main", "init")
    _run(root, "git", "config", "user.name", "Merge Test")
    _run(root, "git", "config", "user.email", "merge@example.test")

    (root / "app").mkdir()
    (root / "app/app.py").write_text("line\n" * 1000, encoding="utf-8")
    _commit(root, "2026-05-01T10:00:00+09:00", "chore: init")

    _run(root, "git", "checkout", "-b", "feature")
    _append(root, "app/app.py")
    _commit(root, "2026-08-20T10:00:00+09:00", "fix(app): merged change")

    _run(root, "git", "checkout", "main")
    environment = os.environ.copy()
    environment["GIT_AUTHOR_DATE"] = "2026-08-21T10:00:00+09:00"
    environment["GIT_COMMITTER_DATE"] = "2026-08-21T10:00:00+09:00"
    _run(
        root,
        "git",
        "merge",
        "--no-ff",
        "feature",
        "-m",
        "Merge branch 'feature'",
        env=environment,
    )

    (root / "hakari.toml").write_text(
        "[hakari.hotspot]\nmin_rework = 1000\n", encoding="utf-8"
    )
    return str(root)
