#!/usr/bin/env python3
"""Findings-brief checker (TECHNICAL_SOW_REBUILD US-12: FR-63, FR-65; AC-16;
the FR-42 structural PoC cap via the §7 pin "PoC-or-informational discipline").

Contract: docs/contracts/findings-brief.md — harden / security / redteam /
adopt emit the brief, this checker + the document gate (guard #9) consume it.
The shape:

    findings-brief: source=harden|security|redteam|adopt count=N

    ## F-n — <title> (severity: act-now|before-growth|track|informational)
    evidence: <file:line or PoC pointer; `none — <reason>` ONLY at informational>
    explained: <plain words a stranger can act on>
    fixed-when: <how we'd know it's fixed>

    ## Checked            (REQUIRED when count=0 — the first-class empty case)
    <what was examined — non-empty>

The PoC cap is structural, not aspirational: `evidence: none — <reason>` is
legal only at severity informational (every source), so a finding that points
at nothing CANNOT hold a grade above informational — no PoC, nothing above
informational. `count` must state the true number of findings (a header that
lies about its own count is exactly the kind of drift this gate exists for).

Verdict rides stdout as ONE JSON object (FR-61 shape, consumed by
hooks/_guard.py). A missing/unreadable brief FILE is valid-fail — the gate
fires at consumption time, and consuming an absent document is the failure.
Exit codes: 0 pass · 1 fail · 2 bad invocation (no verdict printed).
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

SOURCES = ("harden", "security", "redteam", "adopt")
SEVERITIES = ("act-now", "before-growth", "track", "informational")
FIELDS = ("evidence", "explained", "fixed-when")

_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_FINDING_RE = re.compile(r"^F-(\d+)\s+—\s+(.+?)\s+\(severity:\s*([a-z-]+)\)$")

# A7 (harden): evidence above `informational` must be a CONCRETE pointer, not a
# placeholder — the §7 PoC cap made structural (invert the old "not the word
# none" test, which passed `n/a`/`pending`/`see above`). A file, file:line,
# §section, spec-ID (FR-/AC-/S-/D-n), PoC/experiment reference, or URL qualifies.
_EVIDENCE_SHAPE = re.compile(
    r"[\w.\-]+/[\w./\-]+"
    r"|[\w.\-]+\.(?:py|md|js|ts|jsx|tsx|json|jsonl|txt|sh|ya?ml|toml)\b"
    r"|:\d+"
    r"|\bPoC\b|experiment|EXP-\d|reproduc|https?://"
    r"|§|\b(?:FR|NFR|AC|US|S|D)-\d", re.I)

# Bare placeholders that are NOT evidence (some, like "n/a", incidentally match a
# shape above — the denylist wins). "none — <reason>" is legal ONLY at informational,
# handled by the severity gate below.
_PLACEHOLDER_EVIDENCE = frozenset({
    "", "-", "n/a", "na", "none", "tbd", "todo", "pending", "see above",
    "unknown", "reasoning", "reasoned", "n.a."})


def _parse_header(line: str, errors: list[str]) -> tuple[str | None, int | None]:
    parsed = taglines.parse_typed_line(line)
    if not parsed or parsed[0] != "findings-brief":
        errors.append("the first line must be the `findings-brief:` tag line "
                      "(`findings-brief: source=… count=N`) — see "
                      "docs/contracts/findings-brief.md")
        return None, None
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
    return source, count


def _sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    """(heading, body lines) for every H2, in order, duplicates preserved."""
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
    source, declared = _parse_header(non_blank[0] if non_blank else "", errors)

    findings: list[dict] = []
    checked_body: list[str] | None = None
    for heading, body in _sections(lines):
        if heading == "Checked":
            checked_body = body
            continue
        if not heading.startswith("F-"):
            continue  # unknown sections are tolerated; findings are not guessed at
        m = _FINDING_RE.match(heading)
        if not m:
            errors.append(f"the heading {heading!r} looks like a finding but does not "
                          "parse — expected `## F-n — <title> (severity: "
                          f"{'|'.join(SEVERITIES)})`")
            continue
        n, title, severity = int(m.group(1)), m.group(2), m.group(3)
        if severity not in SEVERITIES:
            errors.append(f"F-{n} has severity {severity!r} — must be one of "
                          f"{'|'.join(SEVERITIES)}")
        typed = {}
        for ln in body:
            parsed = taglines.parse_typed_line(ln)
            if parsed and parsed[0] in FIELDS:
                typed[parsed[0]] = parsed[1]
        for field in FIELDS:
            if not typed.get(field, "").strip():
                errors.append(f"F-{n} is missing its `{field}:` line — every finding "
                              "carries evidence, a plain-words explanation, and "
                              "how we'd know it's fixed")
        evidence = typed.get("evidence", "").strip()
        ev_norm = evidence.lower().rstrip(".").strip()
        vague = (ev_norm in _PLACEHOLDER_EVIDENCE
                 or ev_norm.startswith(("none ", "none—", "none —", "n/a ", "tbd ",
                                        "todo ", "pending ", "see above")))
        if severity != "informational" and (vague or not _EVIDENCE_SHAPE.search(evidence)):
            errors.append(f"F-{n} claims severity {severity!r} but its evidence is not a "
                          "concrete pointer (a file, file:line, §section, spec-ID, PoC, or "
                          "experiment) — no PoC, nothing above informational: point at real "
                          "evidence or downgrade the finding to informational")
        findings.append({"n": n, "title": title, "severity": severity})

    ids = [f["n"] for f in findings]
    for dup in sorted({n for n in ids if ids.count(n) > 1}):
        errors.append(f"F-{dup} appears more than once — finding numbers must be unique")

    if declared is not None and declared != len(findings):
        errors.append(f"the header declares count={declared} but the brief holds "
                      f"{len(findings)} finding(s) — the header must state the true count")

    if declared == 0 and not findings:
        if checked_body is None or not any(ln.strip() for ln in checked_body):
            errors.append("count=0 requires a non-empty `## Checked` section — "
                          "\"no findings\" only counts when the brief says what "
                          "was examined")

    if errors:
        return {"verdict": "valid-fail", "errors": errors, "source": source,
                "count": len(findings),
                "summary": f"findings brief INVALID: {len(errors)} problem(s) — {errors[0]}"}
    return {"verdict": "valid-pass", "errors": [], "source": source,
            "count": len(findings),
            "summary": (f"findings brief OK: source={source} count={len(findings)}"
                        + ("" if findings else " (empty case: Checked section present)"))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate a findings brief (contract: "
                                             "docs/contracts/findings-brief.md)")
    ap.add_argument("--file", required=True, help="path to the findings-brief markdown")
    args = ap.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(json.dumps({"verdict": "valid-fail",
                          "errors": [f"findings brief missing or unreadable: {exc}"],
                          "summary": "findings brief INVALID: the document being "
                                     f"consumed does not exist at {args.file}"}))
        return 1
    res = check_text(text)
    print(json.dumps(res))
    return 0 if res["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
