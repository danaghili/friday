"""Guard #5 — build-past-open-risks (PostToolUse, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55 guard #5, D-0018). Checker verdict matrix
(tools/open_risks_check.py) plus the frozen 5-test hook pattern (AC-13/
AC-14) and the AC-15 stranger read.

Positive control: build-in-progress, TSOW risk register holds an open
("verify") row with no matching token in DECISIONS.md → PostToolUse block
on the CLAUDE.md write. Fail-open controls: same seeded lie with
tools/open_risks_check.py deleted / crashing / timing out / emitting an
invalid-empty verdict → ALLOWED.
"""
import json
import os
import sys

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import open_risks_check as orc  # noqa: E402

TSOW_WITH_OPEN_ROW = """# tsow

### Stack-risk register

| Element | Risk | Settles it | Verdict |
| --- | --- | --- | --- |
| `graphifyy` (real tool) | Cost unmeasured | Spike before commit | verify |
| Committed-test detection | Needs a definition | Prototype it | settled — probe-guard7.md |
"""

TSOW_ALL_SETTLED = TSOW_WITH_OPEN_ROW.replace("| verify |", "| settled — spike-2026.md |")

TSOW_NO_REGISTER = "# tsow\n\nNo risk section here.\n"


def _claude_md(*, state="build-in-progress", tsow="docs/TECHNICAL_SOW.md"):
    return (f"# proj\n\n<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: path:python3\n"
            f"<!-- FRIDAY-CLAIMS:END -->\n\n<!-- FRIDAY-STATE:BEGIN -->\n"
            f"state: {state}\ntsow: {tsow}\n<!-- FRIDAY-STATE:END -->\n")


def _proj(tmp_path, *, tsow_text=TSOW_WITH_OPEN_ROW, decisions_text="# Decisions\n",
         state="build-in-progress"):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text(tsow_text, encoding="utf-8")
    (root / "docs" / "DECISIONS.md").write_text(decisions_text, encoding="utf-8")
    (root / "CLAUDE.md").write_text(_claude_md(state=state), encoding="utf-8")
    return root


def _event(root, path=None):
    return {"hook_event_name": "PostToolUse", "tool_name": "Write", "cwd": str(root),
            "tool_input": {"file_path": str(path or (root / "CLAUDE.md"))}}


# --- checker verdict matrix -----------------------------------------------------

def test_open_row_undocumented_is_valid_fail(tmp_path):
    proj = _proj(tmp_path)
    res = orc.check(str(proj))
    assert res["verdict"] == "valid-fail"
    assert any("graphifyy" in r for r in res["open_rows"])


def test_open_row_documented_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, decisions_text="# Decisions\n\n## D-0001 — proceed on graphifyy\n"
                                          "override-grant: graphifyy\n")
    assert orc.check(str(proj))["verdict"] == "valid-pass"


def test_open_row_bare_mention_does_not_pass(tmp_path):
    # A3 (harden): a mention that REJECTS the tool must not excuse the open risk row.
    proj = _proj(tmp_path, decisions_text="# Decisions\n\n## D-0001 — rejected\n"
                                          "we evaluated graphifyy and REJECTED it.\n")
    assert orc.check(str(proj))["verdict"] == "valid-fail"


def test_all_settled_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, tsow_text=TSOW_ALL_SETTLED)
    assert orc.check(str(proj))["verdict"] == "valid-pass"


def test_not_build_in_progress_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, state="tsow-approved")
    assert orc.check(str(proj))["verdict"] == "valid-pass"


def test_no_risk_register_section_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, tsow_text=TSOW_NO_REGISTER)
    assert orc.check(str(proj))["verdict"] == "valid-pass"


# --- the hook: 5-test blocking pattern ------------------------------------------

def test_positive_control_open_risk_blocks_claude_md_write(tmp_path):
    proj = _proj(tmp_path)
    p = run_hook(BUILD_ROOT, "open_risks_guard.py", _event(proj))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in out["reason"], (part, out["reason"])


def test_fail_open_all_four_checker_conditions(tmp_path):
    proj = _proj(tmp_path)
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/open_risks_check.py", mode)
        p = run_hook(pr, "open_risks_guard.py", _event(proj),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)


def test_documented_risk_is_allowed(tmp_path):
    proj = _proj(tmp_path, decisions_text="# Decisions\n\n## D-0001 — proceed on graphifyy\n"
                                          "override-grant: graphifyy\n")
    p = run_hook(BUILD_ROOT, "open_risks_guard.py", _event(proj))
    assert p.stdout.strip() == ""


def test_non_claude_md_write_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "notes.md").write_text("x", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "open_risks_guard.py", _event(proj, proj / "docs" / "notes.md"))
    assert p.stdout.strip() == ""


def test_event_without_a_path_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    event = {"hook_event_name": "PostToolUse", "tool_name": "Write",
             "cwd": str(proj), "tool_input": {}}
    p = run_hook(BUILD_ROOT, "open_risks_guard.py", event)
    assert p.stdout.strip() == ""
