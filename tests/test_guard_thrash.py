"""Guard #17 — thrash detector (PostToolUse, WARN tier; TECHNICAL_SOW_REBUILD
FR-56 guard #17). No external checker — the journal itself is the evidence.
Each qualifying edit journals a `file-edited` event; ≥5 for the SAME path
within the journal's last 200 lines with no `decision-captured` after the
earliest of them → warn, never blocks.
"""
import json

from guardkit import BUILD_ROOT, run_hook


def _proj(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    return root


def _seed_journal(root, lines):
    (root / ".friday").mkdir(exist_ok=True)
    with open(root / ".friday" / "journal.jsonl", "w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line) + "\n")


def _edit_line(path, ts):
    return {"ts": ts, "feature": "-", "phase": "session", "event": "file-edited",
            "by": "tool", "data": {"path": path}}


def _decision_line(ts):
    return {"ts": ts, "feature": "-", "phase": "session", "event": "decision-captured",
            "by": "lead", "data": {"id": "D-0001"}}


def _event(root, path):
    return {"hook_event_name": "PostToolUse", "tool_name": "Write", "cwd": str(root),
            "tool_input": {"file_path": str(path)}}


def test_five_edits_without_a_decision_warns(tmp_path):
    proj = _proj(tmp_path)
    lines = [_edit_line("tools/foo.py", f"2026-07-14T00:0{i}:00Z") for i in range(4)]
    _seed_journal(proj, lines)  # hook's own write makes the 5th
    p = run_hook(BUILD_ROOT, "thrash_detector.py", _event(proj, proj / "tools" / "foo.py"))
    out = json.loads(p.stdout)
    assert "churned" in out["systemMessage"]
    assert "tools/foo.py" in out["systemMessage"]
    assert "decision" not in out
    assert "hookSpecificOutput" not in out


def test_decision_after_the_first_edit_is_silent(tmp_path):
    proj = _proj(tmp_path)
    lines = [_edit_line("tools/foo.py", "2026-07-14T00:00:00Z"),
             _decision_line("2026-07-14T00:00:30Z"),
             _edit_line("tools/foo.py", "2026-07-14T00:01:00Z"),
             _edit_line("tools/foo.py", "2026-07-14T00:02:00Z"),
             _edit_line("tools/foo.py", "2026-07-14T00:03:00Z")]
    _seed_journal(proj, lines)  # + hook's own write = 5 edits total
    p = run_hook(BUILD_ROOT, "thrash_detector.py", _event(proj, proj / "tools" / "foo.py"))
    assert p.stdout.strip() == ""


def test_empty_journal_is_silent(tmp_path):
    proj = _proj(tmp_path)
    p = run_hook(BUILD_ROOT, "thrash_detector.py", _event(proj, proj / "tools" / "foo.py"))
    assert p.stdout.strip() == ""


def test_edits_on_a_different_path_dont_count(tmp_path):
    proj = _proj(tmp_path)
    lines = [_edit_line("tools/other.py", f"2026-07-14T00:0{i}:00Z") for i in range(6)]
    _seed_journal(proj, lines)
    p = run_hook(BUILD_ROOT, "thrash_detector.py", _event(proj, proj / "tools" / "foo.py"))
    assert p.stdout.strip() == ""


def test_non_friday_project_is_untouched(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    p = run_hook(BUILD_ROOT, "thrash_detector.py", _event(root, root / "x.py"))
    assert p.stdout.strip() == ""
    assert not (root / ".friday" / "journal.jsonl").exists()
