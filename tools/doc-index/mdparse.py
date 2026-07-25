#!/usr/bin/env python3
"""
mdparse — markdown heading tree + section spans for friday-docs (PROP-024).

Shared parser core: friday-docs' reader triad (list_sections / get_section /
search_in) live-parses files through this module, and PROP-023's lifecycle
sweep will reuse it for FEATURES.md regeneration. Keep it dependency-free.

Design rules (binding, from PROP-024 §Pre-build audits):
- ATX headings only (`# ...` .. `###### ...`); setext headings don't occur in
  the corpus (scaffolder templates are ATX-only) and are ignored.
- Headings inside fenced code blocks (``` / ~~~) are NOT headings — real
  artifacts contain shell snippets with `# comment` lines.
- Heading matching is exact-after-normalization, NO fuzzy matching:
  strip → drop leading "N." / "N.N" numbering → strip trailing #s → casefold
  → collapse whitespace → strip emphasis tokens.
- A section's span runs from its heading line to the line before the next
  heading of equal-or-shallower level (an H2 section includes its child H3s).
- Line numbers are 1-based; byte offsets are computed against the ORIGINAL
  file bytes (CRLF preserved) so citations line up with what plain Read sees.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ATX heading: 1-6 #s, at least one space, then text; tolerate closing #s.
_ATX_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
# Leading section numbering: "1. ", "2.3 ", "10.1.2. " — anchored, requires
# trailing whitespace so "1.5x speedup" mid-heading is untouched.
_NUMBERING_RE = re.compile(r"^\d+(\.\d+)*\.?\s+")
_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_WS_RUN_RE = re.compile(r"\s+")


@dataclass
class Heading:
    level: int          # 1-6
    text: str           # verbatim heading text (no leading #s, trimmed)
    norm: str           # normalized form used for matching
    line: int           # 1-based line number of the heading line
    end_line: int       # 1-based last line of the section span (inclusive)
    byte_start: int     # offset of the heading line's first byte
    byte_end: int       # offset one past the section's last byte
    ordinal: int = 0    # order of appearance within the document

    @property
    def approx_bytes(self) -> int:
        return self.byte_end - self.byte_start


@dataclass
class Document:
    """Parsed markdown document: original bytes + heading tree."""
    raw: bytes
    lines: list[str] = field(default_factory=list)        # decoded, EOL-stripped
    line_byte_offsets: list[int] = field(default_factory=list)  # per line, into raw
    headings: list[Heading] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return len(self.raw)

    @property
    def line_count(self) -> int:
        return len(self.lines)


def normalize_heading(text: str) -> str:
    """Exact-after-normalization transform — the ONLY matching rule.

    Order matters: numbering is stripped before casefolding so the regex
    anchors stay simple; emphasis tokens are stripped last so "## `Foo`"
    and "## **3. Foo**" both normalize to "foo".
    """
    t = text.strip()
    # Strip closing ATX hashes ("## Foo ##") — but only when whitespace-
    # separated, so a heading like "C#" keeps its hash.
    t = re.sub(r"\s+#+\s*$", "", t)
    # vnext deviation from the v0.4.0 parser (DECISIONS.md D-0006): backticks
    # and asterisks are pure markup and are removed EVERYWHERE, so
    # "`Config` Surface" matches a "config surface" query. Underscores stay
    # edge-only below — they are semantic inside identifiers (verify_state.py).
    t = t.replace("`", "").replace("*", "")
    # Strip surrounding emphasis tokens repeatedly, then re-check for
    # numbering underneath ("**3. Foo**" arrives here as "3. Foo").
    for _ in range(4):
        stripped = t.strip("*_`").strip()
        stripped = _NUMBERING_RE.sub("", stripped)
        if stripped == t:
            break
        t = stripped
    t = t.casefold()
    t = _WS_RUN_RE.sub(" ", t).strip()
    return t


def parse_document(raw: bytes) -> Document:
    """Parse original file bytes into a heading tree with accurate offsets."""
    # Strip a UTF-8 BOM for *matching* purposes but keep raw offsets honest:
    # the BOM stays in `raw`; the first line's text just has it removed.
    text = raw.decode("utf-8", errors="replace")

    doc = Document(raw=raw)
    # Walk original text keeping byte offsets (CRLF intact in raw).
    offset = 0
    fence_marker: str | None = None  # the opening fence string when inside one
    ordinal = 0
    for i, line in enumerate(text.splitlines(keepends=True)):
        stripped_eol = line.rstrip("\r\n")
        if i == 0 and stripped_eol.startswith("\ufeff"):
            stripped_eol = stripped_eol.lstrip("\ufeff")
        doc.lines.append(stripped_eol)
        doc.line_byte_offsets.append(offset)

        fence_match = _FENCE_RE.match(stripped_eol)
        if fence_match:
            marker = fence_match.group(1)
            if fence_marker is None:
                fence_marker = marker[0] * 3  # close on same char family
            elif marker.startswith(fence_marker):
                fence_marker = None
            # A fence line is never a heading.
        elif fence_marker is None:
            m = _ATX_RE.match(stripped_eol)
            if m:
                heading_text = re.sub(r"\s+#+\s*$", "", m.group(2)).strip()
                doc.headings.append(Heading(
                    level=len(m.group(1)),
                    text=heading_text,
                    norm=normalize_heading(heading_text),
                    line=i + 1,
                    end_line=0,        # filled below
                    byte_start=offset,
                    byte_end=0,        # filled below
                    ordinal=ordinal,
                ))
                ordinal += 1

        offset += len(line.encode("utf-8"))

    total = len(raw)
    n_lines = len(doc.lines)
    # Close section spans: each heading runs until the next heading of
    # equal-or-shallower level, or EOF.
    for idx, h in enumerate(doc.headings):
        end_byte = total
        end_line = n_lines
        for later in doc.headings[idx + 1:]:
            if later.level <= h.level:
                end_byte = later.byte_start
                end_line = later.line - 1
                break
        h.byte_end = end_byte
        h.end_line = end_line
    return doc


def parse_file(path: str) -> Document:
    with open(path, "rb") as f:
        return parse_document(f.read())


def find_section(doc: Document, query: str) -> tuple[Heading | None, int]:
    """Match a heading by exact-after-normalization. NO fuzzy.

    Returns (heading, duplicate_count). On duplicates the FIRST occurrence
    wins and duplicate_count tells the caller how many shared the norm.
    """
    q = normalize_heading(query)
    matches = [h for h in doc.headings if h.norm == q]
    if not matches:
        return None, 0
    return matches[0], len(matches)


def section_text(doc: Document, heading: Heading) -> str:
    """The section's verbatim text (heading line included), from raw bytes."""
    return doc.raw[heading.byte_start:heading.byte_end].decode(
        "utf-8", errors="replace")


def enclosing_section(doc: Document, line: int) -> str | None:
    """Name of the innermost section containing a 1-based line number.

    The latest heading (in document order) whose span contains the line IS
    the innermost one — spans only nest, they never partially overlap.
    """
    best: Heading | None = None
    for h in doc.headings:
        if h.line <= line <= h.end_line:
            best = h
    return best.text if best else None


def search_lines(doc: Document, query: str) -> list[dict]:
    """Case-insensitive substring search per line, with enclosing section."""
    q = query.casefold()
    out = []
    for i, line in enumerate(doc.lines):
        if q in line.casefold():
            out.append({
                "line": i + 1,
                "text": line,
                "section": enclosing_section(doc, i + 1),
            })
    return out
