#!/usr/bin/env python3
"""INC-107 FR-107.1/107.2/107.8 — the loose-deferral scan (the mechanical half).

Finds CANDIDATE deferrals in code comments: walks a project's source files,
extracts comment text only (line comments, block comments, and Python
triple-quoted prose — the idiom friday's own specimens lived in), and matches
a deliberately generous marker vocabulary against each contiguous comment
block's whitespace-flattened text. Generous by measured necessity: the
audit's flagship deferral carries none of the classic markers and is
reachable only by a wide net whose junk a later model read rejects
(INC-107 §3; the reading is NOT this tool's job — no candidate is judged
here). Flattened matching because a phrase that wraps across comment lines
is still the phrase (INC-110 KH-4's lesson, applied at birth).

The reported unit is the comment block, never the matched line: the
flagship's only marker hit lands on a line quoting a documentation-section
title while the decision sits above it unmatched, so a line-keyed report
finds the specimen and describes it wrongly (D6). Several hits in one block
are one candidate.

What the scan cannot reach is named, never absorbed into a clean result
(FR-107.8, S-107.2): an unreadable file lands in `unread`, a source file
whose comment syntax this scanner does not parse lands in `unparsed`.
Documents are deliberately not hunted (D4 — a deferral written only in a
document has its own route on friday-built projects and its honest limit is
recorded in the oracle's §10), so document extensions are out of the
hunting ground rather than unparsed. Where a block carries a value-shaped
token it is reported by location with the token withheld (S-107.4).

Reads and reports only: no file in the scanned project is written, no
marker removed, no comment touched (S-107.3). Exact matching throughout —
never a similarity judgement. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# OQ-107.1 — the marker vocabulary, resolved at build from the discovery
# drill's measured behaviour on two real trees (banked evidence E2-E4).
# Phrases are matched word-bounded and case-insensitive against FLATTENED
# block text, so multi-word members survive a mid-phrase wrap.
VOCABULARY = (
    "todo", "fixme", "tbd", "xxx", "hack",
    "known gap", "known gaps",
    "defer", "defers", "deferred", "deferral", "deferrals",
    "revisit", "revisits", "revisited",
    "postpone", "postponed",
    "post-launch",
    "for now", "not yet", "not implemented",
    "temporary", "temporarily", "stopgap", "workaround",
    "polish pass", "at current scale", "at this scale",
)

_MARKER_RX = tuple(
    (m, re.compile(r"(?i)(?<![\w-])" + re.escape(m).replace(r"\ ", r"[ ]")
                   + r"(?![\w-])"))
    for m in VOCABULARY
)

# Comment syntax families, by extension (and a few well-known basenames).
_HASH_EXT = {".py", ".sh", ".bash", ".rb", ".pl", ".yml", ".yaml", ".toml",
             ".ini", ".cfg", ".conf", ".tf", ".mk", ".cmake", ".r"}
_SLASH_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".c", ".h",
              ".cc", ".cpp", ".hpp", ".java", ".go", ".rs", ".kt", ".swift",
              ".scala", ".cs", ".css", ".scss", ".less", ".php", ".proto"}
_DASH_EXT = {".sql"}
_MARKUP_EXT = {".html", ".htm", ".vue", ".xml", ".svelte"}
_HASH_BASENAMES = {"Makefile", "Dockerfile", "Rakefile", "Gemfile",
                   "Justfile", ".gitignore", ".dockerignore",
                   ".gitattributes", ".editorconfig"}
# Documents and data: out of the hunting ground by ruling (D4), not unparsed.
_DOC_DATA_EXT = {".md", ".rst", ".txt", ".adoc", ".json", ".lock", ".csv",
                 ".tsv", ".svg", ".map", ".sum", ".log", ".license"}

_SKIP_DIRS = {".git", ".friday", "node_modules", "__pycache__", ".venv",
              "venv", ".pytest_cache", ".ruff_cache", "dist", "build",
              ".next", "vendor", "coverage", ".tox"}

# S-107.4 — value-shaped tokens are withheld from every report. Conservative
# shapes: keyish prefixes, cloud key ids, long hex/base64 runs, PEM armor.
_VALUE_RX = (
    re.compile(r"\b(?:sk|pk|rk|whsec)_[A-Za-z0-9_]{10,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
    re.compile(r"-----BEGIN[A-Z ]+-----[^-]*-----END[A-Z ]+-----", re.S),
)
_WITHHELD = "«value withheld»"


def _mask_values(text: str) -> str:
    for rx in _VALUE_RX:
        text = rx.sub(_WITHHELD, text)
    return text


def _flatten(text: str) -> str:
    return " ".join(text.split())


def _markers_in(flat: str) -> list[str]:
    return [name for name, rx in _MARKER_RX if rx.search(flat)]


def _split_outside_quotes(line: str, starter: str) -> str | None:
    """The comment tail of a line, or None — quote-parity heuristic so a
    starter inside a string literal is not read as a comment."""
    in_s = in_d = False
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif not in_s and not in_d and line.startswith(starter, i):
            return line[i + len(starter):]
        i += 1
    return None


def _comment_lines_line_style(lines: list[str], starter: str):
    """Yield (lineno, text) for full-line and trailing line-comments."""
    for i, ln in enumerate(lines, 1):
        stripped = ln.strip()
        if stripped.startswith(starter):
            yield i, stripped[len(starter):]
            continue
        tail = _split_outside_quotes(ln, starter)
        if tail is not None and ln.strip():
            yield i, tail


def _spans_block_style(text: str, opener: str, closer: str):
    """Yield (start_line, end_line, body) for opener...closer spans."""
    pos = 0
    while True:
        start = text.find(opener, pos)
        if start == -1:
            return
        end = text.find(closer, start + len(opener))
        if end == -1:
            end = len(text)
        body = text[start + len(opener):end]
        start_line = text.count("\n", 0, start) + 1
        end_line = text.count("\n", 0, end) + 1
        yield start_line, end_line, body
        pos = end + len(closer)


def _py_docstring_spans(text: str):
    """Triple-quoted blocks in Python source, treated as comment prose —
    the idiom the INC-110 specimens lived in, and where friday's own
    vocabulary collisions sit (docstrings are the dogfood junk case)."""
    for quote in ('"""', "'''"):
        yield from _spans_block_style(text, quote, quote)


def _extract_blocks(rel: str, text: str):
    """Return [(start, end, text)] contiguous comment blocks for one file."""
    ext = os.path.splitext(rel)[1].lower()
    base = os.path.basename(rel)
    lines = text.splitlines()
    line_comments: list[tuple[int, str]] = []
    span_blocks: list[tuple[int, int, str]] = []

    is_hash = (ext in _HASH_EXT or base in _HASH_BASENAMES
               or ".env" in base.lower()
               or (not ext and text.startswith("#!")))
    if is_hash:
        line_comments = list(_comment_lines_line_style(lines, "#"))
        if ext == ".py":
            span_blocks = list(_py_docstring_spans(text))
    elif ext in _SLASH_EXT:
        line_comments = list(_comment_lines_line_style(lines, "//"))
        span_blocks = list(_spans_block_style(text, "/*", "*/"))
    elif ext in _DASH_EXT:
        line_comments = list(_comment_lines_line_style(lines, "--"))
        span_blocks = list(_spans_block_style(text, "/*", "*/"))
    elif ext in _MARKUP_EXT:
        span_blocks = list(_spans_block_style(text, "<!--", "-->"))
    else:
        return None  # not a syntax this scanner parses

    blocks: list[tuple[int, int, str]] = []
    run: list[tuple[int, str]] = []
    for lineno, ctext in line_comments:
        if run and lineno == run[-1][0] + 1:
            run.append((lineno, ctext))
        else:
            if run:
                blocks.append((run[0][0], run[-1][0],
                               "\n".join(t for _, t in run)))
            run = [(lineno, ctext)]
    if run:
        blocks.append((run[0][0], run[-1][0], "\n".join(t for _, t in run)))
    blocks.extend(span_blocks)
    blocks.sort(key=lambda b: (b[0], b[1]))
    return blocks


def scan(root: str) -> dict:
    root = os.path.abspath(root)
    candidates: list[dict] = []
    unread: list[str] = []
    unparsed: list[str] = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            ext = os.path.splitext(fn)[1].lower()
            if ext in _DOC_DATA_EXT:
                continue  # documents are not hunted (D4 — limit recorded)
            try:
                with open(full, "rb") as fh:
                    raw = fh.read()
            except OSError:
                unread.append(rel)
                continue
            if b"\0" in raw[:8192]:
                continue  # binary, not source prose
            text = raw.decode("utf-8", errors="replace")
            blocks = _extract_blocks(rel, text)
            if blocks is None:
                unparsed.append(rel)
                continue
            scanned += 1
            for start, end, btext in blocks:
                flat = _flatten(btext)
                markers = _markers_in(flat)
                if markers:
                    candidates.append({
                        "file": rel,
                        "line_start": start,
                        "line_end": end,
                        "markers": markers,
                        "text": _mask_values(flat),
                    })

    candidates.sort(key=lambda c: (c["file"], c["line_start"]))
    return {
        "root": root,
        "scanned_files": scanned,
        "candidates": candidates,
        "unread": sorted(unread),
        "unparsed": sorted(unparsed),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="loose-deferral scan — candidate deferrals in code "
                    "comments; reports only, never edits (INC-107)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = scan(args.root)
    if args.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    else:
        print("loose-deferral scan: %d candidate(s) across %d scanned "
              "file(s); %d unread, %d unparsed"
              % (len(out["candidates"]), out["scanned_files"],
                 len(out["unread"]), len(out["unparsed"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
