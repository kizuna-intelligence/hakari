import pytest

import hakari.app as app
import hakari.platform.gitcli as gitcli
from hakari.contract.model import MeasureRequest
from hakari.platform.gitcli import GitError, parse_git_version


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("git version 2.43.0", (2, 43, 0)),
        ("git version 2.39.5 (Apple Git-154)", (2, 39, 5)),
        ("not a git version", (0, 0, 0)),
    ),
)
def test_parse_git_version(text, expected):
    assert parse_git_version(text) == expected


def test_git_version_uses_parser_without_calling_real_git(monkeypatch):
    def fake_run_git(repo_root, args):
        assert repo_root == "/repo"
        assert args == ["--version"]
        return "git version 2.39.5 (Apple Git-154)"

    monkeypatch.setattr(gitcli, "run_git", fake_run_git)
    assert gitcli.git_version("/repo") == (2, 39, 5)


def test_measure_rejects_git_before_2_31(monkeypatch):
    monkeypatch.setattr(app, "find_repo_root", lambda repo_dir: "/repo")
    monkeypatch.setattr(app, "git_version", lambda repo_root: (2, 30, 9))

    with pytest.raises(GitError) as exc_info:
        app.measure(MeasureRequest("/repo", None))

    assert str(exc_info.value) == (
        "git 2.31 以降が必要です(--diff-merges=first-parent を使うため)。現在: 2.30.9"
    )
