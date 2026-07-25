"""Guard #18a — worktree-create substrate-sharing check (WorktreeCreate,
BLOCK tier; TECHNICAL_SOW_REBUILD FR-55 guard #18a). Checker verdict matrix
(tools/worktree_create_check.py) plus the guard's OWN 5-test shape (this
event has no permission-deny channel — it is a producer, not an observer):
positive control → NO worktreePath on stdout (creation fails, that IS the
block); all four fail-open controls → worktreePath present (fail-open must
never break worktree creation).
"""
import json
import os
import subprocess
import sys

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import worktree_create_check as wcc  # noqa: E402


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path, name="proj"):
    root = tmp_path / name
    root.mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "f.txt").write_text("x", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "c0")
    return root


def _event(root, requested):
    return {"hook_event_name": "WorktreeCreate", "cwd": str(root), "path": requested}


# --- checker verdict matrix -----------------------------------------------------

def test_inside_friday_dir_is_valid_fail(tmp_path):
    root = _repo(tmp_path)
    (root / ".friday").mkdir()
    res = wcc.check(str(root / ".friday" / "worktrees" / "w1"), str(root))
    assert res["verdict"] == "valid-fail"


def test_inside_unrelated_repo_is_valid_fail(tmp_path):
    root = _repo(tmp_path, "proj")
    other = _repo(tmp_path, "other")
    res = wcc.check(str(other / "sub"), str(root))
    assert res["verdict"] == "valid-fail"


def test_fresh_location_outside_any_repo_is_no_verdict(tmp_path):
    root = _repo(tmp_path, "proj")
    fresh = tmp_path / "elsewhere"
    fresh.mkdir()
    res = wcc.check(str(fresh / "w1"), str(root))
    assert res["verdict"] == "no-verdict"


def test_path_inside_same_repo_tree_is_valid_pass(tmp_path):
    root = _repo(tmp_path, "proj")
    res = wcc.check(str(root / "sibling_dir" / "w1"), str(root))
    assert res["verdict"] == "valid-pass"


# --- the hook: guard #18a's own 5-test shape ------------------------------------

def test_positive_control_path_inside_friday_withholds_worktree_path(tmp_path):
    root = _repo(tmp_path)
    (root / ".friday").mkdir()
    requested = str(root / ".friday" / "worktrees" / "w1")
    p = run_hook(BUILD_ROOT, "worktree_create_guard.py", _event(root, requested))
    assert p.stdout.strip() == ""
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in p.stderr, (part, p.stderr)


def test_fail_open_all_four_checker_conditions_still_emit_the_path(tmp_path):
    root = _repo(tmp_path)
    (root / ".friday").mkdir()
    requested = str(root / ".friday" / "worktrees" / "w1")  # the same seeded lie
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/worktree_create_check.py", mode)
        p = run_hook(pr, "worktree_create_guard.py", _event(root, requested),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        out = json.loads(p.stdout)
        assert out["hookSpecificOutput"]["worktreePath"] == requested, (mode, p.stdout)


def test_legitimate_sibling_path_emits_the_path(tmp_path):
    root = _repo(tmp_path)
    requested = str(root / "sibling_dir" / "w1")
    p = run_hook(BUILD_ROOT, "worktree_create_guard.py", _event(root, requested))
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["worktreePath"] == requested


def test_no_requested_path_prints_nothing(tmp_path):
    root = _repo(tmp_path)
    event = {"hook_event_name": "WorktreeCreate", "cwd": str(root)}
    p = run_hook(BUILD_ROOT, "worktree_create_guard.py", event)
    assert p.stdout.strip() == ""
    assert p.stderr.strip() == ""


def test_tool_input_path_key_is_also_read(tmp_path):
    root = _repo(tmp_path)
    requested = str(root / "sibling_dir" / "w2")
    event = {"hook_event_name": "WorktreeCreate", "cwd": str(root),
             "tool_input": {"path": requested}}
    p = run_hook(BUILD_ROOT, "worktree_create_guard.py", event)
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["worktreePath"] == requested
