#!/usr/bin/env python3
"""The answered set — why the next deep clean does not ask again (INC-107).

The loose-deferral scan finds candidates; the reading and the PM answer them;
this record makes those answers durable (FR-107.6 — the increment's largest
make-or-break: without it the second deep clean re-asks everything the first
one settled, against a repository that has already ruled against nagging in
writing). This module OWNS `docs/LOOSE-DEFERRALS.md` (the D-0135 pattern) and
the record is COMMITTED, not substrate-side: durability across clones is the
whole point, and a machine-local record would re-ask everything on the second
clone (OQ-107.4, D-1070).

**Candidate identity (D9, OQ-107.2, KH-2):** a digest of the file path plus
the comment block's whitespace-flattened text. A reformat that re-wraps the
block changes nothing flattened — same identity, passed over. An edited
comment is a changed decision — new identity, re-presented. A moved file
re-presents: the accepted cost, taken over the alternative where two
identical decisions in different files collapse into one identity and one
real decision vanishes.

**The four answers (FR-107.5), a CLOSED vocabulary:** `captured` (into the
parked ledger, PM's word only, and the detail must name the PARK entry — a
capture claim with no ledger id is a route back that does not exist),
`dismissed` (with the junk shape named), `left-standing` (recorded, with the
reason), `already-homed` (with the home named). An unknown value is refused.

**The cap bar (FR-107.7, OQ-107.3):** how many candidates a run PRESENTS is
the project's own declared number — the `FRIDAY-LOOSE-DEFERRAL` block beside
the other measured bars in `docs/standards/coding-standards.md`, typed line
`loose-deferral: presented <= N` — read here, tool-owned default when no line
is declared. The remainder is always a named number, never an absence.

One typed line per answer; the parser anchors on the LAST ` · file: ` marker
so free prose in the detail cannot shift the fields. A malformed line is kept
and flagged, never dropped. The empty case is written down. Contract (both
record shapes of this seam): `docs/contracts/loose-deferral-envelope.md`.
Pure stdlib.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402

BLOCK = "FRIDAY-ANSWERED"
SENTINEL = "_Nothing answered._"
ANSWERS = ("captured", "dismissed", "left-standing", "already-homed")
DEFAULT_PRESENTED_CAP = 25
_FILE_SEP = " · file: "
_HEAD_RE = re.compile(r"^([0-9a-f]{12}) (\d{4}-\d{2}-\d{2}) (\S+) — (.*)$",
                      re.DOTALL)
_CAP_RE = re.compile(r"^presented\s*<=\s*(\d+)$")

HEADER = """# Loose deferrals — the answered set (INC-107)

One line per candidate deferral the deep clean's scan surfaced and someone
answered — including junk rejections, because a rejection that is not recorded
is a question the next run asks again. Written by `tools/loose_deferrals.py`
only. Identity survives a reformat and dies on a comment edit by design
(a changed comment is a changed decision). Contract:
`docs/contracts/loose-deferral-envelope.md`.

<!-- FRIDAY-ANSWERED:BEGIN -->
{body}
<!-- FRIDAY-ANSWERED:END -->
"""


def _path(root: str) -> str:
    return os.path.join(fs.resolve_worktree_root(root), "docs",
                        "LOOSE-DEFERRALS.md")


def _read(root: str) -> str | None:
    try:
        with open(_path(root), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def _atomic_write(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _flatten(text: str) -> str:
    return " ".join(text.split())


def identity(file: str, text: str) -> str:
    """The candidate's durable name: path + flattened block text, digested.
    Flattening here mirrors the scan's flattening, so a caller may pass raw
    wrapped comment text and still land on the same identity. Standalone `*`
    decoration tokens are dropped before digesting: a block-comment rewrap
    that spills one more line adds one more ` * ` prefix, and an identity
    that counts decorations re-asks a settled question on an ordinary rewrap
    — the KH-2 death mode, found live at the acceptance run."""
    tokens = [t for t in _flatten(text).split(" ") if t != "*"]
    digest = hashlib.sha256(
        f"{file}\0{' '.join(tokens)}".encode("utf-8")).hexdigest()
    return digest[:12]


def _parse_line(value: str) -> dict:
    """One `answered:` VALUE → entry dict; anchors on the LAST file marker."""
    head, sep, file = value.rpartition(_FILE_SEP)
    if not sep or not file.strip():
        return {"malformed": True, "raw": f"answered: {value}"}
    m = _HEAD_RE.match(head)
    if not m:
        return {"malformed": True, "raw": f"answered: {value}"}
    ident, date, answer, detail = m.groups()
    if answer not in ANSWERS:
        return {"malformed": True, "raw": f"answered: {value}"}
    return {"malformed": False, "id": ident, "date": date, "answer": answer,
            "detail": detail.strip(), "file": file.strip(),
            "raw": f"answered: {value}"}


def entries(root: str = ".") -> list[dict]:
    """Every answered line, malformed ones included and flagged. [] for an
    absent record or the sentinel — both valid, both quiet."""
    text = _read(root)
    if text is None:
        return []
    out = []
    for line in taglines.block_lines(text, BLOCK) or []:
        if line.strip() == SENTINEL or line.strip().startswith("<!--"):
            continue
        parsed = taglines.parse_typed_line(line)
        if not parsed or parsed[0] != "answered":
            continue
        out.append(_parse_line(parsed[1]))
    return out


def _splice(text: str, body_lines: list[str]) -> str:
    begin, end = f"<!-- {BLOCK}:BEGIN -->", f"<!-- {BLOCK}:END -->"
    head, _, rest = text.partition(begin)
    _, _, tail = rest.partition(end)
    body = "\n".join(body_lines) if body_lines else SENTINEL
    return f"{head}{begin}\n{body}\n{end}{tail}"


def _raw_body(text: str) -> list[str]:
    return [line for line in (taglines.block_lines(text, BLOCK) or [])
            if line.strip() != SENTINEL]


def record(root: str = ".", *, file: str, text: str, answer: str, detail: str,
           when: str | None = None) -> dict:
    """Record one answer. Returns {'id': <digest>, ...}."""
    if answer not in ANSWERS:
        raise ValueError(f"answer must be one of {'|'.join(ANSWERS)}, got {answer!r}")
    detail = " ".join((detail or "").split())
    if not detail:
        raise ValueError("detail must be non-empty — an unexplained answer "
                         "cannot be trusted by the run that reads it back")
    if answer == "captured" and "PARK-" not in detail:
        raise ValueError("a captured answer must name its PARK- ledger entry — "
                         "a capture with no ledger id claims a route back that "
                         "does not exist")
    date = when or datetime.date.today().isoformat()
    ident = identity(file, text)
    line = f"answered: {ident} {date} {answer} — {detail}{_FILE_SEP}{file}"
    doc = _read(root)
    if doc is None:
        os.makedirs(os.path.dirname(_path(root)), exist_ok=True)
        doc = HEADER.format(body=SENTINEL)
    _atomic_write(_path(root), _splice(doc, _raw_body(doc) + [line]))
    return {"id": ident, "date": date, "answer": answer, "file": file}


def recognize(root: str = ".", candidates: list[dict] | None = None) -> dict:
    """Split a scan's candidates into new vs previously answered — and COUNT
    the recognised ones, because a run must state how many settled questions
    it passed over (FR-107.6), never silently skip them."""
    answered = {e["id"] for e in entries(root) if not e["malformed"]}
    new, recognized = [], 0
    for c in (candidates or []):
        if identity(c["file"], c["text"]) in answered:
            recognized += 1
        else:
            new.append(c)
    return {"new": new, "recognized": recognized}


def presented_cap(root: str = ".") -> int:
    """The project's declared presentation cap — the FRIDAY-LOOSE-DEFERRAL
    typed line beside the other measured bars — or the tool-owned default.
    A garbage line falls back rather than crashing a report-only pass."""
    path = os.path.join(fs.resolve_worktree_root(root), "docs", "standards",
                        "coding-standards.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return DEFAULT_PRESENTED_CAP
    for line in taglines.block_lines(text, "FRIDAY-LOOSE-DEFERRAL") or []:
        parsed = taglines.parse_typed_line(line)
        if parsed and parsed[0] == "loose-deferral":
            m = _CAP_RE.match(parsed[1].strip())
            if m:
                return int(m.group(1))
    return DEFAULT_PRESENTED_CAP


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="The answered set (INC-107) — "
                                             "record, list, recognize")
    sub = ap.add_subparsers(dest="verb", required=True)
    r = sub.add_parser("record", help="record one answer for a candidate")
    r.add_argument("--root", default=".")
    r.add_argument("--file", required=True, help="the candidate's file path")
    r.add_argument("--text", required=True, help="the candidate's block text")
    r.add_argument("--answer", required=True, choices=ANSWERS)
    r.add_argument("--detail", required=True)
    r.add_argument("--when", default=None, help="date override (default: today)")
    ls = sub.add_parser("list", help="every answered entry, JSON")
    ls.add_argument("--root", default=".")
    rec = sub.add_parser("recognize", help="split scan candidates: new vs answered")
    rec.add_argument("--root", default=".")
    rec.add_argument("--scan", required=True,
                     help="path to a loose_deferral_scan.py --json output")
    args = ap.parse_args(argv)
    if args.verb == "record":
        try:
            res = record(args.root, file=args.file, text=args.text,
                         answer=args.answer, detail=args.detail, when=args.when)
        except ValueError as exc:
            print(json.dumps({"ok": False, "detail": str(exc)}))
            return 1
        print(json.dumps(res))
        return 0
    if args.verb == "list":
        print(json.dumps({"entries": entries(args.root)}))
        return 0
    with open(args.scan, encoding="utf-8") as fh:
        scan = json.load(fh)
    print(json.dumps(recognize(args.root, scan.get("candidates", []))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
