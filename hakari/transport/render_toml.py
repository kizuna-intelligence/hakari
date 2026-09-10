import re
from collections.abc import Sequence

from hakari.contract.defaults import DEFAULTS
from hakari.domain.detect import Detection


_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _key(value: str) -> str:
    return value if _BARE_KEY.fullmatch(value) else _quote(value)


def _array(values: Sequence[str]) -> str:
    quoted = [_quote(value) for value in values]
    if len(quoted) <= 3:
        return "[" + ", ".join(quoted) + "]"
    return "[\n" + "\n".join(f"  {value}," for value in quoted) + "\n]"


def render_hakari_toml(detection: Detection) -> str:
    lines = [
        "# hakari init が検出した設定。既定と同じ項目は書いていない。",
        "# 既定値の全文は README の「設定項目」を見ること。",
        "",
        "[hakari]",
    ]
    has_paths = any(
        value is not None
        for value in (
            detection.production_extensions,
            detection.tests,
            detection.exclude_extra,
        )
    )
    if not has_paths and detection.components is None:
        lines.append("# 検出できる設定はありませんでした。")
        return "\n".join(lines) + "\n"

    if has_paths:
        lines.extend(("", "[hakari.paths]"))
        if detection.production_extensions is not None:
            lines.append(
                "production_extensions = "
                + _array(detection.production_extensions)
            )
        if detection.tests is not None:
            lines.append("tests = " + _array(detection.tests))
        if detection.exclude_extra is not None:
            exclude = tuple(DEFAULTS["paths"]["exclude"]) + detection.exclude_extra
            lines.append("exclude = " + _array(exclude))

    if detection.components is not None:
        lines.extend(("", "[hakari.components]"))
        for name, patterns in detection.components.items():
            lines.append(f"{_key(name)} = {_array(patterns)}")

    return "\n".join(lines) + "\n"
