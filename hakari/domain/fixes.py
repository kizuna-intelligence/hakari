from dataclasses import dataclass
from datetime import date
from itertools import combinations

from hakari.contract.model import Landing, MetricResult, Window
from hakari.domain.classify import (
    CANONICAL_TYPES,
    classify_file,
    component_names,
    component_of,
    has_hotfix_in_subject,
    is_revert_subject,
    landing_type,
)
from hakari.domain.windows import window_details
from hakari.platform.dates import to_local_date
from hakari.platform.globs import match_any


@dataclass(frozen=True)
class PreparedLanding:
    landing: Landing
    day: date
    type: str
    prod_paths: tuple[str, ...]
    components: frozenset[str]
    cross_components: frozenset[str]
    demoted_from_cross: bool
    has_hotfix_subject: bool
    is_revert_subject: bool


def prepare(landings, config) -> list[PreparedLanding]:
    paths_cfg = config["paths"]
    components_cfg = config["components"]
    fix_cfg = config["fix"]
    prepared: list[PreparedLanding] = []
    for landing in landings:
        prod_paths = tuple(
            change.path
            for change in landing.files
            if classify_file(change.path, paths_cfg) == "production"
        )
        if not prod_paths:
            continue
        version_paths = frozenset(
            change.path
            for change in landing.files
            if classify_file(change.path, paths_cfg) != "exclude"
            and match_any(change.path, paths_cfg["version_files"])
        )
        components = frozenset(component_of(path, components_cfg) for path in prod_paths)
        raw_cross_paths = set(prod_paths) | version_paths
        raw_cross_components = frozenset(
            component_of(path, components_cfg) for path in raw_cross_paths
        )
        cross_components = frozenset(
            component_of(path, components_cfg)
            for path in prod_paths if not match_any(path, paths_cfg["version_files"])
        )
        prepared.append(
            PreparedLanding(
                landing=landing,
                day=to_local_date(landing.author_at, config["timezone"]),
                type=landing_type(landing.subject, landing.body, fix_cfg),
                prod_paths=prod_paths,
                components=components,
                cross_components=cross_components,
                demoted_from_cross=(
                    bool(version_paths)
                    and len(raw_cross_components) >= 2
                    and len(cross_components) < 2
                ),
                has_hotfix_subject=has_hotfix_in_subject(landing.subject, landing.body),
                is_revert_subject=is_revert_subject(landing.subject, landing.body),
            )
        )
    return prepared


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


def _stats(landings: list[PreparedLanding], fix_cfg: dict) -> dict:
    by_type = dict.fromkeys(CANONICAL_TYPES, 0)
    for landing in landings:
        by_type[landing.type] += 1
    total = len(landings)
    fix_count = sum(by_type.get(kind, 0) for kind in set(fix_cfg["fix_types"]))
    feat_count = sum(by_type.get(kind, 0) for kind in set(fix_cfg["feat_types"]))
    return {
        "landings": total,
        "fix_share": _ratio(fix_count, total),
        "fix_to_feat": _ratio(fix_count, feat_count),
        "hotfix_count": sum(item.type == "hotfix" or item.has_hotfix_subject for item in landings),
        "hotfix_typed": by_type["hotfix"],
        "revert_count": sum(item.type == "revert" or item.is_revert_subject for item in landings),
        "unknown_share": _ratio(by_type["unknown"], total),
        "by_type": by_type,
    }


def _component_stats(name: str, landings: list[PreparedLanding], fix_cfg: dict) -> dict:
    touching = []
    exclusive = []
    cross_count = 0
    for landing in landings:
        if name not in landing.components:
            continue
        touching.append(landing)
        if landing.components == {name}:
            exclusive.append(landing)
        cross_count += len(landing.cross_components) >= 2
    return {
        "touching": _stats(touching, fix_cfg),
        "exclusive": _stats(exclusive, fix_cfg),
        "cross_share": _ratio(cross_count, len(touching)),
    }


def _cross_details(landings: list[PreparedLanding], total: int) -> dict:
    cross_landings = [item for item in landings if len(item.cross_components) >= 2]

    pair_counts: dict[tuple[str, str], int] = {}
    for landing in cross_landings:
        for pair in combinations(sorted(landing.cross_components), 2):
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
    pairs = [{"a": pair[0], "b": pair[1], "landings": count}
             for pair, count in sorted(pair_counts.items(), key=lambda item: (-item[1], item[0]))]
    return {
        "landings": len(cross_landings),
        "share": _ratio(len(cross_landings), total),
        "version_only_excluded": sum(item.demoted_from_cross for item in landings),
        "pairs": pairs,
    }


def compute_fixes(
    prepared: list[PreparedLanding],
    recent: Window,
    previous: Window,
    config: dict,
) -> MetricResult:
    recent_landings = [item for item in prepared if recent.contains(item.day)]
    previous_landings = [item for item in prepared if previous.contains(item.day)]
    fix_cfg = config["fix"]
    names = component_names(
        config["components"],
        (component for landing in recent_landings for component in landing.components),
    )
    total = _stats(recent_landings, fix_cfg)
    details = {
        "window": window_details(recent),
        "total": total,
        "previous": {"window": window_details(previous), **_stats(previous_landings, fix_cfg)},
        "components": {name: _component_stats(name, recent_landings, fix_cfg) for name in names},
        "cross": _cross_details(recent_landings, len(recent_landings)),
    }
    return MetricResult("fixes", total["fix_share"], "ratio", details)
