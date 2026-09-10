import re
import subprocess


class GitError(Exception):
    pass


class NotAGitRepo(GitError):
    pass


def _command(repo_root: str, args: list[str]) -> list[str]:
    return ["git", "-c", "core.quotepath=off", "--no-pager", "-C", repo_root, *args]


def _run(repo_root: str, args: list[str], binary: bool) -> str | bytes:
    try:
        completed = subprocess.run(
            _command(repo_root, args), capture_output=True, check=False
        )
    except FileNotFoundError as exc:
        raise GitError("git not found") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")
        raise GitError(stderr[:500])
    if binary:
        return completed.stdout
    return completed.stdout.decode("utf-8", errors="replace")


def run_git(repo_root: str, args: list[str]) -> str:
    return _run(repo_root, args, False)  # type: ignore[return-value]


def run_git_bytes(repo_root: str, args: list[str]) -> bytes:
    return _run(repo_root, args, True)  # type: ignore[return-value]


def parse_git_version(text: str) -> tuple[int, int, int]:
    numbers = re.findall(r"\d+", text)
    if len(numbers) < 3:
        return (0, 0, 0)
    major, minor, patch = (int(value) for value in numbers[:3])
    return major, minor, patch


def git_version(repo_root: str) -> tuple[int, int, int]:
    return parse_git_version(run_git(repo_root, ["--version"]))


def find_repo_root(start_dir: str) -> str:
    try:
        output = run_git(start_dir, ["rev-parse", "--show-toplevel"])
    except GitError as exc:
        raise NotAGitRepo(str(exc)) from exc
    return output.strip()
