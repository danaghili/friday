#!/usr/bin/env python3
"""Document-gate family checker — guard #9's judgment (TECHNICAL_SOW_REBUILD
US-12: FR-64 "load-bearing fields present, IDs unique, grammar parsed"; FR-67
provenance; FR-65 empty cases; AC-16).

One checker, four build-feeding document kinds, validated at CONSUMPTION time:

- **spec** — carries a `provenance:` claim (`born-from-discovery` |
  `recovered-from-code`, FR-67) and at least one requirement-ID DECLARATION,
  each declared exactly once. Uniqueness is judged over line-start
  declarations (`- **FR-1** …`, `| AC-2 |`) — the line-start half of
  tools/verify_coverage.py's extraction idiom. A bold mid-prose mention
  ("**FR-78's** relocation…" in the rebuild oracle's own amendments block is
  the live example) is a reference, never a second declaration.
- **increment** — dotted IDs only (`FR-n.m`; an undotted ID would collide
  with the parent oracle's space — cf. skills/feature/SKILL.md), at least one.
  With --parent, the parent's `## Increments` section must point at this
  file: an orphan increment being consumed is a provable failure; an
  unreadable parent degrades to structural-only with a note (fail-open
  evidence rules, as in trail_check).
- **findings-brief** — delegates to tools/findings_brief_check.py (one
  grammar, one home; contract: docs/contracts/findings-brief.md).
- **intake-brief** — contract: docs/contracts/intake-brief.md (cited on both
  sides). Formal sign-off half (goals / scope / exclusions / budget /
  timeline / approver + the PM-amendment-4 consumer-expected fields:
  data-sovereignty, hosting-sla, payment-ip-exit, client-tier), informal
  half, glossary — populated, or exactly the sentinel empty case.

Verdict rides stdout as ONE JSON object (FR-61 shape, consumed by
hooks/_guard.py). A missing/unreadable document FILE is valid-fail — the
gate fires at consumption time, and consuming an absent document is the
failure. Exit codes: 0 pass · 1 fail · 2 bad invocation (no verdict).
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
import findings_brief_check  # noqa: E402
import taglines  # noqa: E402

KINDS = ("spec", "increment", "findings-brief", "intake-brief")
PROVENANCES = taglines.PROVENANCE_VALUES  # one home for the vocabulary (FR-67)
GLOSSARY_NONE = "glossary: none — no client-specific terms arose"
FORMAL_FIELDS = ("goals", "scope", "exclusions", "budget", "timeline", "approver",
                 "data-sovereignty", "hosting-sla", "payment-ip-exit", "client-tier")
# The optional Brownfield block (D-0042): present for an existing-site
# engagement, omitted for greenfield — its fields are load-bearing when present.
BROWNFIELD_FIELDS = ("assessment", "direction", "keys")

# Line-start declarations only — the anchored half of verify_coverage's
# _ANCHORED_ID_RE. Its `\*\*ID` mid-prose alternative stays out on purpose:
# references never mint (or re-mint) a requirement.
_DECL_RE = re.compile(r"^\s*[|\-*]\s*\**((?:FR|NFR|AC|S)-\d+(?:\.\d+)?)\b", re.M)
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
_GLOSSARY_TERM_RE = re.compile(r"^\s*-\s+.+?\s+—\s+.+$")


def _iso_ok(s: str) -> bool:
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _verdict(errors: list[str], ok_summary: str) -> dict:
    if errors:
        return {"verdict": "valid-fail", "errors": errors,
                "summary": f"document gate REFUSED: {len(errors)} problem(s) — {errors[0]}"}
    return {"verdict": "valid-pass", "errors": [], "summary": ok_summary}


def _sections(text: str) -> list[tuple[str, list[str]]]:
    """(heading, body lines) for every H2, in order."""
    out: list[tuple[str, list[str]]] = []
    for ln in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            out.append((m.group(1), []))
        elif out:
            out[-1][1].append(ln)
    return out


# --- spec ---------------------------------------------------------------------------

def check_spec(text: str) -> dict:
    errors: list[str] = []
    prov = None
    for ln in text.splitlines():
        parsed = taglines.parse_typed_line(ln)
        if parsed and parsed[0] == "provenance":
            prov = parsed[1].strip()
            break
    if prov is None:
        errors.append("the spec carries no `provenance:` line — every spec states "
                      f"{' or '.join(PROVENANCES)} so no checker mistakes an adopted "
                      "spec's authority for an interrogated one's (FR-67)")
    elif prov not in PROVENANCES:
        errors.append(f"provenance must be {' or '.join(PROVENANCES)}, got {prov!r}")

    decls = _DECL_RE.findall(text)
    if not decls:
        errors.append("the spec declares no requirement IDs — a document with no "
                      "anchored FR/NFR/AC/S rows cannot gate a build")
    for dup in sorted({d for d in decls if decls.count(d) > 1}):
        errors.append(f"{dup} is declared more than once — requirement IDs are "
                      "declared exactly once (references in prose don't count)")
    return _verdict(errors, f"spec OK: provenance={prov}, "
                            f"{len(decls)} requirement ID(s) declared once each")


# --- increment ------------------------------------------------------------------------

def check_increment(text: str, *, basename: str, parent_text: str | None = None,
                    parent_error: str | None = None) -> dict:
    errors: list[str] = []
    decls = _DECL_RE.findall(text)
    if not decls:
        errors.append("the increment declares no requirement IDs — an increment "
                      "exists to add requirements; none were found")
    for d in decls:
        if "." not in d:
            errors.append(f"{d} is not a dotted ID — increment IDs are FR-n.m / "
                          "AC-n.m / S-n.m so they can never collide with the "
                          "parent oracle's space")
    for dup in sorted({d for d in decls if decls.count(d) > 1}):
        errors.append(f"{dup} is declared more than once")

    note = ""
    if parent_text is not None:
        inc_bodies = [body for heading, body in _sections(parent_text)
                      if heading.startswith("Increments")]
        if not inc_bodies:
            errors.append("the parent spec has no `## Increments` section — an "
                          "increment must be pointer-linked from its parent "
                          "before it is consumed")
        elif not any(basename in ln for body in inc_bodies for ln in body):
            errors.append(f"the parent spec's `## Increments` section has no pointer "
                          f"to {basename} — an unapproved orphan increment cannot "
                          "feed a build")
    elif parent_error is not None:
        note = " — parent spec unreadable, pointer not cross-checked"

    return _verdict(errors, f"increment OK: {len(decls)} dotted ID(s), "
                            f"pointer-linked{' and verified' if parent_text else ''}" + note)


# --- intake-brief -----------------------------------------------------------------------

def check_intake(text: str) -> dict:
    errors: list[str] = []
    non_blank = [ln for ln in text.splitlines() if ln.strip()]
    header = taglines.parse_typed_line(non_blank[0]) if non_blank else None
    if not header or header[0] != "intake-brief":
        errors.append("the first line must be the `intake-brief:` tag line "
                      "(`intake-brief: client=… date=…`) — see "
                      "docs/contracts/intake-brief.md")
    else:
        pairs = dict(re.findall(r"(\S+)=(.*?)(?=\s+\S+=|\s*$)", header[1]))
        if not pairs.get("client", "").strip():
            errors.append("the intake-brief: line is missing client= (who this is for)")
        if not _iso_ok(pairs.get("date", "")):
            errors.append(f"date must be ISO-8601, got {pairs.get('date')!r}")

    formal = informal = glossary = brownfield = None
    for heading, body in _sections(text):
        if heading.startswith("Formal"):
            formal = body
        elif heading.startswith("Informal"):
            informal = body
        elif heading.startswith("Glossary"):
            glossary = body
        elif heading.startswith("Brownfield"):
            brownfield = body

    if formal is None:
        errors.append("missing the `## Formal` half — the sign-off record "
                      "(goals, scope, exclusions, budget, timeline, approver, "
                      "and the consumer-expected fields)")
    else:
        typed = {}
        for ln in formal:
            parsed = taglines.parse_typed_line(ln)
            if parsed:
                typed[parsed[0]] = parsed[1]
        for field in FORMAL_FIELDS:
            if not typed.get(field, "").strip():
                errors.append(f"the Formal half is missing its `{field}:` line — "
                              "a consumer downstream expects it filled in")

    if informal is None or not any(ln.strip() for ln in informal):
        errors.append("missing (or empty) `## Informal` half — rapport notes and "
                      "preferences are part of the record, not chat exhaust")

    if glossary is None:
        errors.append("missing the `## Glossary` section — every client term a "
                      "stranger would stumble on, defined in plain words")
    else:
        lines = [ln.strip() for ln in glossary if ln.strip()]
        terms = [ln for ln in lines if _GLOSSARY_TERM_RE.match(ln)]
        sentinel = [ln for ln in lines if ln == GLOSSARY_NONE]
        if sentinel and terms:
            errors.append("the glossary claims 'none' and lists terms — it must "
                          "be one or the other")
        elif not sentinel and not terms:
            errors.append(f"the glossary is empty — list `- <term> — <plain words>` "
                          f"entries, or state exactly `{GLOSSARY_NONE}`")

    # The Brownfield block is first-class OPTIONAL: absent = greenfield (fine);
    # present = its three fields are load-bearing (D-0042).
    if brownfield is not None:
        typed = {}
        for ln in brownfield:
            parsed = taglines.parse_typed_line(ln)
            if parsed:
                typed[parsed[0]] = parsed[1]
        for field in BROWNFIELD_FIELDS:
            if not typed.get(field, "").strip():
                errors.append(f"the Brownfield block is present but its `{field}:` line "
                              "is missing or empty — for an existing-site engagement "
                              "assessment/direction/keys are load-bearing (D-0042)")

    return _verdict(errors, "intake brief OK: both halves present, glossary "
                            + ("populated" if glossary and any(
                                _GLOSSARY_TERM_RE.match(ln.strip()) for ln in glossary)
                               else "empty case declared"))


# --- S-4: research consumer-citation check (AC-12) -------------------------------------

def _names_file(text: str, name: str) -> bool:
    """True when `text` mentions `name` as a whole filename token — never a
    substring (`my-sow.md` does not name `sow.md`; `release-notes.md` does
    not satisfy `notes.md`), case-insensitive (case tricks neither dodge a
    binding nor invalidate a citation). Boundary = any char that could be
    part of a filename token."""
    return re.search(rf"(?<![A-Za-z0-9_.-]){re.escape(name)}(?![A-Za-z0-9_-])",
                     text, re.IGNORECASE) is not None


def _research_citation_errors(text: str, basename: str, research_dir: str | None) -> list[str]:
    """Blocking half of the S-4 rule, provable-lie-only: a research brief
    whose `consumer:` line explicitly NAMES this document's filename (whole
    token — see _names_file) must be cited in it (grep-able Sources line) or
    dispositioned ("superseded — reason" — either way the brief's filename
    appears in the document). Prose-only consumer lines that name no file are
    guard #14's warn-tier sweep, never blockable here — ambiguity is not a
    lie. A brief that can't be read (missing, binary, wrong encoding) is
    skipped, never a crash — a crash here would fail the WHOLE consumption
    gate open. Empty case: an absent/empty research dir returns []."""
    if not research_dir or not basename or not os.path.isdir(research_dir):
        return []
    errors: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(research_dir):
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding="utf-8") as fh:
                    brief = fh.read()
            except (OSError, UnicodeDecodeError):
                continue
            consumer = ""
            for ln in brief.splitlines():
                parsed = taglines.parse_typed_line(ln)
                if parsed and parsed[0] == "consumer":
                    consumer = parsed[1]
                    break
            if _names_file(consumer, basename) and not _names_file(text, fn):
                errors.append(f"the research brief {fn} names this document as its "
                              "consumer, but the document neither cites it in a "
                              "Sources line nor dispositions it ('superseded — "
                              "<reason>') — commissioned research is consumed or "
                              "dispositioned, never silently dropped")
    return errors


# --- dispatcher + CLI ----------------------------------------------------------------------

def check(kind: str, text: str, *, basename: str = "", parent_text: str | None = None,
          parent_error: str | None = None, research_dir: str | None = None) -> dict:
    if kind == "spec":
        res = check_spec(text)
    elif kind == "increment":
        res = check_increment(text, basename=basename, parent_text=parent_text,
                              parent_error=parent_error)
    elif kind == "findings-brief":
        res = findings_brief_check.check_text(text)
    elif kind == "intake-brief":
        res = check_intake(text)
    else:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")

    s4_errors = _research_citation_errors(text, basename, research_dir)
    if s4_errors:
        errors = res.get("errors", []) + s4_errors
        return {**res, "verdict": "valid-fail", "errors": errors,
                "summary": f"document gate REFUSED: {len(errors)} problem(s) — {errors[0]}"}
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate a build-feeding document at "
                                             "consumption time (guard #9's checker)")
    ap.add_argument("--kind", required=True, choices=KINDS)
    ap.add_argument("--file", required=True, help="path to the document")
    ap.add_argument("--parent", default=None,
                    help="increment only: the parent spec whose ## Increments "
                         "section must point at --file")
    ap.add_argument("--research-dir", default=None,
                    help="S-4: also verify every research brief whose consumer: "
                         "line names --file is cited or dispositioned in it")
    args = ap.parse_args(argv)

    try:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(json.dumps({"verdict": "valid-fail",
                          "errors": [f"document missing or unreadable: {exc}"],
                          "summary": f"document gate REFUSED: the {args.kind} being "
                                     f"consumed does not exist at {args.file}"}))
        return 1

    parent_text = parent_error = None
    if args.parent is not None:
        try:
            with open(args.parent, encoding="utf-8") as fh:
                parent_text = fh.read()
        except OSError as exc:
            parent_error = str(exc)

    res = check(args.kind, text, basename=os.path.basename(args.file),
                parent_text=parent_text, parent_error=parent_error,
                research_dir=args.research_dir)
    print(json.dumps(res))
    return 0 if res["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
