from hakari.contract.defaults import DEFAULTS
from hakari.domain.classify import (
    classify_file,
    component_of,
    effective_subject,
    landing_type,
)


def test_landing_type_all_paths():
    fix = DEFAULTS["fix"]
    assert landing_type("feat(api)!: x", "", fix) == "feat"
    assert landing_type(
        "Merge pull request #12 from org/fix/x", "fix(a): y", fix
    ) == "fix"
    assert landing_type("Merge pull request #12 from org/hotfix/w", "", fix) == "hotfix"
    assert landing_type('Revert "feat: x"', "", fix) == "revert"
    assert landing_type("いろいろ直した(bug)", "", fix) == "fix"
    assert landing_type("雑多な更新", "", fix) == "unknown"
    assert landing_type("style: x", "", fix) == "other"
    assert effective_subject("Merge pull request #1 from org/fix/x", "\n  fix: body\n") == (
        "fix: body",
        "fix/x",
    )


def test_file_classification_priority():
    paths = DEFAULTS["paths"]
    assert classify_file("tests/x.md", paths) == "tests"
    assert classify_file("a/node_modules/x.js", paths) == "exclude"
    assert classify_file("docs/readme.md", paths) == "docs"
    assert classify_file("a/app.PY", paths) == "production"
    assert classify_file("Makefile", paths) == "other"


def test_component_resolution_is_first_match_and_has_auto_root():
    components = {"backend": ["backend/**"], "all_go": ["**/*.go"]}
    assert component_of("backend/api.go", components) == "backend"
    assert component_of("other/api.go", components) == "all_go"
    assert component_of("README", {}) == "(root)"
    assert component_of("web/app.ts", {}) == "web"
