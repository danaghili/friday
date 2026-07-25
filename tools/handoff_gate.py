#!/usr/bin/env python3
"""Handoff completion-gate checker — the four operator-attested bars (FR-85).

handoff refuses to report done until all four gates are confirmed:
  reconcile  the record's deterministic drift check is clean (or /friday:reconcile
             was offered and run — D-0058);
  keys       every account/key confirmed transferred into the client's name,
             builder access + recovery removed (attested only — friday never
             handles the values, D-0057);
  restore    at least one successful test restore evidenced;
  receiver   a named client-side receiver acknowledged the package.

Attestations are journalled through the single substrate writer as
`handoff-attest` events (data: gate, status[, note]) — the ONE representation;
this module reads the journal and reports complete / outstanding, taking the
LATEST status per gate. Corrupt journal lines (non-JSON, or valid JSON that is
not an object) are skipped, never a crash. A missing or empty journal means all
four are outstanding — the tested empty case (lesson #6). This checker never
sees a secret: it reads gate *status*, not the values behind a transfer.

Exit codes: 0 complete · 1 outstanding gates · 2 bad invocation. Pure stdlib.
"""
# Contract: docs/contracts/handoff-package.md — this gate reader is a named consumer;
# cited on both sides of the handoff (A14).
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402

GATES = ("reconcile", "keys", "restore", "receiver")
STATUSES = ("confirmed", "pending", "blocked")

_REASONS = {
    "reconcile": "record drift check not confirmed clean — run /friday:reconcile",
    "keys": "not every key confirmed transferred into the client's name (builder access/recovery removed)",
    "restore": "no successful test restore evidenced",
    "receiver": "no named client-side receiver has acknowledged the package",
}


def gates_from_events(events) -> dict:
    """Latest recorded status per gate across a sequence of journal events
    (later events override earlier). A `confirmed` counts only when it came
    through the human channel (envelope `by=pm`) AND — for restore — carries
    evidence (a non-empty note); otherwise it is downgraded to `unverified`
    (A1: the gate must never trust a bare self-set flag). Non-`handoff-attest`
    events, unknown gates, and corrupt (non-dict) entries are ignored."""
    status: dict[str, str] = {}
    for ev in events:
        if not isinstance(ev, dict) or ev.get("event") != "handoff-attest":
            continue
        data = ev.get("data")
        if not isinstance(data, dict):
            continue
        gate = data.get("gate")
        st = data.get("status")
        if gate not in GATES or not st:
            continue
        if st == "confirmed":
            if ev.get("by") != "pm":
                st = "unverified"                                   # not the human channel
            elif gate == "restore" and not str(data.get("note") or "").strip():
                st = "unverified"                                   # restore requires evidence
        status[gate] = st
    return status


def read_gate_status(cwd: str = ".") -> dict:
    """Gate status read from the shared journal; {} when no journal exists."""
    path = os.path.join(fs.friday_dir(cwd), "journal.jsonl")
    events = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return {}
    return gates_from_events(events)


def evaluate(gate_status: dict) -> dict:
    """{complete, confirmed, outstanding} — complete iff all four gates confirmed."""
    confirmed = [g for g in GATES if gate_status.get(g) == "confirmed"]
    outstanding = [g for g in GATES if gate_status.get(g) != "confirmed"]
    return {"complete": not outstanding, "confirmed": confirmed, "outstanding": outstanding}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check the four handoff completion gates")
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"handoff_gate: --root is not a directory: {root}", file=sys.stderr)
        return 2

    status = read_gate_status(root)
    result = evaluate(status)
    if args.json:
        print(json.dumps({**result, "status": status}, indent=2))
    elif result["complete"]:
        print("handoff gates: ALL FOUR CONFIRMED — handover may complete.")
    else:
        print("handoff gates: OUTSTANDING — handover cannot complete until:")
        for g in result["outstanding"]:
            print(f"  - {g}: {_REASONS[g]}")
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
