"""Guard #3 — oracle-edit gate (PreToolUse, BLOCK tier; TECHNICAL_SOW_REBUILD
FR-55 guard #3, D-0018). Checker verdict matrix (tools/oracle_edit_check.py)
plus the frozen 5-test hook pattern (AC-13/AC-14) and the AC-15 stranger read.

Armed ⇔ the oracle's mapped coverage ledger exists and holds ≥1
`disposition:` line (closure underway). Positive control: armed +
DECISIONS.md silent on the oracle's path → PreToolUse deny. Fail-open
controls: same armed lie with tools/oracle_edit_check.py deleted / crashing
/ timing out / emitting an invalid-empty verdict → ALLOWED.
"""
import json
import os
import sys

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import oracle_edit_check as oec  # noqa: E402

ARMED_LEDGER = ("# coverage\n\n<!-- FRIDAY-DISPOSITIONS:BEGIN -->\n"
                "disposition: FR-1 implemented — src/x.py:9\n"
                "<!-- FRIDAY-DISPOSITIONS:END -->\n")
EMPTY_LEDGER = "# coverage\n\n<!-- FRIDAY-DISPOSITIONS:BEGIN -->\n<!-- FRIDAY-DISPOSITIONS:END -->\n"


def _proj(tmp_path, *, ledger=None, decisions_text="# Decisions — proj\n"):
    root = tmp_path / "proj"
    (root / "docs" / "reviews").mkdir(parents=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    (root / "docs" / "DECISIONS.md").write_text(decisions_text, encoding="utf-8")
    if ledger is not None:
        (root / "docs" / "reviews" / "coverage.md").write_text(ledger, encoding="utf-8")
    return root


def _event(root, path):
    return {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": str(root),
            "tool_input": {"file_path": str(path)}}


# --- checker verdict matrix -----------------------------------------------------

def test_ledger_absent_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, ledger=None)
    res = oec.check(str(proj / "docs" / "TECHNICAL_SOW.md"), str(proj))
    assert res["verdict"] == "valid-pass"


def test_ledger_empty_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, ledger=EMPTY_LEDGER)
    res = oec.check(str(proj / "docs" / "TECHNICAL_SOW.md"), str(proj))
    assert res["verdict"] == "valid-pass"


def test_armed_undocumented_is_valid_fail(tmp_path):
    proj = _proj(tmp_path, ledger=ARMED_LEDGER)
    res = oec.check(str(proj / "docs" / "TECHNICAL_SOW.md"), str(proj))
    assert res["verdict"] == "valid-fail"


def test_armed_documented_is_valid_pass(tmp_path):
    proj = _proj(tmp_path, ledger=ARMED_LEDGER,
                 decisions_text="# Decisions\n\n## D-0001 — PM amends the oracle\n"
                                "override-grant: docs/TECHNICAL_SOW.md\n")
    res = oec.check(str(proj / "docs" / "TECHNICAL_SOW.md"), str(proj))
    assert res["verdict"] == "valid-pass"


def test_armed_bare_mention_does_not_unlock(tmp_path):
    # A3 (harden): a mention that does NOT grant — even one that REJECTS the edit —
    # must not unlock the frozen oracle (the closed substring hole).
    proj = _proj(tmp_path, ledger=ARMED_LEDGER,
                 decisions_text="# Decisions\n\n## D-0001 — considered, rejected\n"
                                "We discussed editing docs/TECHNICAL_SOW.md and REJECTED it.\n")
    res = oec.check(str(proj / "docs" / "TECHNICAL_SOW.md"), str(proj))
    assert res["verdict"] == "valid-fail"


def test_unknown_oracle_is_no_verdict(tmp_path):
    proj = _proj(tmp_path)
    res = oec.check(str(proj / "docs" / "TECHNICAL_SOW_WEIRD.md"), str(proj))
    assert res["verdict"] == "no-verdict"


# --- the hook: 5-test blocking pattern ------------------------------------------

def test_positive_control_armed_undocumented_edit_is_denied(tmp_path):
    proj = _proj(tmp_path, ledger=ARMED_LEDGER)
    p = run_hook(BUILD_ROOT, "oracle_edit_guard.py",
                 _event(proj, proj / "docs" / "TECHNICAL_SOW.md"))
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in reason, (part, reason)


def test_fail_open_all_four_checker_conditions(tmp_path):
    proj = _proj(tmp_path, ledger=ARMED_LEDGER)
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/oracle_edit_check.py", mode)
        p = run_hook(pr, "oracle_edit_guard.py",
                     _event(proj, proj / "docs" / "TECHNICAL_SOW.md"),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)


def test_decision_record_unlocks_the_edit(tmp_path):
    proj = _proj(tmp_path, ledger=ARMED_LEDGER,
                 decisions_text="# Decisions\n\n## D-0001 — PM amends the oracle\n"
                                "override-grant: docs/TECHNICAL_SOW.md\n")
    p = run_hook(BUILD_ROOT, "oracle_edit_guard.py",
                 _event(proj, proj / "docs" / "TECHNICAL_SOW.md"))
    assert p.stdout.strip() == ""


def test_non_oracle_path_is_untouched(tmp_path):
    proj = _proj(tmp_path, ledger=ARMED_LEDGER)
    p = run_hook(BUILD_ROOT, "oracle_edit_guard.py",
                 _event(proj, proj / "docs" / "notes.md"))
    assert p.stdout.strip() == ""


def test_event_without_a_path_is_untouched(tmp_path):
    proj = _proj(tmp_path, ledger=ARMED_LEDGER)
    event = {"hook_event_name": "PreToolUse", "tool_name": "Edit",
             "cwd": str(proj), "tool_input": {}}
    p = run_hook(BUILD_ROOT, "oracle_edit_guard.py", event)
    assert p.stdout.strip() == ""
