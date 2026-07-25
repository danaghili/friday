"""INC-001 FR-1.5/FR-1.6 capture doors: spawn-prompt persistence rides the
spawn-telemetry dispatch moment; mission/orientation notes ride the
compaction_note CLI; both key the drawer by the newest session lock when no
--session-id is given. Contract: docs/contracts/compaction-package.md.
"""
import os
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import friday_substrate as fs  # noqa: E402

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture()
def proj(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "CLAUDE.md").write_text(
        "# proj\n\n<!-- FRIDAY-STATE:BEGIN -->\nstate: build-in-progress\n"
        "tsow: docs/TECHNICAL_SOW.md\n<!-- FRIDAY-STATE:END -->\n",
        encoding="utf-8")
    return tmp_path


def _run(tool, *args, stdin=None, cwd=None):
    return subprocess.run(
        ["python3", os.path.join(BUILD_ROOT, "tools", tool), *args],
        input=stdin, capture_output=True, text=True, cwd=cwd)


# --- current_session_id ---------------------------------------------------------------

def test_current_session_id_newest_lock_wins(proj):
    root = str(proj)
    fs.write_session_lock(root, "old-sess", {"role": "lead"})
    time.sleep(0.05)
    fs.write_session_lock(root, "new-sess", {"role": "lead"})
    assert fs.current_session_id(root) == "new-sess"


def test_current_session_id_unkeyed_without_locks(proj):
    assert fs.current_session_id(str(proj)) == fs.COMPACTION_UNKEYED_SESSION


# --- spawn-prompt persistence (FR-1.5) -------------------------------------------------

def test_spawn_with_prompt_file_persists_mission(proj, tmp_path):
    fs.write_session_lock(str(proj), "sess-x", {"role": "lead"})
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("You are the tester. Full spawn context here.\n", encoding="utf-8")
    p = _run("spawn_telemetry.py", "--emit", "spawn", "--agent", "friday-tester",
             "--phase", "build:test", "--cwd", str(proj),
             "--prompt-file", str(prompt))
    assert p.returncode == 0, p.stderr
    pkg = fs.compaction_read_package(str(proj), session_id="sess-x",
                                     agent="friday-tester")
    assert pkg["mission"].startswith("You are the tester.")


def test_prompt_file_rejected_off_spawn(proj, tmp_path):
    prompt = tmp_path / "p.txt"
    prompt.write_text("x\n", encoding="utf-8")
    p = _run("spawn_telemetry.py", "--emit", "done", "--agent", "a",
             "--phase", "x:y", "--cwd", str(proj), "--prompt-file", str(prompt))
    assert p.returncode == 2 and "spawn-time" in p.stderr


# --- compaction_note CLI (FR-1.5 orchestrator mission / FR-1.6 orientation) -----------

def test_note_cli_writes_orientation_from_stdin(proj):
    fs.write_session_lock(str(proj), "sess-y", {"role": "lead"})
    p = _run("compaction_note.py", "--layer", "orientation", "--agent",
             "friday-lead", "--cwd", str(proj), stdin="learned: the API is v2\n")
    assert p.returncode == 0, p.stderr
    pkg = fs.compaction_read_package(str(proj), session_id="sess-y",
                                     agent="friday-lead")
    assert pkg["orientation"] == "learned: the API is v2\n"


def test_note_cli_refuses_unknown_layer_and_empty_text(proj):
    p = _run("compaction_note.py", "--layer", "diary", "--agent", "a",
             "--cwd", str(proj), stdin="x\n")
    assert p.returncode == 2
    p = _run("compaction_note.py", "--layer", "mission", "--agent", "a",
             "--cwd", str(proj), stdin="   \n")
    assert p.returncode == 2


def test_note_cli_refuses_non_friday_project(tmp_path):
    p = _run("compaction_note.py", "--layer", "mission", "--agent", "a",
             "--cwd", str(tmp_path), stdin="x\n")
    assert p.returncode == 2 and "not a friday project" in p.stderr
