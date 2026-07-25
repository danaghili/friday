"""Compaction-package substrate verbs (INC-001 FR-1.3, FR-1.2/FR-1.4 write
semantics; contract: docs/contracts/compaction-package.md).

The single-writer rules under test: every summary lands as an append-only
timestamped generation in the authoring agent's drawer; the current pointer
moves ONLY on a parsed self-ID header; an unattributed summary can never
touch any current pointer; nothing is ever overwritten; the empty case (no
compaction yet) is a valid state every reader accepts.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import friday_substrate as fs  # noqa: E402


SID = "sess-abc123"


def _summary(agent="friday-lead", scope="INC-001 build", body="did things\n"):
    return f"handoff-of: {agent} — {scope}\n\n{body}"


# --- the self-ID header grammar (FR-1.4) -------------------------------------------

def test_header_parses_slug():
    assert fs.parse_handoff_header(_summary()) == "friday-lead"


def test_header_without_scope_still_parses():
    assert fs.parse_handoff_header("handoff-of: friday-tester\nrest\n") == "friday-tester"


def test_missing_or_garbled_header_is_none():
    assert fs.parse_handoff_header("This conversation covered...\n") is None
    assert fs.parse_handoff_header("handoff-of: Bad Slug!\n") is None
    assert fs.parse_handoff_header("") is None


# --- summarizer envelope (fixture-run finding): the raw compact_summary payload
# arrives wrapped in <analysis>…</analysis><summary>…</summary>; the header
# lives on the first line INSIDE the summary block ---------------------------------

def _enveloped(agent="friday-lead", scope="widget refactor"):
    return ("<analysis>\nsummarizer scratch reasoning, never part of the "
            "handoff.\n</analysis>\n\n<summary>\n"
            f"handoff-of: {agent} — {scope}\n\n1. Current objective\nkeep "
            "going\n</summary>")


def test_header_parses_through_summarizer_envelope():
    assert fs.parse_handoff_header(_enveloped()) == "friday-lead"


def test_header_after_leading_blank_lines_parses():
    assert fs.parse_handoff_header("\n\nhandoff-of: friday-lead — x\nrest\n") == "friday-lead"


def test_enveloped_summary_attributes_and_current_holds_stripped_body(tmp_path):
    root = str(tmp_path)
    raw = _enveloped()
    res = fs.compaction_file_summary(root, session_id=SID, summary=raw)
    assert res["attributed"] and res["agent"] == "friday-lead"
    # the generation keeps the RAW payload — the complete record
    gen = os.path.join(fs.friday_dir(root), res["generation"])
    with open(gen, encoding="utf-8") as fh:
        assert fh.read() == raw
    # current.md is the handoff itself — envelope and scratch stripped
    cur = os.path.join(fs.friday_dir(root), "compaction", SID,
                       "friday-lead", "current.md")
    with open(cur, encoding="utf-8") as fh:
        text = fh.read()
    assert text.startswith("handoff-of: friday-lead")
    assert "<analysis>" not in text and "<summary>" not in text


def test_enveloped_summary_without_header_stays_unattributed(tmp_path):
    root = str(tmp_path)
    res = fs.compaction_file_summary(
        root, session_id=SID,
        summary="<analysis>\nscratch\n</analysis>\n<summary>\nAn unguided "
                "summary.\n</summary>")
    assert not res["attributed"] and res["agent"] == fs.COMPACTION_UNATTRIBUTED


# --- the reserved slug (harden-skeptic finding): `unattributed` is grammar-valid,
# so without a guard a summary could claim it and grow a current.md inside the
# shared fallback drawer — the pointer the contract forbids ------------------------

def test_reserved_slug_never_attributes(tmp_path):
    root = str(tmp_path)
    assert fs.parse_handoff_header(
        "handoff-of: unattributed — pretending to be the fallback drawer\n") is None
    res = fs.compaction_file_summary(
        root, session_id=SID,
        summary="handoff-of: unattributed — pretending to be the fallback "
                "drawer\n\nbody\n")
    assert not res["attributed"] and res["agent"] == fs.COMPACTION_UNATTRIBUTED
    assert not os.path.exists(os.path.join(
        fs.friday_dir(root), "compaction", SID,
        fs.COMPACTION_UNATTRIBUTED, "current.md"))


def test_reserved_agent_refused_for_layers(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        fs.compaction_write_layer(str(tmp_path), session_id=SID,
                                  agent=fs.COMPACTION_UNATTRIBUTED,
                                  layer="mission", text="x")


# --- filing (FR-1.2): archive always, current only when attributed ----------------

def test_attributed_summary_archives_and_updates_current(tmp_path):
    res = fs.compaction_file_summary(str(tmp_path), session_id=SID,
                                     summary=_summary())
    assert res["attributed"] and res["agent"] == "friday-lead"
    gen = os.path.join(fs.friday_dir(str(tmp_path)), res["generation"])
    assert os.path.isfile(gen)
    cur = os.path.join(fs.friday_dir(str(tmp_path)), "compaction", SID,
                       "friday-lead", "current.md")
    with open(cur, encoding="utf-8") as fh:
        assert fh.read() == _summary()


def test_unattributed_summary_archives_but_touches_no_current(tmp_path):
    root = str(tmp_path)
    fs.compaction_file_summary(root, session_id=SID, summary=_summary())
    res = fs.compaction_file_summary(root, session_id=SID,
                                     summary="An unguided summary.\n")
    assert not res["attributed"] and res["agent"] == fs.COMPACTION_UNATTRIBUTED
    assert os.path.isfile(os.path.join(fs.friday_dir(root), res["generation"]))
    # the orchestrator's current is untouched
    cur = os.path.join(fs.friday_dir(root), "compaction", SID,
                       "friday-lead", "current.md")
    with open(cur, encoding="utf-8") as fh:
        assert fh.read() == _summary()
    # and the unattributed drawer never grows a current pointer
    assert not os.path.exists(os.path.join(
        fs.friday_dir(root), "compaction", SID,
        fs.COMPACTION_UNATTRIBUTED, "current.md"))


def test_helper_filing_never_touches_another_drawer(tmp_path):
    root = str(tmp_path)
    fs.compaction_file_summary(root, session_id=SID, summary=_summary())
    fs.compaction_file_summary(root, session_id=SID,
                               summary=_summary(agent="friday-tester", scope="unit run", body="tested\n"))
    cur = os.path.join(fs.friday_dir(root), "compaction", SID,
                       "friday-lead", "current.md")
    with open(cur, encoding="utf-8") as fh:
        assert "friday-lead" in fh.readline()


def test_archive_is_append_only_two_filings_two_generations(tmp_path):
    root = str(tmp_path)
    a = fs.compaction_file_summary(root, session_id=SID, summary=_summary(body="one\n"),
                                   ts="2026-07-15T10:00:00Z")
    b = fs.compaction_file_summary(root, session_id=SID, summary=_summary(body="two\n"),
                                   ts="2026-07-15T10:00:00Z")  # same ts: still two files
    assert a["generation"] != b["generation"]
    gen_dir = os.path.join(fs.friday_dir(root), "compaction", SID,
                           "friday-lead", "generations")
    assert len(os.listdir(gen_dir)) == 2


# --- layers (FR-1.5 / FR-1.6) -------------------------------------------------------

def test_layers_write_and_package_read(tmp_path):
    root = str(tmp_path)
    fs.compaction_write_layer(root, session_id=SID, agent="friday-lead",
                              layer="mission", text="ask verbatim; lane; oracle\n")
    fs.compaction_write_layer(root, session_id=SID, agent="friday-lead",
                              layer="orientation", text="learned: X matters\n")
    fs.compaction_file_summary(root, session_id=SID, summary=_summary())
    pkg = fs.compaction_read_package(root, session_id=SID, agent="friday-lead")
    assert pkg["mission"].startswith("ask verbatim")
    assert pkg["orientation"].startswith("learned:")
    assert pkg["current"] == _summary()
    assert pkg["generations"] == 1


def test_unknown_layer_refused(tmp_path):
    try:
        fs.compaction_write_layer(str(tmp_path), session_id=SID,
                                  agent="friday-lead", layer="diary", text="x")
        assert False, "unknown layer must raise"
    except ValueError:
        pass


# --- the empty case (FR-1.3) --------------------------------------------------------

def test_empty_case_reads_clean(tmp_path):
    pkg = fs.compaction_read_package(str(tmp_path), session_id="never-ran",
                                     agent="friday-lead")
    assert pkg == {"mission": None, "orientation": None,
                   "current": None, "generations": 0}


# --- hygiene ------------------------------------------------------------------------

def test_session_and_agent_are_sanitized(tmp_path):
    root = str(tmp_path)
    fs.compaction_write_layer(root, session_id="../evil", agent="friday-lead",
                              layer="mission", text="m\n")
    base = os.path.join(fs.friday_dir(root), "compaction")
    assert os.path.isdir(base)
    assert not os.path.exists(os.path.join(os.path.dirname(fs.friday_dir(root)), "evil"))
    for d in os.listdir(base):
        assert "/" not in d and ".." not in d


def test_filing_emits_journal_event(tmp_path):
    root = str(tmp_path)
    fs.compaction_file_summary(root, session_id=SID, summary=_summary())
    journal = os.path.join(fs.friday_dir(root), "journal.jsonl")
    with open(journal, encoding="utf-8") as fh:
        assert any('"compaction-filed"' in ln for ln in fh)
