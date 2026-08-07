#!/usr/bin/env python3
"""The written conformance check — a declared convention's check, written
down once and kept (INC-105 FR-105.2, FR-105.3, FR-105.9; D1, D11).

The audited project's conventions were violated in ways a minutes-long
search would have found, and nothing ran the search; the first check written
during this increment's own discovery was the wrong check, and what a
project wants at its next sweep is the version somebody improved, not a
fresh guess (KH-4). So the check is an artifact: a typed line in the
FRIDAY-CONFORMANCE block beside the project's measured bars
(`docs/standards/coding-standards.md`), readable and editable by a person,
fingerprinted so the report shows which version ran (AC-105.6).

    conformance: <id> <kind> · rule: <prose> · from: <path>[ · anchor: <exact phrase>][ · scope: <globs>][ · pattern: <regex>][ · except: <globs>]

- **The kind vocabulary is CLOSED** (OQ-105.1 — exact search or a graph
  walk, never a similarity judgement): `forbid` (every match of pattern is
  a finding), `require` (every scope file lacking the pattern is a finding),
  `cycle` (the import-cycle walk over the extracted graph), and `unchecked`
  — found-not-checked as a first-class kind, so a rule harvested with no
  check persists as a line and is never absent from a report (FR-105.3).
- **Exceptions are pattern-shaped, refused as territory by name
  (FR-105.9, AC-105.10):** an except glob whose basename is empty, `*` or
  `**` excludes a whole directory tree — the audit's own carve-out disease —
  and is refused with the reason, with the check still running minus the
  refused exception. Never silently honoured, never silently dropped.
- **The orphan mirror (FR-105.3):** a check whose `from:` document is gone,
  or whose `anchor:` phrase no longer appears in it, is reported orphaned —
  the two halves cannot drift apart in silence.
- **A malformed or unknown-kind line is kept and flagged, never dropped;**
  a kind-rule violation rides as invalid WITH its reason and is reported,
  never silently run and never silently clean.

A person may edit the block directly (D1); `add` is the module's own write
door and never rewrites the lines a person owns. Grammar note: free-prose
fields may contain ` · ` and marker-like words; the parser peels segments
RIGHTMOST-first in reverse emission order (the parked ledger's anchor
lesson), so the emitted shape always round-trips.
Contract: `docs/contracts/conformance-envelope.md`. Pure stdlib.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402

KEY = "conformance"
BLOCK = "FRIDAY-CONFORMANCE"
SENTINEL = "_No conformance checks yet._"
KINDS = ("forbid", "require", "cycle", "unchecked")

_HEAD_RE = re.compile(r"^([a-z][a-z0-9-]*) (" + "|".join(KINDS) + r")$")
_TERRITORY_REASON = (
    "exceptions are pattern-shaped — name files by a discriminating pattern "
    "(e.g. **/conftest.py, *.test.ts, tools/friday_substrate.py), never a "
    "territory (a whole directory tree); refused: {value}")

_STANDARDS_REL = os.path.join("docs", "standards", "coding-standards.md")

_SEED = """# Coding standards

<!-- FRIDAY-CONFORMANCE:BEGIN -->
{body}
<!-- FRIDAY-CONFORMANCE:END -->
"""


def _path(root: str) -> str:
    return os.path.join(fs.resolve_worktree_root(root), _STANDARDS_REL)


def _read_text(root: str) -> str | None:
    try:
        with open(_path(root), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def _peel(rest: str, marker: str) -> tuple[str, str | None]:
    head, sep, tail = rest.rpartition(f" · {marker}: ")
    if not sep:
        return rest, None
    return head, tail


def _split_excepts(raw: str | None) -> tuple[list[str], list[dict]]:
    """Comma-split, then sort each glob into pattern-shaped (kept) or
    territory-shaped (refused by name — the basename discriminates nothing)."""
    kept: list[str] = []
    refused: list[dict] = []
    for value in (v.strip() for v in (raw or "").split(",") if v.strip()):
        basename = value.split("/")[-1]
        if basename in ("", "*", "**"):
            refused.append({"value": value,
                            "reason": _TERRITORY_REASON.format(value=value)})
        else:
            kept.append(value)
    return kept, refused


def _kind_reason(kind: str, scope: str | None, pattern: str | None,
                 excepts_raw: str | None) -> str | None:
    if kind == "forbid" and pattern is None:
        return ("forbid requires pattern — the exact search is the check "
                "(OQ-105.1)")
    if kind == "require" and (pattern is None or scope is None):
        return ("require names the files that must carry the pattern — "
                "scope and pattern are both required")
    if kind == "cycle" and (scope or pattern or excepts_raw):
        return ("cycle walks the extracted graph — scope, pattern and "
                "except do not belong on a cycle check")
    if kind == "unchecked" and (scope or pattern or excepts_raw):
        return ("unchecked is found-not-checked — a rule awaiting its check "
                "carries no pattern, scope or except (FR-105.3)")
    return None


def _parse_check(value: str) -> dict | None:
    rest, excepts_raw = _peel(value, "except")
    rest, pattern = _peel(rest, "pattern")
    rest, scope = _peel(rest, "scope")
    rest, anchor = _peel(rest, "anchor")
    rest, from_ = _peel(rest, "from")
    head, rule = _peel(rest, "rule")
    m = _HEAD_RE.match(head)
    if not m or rule is None or from_ is None:
        return None
    excepts, refused = _split_excepts(excepts_raw)
    check_id, kind = m.groups()
    return {"id": check_id, "kind": kind, "rule": rule, "from": from_,
            "anchor": anchor, "scope": scope, "pattern": pattern,
            "excepts": excepts, "refused_excepts": refused,
            "excepts_raw": excepts_raw,
            "invalid": _kind_reason(kind, scope, pattern, excepts_raw)}


def format_check(check: dict) -> str:
    """Re-emit the exact line — fixed segment order, raw except string kept,
    so a hand-written line always round-trips byte-identically."""
    line = (f"conformance: {check['id']} {check['kind']} "
            f"· rule: {check['rule']} · from: {check['from']}")
    if check.get("anchor"):
        line += f" · anchor: {check['anchor']}"
    if check.get("scope"):
        line += f" · scope: {check['scope']}"
    if check.get("pattern"):
        line += f" · pattern: {check['pattern']}"
    if check.get("excepts_raw"):
        line += f" · except: {check['excepts_raw']}"
    return line


def _fingerprint(line: str) -> str:
    normalized = " ".join(line.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]


def _orphaned(root: str, check: dict) -> str | None:
    """FR-105.3's mirror: the rule left its document. Path-existence always;
    the anchor phrase where one is declared — without an anchor the limit is
    path-existence only, which the contract states rather than hides."""
    doc = os.path.join(fs.resolve_worktree_root(root), check["from"])
    if not os.path.isfile(doc):
        return f"{check['from']} does not exist"
    if check.get("anchor"):
        try:
            with open(doc, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return f"{check['from']} is unreadable"
        # The from-document may be the standards file itself; the check's own
        # line carries the anchor phrase, so the block is cut before the
        # search or every anchor would self-satisfy.
        begin, end = f"<!-- {BLOCK}:BEGIN -->", f"<!-- {BLOCK}:END -->"
        if begin in text and end in text:
            head, _, rest = text.partition(begin)
            _, _, tail = rest.partition(end)
            text = head + tail
        if check["anchor"] not in text:
            return f"anchor phrase not found in {check['from']}"
    return None


def read(root: str = ".") -> dict:
    """The block's current state. `status`: 'absent' (never seeded here),
    'empty' (seeded, no checks yet), 'recorded'. Malformed lines ride along
    flagged; every kept check carries fingerprint, orphan state and any
    kind-rule invalidity WITH its reason."""
    text = _read_text(root)
    lines = taglines.block_lines(text, BLOCK) if text is not None else None
    if lines is None:
        return {"status": "absent", "checks": [], "malformed": []}
    checks: list[dict] = []
    malformed: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if line == SENTINEL:
            continue
        parsed = taglines.parse_typed_line(line)
        entry = _parse_check(parsed[1]) if parsed and parsed[0] == KEY else None
        if entry is None:
            malformed.append(line)
            continue
        if entry["id"] in seen:
            malformed.append(f"{line} — duplicate id {entry['id']}")
            continue
        seen.add(entry["id"])
        entry["line"] = line
        entry["fingerprint"] = _fingerprint(line)
        entry["orphaned"] = _orphaned(root, entry)
        checks.append(entry)
    status = "recorded" if checks or malformed else "empty"
    return {"status": status, "checks": checks, "malformed": malformed}


def init(root: str = ".") -> dict:
    """Seed the block — absent file gets the minimal standards file, a file
    without the block gains it at the end, an existing block is untouched."""
    text = _read_text(root)
    path = _path(root)
    if text is None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        body = _SEED.format(body=SENTINEL)
    elif taglines.block_lines(text, BLOCK) is None:
        body = (text.rstrip("\n") + "\n\n<!-- " + BLOCK + ":BEGIN -->\n"
                + SENTINEL + "\n<!-- " + BLOCK + ":END -->\n")
    else:
        return {"ok": True, "detail": "block already present"}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(body)
    os.replace(tmp, path)
    return {"ok": True, "detail": f"seeded {path}"}


_ADD_KEYS = frozenset(("id", "kind", "rule", "from", "anchor", "scope",
                       "pattern", "except"))


def _add_reason(root: str, spec: dict) -> str | None:
    unknown = set(spec) - _ADD_KEYS
    if unknown:
        return (f"unknown field(s) {sorted(unknown)} — the check grammar's "
                "single home is docs/contracts/conformance-envelope.md")
    if not re.match(r"^[a-z][a-z0-9-]*$", spec.get("id") or ""):
        return f"id must be a kebab-case token, got {spec.get('id')!r}"
    if spec.get("kind") not in KINDS:
        return (f"kind must be one of {'|'.join(KINDS)} — exact search or a "
                f"graph walk, never a similarity judgement (OQ-105.1); got "
                f"{spec.get('kind')!r}")
    if not spec.get("rule") or not spec.get("from"):
        return "a check names its rule and where the rule is written"
    reason = _kind_reason(spec["kind"], spec.get("scope"),
                          spec.get("pattern"), spec.get("except"))
    if reason:
        return reason
    _, refused = _split_excepts(spec.get("except"))
    if refused:
        return refused[0]["reason"]
    if any(c["id"] == spec["id"] for c in read(root)["checks"]):
        return f"duplicate id {spec['id']!r} — one check per id, edit it"
    return None


def add(root: str = ".", spec: dict | None = None) -> dict:
    """The module's own write door — appends one check line before the END
    marker, leaving every hand-written line byte-identical (D1)."""
    spec = {k: v for k, v in (spec or {}).items() if v}
    reason = _add_reason(root, spec)
    if reason:
        return {"ok": False, "reason": reason}
    if read(root)["status"] == "absent":
        init(root)
    line = format_check({**spec, "excepts_raw": spec.get("except")})
    text = _read_text(root)
    end = f"<!-- {BLOCK}:END -->"
    head, sep, tail = text.partition(end)
    head = head.replace(SENTINEL + "\n", "")
    path = _path(root)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(f"{head}{line}\n{sep}{tail}")
    os.replace(tmp, path)
    return {"ok": True, "id": spec["id"], "line": line}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("read", help="current state, JSON")
    sub.add_parser("init", help="seed the empty block")
    a = sub.add_parser("add", help="append one check line")
    a.add_argument("--id", required=True)
    a.add_argument("--kind", required=True)
    a.add_argument("--rule", required=True)
    a.add_argument("--from", dest="from_", required=True)
    a.add_argument("--anchor", default="")
    a.add_argument("--scope", default="")
    a.add_argument("--pattern", default="")
    a.add_argument("--except", dest="except_", default="")
    args = p.parse_args(argv)
    if args.cmd == "read":
        out = read(args.root)
    elif args.cmd == "init":
        out = init(args.root)
    else:
        out = add(args.root, {"id": args.id, "kind": args.kind,
                              "rule": args.rule, "from": args.from_,
                              "anchor": args.anchor, "scope": args.scope,
                              "pattern": args.pattern,
                              "except": args.except_})
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
