#!/usr/bin/env python3
"""The PARKED ledger — the waiting room becomes a real place (D-0108, task #23).

Three surfaces behaved as if a waiting room existed while none did (NF4):
redteam routes confirmed findings "into the waiting room" as candidate
requirements, feedback's vocabulary wanted a "good idea, not now" outcome, and
reconcile's §5 roundup promised to re-present "everything that was ever parked".
With no destination, not-now was recorded as rejection — and rejection has no
re-presentation path, which is the entire difference parking is supposed to make.

This module OWNS `docs/PARKED.md` (the D-0135 pattern: a module owning a whole
record type writes its own record; the substrate is reached only for shared
primitives). One typed line per entry, exactly the four ruled fields:

    parked: PARK-001 2026-07-29 from:feedback — <what> · revisit-when: <when>

- **Writers:** `/friday:feedback` (outcome `parked`) and `/friday:redteam`
  (a candidate requirement the PM declines for now). Both on the PM's word —
  parking is a PM decision, never a model's disposal bin.
- **Sweeper:** `/friday:reconcile` §5 re-presents every live entry for a fresh
  call (still deferred / worth doing now / no longer relevant) and `resolve`s
  the ones the PM moves or kills. The PM's fresh call is captured where
  decisions live (DECISIONS.md / the feedback log) — this ledger holds the
  waiting, not the verdicts.
- **Source vocabulary is CLOSED** (K4 doctrine): the two ruled writers plus the
  two parkers the roundup already sweeps (`discovery`'s conscious exclusions,
  the `lead`'s own deferrals). An unknown source is refused, never recorded.
- **Ids never come back.** The next id is max-ever-seen + 1, scanned from live
  AND resolved history via the tombstone comment the resolver leaves, so a
  reference to PARK-007 in some old conversation can never point at a stranger.
- **A malformed line is kept and flagged, never dropped** — a silently-vanishing
  entry is a parked idea that will never be re-presented, the precise failure
  this file exists to end.
- **The empty case is written down**: `_Nothing parked._` — distinguishable
  from a vandalised block, and restored when the last entry resolves.

Grammar note: `what` is PM prose and may contain em-dashes and the word
"revisit"; the parser therefore anchors on the LAST ` · revisit-when: ` marker.
Contract: `docs/contracts/parked-ledger.md`. Pure stdlib.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402

BLOCK = "FRIDAY-PARKED"
SENTINEL = "_Nothing parked._"
SOURCES = ("feedback", "redteam", "discovery", "lead")
_SEP = " · revisit-when: "
_HEAD_RE = re.compile(r"^PARK-(\d{3,}) (\d{4}-\d{2}-\d{2}) from:(\S+) — (.*)$",
                      re.DOTALL)
# The resolver's tombstone — invisible to the grammar, remembered by the minter.
_TOMB_RE = re.compile(r"<!-- resolved: PARK-(\d{3,}) ")

HEADER = """# Parked — the waiting room (D-0108)

One line per idea the PM chose to defer — not rejected, waiting. Written by
`tools/parked.py` only (feedback and redteam route into it; reconcile's §5
roundup re-presents every entry for a fresh call). Contract:
`docs/contracts/parked-ledger.md`.

<!-- FRIDAY-PARKED:BEGIN -->
{body}
<!-- FRIDAY-PARKED:END -->
"""


def _path(root: str) -> str:
    return os.path.join(fs.resolve_worktree_root(root), "docs", "PARKED.md")


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


def _parse_line(value: str) -> dict:
    """One `parked:` VALUE → entry dict. Anchors on the LAST revisit marker so
    PM prose containing the separator cannot shift the fields."""
    head, sep, revisit = value.rpartition(_SEP)
    if not sep:
        return {"malformed": True, "raw": f"parked: {value}"}
    match = _HEAD_RE.match(head)
    if not match or not revisit.strip():
        return {"malformed": True, "raw": f"parked: {value}"}
    num, date, source, what = match.groups()
    return {"malformed": False, "id": f"PARK-{num}", "num": int(num),
            "date": date, "source": source, "what": what.strip(),
            "revisit_when": revisit.strip(), "raw": f"parked: {value}"}


def entries(root: str = ".") -> list[dict]:
    """Every entry in the block, malformed ones included and flagged.
    [] for an absent ledger or the sentinel — both valid, both quiet."""
    text = _read(root)
    if text is None:
        return []
    lines = taglines.block_lines(text, BLOCK) or []
    out = []
    for line in lines:
        if line.strip() == SENTINEL or line.strip().startswith("<!--"):
            continue
        parsed = taglines.parse_typed_line(line)
        if not parsed or parsed[0] != "parked":
            continue
        out.append(_parse_line(parsed[1]))
    return out


def _next_num(text: str | None) -> int:
    """Max id ever seen — live lines AND resolved tombstones — plus one.
    A resolved number must never be re-minted (old references would dangle
    onto a stranger)."""
    if text is None:
        return 1
    seen = [0]
    for line in taglines.block_lines(text, BLOCK) or []:
        parsed = taglines.parse_typed_line(line)
        if parsed and parsed[0] == "parked":
            entry = _parse_line(parsed[1])
            if not entry["malformed"]:
                seen.append(entry["num"])
    seen.extend(int(m) for m in _TOMB_RE.findall(text))
    return max(seen) + 1


def _splice(text: str, body_lines: list[str]) -> str:
    """Replace the block's contents, leaving everything around it alone."""
    begin, end = f"<!-- {BLOCK}:BEGIN -->", f"<!-- {BLOCK}:END -->"
    head, _, rest = text.partition(begin)
    _, _, tail = rest.partition(end)
    body = "\n".join(body_lines) if body_lines else SENTINEL
    return f"{head}{begin}\n{body}\n{end}{tail}"


def _raw_body(text: str) -> list[str]:
    """The block's raw lines minus the sentinel: live entries, malformed lines,
    and tombstones alike. Every rewrite goes through this so nothing — least of
    all a retired number — is ever silently shed by an unrelated edit."""
    return [line for line in (taglines.block_lines(text, BLOCK) or [])
            if line.strip() != SENTINEL]


def append(root: str = ".", *, source: str, what: str, revisit_when: str,
           when: str | None = None) -> dict:
    """Park one idea, on the PM's word. Returns {'id': 'PARK-NNN', ...}."""
    if source not in SOURCES:
        raise ValueError(f"source must be one of {'|'.join(SOURCES)}, got {source!r}")
    what = " ".join((what or "").split())
    revisit_when = " ".join((revisit_when or "").split())
    if not what:
        raise ValueError("what must be non-empty — an unnamed idea cannot be re-presented")
    if not revisit_when:
        raise ValueError("revisit-when must be non-empty — an entry with no revisit "
                         "condition is the limbo this ledger replaces")
    date = when or datetime.date.today().isoformat()
    text = _read(root)
    num = _next_num(text)
    line = f"parked: PARK-{num:03d} {date} from:{source} — {what}{_SEP}{revisit_when}"
    if text is None:
        os.makedirs(os.path.dirname(_path(root)), exist_ok=True)
        text = HEADER.format(body=SENTINEL)
    _atomic_write(_path(root), _splice(text, _raw_body(text) + [line]))
    return {"id": f"PARK-{num:03d}", "date": date, "source": source}


def resolve(root: str = ".", park_id: str = "", *, by: str) -> dict:
    """Remove one entry — the PM gave it a fresh call at the reconcile roundup
    (moved to a lane, or no longer relevant). The call itself is recorded where
    decisions live; here the line is replaced by a tombstone comment that keeps
    the number retired forever. When the last live entry goes, the sentinel
    returns — 'nothing parked' stays a written fact."""
    text = _read(root)
    if text is None:
        return {"ok": False, "detail": f"no ledger — nothing holds {park_id}"}
    keep, hit, live_left = [], None, 0
    for raw in _raw_body(text):
        parsed = taglines.parse_typed_line(raw)
        entry = _parse_line(parsed[1]) if parsed and parsed[0] == "parked" else None
        if entry and not entry["malformed"] and entry["id"] == park_id:
            hit = entry
            continue
        if entry:
            live_left += 1
        keep.append(raw)
    if hit is None:
        return {"ok": False, "detail": f"{park_id} is not in the ledger — "
                                       f"nothing to resolve"}
    date = datetime.date.today().isoformat()
    tomb = f"<!-- resolved: {park_id} {date} by:{by} -->"
    body = ([SENTINEL] if live_left == 0 else []) + keep + [tomb]
    _atomic_write(_path(root), _splice(text, body))
    return {"ok": True, "id": park_id, "detail": f"{park_id} resolved by {by}"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="The PARKED ledger (D-0108) — "
                                             "append, list, resolve")
    sub = ap.add_subparsers(dest="verb", required=True)
    a = sub.add_parser("append", help="park one idea, on the PM's word")
    a.add_argument("--root", default=".")
    a.add_argument("--source", required=True, choices=SOURCES)
    a.add_argument("--what", required=True)
    a.add_argument("--revisit-when", required=True)
    a.add_argument("--when", default=None, help="date override (default: today)")
    ls = sub.add_parser("list", help="every live entry, JSON")
    ls.add_argument("--root", default=".")
    r = sub.add_parser("resolve", help="remove one entry after the PM's fresh call")
    r.add_argument("--root", default=".")
    r.add_argument("--id", required=True)
    r.add_argument("--by", required=True)
    args = ap.parse_args(argv)
    if args.verb == "append":
        try:
            res = append(args.root, source=args.source, what=args.what,
                         revisit_when=args.revisit_when, when=args.when)
        except ValueError as exc:
            print(json.dumps({"ok": False, "detail": str(exc)}))
            return 1
        print(json.dumps(res))
        return 0
    if args.verb == "list":
        print(json.dumps({"entries": entries(args.root)}))
        return 0
    res = resolve(args.root, args.id, by=args.by)
    print(json.dumps(res))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
