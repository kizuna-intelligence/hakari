import os
from collections.abc import Sequence

from hakari.contract.history import InMemoryTree
from hakari.platform.gitcli import run_git, run_git_bytes


def list_tracked_paths(repo_root: str) -> tuple[str, ...]:
    raw_paths = run_git_bytes(repo_root, ["ls-files", "-z"])
    return tuple(
        raw_path.decode("utf-8", errors="replace")
        for raw_path in raw_paths.split(b"\x00")
        if raw_path
    )


def list_existing_dirs(repo_root: str, candidates: Sequence[str]) -> frozenset[str]:
    wanted = set(candidates)
    found = {
        candidate
        for candidate in wanted
        if os.path.isdir(os.path.join(repo_root, candidate))
    }
    if not wanted:
        return frozenset()
    for _, dirnames, _ in os.walk(repo_root):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        found.update(name for name in dirnames if name in wanted)
        if found == wanted:
            break
    return frozenset(found)


def read_tree(repo_root: str) -> InMemoryTree:
    raw_paths = run_git_bytes(repo_root, ["ls-files", "-z"])
    files: dict[str, int] = {}
    for raw_path in raw_paths.split(b"\x00"):
        if not raw_path:
            continue
        path = raw_path.decode("utf-8", errors="replace")
        try:
            with open(os.path.join(repo_root, path), "rb") as handle:
                data = handle.read()
        except OSError:
            continue
        if b"\x00" in data[:8000]:
            continue
        files[path] = data.count(b"\n")
    return InMemoryTree(files)


def head_sha(repo_root: str, branch: str) -> str:
    return run_git(repo_root, ["rev-parse", branch]).strip()
