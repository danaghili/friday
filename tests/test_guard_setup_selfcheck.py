"""Guard #19 — install self-check (Setup, SILENT tier; TECHNICAL_SOW_REBUILD
FR-57 guard #19). A doc-only harness event (probe-hook-events.md) — SILENT
guards journal only; a test asserts the journal line lands AND stdout stays
empty in every case.
"""
import json
import os
import shutil

from guardkit import BUILD_ROOT, run_hook


def _proj(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    return root


def _journal_text(root):
    p = root / ".friday" / "journal.jsonl"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _event(root):
    return {"hook_event_name": "Setup", "cwd": str(root)}


def test_healthy_install_journals_ok_true(tmp_path):
    proj = _proj(tmp_path)
    p = run_hook(BUILD_ROOT, "setup_selfcheck.py", _event(proj))
    assert p.stdout.strip() == ""
    journal = _journal_text(proj)
    assert "install-self-check" in journal
    assert '"ok":true' in journal.replace(" ", "")


def test_broken_hooks_json_journals_ok_false(tmp_path):
    proj = _proj(tmp_path)
    pr = tmp_path / "plugin-broken"
    shutil.copytree(os.path.join(BUILD_ROOT, "hooks"), pr / "hooks",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(BUILD_ROOT, "tools"), pr / "tools",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (pr / "hooks" / "hooks.json").write_text("not json {{{", encoding="utf-8")
    p = run_hook(str(pr), "setup_selfcheck.py", _event(proj))
    assert p.stdout.strip() == ""
    journal = _journal_text(proj)
    assert "install-self-check" in journal
    assert '"ok":false' in journal.replace(" ", "")


def test_missing_referenced_hook_file_journals_ok_false(tmp_path):
    proj = _proj(tmp_path)
    pr = tmp_path / "plugin-missing-hook"
    shutil.copytree(os.path.join(BUILD_ROOT, "hooks"), pr / "hooks",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(BUILD_ROOT, "tools"), pr / "tools",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (pr / "hooks" / "session_lifecycle.py").unlink()
    p = run_hook(str(pr), "setup_selfcheck.py", _event(proj))
    assert p.stdout.strip() == ""
    journal = _journal_text(proj)
    assert "install-self-check" in journal
    assert "session_lifecycle.py" in journal
    assert '"ok":false' in journal.replace(" ", "")


def test_non_friday_project_is_untouched(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    p = run_hook(BUILD_ROOT, "setup_selfcheck.py", _event(root))
    assert p.stdout.strip() == ""
    assert not (root / ".friday" / "journal.jsonl").exists()
