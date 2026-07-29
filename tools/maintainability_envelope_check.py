#!/usr/bin/env python3
"""Maintainability-envelope checker (INC-008 FR-8.4 / AC-8.4).

Contract: docs/contracts/maintainability-envelope.md — the agent judge (layer 2)
emits the envelope, this checker + the enforcement hook (layer 3) consume it. It
is a SIBLING of the findings brief, not a reuse of it: the findings brief carries
a *severity* axis (act-now / track / …); this carries a *disposition* axis
(justified / unjustified against a declared number). Bending one grammar to carry
both would make every reader guess which meaning a field holds. It is built on the
same structural pattern and REUSES the tagline grammar (Pin #1). The shape:

    maintainability-envelope: source=harden|close|reconcile count=N armed=true|false

    ## M-n — <metric> <measured> > <bar> @ <location> (disposition: justified|unjustified)
    standard: <the cited written line/section in coding-standards.md>
    reason:   <plain words: the justification, or why it must be fixed>
    floor:    none|auth-security|schema-data

    ## Checked          (REQUIRED when count=0 — the first-class empty case)
    <what was measured — non-empty>

Every finding carries all three fields; a header that lies about its own `count`
is refused; a heading that looks like a finding but does not parse is an ERROR,
never silently dropped (a dropped finding is exactly the drift this gate exists
to catch). The `floor:` field is surfaced so the hook can enforce the one-way
dangerous-file rule (S-8.3) — a breach in an auth-security / schema-data file can
never be silently warned past.

Verdict rides stdout as ONE JSON object (the FR-61 shape hooks/_guard.py consumes).
Exit codes: 0 pass · 1 fail · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

SOURCES = ("harden", "close", "reconcile")
DISPOSITIONS = ("justified", "unjustified")
FLOORS = ("none", "auth-security", "schema-data")
FIELDS = ("standard", "reason", "floor")

_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
# `M-n — <metric> <measured> > <bar> @ <location> (disposition: <d>)`
_FINDING_RE = re.compile(
    r"^M-(\d+)\s+—\s+([a-z-]+)\s+(\d+%?)\s+>\s+(\d+%?)\s+@\s+(.+?)\s+"
    r"\(disposition:\s*([a-z-]+)\)$")


def _parse_header(line: str, errors: list[str]) -> tuple[str | None, int | None, bool | None]:
    parsed = taglines.parse_typed_line(line)
    if not parsed or parsed[0] != "maintainability-envelope":
        errors.append("the first line must be the `maintainability-envelope:` tag line "
                      "(`maintainability-envelope: source=… count=N armed=true|false`) — "
                      "see docs/contracts/maintainability-envelope.md")
        return None, None, None
    fields = dict(tok.split("=", 1) for tok in parsed[1].split() if "=" in tok)
    source = fields.get("source")
    if source not in SOURCES:
        errors.append(f"source must be one of {'|'.join(SOURCES)}, got {source!r}")
        source = None
    try:
        count = int(fields.get("count", ""))
        if count < 0:
            raise ValueError
    except ValueError:
        errors.append(f"count must be a whole number, got {fields.get('count')!r}")
        count = None
    armed_raw = fields.get("armed")
    if armed_raw not in ("true", "false"):
        errors.append(f"armed must be true|false, got {armed_raw!r}")
        armed = None
    else:
        armed = armed_raw == "true"
    return source, count, armed


def _sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for ln in lines:
        m = _H2_RE.match(ln)
        if m:
            out.append((m.group(1), []))
        elif out:
            out[-1][1].append(ln)
    return out


def check_text(text: str) -> dict:
    errors: list[str] = []
    lines = text.splitlines()
    non_blank = [ln for ln in lines if ln.strip()]
    source, declared, armed = _parse_header(non_blank[0] if non_blank else "", errors)

    findings: list[dict] = []
    checked_body: list[str] | None = None
    for heading, body in _sections(lines):
        if heading == "Checked":
            checked_body = body
            continue
        if not heading.startswith("M-"):
            continue  # unknown sections tolerated; findings are never guessed at
        m = _FINDING_RE.match(heading)
        if not m:
            errors.append(f"the heading {heading!r} looks like a finding but does not "
                          "parse — expected `## M-n — <metric> <measured> > <bar> @ "
                          "<location> (disposition: justified|unjustified)`")
            continue
        n = int(m.group(1))
        metric, measured, bar, location, disposition = m.group(2, 3, 4, 5, 6)
        if metric not in taglines.MAINTAINABILITY_METRICS:
            errors.append(f"M-{n} names metric {metric!r} — must be one of "
                          f"{'|'.join(taglines.MAINTAINABILITY_METRICS)}")
        if disposition not in DISPOSITIONS:
            errors.append(f"M-{n} disposition {disposition!r} — must be justified|unjustified")
        typed = {}
        for ln in body:
            parsed = taglines.parse_typed_line(ln)
            if parsed and parsed[0] in FIELDS:
                typed[parsed[0]] = parsed[1]
        for field in FIELDS:
            if not typed.get(field, "").strip():
                errors.append(f"M-{n} is missing its `{field}:` line — every finding cites "
                              "the standard, gives a plain-words reason, and states its floor")
        floor = typed.get("floor", "").strip()
        if floor and floor not in FLOORS:
            errors.append(f"M-{n} floor {floor!r} — must be one of {'|'.join(FLOORS)}")
        findings.append({"n": n, "metric": metric, "measured": measured, "bar": bar,
                         "location": location, "disposition": disposition,
                         "floor": floor, "standard": typed.get("standard", "").strip(),
                         "reason": typed.get("reason", "").strip()})

    ids = [f["n"] for f in findings]
    for dup in sorted({n for n in ids if ids.count(n) > 1}):
        errors.append(f"M-{dup} appears more than once — finding numbers must be unique")

    if declared is not None and declared != len(findings):
        errors.append(f"the header declares count={declared} but the envelope holds "
                      f"{len(findings)} finding(s) — the header must state the true count")

    if declared == 0 and not findings:
        if checked_body is None or not any(ln.strip() for ln in checked_body):
            errors.append("count=0 requires a non-empty `## Checked` section — "
                          "\"no breaches\" only counts when the envelope says what was measured")

    if errors:
        return {"verdict": "valid-fail", "errors": errors, "source": source,
                "armed": armed, "count": len(findings), "findings": findings,
                "summary": f"maintainability envelope INVALID: {len(errors)} problem(s) — {errors[0]}"}
    return {"verdict": "valid-pass", "errors": [], "source": source, "armed": armed,
            "count": len(findings), "findings": findings,
            "summary": (f"maintainability envelope OK: source={source} count={len(findings)}"
                        + ("" if findings else " (empty case: Checked section present)"))}


def main(argv: list[str] | None = None, stdin_text: str | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate — or validate-then-write — a "
                                             "maintainability envelope (contract: "
                                             "docs/contracts/maintainability-envelope.md)")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="validate an existing envelope at this path")
    group.add_argument("--write", action="store_true",
                       help="read the envelope body from stdin, validate it, and — "
                            "only if valid — land it at the substrate-resolved path "
                            "(the ONE place the gate reads; D-0148). A malformed "
                            "envelope bounces with its errors and touches nothing.")
    ap.add_argument("--root", default=".", help="write: the project (any subdirectory)")
    args = ap.parse_args(argv)

    if args.write:
        # The judge writes THROUGH this path so it can neither hand-build the
        # location nor land a document the checker would refuse. Validate first,
        # write second — the filesystem only ever meets a valid envelope.
        text = stdin_text if stdin_text is not None else sys.stdin.read()
        res = check_text(text)
        if res["verdict"] != "valid-pass":
            print(json.dumps(res))
            return 1
        import friday_substrate as fs
        path = fs.envelope_path(args.root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
        res["path"] = path
        print(json.dumps(res))
        return 0

    try:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(json.dumps({"verdict": "valid-fail",
                          "errors": [f"envelope missing or unreadable: {exc}"],
                          "summary": "maintainability envelope INVALID: the document being "
                                     f"consumed does not exist at {args.file}"}))
        return 1
    res = check_text(text)
    print(json.dumps(res))
    return 0 if res["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
