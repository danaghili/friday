"""INC-008 FR-8.6 / AC-8.7 / KH-7 — the standards-deviation ledger.

Test-first. A justified measured breach becomes a durable, accountable record in
docs/STANDARDS-DEVIATIONS.md — the governance spine. A SIBLING of the decision
log: same machinery (single writer, monotonic ids, two channels, growing-log
cap+archive, a byte-exact tested empty form), its own schema and file. This is
the ONLY home for a measured breach (a taste departure goes to an ADR — KH-7).
"""
import os
import subprocess

import pytest

import standards_deviations as sd


# --- the empty form (byte-exact, tested) ---------------------------------------

def test_empty_form_roundtrip():
    text = sd.empty_form()
    assert text.startswith("# Standards Deviations")
    assert sd.EMPTY_SENTINEL in text
    res = sd.parse(text)
    assert res["ok"] and res["empty"] and res["entries"] == [] and res["errors"] == []


def test_missing_h1_or_sentinel_is_not_a_valid_empty_form():
    assert not sd.parse("")["ok"]
    assert not sd.parse("# Standards Deviations — x\n")["ok"]   # heading, no sentinel


def test_sentinel_plus_entry_is_malformed():
    text = sd.empty_form() + "\n" + sd.format_entry(
        id_num=1, metric="complexity", measured="37", bar="15",
        location="f.py:1:x", justification="j", standard="s",
        when="2026-07-24T00:00:00Z", channel="model-autonomous", floor="none")
    assert not sd.parse(text)["ok"]   # sentinel must be REPLACED by the first entry


# --- schema roundtrip ----------------------------------------------------------

def test_format_and_parse_roundtrip():
    entry = sd.format_entry(
        id_num=1, metric="param-count", measured="14", bar="6",
        location="tools/decisions.py:265:append_entry",
        justification="documented keyword-only builder; refactor queued",
        standard="coding-standards.md §Size", when="2026-07-24T00:00:00Z",
        channel="pm-ratified", floor="none")
    text = sd.empty_form().replace(sd.EMPTY_SENTINEL, "").rstrip() + "\n\n" + entry
    res = sd.parse(text)
    assert res["ok"] and not res["empty"]
    [e] = res["entries"]
    assert e["id_str"] == "SD-0001"
    assert e["metric"] == "param-count" and e["measured"] == "14" and e["bar"] == "6"
    assert e["location"] == "tools/decisions.py:265:append_entry"
    assert e["channel"] == "pm-ratified" and e["floor"] == "none"
    assert e["justification"].startswith("documented") and e["standard"].endswith("Size")


# --- closed vocabularies -------------------------------------------------------

def test_channel_and_floor_vocab_closed():
    assert sd.validate_fields("model-autonomous", "none") == []
    assert sd.validate_fields("pm-ratified", "auth-security") == []
    assert sd.validate_fields("whatever", "none")          # bad channel
    assert sd.validate_fields("pm-ratified", "kinda")      # bad floor


# --- the single writer: monotonic ids, sentinel replacement --------------------

@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs").mkdir()
    # a minimal friday marker so the substrate engages
    (tmp_path / "docs" / "TECHNICAL_SOW.md").write_text("# TSOW\n")
    return tmp_path


def test_append_replaces_sentinel_and_assigns_monotonic_ids(repo):
    id1, _ = sd.append_entry(str(repo), metric="complexity", measured="37", bar="15",
                             location="tools/trail_check.py:102:check_text",
                             justification="single-pass token scan; splitting scatters it",
                             standard="coding-standards.md §Complexity",
                             channel="model-autonomous", floor="none")
    id2, _ = sd.append_entry(str(repo), metric="file-size", measured="522", bar="450",
                             location="tools/friday_substrate.py",
                             justification="the single shared writer; cohesive on purpose",
                             standard="coding-standards.md §Size",
                             channel="pm-ratified", floor="none")
    assert (id1, id2) == ("SD-0001", "SD-0002")
    text = (repo / "docs" / "STANDARDS-DEVIATIONS.md").read_text()
    assert sd.EMPTY_SENTINEL not in text          # sentinel replaced on first append
    res = sd.parse(text)
    assert res["ok"] and len(res["entries"]) == 2


def test_dangerous_floor_is_recordable(repo):
    idn, _ = sd.append_entry(str(repo), metric="complexity", measured="20", bar="15",
                             location="src/auth/login.py:40:verify",
                             justification="PM-ratified: rewrite scheduled next increment",
                             standard="coding-standards.md §Complexity",
                             channel="pm-ratified", floor="auth-security")
    res = sd.parse((repo / "docs" / "STANDARDS-DEVIATIONS.md").read_text())
    assert res["entries"][0]["floor"] == "auth-security"


def test_bad_channel_raises(repo):
    with pytest.raises(ValueError):
        sd.append_entry(str(repo), metric="complexity", measured="37", bar="15",
                        location="f.py:1:x", justification="j", standard="s",
                        channel="not-a-channel", floor="none")
