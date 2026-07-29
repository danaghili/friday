"""seam_handoff — write and clear through the single writer (journey audit
NF13 added --clear; hot-path test coverage was worklist item #12/#14).

The brief is the carry-forward a NEXT unit starts from; a stale one is worse
than none (resume would happily resume a finished rebuild from it), so the
clear path is as load-bearing as the write path — and both journal.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import friday_substrate as fs  # noqa: E402
import seam_handoff  # noqa: E402


def _proj(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text(
        "# p\n\n<!-- FRIDAY-STATE:BEGIN -->\nstate: build-in-progress\n"
        "<!-- FRIDAY-STATE:END -->\n", encoding="utf-8")
    return str(root)


def _journal_events(root):
    path = os.path.join(fs.friday_dir(root), "journal.jsonl")
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


def test_write_creates_brief_and_journals(tmp_path):
    root = _proj(tmp_path)
    rc = seam_handoff.main(["--root", root, "--next", "finish unit 2"])
    assert rc == 0
    out = os.path.join(fs.friday_dir(root), "seam-handoff.md")
    assert os.path.isfile(out)
    text = open(out, encoding="utf-8").read()
    assert "finish unit 2" in text and "Generated " in text
    assert any(e.get("data", {}).get("seam") is True for e in _journal_events(root))


def test_clear_removes_brief_and_journals_why(tmp_path):
    root = _proj(tmp_path)
    seam_handoff.main(["--root", root, "--next", "x"])
    rc = seam_handoff.main(["--root", root, "--clear", "--reason", "unit shipped"])
    assert rc == 0
    assert not os.path.isfile(os.path.join(fs.friday_dir(root), "seam-handoff.md"))
    cleared = [e for e in _journal_events(root)
               if e.get("data", {}).get("seam") == "cleared"]
    assert cleared and cleared[-1]["data"].get("reason") == "unit shipped"


def test_clear_with_no_brief_is_a_graceful_noop(tmp_path):
    root = _proj(tmp_path)
    rc = seam_handoff.main(["--root", root, "--clear"])
    assert rc == 0
    # no brief, nothing removed — and no false "cleared" journal event
    assert not any(e.get("data", {}).get("seam") == "cleared"
                   for e in _journal_events(root))


# --- task #14: the untested half — refusal, the brief's substance, the empty case ----

def test_refuses_outside_a_friday_project(tmp_path, capsys):
    root = tmp_path / "bare"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    assert seam_handoff.main(["--root", str(root)]) == 2
    assert "not a friday project" in capsys.readouterr().err


def test_the_brief_carries_decisions_ir_and_working_tree(tmp_path):
    """The substance pins: the brief is decisions + code-map + tree state,
    NEVER session history. Decision index is titles-only (the log keeps the
    why); the code map comes from the generated IR; the dirty tree is quoted
    so the next unit knows what it is standing on."""
    import decisions
    root = _proj(tmp_path)
    decisions.append_entry(root, title="pick sqlite", decision="sqlite it is",
                           why="single writer, zero ops", rejected="postgres")
    gen = os.path.join(root, "docs", "architecture", "generated")
    os.makedirs(gen)
    with open(os.path.join(gen, "architecture-ir.json"), "w") as fh:
        json.dump({"modules": [{"id": "app.main", "loc": 120}],
                   "edges": [], "routes": []}, fh)
    with open(os.path.join(root, "stray.txt"), "w") as fh:
        fh.write("uncommitted work\n")

    assert seam_handoff.main(["--root", root, "--next", "wire the API layer"]) == 0
    brief = open(os.path.join(fs.friday_dir(root), "seam-handoff.md"),
                 encoding="utf-8").read()
    assert "D-0001 — pick sqlite" in brief
    assert "single writer, zero ops" not in brief     # titles only — the log has the why
    assert "1 modules · 0 edges · 0 routes" in brief
    assert "`app.main` (120 loc)" in brief
    assert "stray.txt" in brief                       # working tree at the seam
    assert "## Read list (in order)" in brief


def test_the_brief_survives_an_absent_decisions_log_and_ir(tmp_path):
    """The empty case: a seam forced before any decision or extraction exists
    still produces a valid brief — the read list is the constant spine; the
    optional sections simply don't appear."""
    root = _proj(tmp_path)
    assert seam_handoff.main(["--root", root]) == 0
    brief = open(os.path.join(fs.friday_dir(root), "seam-handoff.md"),
                 encoding="utf-8").read()
    assert "## Read list (in order)" in brief
    assert "## Decision index" not in brief
    assert "## Code map" not in brief
