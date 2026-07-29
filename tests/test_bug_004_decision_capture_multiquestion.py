"""BUG-004 regression: multi-question decision-asks — one DECISIONS.md entry
PER decision-shaped question, each carrying ITS OWN answer.

Facets (docs/BUGS.md BUG-004, one root cause — single-question assumption):
  (a) decision-shaped questions after the first must capture too;
  (b) per-question answer attribution — no mashed answers, no cross-talk
      between one question's entry and another question's options;
  (c) the no-answer fallback names the re-record tool, never the ask mirror
      (the same-event cleanup hook deletes the mirror before anyone reads it).
"""
import json
import os
import subprocess

import pytest

import decisions

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLAIMS = ("<!-- FRIDAY-CLAIMS:BEGIN -->\nstack: path:python3\n"
          "<!-- FRIDAY-CLAIMS:END -->")


@pytest.fixture()
def proj(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "CLAUDE.md").write_text(
        "# proj\n\n" + CLAIMS + "\n\n<!-- FRIDAY-STATE:BEGIN -->\n"
        "state: build-in-progress\ntsow: docs/TECHNICAL_SOW.md\n"
        "<!-- FRIDAY-STATE:END -->\n", encoding="utf-8")
    return tmp_path


def run_hook(event, cwd):
    return subprocess.run(
        ["python3", os.path.join(BUILD_ROOT, "hooks", "decision_capture.py"),
         BUILD_ROOT],
        input=json.dumps(event), capture_output=True, text=True, cwd=str(cwd))


ASK_STORE = ("[FRIDAY-DECISION] Session store choice\n"
             "decision: which session store the API uses\n"
             "why: survives restarts\nrejected: in-memory dict\n"
             "floor: none\nweight: two-way\n")
ASK_MODEL = ("[FRIDAY-DECISION] Profiler model pin\n"
             "decision: which model runs the profiler interview\n"
             "why: cheap + sufficient\nrejected: inherit session model\n"
             "floor: spend\nweight: two-way\n")

Q_STORE = {"question": ASK_STORE, "header": "Store",
           "options": [{"label": "redis"}, {"label": "in-memory dict"}]}
Q_MODEL = {"question": ASK_MODEL, "header": "Model",
           "options": [{"label": "haiku"}, {"label": "sonnet"}]}


def _event(proj, questions, tool_response):
    return {"hook_event_name": "PostToolUse", "cwd": str(proj),
            "tool_name": "AskUserQuestion", "session_id": "s1",
            "tool_input": {"questions": questions},
            "tool_response": tool_response}


def _entries(proj):
    parsed = decisions.parse_file(str(proj / "docs" / "DECISIONS.md"))
    assert parsed["ok"], parsed["errors"]
    return parsed["entries"]


# --- facet (a): every decision-shaped question captures ---------------------------------

def test_both_questions_get_entries_modern_answers_shape(proj):
    """Today's host shape: answers keyed by the question's own text."""
    p = run_hook(_event(proj, [Q_STORE, Q_MODEL],
                        {"answers": {ASK_STORE: "redis", ASK_MODEL: "haiku"}}),
                 proj)
    assert p.returncode == 0, p.stderr
    entries = _entries(proj)
    assert len(entries) == 2, [e["title"] for e in entries]
    store, model = entries
    assert store["title"] == "Session store choice"
    assert model["title"] == "Profiler model pin"
    assert "redis" in store["decision"]
    assert "haiku" in model["decision"]
    # floor override still applies per question (PROP-044)
    assert model["floor"] == "spend" and model["weight"] == "one-way"


def test_decision_question_not_in_first_position_still_captures(proj):
    """An ordinary first question must not shadow a decision-shaped second."""
    q_plain = {"question": "Should I also update the README?", "header": "Docs",
               "options": [{"label": "yes"}, {"label": "no"}]}
    p = run_hook(_event(proj, [q_plain, Q_MODEL],
                        {"answers": {"Should I also update the README?": "yes",
                                     ASK_MODEL: "haiku"}}), proj)
    assert p.returncode == 0, p.stderr
    entries = _entries(proj)
    assert len(entries) == 1, [e["title"] for e in entries]
    assert entries[0]["title"] == "Profiler model pin"
    assert "haiku" in entries[0]["decision"]


# --- facet (b): per-question attribution -------------------------------------------------

def test_no_answer_cross_talk_between_questions(proj):
    run_hook(_event(proj, [Q_STORE, Q_MODEL],
                    {"answers": {ASK_STORE: "redis", ASK_MODEL: "haiku"}}), proj)
    store, model = _entries(proj)
    assert "haiku" not in store["decision"]
    assert "redis" not in model["decision"]
    # not-chosen options come from the entry's OWN question only
    assert "in-memory dict" in store["rejected"]
    assert "sonnet" not in store["rejected"]
    assert "sonnet" in model["rejected"]
    assert "in-memory dict" not in model["rejected"]


def test_list_shape_answers_attribute_per_question(proj):
    """Older walkable shape: a list of {question, answer} dicts must not be
    mashed into one 'a; b' string on the first entry."""
    p = run_hook(_event(proj, [Q_STORE, Q_MODEL],
                        {"answers": [{"question": ASK_STORE, "answer": "redis"},
                                     {"question": ASK_MODEL, "answer": "haiku"}]}),
                 proj)
    assert p.returncode == 0, p.stderr
    entries = _entries(proj)
    assert len(entries) == 2, [e["title"] for e in entries]
    store, model = entries
    assert "redis" in store["decision"] and "haiku" not in store["decision"]
    assert "haiku" in model["decision"] and "redis" not in model["decision"]


# --- facet (c): honest fallback, no dead pointer ------------------------------------------

def test_missing_answer_fallback_names_the_rerecord_tool(proj):
    """When one question's answer genuinely can't be found, its entry says how
    to re-record it — and never points at the already-deleted ask mirror."""
    p = run_hook(_event(proj, [Q_STORE, Q_MODEL],
                        {"answers": {ASK_STORE: "redis"}}), proj)
    assert p.returncode == 0, p.stderr
    entries = _entries(proj)
    assert len(entries) == 2, [e["title"] for e in entries]
    model = entries[1]
    assert "decisions_append" in model["decision"]
    assert "ask mirror" not in model["decision"]
