#!/usr/bin/env python3
"""Verdict-artifact verifier for docs/reviews/ — envelope-dispatching (DF-015).

docs/reviews/ holds typed, enveloped verdict artifacts, and this one verifier
guards all of them. It reads the file, decides which verdict grammar the file
declares by the envelope marker it carries, and runs that grammar's checks:

  - FRIDAY-REVIEW       → the reviewer's whole-build review     (R1–R6, below)
  - FRIDAY-RELEASE-GATE → the tester's release gate             (G1–G3)
  - FRIDAY-DISPOSITIONS → the tester's requirement-coverage ledger (D1–D2)

A docs/reviews/*.md that declares NO known envelope is not a review with a
missing header — it is a document in the wrong place; it fails with the
directory contract (sweep warns, --strict-missing blocks). A file declaring
MORE than one family is coherent, not ambiguous — the tester's release-gate.md
and coverage.md each carry a FRIDAY-REVIEW verdict envelope preceding a typed
data block (FRIDAY-RELEASE-GATE / FRIDAY-DISPOSITIONS). Each declared family is
validated against its own grammar and all must pass (failures aggregate); a
duplicated family still blocks on its own one-pair check (R1/G1/D1).

FRIDAY-REVIEW envelope (typed tag lines between FRIDAY-REVIEW:BEGIN/END):
    reviewer: friday-reviewer          # or the custom reviewer's name
    iteration: 1
    verdict: approved | approved-with-minors | changes-required
    spec-compliance: meets-spec | deviations-noted | not-assessed   # §6.8 graft
    finding: 🔴 1 src/x.py:88 — <title>     # zero or more; glyph 🔴|🟡|🟢

Review checks (structural — never the QUALITY of findings; strict on grammar,
precision-first on scope):
  R1 blocking  exactly one BEGIN and one END, BEGIN first.
  R2 blocking  every non-blank line inside the block is `key: value` with a
               known key.
  R3 blocking  reviewer/iteration/verdict/spec-compliance each exactly once;
               iteration a positive integer; closed vocabularies.
  R4 blocking  finding lines parse (`<glyph> <id> <location> — <title>`).
  R5 blocking  verdict↔severity: any 🔴 finding ⇔ verdict changes-required
               (both directions — a stated rationale never downgrades a
               finding, and an approving verdict cannot front a 🔴).
  R6 blocking  envelope↔body bijection: every finding has exactly one heading
               carrying `{glyph}-{id}`, and vice versa.

FRIDAY-RELEASE-GATE envelope (agents/roles/tester.md, skills/harden/SKILL.md):
    reviewer: friday-tester            # known key, optional
    suite: pass | fail                 # each required exactly once
    build: pass | n/a
    migration: pass | n/a
Gate checks:
  G1 blocking  exactly one BEGIN/END pair.
  G2 blocking  every non-blank line is `key: value` with a known key.
  G3 blocking  suite/build/migration each exactly once, value in its vocabulary.

FRIDAY-DISPOSITIONS envelope (agents/roles/tester.md, tools/verify_coverage.py):
    disposition: <ID> implemented — <evidence>   # <ID> is FR/NFR/AC/S-<n>
    disposition: <ID> deferred — <reason>
Disposition checks (line-shape only; set-closure vs the TSOW is
verify_coverage.py's job):
  D1 blocking  exactly one BEGIN/END pair.
  D2 blocking  every non-blank line is a `disposition:` line that parses.

Every grammar's empty case is defined + tested:
  - FRIDAY-REVIEW      empty (zero findings + approving verdict)  → VALID.
  - FRIDAY-RELEASE-GATE empty (no suite/build/migration)          → INVALID
    (the gate must carry a verdict).
  - FRIDAY-DISPOSITIONS empty (nothing to cover)                  → VALID.

Exit codes: 0 ok · 1 blocking failures · 2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

# --- FRIDAY-REVIEW grammar ---------------------------------------------------
VERDICTS = ("approved", "approved-with-minors", "changes-required")
SPEC_COMPLIANCE = ("meets-spec", "deviations-noted", "not-assessed")
KNOWN_KEYS = ("reviewer", "iteration", "verdict", "spec-compliance", "finding")
GLYPHS = ("🔴", "🟡", "🟢")
_FINDING_RE = re.compile(r"^(🔴|🟡|🟢)\s+(\d+)\s+(\S+)\s+—\s+(.+)$")

# --- FRIDAY-RELEASE-GATE grammar ---------------------------------------------
GATE_KNOWN_KEYS = ("reviewer", "suite", "build", "migration")
GATE_VALUES = {"suite": ("pass", "fail"),
               "build": ("pass", "n/a"),
               "migration": ("pass", "n/a")}
GATE_REQUIRED = ("suite", "build", "migration")  # each exactly once

# --- FRIDAY-DISPOSITIONS grammar (mirrors tools/verify_coverage.py, incl.
# dotted increment IDs like FR-1.1 — the two regexes move together) ----------
_DISPO_RE = re.compile(
    r"^((?:FR|NFR|AC|S)-\d+(?:\.\d+)?)\s+(implemented|deferred)\s+—\s+(.+)$")

# The verdict families this directory holds, in declaration-precedence order.
FAMILIES = ("FRIDAY-REVIEW", "FRIDAY-RELEASE-GATE", "FRIDAY-DISPOSITIONS")

# Quoted verbatim by the directory-contract failure (DF-015): a docs/reviews/
# file with no known envelope is misfiled, not a review missing its header.
CONTRACT = ("docs/reviews/ holds typed verdict artifacts "
            "(FRIDAY-REVIEW / FRIDAY-RELEASE-GATE / FRIDAY-DISPOSITIONS); "
            "fix-round ledgers and prose notes live in docs/hardening/ — "
            "relocate and cite by path")


def _declares(text: str, family: str) -> bool:
    """A file declares a verdict family when it carries either marker for it —
    a lone BEGIN or END still declares the family (so a half-written envelope
    dispatches to that grammar's pair check rather than the wrong one)."""
    return (text.count(f"{family}:BEGIN") > 0) or (text.count(f"{family}:END") > 0)


def verify_file(path: str, strict_missing: bool = False) -> dict:
    name = os.path.basename(path)
    failures: list[dict] = []

    def fail(check: str, severity: str, detail: str, owner: str = "reviewer") -> None:
        failures.append({"file": name, "check": check, "severity": severity,
                         "owner": owner, "detail": detail})

    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        fail("R0", "blocking", f"unreadable: {exc}")
        return _result(failures)

    present = [fam for fam in FAMILIES if _declares(text, fam)]

    if not present:
        # No known verdict envelope. Under --strict-missing (a freshly Written
        # artifact) this blocks; in sweep mode it warns. The check code stays
        # R1/warn on the sweep path — the sentinel keys the "still missing"
        # disarm guard on exactly that (hooks/review_format_sentinel.py).
        fail("R1", "blocking" if strict_missing else "warn",
             CONTRACT + (" (a freshly written artifact must declare its "
                         "verdict envelope)" if strict_missing
                         else " (legacy/misfiled artifact — warn only)"))
        return _result(failures)

    # One or more families: a verdict envelope may precede a typed data block
    # (release-gate.md = FRIDAY-REVIEW + FRIDAY-RELEASE-GATE; coverage.md =
    # FRIDAY-REVIEW + FRIDAY-DISPOSITIONS). Validate EACH declared family against
    # its own grammar; failures aggregate. A duplicated family blocks inside its
    # own checker on the one-BEGIN/END-pair rule (R1/G1/D1), which counts only
    # that family's markers, so other families present here don't perturb it.
    for family in present:
        if family == "FRIDAY-REVIEW":
            _check_review(text, fail)
        elif family == "FRIDAY-RELEASE-GATE":
            _check_release_gate(text, fail)
        else:
            _check_dispositions(text, fail)
    return _result(failures)


def _check_review(text: str, fail) -> None:
    begins = text.count("FRIDAY-REVIEW:BEGIN")
    ends = text.count("FRIDAY-REVIEW:END")
    if begins != 1 or ends != 1:
        fail("R1", "blocking",
             f"expected exactly one BEGIN/END pair, got {begins}/{ends}")
        return

    lines = taglines.block_lines(text, "FRIDAY-REVIEW") or []
    typed: list[tuple[str, str]] = []
    for ln in lines:
        parsed = taglines.parse_typed_line(ln)
        if not parsed or parsed[0] not in KNOWN_KEYS:
            fail("R2", "blocking", f"unknown/unparseable envelope line: {ln!r}")
        else:
            typed.append(parsed)

    by_key: dict[str, list[str]] = {}
    for k, v in typed:
        by_key.setdefault(k, []).append(v)
    for key in ("reviewer", "iteration", "verdict", "spec-compliance"):
        if len(by_key.get(key, [])) != 1:
            fail("R3", "blocking",
                 f"{key}: must appear exactly once (got {len(by_key.get(key, []))})")
    iteration = by_key.get("iteration", [""])[0]
    if iteration and not (iteration.isdigit() and int(iteration) > 0):
        fail("R3", "blocking", f"iteration must be a positive integer, got {iteration!r}")
    verdict = by_key.get("verdict", [""])[0]
    if verdict and verdict not in VERDICTS:
        fail("R3", "blocking", f"verdict {verdict!r} not in {'|'.join(VERDICTS)}")
    spec = by_key.get("spec-compliance", [""])[0]
    if spec and spec not in SPEC_COMPLIANCE:
        fail("R3", "blocking",
             f"spec-compliance {spec!r} not in {'|'.join(SPEC_COMPLIANCE)}")

    findings: list[tuple[str, str]] = []  # (glyph, id)
    for raw in by_key.get("finding", []):
        m = _FINDING_RE.match(raw)
        if not m:
            fail("R4", "blocking",
                 f"finding does not parse ('<glyph> <id> <location> — <title>'): {raw!r}")
        else:
            findings.append((m.group(1), m.group(2)))

    has_red = any(g == "🔴" for g, _ in findings)
    if verdict in VERDICTS:
        if has_red and verdict != "changes-required":
            fail("R5", "blocking",
                 "a 🔴 finding under an approving verdict — a stated rationale "
                 "never downgrades a finding's severity")
        if verdict == "changes-required" and not has_red:
            fail("R5", "blocking", "changes-required with no 🔴 finding")

    body = re.sub(r"<!--\s*FRIDAY-REVIEW:BEGIN\s*-->.*?<!--\s*FRIDAY-REVIEW:END\s*-->",
                  "", text, flags=re.S)
    headings = [ln for ln in body.splitlines() if ln.lstrip().startswith("#")]
    for glyph, fid in findings:
        anchors = [h for h in headings if f"{glyph}-{fid}" in h]
        if len(anchors) != 1:
            fail("R6", "blocking",
                 f"finding {glyph}-{fid}: expected exactly one body heading "
                 f"carrying '{glyph}-{fid}', found {len(anchors)}")
    for h in headings:
        for glyph in GLYPHS:
            for m in re.finditer(re.escape(glyph) + r"-(\d+)", h):
                if (glyph, m.group(1)) not in findings:
                    fail("R6", "blocking",
                         f"body heading carries {glyph}-{m.group(1)} with no "
                         "matching envelope finding")


def _check_release_gate(text: str, fail) -> None:
    begins = text.count("FRIDAY-RELEASE-GATE:BEGIN")
    ends = text.count("FRIDAY-RELEASE-GATE:END")
    if begins != 1 or ends != 1:
        fail("G1", "blocking",
             f"FRIDAY-RELEASE-GATE: expected exactly one BEGIN/END pair, "
             f"got {begins}/{ends}", owner="tester")
        return

    lines = taglines.block_lines(text, "FRIDAY-RELEASE-GATE") or []
    by_key: dict[str, list[str]] = {}
    for ln in lines:
        parsed = taglines.parse_typed_line(ln)
        if not parsed or parsed[0] not in GATE_KNOWN_KEYS:
            fail("G2", "blocking",
                 f"unknown/unparseable release-gate line: {ln!r}", owner="tester")
        else:
            by_key.setdefault(parsed[0], []).append(parsed[1])

    # Empty block lands here with by_key == {}: every required key is absent, so
    # each fires a G3 (the defined empty case — an empty gate is INVALID).
    for key in GATE_REQUIRED:
        vals = by_key.get(key, [])
        if len(vals) != 1:
            fail("G3", "blocking",
                 f"{key}: must appear exactly once (got {len(vals)})", owner="tester")
        elif vals[0] not in GATE_VALUES[key]:
            fail("G3", "blocking",
                 f"{key} {vals[0]!r} not in {'|'.join(GATE_VALUES[key])}",
                 owner="tester")


def _check_dispositions(text: str, fail) -> None:
    begins = text.count("FRIDAY-DISPOSITIONS:BEGIN")
    ends = text.count("FRIDAY-DISPOSITIONS:END")
    if begins != 1 or ends != 1:
        fail("D1", "blocking",
             f"FRIDAY-DISPOSITIONS: expected exactly one BEGIN/END pair, "
             f"got {begins}/{ends}", owner="tester")
        return

    # An empty block yields no lines and no failures — the defined empty case is
    # VALID (nothing to cover; taglines empty-case rule + verify_coverage.py).
    lines = taglines.block_lines(text, "FRIDAY-DISPOSITIONS") or []
    for ln in lines:
        parsed = taglines.parse_typed_line(ln)
        if not parsed or parsed[0] != "disposition":
            fail("D2", "blocking",
                 f"non-disposition line inside the block: {ln!r}", owner="tester")
        elif not _DISPO_RE.match(parsed[1]):
            fail("D2", "blocking",
                 f"disposition does not parse (need '<ID> implemented|deferred "
                 f"— <note>'): {parsed[1]!r}", owner="tester")


def _result(failures: list[dict]) -> dict:
    blocking = [f for f in failures if f["severity"] == "blocking"]
    return {"ok": not blocking, "failures": failures,
            "summary": ("verdict artifact consistent" if not blocking else
                        f"{len(blocking)} blocking envelope failure(s)")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True)
    ap.add_argument("--strict-missing", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isfile(args.file):
        print(f"verify_review_format: no such file: {args.file}", file=sys.stderr)
        return 2
    res = verify_file(args.file, strict_missing=args.strict_missing)
    print(json.dumps(res) if args.json else res["summary"])
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
