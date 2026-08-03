"""INC-004 FR-4.1 / AC-4.1 / AC-4.4: the candidate register is a typed-line
grammar with a tested empty case; the shipped register carries the reframe's
verdicts (survey cluster stays-LLM) and the promoted tool's discoverability
line. Grammar strictness is also the prose guard: every non-blank line inside
the block must parse, so conversation prose cannot ride in the machine block.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import taglines  # noqa: E402

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(BUILD_ROOT, "proposals", "_recurrence-candidates.md")

CANDIDATE_RE = re.compile(
    r"^candidate: [a-z0-9][a-z0-9-]* — verdict=(scriptify|bundle|stays-LLM|covered|below-bar|deferred)"
    r" — occurrences=\d+ — danger=(high|medium|low) — .+$")
PROMOTED_RE = re.compile(r"^promoted: [a-z0-9][a-z0-9-]* → tools/[a-z0-9_]+\.py — replaces: .+$")
# INC-208 D9: one register, one rule — a `bundle` verdict earns a text-file
# outcome line exactly as `scriptify` earns a tool one.
BUNDLED_RE = re.compile(r"^bundled: [a-z0-9][a-z0-9-]* → [\w./-]+\.md — replaces: .+$")


def read_block(text):
    return taglines.block_lines(text, "FRIDAY-CANDIDATES")


def test_bundled_line_rejects_a_tool_path():
    """Grammar strictness both ways: a `bundled:` line names a text file, so a
    tool path fails the shape rather than quietly recording the wrong outcome."""
    assert not BUNDLED_RE.match(
        "bundled: some-slug → tools/thing.py — replaces: a hand-composition")


def test_empty_case_is_the_none_yet_sentinel():
    empty = "# x\n\n<!-- FRIDAY-CANDIDATES:BEGIN -->\n_None yet._\n<!-- FRIDAY-CANDIDATES:END -->\n"
    lines = read_block(empty)
    assert lines == ["_None yet._"]
    # the sentinel is the ONLY non-grammar line the block may hold, and only alone
    assert not CANDIDATE_RE.match(lines[0]) and not PROMOTED_RE.match(lines[0])
