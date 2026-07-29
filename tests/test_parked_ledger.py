"""INC-200 C3 (task #23, D-0108) — the PARKED ledger: the waiting room becomes real.

Three surfaces already behaved as if a waiting room existed (redteam's candidate
requirements "into the waiting room", feedback's decline vocabulary, reconcile's
§5 roundup) while no such destination existed anywhere (NF4). "Good idea, not
now" was therefore recorded as rejection — losing the re-presentation path that
is the entire point of parking something rather than killing it.

D-0108 rules the shape: a small typed ledger at docs/PARKED.md — one line per
entry carrying source, date, what, and revisit-when — written by feedback and
redteam, swept and re-presented by reconcile. `tools/parked.py` owns the record
(the D-0135 pattern: a module owning a whole record type writes it itself).

What the tests insist on, learned the hard way elsewhere in this house:

- **The empty case is a first-class citizen** (house grammar rule): an absent
  file, and a present file with nothing parked, are both valid and quiet.
- **A malformed line is surfaced, never dropped** — a silently-vanishing entry
  is a parked idea that will never be re-presented, which is precisely the
  failure the ledger exists to end (same fault class task #10 fixed).
- **Resolution removes the line but the ledger never forgets how to be empty**
  — the sentinel returns when the last entry goes, so "nothing parked" stays a
  written fact rather than a bare block.
- **Free text cannot break the grammar** — a `what` containing the separator
  glyphs must round-trip; the parser anchors on the LAST separator, not the
  first.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import parked  # noqa: E402


def _root(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    return str(root)


def _ledger(root):
    return open(os.path.join(root, "docs", "PARKED.md"), encoding="utf-8").read()


# --- the empty cases -------------------------------------------------------------------

def test_no_ledger_file_means_no_entries_and_no_crash(tmp_path):
    root = _root(tmp_path)
    assert parked.entries(root) == []


def test_a_fresh_ledger_carries_the_sentinel_not_a_bare_block(tmp_path):
    """`_Nothing parked._` is a written fact — the reader can tell 'empty by
    design' from 'someone deleted the contents'."""
    root = _root(tmp_path)
    parked.append(root, source="feedback", what="an idea", revisit_when="later",
                  when="2026-07-29")
    parked.resolve(root, "PARK-001", by="reconcile")
    text = _ledger(root)
    assert "_Nothing parked._" in text
    assert parked.entries(root) == []


# --- appending -------------------------------------------------------------------------

def test_the_first_park_creates_the_ledger_and_mints_park_001(tmp_path):
    root = _root(tmp_path)
    res = parked.append(root, source="feedback",
                        what="dark mode for the dashboard",
                        revisit_when="after the v2 design pass",
                        when="2026-07-29")
    assert res["id"] == "PARK-001"
    text = _ledger(root)
    assert text.startswith("# Parked")
    assert "PARK-001" in text and "dark mode for the dashboard" in text


def test_an_entry_round_trips_all_four_ruled_fields(tmp_path):
    """D-0108 names exactly these: source, date, what, revisit-when."""
    root = _root(tmp_path)
    parked.append(root, source="redteam", what="rate-limit the export endpoint",
                  revisit_when="before the first external user", when="2026-07-29")
    (entry,) = parked.entries(root)
    assert entry["source"] == "redteam"
    assert entry["date"] == "2026-07-29"
    assert entry["what"] == "rate-limit the export endpoint"
    assert entry["revisit_when"] == "before the first external user"
    assert entry["malformed"] is False


def test_ids_are_sequential_and_never_reused_after_a_resolve(tmp_path):
    """A resolved PARK-001 must not free its number: an id that comes back as a
    different idea would poison every old reference to it."""
    root = _root(tmp_path)
    parked.append(root, source="feedback", what="a", revisit_when="x", when="2026-07-29")
    parked.append(root, source="redteam", what="b", revisit_when="y", when="2026-07-29")
    parked.resolve(root, "PARK-002", by="reconcile")
    res = parked.append(root, source="feedback", what="c", revisit_when="z",
                        when="2026-07-30")
    assert res["id"] == "PARK-003"


def test_an_unknown_source_is_refused(tmp_path):
    """Closed vocabulary (K4 doctrine): the writers D-0108 names, plus the two
    the reconcile roundup already sweeps — never an invented value."""
    root = _root(tmp_path)
    try:
        parked.append(root, source="somebody", what="a", revisit_when="x")
        raised = False
    except ValueError as exc:
        raised = True
        assert "source" in str(exc)
    assert raised
    assert parked.entries(root) == []


def test_empty_what_or_revisit_is_refused(tmp_path):
    """An entry with no revisit condition is exactly the unre-presentable
    limbo the ledger replaces."""
    root = _root(tmp_path)
    for kwargs in ({"what": "", "revisit_when": "x"},
                   {"what": "a", "revisit_when": "  "}):
        try:
            parked.append(root, source="feedback", **kwargs)
            assert False, f"accepted {kwargs}"
        except ValueError:
            pass


# --- the grammar under hostile text ------------------------------------------------------

def test_free_text_containing_the_separators_round_trips(tmp_path):
    """`what` is PM prose — it WILL eventually contain an em-dash and the word
    'revisit'. The parser must anchor on the final `· revisit-when:` marker,
    not the first glyph it sees."""
    root = _root(tmp_path)
    tricky = "support import — csv · maybe json too — revisit the parser"
    parked.append(root, source="feedback", what=tricky,
                  revisit_when="when a second format is requested",
                  when="2026-07-29")
    (entry,) = parked.entries(root)
    assert entry["what"] == tricky
    assert entry["revisit_when"] == "when a second format is requested"


def test_a_malformed_line_is_kept_and_flagged_never_dropped(tmp_path):
    root = _root(tmp_path)
    parked.append(root, source="feedback", what="fine", revisit_when="later",
                  when="2026-07-29")
    path = os.path.join(root, "docs", "PARKED.md")
    text = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(text.replace(
        "<!-- FRIDAY-PARKED:END -->",
        "parked: PARK-999 this line has no separator at all\n<!-- FRIDAY-PARKED:END -->"))
    all_entries = parked.entries(root)
    assert len(all_entries) == 2
    bad = [e for e in all_entries if e["malformed"]]
    assert len(bad) == 1 and "PARK-999" in bad[0]["raw"]


# --- resolving ---------------------------------------------------------------------------

def test_resolve_removes_exactly_that_line(tmp_path):
    root = _root(tmp_path)
    parked.append(root, source="feedback", what="keep me", revisit_when="x",
                  when="2026-07-29")
    parked.append(root, source="redteam", what="remove me", revisit_when="y",
                  when="2026-07-29")
    res = parked.resolve(root, "PARK-002", by="reconcile")
    assert res["ok"] is True
    remaining = parked.entries(root)
    assert [e["id"] for e in remaining] == ["PARK-001"]
    assert "remove me" not in _ledger(root)


def test_resolving_an_unknown_id_is_an_error_not_a_crash_and_changes_nothing(tmp_path):
    root = _root(tmp_path)
    parked.append(root, source="feedback", what="a", revisit_when="x",
                  when="2026-07-29")
    before = _ledger(root)
    res = parked.resolve(root, "PARK-042", by="reconcile")
    assert res["ok"] is False and "PARK-042" in res["detail"]
    assert _ledger(root) == before


# --- the shape the lanes consume ----------------------------------------------------------

def test_cli_append_prints_the_id_and_exits_zero(tmp_path, capsys):
    root = _root(tmp_path)
    rc = parked.main(["append", "--root", root, "--source", "feedback",
                      "--what", "an idea", "--revisit-when", "next quarter"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["id"] == "PARK-001"


def test_cli_list_emits_json_entries(tmp_path, capsys):
    root = _root(tmp_path)
    parked.append(root, source="redteam", what="a", revisit_when="x",
                  when="2026-07-29")
    rc = parked.main(["list", "--root", root])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and len(out["entries"]) == 1


def test_cli_resolve_unknown_id_exits_nonzero(tmp_path, capsys):
    root = _root(tmp_path)
    rc = parked.main(["resolve", "--root", root, "--id", "PARK-007",
                      "--by", "reconcile"])
    capsys.readouterr()
    assert rc == 1
