"""Worktree-substrate warn (SessionStart, WARN tier; D-0023 item 3 — replaces
guard #18a's protection). Exemplar: hooks/graph_freshness_guard.py. No
checker — pure stat logic, like hooks/teammate_idle_nudge.py.

Cheap-first: only a LINKED worktree (resolve_worktree_root != resolve_
project_root) is even a candidate; a plain repo (or no repo) is a stat-free
no-op. Inside a linked worktree, a LOCAL `.friday/` at the worktree root
that differs from the SHARED `.friday/` (fs.friday_dir) is the shadow this
warns about — records written there are stale or lost.
"""
import json
import subprocess
import sys

from guardkit import BUILD_ROOT, run_hook


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _main_repo(tmp_path):
    root = tmp_path / "main"
    root.mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "f.txt").write_text("x", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "c0")
    return root


def _linked_worktree(tmp_path, main_repo, name="wt"):
    wt = tmp_path / name
    _git(main_repo, "worktree", "add", "-q", str(wt))
    return wt


def _event(cwd):
    return {"hook_event_name": "SessionStart", "cwd": str(cwd)}


def test_shadowed_local_friday_in_linked_worktree_warns(tmp_path):
    main = _main_repo(tmp_path)
    wt = _linked_worktree(tmp_path, main)
    (wt / ".friday").mkdir()
    p = run_hook(BUILD_ROOT, "worktree_substrate_warn.py", _event(wt))
    out = json.loads(p.stdout)
    assert ".friday" in out["systemMessage"]
    assert "decision" not in out
    assert "hookSpecificOutput" not in out


def test_linked_worktree_without_local_friday_is_silent(tmp_path):
    main = _main_repo(tmp_path)
    wt = _linked_worktree(tmp_path, main)
    p = run_hook(BUILD_ROOT, "worktree_substrate_warn.py", _event(wt))
    assert p.stdout.strip() == ""


def test_plain_non_worktree_repo_is_silent(tmp_path):
    main = _main_repo(tmp_path)
    p = run_hook(BUILD_ROOT, "worktree_substrate_warn.py", _event(main))
    assert p.stdout.strip() == ""


def test_garbage_stdin_is_silent_and_exits_zero():
    proc = subprocess.run(
        [sys.executable, f"{BUILD_ROOT}/hooks/worktree_substrate_warn.py", BUILD_ROOT],
        input="not json {{{", capture_output=True, text=True)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
