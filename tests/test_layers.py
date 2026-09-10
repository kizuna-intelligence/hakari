import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _layer(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else ""


def _target_modules(node: ast.AST):
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [node.module]
    return []


def test_import_directions_are_clean():
    allowed = {
        "platform": {"stdlib"},
        "contract": {"stdlib", "contract"},
        "domain": {"stdlib", "contract", "platform", "domain"},
        "external": {"stdlib", "contract", "platform", "external"},
        "transport": {"stdlib", "contract", "domain", "platform", "transport"},
        "application": {
            "stdlib",
            "contract",
            "domain",
            "platform",
            "external",
            "transport",
            "application",
        },
    }
    violations = []
    for path in sorted((ROOT / "hakari").rglob("*.py")):
        relative_parts = path.relative_to(ROOT).with_suffix("").parts
        source_layer = _layer(".".join(relative_parts))
        if source_layer not in allowed or path.name in {"__init__.py", "__main__.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for target in _target_modules(node):
                if not target.startswith("hakari"):
                    target_layer = "stdlib"
                else:
                    target_layer = _layer(target)
                if target_layer not in allowed[source_layer]:
                    violations.append(f"{path}: {target}")
    assert violations == []


def test_transport_does_not_import_application():
    violations = []
    for path in sorted((ROOT / "hakari" / "transport").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for target in _target_modules(node):
                if target == "hakari.app" or target.startswith("hakari.app."):
                    violations.append(f"{path}: {target}")
    assert violations == []


def test_hakari_does_not_call_importlib_import_module():
    violations = []
    for path in sorted((ROOT / "hakari").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if (
                isinstance(function, ast.Attribute)
                and function.attr == "import_module"
                and isinstance(function.value, ast.Name)
                and function.value.id == "importlib"
            ):
                violations.append(f"{path}:{node.lineno}")
    assert violations == []
