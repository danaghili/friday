"""Guard #11 — bug-close gate (Stop, BLOCK tier; TECHNICAL_SOW_REBUILD FR-55
guard #11, S-1). Checker verdict matrix (tools/bug_close_check.py) plus the
frozen 5-test hook pattern (AC-13/AC-14) and the AC-15 stranger read.

OWNERSHIP (D-0023, interim finding): this guard owns bug lanes outright —
it judges the full bar (trail AND regression test) and DISARMS the sentinel
on pass; lane_close_gate ignores lane=bug entirely. The cross-guard test at
the bottom pins the exact hole the interim review found: a bug lane with a
passing trail but no regression test must stay armed and blocked even when
both Stop guards run over the same event.
"""
import json
import os
import sys

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

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

INVALID_TRAIL = "trail: lane=bug id=BUG-1 date=2026-07-14\n\n## Asked\nx\n"


FIXED_LEDGER = ("# Bugs — proj\n\n## BUG-1 — the parser crashed on empty input\n\n"
                "**Status:** fixed 2026-07-14 (trail docs/trails/BUG-1.md)\n")
OPEN_LEDGER = ("# Bugs — proj\n\n## BUG-1 — the parser crashed on empty input\n\n"
               "**Status:** open\n")


def _proj(tmp_path, *, trail=VALID_TRAIL, regression_test="tests/test_bug1.py",
         write_regression_test=True, sentinel_lane="bug", sentinel_body=None,
         bugs_md=FIXED_LEDGER):
    root = tmp_path / "proj"
    (root / "docs" / "trails").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "docs" / "DECISIONS.md").write_text("# Decisions — proj\n", encoding="utf-8")
    if bugs_md is not None:
        (root / "docs" / "BUGS.md").write_text(bugs_md, encoding="utf-8")
    if trail is not None:
        (root / "docs" / "trails" / "BUG-1.md").write_text(trail, encoding="utf-8")
    if write_regression_test and regression_test:
        rel_parts = regression_test.split("/")
        p = root
        for part in rel_parts[:-1]:
            p = p / part
            p.mkdir(exist_ok=True)
        (root / regression_test).write_text("def test_x(): assert True\n", encoding="utf-8")
    (root / ".friday").mkdir()
    body = sentinel_body
    if body is None:
        sentinel = {"lane": sentinel_lane, "id": "BUG-1", "trail": "docs/trails/BUG-1.md"}
        if regression_test:
            sentinel["regression-test"] = regression_test
        body = json.dumps(sentinel)
    (root / ".friday" / "lane-open").write_text(body, encoding="utf-8")
    return root


def _stop(proj):
    return {"hook_event_name": "Stop", "cwd": str(proj)}


def _sentinel_path(proj):
    return str(proj / ".friday" / "lane-open")


# --- checker verdict matrix -----------------------------------------------------

def test_missing_regression_test_field_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, regression_test=None, write_regression_test=False)
    res = bcc.check(str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"


def test_regression_test_not_tests_py_path_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, regression_test="src/test_bug1.py")
    res = bcc.check(str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"


def test_regression_test_file_missing_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, regression_test="tests/test_bug1.py", write_regression_test=False)
    res = bcc.check(str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"


def test_invalid_trail_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, trail=INVALID_TRAIL)
    res = bcc.check(str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"


def test_both_valid_is_valid_pass(tmp_path):
    proj = _proj(tmp_path)
    res = bcc.check(str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-pass"


def test_unreadable_sentinel_is_no_verdict(tmp_path):
    proj = _proj(tmp_path, sentinel_body="not json {{{")
    res = bcc.check(str(proj), _sentinel_path(proj))
    assert res["verdict"] == "no-verdict"


# --- the ledger Status flip (journey audit NF11) --------------------------------

def test_ledger_status_still_open_is_valid_fail(tmp_path):
    # A bug must not close while the dedup ledger still calls it open.
    proj = _proj(tmp_path, bugs_md=OPEN_LEDGER)
    res = bcc.check(str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"
    assert "open" in res["summary"].lower()


def test_ledger_entry_missing_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, bugs_md="# Bugs — proj\n\n## BUG-9 — other\n\n**Status:** open\n")
    res = bcc.check(str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"
    assert "BUG-1" in res["summary"]


def test_ledger_file_missing_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, bugs_md=None)
    res = bcc.check(str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"


# --- the hook: 5-test blocking pattern ------------------------------------------

def test_positive_control_missing_regression_test_blocks_stop(tmp_path):
    proj = _proj(tmp_path, regression_test=None, write_regression_test=False)
    p = run_hook(BUILD_ROOT, "bug_close_gate.py", _stop(proj))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in out["reason"], (part, out["reason"])
    assert (proj / ".friday" / "lane-open").is_file()  # never disarms on block


def test_fail_open_all_four_checker_conditions(tmp_path):
    proj = _proj(tmp_path, regression_test=None, write_regression_test=False)
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/bug_close_check.py", mode)
        p = run_hook(pr, "bug_close_gate.py", _stop(proj),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)


def test_valid_bug_close_is_allowed_and_disarms(tmp_path):
    # D-0023: bug lanes have ONE owner — this guard disarms on pass.
    proj = _proj(tmp_path)
    p = run_hook(BUILD_ROOT, "bug_close_gate.py", _stop(proj))
    assert p.stdout.strip() == ""
    assert not (proj / ".friday" / "lane-open").exists()


def test_cross_guard_good_trail_missing_regression_test_stays_armed(tmp_path):
    # The interim review's exact hole: trail passes, regression test absent.
    # Run BOTH Stop guards in hooks.json order over the same event — the bug
    # gate must block and the sentinel must SURVIVE both guards.
    proj = _proj(tmp_path, regression_test=None, write_regression_test=False)
    p6 = run_hook(BUILD_ROOT, "lane_close_gate.py", _stop(proj))
    assert p6.stdout.strip() == ""                       # bug lanes not #6's
    p11 = run_hook(BUILD_ROOT, "bug_close_gate.py", _stop(proj))
    assert json.loads(p11.stdout)["decision"] == "block"
    assert (proj / ".friday" / "lane-open").is_file()    # still armed


def test_patch_lane_is_untouched(tmp_path):
    proj = _proj(tmp_path, sentinel_lane="patch", regression_test=None,
                 write_regression_test=False,
                 sentinel_body=json.dumps({"lane": "patch", "id": "PATCH-1",
                                          "trail": "docs/trails/BUG-1.md"}))
    p = run_hook(BUILD_ROOT, "bug_close_gate.py", _stop(proj))
    assert p.stdout.strip() == ""


def test_no_sentinel_is_a_cheap_no_op(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    p = run_hook(BUILD_ROOT, "bug_close_gate.py", _stop(root))
    assert p.stdout.strip() == ""
