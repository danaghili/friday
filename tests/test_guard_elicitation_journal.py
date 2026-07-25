"""Guard #16 — elicitation journaling (Elicitation + PermissionDenied,
SILENT tier; TECHNICAL_SOW_REBUILD FR-57 guard #16). SILENT guards journal
only — a test asserts the journal line lands AND stdout stays empty.
"""
import json

from guardkit import BUILD_ROOT, run_hook


def _proj(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    return root


def _journal_text(root):
    p = root / ".friday" / "journal.jsonl"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def test_elicitation_question_is_journaled_and_stdout_stays_empty(tmp_path):
    proj = _proj(tmp_path)
    event = {"hook_event_name": "Elicitation", "cwd": str(proj),
             "tool_input": {"questions": [{"question": "Which store?",
                                          "header": "Store", "options": []}]}}
    p = run_hook(BUILD_ROOT, "elicitation_journal.py", event)
    assert p.stdout.strip() == ""
    journal = _journal_text(proj)
    assert "elicitation" in journal
    assert "Which store?" in journal


def test_permission_denied_is_also_journaled(tmp_path):
    proj = _proj(tmp_path)
    event = {"hook_event_name": "PermissionDenied", "cwd": str(proj),
             "tool_name": "Bash", "reason": "user declined"}
    p = run_hook(BUILD_ROOT, "elicitation_journal.py", event)
    assert p.stdout.strip() == ""
    journal = _journal_text(proj)
    assert "elicitation" in journal
    assert "PermissionDenied" in journal
    assert "Bash" in journal


def test_non_friday_project_is_untouched(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    event = {"hook_event_name": "Elicitation", "cwd": str(root)}
    p = run_hook(BUILD_ROOT, "elicitation_journal.py", event)
    assert p.stdout.strip() == ""
    assert not (root / ".friday" / "journal.jsonl").exists()
