"""INC-202 KH-1 / FR-202.2 / AC-202.1 — the make-or-break grammar measurement.

D3's whole "this is not a new convention" premise is one claim: a proposal's
`---`-fenced header block of lowercase `key: value` lines is SIMULTANEOUSLY
well-formed frontmatter and the house typed-tag-line grammar, read by the
existing `tools/taglines.py` with no new parser. This file is the measurement
the increment mandates before any consumer is written — if these tests cannot
pass, the build stops and the header design goes back to the PM. The field
spelling pinned here IS the OQ-202.6 resolution (recorded in DECISIONS.md):
`status` (the stage word, identical to the folder name so the checker's
comparison is a string equality) · `captured` · `note` · `increment` ·
`validated` · `reason`.
"""
import taglines

# A real header in every lifecycle state at once — the superset a validated,
# once-bounced proposal would carry. Values deliberately include the shapes
# that could break a lazy grammar: em-dashes, dates, path pointers, a colon
# inside a value, and an id containing uppercase (in the VALUE, never the key).
HEADER = """---
status: 04-validated
captured: 2026-07-30
note: built 2026-07-29; bounced once — validation failed on the first target
increment: INC-202
validated: 2026-07-30 — close ran the mover live: docs/trails/INC-202.md
reason: first target lacked a real deployment; re-validated against friday itself
---"""

EXPECTED = [
    ("status", "04-validated"),
    ("captured", "2026-07-30"),
    ("note", "built 2026-07-29; bounced once — validation failed on the first target"),
    ("increment", "INC-202"),
    ("validated", "2026-07-30 — close ran the mover live: docs/trails/INC-202.md"),
    ("reason", "first target lacked a real deployment; re-validated against friday itself"),
]


def test_every_header_field_parses_through_taglines_unchanged():
    """The core equivalence: each interior line IS a house typed tag line —
    tools/taglines.py `parse_typed_line`, no new parser, expected fields back."""
    lines = HEADER.splitlines()
    parsed = [taglines.parse_typed_line(ln) for ln in lines[1:-1]]
    assert parsed == EXPECTED


def test_the_fence_is_a_delimiter_not_a_field():
    """`---` must be invisible to the typed-line grammar — it delimits the
    live region, it never parses as a claim."""
    assert taglines.parse_typed_line("---") is None


def test_the_block_is_well_formed_frontmatter():
    """The frontmatter half of the equivalence, at the shape level the
    convention defines: the block opens the file with `---`, closes with
    `---`, and every interior line is a plain `key: value` pair (the YAML
    subset simple scalars occupy) — no line is anything else."""
    lines = HEADER.splitlines()
    assert lines[0] == "---" and lines[-1] == "---"
    for ln in lines[1:-1]:
        pair = taglines.parse_typed_line(ln)
        assert pair is not None, f"non-field line inside the fence: {ln!r}"
        key = pair[0]
        assert key == key.lower() and " " not in key


def test_a_colon_inside_a_value_stays_in_the_value():
    """The reflow incident's near-miss, pinned from the other side: a value
    containing `: ` must not truncate — the first key-colon wins, the rest is
    value bytes."""
    key, value = taglines.parse_typed_line(
        "validated: 2026-07-30 — close ran the mover live: docs/trails/INC-202.md")
    assert key == "validated"
    assert value.endswith("live: docs/trails/INC-202.md")


def test_prose_below_the_fence_never_reads_as_a_field():
    """The frozen body stays outside the grammar: a prose sentence whose first
    word is followed later by a colon (the brainstormer's reflow false
    positive, 'changed the increment three times: once when...') must NOT
    parse as a typed line — the key must sit immediately against its colon."""
    assert taglines.parse_typed_line(
        "changed the increment three times: once when a measurement landed") is None
