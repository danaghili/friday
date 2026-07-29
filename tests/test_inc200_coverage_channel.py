"""INC-200 FR-200.10 / FR-200.11 / AC-200.9 / AC-200.10 / KH-2 — the coverage
ledger's verifier channel, test-first.

The defect (D7): the ledger's header claimed every `implemented` line was
"re-verified directly by this tester … not accepted on the build's
self-report", but every increment since the original harden pass appends its
lines through the feature lane, where the LEAD writes them — the same context
that built the slice. A growing share of a ledger whose whole promise is
"not the builder's self-report" IS the builder's self-report, filed under the
tester's name.

The fix is the two-channel pattern DECISIONS.md and STANDARDS-DEVIATIONS.md
already use, applied to a third record: each line records its verifier, and
**an unmarked line reads as lead-authored — the weaker value** — so 265
existing lines need no archaeology and nothing can over-claim by omission.

KH-2 / AC-200.9: `verify_coverage.py` is a floor primitive that gates
requirement closure for every project. The widening is ADDITIVE-ONLY.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import verify_coverage as vc  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ledger(*lines):
    body = "\n".join(lines)
    return ("# Coverage\n\n<!-- FRIDAY-DISPOSITIONS:BEGIN -->\n"
            f"{body}\n<!-- FRIDAY-DISPOSITIONS:END -->\n")


# --- AC-200.10: omission can never produce the stronger reading ------------------------

def test_unmarked_line_reads_as_lead_authored():
    """The load-bearing default. All 265 existing lines are this shape."""
    parsed, errors = vc.parse_ledger(_ledger(
        "disposition: FR-1 implemented — a real file read"))
    assert errors == []
    assert parsed["FR-1"]["verifier"] == "lead-authored"


def test_marked_independently_tested_reads_as_such():
    parsed, errors = vc.parse_ledger(_ledger(
        "disposition: FR-2 implemented (independently-tested) — tester re-ran the suite"))
    assert errors == []
    assert parsed["FR-2"]["verifier"] == "independently-tested"
    assert parsed["FR-2"]["state"] == "implemented"
    assert parsed["FR-2"]["note"] == "tester re-ran the suite"


def test_explicitly_marked_lead_authored_round_trips():
    parsed, errors = vc.parse_ledger(_ledger(
        "disposition: FR-3 implemented (lead-authored) — feature lane appended it"))
    assert errors == []
    assert parsed["FR-3"]["verifier"] == "lead-authored"


def test_unknown_channel_is_an_error_never_silently_dropped():
    """A malformed channel must not read as the stronger value, and must not
    vanish — the same discipline the envelope grammar holds."""
    parsed, errors = vc.parse_ledger(_ledger(
        "disposition: FR-4 implemented (rigorously-vibed) — nope"))
    assert errors, "an unknown verifier channel must be reported"
    assert "FR-4" not in parsed or parsed["FR-4"]["verifier"] == "lead-authored"


# --- AC-200.9 / KH-2: additive-only, existing behavior unchanged -----------------------

def _tree(tmp_path, disposition_line):
    """A minimal real oracle+ledger pair — check() reads files, and the floor
    primitive's signature stays untouched by these tests (KH-2)."""
    (tmp_path / "docs" / "reviews").mkdir(parents=True)
    (tmp_path / "docs" / "TECHNICAL_SOW.md").write_text(
        "# tsow\n\n- **FR-5** — the one requirement\n", encoding="utf-8")
    (tmp_path / "docs" / "reviews" / "coverage.md").write_text(
        _ledger(disposition_line), encoding="utf-8")
    return str(tmp_path)


def test_existing_verdicts_are_unchanged_deferred_still_needs_a_decision(tmp_path):
    """The A2 rule (a deferred line must cite a pm-ratified D-NNNN) is untouched
    by the widening — proven marked and unmarked."""
    unmarked = vc.check(_tree(tmp_path / "a", "disposition: FR-5 deferred — just because"))
    assert not unmarked["ok"], "deferral without a decision must still gap"
    marked = vc.check(_tree(
        tmp_path / "b",
        "disposition: FR-5 deferred (independently-tested) — just because"))
    assert not marked["ok"], "the channel must not excuse a decision-less deferral"
    cited = vc.check(_tree(tmp_path / "c",
                           "disposition: FR-5 deferred — see D-0119"))
    assert cited["ok"], cited["summary"]


def test_implemented_closes_the_same_way_marked_or_not(tmp_path):
    for i, line in enumerate(("disposition: FR-5 implemented — evidence",
                              "disposition: FR-5 implemented (independently-tested) — evidence",
                              "disposition: FR-5 implemented (lead-authored) — evidence")):
        res = vc.check(_tree(tmp_path / f"i{i}", line))
        assert res["ok"], f"{line} → {res['summary']}"


def test_empty_block_is_still_the_defined_empty_case():
    parsed, errors = vc.parse_ledger(
        "# Coverage\n\n<!-- FRIDAY-DISPOSITIONS:BEGIN -->\n"
        "<!-- FRIDAY-DISPOSITIONS:END -->\n")
    assert parsed == {} and errors == []


def test_real_tree_coverage_verdict_still_holds():
    """The floor primitive still gates closure over the real oracles."""
    res = vc.check(REPO)
    assert "summary" in res and isinstance(res["ok"], bool)
