"""Guard #9 — document-consumption gate (PreToolUse Read, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55/FR-64 guard #9, D-0018). No new checker —
tools/doc_gate.py IS the checker, dispatched by path. Spec kind ARMED
since D-0023 (the PM provenance amendment landed): reading a spec that
fails its gate blocks; a provenance-carrying valid spec reads untouched.

Positive control: reading a malformed increment (undotted ID) → PreToolUse
block. Fail-open controls: same seeded lie with tools/doc_gate.py deleted /
crashing / timing out / emitting an invalid-empty verdict → ALLOWED.
"""
import json

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

GOOD_TSOW = """# TSOW — testproj

provenance: born-from-discovery

## Requirements
- **FR-1** The thing works.

## Increments
- docs/increments/INC-1.md
"""

GOOD_INCREMENT = """# INC-1

## Requirements
- **FR-1.1** A slice of the thing.
"""
BAD_INCREMENT = GOOD_INCREMENT.replace("- **FR-1.1**", "- **FR-1**")  # undotted lie

GOOD_FINDINGS = """findings-brief: source=harden count=0

## Checked
Nothing turned up.
"""
BAD_FINDINGS = "findings-brief: source=harden count=1\n\nno findings here\n"

GOOD_INTAKE = """intake-brief: client=Acme date=2026-07-14

## Formal — for sign-off
goals: ship it
scope: the thing
exclusions: nothing else
budget: 10k
timeline: soon
approver: Dan
data-sovereignty: local
hosting-sla: us
payment-ip-exit: net30
client-tier: small

## Informal — workroom notes
friendly client.

## Glossary
glossary: none — no client-specific terms arose
"""
BAD_INTAKE = "intake-brief: client= date=bad\n"


def _proj(tmp_path):
    root = tmp_path / "proj"
    (root / "docs" / "increments").mkdir(parents=True)
    (root / "docs" / "reviews").mkdir(parents=True)
    (root / "docs" / "briefs").mkdir(parents=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text(GOOD_TSOW, encoding="utf-8")
    return root


def _event(root, path):
    return {"hook_event_name": "PreToolUse", "tool_name": "Read", "cwd": str(root),
            "tool_input": {"file_path": str(path)}}


def test_positive_control_malformed_increment_is_blocked(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "increments" / "INC-1.md").write_text(BAD_INCREMENT, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py",
                 _event(proj, proj / "docs" / "increments" / "INC-1.md"))
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in reason, (part, reason)


def test_fail_open_all_four_checker_conditions(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "increments" / "INC-1.md").write_text(BAD_INCREMENT, encoding="utf-8")
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/doc_gate.py", mode)
        p = run_hook(pr, "doc_consumption_guard.py",
                     _event(proj, proj / "docs" / "increments" / "INC-1.md"),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)


def test_valid_increment_read_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "increments" / "INC-1.md").write_text(GOOD_INCREMENT, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py",
                 _event(proj, proj / "docs" / "increments" / "INC-1.md"))
    assert p.stdout.strip() == ""


def test_malformed_findings_brief_is_blocked(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "reviews" / "findings-harden.md").write_text(BAD_FINDINGS, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py",
                 _event(proj, proj / "docs" / "reviews" / "findings-harden.md"))
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_valid_findings_brief_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "reviews" / "findings-harden.md").write_text(GOOD_FINDINGS, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py",
                 _event(proj, proj / "docs" / "reviews" / "findings-harden.md"))
    assert p.stdout.strip() == ""


def test_malformed_intake_brief_is_blocked(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "briefs" / "intake-acme.md").write_text(BAD_INTAKE, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py",
                 _event(proj, proj / "docs" / "briefs" / "intake-acme.md"))
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_valid_intake_brief_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "briefs" / "intake-acme.md").write_text(GOOD_INTAKE, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py",
                 _event(proj, proj / "docs" / "briefs" / "intake-acme.md"))
    assert p.stdout.strip() == ""


def test_malformed_spec_read_is_blocked_since_d0023(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "TECHNICAL_SOW.md").write_text(
        "# TSOW\n\nno provenance, no requirement IDs\n", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py",
                 _event(proj, proj / "docs" / "TECHNICAL_SOW.md"))
    out = json.loads(p.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_valid_spec_read_is_untouched(tmp_path):
    proj = _proj(tmp_path)  # GOOD_TSOW carries provenance + one declared FR
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py",
                 _event(proj, proj / "docs" / "TECHNICAL_SOW.md"))
    assert p.stdout.strip() == ""


def test_non_matching_path_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    (proj / "docs" / "notes.md").write_text("whatever", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py",
                 _event(proj, proj / "docs" / "notes.md"))
    assert p.stdout.strip() == ""


def test_event_without_a_path_is_untouched(tmp_path):
    proj = _proj(tmp_path)
    event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
             "cwd": str(proj), "tool_input": {}}
    p = run_hook(BUILD_ROOT, "doc_consumption_guard.py", event)
    assert p.stdout.strip() == ""
