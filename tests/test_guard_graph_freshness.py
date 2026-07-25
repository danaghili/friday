"""Guard #8 — the WARN-tier exemplar (FR-56, FR-71): checker verdict matrix
plus the hook's one law — it may inform, it may never block. Warn guards
don't carry the blocking 5-test pattern (AC-13/14 bind blocking guards);
what they must prove instead is the never-blocks posture and quiet
degradation.
"""
import json
import os
import subprocess
import sys

from guardkit import BUILD_ROOT, broken_plugin, run_hook

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import graph_freshness_check as gfc  # noqa: E402


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path, *, commits=2):
    root = tmp_path / "proj"
    root.mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    hashes = []
    for i in range(commits):
        (root / f"f{i}.txt").write_text(str(i), encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", f"c{i}")
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        hashes.append(out.stdout.strip())
    return root, hashes


def _stamp(root, value):
    (root / ".friday").mkdir(exist_ok=True)
    (root / ".friday" / "graph.stamp").write_text(value, encoding="utf-8")


# --- checker verdicts ---------------------------------------------------------

def test_no_stamp_means_no_graph_adopted(tmp_path):
    root, _ = _repo(tmp_path)
    assert gfc.check(str(root))["verdict"] == "valid-pass"


def test_current_stamp_passes(tmp_path):
    root, hashes = _repo(tmp_path)
    _stamp(root, hashes[-1])
    assert gfc.check(str(root))["verdict"] == "valid-pass"


def test_stale_stamp_fails_with_commits_behind(tmp_path):
    root, hashes = _repo(tmp_path)
    _stamp(root, hashes[0])
    res = gfc.check(str(root))
    assert res["verdict"] == "valid-fail"
    assert res["behind"] == 1
    assert "behind" in res["summary"]


def test_garbage_stamp_is_no_verdict(tmp_path):
    root, _ = _repo(tmp_path)
    _stamp(root, "not-a-commit-hash")
    assert gfc.check(str(root))["verdict"] == "no-verdict"


def test_empty_stamp_is_no_verdict(tmp_path):
    root, _ = _repo(tmp_path)
    _stamp(root, "")
    assert gfc.check(str(root))["verdict"] == "no-verdict"


# --- the hook: warns, never blocks ---------------------------------------------

def _event(root):
    return {"hook_event_name": "PostToolUse", "tool_name": "Write",
            "cwd": str(root), "tool_input": {"file_path": str(root / "x.py")}}


def test_stale_graph_warns_and_never_blocks(tmp_path):
    root, hashes = _repo(tmp_path)
    _stamp(root, hashes[0])
    p = run_hook(BUILD_ROOT, "graph_freshness_guard.py", _event(root))
    out = json.loads(p.stdout)
    assert "behind" in out["systemMessage"]
    assert "decision" not in out                      # warn tier NEVER blocks
    assert "hookSpecificOutput" not in out


def test_fresh_graph_is_silent(tmp_path):
    root, hashes = _repo(tmp_path)
    _stamp(root, hashes[-1])
    p = run_hook(BUILD_ROOT, "graph_freshness_guard.py", _event(root))
    assert p.stdout.strip() == ""


def test_no_stamp_is_a_cheap_no_op(tmp_path):
    root, _ = _repo(tmp_path)
    p = run_hook(BUILD_ROOT, "graph_freshness_guard.py", _event(root))
    assert p.stdout.strip() == ""


def test_broken_checker_stays_quiet(tmp_path):
    root, hashes = _repo(tmp_path)
    _stamp(root, hashes[0])
    pr = broken_plugin(tmp_path, "tools/graph_freshness_check.py", "crash")
    p = run_hook(pr, "graph_freshness_guard.py", _event(root))
    assert p.stdout.strip() == ""
