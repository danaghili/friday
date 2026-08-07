"""INC-107 FR-107.5/107.6/107.7 — the answered set (the durable half of KH-2).

The scan finds candidates; the reading and the PM answer them; THIS record is
why the next deep clean does not ask again. It is COMMITTED (docs/
LOOSE-DEFERRALS.md) because durability across clones is the whole point — a
substrate-side record is machine-local and the second clone would re-ask
everything the first one settled (D-1070, OQ-107.4).

What the tests insist on:

- **KH-2's three-way criterion, at unit level** (D9, OQ-107.2): a reformat of
  the file around the block changes nothing flattened — same identity, passed
  over; an edited comment is a changed decision — new identity, re-presented;
  a moved file re-presents (the accepted cost, chosen over collapsing two
  identical decisions in different files into one identity).
- **Recognition is counted, never silent** (FR-107.6): a run states how many
  previously-answered candidates it recognised and passed over.
- **The answer vocabulary is CLOSED** (FR-107.5's four): captured / dismissed /
  left-standing / already-homed; an unknown value is refused, and `captured`
  must name the PARK entry it landed as — a capture claim with no ledger id is
  a route back that does not exist.
- **The empty case is first-class**; a malformed line is kept and flagged,
  never dropped (house grammar rules).
- **The cap bar is read from the standards home, tool-owned default** (FR-107.7,
  OQ-107.3): the FRIDAY-LOOSE-DEFERRAL block in docs/standards/
  coding-standards.md, typed line `loose-deferral: presented <= N`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import loose_deferrals as ld  # noqa: E402


def _root(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    return str(root)


def _record_file(root):
    return open(os.path.join(root, "docs", "LOOSE-DEFERRALS.md"),
                encoding="utf-8").read()


# --- identity: KH-2's three-way criterion ------------------------------------------

def test_identity_survives_a_reformat_wrap(tmp_path):
    """The scan flattens block text; identity must flatten too, so the same
    decision re-wrapped across different comment lines is the same candidate."""
    a = ld.identity("src/route.ts", "liveness only,\nno DB ping.\nRevisit later.")
    b = ld.identity("src/route.ts", "liveness only, no DB ping. Revisit later.")
    assert a == b


def test_identity_survives_a_jsdoc_rewrap_that_adds_a_decoration_line(tmp_path):
    """Found live at the acceptance run: a block-comment rewrap that spills one
    more line adds one more ` * ` decoration token, and an identity computed on
    the raw flattened text treats that as an edited decision — the ordinary
    edit KH-2 says every cheap scheme breaks on. Decoration tokens carry no
    decision content; identity drops them."""
    a = ld.identity("src/route.ts",
                    "* INTENTIONALLY MINIMAL — process-alive only, no DB ping")
    b = ld.identity("src/route.ts",
                    "* INTENTIONALLY MINIMAL — process-alive\n * only, no DB ping")
    assert a == b


def test_an_edited_comment_is_a_new_identity(tmp_path):
    a = ld.identity("src/route.ts", "liveness only, no DB ping")
    b = ld.identity("src/route.ts", "liveness only, no DB ping — and no queue check")
    assert a != b


def test_a_moved_file_is_a_new_identity_the_accepted_cost(tmp_path):
    """D9: identity carries the path so two identical decisions in different
    files stay two decisions; the cost — a moved file re-presents — is the
    ruled trade, recorded here as behaviour, not as an accident."""
    a = ld.identity("src/old.ts", "liveness only, no DB ping")
    b = ld.identity("src/new.ts", "liveness only, no DB ping")
    assert a != b


# --- recording answers ---------------------------------------------------------------

def test_first_record_creates_the_file_and_round_trips(tmp_path):
    root = _root(tmp_path)
    res = ld.record(root, file="src/health.py",
                    text="liveness only, no DB ping",
                    answer="dismissed", detail="import-placement junk",
                    when="2026-08-04")
    assert res["id"] == ld.identity("src/health.py", "liveness only, no DB ping")
    (entry,) = ld.entries(root)
    assert entry["malformed"] is False
    assert entry["id"] == res["id"]
    assert entry["date"] == "2026-08-04"
    assert entry["answer"] == "dismissed"
    assert entry["detail"] == "import-placement junk"
    assert entry["file"] == "src/health.py"


def test_no_file_means_no_entries_and_no_crash(tmp_path):
    assert ld.entries(_root(tmp_path)) == []


def test_unknown_answer_is_refused(tmp_path):
    root = _root(tmp_path)
    try:
        ld.record(root, file="a.py", text="x", answer="maybe", detail="d")
        raised = False
    except ValueError as exc:
        raised = True
        assert "answer" in str(exc)
    assert raised and ld.entries(root) == []


def test_captured_requires_the_park_id_in_detail(tmp_path):
    """A capture answer that names no PARK entry claims a route back that
    does not exist — the whole failure class this increment ends."""
    root = _root(tmp_path)
    try:
        ld.record(root, file="a.py", text="x", answer="captured",
                  detail="parked it somewhere")
        raised = False
    except ValueError as exc:
        raised = True
        assert "PARK-" in str(exc)
    assert raised
    ld.record(root, file="a.py", text="x", answer="captured",
              detail="PARK-013 — revisit at first real incident")
    assert len(ld.entries(root)) == 1


def test_empty_detail_is_refused(tmp_path):
    root = _root(tmp_path)
    for detail in ("", "   "):
        try:
            ld.record(root, file="a.py", text="x", answer="dismissed",
                      detail=detail)
            assert False, "accepted empty detail"
        except ValueError:
            pass


def test_detail_containing_the_grammar_glyphs_round_trips(tmp_path):
    root = _root(tmp_path)
    tricky = "cites README · file: layout — but schedules nothing"
    ld.record(root, file="src/webhook.ts", text="stuck-sending is manual",
              answer="left-standing", detail=tricky, when="2026-08-04")
    (entry,) = ld.entries(root)
    assert entry["detail"] == tricky
    assert entry["file"] == "src/webhook.ts"


def test_a_malformed_line_is_kept_and_flagged_never_dropped(tmp_path):
    root = _root(tmp_path)
    ld.record(root, file="a.py", text="x", answer="dismissed", detail="junk",
              when="2026-08-04")
    path = os.path.join(root, "docs", "LOOSE-DEFERRALS.md")
    text = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(text.replace(
        "<!-- FRIDAY-ANSWERED:END -->",
        "answered: deadbeef0000 not-a-real-line\n<!-- FRIDAY-ANSWERED:END -->"))
    all_entries = ld.entries(root)
    assert len(all_entries) == 2
    bad = [e for e in all_entries if e["malformed"]]
    assert len(bad) == 1 and "deadbeef0000" in bad[0]["raw"]


# --- recognition: the no-re-ask mechanism -------------------------------------------

def test_recognize_splits_new_from_answered_and_counts(tmp_path):
    root = _root(tmp_path)
    ld.record(root, file="src/a.ts", text="known gap: no focus trap",
              answer="dismissed", detail="junk", when="2026-08-04")
    ld.record(root, file="src/b.ts", text="deferred to a later version",
              answer="left-standing", detail="waiting on v2", when="2026-08-04")
    candidates = [
        {"file": "src/a.ts", "text": "known gap: no focus trap"},
        {"file": "src/b.ts", "text": "deferred to a later version"},
        {"file": "src/c.ts", "text": "TODO: rotate the key post-launch"},
    ]
    out = ld.recognize(root, candidates)
    assert out["recognized"] == 2
    assert [c["file"] for c in out["new"]] == ["src/c.ts"]


def test_recognize_re_presents_an_edited_block(tmp_path):
    root = _root(tmp_path)
    ld.record(root, file="src/a.ts", text="known gap: no focus trap",
              answer="dismissed", detail="junk", when="2026-08-04")
    out = ld.recognize(root, [
        {"file": "src/a.ts", "text": "known gap: no focus trap or escape key"}])
    assert out["recognized"] == 0 and len(out["new"]) == 1


# --- the cap bar (FR-107.7 / OQ-107.3) -----------------------------------------------

def test_cap_default_when_no_standards_file(tmp_path):
    assert ld.presented_cap(_root(tmp_path)) == 25


def test_cap_read_from_the_declared_bar(tmp_path):
    root = _root(tmp_path)
    std = os.path.join(root, "docs", "standards")
    os.makedirs(std)
    open(os.path.join(std, "coding-standards.md"), "w", encoding="utf-8").write(
        "# Standards\n\n<!-- FRIDAY-LOOSE-DEFERRAL:BEGIN -->\n"
        "loose-deferral: presented <= 7\n"
        "<!-- FRIDAY-LOOSE-DEFERRAL:END -->\n")
    assert ld.presented_cap(root) == 7


def test_cap_garbage_line_falls_back_to_default(tmp_path):
    root = _root(tmp_path)
    std = os.path.join(root, "docs", "standards")
    os.makedirs(std)
    open(os.path.join(std, "coding-standards.md"), "w", encoding="utf-8").write(
        "<!-- FRIDAY-LOOSE-DEFERRAL:BEGIN -->\n"
        "loose-deferral: presented <= minus-four\n"
        "<!-- FRIDAY-LOOSE-DEFERRAL:END -->\n")
    assert ld.presented_cap(root) == 25


# --- CLI -------------------------------------------------------------------------------

def test_cli_record_prints_the_id(tmp_path, capsys):
    root = _root(tmp_path)
    rc = ld.main(["record", "--root", root, "--file", "src/a.ts",
                  "--text", "known gap here", "--answer", "dismissed",
                  "--detail", "junk shape: english phrase"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["id"] == ld.identity("src/a.ts", "known gap here")


def test_cli_recognize_reads_scan_json(tmp_path, capsys):
    root = _root(tmp_path)
    ld.record(root, file="src/a.ts", text="known gap here",
              answer="dismissed", detail="junk", when="2026-08-04")
    scan = tmp_path / "scan.json"
    scan.write_text(json.dumps({"candidates": [
        {"file": "src/a.ts", "text": "known gap here"},
        {"file": "src/b.ts", "text": "TODO: later"}]}), encoding="utf-8")
    rc = ld.main(["recognize", "--root", root, "--scan", str(scan)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["recognized"] == 1 and len(out["new"]) == 1
