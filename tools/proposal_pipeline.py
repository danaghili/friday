#!/usr/bin/env python3
"""Proposal pipeline core + the mover (INC-202: FR-202.4, D-0155 fields).

The ledger's stages are folders and the folder name IS the status word (D4),
so state is one `ls` to read and the drift check is string equality. This
module is the single authority for three things: finding a proposal by name
(D1 — live surfaces refer to proposals as `PROP-NNN`, never by path; this
lookup is what makes that affordable), reading and writing the fenced live
header (the grammar measured equivalent to `tools/taglines.py` in
`tests/test_inc202_header_grammar.py` — the fields are D-0155's: status ·
captured · note · increment · validated · reason), and performing a move —
the header status edit and the file relocation as ONE operation, both halves
or neither (S-202.1). Everything validates before anything writes; a refusal
changes zero bytes. The write order is destination-first then source-unlink:
a crash in the gap leaves a loud duplicate (caught by the checker and
AC-202.7's every-proposal-exactly-once), never a lost file.

The mover is the only thing in the repo that moves a proposal. The
`proposal-move` skill is its PM-facing door; the feature lane's close is its
automatic caller (D7). Transition law (D7/D10): forward along the pipeline,
backwards only `03 → 02` with a reason (failed validation), any working stage
→ `05-rejected` with a reason, and nothing moves out of a terminal stage.

Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

STAGES = ("01-proposed", "02-in-progress", "03-pending-validation",
          "04-validated", "05-rejected")
RETIRED = ("open", "shipped", "rejected", "research")
TERMINAL = ("04-validated", "05-rejected")

_FORWARD = {("01-proposed", "02-in-progress"),
            ("02-in-progress", "03-pending-validation"),
            ("03-pending-validation", "04-validated")}
_BACK = {("03-pending-validation", "02-in-progress")}


def proposals_dir(root: str) -> str:
    return os.path.join(root, "proposals")


def find_proposal(root: str, name: str) -> list[tuple[str, str]]:
    """Every (stage, path) holding `<name>.md` — the D1 by-name lookup. A
    healthy tree yields exactly one hit; zero and multiple are both verdicts
    the caller must handle, never silently picked from."""
    hits = []
    for stage in STAGES:
        p = os.path.join(proposals_dir(root), stage, name + ".md")
        if os.path.isfile(p):
            hits.append((stage, p))
    return hits


def read_header(text: str) -> dict | None:
    """Parse the fenced live header: `---`, typed `key: value` lines, `---`.
    Returns {"fields": [(key, value), ...], "body": str} — or None for a
    missing or malformed header (the caller refuses; nothing here guesses,
    because a guessed header would manufacture the drift this pipeline
    exists to kill)."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() != "---":
            continue
        fields = []
        for ln in lines[1:i]:
            pair = taglines.parse_typed_line(ln)
            if pair is None:
                return None
            fields.append(pair)
        return {"fields": fields, "body": "".join(lines[i + 1:])}
    return None


def render(fields: list[tuple[str, str]], body: str) -> str:
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in fields) + "---\n" + body


def set_field(fields: list[tuple[str, str]], key: str, value: str) -> list[tuple[str, str]]:
    """Replace in place (stable order) or append — the header's field order
    stays readable instead of churning on every edit."""
    out, replaced = [], False
    for k, v in fields:
        if k == key:
            out.append((k, value))
            replaced = True
        else:
            out.append((k, v))
    if not replaced:
        out.append((key, value))
    return out


def _transition_error(frm: str, to: str, *, has_increment: bool,
                      evidence: str | None, reason: str | None) -> str | None:
    """The whole of D7/D10 as one closed rule table. Returns the refusal
    text, or None when the move is legal with its requirements met."""
    if frm in TERMINAL:
        return f"{frm} is terminal — nothing moves out of it"
    if frm == to:
        return f"already in {to}"
    if (frm, to) not in _FORWARD and (frm, to) not in _BACK and to != "05-rejected":
        return f"no rule permits {frm} → {to}"
    if to == "02-in-progress" and frm == "01-proposed" and not has_increment:
        return "queueing is the linking moment — an increment id is required (D2)"
    if to == "04-validated" and not evidence:
        return "a move to 04-validated requires evidence (the validation gate)"
    if (to == "05-rejected" or (frm, to) in _BACK) and not reason:
        return f"a move to {to} from {frm} requires a reason (D10)"
    return None


def move(root: str, name: str, to: str, evidence: str | None = None,
         reason: str | None = None, increment: str | None = None) -> dict:
    """Perform one move: validate everything, then write. The returned dict
    is the typed verdict both callers (skill door and close) relay."""
    if to not in STAGES:
        return _refuse(name, f"unknown stage {to!r} — stages are {', '.join(STAGES)}")
    hits = find_proposal(root, name)
    if not hits:
        return _refuse(name, "not found in any stage folder")
    if len(hits) > 1:
        return _refuse(name, "exists in more than one stage: "
                       + ", ".join(s for s, _ in hits) + " — repair before moving")
    frm, path = hits[0]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    header = read_header(text)
    if header is None:
        return _refuse(name, "no parseable fenced header — the migration writes "
                             "headers; the mover never guesses one")
    fields = header["fields"]
    err = _transition_error(
        frm, to, has_increment=bool(increment or dict(fields).get("increment")),
        evidence=evidence, reason=reason)
    if err:
        return _refuse(name, err)

    fields = set_field(fields, "status", to)
    if increment:
        fields = set_field(fields, "increment", increment)
    if evidence:
        fields = set_field(fields, "validated", evidence)
    if reason:
        fields = set_field(fields, "reason", reason)
    dest = os.path.join(proposals_dir(root), to, name + ".md")
    if os.path.exists(dest):
        return _refuse(name, f"destination {to} already holds {name}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(render(fields, header["body"]))
    os.replace(tmp, dest)
    os.unlink(path)  # dest-first ordering: a crash here duplicates loudly, never loses
    return {"verdict": "moved", "name": name, "from": frm, "to": to}


def _refuse(name: str, why: str) -> dict:
    return {"verdict": "refused", "name": name, "reason": why}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Move one proposal through the pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    mv = sub.add_parser("move", help="header edit + relocation, both or neither")
    mv.add_argument("--root", default=".")
    mv.add_argument("--name", required=True, help="e.g. PROP-206 — never a path")
    mv.add_argument("--to", required=True, choices=STAGES)
    mv.add_argument("--evidence", help="required for 04-validated")
    mv.add_argument("--reason", help="required for 05-rejected and 03→02")
    mv.add_argument("--increment", help="required when queueing 01→02 (D2)")
    mv.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = move(args.root, args.name, args.to, evidence=args.evidence,
               reason=args.reason, increment=args.increment)
    print(json.dumps(res) if args.json else
          f"{res['verdict']}: {res['name']} — "
          + (f"{res['from']} → {res['to']}" if res["verdict"] == "moved"
             else res["reason"]))
    return 0 if res["verdict"] == "moved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
