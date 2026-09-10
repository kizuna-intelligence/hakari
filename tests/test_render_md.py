from hakari.transport.render_md import render_report


def _document(hotspots=None, pairs=None):
    return {
        "repo": {
            "branch": "main",
            "head": "1234567890abcdef",
            "as_of": "2026-08-23",
            "timezone": "Asia/Tokyo",
        },
        "metrics": {
            "fixes": {
                "window": {"start": "2026-07-25", "end": "2026-08-23", "days": 30},
                "total": {
                    "landings": 648,
                    "fix_share": 0.554,
                    "fix_to_feat": 10.4,
                    "hotfix_count": 117,
                    "revert_count": 1,
                    "unknown_share": None,
                },
                "previous": {"fix_share": 0.533},
                "components": {
                    "backend": {
                        "touching": {
                            "landings": 210,
                            "fix_share": 0.61,
                            "fix_to_feat": 8.0,
                            "hotfix_count": 40,
                        },
                        "exclusive": {
                            "landings": 150,
                            "fix_share": 0.58,
                            "fix_to_feat": 7.1,
                            "hotfix_count": 31,
                        },
                        "cross_share": 0.29,
                    }
                },
                "cross": {
                    "landings": 0,
                    "share": 0,
                    "version_only_excluded": 0,
                    "pairs": pairs or [],
                },
            },
            "hotspots": {
                "window": {"start": "2026-05-26", "end": "2026-08-23", "days": 90},
                "total": {
                    "count": 0,
                    "files_over_min_lines": 0,
                    "max_file_lines": 0,
                    "below_min_rework": 0,
                },
                "components": {},
                "thresholds": {
                    "min_lines": 800,
                    "min_rework": 1000,
                },
                "files": hotspots or [],
            },
        },
        "notes": ["note one", "note two"],
    }


def test_report_is_one_page_and_renders_delta_and_none():
    report = render_report(_document())
    assert len(report.splitlines()) <= 60
    assert "**全体**" in report
    assert "| **全体** | 648 | 0.554 | +0.021 | 10.400 | 117 | 0.000 |" in report
    assert "+0.021" in report
    assert "—" in report
    assert "横断着地はなかった。" in report
    assert "ホットスポットはなかった。" in report
    assert "- note one" in report
    assert "- note two" in report


def test_report_renders_top_rows_and_three_digit_separators():
    report = render_report(
        _document(
            hotspots=[
                {
                    "path": "backend/big.py",
                    "component": "backend",
                    "lines": 12253,
                    "commits": 285,
                    "churn": 1890,
                    "created_lines": 700,
                    "rework": 1190,
                }
            ],
            pairs=[{"a": "backend", "b": "cli", "landings": 52}],
        )
    )
    assert "| backend | cli | 52 |" in report
    assert "12,253" in report
    assert "1,190" in report
    # churn は判定に使わないので表には出さない(metrics.json には残る)
    assert "1,890" not in report
    assert "| `backend/big.py` | backend | 12,253 | 1,190 | 285 |" in report


def test_report_formats_rates_and_ratios_with_three_decimal_places():
    document = _document()
    document["metrics"]["fixes"]["total"].update(
        {"fix_share": 1, "fix_to_feat": 12}
    )
    document["metrics"]["fixes"]["cross"]["share"] = 0.84
    document["metrics"]["fixes"]["components"]["backend"]["touching"].update(
        {"fix_share": 1, "fix_to_feat": 12}
    )
    document["metrics"]["fixes"]["components"]["backend"]["cross_share"] = 0.84

    report = render_report(document)

    assert "| **全体** | 648 | 1.000 | +0.467 | 12.000 | 117 | 0.840 |" in report
    assert "| backend(触) | 210 | 1.000 | — | 12.000 | 40 | 0.840 |" in report
