import copy

import pytest

from hakari.contract.defaults import DEFAULTS
from hakari.contract.model import ConfigError
from hakari.external.config_toml import _validate_and_merge, load_config


def test_hakari_table_is_loaded_and_deep_merged(tmp_path):
    (tmp_path / "hakari.toml").write_text(
        """
[hakari]
timezone = "UTC"

[hakari.hotspot]
min_rework = 1100

[hakari.components]
backend = ["backend/**"]
""",
        encoding="utf-8",
    )
    config = load_config(str(tmp_path))
    assert config["timezone"] == "UTC"
    assert config["hotspot"] == {
        "min_lines": 800,
        "min_rework": 1100.0,
    }
    assert config["components"] == {"backend": ["backend/**"]}
    assert config["paths"] == copy.deepcopy(DEFAULTS["paths"])


def test_hakari_file_requires_root_table(tmp_path):
    (tmp_path / "hakari.toml").write_text('timezone = "UTC"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match=r"\[hakari\]"):
        load_config(str(tmp_path))


def test_unknown_and_wrong_type_config_are_rejected(tmp_path):
    (tmp_path / "hakari.toml").write_text(
        "[hakari]\nunknown = 1\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="unknown config key: unknown"):
        load_config(str(tmp_path))
    (tmp_path / "hakari.toml").write_text(
        "[hakari]\nrecent_days = \"30\"\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="recent_days"):
        load_config(str(tmp_path))


def test_min_rework_is_accepted_as_int_and_rejects_bool(tmp_path):
    (tmp_path / "hakari.toml").write_text(
        "[hakari.hotspot]\nmin_rework = 2\n", encoding="utf-8"
    )
    config = load_config(str(tmp_path))
    assert config["hotspot"]["min_rework"] == 2.0
    (tmp_path / "hakari.toml").write_text(
        "[hakari.hotspot]\nmin_rework = true\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError, match=r"expected int"):
        load_config(str(tmp_path))


def test_validate_and_merge_keeps_int_to_float_but_rejects_bool():
    base = {"x": 1.5}
    override = {"x": 2}
    _validate_and_merge(base, override)
    assert base["x"] == 2.0
    assert isinstance(base["x"], float)
    with pytest.raises(ConfigError, match=r"expected float"):
        _validate_and_merge({"x": 1.5}, {"x": True})


def test_pyproject_tool_hakari_is_fallback(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.hakari]\nrecent_days = 14\n", encoding="utf-8"
    )
    assert load_config(str(tmp_path))["recent_days"] == 14
