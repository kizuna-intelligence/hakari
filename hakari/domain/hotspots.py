from typing import Mapping

from hakari.contract.model import MetricResult, Window
from hakari.domain.classify import classify_file, component_names, component_of
from hakari.domain.windows import window_details


def compute_hotspots(
    prepared,
    tree: Mapping[str, int],
    window: Window,
    config: dict,
    creations: frozenset[tuple[str, str]] = frozenset(),
) -> MetricResult:
    paths_cfg = config["paths"]
    components_cfg = config["components"]
    tree_files = tree.files() if hasattr(tree, "files") else tree
    target = {
        path: lines
        for path, lines in tree_files.items()
        if classify_file(path, paths_cfg) == "production"
    }
    stats: dict[str, list[int]] = {path: [0, 0, 0] for path in target}
    for landing in prepared:
        if not window.contains(landing.day):
            continue
        sha = landing.landing.sha
        changes = {change.path: change for change in landing.landing.files}
        for path in landing.prod_paths:
            if path not in target:
                continue
            values = stats[path]
            values[0] += 1
            change = changes.get(path)
            if change is not None:
                values[1] += (change.added or 0) + (change.deleted or 0)
                if (sha, path) in creations:
                    values[2] += change.added or 0
    min_lines = config["hotspot"]["min_lines"]
    min_rework = config["hotspot"]["min_rework"]

    def rework_of(path: str) -> int:
        return stats[path][1] - stats[path][2]

    def item(path: str) -> dict:
        commits, churn, created = stats[path]
        return {
            "path": path,
            "component": component_of(path, components_cfg),
            "lines": target[path],
            "commits": commits,
            "churn": churn,
            "created_lines": created,
            "rework": rework_of(path),
        }

    big = [path for path in target if target[path] > min_lines]
    files = [item(path) for path in big if rework_of(path) >= min_rework]
    near = [
        item(path)
        for path in big
        if min_rework / 2 <= rework_of(path) < min_rework
    ]
    sort_key = lambda value: (-value["rework"], -value["lines"], value["path"])
    files.sort(key=sort_key)
    near.sort(key=sort_key)

    target_lines = list(target.values())
    hotspot_paths = {item["path"] for item in files}
    names = component_names(
        components_cfg, (component_of(path, components_cfg) for path in target)
    )
    components = {}
    for name in names:
        paths = [path for path in target if component_of(path, components_cfg) == name]
        components[name] = {
            "count": sum(path in hotspot_paths for path in paths),
            "files_over_min_lines": sum(target[path] > min_lines for path in paths),
            "max_file_lines": max((target[path] for path in paths), default=0),
        }

    below_min_rework = sum(
        1 for path in target if target[path] > min_lines and rework_of(path) < min_rework
    )
    details = {
        "window": window_details(window),
        "thresholds": {
            "min_lines": min_lines,
            "min_rework": min_rework,
        },
        "total": {
            "count": len(files),
            "files_over_min_lines": sum(lines > min_lines for lines in target_lines),
            "max_file_lines": max(target_lines, default=0),
            "below_min_rework": below_min_rework,
        },
        "components": components,
        "files": files,
        "near": near,
    }
    return MetricResult("hotspots", len(files), "files", details)
