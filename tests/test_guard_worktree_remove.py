"""Guard #18b — worktree-remove warn (WorktreeRemove, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #18b). Doc-only harness event
(probe-hook-events.md) — no checker, the sentinel's presence alone is the
fact being warned about.
"""
import json

from guardkit import BUILD_ROOT, run_hook


def _proj(tmp_path, *, armed=True, sentinel_body=None):
    root = tmp_path / "proj"
    root.mkdir()
    if armed:
        (root / ".friday").mkdir()
        body = sentinel_body if sentinel_body is not None else json.dumps(
            {"lane": "patch", "id": "PATCH-1", "trail": "docs/trails/PATCH-1.md"})
        (root / ".friday" / "lane-open").write_text(body, encoding="utf-8")
    return root


def _event(root):
    return {"hook_event_name": "WorktreeRemove", "cwd": str(root)}


def test_open_lane_warns_and_never_blocks(tmp_path):
    proj = _proj(tmp_path)
    p = run_hook(BUILD_ROOT, "worktree_remove_warn.py", _event(proj))
    out = json.loads(p.stdout)
    assert "patch" in out["systemMessage"] and "PATCH-1" in out["systemMessage"]
    assert "decision" not in out
    assert "hookSpecificOutput" not in out


def test_no_open_lane_is_silent(tmp_path):
    proj = _proj(tmp_path, armed=False)
    p = run_hook(BUILD_ROOT, "worktree_remove_warn.py", _event(proj))
    assert p.stdout.strip() == ""


def test_unreadable_sentinel_still_warns_generically(tmp_path):
    proj = _proj(tmp_path, sentinel_body="not json {{{")
    p = run_hook(BUILD_ROOT, "worktree_remove_warn.py", _event(proj))
    out = json.loads(p.stdout)
    assert "open" in out["systemMessage"].lower()
    assert "decision" not in out
    assert "hookSpecificOutput" not in out
