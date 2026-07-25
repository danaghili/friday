#!/usr/bin/env python3
"""Sanitized mirror — S-3's unicode-stripping mechanism (TECHNICAL_SOW_REBUILD
S-3 / guard #13's file-content half; probe: docs/research/rebuild/
probe-sandbox-unicode.md, prototype rebuilt test-first).

A deterministic pre-pass copies the repo to a stripped mirror; a sandboxed
reviewer is pointed ONLY at the mirror, so invisible-character smuggling —
zero-width splices, bidi overrides/isolates (the "Trojan Source" class),
BOMs, and the Unicode Tag block (ASCII smuggling) — never reaches the
model's read path. Legitimate content (accents, CJK, emoji, combining
marks) is preserved byte-for-byte; non-UTF-8 files (binaries) pass through
unchanged. `.git/` and `.friday/` are not copied: history and substrate are
not review surface.

SAY THIS PLAINLY (the probe's honest limit, pinned by test): stripping
defeats INVISIBLE-character smuggling only. A hostile instruction in plain
visible text survives by design — that class is countered by the reviewers'
read-only tool grant and the repo-bytes-are-data contract, never by this
script.

Usage: python3 tools/sanitized_mirror.py --src <repo> --dst <mirror> [--json]
Exit codes: 0 ok · 2 bad invocation (dst inside src would recurse forever).
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Closed intervals of code points stripped outright (probe-verified +
# harden-widened, A6 — the earlier set missed several invisible classes inside
# its own stated mission: variation selectors, ALM, soft hyphen, braille-blank).
STRIP_RANGES = (
    (0x00AD, 0x00AD),   # soft hyphen — invisible
    (0x061C, 0x061C),   # Arabic letter mark — bidi control
    (0x180E, 0x180E),   # Mongolian vowel separator — invisible
    (0x200B, 0x200F),   # zero-width space/joiners + LTR/RTL marks
    (0x2028, 0x202E),   # line/para separators + bidi embed/override
    (0x2060, 0x2064),   # word joiner + invisible operators
    (0x2066, 0x2069),   # bidi isolates — Trojan Source class
    (0x2800, 0x2800),   # braille pattern blank — renders as blank
    (0xFE00, 0xFE0F),   # variation selectors — smuggling channel
    (0xFEFF, 0xFEFF),   # BOM / zero-width no-break space
    (0xFFF9, 0xFFFB),   # interlinear annotation anchors
    (0xE0000, 0xE007F),  # Unicode tag block — ASCII smuggling
    (0xE0100, 0xE01EF),  # variation selectors supplement — smuggling channel
)

SKIP_DIRS = {".git", ".friday", "node_modules", "__pycache__", ".venv", "venv"}


def strip_text(text: str) -> str:
    return "".join(ch for ch in text
                   if not any(lo <= ord(ch) <= hi for lo, hi in STRIP_RANGES))


def strip_bytes(raw: bytes) -> tuple[bytes, bool]:
    """(possibly-stripped bytes, was_changed). Non-UTF-8 passes through —
    a binary is never 'sanitized' into corruption."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw, False
    out = strip_text(text).encode("utf-8")
    return out, out != raw


def mirror(src: str, dst: str) -> dict:
    """Walk src into a stripped copy at dst. Returns {"files": N,
    "stripped": M, "symlinks_skipped": K}. Symlinks are NEVER followed
    (D-0033): a shortcut pointing outside the repo would pull unvetted
    content into the review surface — skipped and counted so the reviewer
    sees a named gap, never a silent one. Empty tree → all-zero stats (the
    tested empty case)."""
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    files = stripped = symlinks = 0
    for dirpath, dirnames, filenames in os.walk(src):
        linked = [d for d in dirnames if os.path.islink(os.path.join(dirpath, d))]
        symlinks += len(linked)
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and d not in linked]
        rel_dir = os.path.relpath(dirpath, src)
        out_dir = dst if rel_dir == "." else os.path.join(dst, rel_dir)
        os.makedirs(out_dir, exist_ok=True)
        for fn in sorted(filenames):
            path = os.path.join(dirpath, fn)
            if os.path.islink(path):
                symlinks += 1
                continue
            with open(path, "rb") as fh:
                raw = fh.read()
            out, changed = strip_bytes(raw)
            with open(os.path.join(out_dir, fn), "wb") as fh:
                fh.write(out)
            files += 1
            stripped += changed
    return {"files": files, "stripped": stripped, "symlinks_skipped": symlinks}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build a unicode-sanitized mirror "
                                             "of a repo for sandboxed review (S-3)")
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    src, dst = os.path.abspath(args.src), os.path.abspath(args.dst)
    if not os.path.isdir(src):
        print(f"sanitized_mirror: --src is not a directory: {src}", file=sys.stderr)
        return 2
    if dst == src or dst.startswith(src + os.sep):
        print("sanitized_mirror: --dst must lie outside --src (a mirror inside "
              "its source would mirror itself)", file=sys.stderr)
        return 2
    stats = mirror(src, dst)
    print(json.dumps(stats) if args.json
          else f"sanitized mirror: {stats['files']} file(s) copied, "
               f"{stats['stripped']} stripped, "
               f"{stats['symlinks_skipped']} symlink(s) SKIPPED (never followed "
               f"— named review gaps) at {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
