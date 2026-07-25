"""Guard #21 — config-change journaling (ConfigChange, SILENT tier;
TECHNICAL_SOW_REBUILD FR-57 guard #21). SILENT guards journal only — a test
asserts the journal line lands AND stdout stays empty.
"""
from guardkit import BUILD_ROOT, run_hook


def _proj(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    return root


def _journal_text(root):
    p = root / ".friday" / "journal.jsonl"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def test_config_change_with_identifying_fields_is_journaled(tmp_path):
    proj = _proj(tmp_path)
    event = {"hook_event_name": "ConfigChange", "cwd": str(proj),
             "source": "settings.json", "path": ".claude/settings.json"}
    p = run_hook(BUILD_ROOT, "config_change_journal.py", event)
    assert p.stdout.strip() == ""
    journal = _journal_text(proj)
    assert "config-change" in journal
    assert "settings.json" in journal


def test_config_change_with_no_identifying_fields_still_journals(tmp_path):
    proj = _proj(tmp_path)
    event = {"hook_event_name": "ConfigChange", "cwd": str(proj)}
    p = run_hook(BUILD_ROOT, "config_change_journal.py", event)
    assert p.stdout.strip() == ""
    journal = _journal_text(proj)
    assert "config-change" in journal


def test_non_friday_project_is_untouched(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    event = {"hook_event_name": "ConfigChange", "cwd": str(root)}
    p = run_hook(BUILD_ROOT, "config_change_journal.py", event)
    assert p.stdout.strip() == ""
    assert not (root / ".friday" / "journal.jsonl").exists()
