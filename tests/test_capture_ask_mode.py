"""decisions_append.py --capture-ask — the decision-ask capture moved from the
decision_capture hook into the record owner's own CLI (2026-08-06, D-1084
follow-on: hooks shell out to the logic core, so the parse + compose + append
live on the tool side and the hook stays a subprocess adapter)."""
import json
import os
import subprocess
import sys

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BUILD_ROOT, "tools"))
import decisions  # noqa: E402

ASK = ("[FRIDAY-DECISION] Session store choice\n"
       "decision: which session store the API uses\n"
       "why: survives restarts\nrejected: in-memory dict\n"
       "floor: none\nweight: two-way\n")
ASK_FLOOR = ("[FRIDAY-DECISION] Auth token home\n"
             "decision: where tokens live\nwhy: exposure\nrejected: none\n"
             "floor: auth-security\nweight: two-way\n")


def _run(root, payload):
    return subprocess.run(
        [sys.executable, os.path.join(BUILD_ROOT, "tools", "decisions_append.py"),
         "--capture-ask", "--root", str(root)],
        input=json.dumps(payload), capture_output=True, text=True)


def _init(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs").mkdir()
    subprocess.run(
        [sys.executable, os.path.join(BUILD_ROOT, "tools", "decisions_append.py"),
         "--init", "--project", "t", "--root", str(tmp_path)],
        check=True, capture_output=True)


def test_a_decision_shaped_ask_captures_pm_ratified(tmp_path):
    _init(tmp_path)
    p = _run(tmp_path, {"question": ASK, "answer": "redis",
                        "options": ["redis", "in-memory dict"]})
    out = json.loads(p.stdout)
    assert out["captured"] is True and out["id"].startswith("D-")
    entries = decisions.parse_file(str(tmp_path / "docs" / "DECISIONS.md"))["entries"]
    (e,) = entries
    assert e["channel"] == "pm-ratified"
    assert "redis" in e["decision"]
    assert "options not chosen: in-memory dict" in e["rejected"]


def test_an_ordinary_dialog_is_never_captured(tmp_path):
    _init(tmp_path)
    p = _run(tmp_path, {"question": "Proceed with the merge?", "answer": "yes",
                        "options": ["yes", "no"]})
    out = json.loads(p.stdout)
    assert out["captured"] is False
    entries = decisions.parse_file(str(tmp_path / "docs" / "DECISIONS.md"))["entries"]
    assert entries == []


def test_a_floored_ask_forces_one_way(tmp_path):
    _init(tmp_path)
    p = _run(tmp_path, {"question": ASK_FLOOR, "answer": "server-side vault",
                        "options": []})
    out = json.loads(p.stdout)
    assert out["captured"] is True
    (e,) = decisions.parse_file(str(tmp_path / "docs" / "DECISIONS.md"))["entries"]
    assert e["weight"] == "one-way"
