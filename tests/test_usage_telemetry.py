"""hooks/usage_telemetry.py — the token-cost telemetry hook (task #14).

The ONLY wired hook of 32 that had zero tests, and it runs at EVERY Stop and
SubagentStop — exactly where a silent failure is least visible (the failure
contract is "degrade to no telemetry", so nothing downstream would ever
complain). These tests drive `process_event` with the real substrate over a
real tmp project: the byte-cursor discipline (advance, partial trailing line,
shrunken-file reset) is the part most likely to rot silently, so it gets the
most pins.
"""
import json
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_BASE, "tools"))
sys.path.insert(0, os.path.join(_BASE, "hooks"))
import friday_substrate as fs  # noqa: E402
import usage_telemetry as ut  # noqa: E402


def _proj(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".friday").mkdir()          # should_engage: an existing .friday suffices
    return root


def _usage_line(model, inp=0, out=0, cr=0, cw=0):
    return json.dumps({"message": {"model": model, "usage": {
        "input_tokens": inp, "output_tokens": out,
        "cache_read_input_tokens": cr, "cache_creation_input_tokens": cw}}}) + "\n"


def _journal(root):
    path = root / ".friday" / "journal.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def _usage_events(root):
    return [ln for ln in _journal(root) if ln["event"] == "usage"]


def _event(root, transcript, name="Stop", **extra):
    return {"hook_event_name": name, "cwd": str(root),
            "transcript_path": str(transcript), **extra}


def test_stop_appends_one_usage_line_per_model_with_priced_usd(tmp_path):
    root = _proj(tmp_path)
    t = tmp_path / "t.jsonl"
    t.write_text(_usage_line("claude-opus-5", inp=100, out=50, cr=1000, cw=200)
                 + _usage_line("claude-haiku-4-5", inp=10, out=5))
    ut.process_event(fs, _event(root, t))
    events = _usage_events(root)
    assert len(events) == 2
    by_model = {e["data"]["model"]: e["data"] for e in events}
    opus = by_model["claude-opus-5"]
    assert opus["agent"] == "lead"
    assert (opus["input"], opus["output"], opus["cache_read"], opus["cache_write"]) \
        == (100, 50, 1000, 200)
    # priced from the table: (100*5 + 50*25 + 1000*5*0.1 + 200*5*1.25) / 1e6
    assert opus["usd"] == round((100 * 5 + 50 * 25 + 1000 * 0.5 + 200 * 6.25) / 1e6, 4)
    assert "usd" in by_model["claude-haiku-4-5"]


def test_unrecognized_model_records_tokens_but_omits_usd(tmp_path):
    """Token counts are the durable record; the price is a convenience that
    must never be guessed for a model the table doesn't know."""
    root = _proj(tmp_path)
    t = tmp_path / "t.jsonl"
    t.write_text(_usage_line("gpt-42-mega", inp=100, out=100))
    ut.process_event(fs, _event(root, t))
    (event,) = _usage_events(root)
    assert event["data"]["input"] == 100 and "usd" not in event["data"]


def test_second_pass_reads_only_the_new_portion(tmp_path):
    """The whole point of the byte cursor: N passes over a growing transcript
    journal each token exactly once, never re-billing the prefix."""
    root = _proj(tmp_path)
    t = tmp_path / "t.jsonl"
    t.write_text(_usage_line("claude-opus-5", inp=100, out=10))
    ut.process_event(fs, _event(root, t))
    with open(t, "a") as fh:
        fh.write(_usage_line("claude-opus-5", inp=7, out=3))
    ut.process_event(fs, _event(root, t))
    events = _usage_events(root)
    assert len(events) == 2
    assert (events[1]["data"]["input"], events[1]["data"]["output"]) == (7, 3)


def test_a_partial_trailing_line_waits_for_the_next_pass(tmp_path):
    """A writer mid-line at Stop time must not have its half-line consumed:
    the cursor stops at the last complete line, and the finished line is
    picked up whole on the next pass."""
    root = _proj(tmp_path)
    t = tmp_path / "t.jsonl"
    half = _usage_line("claude-opus-5", inp=50, out=50).rstrip("\n")
    t.write_text(_usage_line("claude-sonnet-5", inp=1, out=1) + half)
    ut.process_event(fs, _event(root, t))
    assert len(_usage_events(root)) == 1        # only the complete sonnet line
    with open(t, "a") as fh:
        fh.write("\n")                          # the writer finishes its line
    ut.process_event(fs, _event(root, t))
    events = _usage_events(root)
    assert len(events) == 2
    assert events[1]["data"]["model"] == "claude-opus-5"
    assert events[1]["data"]["input"] == 50     # whole line, counted once


def test_a_shrunken_transcript_resets_the_cursor(tmp_path):
    """A cursor past the end of the file means the transcript was replaced —
    re-read from the top rather than silently recording nothing forever."""
    root = _proj(tmp_path)
    t = tmp_path / "t.jsonl"
    t.write_text(_usage_line("claude-opus-5", inp=100, out=100) * 5)
    ut.process_event(fs, _event(root, t))
    t.write_text(_usage_line("claude-opus-5", inp=9, out=9))   # smaller than the cursor
    ut.process_event(fs, _event(root, t))
    events = _usage_events(root)
    assert len(events) == 2
    assert events[1]["data"]["input"] == 9


def test_subagent_stop_records_the_agent_type(tmp_path):
    root = _proj(tmp_path)
    t = tmp_path / "t.jsonl"
    t.write_text(_usage_line("claude-sonnet-5", inp=5, out=5))
    ut.process_event(fs, _event(root, t, name="SubagentStop",
                                agent_type="friday-tester"))
    (event,) = _usage_events(root)
    assert event["data"]["agent"] == "friday-tester"


def test_zero_token_and_malformed_lines_are_skipped_quietly(tmp_path):
    """Garbage in the transcript degrades to 'no telemetry for that line',
    never a crash and never a zero-value journal entry."""
    root = _proj(tmp_path)
    t = tmp_path / "t.jsonl"
    t.write_text("not json at all\n"
                 + json.dumps({"message": "not-a-dict"}) + "\n"
                 + _usage_line("claude-opus-5"))                # all-zero usage
    ut.process_event(fs, _event(root, t))
    assert _usage_events(root) == []


def test_non_stop_events_and_missing_transcripts_are_noops(tmp_path):
    root = _proj(tmp_path)
    t = tmp_path / "t.jsonl"
    t.write_text(_usage_line("claude-opus-5", inp=1, out=1))
    ut.process_event(fs, _event(root, t, name="PreToolUse"))
    ut.process_event(fs, _event(root, tmp_path / "absent.jsonl"))
    assert _usage_events(root) == []
