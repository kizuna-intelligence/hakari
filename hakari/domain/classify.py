import re
from collections.abc import Iterable

from hakari.platform.globs import first_match, match_any


FileKind = str


CANONICAL_TYPES = (
    "fix",
    "hotfix",
    "feat",
    "refactor",
    "test",
    "chore",
    "docs",
    "revert",
    "other",
    "unknown",
)


_MERGE_SUBJECT = re.compile(r"^Merge pull request #\d+ from (?P<ref>\S+)")
_CONVENTIONAL_SUBJECT = re.compile(r"\A(?P<type>[A-Za-z]+)(\([^)]*\))?!?:")


def classify_file(path: str, paths_cfg: dict) -> FileKind:
    if match_any(path, paths_cfg["exclude"]):
        return "exclude"
    if match_any(path, paths_cfg["tests"]):
        return "tests"
    if match_any(path, paths_cfg["docs"]):
        return "docs"
    filename = path.rsplit("/", 1)[-1]
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension in paths_cfg["production_extensions"]:
        return "production"
    return "other"


def component_of(path: str, components: dict[str, list[str]]) -> str:
    if components:
        return first_match(path, tuple(components.items())) or "(other)"
    return path.split("/", 1)[0] if "/" in path else "(root)"


def component_names(components: dict[str, list[str]], names: Iterable[str]) -> list[str]:
    seen = set(names)
    if not components:
        return sorted(seen)
    result = list(components)
    if "(other)" in seen and "(other)" not in result:
        result.append("(other)")
    return result


def effective_subject(subject: str, body: str) -> tuple[str, str | None]:
    match = _MERGE_SUBJECT.match(subject)
    if match is None:
        return subject, None
    ref = match.group("ref")
    branch = ref.split("/", 1)[1] if "/" in ref else ref
    effective = next((line.strip() for line in body.splitlines() if line.strip()), subject)
    return effective, branch


def landing_type(subject: str, body: str, fix_cfg: dict) -> str:
    effective, branch = effective_subject(subject, body)
    if effective.startswith('Revert "'):
        return "revert"
    conventional = _CONVENTIONAL_SUBJECT.match(effective)
    if conventional is not None:
        candidate = conventional.group("type").lower()
        return candidate if candidate in CANONICAL_TYPES else "other"
    if branch is not None:
        branch_type = branch.split("/", 1)[0].lower()
        if branch_type in CANONICAL_TYPES:
            return branch_type
    if re.search(fix_cfg["subject_pattern"], effective, re.IGNORECASE):
        return "fix"
    return "unknown"


def has_hotfix_in_subject(subject: str, body: str) -> bool:
    effective, _ = effective_subject(subject, body)
    return "hotfix" in effective.lower()


def is_revert_subject(subject: str, body: str) -> bool:
    effective, _ = effective_subject(subject, body)
    return effective.startswith('Revert "')
