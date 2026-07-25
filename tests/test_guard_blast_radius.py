"""Guard #12 — patch blast-radius (PreToolUse, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55 guard #12, S-2). Checker verdict matrix (tools/
blast_radius_check.py --mode edit) plus the frozen 5-test hook pattern
(AC-13/AC-14) and the AC-15 stranger read. --mode diff (guard #12b's Stop
backstop) is exercised in tests/test_guard_blast_radius_backstop.py.
"""
import json
import os
import sys

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import blast_radius_check as brc  # noqa: E402


def _proj(tmp_path, *, radius=("tools/",), sentinel_lane="patch", sentinel_body=None):
    root = tmp_path / "proj"
    (root / "tools").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / ".friday").mkdir()
    body = sentinel_body
    if body is None:
        sentinel = {"lane": sentinel_lane, "id": "PATCH-1", "trail": "docs/trails/PATCH-1.md"}
        if radius is not None:
            sentinel["blast-radius"] = list(radius)
        body = json.dumps(sentinel)
    (root / ".friday" / "lane-open").write_text(body, encoding="utf-8")
    return root


def _sentinel_path(proj):
    return str(proj / ".friday" / "lane-open")


def _event(root, path):
    return {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": str(root),
            "tool_input": {"file_path": str(path)}}


# --- checker verdict matrix -----------------------------------------------------

def test_no_declared_radius_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, radius=None)
    res = brc.check_edit(str(proj / "tools" / "x.py"), str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"


def test_empty_radius_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, radius=())
    res = brc.check_edit(str(proj / "tools" / "x.py"), str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"


def test_path_outside_radius_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, radius=("tools/",))
    res = brc.check_edit(str(proj / "docs" / "notes.md"), str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-fail"


def test_path_inside_prefix_radius_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, radius=("tools/",))
    res = brc.check_edit(str(proj / "tools" / "x.py"), str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-pass"


def test_path_inside_glob_radius_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, radius=("tests/*.py",))
    (proj / "tests").mkdir()
    res = brc.check_edit(str(proj / "tests" / "test_x.py"), str(proj), _sentinel_path(proj))
    assert res["verdict"] == "valid-pass"


def test_unreadable_sentinel_is_no_verdict(tmp_path):
    proj = _proj(tmp_path, sentinel_body="not json {{{")
    res = brc.check_edit(str(proj / "tools" / "x.py"), str(proj), _sentinel_path(proj))
    assert res["verdict"] == "no-verdict"


# --- the hook: 5-test blocking pattern ------------------------------------------

def test_positive_control_path_outside_radius_is_denied(tmp_path):
    proj = _proj(tmp_path, radius=("tools/",))
    p = run_hook(BUILD_ROOT, "blast_radius_guard.py",
                 _event(proj, proj / "docs" / "notes.md"))
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in reason, (part, reason)


def test_fail_open_all_four_checker_conditions(tmp_path):
    proj = _proj(tmp_path, radius=("tools/",))
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/blast_radius_check.py", mode)
        p = run_hook(pr, "blast_radius_guard.py",
                     _event(proj, proj / "docs" / "notes.md"),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)


def test_path_inside_radius_is_allowed(tmp_path):
    proj = _proj(tmp_path, radius=("tools/",))
    p = run_hook(BUILD_ROOT, "blast_radius_guard.py", _event(proj, proj / "tools" / "x.py"))
    assert p.stdout.strip() == ""


def test_non_patch_lane_is_untouched(tmp_path):
    proj = _proj(tmp_path, sentinel_lane="bug", radius=None)
    p = run_hook(BUILD_ROOT, "blast_radius_guard.py",
                 _event(proj, proj / "docs" / "notes.md"))
    assert p.stdout.strip() == ""


def test_no_sentinel_is_a_cheap_no_op(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    p = run_hook(BUILD_ROOT, "blast_radius_guard.py", _event(root, root / "docs" / "x.md"))
    assert p.stdout.strip() == ""
