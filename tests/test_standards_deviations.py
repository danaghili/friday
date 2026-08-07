"""INC-105 FR-105.10 — the deviations ledger widened to the rule-shaped entry.

An `accepted` answer from the conformance envelope lands in the ONE ledger
(docs/STANDARDS-DEVIATIONS.md) beside the number-shaped measured breaches —
a project's accepted deviations are one question with one answer (D8). The
title alternative parses back (`conformance <check-id> @ <location>`), the
empty form is byte-identical to what INC-008 pinned (the widening adds a
shape, never disturbs the file), and the archive reformatter round-trips
both shapes. Contract: docs/contracts/standards-deviation.md, amended on
both sides of the seam with docs/contracts/conformance-envelope.md.
"""
import os
import subprocess
import sys

import pytest

import standards_deviations as sd

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools",
                    "standards_deviations.py")


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "TECHNICAL_SOW.md").write_text("# TSOW\n")
    return tmp_path


# --- the empty form is untouched by the widening --------------------------------

def test_empty_form_byte_identical_to_the_inc008_pin():
    assert sd.empty_form() == (
        "# Standards Deviations — friday project\n\n"
        "<!-- FRIDAY-STANDARDS-DEVIATIONS v1 — append via tools/standards_deviations.py (never\n"
        "     hand-edit past entries). Schema contract: docs/contracts/standards-deviation.md.\n"
        "     Growing-log discipline: entry cap 100; overflow MOVES the oldest half to\n"
        "     docs/deviations/archive-NNN.md — completion is a move, not a flag. -->\n\n"
        "_No standards deviations recorded yet._\n")


# --- the rule-shaped title parses back -------------------------------------------

def test_rule_entry_title_parses_back():
    entry = sd.format_rule_entry(
        id_num=7, check_id="no-env-bypass", location="app/jobs/sync.ts:1",
        justification="legacy job retires next quarter; breach accepted",
        standard="every environment variable is read through config.ts",
        when="2026-08-04T00:00:00Z", channel="pm-ratified", floor="none")
    assert "## SD-0007 — conformance no-env-bypass @ app/jobs/sync.ts:1\n" in entry
    text = sd.empty_form().replace(sd.EMPTY_SENTINEL, "").rstrip() + "\n\n" + entry
    res = sd.parse(text)
    assert res["ok"]
    [e] = res["entries"]
    assert e["shape"] == "rule"
    assert e["check"] == "no-env-bypass"
    assert e["location"] == "app/jobs/sync.ts:1"
    assert e["standard"].startswith("every environment variable")


def test_title_parsing_as_neither_shape_is_an_error_naming_both():
    text = (sd.empty_form().replace(sd.EMPTY_SENTINEL, "").rstrip()
            + "\n\n## SD-0001 — vibes felt off near the handler\n"
              "**When:** 2026-08-04T00:00:00Z · **Channel:** pm-ratified · **Floor:** none\n"
              "- **Justification:** j\n- **Standard:** s\n")
    res = sd.parse(text)
    assert not res["ok"]
    [err] = [e for e in res["errors"] if "title does not parse" in e]
    assert "conformance <check-id> @ <location>" in err


# --- one ledger: both shapes side by side, one id sequence -----------------------

def test_rule_entry_appends_beside_number_entry_in_one_sequence(repo):
    sd.append_entry(str(repo), metric="complexity", measured="23", bar="15",
                    location="app/big.py:10:run", justification="j",
                    standard="s")
    idn, _ = sd.append_rule_entry(str(repo), check_id="no-env-bypass",
                                  location="app/jobs/sync.ts:1",
                                  justification="accepted for the quarter",
                                  standard="every env var through config.ts",
                                  channel="pm-ratified")
    assert idn == "SD-0002"
    res = sd.parse_file(str(repo / "docs" / "STANDARDS-DEVIATIONS.md"))
    assert res["ok"]
    assert [e["shape"] for e in res["entries"]] == ["number", "rule"]


def test_rule_append_validates_first_and_writes_nothing_on_bad_channel(repo):
    with pytest.raises(ValueError):
        sd.append_rule_entry(str(repo), check_id="c", location="l",
                             justification="j", standard="s",
                             channel="gut-feeling")
    assert not (repo / "docs" / "STANDARDS-DEVIATIONS.md").exists()


# --- the archive reformatter round-trips mixed shapes ----------------------------

def test_archive_overflow_reformats_both_shapes_faithfully(repo):
    for i in range(3):
        sd.append_entry(str(repo), metric="loc", measured=str(400 + i),
                        bar="300", location=f"m{i}.py", justification="j",
                        standard="s", cap=4)
    sd.append_rule_entry(str(repo), check_id="no-env-bypass",
                         location="app/a.ts:1", justification="j",
                         standard="s", cap=4)
    sd.append_entry(str(repo), metric="loc", measured="500", bar="300",
                    location="m9.py", justification="j", standard="s", cap=4)
    arch = repo / "docs" / "deviations" / "archive-001.md"
    assert arch.exists()
    live = sd.parse_file(str(repo / "docs" / "STANDARDS-DEVIATIONS.md"))
    archived = sd.parse(arch.read_text())
    assert live["ok"] and archived["ok"]
    shapes = ([e["shape"] for e in archived["entries"]]
              + [e["shape"] for e in live["entries"]])
    assert shapes == ["number", "number", "number", "rule", "number"]
    [rule] = [e for e in archived["entries"] + live["entries"]
              if e["shape"] == "rule"]
    assert rule["check"] == "no-env-bypass" and rule["location"] == "app/a.ts:1"


# --- the CLI door (--check replaces --metric/--measured/--bar) --------------------

def test_cli_check_flag_appends_rule_entry(repo):
    out = subprocess.run(
        [sys.executable, TOOL, "--root", str(repo), "--check", "no-env-bypass",
         "--location", "app/jobs/sync.ts:1", "--justification", "accepted",
         "--standard", "every env var through config.ts",
         "--channel", "pm-ratified"],
        capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "SD-0001"
    ledger = (repo / "docs" / "STANDARDS-DEVIATIONS.md").read_text()
    assert "conformance no-env-bypass @ app/jobs/sync.ts:1" in ledger


def test_cli_check_flag_names_its_missing_fields(repo):
    out = subprocess.run(
        [sys.executable, TOOL, "--root", str(repo), "--check", "c",
         "--justification", "j"],
        capture_output=True, text=True)
    assert out.returncode == 2
    assert "--check needs" in out.stderr
