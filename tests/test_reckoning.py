"""INC-104 FR-104.4/104.5/104.6/104.8 — the consumer reckoning record
(tools/reckoning.py).

One typed line per enumerated consumer in a marker-fenced block; the answer
vocabulary is closed and locked to the contract table
(docs/contracts/reckoning-record.md); a clearance cannot be recorded without
its observable (refused) and resolves to not-proven when nothing exercises
the observable (AC-104.2, KH-1); the per-change `searched:` line's
not-covered statement is derived by the module, never accepted through any
field (S-104.2); the empty case is a valid, distinct outcome.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import reckoning  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONTRACT = os.path.join(REPO, "docs", "contracts", "reckoning-record.md")


def _record_path(root):
    return os.path.join(str(root), "docs", "RECKONINGS.md")


def _text(root):
    with open(_record_path(root), encoding="utf-8") as fh:
        return fh.read()


def _row(**over):
    base = {"change": "INC-104", "what": "tools/rollback.sh",
            "class": "code", "source": "name-match",
            "answer": "moves-with-change",
            "evidence": "tools/rollback.sh:12 names the deploy tag",
            "when": "2026-08-03"}
    base.update(over)
    return base


def _spec(**over):
    base = {"change": "INC-104", "declared": "ran", "name_match": "ran",
            "reading": "ran", "person": "answered", "name": "sha-tag",
            "when": "2026-08-03"}
    base.update(over)
    return base


# --- the vocabulary lock: module and contract state the same answer set ----

def test_answer_vocabulary_matches_the_contract_table():
    """The contract file is the answer set's single home (FR-104.4, D9); the
    module carries the operational copy. This test is the lock that keeps
    the two from rotting apart."""
    with open(CONTRACT, encoding="utf-8") as fh:
        text = fh.read()
    answers = re.findall(r"^\|\s*`([a-z][a-z-]*)`\s*\|", text, re.MULTILINE)
    assert answers, "contract table not found — the lock has nothing to hold"
    assert tuple(answers) == reckoning.ANSWERS


def test_the_word_is_not_disposition():
    """D9: `disposition` already names three things in this tree; the
    consumer answer's typed key must not be a fourth."""
    assert reckoning.KEY == "reckoning"
    assert "disposition" not in (reckoning.KEY,) + reckoning.ANSWERS


# --- recording the four answers --------------------------------------------

def test_moves_with_change_records_and_reads_back(tmp_path):
    res = reckoning.record(str(tmp_path), _row(change="PATCH-004"))
    assert res["ok"] is True
    out = reckoning.read(str(tmp_path))
    assert out["status"] == "recorded"
    (row,) = out["reckonings"]
    assert row["answer"] == "moves-with-change"
    assert row["what"] == "tools/rollback.sh"
    assert row["class"] == "code"
    assert row["source"] == "name-match"
    assert row["change"] == "PATCH-004"
    assert row["date"] == "2026-08-03"
    assert row["evidence"] == "tools/rollback.sh:12 names the deploy tag"


def test_cleared_requires_and_carries_both_parts(tmp_path):
    res = reckoning.record(str(tmp_path), _row(
        answer="cleared", source="declared",
        evidence="cites the deploy contract by name",
        observable="a reboot restores the recorded tag",
        exercised_by="tests/test_rollback.py::test_reboot"))
    assert res["ok"] is True
    (row,) = reckoning.read(str(tmp_path))["reckonings"]
    assert row["answer"] == "cleared"
    assert row["observable"] == "a reboot restores the recorded tag"
    assert row["exercised_by"] == "tests/test_rollback.py::test_reboot"


def test_not_proven_carries_observable_and_reason(tmp_path):
    res = reckoning.record(str(tmp_path), _row(
        what="the launchd supervisor", **{"class": "process"},
        source="person", answer="not-proven",
        evidence="the operator names it at the ask",
        observable="the app survives a host reboot",
        because="the observable lives on a production host friday "
                "never touches"))
    assert res["ok"] is True
    (row,) = reckoning.read(str(tmp_path))["reckonings"]
    assert row["answer"] == "not-proven"
    assert row["class"] == "process"
    assert row["because"].startswith("the observable lives")


def test_not_a_consumer_requires_its_reason(tmp_path):
    res = reckoning.record(str(tmp_path), _row(
        what="docs/old-notes.md", answer="not-a-consumer",
        evidence="docs/old-notes.md:3 names the tag",
        because="the mention is a dated example, not a dependency"))
    assert res["ok"] is True
    (row,) = reckoning.read(str(tmp_path))["reckonings"]
    assert row["answer"] == "not-a-consumer"
    res2 = reckoning.record(str(tmp_path), _row(
        what="docs/other.md", answer="not-a-consumer",
        evidence="docs/other.md:9 names the tag"))
    assert res2["ok"] is False
    assert "because" in res2["reason"] or "reason" in res2["reason"]


# --- AC-104.2: the clearance rule, both sides -------------------------------

def test_bare_clearance_is_refused_and_says_why(tmp_path):
    """A cleared consumer with no named observable is the artefact this
    increment exists to end — refused, with the reason in the refusal."""
    res = reckoning.record(str(tmp_path), _row(
        answer="cleared", source="reading",
        evidence="reads the tag file at boot"))
    assert res["ok"] is False
    assert "observable" in res["reason"]
    assert reckoning.read(str(tmp_path))["status"] == "absent"


def test_unexercised_clearance_resolves_to_not_proven(tmp_path):
    """An observable that nothing exercises resolves to not-proven rather
    than to cleared — reported, never silent."""
    res = reckoning.record(str(tmp_path), _row(
        answer="cleared", source="reading",
        evidence="reads the tag file at boot",
        observable="a reboot restores the recorded tag"))
    assert res["ok"] is True
    assert res["resolved_to"] == "not-proven"
    (row,) = reckoning.read(str(tmp_path))["reckonings"]
    assert row["answer"] == "not-proven"
    assert row["because"] == reckoning.NO_EXERCISER


def test_forbidden_parts_are_refused_per_answer(tmp_path):
    """moves-with-change is the change's own work — a clearance observable
    on it is a category error the grammar refuses."""
    res = reckoning.record(str(tmp_path), _row(observable="o"))
    assert res["ok"] is False
    res2 = reckoning.record(str(tmp_path), _row(
        answer="not-proven", observable="o", because="b",
        exercised_by="t.py::t"))
    assert res2["ok"] is False


def test_unknown_vocab_is_refused_never_recorded(tmp_path):
    for over in ({"answer": "fine"}, {"class": "script"},
                 {"source": "grep"}, {"change": "has space"},
                 {"disposition": "kept"}):
        res = reckoning.record(str(tmp_path), _row(**over))
        assert res["ok"] is False, f"accepted {over}"
    assert not os.path.exists(_record_path(tmp_path))


# --- upsert: one line per (change, consumer) --------------------------------

def test_record_upserts_one_line_per_change_and_consumer(tmp_path):
    reckoning.record(str(tmp_path), _row(
        what="a.sh", answer="not-proven", evidence="e", observable="o",
        because="b", when="2026-08-01"))
    reckoning.record(str(tmp_path), _row(
        what="a.sh", answer="cleared", evidence="e", observable="o",
        exercised_by="tests/t.py::t"))
    text = _text(tmp_path)
    assert text.count("what: a.sh") == 1
    (row,) = reckoning.read(str(tmp_path))["reckonings"]
    assert row["answer"] == "cleared"
    reckoning.record(str(tmp_path), _row(
        change="INC-105", what="a.sh", evidence="e"))
    assert len(reckoning.read(str(tmp_path))["reckonings"]) == 2


# --- the searched line: FR-104.8's structural statement ---------------------

def test_searched_line_derives_not_covered_never_accepts_it(tmp_path):
    res = reckoning.searched(str(tmp_path), _spec())
    assert res["ok"] is True
    sw = reckoning.read(str(tmp_path))["searched"]["INC-104"]
    assert sw["person"] == "answered"
    assert sw["name"] == "sha-tag"
    assert reckoning.NAMELESS_LIMIT in sw["not_covered"]
    res2 = reckoning.searched(str(tmp_path),
                              _spec(not_covered="all covered"))
    assert res2["ok"] is False
    assert "derived" in res2["reason"]


def test_not_covered_grows_with_what_did_not_run(tmp_path):
    reckoning.searched(str(tmp_path), _spec(
        declared="skipped", name_match="too-common", person="not-asked",
        name="db"))
    sw = reckoning.read(str(tmp_path))["searched"]["INC-104"]
    nc = sw["not_covered"]
    assert reckoning.NAMELESS_LIMIT in nc
    assert "too common" in nc
    assert "person was not asked" in nc
    assert "declared" in nc


def test_searched_person_states_are_distinguishable(tmp_path):
    """AC-104.5: answered, nothing-known and not-asked are three states,
    never merged."""
    for i, person in enumerate(reckoning.PERSON_STATES):
        reckoning.searched(str(tmp_path), _spec(change=f"C-{i}",
                                                person=person))
    sw = reckoning.read(str(tmp_path))["searched"]
    got = {sw[f"C-{i}"]["person"] for i in range(len(reckoning.PERSON_STATES))}
    assert got == set(reckoning.PERSON_STATES)
    assert set(reckoning.PERSON_STATES) == {"answered", "nothing-known",
                                            "not-asked"}


def test_no_completeness_sentence_can_be_written(tmp_path):
    """S-104.2 structurally: the module owns every sentence it writes and
    none of them claims completeness."""
    reckoning.searched(str(tmp_path), _spec())
    reckoning.record(str(tmp_path), _row(what="a.sh", evidence="e"))
    text = _text(tmp_path).lower()
    for phrase in ("complete", "all consumers", "everything that depends",
                   "nothing else"):
        assert phrase not in text


def test_searched_upserts_and_rederives_per_run(tmp_path):
    reckoning.searched(str(tmp_path), _spec(
        name_match="too-common", person="not-asked", name="db",
        when="2026-08-01"))
    reckoning.searched(str(tmp_path), _spec())
    assert _text(tmp_path).count("searched: change=INC-104") == 1
    sw = reckoning.read(str(tmp_path))["searched"]["INC-104"]
    assert "too common" not in sw["not_covered"]
    assert sw["date"] == "2026-08-03"


# --- has(): what the deep-clean catch-up reads (FR-104.9) -------------------

def test_has_distinguishes_reconciled_from_bare(tmp_path):
    assert reckoning.has(str(tmp_path), "INC-104")["recorded"] is False
    reckoning.searched(str(tmp_path), _spec(person="nothing-known", name="n"))
    got = reckoning.has(str(tmp_path), "INC-104")
    assert got["recorded"] is True
    assert got["reckonings"] == 0
    assert reckoning.has(str(tmp_path), "INC-999")["recorded"] is False


def test_zero_consumer_run_still_counts_as_reconciled(tmp_path):
    """A run that enumerated and found nothing writes its searched line and
    zero reckonings — that IS a record of having reconciled, distinct from
    never having run."""
    reckoning.searched(str(tmp_path), _spec(change="PATCH-007",
                                            person="nothing-known", name="n"))
    assert reckoning.has(str(tmp_path), "PATCH-007")["recorded"] is True


# --- the growing-log discipline ---------------------------------------------

def test_growing_log_archives_oldest_whole_changes(tmp_path, monkeypatch):
    """Contract § The growing-log discipline: past CAP typed lines the
    oldest whole changes move to docs/reckonings/archive-NNN.md — searched
    line and reckonings together, never split — so has() stays truthful
    for anything recent enough for the catch-up sweep to ask about."""
    monkeypatch.setattr(reckoning, "CAP", 4)
    for i in range(3):
        reckoning.searched(str(tmp_path), _spec(change=f"C-{i}",
                                                when=f"2026-08-0{i + 1}"))
    reckoning.record(str(tmp_path), _row(change="C-0", what="a.sh",
                                         evidence="e", when="2026-08-01"))
    reckoning.record(str(tmp_path), _row(change="C-2", what="b.sh",
                                         evidence="e", when="2026-08-03"))
    live = _text(tmp_path)
    assert "change=C-0" not in live
    assert "change=C-1" in live and "change=C-2" in live
    assert reckoning.has(str(tmp_path), "C-0")["recorded"] is False
    assert reckoning.has(str(tmp_path), "C-2")["recorded"] is True
    archive = os.path.join(str(tmp_path), "docs", "reckonings",
                           "archive-001.md")
    with open(archive, encoding="utf-8") as fh:
        arch = fh.read()
    assert "searched: change=C-0" in arch
    assert "what: a.sh" in arch
    assert "change=C-1" not in arch


# --- the empty case and malformed lines -------------------------------------

def test_absent_empty_and_recorded_are_three_states(tmp_path):
    assert reckoning.read(str(tmp_path))["status"] == "absent"
    reckoning.init(str(tmp_path))
    out = reckoning.read(str(tmp_path))
    assert out["status"] == "empty"
    assert out["reckonings"] == []
    assert reckoning.SENTINEL in _text(tmp_path)
    reckoning.record(str(tmp_path), _row(what="a.sh", evidence="e"))
    out = reckoning.read(str(tmp_path))
    assert out["status"] == "recorded"
    assert reckoning.SENTINEL not in _text(tmp_path)


def test_malformed_line_is_kept_and_flagged_never_dropped(tmp_path):
    reckoning.record(str(tmp_path), _row(what="a.sh", evidence="e"))
    text = _text(tmp_path)
    vandal = text.replace(
        "\n<!-- FRIDAY-RECKONINGS:END -->",
        "\nreckoning: garbled beyond parse\n<!-- FRIDAY-RECKONINGS:END -->")
    with open(_record_path(tmp_path), "w", encoding="utf-8") as fh:
        fh.write(vandal)
    out = reckoning.read(str(tmp_path))
    assert len(out["reckonings"]) == 1
    assert out["malformed"] == ["reckoning: garbled beyond parse"]
    reckoning.record(str(tmp_path), _row(what="b.sh", evidence="e"))
    assert "garbled beyond parse" in _text(tmp_path)


def test_prose_with_markers_parses_by_the_anchor_rule(tmp_path):
    """Like the parked ledger: free-prose fields may contain ` · ` and
    marker-like words; the parser peels segments rightmost-first, so the
    honest shape always round-trips."""
    reckoning.record(str(tmp_path), _row(
        what="the reboot routine", **{"class": "process"}, source="person",
        answer="not-proven",
        evidence="the operator's own answer — a habit · observable: none "
                 "written down",
        observable="the app is running after a reboot",
        because="production host"))
    (row,) = reckoning.read(str(tmp_path))["reckonings"]
    assert row["what"] == "the reboot routine"
    assert row["observable"] == "the app is running after a reboot"
    assert "habit" in row["evidence"]
