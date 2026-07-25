"""Guard #10 — design-contract gate (PreToolUse, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55 guard #10, D-0018). Checker verdict matrix
(tools/design_contract_check.py) plus the frozen 5-test hook pattern
(AC-13/AC-14) and the AC-15 stranger read.

Positive control: an edit to a COMMITTED docs/contracts/ file with no
re-sync record in DECISIONS.md → PreToolUse block. Fail-open controls: same
seeded lie with tools/design_contract_check.py deleted / crashing / timing
out / emitting an invalid-empty verdict → ALLOWED.
"""
import json
import os
import subprocess
import sys

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import design_contract_check as dcc  # noqa: E402


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _proj(tmp_path, *, commit_contract=True, decisions_text="# Decisions\n"):
    root = tmp_path / "proj"
    (root / "docs" / "contracts").mkdir(parents=True)
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "README.md").write_text("scaffold\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "scaffold")  # a real commit exists either way
    (root / "docs" / "DECISIONS.md").write_text(decisions_text, encoding="utf-8")
    (root / "docs" / "contracts" / "foo.md").write_text("# foo contract\n", encoding="utf-8")
    if commit_contract:
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "add contract")
    return root


def _event(root, path):
    return {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": str(root),
            "tool_input": {"file_path": str(path)}}


# --- checker verdict matrix -----------------------------------------------------

def test_untracked_file_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, commit_contract=False)
    res = dcc.check(str(proj / "docs" / "contracts" / "foo.md"), str(proj))
    assert res["verdict"] == "valid-pass"


def test_committed_undocumented_is_valid_fail(tmp_path):
    proj = _proj(tmp_path)
    res = dcc.check(str(proj / "docs" / "contracts" / "foo.md"), str(proj))
    assert res["verdict"] == "valid-fail"


def test_committed_documented_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, decisions_text="# Decisions\n\n## D-0001 — re-sync\n"
                                          "override-grant: docs/contracts/foo.md\n")
    res = dcc.check(str(proj / "docs" / "contracts" / "foo.md"), str(proj))
    assert res["verdict"] == "valid-pass"


def test_committed_bare_mention_does_not_unlock(tmp_path):
    # A3 (harden): a bare mention / rejection must NOT unlock a locked contract.
    proj = _proj(tmp_path, decisions_text="# Decisions\n\n## D-0001 — rejected\n"
                                          "we did NOT re-sync docs/contracts/foo.md.\n")
    res = dcc.check(str(proj / "docs" / "contracts" / "foo.md"), str(proj))
    assert res["verdict"] == "valid-fail"


def test_non_git_repo_is_no_verdict(tmp_path):
    bare = tmp_path / "bare"
    (bare / "docs" / "contracts").mkdir(parents=True)
    (bare / "docs" / "contracts" / "foo.md").write_text("x", encoding="utf-8")
    res = dcc.check(str(bare / "docs" / "contracts" / "foo.md"), str(bare))
    assert res["verdict"] == "no-verdict"


# --- the hook: 5-test blocking pattern ------------------------------------------

def test_positive_control_locked_contract_edit_is_denied(tmp_path):
    proj = _proj(tmp_path)
    p = run_hook(BUILD_ROOT, "design_contract_guard.py",
                 _event(proj, proj / "docs" / "contracts" / "foo.md"))
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in reason, (part, reason)


def test_fail_open_all_four_checker_conditions(tmp_path):
    proj = _proj(tmp_path)
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/design_contract_check.py", mode)
        p = run_hook(pr, "design_contract_guard.py",
                     _event(proj, proj / "docs" / "contracts" / "foo.md"),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)


def test_new_uncommitted_contract_is_allowed(tmp_path):
    proj = _proj(tmp_path, commit_contract=False)
    p = run_hook(BUILD_ROOT, "design_contract_guard.py",
                 _event(proj, proj / "docs" / "contracts" / "foo.md"))
    assert p.stdout.strip() == ""


def test_decision_record_unlocks_the_edit(tmp_path):
    proj = _proj(tmp_path, decisions_text="# Decisions\n\n## D-0001 — re-sync\n"
                                          "override-grant: docs/contracts/foo.md\n")
    p = run_hook(BUILD_ROOT, "design_contract_guard.py",
                 _event(proj, proj / "docs" / "contracts" / "foo.md"))
    assert p.stdout.strip() == ""


def test_non_contract_path_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "notes.md").write_text("x", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "design_contract_guard.py",
                 _event(proj, proj / "docs" / "notes.md"))
    assert p.stdout.strip() == ""
