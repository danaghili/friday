"""INC-008 FR-8.1 / AC-8.3 / KH-2 — the additive maintainability claim grammar.

Test-first. A project declares its maintainability bars as a NEW typed claim
type (`maintainability: <metric> <= <N>[%]`) over a closed metric vocabulary,
homed in a `FRIDAY-MAINTAINABILITY` block inside its coding-standards file —
NOT in CLAUDE.md's FRIDAY-CLAIMS. The change is additive-only:

- `taglines.py` gains one closed vocabulary + a bar parser; every existing
  primitive is untouched.
- `verify_claims.py` gains a well-formedness check for the new type; the
  CLAUDE.md CLAIM_TYPES vocabulary and its verdicts are byte-unchanged.
- The empty case is first-class: an ABSENT or PRESENT-EMPTY maintainability
  block is a VALID "no bars declared" outcome (the non-adopter invariant,
  FR-8.13) — never an error.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import taglines  # noqa: E402
import verify_claims as vc  # noqa: E402


# --- the closed metric vocabulary + the bar parser (taglines) ------------------

def test_metric_vocabulary_is_closed_and_ordered():
    assert taglines.MAINTAINABILITY_METRICS == (
        "complexity", "file-size", "function-size",
        "param-count", "nesting-depth", "duplication")


def test_parse_bar_valid_forms():
    assert taglines.parse_maintainability_bar("complexity <= 15") == {
        "metric": "complexity", "limit": 15, "pct": False}
    assert taglines.parse_maintainability_bar("duplication <= 5%") == {
        "metric": "duplication", "limit": 5, "pct": True}
    assert taglines.parse_maintainability_bar("nesting-depth <= 4") == {
        "metric": "nesting-depth", "limit": 4, "pct": False}


def test_parse_bar_rejects_garbage():
    assert taglines.parse_maintainability_bar("complexity < 15") is None      # wrong comparator
    assert taglines.parse_maintainability_bar("cyclomatic <= 15") is None     # unknown metric
    assert taglines.parse_maintainability_bar("complexity <= big") is None    # non-numeric
    assert taglines.parse_maintainability_bar("complexity <= -3") is None     # negative
    assert taglines.parse_maintainability_bar("") is None


# --- well-formedness of a declared block (verify_claims) ------------------------

_VALID = (
    "# Coding standards\n\n"
    "<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
    "maintainability: complexity <= 15\n"
    "maintainability: function-size <= 60\n"
    "maintainability: duplication <= 5%\n"
    "<!-- FRIDAY-MAINTAINABILITY:END -->\n"
)


def test_well_formed_valid_block():
    ok, errs = vc.well_formed_maintainability(_VALID)
    assert ok and errs == []


def test_absent_block_is_valid_non_adopter():
    # the load-bearing invariant: no bars declared -> tolerated, zero change
    ok, errs = vc.well_formed_maintainability("# a standards doc with no bars block\n")
    assert ok and errs == []


def test_present_empty_block_is_valid():
    empty = ("<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
             "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    ok, errs = vc.well_formed_maintainability(empty)
    assert ok and errs == []


def test_unknown_metric_is_malformed():
    bad = ("<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
           "maintainability: cyclomatic <= 15\n"
           "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    ok, errs = vc.well_formed_maintainability(bad)
    assert not ok and errs


def test_duplicate_metric_is_malformed():
    dup = ("<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
           "maintainability: complexity <= 15\n"
           "maintainability: complexity <= 20\n"
           "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    ok, errs = vc.well_formed_maintainability(dup)
    assert not ok and errs


def test_bars_helper_distinguishes_absent_from_empty():
    # None = block absent (non-adopter); [] = present but empty; both valid upstream
    assert vc.maintainability_bars("no block here\n") is None
    empty = ("<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
             "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    assert vc.maintainability_bars(empty) == []


# --- the additive-only guarantee (AC-8.3 / KH-2) -------------------------------

def test_arm_switch_defaults_to_warn_and_reads_block():
    # the one per-project strictness switch (D2), co-homed with the bars
    assert vc.maintainability_arm("# no block\n") == "warn"          # absent -> warn-first
    assert vc.maintainability_arm(_VALID) == "warn"                  # bars but no arm line
    armed = _VALID.replace("maintainability: complexity <= 15\n",
                           "maintainability: complexity <= 15\narm: block\n")
    assert vc.maintainability_arm(armed) == "block"


def test_arm_line_does_not_count_as_a_bar_and_bad_arm_is_malformed():
    armed = ("<!-- FRIDAY-MAINTAINABILITY:BEGIN -->\n"
             "arm: block\n"
             "maintainability: complexity <= 15\n"
             "<!-- FRIDAY-MAINTAINABILITY:END -->\n")
    ok, errs = vc.well_formed_maintainability(armed)
    assert ok and errs == []                                        # arm is valid, not a bar
    bad = armed.replace("arm: block", "arm: sometimes")
    ok2, errs2 = vc.well_formed_maintainability(bad)
    assert not ok2 and errs2                                        # unknown arm value


def test_existing_claim_vocabulary_is_untouched():
    # The CLAUDE.md FRIDAY-CLAIMS vocabulary must not gain 'maintainability' —
    # the bars live in coding-standards.md, a different file and block.
    assert vc.CLAIM_TYPES == ("stack", "ci-gate", "non-goal", "threshold",
                              "provenance", "world")
    assert "maintainability" not in vc.CLAIM_TYPES
