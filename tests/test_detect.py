from hakari.domain.detect import detect
from hakari.contract.defaults import DEFAULTS


def _detect(paths, existing_dirs=()):
    return detect(paths, existing_dirs, DEFAULTS)


def test_test_pattern_catalog_covers_go_python_typescript_swift_and_rust():
    cases = (
        (
            ["backend/a.go", "backend/b.go", "backend/c.go", "backend/a_test.go"],
            ("**/*_test.go",),
        ),
        (
            ["cli/a.py", "cli/b.py", "cli/c.py", "cli/test_x.py", "cli/tests/test_y.py"],
            ("**/tests/**", "**/test_*.py"),
        ),
        (
            ["web/a.ts", "web/b.ts", "web/c.ts", "web/a.test.ts", "web/b.spec.ts"],
            ("**/*.test.ts", "**/*.spec.ts"),
        ),
        (
            ["ios/A.swift", "ios/B.swift", "ios/C.swift", "ios/ATests.swift"],
            ("**/*Tests.swift",),
        ),
        (
            [
                "crates/a/src/lib.rs",
                "crates/a/src/a.rs",
                "crates/a/src/b.rs",
                "crates/a/src/a_test.rs",
            ],
            ("**/*_test.rs",),
        ),
    )
    for paths, expected in cases:
        assert _detect(paths).tests == expected


def test_detection_uses_three_file_extension_threshold_and_components():
    detection = _detect(
        [
            "backend/a.go",
            "backend/b.go",
            "backend/c.go",
            "cli/a.go",
            "cli/b.go",
            "cli/c.go",
        ]
    )
    assert detection.production_extensions == ("go",)
    assert detection.components == {
        "backend": ["backend/**"],
        "cli": ["cli/**"],
    }
    assert _detect(["backend/a.go", "backend/b.go", "backend/c.go"]).components is None


def test_extra_exclude_is_added_without_removing_defaults():
    detection = _detect(
        ["backend/a.go", "backend/b.go", "backend/c.go"], {"Pods"}
    )
    assert detection.exclude_extra == ("**/Pods/**",)
    assert set(DEFAULTS["paths"]["exclude"]).issuperset(
        {"**/node_modules/**", "**/*.lock", "**/.next/**"}
    )


def test_default_excludes_do_not_affect_language_or_component_detection():
    detection = _detect(
        [
            "web/a.ts",
            "web/b.ts",
            "web/c.ts",
            "web/node_modules/x.ts",
            "backend/a.ts",
            "backend/b.ts",
            "backend/c.ts",
        ]
    )
    assert detection.production_extensions == ("ts",)
    assert detection.components == {
        "backend": ["backend/**"],
        "web": ["web/**"],
    }
