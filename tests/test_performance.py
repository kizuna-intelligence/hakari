import os
import subprocess
import time
from pathlib import Path

import pytest

from hakari.app import MeasureRequest, measure


@pytest.mark.slow
def test_measure_3000_landings_under_ten_seconds(tmp_path):
    root = Path(tmp_path / "large")
    root.mkdir()
    subprocess.run(
        ["git", "-c", "init.defaultBranch=main", "init"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.name", "Performance"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "performance@example.test"],
        cwd=root,
        check=True,
    )
    source = root / "component" / "app.py"
    source.parent.mkdir()
    source.write_text("line\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["GIT_AUTHOR_DATE"] = "2026-08-01T12:00:00+00:00"
    environment["GIT_COMMITTER_DATE"] = environment["GIT_AUTHOR_DATE"]
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "chore: init"], cwd=root, check=True, env=environment, capture_output=True)
    for index in range(2999):
        with source.open("a", encoding="utf-8") as handle:
            handle.write("line\n")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        environment["GIT_AUTHOR_DATE"] = "2026-08-01T12:00:00+00:00"
        environment["GIT_COMMITTER_DATE"] = environment["GIT_AUTHOR_DATE"]
        subprocess.run(
            ["git", "commit", "-m", f"chore: change {index}"],
            cwd=root,
            check=True,
            env=environment,
            capture_output=True,
        )
    (root / "hakari.toml").write_text(
        "[hakari.hotspot]\nmin_rework = 1000\n", encoding="utf-8"
    )
    started = time.perf_counter()
    document = measure(MeasureRequest(str(root), __import__("datetime").date(2026, 8, 23)))
    elapsed = time.perf_counter() - started
    print(f"3,000 landings measure elapsed: {elapsed:.6f}s")
    assert document["metrics"]["fixes"]["total"]["landings"] == 3000
    assert elapsed <= 10.0
