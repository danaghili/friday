"""BUG-010 regression — guard #11's requirement 1 hard-coded tests/*.py.

On a TS/Vitest project the real regression test is a committed .test.ts
file; the old check rejected every non-Python path before it ever looked at
existence, so no honest close could pass (docs/BUGS.md BUG-010, D-0185).
The rule after the fix: the declared path must EXIST and its filename must
be test-shaped — it carries "test" or "spec", any case, any directory.
These tests pin both halves and the surviving Python convention.
"""
import json
import os
import sys

from guardkit import BUILD_ROOT

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import bug_close_check as bcc  # noqa: E402

VALID_TRAIL = """trail: lane=bug id=BUG-1 date=2026-07-14

## Asked
The parser crashed on empty input.

## Decisions
decisions: none — change fully specified by the ask

## Proof
proof: `python3 -m pytest tests/ -q` → all green

changelog: fixed the empty-input crash
"""

FIXED_LEDGER = ("# Bugs — proj\n\n## BUG-1 — the parser crashed on empty input\n\n"
                "**Status:** fixed 2026-07-14 (trail docs/trails/BUG-1.md)\n")


def _proj(tmp_path, regression_test, *, write_regression_test=True):
    """A minimal full-bar fixture: valid trail, flipped ledger, decisions log
    — so the only variable under test is requirement 1's path judgment."""
    root = tmp_path / "proj"
    (root / "docs" / "trails").mkdir(parents=True)
    (root / "docs" / "DECISIONS.md").write_text("# Decisions — proj\n",
                                                encoding="utf-8")
    (root / "docs" / "BUGS.md").write_text(FIXED_LEDGER, encoding="utf-8")
    (root / "docs" / "trails" / "BUG-1.md").write_text(VALID_TRAIL,
                                                       encoding="utf-8")
    if write_regression_test:
        p = root
        for part in regression_test.split("/")[:-1]:
            p = p / part
            p.mkdir(exist_ok=True)
        (p / regression_test.split("/")[-1]).write_text(
            "// regression pin\n", encoding="utf-8")
    sentinel = tmp_path / "sentinel.json"
    sentinel.write_text(json.dumps({
        "lane": "bug", "id": "BUG-1", "trail": "docs/trails/BUG-1.md",
        "regression-test": regression_test}), encoding="utf-8")
    return str(root), str(sentinel)


def test_vitest_convention_in_tests_dir_passes(tmp_path):
    root, sentinel = _proj(tmp_path, "tests/bug-42-close-gate.test.ts")
    assert bcc.check(root, sentinel)["verdict"] == "valid-pass"


def test_colocated_vitest_test_passes(tmp_path):
    # Vitest colocates unit tests beside the source — no tests/ prefix.
    root, sentinel = _proj(tmp_path, "src/lib/dates.test.ts")
    assert bcc.check(root, sentinel)["verdict"] == "valid-pass"


def test_spec_convention_passes(tmp_path):
    # The Playwright/Jasmine family names by .spec.
    root, sentinel = _proj(tmp_path, "e2e/checkout.spec.ts")
    assert bcc.check(root, sentinel)["verdict"] == "valid-pass"


def test_python_convention_still_passes(tmp_path):
    root, sentinel = _proj(tmp_path, "tests/test_bug1.py")
    assert bcc.check(root, sentinel)["verdict"] == "valid-pass"


def test_non_test_shaped_filename_fails(tmp_path):
    # Existence alone is not enough: a declared path whose filename carries
    # neither "test" nor "spec" is not a regression test.
    root, sentinel = _proj(tmp_path, "src/helpers.ts")
    res = bcc.check(root, sentinel)
    assert res["verdict"] == "valid-fail"


def test_missing_test_shaped_file_fails_on_existence(tmp_path):
    # A test-shaped path that does not exist must fail for THAT reason —
    # the old code masked it behind "not a tests/*.py path".
    root, sentinel = _proj(tmp_path, "tests/bug-9.test.ts",
                           write_regression_test=False)
    res = bcc.check(root, sentinel)
    assert res["verdict"] == "valid-fail"
    assert "does not exist" in res["summary"]
