import json


def build(repo, components, fixes, hotspots, notes) -> dict:
    return {
        "schema_version": 2,
        "tool": {"name": "hakari", "version": "0.0.1"},
        "repo": repo,
        "components": components,
        "metrics": {
            "fixes": fixes.details,
            "hotspots": hotspots.details,
        },
        "notes": notes,
    }


def dump(document: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
