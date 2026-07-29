"""INC-008 FR-8.5 / AC-8.1 / AC-8.5 / AC-8.13 / KH-5 — the enforcement hook.

The blocking-guard 5-test pattern (guardkit): one positive control that the
armed gate blocks an un-dispositioned breach, plus the four fail-open controls
(checker missing / crash / timeout / invalid verdict) that must ALLOW. Adds the
INC-008-specific behaviors: warn-first (disarmed → warn, never block) and the
non-adopter invariant (no declared bars → the checker is never even reached).
"""
import json
import os
import subprocess

import pytest

import guardkit

CHECKER = "tools/maintainability_gate_check.py"
HOOK = "maintainability_gate.py"

_BREACH_SRC = "def big(a, b, c, d, e, f, g):\n    return a\n"


def _proj(tmp_path, *, arm=None, bars="maintainability: param-count <= 4"):
    root = tmp_path / "proj"
    (root / "docs" / "standards").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    arm_line = f"\narm: {arm}" if arm else ""
    (root / "docs" / "standards" / "coding-standards.md").write_text(
        f"# standards\n<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n{bars}{arm_line}\n"
        "<!-- FRIDAY-MAINTAINABILITY:END -->\n", encoding="utf-8")
    (root / "app.py").write_text(_BREACH_SRC, encoding="utf-8")   # 7 params > 4
    return root


def _run(plugin_root, proj):
    return guardkit.run_hook(plugin_root, HOOK, {"cwd": str(proj)})


def test_armed_gate_blocks_an_undispositioned_breach(tmp_path):
    proj = _proj(tmp_path, arm="block")
    out = _run(guardkit.BUILD_ROOT, proj).stdout
    assert out.strip(), "armed gate must emit a block decision"
    emitted = json.loads(out)
    assert emitted.get("decision") == "block"
    assert "Override path" in emitted["reason"] and "Why:" in emitted["reason"]


def test_the_block_names_an_override_that_actually_clears_it(tmp_path):
    """A block whose stated escape hatch does not work is worse than no block:
    the reader follows the instruction, stays blocked, and stops trusting the
    next message (the BUG-005 shape). The checker reads the judge's ENVELOPE, so
    that is what the override has to name. The deviations ledger is the durable
    record that accompanies a disposition — writing it does not clear the gate,
    and the message must not imply it does."""
    proj = _proj(tmp_path, arm="block")
    emitted = json.loads(_run(guardkit.BUILD_ROOT, proj).stdout)
    override = emitted["reason"].split("Override path:", 1)[1]
    assert "envelope" in override.lower(), override
    assert "arm: warn" in override, override
    if "standards_deviations" in override:
        assert "does not clear" in override or "not the thing" in override, override


def test_all_malformed_bars_warns_instead_of_silent_noop(tmp_path):
    # A typo'd bar means the PM THINKS a bar is enforced when nothing is —
    # the gate must say so, never quietly treat the project as a non-adopter.
    proj = _proj(tmp_path, arm=None, bars="maintainability: param-count at most 4")
    out = _run(guardkit.BUILD_ROOT, proj).stdout
    assert out.strip(), "malformed-only bars must surface a warn"
    emitted = json.loads(out)
    assert emitted.get("decision") != "block"
    assert "malformed" in emitted["systemMessage"].lower()
    assert "param-count at most 4" in emitted["systemMessage"]


def test_mixed_malformed_bar_is_named_in_the_verdict(tmp_path):
    # Valid bars still enforce; the malformed sibling is named as NOT enforced.
    proj = _proj(tmp_path, arm="block",
                 bars="maintainability: param-count <= 4\n"
                      "maintainability: file-length at most 300")
    out = _run(guardkit.BUILD_ROOT, proj).stdout
    emitted = json.loads(out)
    assert emitted.get("decision") == "block"          # the valid bar still bites
    assert "file-length at most 300" in emitted["reason"]


def test_gate_engages_from_a_subdirectory_cwd(tmp_path):
    # A session started in a subdir must not silently disable the capability —
    # the gate anchors on the worktree root like every sibling Stop gate.
    proj = _proj(tmp_path, arm="block")
    sub = proj / "app"
    sub.mkdir()
    out = guardkit.run_hook(guardkit.BUILD_ROOT, HOOK, {"cwd": str(sub)}).stdout
    assert out.strip(), "gate must still engage when cwd is a project subdir"
    emitted = json.loads(out)
    assert emitted.get("decision") == "block"


def test_warn_first_disarmed_never_blocks(tmp_path):
    proj = _proj(tmp_path, arm=None)          # warn-first default
    out = _run(guardkit.BUILD_ROOT, proj).stdout
    if out.strip():
        emitted = json.loads(out)
        assert emitted.get("decision") != "block"    # a systemMessage warn, never a block
        assert "systemMessage" in emitted


def test_non_adopter_no_bars_is_a_noop(tmp_path):
    proj = _proj(tmp_path, arm="block", bars="")   # block present but empty — no real bars
    # rewrite standards to have NO maintainability block at all
    (proj / "docs" / "standards" / "coding-standards.md").write_text(
        "# standards, no bars\n", encoding="utf-8")
    out = _run(guardkit.BUILD_ROOT, proj).stdout
    assert out.strip() == ""                  # zero new behavior for a non-adopter


@pytest.mark.parametrize("mode", guardkit.FAIL_OPEN_MODES)
def test_fails_open_when_checker_is_broken(tmp_path, mode):
    proj = _proj(tmp_path, arm="block")       # armed — so only fail-open can save it
    broken = guardkit.broken_plugin(tmp_path, CHECKER, mode)
    env = {"FRIDAY_GUARD_TIMEOUT_S": "1"} if mode == "timeout" else None
    out = guardkit.run_hook(broken, HOOK, {"cwd": str(proj)}, env=env).stdout
    if out.strip():
        assert json.loads(out).get("decision") != "block"   # a broken checker must never block


# --- task #7: the cheap self-gate — skip the whole-tree scan when nothing moved --------

def _sig(root):
    """The hook's own signature helper, white-box (same sys.path the hook gets)."""
    import sys as _sys
    for sub in ("hooks", "tools"):
        p = os.path.join(guardkit.BUILD_ROOT, sub)
        if p not in _sys.path:
            _sys.path.insert(0, p)
    import maintainability_gate as mg
    standards = os.path.join(str(root), "docs", "standards", "coding-standards.md")
    envelope = os.path.join(str(root), ".friday", "maintainability-envelope.md")
    return mg._tree_signature(str(root), standards, envelope)


def _stamp_path(root):
    return os.path.join(str(root), ".friday", "maintainability-scan.stamp")


def test_a_clean_scan_writes_the_skip_stamp(tmp_path):
    """The cache exists only on the safe side: a scan that found nothing wrong
    records the tree's shape so the next Stop can skip the re-scan."""
    proj = _proj(tmp_path, arm="block", bars="maintainability: param-count <= 10")
    out = _run(guardkit.BUILD_ROOT, proj)
    assert not out.stdout.strip()  # clean: no block, no warn
    assert os.path.isfile(_stamp_path(proj))
    stamp = json.load(open(_stamp_path(proj)))
    assert stamp["root"] == str(proj) and stamp["count"] >= 1


def test_an_unchanged_tree_skips_the_rescan(tmp_path):
    """THE skip proof, observed from behavior: a stamp matching the current
    tree suppresses the scan entirely — planted over a breaching armed project,
    the gate emits nothing, which only happens if the checker never ran."""
    proj = _proj(tmp_path, arm="block")  # breaching: would block if scanned
    (proj / ".friday").mkdir(exist_ok=True)
    count, max_mtime = _sig(proj)
    json.dump({"root": str(proj), "count": count, "max_mtime": max_mtime},
              open(_stamp_path(proj), "w"))
    out = _run(guardkit.BUILD_ROOT, proj)
    assert not out.stdout.strip(), out.stdout


def test_a_breaching_scan_writes_no_stamp(tmp_path):
    """A standing breach must be re-evaluated at every Stop — the envelope can
    change between them — so only a clean verdict ever earns the cache."""
    proj = _proj(tmp_path, arm="warn")  # breaching, warn tier
    out = _run(guardkit.BUILD_ROOT, proj)
    assert "warn-first" in out.stdout
    assert not os.path.exists(_stamp_path(proj))


def test_editing_a_py_file_invalidates_the_stamp(tmp_path):
    proj = _proj(tmp_path, arm="block")
    (proj / ".friday").mkdir(exist_ok=True)
    count, max_mtime = _sig(proj)
    json.dump({"root": str(proj), "count": count, "max_mtime": max_mtime},
              open(_stamp_path(proj), "w"))
    src = proj / "app.py"
    src.write_text(src.read_text(), encoding="utf-8")
    os.utime(src, (max_mtime + 5, max_mtime + 5))
    out = _run(guardkit.BUILD_ROOT, proj)
    assert json.loads(out.stdout).get("decision") == "block"


def test_editing_the_standards_or_envelope_invalidates_the_stamp(tmp_path):
    """Tightening a bar or withdrawing a disposition can create a breach on an
    UNCHANGED tree — both files are part of the signature for exactly that."""
    for touched in ("docs/standards/coding-standards.md",
                    ".friday/maintainability-envelope.md"):
        proj = _proj(tmp_path / touched.replace("/", "_"), arm="block")
        (proj / ".friday").mkdir(exist_ok=True)
        count, max_mtime = _sig(proj)
        json.dump({"root": str(proj), "count": count, "max_mtime": max_mtime},
                  open(_stamp_path(proj), "w"))
        target = proj / touched
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
        os.utime(target, (max_mtime + 5, max_mtime + 5))
        out = _run(guardkit.BUILD_ROOT, proj)
        assert json.loads(out.stdout).get("decision") == "block", touched


def test_a_stamp_from_another_worktree_does_not_suppress(tmp_path):
    """.friday/ is shared across worktrees; a clean scan of worktree A must not
    silence worktree B's different tree."""
    proj = _proj(tmp_path, arm="block")
    (proj / ".friday").mkdir(exist_ok=True)
    count, max_mtime = _sig(proj)
    json.dump({"root": "/somewhere/else", "count": count, "max_mtime": max_mtime},
              open(_stamp_path(proj), "w"))
    out = _run(guardkit.BUILD_ROOT, proj)
    assert json.loads(out.stdout).get("decision") == "block"


def test_a_corrupt_stamp_means_scan_not_skip(tmp_path):
    proj = _proj(tmp_path, arm="block")
    (proj / ".friday").mkdir(exist_ok=True)
    open(_stamp_path(proj), "w").write("{not json")
    out = _run(guardkit.BUILD_ROOT, proj)
    assert json.loads(out.stdout).get("decision") == "block"


# --- task #9: one path authority — the producer/consumer seam, end to end --------------

def test_envelope_written_through_the_tool_is_the_one_the_gate_reads(tmp_path):
    """The whole seam in one breath (D-0148): the judge lands its envelope via
    `maintainability_envelope_check.py --write` — from a SUBDIRECTORY, the shape
    that used to make hand-built paths diverge — and the armed gate, which
    resolves the SAME substrate verb, finds the justified disposition and
    allows. Before this, producer and consumer each owned a copy of the path
    string; a split meant the gate blocked on an envelope that existed."""
    import sys
    proj = _proj(tmp_path, arm="block")            # breaching: 7 params > 4
    sub = proj / "app"
    sub.mkdir()
    body = (
        "maintainability-envelope: source=close count=1 armed=true\n\n"
        "## M-1 — param-count 7 > 4 @ app.py:1:big (disposition: justified)\n"
        "standard: coding-standards.md — param-count <= 4\n"
        "reason: justified for the seam test\n"
        "floor: none\n")
    tool = os.path.join(guardkit.BUILD_ROOT, "tools", "maintainability_envelope_check.py")
    wrote = subprocess.run([sys.executable, tool, "--write", "--root", str(sub)],
                           input=body, capture_output=True, text=True)
    assert wrote.returncode == 0, wrote.stdout + wrote.stderr
    landed = json.loads(wrote.stdout)["path"]
    assert landed == os.path.join(str(proj), ".friday", "maintainability-envelope.md")
    out = _run(guardkit.BUILD_ROOT, proj)
    assert not out.stdout.strip(), out.stdout      # dispositioned → the armed gate allows
