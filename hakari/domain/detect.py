from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from hakari.domain.classify import classify_file
from hakari.platform.globs import match_any

TEST_PATTERN_CATALOG = (
    "**/tests/**",
    "**/test/**",
    "**/__tests__/**",
    "**/*_test.go",
    "**/test_*.py",
    "**/*_test.py",
    "**/*.test.ts",
    "**/*.test.tsx",
    "**/*.spec.ts",
    "**/*.spec.tsx",
    "**/*.test.js",
    "**/*Tests.swift",
    "**/*Test.swift",
    "**/*_test.rs",
    "**/*Test.java",
    "**/*Tests.cs",
)

EXCLUDE_EXTRA_CATALOG = (
    ("**/Pods/**", "Pods"),
    ("**/.venv/**", ".venv"),
    ("**/venv/**", "venv"),
    ("**/__pycache__/**", "__pycache__"),
    ("**/DerivedData/**", "DerivedData"),
    ("**/.gradle/**", ".gradle"),
    ("**/.terraform/**", ".terraform"),
    ("**/*.generated.*", None),
    ("**/*.g.dart", None),
)

EXCLUDE_DIR_NAMES = tuple(
    name for _, name in EXCLUDE_EXTRA_CATALOG if name is not None
)


@dataclass(frozen=True)
class Detection:
    production_extensions: tuple[str, ...] | None
    tests: tuple[str, ...] | None
    components: dict[str, list[str]] | None
    exclude_extra: tuple[str, ...] | None


def _without_default_excludes(paths: Sequence[str], defaults: dict) -> list[str]:
    patterns = defaults["paths"]["exclude"]
    return [path for path in paths if not match_any(path, patterns)]


def _extension(path: str) -> str:
    filename = path.rsplit("/", 1)[-1]
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _production_extensions(paths: Sequence[str], defaults: dict) -> tuple[str, ...] | None:
    configured = tuple(defaults["paths"]["production_extensions"])
    counts = Counter(_extension(path) for path in paths)
    selected = tuple(extension for extension in configured if counts[extension] >= 3)
    if not selected or selected == configured:
        return None
    return selected


def _tests(paths: Sequence[str], defaults: dict) -> tuple[str, ...] | None:
    selected = tuple(
        pattern
        for pattern in TEST_PATTERN_CATALOG
        if any(match_any(path, (pattern,)) for path in paths)
    )
    if not selected or set(selected) == set(defaults["paths"]["tests"]):
        return None
    return selected


def _components(paths: Sequence[str], defaults: dict) -> dict[str, list[str]] | None:
    counts: Counter[str] = Counter()
    paths_cfg = defaults["paths"]
    for path in paths:
        if "/" not in path or classify_file(path, paths_cfg) != "production":
            continue
        name = path.split("/", 1)[0]
        if not name.startswith("."):
            counts[name] += 1
    names = sorted(name for name, count in counts.items() if count > 0)
    if len(names) < 2:
        return None
    return {name: [f"{name}/**"] for name in names}


def _exclude_extra(paths: Sequence[str], existing_dirs: Iterable[str]) -> tuple[str, ...] | None:
    directories = set(existing_dirs)
    selected = tuple(
        pattern
        for pattern, directory in EXCLUDE_EXTRA_CATALOG
        if (directory is not None and directory in directories)
        or any(match_any(path, (pattern,)) for path in paths)
    )
    return selected or None


def detect(
    paths: Sequence[str], existing_dirs: Iterable[str], defaults: dict
) -> Detection:
    filtered = _without_default_excludes(paths, defaults)
    return Detection(
        production_extensions=_production_extensions(filtered, defaults),
        tests=_tests(filtered, defaults),
        components=_components(filtered, defaults),
        exclude_extra=_exclude_extra(filtered, existing_dirs),
    )
