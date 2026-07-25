"""Guard #4 — foundation gate (Stop, BLOCK tier; TECHNICAL_SOW_REBUILD FR-55
guard #4, restating K0 stranger-proof). Checker verdict matrix (tools/
foundation_check.py) plus the frozen 5-test hook pattern (AC-13/AC-14) and
the AC-15 stranger read.

Positive control: state: build-in-progress with a tsow: file that does not
exist → Stop blocked. Fail-open controls: same seeded lie with
tools/foundation_check.py deleted / crashing / timing out / emitting an
invalid-empty verdict → ALLOWED.
"""
import json
import os
import sys

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import foundation_check as fc  # noqa: E402

GOOD_CLAIMS = "<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: python3\n<!-- FRIDAY-CLAIMS:END -->"


def _claude_md(*, state="build-in-progress", tsow="docs/TECHNICAL_SOW.md",
               claims=GOOD_CLAIMS):
    state_block = "<!-- FRIDAY-STATE:BEGIN -->\n"
    if state is not None:
        state_block += f"state: {state}\n"
    if tsow is not None:
        state_block += f"tsow: {tsow}\n"
    state_block += "<!-- FRIDAY-STATE:END -->\n"
    return f"# proj\n\n{claims}\n\n{state_block}"


def _proj(tmp_path, *, claude_md_text, with_tsow=True):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    if with_tsow:
        (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text(claude_md_text, encoding="utf-8")
    return root


def _stop(proj):
    return {"hook_event_name": "Stop", "cwd": str(proj)}


# --- checker verdict matrix -----------------------------------------------------

def test_no_claude_md_is_valid_pass(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    assert fc.check(str(root))["verdict"] == "valid-pass"


def test_no_state_block_is_valid_pass(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "CLAUDE.md").write_text(f"# proj\n\n{GOOD_CLAIMS}\n", encoding="utf-8")
    assert fc.check(str(root))["verdict"] == "valid-pass"


def test_missing_tsow_file_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, claude_md_text=_claude_md(), with_tsow=False)
    res = fc.check(str(proj))
    assert res["verdict"] == "valid-fail"
    assert any("does not exist" in p for p in res["problems"])


def test_malformed_claims_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, claude_md_text=_claude_md(claims="<!-- FRIDAY-CLAIMS:BEGIN -->\n"
                                                            "<!-- FRIDAY-CLAIMS:END -->"))
    res = fc.check(str(proj))
    assert res["verdict"] == "valid-fail"
    assert any("well-formed" in p for p in res["problems"])


def test_all_good_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, claude_md_text=_claude_md())
    assert fc.check(str(proj))["verdict"] == "valid-pass"


# --- the hook: 5-test blocking pattern ------------------------------------------

def test_positive_control_broken_foundation_blocks_stop(tmp_path):
    proj = _proj(tmp_path, claude_md_text=_claude_md(), with_tsow=False)
    p = run_hook(BUILD_ROOT, "foundation_gate.py", _stop(proj))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in out["reason"], (part, out["reason"])


def test_fail_open_all_four_checker_conditions(tmp_path):
    proj = _proj(tmp_path, claude_md_text=_claude_md(), with_tsow=False)
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/foundation_check.py", mode)
        p = run_hook(pr, "foundation_gate.py", _stop(proj),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)


def test_sound_foundation_is_allowed(tmp_path):
    proj = _proj(tmp_path, claude_md_text=_claude_md())
    p = run_hook(BUILD_ROOT, "foundation_gate.py", _stop(proj))
    assert p.stdout.strip() == ""


def test_non_build_in_progress_state_is_untouched(tmp_path):
    proj = _proj(tmp_path, claude_md_text=_claude_md(state="tsow-approved"), with_tsow=False)
    p = run_hook(BUILD_ROOT, "foundation_gate.py", _stop(proj))
    assert p.stdout.strip() == ""


def test_no_claude_md_is_a_cheap_no_op(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    p = run_hook(BUILD_ROOT, "foundation_gate.py", _stop(root))
    assert p.stdout.strip() == ""
