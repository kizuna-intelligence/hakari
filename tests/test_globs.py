from hakari.platform.globs import compile_glob, first_match, match_any


def test_required_double_star_patterns():
    assert match_any("node_modules/x.js", ["**/node_modules/**"])
    assert match_any("web/node_modules/a/b.js", ["**/node_modules/**"])
    assert match_any("docs/a.md", ["docs/**"])
    assert match_any("docs/x/y.md", ["docs/**"])
    assert not match_any("docs", ["docs/**"])
    assert not match_any("docsx/a.md", ["docs/**"])
    assert match_any("a_test.go", ["**/*_test.go"])
    assert match_any("backend/internal/a_test.go", ["**/*_test.go"])
    assert match_any("backend/internal/models/models.go", ["backend/**"])
    assert not match_any("web/backend/x.go", ["backend/**"])
    assert match_any("Cargo.lock", ["**/*.lock"])
    assert match_any("a/b/c.lock", ["**/*.lock"])


def test_match_and_first_match():
    assert match_any("a.py", ["*.go", "*.py"])
    assert first_match("backend/api.go", [("first", ["backend/**"]), ("second", ["**/*.go"])]) == "first"
    assert first_match("README", [("docs", ["docs/**"])]) is None
    assert compile_glob("*.py") is compile_glob("*.py")
