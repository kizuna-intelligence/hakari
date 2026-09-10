import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from typing import Callable
from zoneinfo import ZoneInfoNotFoundError

from hakari.contract.model import ConfigError, MeasureRequest
from hakari.platform.gitcli import GitError, NotAGitRepo, find_repo_root
from hakari.transport.render_md import render_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hakari")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init")
    initialize.add_argument("--force", action="store_true")
    initialize.add_argument("-C", "--cd", dest="repo_dir", default=os.getcwd())
    measure = commands.add_parser("measure")
    measure.add_argument("--as-of")
    measure.add_argument("--json", dest="json_path")
    measure.add_argument("--md", dest="md_path")
    measure.add_argument("--quiet", action="store_true")
    measure.add_argument("-C", "--cd", dest="repo_dir", default=os.getcwd())
    return parser


def _as_of(value: str | None) -> date | None:
    if value is None:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("--as-of must be YYYY-MM-DD")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("--as-of must be YYYY-MM-DD") from exc


def _print_summary(document: dict, json_path: str, md_path: str) -> None:
    repo = document["repo"]
    fixes = document["metrics"]["fixes"]
    total = fixes["total"]
    cross = fixes["cross"]
    hotspots = document["metrics"]["hotspots"]
    hotspot_total = hotspots["total"]
    shown = lambda value: "-" if value is None else str(value)
    print("\n".join((
        f"repo   {repo['branch']} @ {repo['head'][:8]}  as_of {repo['as_of']}",
        "fixes  "
        f"landings {total['landings']}  fix_share {shown(total['fix_share'])}  "
        f"fix_to_feat {shown(total['fix_to_feat'])}  hotfix {total['hotfix_count']}  "
        f"revert {total['revert_count']}  unknown_share {shown(total['unknown_share'])}",
        "cross  "
        f"landings {cross['landings']}  share {shown(cross['share'])}  "
        f"version_only_excluded {cross['version_only_excluded']}",
        "hotspots "
        f"count {hotspot_total['count']}  files_over_min_lines {hotspot_total['files_over_min_lines']}  "
        f"max_file_lines {hotspot_total['max_file_lines']}",
        f"wrote  {json_path}",
        f"wrote  {md_path}",
    )))


def _dump(document: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _dump_report(document: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_report(document))


def _print_init_summary(result) -> None:
    if not result.written:
        print(f"exists {result.path} (--force で上書き)")
        return
    detection = result.detection
    count = lambda value: 0 if value is None else len(value)
    components = 0 if detection.components is None else len(detection.components)
    print(
        "\n".join(
            (
                f"wrote  {result.path}",
                "       "
                f"production_extensions {count(detection.production_extensions)} / "
                f"tests {count(detection.tests)} / "
                f"components {components} / "
                f"exclude +{count(detection.exclude_extra)}",
            )
        )
    )


def run(
    argv: list[str] | None,
    measure: Callable[[MeasureRequest], dict],
    initialize: Callable[[str, bool], object] | None = None,
) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    if args.command == "init":
        if initialize is None:
            return 2
        try:
            result = initialize(args.repo_dir, args.force)
        except (NotAGitRepo, GitError):
            return 3
        _print_init_summary(result)
        return 0
    if args.command != "measure":
        return 2
    try:
        as_of = _as_of(args.as_of)
    except ValueError as exc:
        parser.print_usage(sys.stderr)
        print(f"hakari: error: {exc}", file=sys.stderr)
        return 2
    try:
        request = MeasureRequest(args.repo_dir, as_of)
        document = measure(request)
        root = find_repo_root(args.repo_dir)
        output_path = args.json_path or os.path.join(
            root, getattr(measure, "_hakari_output_dir", "docs/quality-metrics"), "metrics.json"
        )
        report_path = args.md_path or os.path.join(
            root, getattr(measure, "_hakari_output_dir", "docs/quality-metrics"), "report.md"
        )
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _dump(document, output_path)
        report_parent = os.path.dirname(report_path)
        if report_parent:
            os.makedirs(report_parent, exist_ok=True)
        _dump_report(document, report_path)
    except (NotAGitRepo, GitError):
        return 3
    except (ConfigError, ZoneInfoNotFoundError):
        return 2
    if not args.quiet:
        _print_summary(document, output_path, report_path)
    return 0


__all__ = ["build_parser", "run"]
