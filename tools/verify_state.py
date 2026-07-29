#!/usr/bin/env python3
"""K-rule verifier — the mid-build state model's single mechanical checker
(A.3, resolves OQ-1; replaces v0.4.0's per-feature C1–C9 checkpoint verifier).

State model (project-level, source of truth = CLAUDE.md's FRIDAY-STATE block):
  tsow-approved → substrate-seeded → build-in-progress →
  post-build-review-recorded → closed

Precision-first, same posture as the retired C-rules and the doctrine's
asymmetric tolerance ("a false block is worse than a miss"): an in-flight
trail violates nothing blocking; only a record that DECLARES a state its
artifacts do not back is a finding. Each rule names its fixing owner.

  K0 blocking lead    (init/TSOW-substrate gate — the 2 surviving Strategist
                      checks) docs/TECHNICAL_SOW.md exists; past tsow-approved,
                      CLAUDE.md carries a well-formed FRIDAY-CLAIMS block.
  K1 blocking closer  closed ⇒ K0's conditions re-verified at close.
  K2 blocking closer  closed ⇒ a docs/reviews/ artifact carries a FRIDAY-REVIEW
                      envelope with verdict approved|approved-with-minors AND a
                      spec-compliance: line (the §6.8 graft).
  K3 blocking closer  closed ⇒ docs/reviews/release-gate.md records the
                      Tester's release-gate pass (suite/build/migration).
  K4 blocking project state classifies to the closed vocabulary — no invented
                      strings (verbatim from C6).
  K5 blocking closer  closed ⇒ PROP-028 dirty-bit fields (last-verified: +
                      record-status:) present on the closure record.
  K6 warn     lead    build-in-progress with zero DECISIONS.md entries
                      (capture-integrity).
  K7 blocking closer  closed ⇒ every TSOW FR/NFR/AC/S ID has a closing
                      disposition (verify_coverage).
  K8 blocking closer  closed ⇒ verify_claims drift check passes (sole home).

Enforced by hooks/state_sentinel.py (detector) + hooks/state_stop_gate.py
(stop gate) — the detector→sentinel→stop-gate shape. Runs leave a receipt
(tools/receipt.py) — best-effort, never a gate of its own.

Exit codes: 0 ok · 1 blocking failures · 2 bad invocation. Pure stdlib.
"""
# Contract: docs/contracts/state-record.md — this K-rule verifier is the enforcing
# consumer; cited on both sides of the handoff (A14).
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decisions  # noqa: E402
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402
import verify_claims  # noqa: E402
import verify_coverage  # noqa: E402

STATES = ("tsow-approved", "substrate-seeded", "build-in-progress",
          "post-build-review-recorded", "closed")
REVIEW_VERDICTS_OK = ("approved", "approved-with-minors")
REVIEWS_DIR = os.path.join("docs", "reviews")


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


# A4 (harden): the close-review verdict is honored ONLY from a canonical review
# artifact carrying a reviewer: provenance line — not a free-standing marker in any
# docs/reviews/*.md (the forgery the redteam demonstrated). The honest residual (a
# single-operator local model can still hand-author the canonical file) is covered
# by reconcile, which RE-DERIVES this verdict rather than trusting the marker.
CANONICAL_REVIEW = ("post-build-review.md", "whole-build-review.md")


def _review_ok(root: str) -> tuple[bool, str]:
    rdir = os.path.join(root, REVIEWS_DIR)
    for name in CANONICAL_REVIEW:
        text = _read(os.path.join(rdir, name))
        if text is None:
            continue
        env = taglines.block_typed(text, "FRIDAY-REVIEW")
        if not env:
            continue
        verdicts = env.get("verdict", [])
        if verdicts and verdicts[0] in REVIEW_VERDICTS_OK:
            if not env.get("spec-compliance"):
                return False, (f"{name}: approving verdict but no spec-compliance: "
                               "line (§6.8 graft — both lines are required)")
            if not (env.get("reviewer") and env["reviewer"][0].strip()):
                return False, (f"{name}: approving verdict but no reviewer: provenance "
                               "line — a close-review envelope must name the run that "
                               "produced it, not a free-standing marker (A4)")
            return True, name
    return False, ("no canonical review artifact (post-build-review.md / "
                   "whole-build-review.md) carries a FRIDAY-REVIEW envelope with an "
                   "approving verdict + reviewer provenance")


def _release_gate_ok(root: str) -> tuple[bool, str]:
    text = _read(os.path.join(root, REVIEWS_DIR, "release-gate.md"))
    if text is None:
        return False, f"missing {REVIEWS_DIR}/release-gate.md"
    gate = taglines.block_typed(text, "FRIDAY-RELEASE-GATE")
    if gate is None:
        return False, "release-gate.md lacks the FRIDAY-RELEASE-GATE block"
    problems = []
    if gate.get("suite", [""])[0] != "pass":
        problems.append(f"suite: {gate.get('suite', ['<missing>'])[0]}")
    if gate.get("build", [""])[0] not in ("pass", "n/a"):
        problems.append(f"build: {gate.get('build', ['<missing>'])[0]}")
    if gate.get("migration", [""])[0] not in ("pass", "n/a"):
        problems.append(f"migration: {gate.get('migration', ['<missing>'])[0]}")
    return (not problems), (", ".join(problems) or "release gate recorded")


def verify_state(root: str) -> dict:
    root = fs.resolve_worktree_root(os.path.abspath(root))
    failures: list[dict] = []

    def fail(check: str, severity: str, owner: str, detail: str) -> None:
        failures.append({"check": check, "severity": severity, "owner": owner,
                         "detail": detail})

    claude_text = _read(os.path.join(root, "CLAUDE.md"))
    state_block = taglines.block_typed(claude_text or "", "FRIDAY-STATE")
    if claude_text is None or state_block is None:
        return {"ok": True, "skipped": True, "state": None, "failures": [],
                "summary": "no FRIDAY-STATE block — state model not engaged "
                           "(precision-first: never a false block)"}

    state = state_block.get("state", ["<missing>"])[0]
    result: dict = {"state": state}

    # K4 — closed vocabulary.
    if state not in STATES:
        fail("K4", "blocking", "project",
             f"state {state!r} is not in the closed vocabulary "
             f"{'|'.join(STATES)} — never invent a status string")
        summary = f"state record INVALID: {failures[0]['detail']}"
        return {**result, "ok": False, "failures": failures, "summary": summary}

    # K0 / K1 — the init/TSOW-substrate gate (re-verified at close as K1).
    check_id = "K1" if state == "closed" else "K0"
    if not os.path.isfile(os.path.join(root, "docs", "TECHNICAL_SOW.md")):
        fail(check_id, "blocking", "closer" if state == "closed" else "lead",
             "docs/TECHNICAL_SOW.md missing — the TSOW is the external oracle "
             "(PROP-060c) and must exist at every state")
    if state != "tsow-approved":
        wf, errs = verify_claims.well_formed(claude_text)
        if not wf:
            fail(check_id, "blocking", "closer" if state == "closed" else "lead",
                 "FRIDAY-CLAIMS not well-formed: " + "; ".join(errs))

    # K6 — capture-integrity warn.
    if state == "build-in-progress":
        parsed = decisions.parse_file(os.path.join(root, decisions.DEFAULT_PATH))
        if not parsed["entries"]:
            fail("K6", "warn", "lead",
                 "build-in-progress with zero DECISIONS.md entries — as-you-go "
                 "capture is not happening (or the log is missing/malformed)")

    if state == "closed":
        _closed_checks(root, state_block, fail)

    blocking = [f for f in failures if f["severity"] == "blocking"]
    ok = not blocking
    summary = (f"state={state}: record consistent"
               + (f" ({len(failures)} warning(s))" if failures else "")
               if ok else
               f"state={state}: {len(blocking)} blocking failure(s) — "
               + "; ".join(f"{f['check']}({f['owner']}): {f['detail']}"
                           for f in blocking))
    out = {**result, "ok": ok, "failures": failures, "summary": summary}

    try:  # receipts backstop — best-effort, never a gate of its own
        import receipt
        receipt.leave_receipt(root, "state", ok, len(blocking))
    except Exception:
        pass
    return out


def _closed_checks(root: str, state_block: dict, fail) -> None:
    """K2/K3/K5/K7/K8 — the closure gates, checked only at state=closed.
    (Kept BELOW verify_state so its recorded breach location keeps its line.)"""
    ok2, d2 = _review_ok(root)
    if not ok2:
        fail("K2", "blocking", "closer", d2)
    ok3, d3 = _release_gate_ok(root)
    if not ok3:
        fail("K3", "blocking", "closer", d3)
    if not (state_block.get("last-verified") and
            state_block.get("record-status", [""])[0] in ("verified", "stale")):
        fail("K5", "blocking", "closer",
             "closure record lacks the PROP-028 dirty-bit fields "
             "(last-verified: + record-status: verified|stale) in FRIDAY-STATE")
    cov = verify_coverage.check(root)
    if not cov["ok"]:
        fail("K7", "blocking", "closer", cov["summary"])
    claims = verify_claims.check_all(root)
    if not claims["ok"]:
        fail("K8", "blocking", "closer", claims["summary"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print(f"verify_state: no such dir: {args.root}", file=sys.stderr)
        return 2
    res = verify_state(args.root)
    print(json.dumps(res) if args.json else res["summary"])
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
