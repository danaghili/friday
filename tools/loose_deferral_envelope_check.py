#!/usr/bin/env python3
"""Loose-deferral envelope checker (INC-107 FR-107.10).

Contract: docs/contracts/loose-deferral-envelope.md — the deep clean's run
emits the envelope, this checker consumes it and the producer writes THROUGH
it. A sibling of the maintainability envelope by that contract's own
reasoning (D10): the findings brief carries a *severity* axis, the
maintainability envelope a *disposition* axis; this seam's axis is *whether a
decision has a route back*, and the answer comes from the PM rather than a
judge. Same structural pattern, same tagline grammar, its own contract. The
shape:

    loose-deferral-envelope: source=deep-clean count=N remainder=R recognized=K unread=U unparsed=P

    ## LD-n — <file>:<start>-<end> (recommend: capture|dismiss|leave-standing|already-homed)
    id:      <the answered-set identity digest>
    text:    <flattened, value-masked block text>
    reading: <the in-context read — why this is or is not a real deferral>
    home:    homed|homeless|unanswerable — <what was read and what it said>

    ## Unreached        (REQUIRED when unread+unparsed > 0)
    unread: <path>
    unparsed: <path>

    ## Scanned          (REQUIRED when count=0 — the first-class empty case)
    <what was scanned — non-empty>

`count` must be the TRUE number of candidates; a heading that looks like a
candidate but does not parse is an ERROR, never tolerated prose (a dropped
candidate is the silent miss this line of work exists to end, S-107.2); the
remainder and the recognised-and-passed-over count ride the tag line so a
capped run and a no-re-ask run are both honest by construction (FR-107.7,
FR-107.6); what the scan could not reach is named line by line, matching the
declared counts (FR-107.8).

Verdict rides stdout as ONE JSON object (the FR-61 shape). Exit codes:
0 pass · 1 fail · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

SOURCES = ("deep-clean",)
RECOMMENDATIONS = ("capture", "dismiss", "leave-standing", "already-homed")
HOME_ANSWERS = ("homed", "homeless", "unanswerable")
FIELDS = ("id", "text", "reading", "home")
COUNT_KEYS = ("count", "remainder", "recognized", "unread", "unparsed")

_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_FINDING_RE = re.compile(
    r"^LD-(\d+)\s+—\s+(.+?):(\d+)-(\d+)\s+\(recommend:\s*([a-z-]+)\)$")
_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_HOME_RE = re.compile(r"^(homed|homeless|unanswerable)\s+—\s+\S.*$", re.DOTALL)


def _parse_header(line: str, errors: list[str]) -> tuple[str | None, dict]:
    parsed = taglines.parse_typed_line(line)
    if not parsed or parsed[0] != "loose-deferral-envelope":
        errors.append("the first line must be the `loose-deferral-envelope:` tag "
                      "line (`loose-deferral-envelope: source=deep-clean count=N "
                      "remainder=R recognized=K unread=U unparsed=P`) — see "
                      "docs/contracts/loose-deferral-envelope.md")
        return None, {}
    fields = dict(tok.split("=", 1) for tok in parsed[1].split() if "=" in tok)
    source = fields.get("source")
    if source not in SOURCES:
        errors.append(f"source must be one of {'|'.join(SOURCES)}, got {source!r}")
        source = None
    counts: dict = {}
    for key in COUNT_KEYS:
        try:
            val = int(fields.get(key, ""))
            if val < 0:
                raise ValueError
            counts[key] = val
        except ValueError:
            errors.append(f"{key} must be a whole number, got {fields.get(key)!r}")
            counts[key] = None
    return source, counts


def _sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for ln in lines:
        m = _H2_RE.match(ln)
        if m:
            out.append((m.group(1), []))
        elif out:
            out[-1][1].append(ln)
    return out


def _check_candidate(heading: str, body: list[str], errors: list[str]) -> dict | None:
    """One `## LD-n` section → finding dict, its field errors appended.
    A heading that looks like a candidate but does not parse is an ERROR
    returned as None — never tolerated prose (S-107.2)."""
    m = _FINDING_RE.match(heading)
    if not m:
        errors.append(f"the heading {heading!r} looks like a candidate but "
                      "does not parse — expected `## LD-n — <file>:<start>-"
                      "<end> (recommend: capture|dismiss|leave-standing|"
                      "already-homed)`")
        return None
    n = int(m.group(1))
    file, start, end, recommend = m.group(2), int(m.group(3)), int(m.group(4)), m.group(5)
    if recommend not in RECOMMENDATIONS:
        errors.append(f"LD-{n} recommends {recommend!r} — must be one of "
                      f"{'|'.join(RECOMMENDATIONS)}")
    typed = {}
    for ln in body:
        parsed = taglines.parse_typed_line(ln)
        if parsed and parsed[0] in FIELDS:
            typed[parsed[0]] = parsed[1].strip()
    for field in FIELDS:
        if not typed.get(field, ""):
            errors.append(f"LD-{n} is missing its `{field}:` line — every "
                          "candidate carries its identity, its text, its "
                          "reading, and its home answer")
    ident = typed.get("id", "")
    if ident and not _ID_RE.match(ident):
        errors.append(f"LD-{n} id {ident!r} — must be the answered-set "
                      "identity digest (12 hex chars, tools/loose_deferrals.py)")
    home = typed.get("home", "")
    if home and not _HOME_RE.match(home):
        errors.append(f"LD-{n} home {home!r} — must be `homed|homeless|"
                      "unanswerable — <evidence>` (the home test's answer "
                      "with what was read, FR-107.4)")
    return {"n": n, "file": file, "line_start": start, "line_end": end,
            "recommend": recommend, "id": ident, "text": typed.get("text", ""),
            "reading": typed.get("reading", ""), "home": home}


def _check_totals(counts: dict, findings: list[dict], scanned_body: list[str] | None,
                  unreached: dict, errors: list[str]) -> None:
    """The header's numbers against the document's own contents: unique
    candidate numbers, a truthful count, the first-class empty case, and
    the Unreached section matching the declared unread/unparsed."""
    ids = [f["n"] for f in findings]
    for dup in sorted({n for n in ids if ids.count(n) > 1}):
        errors.append(f"LD-{dup} appears more than once — candidate numbers "
                      "must be unique")
    declared = counts.get("count")
    if declared is not None and declared != len(findings):
        errors.append(f"the header declares count={declared} but the envelope "
                      f"holds {len(findings)} candidate(s) — the header must "
                      "state the true count")
    if declared == 0 and not findings:
        if scanned_body is None or not any(ln.strip() for ln in scanned_body):
            errors.append("count=0 requires a non-empty `## Scanned` section — "
                          "a run that reached nothing must not read the same "
                          "as a run that found nothing (FR-107.8)")
    for key in ("unread", "unparsed"):
        want = counts.get(key)
        if want is not None and want != unreached[key]:
            errors.append(f"the header declares {key}={want} but the `## "
                          f"Unreached` section names {unreached[key]} — what "
                          "the scan could not reach is named line by line, "
                          "never absorbed into a count")


def check_text(text: str) -> dict:
    errors: list[str] = []
    lines = text.splitlines()
    non_blank = [ln for ln in lines if ln.strip()]
    source, counts = _parse_header(non_blank[0] if non_blank else "", errors)

    findings: list[dict] = []
    scanned_body: list[str] | None = None
    unreached: dict[str, int] = {"unread": 0, "unparsed": 0}
    for heading, body in _sections(lines):
        if heading == "Scanned":
            scanned_body = body
        elif heading == "Unreached":
            for ln in body:
                parsed = taglines.parse_typed_line(ln)
                if parsed and parsed[0] in unreached and parsed[1].strip():
                    unreached[parsed[0]] += 1
        elif heading.startswith("LD-"):
            finding = _check_candidate(heading, body, errors)
            if finding is not None:
                findings.append(finding)
        # unknown sections tolerated; candidates are never guessed at

    _check_totals(counts, findings, scanned_body, unreached, errors)

    out = {"source": source, "count": len(findings),
           "remainder": counts.get("remainder"),
           "recognized": counts.get("recognized"), "findings": findings}
    if errors:
        return {**out, "verdict": "valid-fail", "errors": errors,
                "summary": f"loose-deferral envelope INVALID: {len(errors)} "
                           f"problem(s) — {errors[0]}"}
    return {**out, "verdict": "valid-pass", "errors": [],
            "summary": (f"loose-deferral envelope OK: source={source} "
                        f"count={len(findings)} remainder={counts.get('remainder')} "
                        f"recognized={counts.get('recognized')}"
                        + ("" if findings else " (empty case: Scanned section present)"))}


def main(argv: list[str] | None = None, stdin_text: str | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate — or validate-then-write — "
                                             "a loose-deferral envelope (contract: "
                                             "docs/contracts/loose-deferral-envelope.md)")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="validate an existing envelope at this path")
    group.add_argument("--write", action="store_true",
                       help="read the envelope body from stdin, validate it, and — "
                            "only if valid — land it at the substrate-resolved path "
                            "(the D-0148 pattern). A malformed envelope bounces "
                            "with its errors and touches nothing.")
    ap.add_argument("--root", default=".", help="write: the project (any subdirectory)")
    args = ap.parse_args(argv)

    if args.write:
        # The producer writes THROUGH this path so it can neither hand-build
        # the location nor land a document the checker would refuse.
        text = stdin_text if stdin_text is not None else sys.stdin.read()
        res = check_text(text)
        if res["verdict"] != "valid-pass":
            print(json.dumps(res))
            return 1
        import friday_substrate as fs
        path = fs.loose_deferral_envelope_path(args.root)
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
                          "summary": "loose-deferral envelope INVALID: the document "
                                     f"being consumed does not exist at {args.file}"}))
        return 1
    res = check_text(text)
    print(json.dumps(res))
    return 0 if res["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
