from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_default_exclude_is_defined_only_in_contract_defaults():
    literal = '"**/node_modules/**"'
    definition = Path("hakari/contract/defaults.py")
    violations = [
        str(path.relative_to(ROOT))
        for path in sorted((ROOT / "hakari").rglob("*.py"))
        if path.relative_to(ROOT) != definition
        and literal in path.read_text(encoding="utf-8")
    ]
    assert violations == [], f"default exclude literal found in: {violations}"
