#!/usr/bin/env python3
"""Conformance-envelope checker (INC-105 FR-105.7; D8).

Contract: docs/contracts/conformance-envelope.md — the maintainability judge
(layer 2, running its conformance worklist) emits the envelope, this checker
validates and lands it. A SIBLING of the maintainability envelope, not a
reuse: that one carries a disposition over measured numbers and feeds the
enforcement gate; this one carries the judge's written answer to a rule
breach and **the gate never reads it — there is no `armed` field to
express a block with (D6, structural)**. The shape:

    conformance-envelope: source=harden|reconcile count=N

    ## C-n — <check-id> @ <location> (answer: breach|not-a-breach|accepted)
    rule:   <the written rule the judge reasoned against — the anchor>
    from:   <where the rule is written>
    reason: <plain words>

    ## Checked          (REQUIRED when count=0 — the first-class empty case)
    <what was swept — non-empty>

Every answer carries all three fields — an unanchored verdict is rejected,
the judge's iron rule unchanged (§9: the line is anchored-versus-taste). A
header that lies about its own `count` is refused; a heading that looks like
a finding but does not parse is an ERROR, never silently dropped.

Verdict rides stdout as ONE JSON object (the FR-61 shape). `--write`
validates FIRST and lands the body at the substrate-resolved path only on
valid-pass. Exit codes: 0 pass · 1 fail · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402

SOURCES = ("harden", "reconcile")
ANSWERS = ("breach", "not-a-breach", "accepted")
FIELDS = ("rule", "from", "reason")

_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_FINDING_RE = re.compile(
    r"^C-(\d+)\s+—\s+([a-z][a-z0-9-]*)\s+@\s+(.+?)\s+\(answer:\s*([a-z-]+)\)$")
_FIELD_RE = re.compile(r"^(rule|from|reason):\s*(.+?)\s*$")


def _parse_header(line: str, errors: list[str]) -> tuple[str | None, int | None]:
    parsed = taglines.parse_typed_line(line)
    if not parsed or parsed[0] != "conformance-envelope":
        errors.append("the first line must be the `conformance-envelope:` tag "
                      "line (`conformance-envelope: source=… count=N`) — see "
                      "docs/contracts/conformance-envelope.md")
        return None, None
    fields = dict(part.split("=", 1) for part in parsed[1].split(" ")
                  if "=" in part)
    source = fields.get("source")
    if source not in SOURCES:
        errors.append(f"source must be one of {'|'.join(SOURCES)} — the two "
                      f"run moments (FR-105.11); got {source!r}")
    if "armed" in fields:
        errors.append("there is no `armed` field by design — this envelope "
                      "cannot express a block (D6)")
    try:
        count = int(fields.get("count", ""))
    except ValueError:
        errors.append("count must state the true number of answered findings")
        count = None
    return source, count


def _close_finding(finding: dict | None, errors: list[str]) -> None:
    if finding is None:
        return
    for field in FIELDS:
        if not finding.get(field):
            errors.append(f"C-{finding['n']} is missing `{field}:` — an "
                          "unanchored verdict is rejected (the judge's iron "
                          "rule; FR-105.7)")


def parse(text: str) -> dict:
    errors: list[str] = []
    findings: list[dict] = []
    checked: list[str] = []
    lines = [ln for ln in text.splitlines()]
    body = [ln for ln in lines if ln.strip()]
    if not body:
        return {"errors": ["empty envelope — not a valid document"],
                "findings": [], "count": None, "source": None}
    source, count = _parse_header(body[0], errors)
    current: dict | None = None
    in_checked = False
    seen: set[int] = set()
    for line in lines[1:]:
        h2 = _H2_RE.match(line)
        if h2:
            _close_finding(current, errors)
            current, in_checked = None, False
            head = h2.group(1)
            if head == "Checked":
                in_checked = True
                continue
            m = _FINDING_RE.match(head)
            if not m:
                if head.startswith("C-") or "answer" in head:
                    errors.append(f"finding heading does not parse: {head!r} "
                                  "— a dropped finding is the drift this "
                                  "checker exists to catch")
                continue
            n, check_id, location, answer = m.groups()
            if int(n) in seen:
                errors.append(f"duplicate finding number C-{n}")
            seen.add(int(n))
            if answer not in ANSWERS:
                errors.append(f"C-{n}: answer must be one of "
                              f"{'|'.join(ANSWERS)}, got {answer!r}")
            current = {"n": n, "check": check_id, "location": location,
                       "answer": answer}
            findings.append(current)
            continue
        if in_checked and line.strip():
            checked.append(line.strip())
        field = _FIELD_RE.match(line)
        if current is not None and field:
            current[field.group(1)] = field.group(2)
    _close_finding(current, errors)
    if count is not None and count != len(findings):
        errors.append(f"count={count} but the envelope carries "
                      f"{len(findings)} finding(s) — a header that lies "
                      "about its own count is refused")
    if count == 0 and not checked:
        errors.append("count=0 requires a non-empty `## Checked` section — "
                      "\"no breaches\" only counts when the envelope says "
                      "what was swept (the first-class empty case)")
    return {"errors": errors, "findings": findings, "count": count,
            "source": source}


def check_text(text: str) -> dict:
    out = parse(text)
    verdict = "valid-pass" if not out["errors"] else "valid-fail"
    return {"verdict": verdict, "errors": out["errors"],
            "count": out["count"], "findings": out["findings"],
            "summary": (f"conformance envelope: {verdict} — "
                        f"{len(out['findings'])} answered finding(s)")}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default=".")
    p.add_argument("--file", default=None,
                   help="check this file (default: the substrate-resolved "
                        "envelope)")
    p.add_argument("--write", action="store_true",
                   help="validate stdin FIRST; land it at the substrate path "
                        "only on valid-pass")
    args = p.parse_args(argv)
    if args.write:
        text = sys.stdin.read()
        out = check_text(text)
        if out["verdict"] == "valid-pass":
            path = fs.conformance_envelope_path(args.root)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, path)
            out["path"] = path
    else:
        path = args.file or fs.conformance_envelope_path(args.root)
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            out = {"verdict": "valid-fail",
                   "errors": [f"envelope absent or unreadable at {path} — "
                              "consuming an absent document is the failure"],
                   "count": None, "findings": [],
                   "summary": "conformance envelope: valid-fail — absent"}
            print(json.dumps(out))
            return 1
        out = check_text(text)
    print(json.dumps(out))
    return 0 if out["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
