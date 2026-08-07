"""INC-105 FR-105.4 / OQ-105.2 — friday's shipped baseline catalog
(docs/conformance-baseline.md).

The catalog is a deliverable, and a deliverable of typed lines can rot like
any record: a malformed line, a pattern that does not compile, or a
switch-on condition outside the closed vocabulary would surface as
could-not-run noise on every project friday manages. This guard runs the
REAL shipped catalog through the real sweep and requires every invariant to
land as itself — engaged, switched-off, or out-of-reach — never as a
malformed or unrunnable line. Grammar home: docs/contracts/
conformance-envelope.md § The baseline line grammar (D4, D5, KH-6).
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import conformance_sweep as sweep_mod  # noqa: E402

CATALOG = os.path.join(os.path.dirname(__file__), "..", "docs",
                       "conformance-baseline.md")


def _shipped_ids():
    with open(CATALOG, encoding="utf-8") as fh:
        text = fh.read()
    body = text.split("FRIDAY-BASELINE:BEGIN -->")[1].split(
        "<!-- FRIDAY-BASELINE:END")[0]
    return re.findall(r"^baseline: (\S+)", body, re.M), body


def test_every_shipped_invariant_lands_as_itself_never_malformed(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    ids, _ = _shipped_ids()
    assert ids, "the shipped catalog carries no baseline lines"
    out = sweep_mod.sweep(str(tmp_path), baseline_path=CATALOG)
    assert out["could_not_run"] == []
    landed = ({c["id"] for c in out["clean_checks"]}
              | {f["check"] for f in out["findings"]}
              | {s["id"] for s in out["switched_off"]}
              | {o["id"] for o in out["out_of_reach"]})
    assert landed == set(ids)


def test_ids_unique_and_every_provenance_mark_well_formed():
    ids, body = _shipped_ids()
    assert len(set(ids)) == len(ids)
    marks = re.findall(r"provenance: (scarred — .+?|unscarred[^·\n]*)(?: ·|$)",
                       body, re.M)
    assert len(marks) == len(ids)
    for mark in marks:
        if mark.startswith("scarred"):
            named = mark.split(" — ", 1)[1]
            assert named.strip(), "a scarred mark must name its finding"
        else:
            assert mark.startswith("unscarred")


def test_the_scarred_marks_name_the_audits_own_findings():
    """KH-6's readable tail: the evidence-backed rules say which finding, so
    the demotion question stays answerable from the list itself."""
    _, body = _shipped_ids()
    scarred = [ln for ln in body.splitlines() if "scarred — " in ln
               and "unscarred" not in ln.split("provenance:")[1].split("·")[0]]
    joined = "\n".join(scarred)
    for finding in ("SCA-001", "DEP-001", "ARC-004"):
        assert finding in joined


def _reader_relative_pattern():
    _, body = _shipped_ids()
    for ln in body.splitlines():
        if ln.startswith("baseline: reader-relative-referent "):
            return re.compile(ln.rsplit("pattern: ", 1)[1].strip())
    raise AssertionError("reader-relative-referent line missing from catalog")


def test_reader_relative_pattern_sees_the_possessive_form():
    """INC-110 110.b red run: the live surfaces the rewrite targets say
    "this machine's range" — the mention-exemption's trailing quote guard
    must not read the possessive apostrophe as a closing quote, or the
    invariant is blind to the exact sentences that prove it was needed."""
    rx = _reader_relative_pattern()
    for use in ("ids allocate inside this machine's range",
                "counts only ids inside this clone's lane",
                "came out in the other machine's lane",
                "on this machine the base is 200"):
        assert rx.search(use), use


def test_reader_relative_pattern_still_exempts_mentions_by_property():
    """D6: a backticked or quoted mention asserts no machine fact; a longer
    word sharing the prefix is not the phrase."""
    rx = _reader_relative_pattern()
    for mention in ("the phrase `this machine` is banned",
                    'say "this machine" and the referent rebinds',
                    "the ban names 'this clone' explicitly",
                    "this machinery hums along"):
        assert not rx.search(mention), mention


def test_sweep_convicts_the_possessive_sentence_end_to_end(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "notes.md").write_text(
        "New ids allocate inside this machine's range.\n", encoding="utf-8")
    out = sweep_mod.sweep(str(tmp_path), baseline_path=CATALOG)
    hits = [f for f in out["findings"]
            if f["check"] == "reader-relative-referent"]
    assert hits and hits[0]["path"] == "notes.md"
