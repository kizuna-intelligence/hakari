import copy
from typing import Any

from hakari.contract.defaults import DEFAULTS
from hakari.contract.model import ConfigError

try:
    import tomllib
except ImportError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


def _type_name(value: Any) -> str:
    return {
        dict: "table", list: "array", bool: "bool", int: "int", float: "float", str: "str",
    }.get(type(value), type(value).__name__)


def _validate_and_merge(base: dict, override: dict, path: str = "") -> None:
    for key, value in override.items():
        key_path = f"{path}.{key}" if path else key
        if key not in base:
            raise ConfigError(f"unknown config key: {key_path}")
        expected = base[key]
        if isinstance(expected, dict):
            if not isinstance(value, dict):
                raise ConfigError(f"{key_path}: expected {_type_name(expected)}")
            if not expected:
                if key == "components":
                    for component, patterns in value.items():
                        if (not isinstance(component, str) or not isinstance(patterns, list)
                                or not all(isinstance(item, str) for item in patterns)):
                            raise ConfigError(f"{key_path}.{component}: expected array of str")
                base[key] = copy.deepcopy(value)
            else:
                _validate_and_merge(expected, value, key_path)
        elif isinstance(expected, list):
            if not isinstance(value, list):
                raise ConfigError(f"{key_path}: expected {_type_name(expected)}")
            if expected and any(type(item) is not type(expected[0]) for item in value):
                raise ConfigError(f"{key_path}: expected array of {_type_name(expected[0])}")
            base[key] = copy.deepcopy(value)
        elif isinstance(expected, float) and isinstance(value, int) and not isinstance(value, bool):
            base[key] = float(value)
        elif type(value) is not type(expected):
            raise ConfigError(f"{key_path}: expected {_type_name(expected)}")
        else:
            base[key] = value


def _read_toml(path: str) -> dict:
    try:
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"could not read config: {path}: {exc}") from exc
    return data


def _settings_from_file(path: str, is_hakari_file: bool) -> dict | None:
    data = _read_toml(path)
    if is_hakari_file:
        if set(data) != {"hakari"} or not isinstance(data.get("hakari"), dict):
            raise ConfigError("hakari.toml must contain a [hakari] table")
        return data["hakari"]
    tool = data.get("tool")
    if not isinstance(tool, dict) or "hakari" not in tool:
        return None
    if not isinstance(tool["hakari"], dict):
        raise ConfigError("tool.hakari: expected table")
    return tool["hakari"]


def load_config(repo_root: str) -> dict:
    config_path = f"{repo_root}/hakari.toml"
    if _exists(config_path):
        settings = _settings_from_file(config_path, True)
    else:
        pyproject_path = f"{repo_root}/pyproject.toml"
        settings = _settings_from_file(pyproject_path, False) if _exists(pyproject_path) else None
    config = copy.deepcopy(DEFAULTS)
    if settings is not None:
        _validate_and_merge(config, settings)
    return config


def _exists(path: str) -> bool:
    try:
        with open(path, "rb"):
            return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ConfigError(f"could not access config: {path}: {exc}") from exc
