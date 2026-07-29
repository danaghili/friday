#!/usr/bin/env python3
"""Typed tag-line grammar — the house convention every verifier depends on.

One fact per line, grep-able, attributed, never free prose for a checkable
claim (preserve-list §1.1). Families served by this one module:

  - Cross-unit notes:   `- [ACTION] {desc} (From {source} — {role} — {date})`
    with the closed tag vocabulary ACTION / INFO / DONE / OBSOLETE.
  - Typed claim lines:  `key: value` inside a marker-fenced block
    (FRIDAY-CLAIMS, FRIDAY-STATE, FRIDAY-REVIEW, FRIDAY-RELEASE-GATE …).
  - Marker blocks:      `<!-- {NAME}:BEGIN -->` … `<!-- {NAME}:END -->` —
    byte-exact splice points (never rename without updating every consumer).

Empty-case rule (hard-won lesson #6, ISSUE-008): an empty block or a document
with zero tag lines is a VALID, distinct outcome — `block_lines()` returns []
for an empty block and None only when the block is absent; `scan_notes()`
returns [] on a tagless document. Both are tested.

Pure stdlib. Parsing only — emission helpers keep writers on the exact shape.
"""
from __future__ import annotations

import re

NOTE_TAGS = ("ACTION", "INFO", "DONE", "OBSOLETE")

# Closed value vocabularies for the U1 claims extensions (TECHNICAL_SOW_REBUILD
# FR-66/FR-67). ONE home — verify_claims.py and doc_gate.py both import these;
# neither re-derives the list. Absent claims are declared gaps readers
# tolerate; the one consumer that REQUIRES provenance is doc_gate's spec kind.
PROVENANCE_VALUES = ("born-from-discovery", "recovered-from-code")
WORLD_VALUES = ("greenfield", "brownfield")

# INC-008 FR-8.1: the closed maintainability-metric vocabulary. A project's
# declared bars (`maintainability: <metric> <= <N>[%]`) live in a
# FRIDAY-MAINTAINABILITY block in its coding-standards file — a DIFFERENT home
# from CLAUDE.md's FRIDAY-CLAIMS, so the CLAUDE.md claim vocabulary is untouched
# (the additive-only guarantee, AC-8.3). ONE home for the vocabulary, exactly
# as with the value vocabularies above: verify_claims (well-formedness) and the
# measurer (the code check) both import this; neither re-derives it.
MAINTAINABILITY_METRICS = ("complexity", "file-size", "function-size",
                           "param-count", "nesting-depth", "duplication")

# `- [ACTION] desc (From F015 — Architect — 2026-04-12)` — the canonical line
# shape. The attribution suffix is required: an unattributed note can't be
# routed or retired.
_NOTE_RE = re.compile(
    r"^\s*-\s*\[(" + "|".join(NOTE_TAGS) + r")\]\s+(.+?)\s+"
    r"\(From\s+(.+?)\s+—\s+(.+?)\s+—\s+(\d{4}-\d{2}-\d{2})\)\s*$")

# `key: value` — key is a single lowercase token (hyphens allowed). Anchored at
# line start (allowing indent) so prose containing a colon never parses.
_TYPED_RE = re.compile(r"^\s*([a-z][a-z0-9-]*):\s+(.+?)\s*$")

_BEGIN_TMPL = "<!-- {name}:BEGIN -->"
_END_TMPL = "<!-- {name}:END -->"


def parse_note_line(line: str) -> dict | None:
    m = _NOTE_RE.match(line)
    if not m:
        return None
    tag, desc, source, role, date = m.groups()
    return {"tag": tag, "desc": desc, "source": source, "role": role, "date": date}


def format_note_line(tag: str, desc: str, *, source: str, role: str, date: str) -> str:
    if tag not in NOTE_TAGS:
        raise ValueError(f"tag must be one of {NOTE_TAGS}, got {tag!r}")
    return f"- [{tag}] {desc} (From {source} — {role} — {date})"


def parse_typed_line(line: str) -> tuple[str, str] | None:
    """(key, value) for a typed claim line; None for anything else. A prose
    sentence that merely contains a colon does not parse (the key must be a
    single lowercase token immediately followed by ':')."""
    m = _TYPED_RE.match(line)
    if not m:
        return None
    return m.group(1), m.group(2)


# A declared bar: `<metric> <= <N>` (a ceiling), duplication optionally as
# `<= N%`. `<=` is the only comparator — every maintainability bar is an upper
# limit. Numbers are non-negative integers; a negative/garbage/other-comparator
# value does NOT parse (well-formedness rejects it).
_MAINT_BAR_RE = re.compile(
    r"^(" + "|".join(MAINTAINABILITY_METRICS) + r")\s*<=\s*(\d+)(%?)$")


def parse_maintainability_bar(value: str) -> dict | None:
    """Parse a maintainability claim's VALUE — `<metric> <= <N>[%]`.

    Returns {'metric', 'limit': int, 'pct': bool} for a well-formed bar over the
    closed metric vocabulary, or None for anything else (unknown metric, wrong
    comparator, non-numeric or negative limit). Parsing only — the caller decides
    what a breach of the bar means (the measurer reads `pct` for duplication)."""
    m = _MAINT_BAR_RE.match(value.strip())
    if not m:
        return None
    return {"metric": m.group(1), "limit": int(m.group(2)), "pct": m.group(3) == "%"}


def block_lines(text: str, name: str) -> list[str] | None:
    """Non-blank lines inside `<!-- name:BEGIN -->` … `<!-- name:END -->`.
    Returns [] for a present-but-empty block (valid), None when the block is
    absent (a different fact — callers must not conflate them)."""
    begin, end = _BEGIN_TMPL.format(name=name), _END_TMPL.format(name=name)
    i = text.find(begin)
    if i < 0:
        return None
    j = text.find(end, i + len(begin))
    if j < 0:
        return None  # unterminated block — treat as absent, callers verify separately
    body = text[i + len(begin):j]
    return [ln.strip() for ln in body.splitlines() if ln.strip()]


def block_typed(text: str, name: str) -> dict[str, list[str]] | None:
    """Typed lines of a block as {key: [values]} (repeated keys legal, e.g.
    `finding:`). None when the block is absent; {} when present and empty."""
    lines = block_lines(text, name)
    if lines is None:
        return None
    out: dict[str, list[str]] = {}
    for ln in lines:
        parsed = parse_typed_line(ln)
        if parsed:
            out.setdefault(parsed[0], []).append(parsed[1])
    return out


def format_block(name: str, typed: list[tuple[str, str]]) -> str:
    body = "\n".join(f"{k}: {v}" for k, v in typed)
    return _BEGIN_TMPL.format(name=name) + ("\n" + body if body else "") + "\n" + _END_TMPL.format(name=name)


def scan_notes(text: str) -> list[dict]:
    """Every tag-line note in a document, with 1-based line numbers. [] on a
    tagless document — the tested empty case."""
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        parsed = parse_note_line(line)
        if parsed:
            parsed["line"] = i
            out.append(parsed)
    return out
