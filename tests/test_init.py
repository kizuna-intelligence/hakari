import subprocess

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib

from hakari.app import InitRequest, init, measure
from hakari.contract.model import MeasureRequest
from hakari.external.config_toml import load_config
from hakari.transport.render_toml import render_hakari_toml
from tests.repo_builder import build_golden_repo


def _repo_without_config(tmp_path):
    root = tmp_path / "repo"
    build_golden_repo(str(root))
    (root / "hakari.toml").unlink()
    for name in ("extra_a.go", "extra_b.go"):
        (root / "b" / name).write_text("package b\n", encoding="utf-8")
    subprocess.run(["git", "add", "b/extra_a.go", "b/extra_b.go"], cwd=root, check=True)
    return root


def test_init_writes_readable_config_and_preserves_measure_landings(tmp_path):
    root = _repo_without_config(tmp_path)
    before = measure(MeasureRequest(str(root), None))
    result = init(InitRequest(str(root), False))
    text = (root / "hakari.toml").read_text(encoding="utf-8")
    assert result.written is True
    parsed = tomllib.loads(text)
    assert load_config(str(root))["paths"]
    assert parsed["hakari"]
    after = measure(MeasureRequest(str(root), None))
    assert after["metrics"]["fixes"]["total"]["landings"] == before["metrics"]["fixes"]["total"]["landings"]
    assert text.endswith("\n")


def test_init_without_force_does_not_touch_existing_file(tmp_path):
    root = _repo_without_config(tmp_path)
    path = root / "hakari.toml"
    original = "this is intentionally not parsed\n"
    path.write_text(original, encoding="utf-8")
    result = init(InitRequest(str(root), False))
    assert result.written is False
    assert result.path == str(path.resolve())
    assert path.read_text(encoding="utf-8") == original


def test_init_force_overwrites_existing_file(tmp_path):
    root = _repo_without_config(tmp_path)
    init(InitRequest(str(root), False))
    path = root / "hakari.toml"
    path.write_text("[hakari]\n", encoding="utf-8")
    result = init(InitRequest(str(root), True))
    assert result.written is True
    assert path.read_text(encoding="utf-8") == render_hakari_toml(result.detection)
