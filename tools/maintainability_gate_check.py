#!/usr/bin/env python3
"""INC-008 layer-3 gate CHECKER — disposition-completeness (FR-8.5 / AC-8.1/8.2).

The deterministic script the enforcement hook runs. It answers ONE question over
the real tree: **is every current measured breach dispositioned?** — and prints a
typed verdict (`valid-pass` / `valid-fail`, the FR-61 shape `hooks/_guard.py`
consumes). The hook decides block-vs-warn from the project's arm state; this
checker only produces the reproducible verdict.

A breach is dispositioned iff the agent-judge envelope carries a matching finding
marked `justified` (→ recorded in the deviations ledger). It is UN-dispositioned
if there is no envelope, the envelope is malformed, no finding matches it, or the
matching finding is `unjustified` — because an unjustified breach that is STILL
measured over its bar has not been fixed. A breach that was really fixed no longer
measures over the bar, so it drops out of the current set entirely (Pin #2 /
AC-8.2: the measurer is the fix-verifier — no trusted "fixed" flag).

**What counts as "matching" (D-0136).** Two things, and the split matters:

- **Identity is file + function + metric — not the line.** The line number is
  kept in every record because it is how a person finds the code, but keying on
  it made a settled judgement vanish whenever unrelated code above it grew. That
  fired live on 2026-07-29 and produced duplicate ledger entries. The one case
  identity cannot separate is two same-named functions in one file (the measurer
  records a bare name); there the gate demands the exact line rather than let one
  justification cover both — ambiguity resolves toward asking.
- **A justification covers the NUMBER that was judged.** Same identity, same or
  better number → it holds. Worse than when it was judged → it surfaces for
  re-judging, naming both numbers. The old key was blind to this: rewrite a
  function into something far worse without moving it, and the old "this is fine"
  kept covering it — silent erosion, which is precisely what this gate exists to
  stop. Improvement never re-opens a judgement, or the gate would punish the
  person who made things better.

This is a gate on the PROCESS, not on the judge's opinion: the finding-set may be
non-reproducible, but "is everything dispositioned?" is reproducible. Blocking on
that is what makes a gate built on agent judgment trustworthy. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maintainability_measure as mm  # noqa: E402
import maintainability_envelope_check as ec  # noqa: E402


def _rel_location(loc: str, root_abs: str) -> str:
    """Normalize a `path:line:name` location to root-relative form. The judge's
    envelope carries root-relative locations (portable artifact) while the
    measurer stamps whatever path form it walked (absolute when the hook runs
    it) — without one shared identity every disposition fails to match and the
    whole breach set counts un-dispositioned (surfaced live 2026-07-28).
    Non-path locations (`<tree>`) pass through untouched."""
    prefix = root_abs.rstrip(os.sep) + os.sep
    if loc.startswith(prefix):
        return loc[len(prefix):]
    if loc.startswith("./"):
        return loc[2:]
    return loc


def _identity(rel_loc: str, metric: str) -> tuple[str, str, str]:
    """What makes two breaches THE SAME breach: file, function, metric (D-0136).

    Deliberately position-free. The line number stays in the record because it is
    how a human finds the code, but it is not part of the identity: a function
    that merely moved down because something above it grew is the same breach,
    and a judgement that evaporates on unrelated edits can never reach zero.

    A location with no function part (`file-size`, `<tree>`) identifies on its
    path alone.
    """
    parts = rel_loc.rsplit(":", 2)
    if len(parts) == 3 and parts[1].isdigit():
        return (parts[0], parts[2], metric)
    return (rel_loc, "", metric)


def _judged_at(findings: list[dict], root_abs: str) -> tuple[dict, dict]:
    """The justified dispositions, keyed two ways: exactly (path:line:name, metric)
    and position-free. Values are the number the judge actually saw."""
    exact: dict[tuple[str, str], int | None] = {}
    loose: dict[tuple[str, str, str], list[int | None]] = {}
    for f in findings:
        if f.get("disposition") != "justified":
            continue
        rel = _rel_location(f["location"], root_abs)
        try:
            judged = int(f["measured"])
        except (TypeError, ValueError):
            judged = None       # unreadable number: match on identity, skip the drift check
        exact[(rel, f["metric"])] = judged
        loose.setdefault(_identity(rel, f["metric"]), []).append(judged)
    return exact, loose


def _disposition_for(breach: dict, rel: str, exact: dict, loose: dict,
                     ambiguous: set) -> tuple[bool, int | None]:
    """(is it dispositioned, the number it was judged at).

    Exact position first, so an envelope that names the precise line always wins.
    Otherwise the position-free identity — but ONLY when it is unambiguous on both
    sides. The measurer records a bare function name, so a method and a
    module-level function of the same name collide; when that happens the gate
    falls back to demanding the exact line rather than letting one justification
    silently cover two breaches. Ambiguity resolves toward asking, never toward
    assuming.
    """
    key = (rel, breach["metric"])
    if key in exact:
        return True, exact[key]
    ident = _identity(rel, breach["metric"])
    if ident not in ambiguous and len(loose.get(ident, [])) == 1:
        return True, loose[ident][0]
    return False, None


def _undispositioned(breaches: list[dict], exact: dict, loose: dict,
                     root_abs: str) -> list[str]:
    """Every current breach with no judgement covering it, said in one line each.

    Two ways to land here: nothing in the envelope matches it, or something does
    but the code has grown worse than the number that was judged. The second says
    both numbers, because "complexity 41" means nothing to a reader who does not
    know it was justified at 32.
    """
    seen: dict[tuple[str, str, str], int] = {}
    for b in breaches:
        ident = _identity(_rel_location(b["location"], root_abs), b["metric"])
        seen[ident] = seen.get(ident, 0) + 1
    # An identity shared by two CURRENT breaches cannot pick between them either,
    # so it is ambiguous from both directions.
    ambiguous = {ident for ident, n in seen.items() if n > 1}

    listed: list[str] = []
    for b in breaches:
        rel = _rel_location(b["location"], root_abs)
        matched, judged = _disposition_for(b, rel, exact, loose, ambiguous)
        drifted = matched and judged is not None and b["measured"] > judged
        if matched and not drifted:
            continue
        line = f"{b['metric']} {b['measured']}>{b['bar']} @ {rel}"
        if drifted:
            line += (f" — judged justified at {judged}, now {b['measured']}: "
                     f"worse than what was judged, so it needs re-judging")
        listed.append(line)
    return listed


def check(*, root: str, standards: str | None, envelope: str | None,
          files: list[str] | None = None, min_tokens: int = 25) -> dict:
    """Return the typed verdict {verdict, summary, undispositioned, breach_count}.

    Fail-CLOSED here is deliberate for the LOGIC (an un-dispositioned breach is a
    valid-fail); fail-OPEN lives one layer up, in the hook — a broken checker
    yields no-verdict and the hook allows (a false block is worse than a miss)."""
    bars = {}
    if standards:
        try:
            with open(standards, encoding="utf-8") as fh:
                bars = mm.load_bars(fh.read())
        except OSError:
            bars = {}
    # No declared bars -> the non-adopter invariant: nothing to enforce.
    if not bars:
        return {"verdict": "valid-pass", "undispositioned": [], "breach_count": 0,
                "summary": "no maintainability bars declared — nothing to enforce"}

    file_list = files if files is not None else mm._walk_py(os.path.abspath(root))
    measured = mm.measure_paths(file_list, min_tokens=min_tokens)
    breaches = mm.breaches(measured, bars)
    if not breaches:
        return {"verdict": "valid-pass", "undispositioned": [], "breach_count": 0,
                "summary": "code is within every declared bar"}

    # There ARE breaches — they must all be dispositioned by the judge envelope.
    exact: dict[tuple[str, str], int | None] = {}
    loose: dict[tuple[str, str, str], list[int | None]] = {}
    if envelope:
        try:
            with open(envelope, encoding="utf-8") as fh:
                env_res = ec.check_text(fh.read())
        except OSError:
            env_res = {"verdict": "valid-fail", "findings": []}
        if env_res.get("verdict") != "valid-pass":
            return {"verdict": "valid-fail", "breach_count": len(breaches),
                    "undispositioned": [f"{b['metric']} @ {b['location']}" for b in breaches],
                    "summary": (f"{len(breaches)} breach(es) but the judge envelope is "
                                "missing or malformed — nothing is dispositioned")}
        root_abs = os.path.abspath(root)
        exact, loose = _judged_at(env_res["findings"], root_abs)

    root_abs = os.path.abspath(root)
    listed = _undispositioned(breaches, exact, loose, root_abs)
    if listed:
        return {"verdict": "valid-fail", "breach_count": len(breaches),
                "undispositioned": listed,
                "summary": (f"{len(listed)} un-dispositioned breach(es): each must be "
                            "justified-and-recorded or fixed-and-re-measured-clean — "
                            + listed[0])}
    return {"verdict": "valid-pass", "undispositioned": [], "breach_count": len(breaches),
            "summary": f"all {len(breaches)} breach(es) dispositioned (justified & recorded)"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Maintainability disposition-completeness gate "
                                             "(INC-008 FR-8.5)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--standards", help="coding-standards file holding the declared bars")
    ap.add_argument("--envelope", help="the agent judge's envelope file (dispositions)")
    ap.add_argument("--min-tokens", type=int, default=25)
    args = ap.parse_args(argv)
    res = check(root=args.root, standards=args.standards, envelope=args.envelope,
                min_tokens=args.min_tokens)
    print(json.dumps(res))
    return 0 if res["verdict"] == "valid-pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
