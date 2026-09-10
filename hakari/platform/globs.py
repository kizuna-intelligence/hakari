import re
from functools import lru_cache
from typing import Sequence


@lru_cache(maxsize=None)
def compile_glob(pattern: str) -> re.Pattern:
    pieces: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            pieces.append(r"(?:[^/]+/)*")
            index += 3
            continue
        if pattern.startswith("/**", index) and index + 3 == len(pattern):
            # A trailing glob names children of the directory, not the directory
            # entry itself.  This also keeps docs/** distinct from docs.
            pieces.append(r"(?:/.*)")
            index += 3
            continue
        if pattern.startswith("**", index):
            pieces.append(r".*")
            index += 2
            continue
        char = pattern[index]
        if char == "*":
            pieces.append(r"[^/]*")
        elif char == "?":
            pieces.append(r"[^/]")
        else:
            pieces.append(re.escape(char))
        index += 1
    return re.compile(r"\A" + "".join(pieces) + r"\Z")


def match_any(path: str, patterns: Sequence[str]) -> bool:
    return any(compile_glob(pattern).match(path) is not None for pattern in patterns)


def first_match(
    path: str, named_patterns: Sequence[tuple[str, Sequence[str]]]
) -> str | None:
    for name, patterns in named_patterns:
        if match_any(path, patterns):
            return name
    return None
