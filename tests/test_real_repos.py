import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from hakari.app import _init_detection, main
from hakari.transport.render_toml import render_hakari_toml


REPOSITORY = os.environ.get("HAKARI_TEST_REPO")


def _status(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _last_author_date(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%aI"],
        capture_output=True,
        text=True,
        check=True,
    )
    return datetime.fromisoformat(result.stdout.strip()).date().isoformat()


def test_real_repo_detection_and_measure_are_read_only(tmp_path):
    if not REPOSITORY:
        pytest.skip("set HAKARI_TEST_REPO to test an existing repository")
    root = Path(REPOSITORY)
    assert root.is_dir(), "HAKARI_TEST_REPO must point to an existing directory"
    before = _status(root)
    try:
        toml_text = render_hakari_toml(_init_detection(str(root)))
        assert "[hakari]" in toml_text
        try:
            import tomllib
        except ImportError:  # pragma: no cover
            import tomli as tomllib

        tomllib.loads(toml_text)
        as_of = _last_author_date(root)
        json_path = tmp_path / "metrics.json"
        md_path = tmp_path / "report.md"
        assert main(
            [
                "measure",
                "--as-of",
                as_of,
                "--json",
                str(json_path),
                "--md",
                str(md_path),
                "--quiet",
                "-C",
                str(root),
            ]
        ) == 0
        document = json.loads(json_path.read_text(encoding="utf-8"))
        assert document["metrics"]["fixes"]["total"]["landings"] >= 1
        assert md_path.read_text(encoding="utf-8")
        assert len(md_path.read_text(encoding="utf-8").splitlines()) <= 80
    finally:
        assert _status(root) == before
