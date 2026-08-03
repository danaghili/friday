"""INC-208 FR-208.4/.5 — the dispatch-briefing typed line and the report-only
checker (tests first).

The checker's precision is the make-or-break property (AC-208.1, KH-1): a
drawer's `mission.md` has TWO legitimate producers under
`docs/contracts/compaction-package.md` — a dispatch briefing, and the
orchestrator's own lane-entry note. Reporting the second as a defective
briefing is how a report-only checker earns the reputation that gets it
ignored, so scoping runs off the spawn journal (which dispatches actually
happened) rather than off which files exist.

Every fixture is built in a tmp tree; nothing here reads the real drawer.
"""
import json
import os
import subprocess
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
sys.path.insert(0, TOOLS)

import dispatch_briefing_check as dbc  # noqa: E402

SID = "session-abc"


def _journal(root, records):
    """Write .friday/journal.jsonl with the given event dicts."""
    d = os.path.join(root, ".friday")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "journal.jsonl"), "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _spawn(agent, phase="feature:increment-discovery", ts="2026-07-31T09:00:00Z"):
    return {"ts": ts, "feature": "-", "phase": phase, "event": "spawn",
            "by": "lead", "data": {"agent": agent}}


def _drawer(root, agent, text, sid=SID, layer="mission"):
    d = os.path.join(root, ".friday", "compaction", sid, agent)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{layer}.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def _line(lane="feature", role="friday-tester", drawer=None, template=None, sid=SID):
    drawer = drawer if drawer is not None else f".friday/compaction/{sid}/{role}/"
    template = template if template is not None else "docs/dispatch-briefing-template.md"
    return (f"dispatch: lane={lane} role={role} drawer={drawer} "
            f"template={template}\n")


def _briefing(**kw):
    return _line(**kw) + "\nYou are the tester. Read these files first: ...\n"


# --- the typed line's grammar (FR-208.4) ------------------------------------

def test_typed_line_parses_all_four_required_fields():
    fields = dbc.parse_dispatch_line(_line().strip())
    assert fields == {"lane": "feature", "role": "friday-tester",
                      "drawer": f".friday/compaction/{SID}/friday-tester/",
                      "template": "docs/dispatch-briefing-template.md"}


def test_typed_line_must_be_the_first_non_blank_line():
    text = "Some preamble the composer wrote.\n\n" + _line()
    assert dbc.briefing_line(text) is None


def test_blank_lines_before_the_typed_line_are_tolerated():
    assert dbc.briefing_line("\n\n" + _line()) is not None


def test_a_line_that_is_not_a_dispatch_tag_is_not_a_briefing_line():
    assert dbc.briefing_line("trail: lane=feature id=INC-208 date=2026-07-31\n") is None


def test_empty_text_yields_no_line():
    assert dbc.briefing_line("") is None
    assert dbc.briefing_line("\n\n\n") is None


# --- the checker's two defect classes (FR-208.5) ----------------------------

def test_missing_field_is_named_by_field_and_file(tmp_path):
    root = str(tmp_path)
    _journal(root, [_spawn("friday-tester")])
    _drawer(root, "friday-tester",
            "dispatch: lane=feature role=friday-tester "
            "template=docs/dispatch-briefing-template.md\n\nbody\n")
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is False
    f = [x for x in res["findings"] if x["kind"] == "missing-field"]
    assert len(f) == 1
    assert f[0]["field"] == "drawer"
    assert f[0]["file"].endswith("friday-tester/mission.md")
    assert f[0]["role"] == "friday-tester"


def test_dispatch_with_no_saved_briefing_at_all_is_named(tmp_path):
    root = str(tmp_path)
    _journal(root, [_spawn("friday-brainstormer")])
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is False
    f = [x for x in res["findings"] if x["kind"] == "unsaved-briefing"]
    assert len(f) == 1 and f[0]["role"] == "friday-brainstormer"


def test_saved_briefing_with_no_typed_line_reports_unchecked_never_passed(tmp_path):
    root = str(tmp_path)
    _journal(root, [_spawn("friday-tester")])
    _drawer(root, "friday-tester", "You are the tester. No typed line here.\n")
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is False
    kinds = {x["kind"] for x in res["findings"]}
    assert kinds == {"unchecked-briefing"}


def test_complete_briefing_reports_nothing(tmp_path):
    root = str(tmp_path)
    _journal(root, [_spawn("friday-tester")])
    _drawer(root, "friday-tester", _briefing())
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is True and res["findings"] == []


# --- KH-1: the orchestrator's own note is never a briefing ------------------

def test_lane_entry_note_in_the_same_drawer_is_never_reported(tmp_path):
    """The make-or-break precision case: a drawer holding BOTH a real dispatch
    briefing and the orchestrator's self-authored lane-entry note. The checker
    reports on the first and says nothing whatever about the second."""
    root = str(tmp_path)
    _journal(root, [_spawn("friday-tester")])
    _drawer(root, "friday-tester", _briefing())
    _drawer(root, "friday-lead",
            "# Lane entry — my own note\n\nWhat I set out to do this session.\n")
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is True and res["findings"] == []
    assert all("friday-lead" not in f.get("file", "") for f in res["findings"])


def test_a_dispatch_briefed_in_an_earlier_session_is_not_reported(tmp_path):
    """The false-alarm class the checker's own first live run exposed: the
    journal spans every session, but a drawer is per-session. A dispatch from
    an earlier session saved its briefing in THAT session's drawer, so looking
    only in today's drawer reports it as unsaved — nine such false alarms on
    the first real run. A briefing found in any drawer is a briefing that was
    saved (KH-1: this checker may never cry wolf)."""
    root = str(tmp_path)
    _journal(root, [_spawn("friday-researcher")])
    _drawer(root, "friday-researcher", _briefing(role="friday-researcher",
                                                 sid="session-older"),
            sid="session-older")
    res = dbc.check(root, session_id=SID)          # today's session drawer
    assert res["ok"] is True and res["findings"] == []


def test_a_dispatch_briefed_nowhere_at_all_is_still_reported(tmp_path):
    """The other side of the same fix: cross-drawer lookup must not become a
    blanket amnesty — a role briefed in NO drawer anywhere is the real defect
    and stays reported."""
    root = str(tmp_path)
    _journal(root, [_spawn("friday-researcher")])
    _drawer(root, "friday-tester", _briefing(), sid="session-older")
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is False
    assert [f["kind"] for f in res["findings"]] == ["unsaved-briefing"]


def test_an_instance_suffixed_drawer_counts_as_that_role_s_briefing(tmp_path):
    """The template tells a lane to instance-suffix the drawer when it
    dispatches the same role twice in one session, so the second briefing does
    not overwrite the first agent's notes. A checker that only looks up the
    bare slug would then report a properly-briefed dispatch as unsaved —
    the template's own advice creating the false alarm."""
    root = str(tmp_path)
    _journal(root, [_spawn("friday-brainstormer")])
    _drawer(root, "friday-brainstormer-208",
            _briefing(role="friday-brainstormer"))
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is True and res["findings"] == []


def test_a_drawer_nobody_dispatched_is_invisible_even_when_malformed(tmp_path):
    root = str(tmp_path)
    _journal(root, [])          # no dispatches at all
    _drawer(root, "friday-lead", "not a briefing, no typed line, deliberately\n")
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is True and res["findings"] == []


# --- empty cases (AC-208.1) -------------------------------------------------

def test_no_journal_at_all_is_a_clean_empty_case(tmp_path):
    res = dbc.check(str(tmp_path), session_id=SID)
    assert res["ok"] is True and res["findings"] == []


def test_journal_with_no_spawn_events_is_a_clean_empty_case(tmp_path):
    root = str(tmp_path)
    _journal(root, [{"ts": "2026-07-31T09:00:00Z", "feature": "-",
                     "phase": "feature:build", "event": "done", "by": "lead",
                     "data": {"agent": "friday-tester"}}])
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is True and res["findings"] == []


def test_one_finding_per_dispatch_even_when_an_agent_spawned_twice(tmp_path):
    root = str(tmp_path)
    _journal(root, [_spawn("friday-tester", ts="2026-07-31T09:00:00Z"),
                    _spawn("friday-tester", ts="2026-07-31T10:00:00Z")])
    res = dbc.check(root, session_id=SID)
    # one drawer, one mission file — the agent is reported once, not twice
    assert len([f for f in res["findings"] if f["kind"] == "unsaved-briefing"]) == 1


# --- S-208.1 fail-open, S-208.2 names never prose ---------------------------

def test_unreadable_journal_allows_rather_than_crashing(tmp_path):
    root = str(tmp_path)
    d = os.path.join(root, ".friday")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "journal.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("{not json at all\n")
    res = dbc.check(root, session_id=SID)
    assert res["ok"] is True          # fail-open: unsure ALLOWS


def test_findings_never_carry_briefing_body_text(tmp_path):
    root = str(tmp_path)
    secret = "THE-PMS-OWN-WORDS-THAT-MUST-NOT-TRAVEL"
    _journal(root, [_spawn("friday-tester")])
    _drawer(root, "friday-tester",
            "dispatch: lane=feature role=friday-tester "
            f"template=docs/dispatch-briefing-template.md\n\n{secret}\n")
    res = dbc.check(root, session_id=SID)
    assert secret not in json.dumps(res)


def test_cli_exits_zero_even_with_findings(tmp_path):
    """Report-only (S-208.1): the checker names defects and still exits 0 —
    it can never become the reason a close fails."""
    root = str(tmp_path)
    _journal(root, [_spawn("friday-brainstormer")])
    res = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "dispatch_briefing_check.py"),
         "--root", root, "--session-id", SID, "--json"],
        capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["ok"] is False and payload["findings"]
