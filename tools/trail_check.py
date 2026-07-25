#!/usr/bin/env python3
"""Change-trail checker — one grammar, three sizes (TECHNICAL_SOW_REBUILD
US-12: FR-62, FR-65; AC-16; §7 pin "Trail grammar at three sizes").

Contract: docs/contracts/change-trail.md — the lanes (bug/patch/feature)
emit the trail, this checker + guard #6 consume it. The shape:

    trail: lane=bug|patch|feature id=<token> date=<ISO8601>

    ## Asked
    <what was asked or found — non-empty>

    ## Decisions
    - D-NNNN — <title>            (references into docs/DECISIONS.md)
        …or exactly, when no decisions arose (the tested empty case):
    decisions: none — change fully specified by the ask

    ## Proof
    proof: <real command output, quoted>   (at least one; never empty)

    changelog: <one line>                  (exactly one in the document)

Decision references are POINTERS into the single decision log, never
embedded copies — two copies drift. With --decisions-log, a reference
absent from a READABLE log is a provable lie → valid-fail; an unreadable
or unparseable log degrades to structural-only with a note (a missing log
is not a lie — the fail-open doctrine reaches the checker's evidence rules).

Verdict rides stdout as ONE JSON object (FR-61 typed-verdict shape consumed
by hooks/_guard.py): {"verdict": "valid-pass"|"valid-fail", "summary": ...,
"errors": [...]}. A missing/unreadable trail FILE is valid-fail — the absent
record is the exact failure guard #6 exists to catch, not a malfunction.
Exit codes: 0 pass · 1 fail · 2 bad invocation (no verdict printed).
Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decisions  # noqa: E402
import taglines  # noqa: E402

LANES = ("bug", "patch", "feature")
EMPTY_DECISIONS = "decisions: none — change fully specified by the ask"
SECTIONS = ("Asked", "Decisions", "Proof")

_REF_RE = re.compile(r"^\s*-\s*(D-\d{4,})\s+—\s+(.+?)\s*$")
_H2_RE = re.compile(r"^##\s+(.+?)\s*$")


def _parse_header(line: str, errors: list[str]) -> dict:
    parsed = taglines.parse_typed_line(line)
    if not parsed or parsed[0] != "trail":
        errors.append("the first line must be the `trail:` tag line "
                      "(`trail: lane=… id=… date=…`) — see docs/contracts/change-trail.md")
        return {}
    fields: dict[str, str] = {}
    for token in parsed[1].split():
        if "=" not in token:
            errors.append(f"the trail: line has a malformed piece {token!r} — "
                          "every piece must be key=value")
            continue
        k, v = token.split("=", 1)
        fields[k] = v
    if fields.get("lane") not in LANES:
        errors.append(f"lane must be one of {'|'.join(LANES)}, got {fields.get('lane')!r}")
    if not fields.get("id"):
        errors.append("the trail: line is missing its id= (the change's own identifier)")
    date = fields.get("date", "")
    try:
        datetime.fromisoformat(date.replace("Z", "+00:00") if date else "")
    except ValueError:
        errors.append(f"date must be ISO-8601 (like 2026-07-14 or "
                      f"2026-07-14T12:00:00Z), got {date!r}")
    return fields


def _split_sections(lines: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """{heading: body lines} for every H2, plus heading order of the known three."""
    bodies: dict[str, list[str]] = {}
    order: list[str] = []
    current: str | None = None
    for ln in lines:
        m = _H2_RE.match(ln)
        if m:
            current = m.group(1)
            bodies.setdefault(current, [])
            if current in SECTIONS:
                order.append(current)
            continue
        if current is not None:
            bodies[current].append(ln)
    return bodies, order


def check_text(text: str, decisions_text: str | None = None,
               decisions_log_error: str | None = None) -> dict:
    """The whole grammar as a pure function; tests drive this directly."""
    errors: list[str] = []
    lines = text.splitlines()
    non_blank = [ln for ln in lines if ln.strip()]
    fields = _parse_header(non_blank[0] if non_blank else "", errors)

    bodies, order = _split_sections(lines)
    for name in SECTIONS:
        if name not in bodies:
            errors.append(f"missing the `## {name}` section")
    expected = [s for s in SECTIONS if s in order]
    if order and order != expected:
        errors.append("sections are out of order — the trail reads "
                      "Asked, then Decisions, then Proof")
    if len(order) != len(set(order)):
        errors.append("a section appears twice — each of Asked/Decisions/Proof "
                      "appears exactly once")

    if "Asked" in bodies and not any(ln.strip() for ln in bodies["Asked"]):
        errors.append("the Asked section is empty — say what was asked or found")

    refs: list[str] = []
    if "Decisions" in bodies:
        dec_lines = [ln.strip() for ln in bodies["Decisions"] if ln.strip()]
        sentinel = [ln for ln in dec_lines if ln == EMPTY_DECISIONS]
        for ln in dec_lines:
            m = _REF_RE.match(ln)
            if m:
                refs.append(m.group(1))
            elif ln != EMPTY_DECISIONS:
                errors.append(f"the Decisions section holds {ln!r} — every line must "
                              "be a `- D-NNNN — <title>` reference into docs/DECISIONS.md, "
                              f"or exactly `{EMPTY_DECISIONS}` when none arose")
        if sentinel and refs:
            errors.append("the Decisions section claims both 'none' and actual "
                          "decision references — it must be one or the other")
        if not sentinel and not refs:
            errors.append("the Decisions section is empty — list `- D-NNNN — <title>` "
                          f"references, or state exactly `{EMPTY_DECISIONS}`")

    proof_count = 0
    if "Proof" in bodies:
        for ln in bodies["Proof"]:
            parsed = taglines.parse_typed_line(ln)
            if parsed and parsed[0] == "proof":
                proof_count += 1
        if proof_count == 0:
            errors.append("the Proof section has no `proof:` line — quote the real "
                          "command output that shows the change works (proof is the "
                          "point; a trail is never closed without it)")

    changelogs = [ln for ln in lines
                  if (p := taglines.parse_typed_line(ln)) and p[0] == "changelog"]
    if len(changelogs) != 1:
        errors.append(f"expected exactly one `changelog:` line, found {len(changelogs)}")

    note = ""
    if refs and decisions_text is not None:
        parsed_log = decisions.parse(decisions_text)
        if parsed_log["ok"]:
            known = {e["id_str"] for e in parsed_log["entries"]}
            for ref in refs:
                if ref not in known:
                    errors.append(f"the trail cites {ref} but the decision log has no "
                                  "such entry — a cited decision must exist in "
                                  "docs/DECISIONS.md")
        else:
            note = " — decision log did not parse cleanly, references not cross-checked"
    elif refs and decisions_log_error is not None:
        note = " — decision log unreadable, references not cross-checked"

    if errors:
        return {"verdict": "valid-fail", "errors": errors, "lane": fields.get("lane"),
                "id": fields.get("id"),
                "summary": f"change trail INVALID: {len(errors)} problem(s) — {errors[0]}"}
    return {"verdict": "valid-pass", "errors": [], "lane": fields.get("lane"),
            "id": fields.get("id"),
            "summary": (f"change trail OK: lane={fields.get('lane')} id={fields.get('id')} "
                        f"({len(refs)} decision reference(s), {proof_count} proof line(s))"
                        + note)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate a change trail (contract: "
                                             "docs/contracts/change-trail.md)")
    ap.add_argument("--file", required=True, help="path to the trail markdown")
    ap.add_argument("--decisions-log", default=None,
                    help="cross-check decision references against this DECISIONS.md")
    args = ap.parse_args(argv)

    try:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        # Plain words, no raw errno — this string reaches PM-facing block
        # texts verbatim (D-0023 item 4).
        print(json.dumps({"verdict": "valid-fail",
                          "errors": [f"no trail record exists at {args.file} — "
                                     "the change's three-part record was never "
                                     "written (or the path is wrong)"],
                          "summary": "change trail INVALID: the required trail record "
                                     f"does not exist at {args.file}"}))
        return 1

    decisions_text = None
    log_error = None
    if args.decisions_log is not None:
        try:
            with open(args.decisions_log, encoding="utf-8") as fh:
                decisions_text = fh.read()
        except OSError as exc:
            log_error = str(exc)

    res = check_text(text, decisions_text=decisions_text, decisions_log_error=log_error)
    print(json.dumps(res))
    return 0 if res["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
