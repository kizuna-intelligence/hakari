from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from hakari.contract.history import InMemoryHistory
from hakari.contract.model import FileChange, Landing
from hakari.platform.dates import parse_iso
from hakari.platform.gitcli import GitError, run_git


def resolve_branch(repo_root: str, configured: str) -> str:
    if configured != "auto":
        run_git(repo_root, ["rev-parse", "--verify", "--quiet", configured])
        return configured
    try:
        output = run_git(
            repo_root, ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"]
        ).strip()
        prefix = "refs/remotes/"
        return output[len(prefix) :] if output.startswith(prefix) else output
    except GitError:
        pass

    for branch in ("main", "master"):
        try:
            run_git(repo_root, ["rev-parse", "--verify", "--quiet", branch])
            return branch
        except GitError:
            pass
    return run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()


def _numstat(blob: str) -> tuple[FileChange, ...]:
    changes: list[FileChange] = []
    for line in blob.splitlines():
        fields = line.split("\t", 2)
        if len(fields) != 3:
            continue
        added_text, deleted_text, path = fields
        try:
            added = None if added_text == "-" else int(added_text)
            deleted = None if deleted_text == "-" else int(deleted_text)
        except ValueError:
            continue
        changes.append(FileChange(path=path, added=added, deleted=deleted))
    return tuple(changes)


def read_history(
    repo_root: str, branch: str, since: date, tz_name: str
) -> InMemoryHistory:
    since_dt = datetime.combine(since, time.min, tzinfo=ZoneInfo(tz_name))
    args = [
        "log",
        branch,
        "--first-parent",
        "--diff-merges=first-parent",
        "--no-renames",
        "--numstat",
        "--date=iso-strict",
        "--format=%x00%H%x00%aI%x00%s%x00%b%x00",
        f"--since={since_dt.isoformat()}",
    ]

    try:
        output = run_git(repo_root, args)
    except GitError as exc:
        if "does not have any commits" in str(exc):
            return InMemoryHistory(())
        raise
    if not output:
        return InMemoryHistory(())

    fields = output.split("\x00")
    if fields and not fields[0]:
        fields = fields[1:]
    landings: list[Landing] = []

    for index in range(0, len(fields) - 4, 5):
        sha, author_text, subject, body, numstat_blob = fields[index : index + 5]
        if not sha:
            continue
        landings.append(
            Landing(
                sha=sha,
                author_at=parse_iso(author_text),
                subject=subject,
                body=body,
                files=_numstat(numstat_blob),
            )
        )

    return InMemoryHistory(tuple(landings))


def read_creations(
    repo_root: str, branch: str, since: date, tz_name: str
) -> frozenset[tuple[str, str]]:
    """窓内の first-parent 着地で新規作成されたファイルを (sha, path) で返す。"""
    since_dt = datetime.combine(since, time.min, tzinfo=ZoneInfo(tz_name))
    args = [
        "log",
        branch,
        "--first-parent",
        "--diff-merges=first-parent",
        "--no-renames",
        "--diff-filter=A",
        "--name-only",
        "--format=%x00%H",
        f"--since={since_dt.isoformat()}",
    ]

    try:
        output = run_git(repo_root, args)
    except GitError as exc:
        if "does not have any commits" in str(exc):
            return frozenset()
        raise
    if not output:
        return frozenset()

    fields = output.split("\x00")
    if fields and not fields[0]:
        fields = fields[1:]

    creations: set[tuple[str, str]] = set()
    for block in fields:
        if not block:
            continue
        lines = block.splitlines()
        if not lines:
            continue
        sha = lines[0]
        for path in lines[1:]:
            if not path:
                continue
            creations.add((sha, path))
    return frozenset(creations)
