"""Guard #12b — blast-radius Stop backstop (Stop, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #12b, S-2). WARN guards never carry the
blocking 5-test pattern (that binds block-tier guards); what they must
prove instead is the never-blocks posture and quiet degradation — mirrors
tests/test_guard_graph_freshness.py's shape.
"""
import json
import subprocess

from guardkit import BUILD_ROOT, broken_plugin, run_hook


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path):
    root = tmp_path / "proj"
    (root / "tools").mkdir(parents=True)
    (root / "docs").mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / ".gitignore").write_text(".friday/\n", encoding="utf-8")  # D-0007: always ignored
    (root / "tools" / "base.py").write_text("x", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "c0")
    return root


def _arm(root, *, radius=("tools/",)):
    (root / ".friday").mkdir(exist_ok=True)
    (root / ".friday" / "lane-open").write_text(
        json.dumps({"lane": "patch", "id": "PATCH-1", "trail": "docs/trails/PATCH-1.md",
                    "blast-radius": list(radius)}), encoding="utf-8")


def _stop(root):
    return {"hook_event_name": "Stop", "cwd": str(root)}


def test_drift_outside_radius_warns_and_never_blocks(tmp_path):
    root = _repo(tmp_path)
    _arm(root)
    (root / "tools" / "base.py").write_text("changed", encoding="utf-8")
    (root / "docs" / "extra.md").write_text("outside radius", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "blast_radius_backstop.py", _stop(root))
    out = json.loads(p.stdout)
    assert "extra.md" in out["systemMessage"] or "outside" in out["systemMessage"].lower()
    assert "decision" not in out
    assert "hookSpecificOutput" not in out


def test_all_changes_inside_radius_is_silent(tmp_path):
    root = _repo(tmp_path)
    _arm(root)
    (root / "tools" / "base.py").write_text("changed", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "blast_radius_backstop.py", _stop(root))
    assert p.stdout.strip() == ""


def test_no_sentinel_is_a_cheap_no_op(tmp_path):
    root = _repo(tmp_path)
    p = run_hook(BUILD_ROOT, "blast_radius_backstop.py", _stop(root))
    assert p.stdout.strip() == ""


def test_non_patch_lane_is_untouched(tmp_path):
    root = _repo(tmp_path)
    (root / ".friday").mkdir()
    (root / ".friday" / "lane-open").write_text(
        json.dumps({"lane": "bug", "id": "BUG-1", "trail": "docs/trails/BUG-1.md"}),
        encoding="utf-8")
    (root / "docs" / "extra.md").write_text("x", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "blast_radius_backstop.py", _stop(root))
    assert p.stdout.strip() == ""


def test_broken_checker_stays_quiet(tmp_path):
    root = _repo(tmp_path)
    _arm(root)
    (root / "docs" / "extra.md").write_text("x", encoding="utf-8")
    pr = broken_plugin(tmp_path, "tools/blast_radius_check.py", "crash")
    p = run_hook(pr, "blast_radius_backstop.py", _stop(root))
    assert p.stdout.strip() == ""
