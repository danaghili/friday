#!/usr/bin/env python3
"""The operations battery's verdict record (INC-102 FR-102.3, D7/D8/D9).

This module OWNS `docs/ops/battery.md` (the D-0135 pattern: a module owning a
whole record type writes its own record; the substrate is reached only for
shared primitives). One typed line per battery row — the CURRENT verdict, its
date, and (for a proven drill row) the paths the drill proves; history lives
in git, never in the file:

    verdict: restore proven 2026-08-03 proves: backup.sh compose.yml — note
    verdict: undo not-proven 2026-08-03 — drill written, awaiting operator
    verdict: monitoring judged 2026-08-03 — alerts reach the PM's phone

- **Row keys are a CLOSED vocabulary** whose single home is the contract table
  in `docs/contracts/ops-battery.md` (FR-102.1, D8); ROWS below is the
  operational copy and a committed test locks the two together. An unknown
  row is refused, never recorded.
- **A non-verdict is structurally impossible (KH-5):** proof-grammar rows take
  exactly proven / not-proven / not-applicable; a proven DRILL row must name
  the paths it proves (that is what the expiry reads, FR-102.4); proves
  anywhere else is refused; not-applicable requires its reason (FR-102.10).
- **Judged rows are labelled literally (D8):** the two rows carried unchanged
  from before the proof grammar record `judged` (with the judgment's
  substance as a mandatory note) or `not-applicable` — the proof vocabulary
  never leaks onto them, and they never borrow its authority.
- **The empty case is a valid, distinct outcome (AC-102.7, S-102.4):** an
  absent file means the battery never ran here; an empty block means nothing
  proven yet — reported as exactly that, never as clean.
- **A malformed line is kept and flagged, never dropped** — a vanishing
  verdict is the silent miss this record exists to end.

Contract: `docs/contracts/ops-battery.md`. Pure stdlib.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402

BLOCK = "FRIDAY-OPS-BATTERY"
SENTINEL = "_Nothing proven yet._"

# (key, kind) in contract-table order — the operational copy of the single
# home; tests/test_ops_battery.py locks this tuple to the contract's table.
ROWS = (
    ("restore", "drill"),
    ("undo", "drill"),
    ("restart", "drill"),
    ("job-list", "inspection"),
    ("job-freshness", "inspection"),
    ("isolation", "inspection"),
    ("runtime-parity", "inspection"),
    ("client-visibility", "inspection"),
    ("dependency-advisory", "inspection"),
    ("monitoring", "judged"),
    ("runbook", "judged"),
)
KIND = dict(ROWS)
PROOF_VERDICTS = ("proven", "not-proven", "not-applicable")
JUDGED_VERDICTS = ("judged", "not-applicable")

_NOTE_SEP = " — "
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HEAD_RE = re.compile(
    r"^(\S+) (proven|not-proven|not-applicable|judged) (\d{4}-\d{2}-\d{2})"
    r"(?: proves:((?: \S+)+))?(?: ratified: (\d{4}-\d{2}-\d{2}))?$")

HEADER = """# Operations battery — verdict record

One typed line per battery row: the current verdict, its date, and — for a proven drill row — the paths the drill proves. Written by `tools/ops_battery.py` only; the row set, each row's kind, and the verdict grammar live in `docs/contracts/ops-battery.md` (the battery's single home). History lives in git — this file holds the current state, never the story.

<!-- FRIDAY-OPS-BATTERY:BEGIN -->
{body}
<!-- FRIDAY-OPS-BATTERY:END -->
"""


def _path(root: str) -> str:
    return os.path.join(fs.resolve_worktree_root(root), "docs", "ops", "battery.md")


def _read_text(root: str) -> str | None:
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


def _parse_value(value: str) -> dict | None:
    """One `verdict:` VALUE → row dict, or None when malformed. The note is
    everything after the FIRST ` — `: the structured head carries no spaces
    beyond its own separators, so free prose can never shift the fields."""
    head, sep, note = value.partition(_NOTE_SEP)
    match = _HEAD_RE.match(head.strip())
    if not match:
        return None
    key, verdict, date, proves, ratified = match.groups()
    if key not in KIND:
        return None
    return {"key": key, "kind": KIND[key], "verdict": verdict, "date": date,
            "proves": proves.split() if proves else [],
            "ratified": ratified or "",
            "note": note.strip() if sep else ""}


def _validate(key: str, verdict: str, proves: list[str], note: str) -> None:
    if key not in KIND:
        raise ValueError(f"unknown row {key!r} — the row set's single home is "
                         f"docs/contracts/ops-battery.md")
    kind = KIND[key]
    allowed = JUDGED_VERDICTS if kind == "judged" else PROOF_VERDICTS
    if verdict not in allowed:
        raise ValueError(f"{key} is a {kind} row — its verdict must be one of "
                         f"{'|'.join(allowed)}, got {verdict!r}")
    if verdict == "proven" and kind == "drill":
        if not proves:
            raise ValueError(f"a proven drill row names the paths it proves "
                             f"(FR-102.4 reads them) — {key} got none")
    elif proves:
        raise ValueError("proves: belongs only on a proven drill row — "
                         f"{key} {verdict} cannot carry it")
    if verdict == "not-applicable" and not note:
        raise ValueError("not-applicable comes with the reason written down "
                         "(FR-102.10)")
    if verdict == "judged" and not note:
        raise ValueError("a judged row records the judgment's substance as its "
                         "note — a bare label decides nothing")


def _format_line(key: str, verdict: str, date: str, proves: list[str],
                 note: str, ratified: str = "") -> str:
    line = f"verdict: {key} {verdict} {date}"
    if proves:
        line += " proves: " + " ".join(proves)
    if ratified:
        line += f" ratified: {ratified}"
    if note:
        line += f"{_NOTE_SEP}{note}"
    return line


def _splice(text: str, body_lines: list[str]) -> str:
    begin, end = f"<!-- {BLOCK}:BEGIN -->", f"<!-- {BLOCK}:END -->"
    head, _, rest = text.partition(begin)
    _, _, tail = rest.partition(end)
    body = "\n".join(body_lines) if body_lines else SENTINEL
    return f"{head}{begin}\n{body}\n{end}{tail}"


def read(root: str = ".") -> dict:
    """The record's current state. `status` is one of three REAL outcomes:
    'absent' (this project never ran the battery), 'empty' (nothing proven
    yet — never clean), 'recorded'. Malformed lines ride along flagged."""
    text = _read_text(root)
    if text is None:
        return {"status": "absent", "rows": {}, "malformed": []}
    lines = taglines.block_lines(text, BLOCK)
    if lines is None:
        return {"status": "absent", "rows": {}, "malformed": []}
    rows: dict[str, dict] = {}
    malformed: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == SENTINEL or stripped.startswith("<!--"):
            continue
        parsed = taglines.parse_typed_line(line)
        if not parsed or parsed[0] != "verdict":
            malformed.append(line)
            continue
        entry = _parse_value(parsed[1])
        if entry is None:
            malformed.append(line)
            continue
        rows[entry.pop("key")] = entry
    status = "recorded" if rows or malformed else "empty"
    return {"status": status, "rows": rows, "malformed": malformed}


def init(root: str = ".") -> dict:
    """Write the record with its empty block — 'nothing proven yet' as a
    written fact. A no-op when the record already exists."""
    if _read_text(root) is not None:
        return {"ok": True, "detail": "record already exists"}
    path = _path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _atomic_write(path, HEADER.format(body=SENTINEL))
    return {"ok": True, "detail": f"initialized {path}"}


def _rewrite(root: str, rows: dict[str, dict], malformed: list[str]) -> None:
    text = _read_text(root)
    if text is None:
        init(root)
        text = _read_text(root)
    order = [k for k, _ in ROWS]
    body = [_format_line(k, r["verdict"], r["date"], r["proves"], r["note"],
                         r.get("ratified", ""))
            for k, r in sorted(rows.items(), key=lambda kv: order.index(kv[0]))]
    _atomic_write(_path(root), _splice(text, body + malformed))


def record(root: str = ".", key: str = "", verdict: str = "", *,
           proves: list[str] | None = None, note: str = "",
           when: str | None = None) -> dict:
    """Upsert one row's verdict — one line per row, latest call wins, rows in
    contract-table order. Everything unparseable in the block is preserved.
    Recording is the ROLE's moment; the PM's ratification of a
    not-applicable row is a separate moment (the close) and a separate verb —
    ratify() below — so a fresh recording always arrives unratified."""
    proves = proves or []
    note = " ".join((note or "").split())
    _validate(key, verdict, proves, note)
    date = when or datetime.date.today().isoformat()
    if not _DATE_RE.match(date):
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}")
    current = read(root)
    kept = current["rows"]
    kept[key] = {"kind": KIND[key], "verdict": verdict, "date": date,
                 "proves": proves, "note": note, "ratified": ""}
    _rewrite(root, kept, current["malformed"])
    return {"ok": True, "row": key, "verdict": verdict, "date": date}


def ratify(root: str = ".", key: str = "", *, when: str | None = None) -> dict:
    """The PM's dated ruling on a not-applicable row (FR-102.10, OQ-102.5) —
    structural, so the deep clean's accepted-risk aging reads it back. Only
    an existing not-applicable row can be ratified: the PM ratifies a
    decline, never a proof."""
    date = when or datetime.date.today().isoformat()
    if not _DATE_RE.match(date):
        raise ValueError(f"ratified date must be YYYY-MM-DD, got {date!r}")
    current = read(root)
    row = current["rows"].get(key)
    if row is None:
        return {"ok": False, "detail": f"{key!r} has no recorded verdict — "
                                       f"nothing to ratify"}
    if row["verdict"] != "not-applicable":
        raise ValueError("ratified: belongs only to a not-applicable row — "
                         "the PM ratifies a decline, never a proof")
    row["ratified"] = date
    _rewrite(root, current["rows"], current["malformed"])
    return {"ok": True, "row": key, "ratified": date}


GIT_TIMEOUT_S = 10


def _git_lines(root: str, *args: str) -> list[str] | None:
    """Run one git query; None when git cannot answer (not a repo, no git) —
    the caller must treat None as could-not-verify, never as nothing-moved."""
    try:
        proc = subprocess.run(["git", "-C", root, *args],
                              capture_output=True, text=True,
                              timeout=GIT_TIMEOUT_S)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def check_expiry(root: str = ".") -> dict:
    """FR-102.4: for every proven DRILL row, ask the project's own history
    whether any path the drill proves changed since the drill's date. A
    change — committed strictly after that date, or sitting uncommitted —
    expires the result and NAMES the killer. A path git has never seen is
    unverifiable, reported as exactly that and never folded into stands
    (the S-102.4 shape). Report-only: exits nothing, blocks nothing
    (S-102.2); inspection rows re-derive and judged rows never expire (D7),
    so neither is checked here."""
    top = fs.resolve_worktree_root(root)
    state = read(root)
    checks = []
    for key, _ in ROWS:
        row = state["rows"].get(key)
        if not row or row["kind"] != "drill" or row["verdict"] != "proven":
            continue
        changed, dirty, unknown = [], [], []
        for path in row["proves"]:
            hist = _git_lines(top, "log", "--format=%H\t%cs\t%s",
                              "--follow", "--", path)
            if hist is None or not hist:
                unknown.append(path)
                continue
            for line in hist:
                commit, cdate, subject = (line.split("\t", 2) + ["", ""])[:3]
                if cdate > row["date"]:
                    changed.append({"path": path, "commit": commit,
                                    "date": cdate, "subject": subject})
            status = _git_lines(top, "status", "--porcelain", "--", path)
            if status:
                dirty.append(path)
        if changed or dirty:
            result = "expired"
        elif unknown:
            result = "unverifiable"
        else:
            result = "stands"
        killer = max(changed, key=lambda c: c["date"]) if changed else None
        checks.append({"row": key, "date": row["date"], "result": result,
                       "killer": killer, "changed": changed, "dirty": dirty,
                       "unknown": unknown})
    return {"status": state["status"], "checks": checks}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="The operations battery's verdict record (INC-102 FR-102.3)")
    sub = ap.add_subparsers(dest="verb", required=True)
    r = sub.add_parser("record", help="upsert one row's verdict")
    r.add_argument("--root", default=".")
    r.add_argument("--row", required=True)
    r.add_argument("--verdict", required=True)
    r.add_argument("--proves", action="append", default=[],
                   help="a path the drill proves (repeatable; proven drill rows only)")
    r.add_argument("--note", default="")
    r.add_argument("--when", default=None, help="date override (default: today)")
    rt = sub.add_parser("ratify", help="the PM's dated ruling on a recorded "
                                       "not-applicable row (FR-102.10)")
    rt.add_argument("--root", default=".")
    rt.add_argument("--row", required=True)
    rt.add_argument("--when", default=None, help="date override (default: today)")
    rd = sub.add_parser("read", help="current state, JSON")
    rd.add_argument("--root", default=".")
    ini = sub.add_parser("init", help="write the empty record — nothing proven yet")
    ini.add_argument("--root", default=".")
    ck = sub.add_parser("check", help="drill-row expiry against real history "
                                      "(FR-102.4) — report only, always exit 0")
    ck.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    if args.verb == "check":
        print(json.dumps(check_expiry(args.root)))
        return 0
    if args.verb == "record":
        try:
            res = record(args.root, args.row, args.verdict, proves=args.proves,
                         note=args.note, when=args.when)
        except ValueError as exc:
            print(json.dumps({"ok": False, "detail": str(exc)}))
            return 1
        print(json.dumps(res))
        return 0
    if args.verb == "ratify":
        try:
            res = ratify(args.root, args.row, when=args.when)
        except ValueError as exc:
            print(json.dumps({"ok": False, "detail": str(exc)}))
            return 1
        print(json.dumps(res))
        return 0 if res.get("ok") else 1
    if args.verb == "read":
        print(json.dumps(read(args.root)))
        return 0
    print(json.dumps(init(args.root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
