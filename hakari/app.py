import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from hakari.contract.defaults import DEFAULTS
from hakari.domain.classify import classify_file, component_of
from hakari.domain.detect import EXCLUDE_DIR_NAMES, Detection, detect
from hakari.domain.fixes import compute_fixes, prepare
from hakari.domain.hotspots import compute_hotspots
from hakari.domain.windows import hotspot_window, previous_window, recent_window
from hakari.contract.model import MeasureRequest
from hakari.external.config_toml import ConfigError, load_config
from hakari.external.git_history import read_creations, read_history, resolve_branch
from hakari.external.git_tree import (
    head_sha,
    list_existing_dirs,
    list_tracked_paths,
    read_tree,
)
from hakari.platform.gitcli import GitError, find_repo_root, git_version
from hakari.transport.render_json import build
from hakari.transport.render_toml import render_hakari_toml


@dataclass(frozen=True)
class InitRequest:
    repo_dir: str
    force: bool


@dataclass(frozen=True)
class InitResult:
    path: str
    written: bool
    detection: Detection


def _init_detection(root: str) -> Detection:
    paths = list_tracked_paths(root)
    existing_dirs = {
        segment
        for path in paths
        for segment in path.split("/")[:-1]
    }
    existing_dirs.update(list_existing_dirs(root, EXCLUDE_DIR_NAMES))
    return detect(paths, existing_dirs, DEFAULTS)


def init(request: InitRequest) -> InitResult:
    root = find_repo_root(request.repo_dir)
    path = os.path.abspath(os.path.join(root, "hakari.toml"))
    if os.path.exists(path) and not request.force:
        return InitResult(path, False, Detection(None, None, None, None))
    detection = _init_detection(root)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_hakari_toml(detection))
    return InitResult(path, True, detection)


def _output_components(config: dict, prepared, tree: dict) -> dict:
    configured = config["components"]
    seen = {
        component_of(path, configured)
        for path in tree
        if classify_file(path, config["paths"]) == "production"
    }
    seen.update(component for landing in prepared for component in landing.components)
    if configured:
        result = {name: list(patterns) for name, patterns in configured.items()}
        if "(other)" in seen:
            result["(other)"] = []
        return result
    return {name: [] for name in sorted(seen)}


def measure(request: MeasureRequest) -> dict:
    root = find_repo_root(request.repo_dir)
    version = git_version(root)
    if version < (2, 31, 0):
        current = ".".join(str(part) for part in version)
        raise GitError(
            "git 2.31 以降が必要です(--diff-merges=first-parent を使うため)。"
            f"現在: {current}"
        )
    config = load_config(root)
    timezone = config["timezone"]
    measure._hakari_output_dir = config["output"]["dir"]
    as_of = request.as_of or datetime.now(ZoneInfo(timezone)).date()
    recent = recent_window(as_of, config["recent_days"])
    previous = previous_window(recent)
    hotspots_window = hotspot_window(as_of, config["hotspot_days"])
    since = min(previous.start, hotspots_window.start) - timedelta(days=7)
    branch = resolve_branch(root, config["branch"])
    head = head_sha(root, branch)
    history = read_history(root, branch, since, timezone)
    creations = read_creations(root, branch, since, timezone)
    tree = read_tree(root)
    prepared = prepare(history.landings(), config)
    fixes = compute_fixes(prepared, recent, previous, config)
    hotspots = compute_hotspots(
        prepared, tree.files(), hotspots_window, config, creations
    )
    total = fixes.details["total"]
    cross = fixes.details["cross"]
    notes: list[str] = []
    unknown_share = total["unknown_share"]
    if unknown_share is not None and unknown_share > 0.3:
        notes.append(f"unknown_share {unknown_share}: 件名規約のない着地が {round(unknown_share * 100)}% あり、型比は参考値")
    if cross["version_only_excluded"] > 0:
        notes.append(
            f"版数ファイルの除外で横断でなくなった着地 {cross['version_only_excluded']} 件を横断集計から除外"
        )
    notes.append("rename 追跡なし(--no-renames)。リネーム直後のファイルは commits が過小評価になる")
    repo = {
        "branch": branch,
        "head": head,
        "as_of": as_of.isoformat(),
        "timezone": timezone,
    }
    return build(
        repo,
        _output_components(config, prepared, tree.files()),
        fixes,
        hotspots,
        notes,
    )


def main(argv: list[str] | None = None) -> int:
    from hakari.transport import cli
    return cli.run(argv, measure, lambda repo_dir, force: init(InitRequest(repo_dir, force)))


__all__ = [
    "ConfigError",
    "InitRequest",
    "InitResult",
    "MeasureRequest",
    "init",
    "load_config",
    "main",
    "measure",
]
