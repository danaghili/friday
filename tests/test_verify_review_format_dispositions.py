"""Regression: verify_review_format.py's FRIDAY-DISPOSITIONS grammar must stay
in sync with verify_coverage.py's (INC-200 FR-200.10 widened it to accept an
optional `(verifier)` group -- `independently-tested` | `lead-authored` --
between the implemented|deferred keyword and the em dash).

Found during the INC-200 independent hardening pass: verify_coverage.py's
`_DISPO_RE` was widened for the verifier-channel marker, but
verify_review_format.py's OWN copy of the same regex family was never
updated to match. The two are meant to accept exactly the same disposition
line shape -- one gates requirement closure (verify_coverage.py), the other
gates the docs/reviews/ artifact's format (verify_review_format.py, wired as
a PostToolUse bounce in hooks/review_format_sentinel.py). Left divergent,
EVERY disposition line carrying a verifier-channel marker -- which is to say
every one of INC-200's own 35 lines, and any future line written under
FR-200.10's own grammar -- fails `_check_dispositions`'s D2 check as
"non-parsing", which arms the Stop-gate's `review-format-invalid` sentinel on
the very next write to docs/reviews/coverage.md and can never be cleared by
editing the ledger's CONTENT, since the failure is in the checker, not the
document. This test pins the fix: the two `_DISPO_RE` patterns accept the
same set of lines.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import verify_coverage as vc          # noqa: E402
import verify_review_format as vrf    # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _doc(*lines):
    body = "\n".join(lines)
    return ("# Coverage\n\n<!-- FRIDAY-DISPOSITIONS:BEGIN -->\n"
            f"{body}\n<!-- FRIDAY-DISPOSITIONS:END -->\n")


def test_a_verifier_marked_line_parses_under_both_checkers_identically():
    """The exact shape FR-200.10 introduced: verify_coverage.py already
    accepts it (proven by tests/test_inc200_coverage_channel.py); this
    asserts verify_review_format.py's independent copy of the grammar
    accepts the same line, not a stricter one."""
    for line in ("FR-1 implemented (lead-authored) — a real file read",
                 "FR-2 implemented (independently-tested) — tester re-ran the suite",
                 "FR-3 deferred (lead-authored) — see D-0001",
                 "FR-4 implemented — no verifier marker at all (the 265 pre-INC-200 lines)"):
        assert vc._DISPO_RE.match(line), f"verify_coverage.py rejects: {line!r}"
        assert vrf._DISPO_RE.match(line), (
            f"verify_review_format.py rejects a line verify_coverage.py "
            f"accepts: {line!r} -- the two disposition grammars have drifted")


