"""Guard #7 through the real hook — the frozen 5-test pattern (AC-13/AC-14)
plus the AC-15 stranger read of its block text.

Positive control: an in-build Edit event aimed at a test committed before
the epoch, no permission record → PreToolUse deny. Fail-open controls: the
same seeded lie with tools/committed_test_check.py deleted / crashing /
timing out / emitting an invalid-empty verdict → the edit is ALLOWED (empty
stdout; breadcrumb on stderr only). The checker's own verdict matrix lives
in tests/test_committed_test_check.py; these tests pin the HOOK's behavior.
"""
import json
import os
import subprocess

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

EPOCH = "2026-07-10T12:00:00Z"
PRE = "2026-07-01T00:00:00 +0000"

STATE_BLOCK = ("<!-- FRIDAY-STATE:BEGIN -->\n"
               "state: build-in-progress\n"
               f"since: {EPOCH}\n"
               "<!-- FRIDAY-STATE:END -->\n")


def _git(repo, *args, date=None):
    env = dict(os.environ)
    if date:
        env["GIT_COMMITTER_DATE"] = date
        env["GIT_AUTHOR_DATE"] = date
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=env,
                   capture_output=True)


def _proj(tmp_path):
    """A friday project mid-build with a pre-epoch committed test — the
    seeded lie every control below aims at."""
    root = tmp_path / "proj"
    (root / "tests").mkdir(parents=True)
    (root / "docs").mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "CLAUDE.md").write_text("# proj\n\n" + STATE_BLOCK, encoding="utf-8")
    (root / "docs" / "DECISIONS.md").write_text("# Decisions — proj\n", encoding="utf-8")
    (root / "tests" / "test_old.py").write_text("def test_x(): assert True\n",
                                                encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "scaffold", date=PRE)
    return root


def _edit_event(proj, path=None):
    return {"hook_event_name": "PreToolUse", "tool_name": "Edit",
            "cwd": str(proj),
            "tool_input": {"file_path": path or str(proj / "tests" / "test_old.py")}}


def test_positive_control_seeded_lie_is_denied(tmp_path):
    proj = _proj(tmp_path)
    p = run_hook(BUILD_ROOT, "committed_test_guard.py", _edit_event(proj))
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    # AC-15: the four stranger-proof parts.
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in reason, (part, reason)


def test_fail_open_all_four_checker_conditions(tmp_path):
    proj = _proj(tmp_path)
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/committed_test_check.py", mode)
        p = run_hook(pr, "committed_test_guard.py", _edit_event(proj),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)  # ALLOW, never deny


def test_permission_record_unlocks_the_edit(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "DECISIONS.md").write_text(
        "# Decisions — proj\n\n## D-0001 — PM permits the fix\n"
        "- **Decision:** tests/test_old.py may be corrected.\n"
        "override-grant: tests/test_old.py\n", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "committed_test_guard.py", _edit_event(proj))
    assert p.stdout.strip() == ""


def test_non_test_edit_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    p = run_hook(BUILD_ROOT, "committed_test_guard.py",
                 _edit_event(proj, path=str(proj / "docs" / "notes.md")))
    assert p.stdout.strip() == ""


def test_event_without_a_path_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    event = {"hook_event_name": "PreToolUse", "tool_name": "Edit",
             "cwd": str(proj), "tool_input": {}}
    p = run_hook(BUILD_ROOT, "committed_test_guard.py", event)
    assert p.stdout.strip() == ""
