"""Guard #2 — spec-write gate (PostToolUse Write|Edit|MultiEdit, BLOCK tier;
TECHNICAL_SOW_REBUILD FR-55 guard #2, D-0018 event mapping). No new
checker — tools/doc_gate.py IS the checker, dispatched by path: `docs/
TECHNICAL_SOW*.md` → --kind spec; `docs/increments/*.md` → --kind increment
--parent <wroot>/docs/TECHNICAL_SOW.md. Other paths are untouched.

Positive control: a just-written TSOW missing its `provenance:` line (the
seeded lie doc_gate's spec kind exists to catch) → PostToolUse block. Fail-
open controls: same seeded lie with tools/doc_gate.py deleted / crashing /
timing out / emitting an invalid-empty verdict → ALLOWED.
"""
import json

from guardkit import BUILD_ROOT, FAIL_OPEN_MODES, broken_plugin, run_hook

GOOD_SPEC = """# TSOW — testproj

provenance: born-from-discovery

## Requirements
- **FR-1** The thing works.
"""

BAD_SPEC = GOOD_SPEC.replace("provenance: born-from-discovery\n", "")

GOOD_INCREMENT = """# INC-1

## Requirements
- **FR-1.1** A slice of the thing.
"""

PARENT_WITH_POINTER = GOOD_SPEC + "\n## Increments\n- docs/increments/INC-1.md\n"


def _proj(tmp_path, *, tsow_text=GOOD_SPEC, friday_marker=True):
    root = tmp_path / "proj"
    (root / "docs" / "increments").mkdir(parents=True)
    if tsow_text is not None:
        (root / "docs" / "TECHNICAL_SOW.md").write_text(tsow_text, encoding="utf-8")
    if friday_marker:
        (root / "CLAUDE.md").write_text(
            "# proj\n\n<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: python3\n"
            "<!-- FRIDAY-CLAIMS:END -->\n", encoding="utf-8")
    return root


def _event(root, path, tool_name="Write"):
    return {"hook_event_name": "PostToolUse", "tool_name": tool_name,
            "cwd": str(root), "tool_input": {"file_path": str(path)}}


def test_positive_control_spec_missing_provenance_is_blocked(tmp_path):
    proj = _proj(tmp_path, tsow_text=BAD_SPEC)
    p = run_hook(BUILD_ROOT, "spec_write_guard.py",
                 _event(proj, proj / "docs" / "TECHNICAL_SOW.md"))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"
    for part in ("BLOCKED:", "Why:", "What to do next:", "Override path:"):
        assert part in out["reason"], (part, out["reason"])


def test_fail_open_all_four_checker_conditions(tmp_path):
    proj = _proj(tmp_path, tsow_text=BAD_SPEC)
    for mode in FAIL_OPEN_MODES:
        pr = broken_plugin(tmp_path, "tools/doc_gate.py", mode)
        p = run_hook(pr, "spec_write_guard.py",
                     _event(proj, proj / "docs" / "TECHNICAL_SOW.md"),
                     env={"FRIDAY_GUARD_TIMEOUT_S": "1"})
        assert p.stdout.strip() == "", (mode, p.stdout)


def test_valid_spec_write_is_untouched(tmp_path):
    proj = _proj(tmp_path, tsow_text=GOOD_SPEC)
    p = run_hook(BUILD_ROOT, "spec_write_guard.py",
                 _event(proj, proj / "docs" / "TECHNICAL_SOW.md"))
    assert p.stdout.strip() == ""


def test_orphan_increment_is_blocked(tmp_path):
    proj = _proj(tmp_path, tsow_text=GOOD_SPEC)  # no ## Increments pointer
    (proj / "docs" / "increments" / "INC-1.md").write_text(GOOD_INCREMENT, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "spec_write_guard.py",
                 _event(proj, proj / "docs" / "increments" / "INC-1.md"))
    out = json.loads(p.stdout)
    assert out["decision"] == "block"


def test_pointer_linked_increment_is_untouched(tmp_path):
    proj = _proj(tmp_path, tsow_text=PARENT_WITH_POINTER)
    (proj / "docs" / "increments" / "INC-1.md").write_text(GOOD_INCREMENT, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "spec_write_guard.py",
                 _event(proj, proj / "docs" / "increments" / "INC-1.md"))
    assert p.stdout.strip() == ""


def test_non_spec_path_is_untouched(tmp_path):
    proj = _proj(tmp_path, tsow_text=GOOD_SPEC)
    (proj / "docs" / "notes.md").write_text("whatever", encoding="utf-8")
    p = run_hook(BUILD_ROOT, "spec_write_guard.py",
                 _event(proj, proj / "docs" / "notes.md"))
    assert p.stdout.strip() == ""


def test_non_friday_project_increment_is_untouched(tmp_path):
    # No docs/TECHNICAL_SOW.md and no CLAUDE.md FRIDAY markers at all — the
    # increments path alone must not count as a friday project (is_friday_project
    # is a real dependency, not re-derived by this guard).
    bare = tmp_path / "bare"
    (bare / "docs" / "increments").mkdir(parents=True)
    bad_increment = GOOD_INCREMENT.replace("- **FR-1.1**", "- **FR-1**")  # undotted lie
    (bare / "docs" / "increments" / "INC-1.md").write_text(bad_increment, encoding="utf-8")
    p = run_hook(BUILD_ROOT, "spec_write_guard.py",
                 _event(bare, bare / "docs" / "increments" / "INC-1.md"))
    assert p.stdout.strip() == ""
