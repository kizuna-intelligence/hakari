from collections.abc import Mapping


def _decimal(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".") or "0"
    return str(value)


def _integer(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return _decimal(value)


def _ratio(value: object) -> str:
    if value is None:
        return "—"
    return f"{float(value):.3f}"


def _percent(value: object) -> str:
    if value is None:
        return "—"
    return _decimal(float(value) * 100)


def _signed_delta(total: object, previous: object) -> str:
    if total is None or previous is None:
        return "—"
    delta = float(total) - float(previous)
    return f"{delta:+.3f}"


def _stat_row(
    label: str, stats: Mapping[str, object], previous: object = None, cross: object = None
) -> str:
    previous_value = previous if isinstance(previous, Mapping) else None
    prior_share = previous_value.get("fix_share") if previous_value is not None else None
    return (
        f"| {label} | {_integer(stats.get('landings'))} | "
        f"{_ratio(stats.get('fix_share'))} | "
        f"{_signed_delta(stats.get('fix_share'), prior_share)} | "
        f"{_ratio(stats.get('fix_to_feat'))} | "
        f"{_integer(stats.get('hotfix_count'))} | "
        f"{_ratio(cross)} |"
    )


def _component_items(
    components: Mapping[str, Mapping[str, object]],
) -> list[tuple[str, Mapping[str, object]]]:
    def sort_key(item: tuple[str, Mapping[str, object]]) -> tuple[int, str]:
        stats = item[1].get("touching", {})
        landings = stats.get("landings") if isinstance(stats, Mapping) else None
        return (-(landings if isinstance(landings, int) else 0), item[0])

    return sorted(components.items(), key=sort_key)


def _append(lines: list[str], *values: str) -> None:
    lines.extend(values)


def render_report(document: dict) -> str:
    repo = document["repo"]
    metrics = document["metrics"]
    fixes = metrics["fixes"]
    hotspots = metrics["hotspots"]
    fix_window = fixes["window"]
    hotspot_window = hotspots["window"]
    total = fixes["total"]
    previous = fixes.get("previous", {})
    lines = [
        "# hakari — 修正率とホットスポット",
        "",
        f"- リポジトリ: `{repo['branch']}` @ `{str(repo['head'])[:8]}`",
        f"- 基準日: `{repo['as_of']}`(タイムゾーン `{repo['timezone']}`)",
        f"- 窓: 修正率 `{fix_window['start']}` 〜 `{fix_window['end']}`({fix_window['days']} 日) / "
        f"ホットスポット `{hotspot_window['start']}` 〜 `{hotspot_window['end']}`({hotspot_window['days']} 日)",
        "",
        "## 表 1 修正率",
        "",
        "| 対象 | 着地 | fix 率 | 前期比 | fix/feat | hotfix | 横断率 |",
        "|---|--:|--:|--:|--:|--:|--:|",
        _stat_row("**全体**", total, previous, cross=fixes["cross"].get("share")),
    ]

    components = fixes.get("components", {})
    component_items = _component_items(components) if isinstance(components, Mapping) else []
    shown_components = component_items[:8]
    for name, detail in shown_components:
        touching = detail.get("touching", {})
        exclusive = detail.get("exclusive", {})
        cross_share = detail.get("cross_share")
        _append(
            lines,
            _stat_row(f"{name}(触)", touching, cross=cross_share),
            _stat_row(f"{name}(専)", exclusive),
        )
    if len(component_items) > 8:
        _append(lines, "", f"他 {len(component_items) - 8} コンポーネントは metrics.json を参照")

    cross = fixes["cross"]
    _append(lines, "", "## 表 2 横断(コンポーネント対)", "")
    pairs = cross.get("pairs", [])
    if pairs:
        _append(
            lines,
            f"窓内の横断着地 {_integer(cross.get('landings'))} 件(全体の {_percent(cross.get('share'))}%)。"
            f"版数ファイルの除外で横断でなくなった着地 {_integer(cross.get('version_only_excluded'))} 件は除外している。",
            "",
            "| a | b | 着地 |",
            "|---|---|--:|",
        )
        ordered_pairs = sorted(
            pairs,
            key=lambda pair: (-int(pair.get("landings", 0)), pair.get("a", ""), pair.get("b", "")),
        )
        for pair in ordered_pairs[:5]:
            _append(
                lines,
                f"| {pair.get('a', '—')} | {pair.get('b', '—')} | {_integer(pair.get('landings'))} |",
            )
    else:
        _append(lines, "横断着地はなかった。")

    _append(lines, "", "## 表 3 ホットスポット", "")
    files = hotspots.get("files", [])
    hotspot_total = hotspots["total"]
    thresholds = hotspots["thresholds"]
    min_lines = thresholds["min_lines"]
    min_rework = thresholds["min_rework"]
    if files:
        _append(
            lines,
            f"窓内で `行数 > {min_lines}` かつ `書換量 >= {min_rework}` の本番ファイルは "
            f"{_integer(hotspot_total.get('count'))} 件({min_lines} 行超は "
            f"{_integer(hotspot_total.get('files_over_min_lines'))} 件、最大 {_integer(hotspot_total.get('max_file_lines'))} 行)。",
            "",
            "| ファイル | コンポーネント | 行数 | 書換量 | 着地 |",
            "|---|---|--:|--:|--:|",
        )
        for item in files[:10]:
            _append(
                lines,
                f"| `{item.get('path', '—')}` | {item.get('component', '—')} | "
                f"{_integer(item.get('lines'))} | {_integer(item.get('rework'))} | "
                f"{_integer(item.get('commits'))} |",
            )
        component_counts = hotspots.get("components", {})
        shown_counts = []
        if isinstance(component_counts, Mapping):
            for name, values in component_counts.items():
                count = values.get("count") if isinstance(values, Mapping) else None
                if isinstance(count, int) and count > 0:
                    shown_counts.append((name, count))
        shown_counts.sort(key=lambda item: (-item[1], item[0]))
        if shown_counts:
            _append(
                lines,
                "",
                "コンポーネント別: "
                + " / ".join(f"{name} {_integer(count)}" for name, count in shown_counts),
            )
    else:
        _append(lines, "ホットスポットはなかった。")

    below = hotspot_total.get("below_min_rework")
    if isinstance(below, int) and below > 0:
        _append(
            lines,
            "",
            f"{min_lines} 行超のうち {below} 件は窓内の書き換え量が {min_rework} に満たず、対象外としている"
            "(窓内で作成されたきりのファイルと、窓の前からあって窓内ではあまり触られていないファイルの両方を含む)。",
        )

    _append(lines, "", "## 注意", "")
    for note in document.get("notes", []):
        _append(lines, f"- {note}")
    return "\n".join(lines) + "\n"
