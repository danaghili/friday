#!/usr/bin/env python3
"""Record one handoff completion-gate attestation through the single substrate
writer (FR-85). The operator confirms a gate; friday journals the confirmation —
never the secret value behind it (D-0057). Pairs with `handoff_gate.py`'s reader.

Usage (from the handoff playbook, as the PM confirms each gate):
  python3 "${CLAUDE_PLUGIN_ROOT}/tools/handoff_attest.py" --gate keys \
      --status confirmed --by pm [--note "..."] [--phase handoff:gates] [--cwd .]

Gates: reconcile · keys · restore · receiver. Refuses to run outside a friday
project. Exit codes: 0 appended (line echoed) · 2 bad invocation. Pure stdlib.
"""
# Contract: docs/contracts/handoff-package.md — this attest writer is the
# producer side of the completion-gate seam; cited on both sides (A14).
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import handoff_gate as hg  # noqa: E402

# A5 (harden): the free-text --note is a value SINK next to the keys transfer —
# refuse anything shaped like a secret VALUE so friday never records or echoes one
# (FR-84 / D-0056: names and purposes, never values). Benign context is fine.
_SECRET_SHAPE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]{1,}\s*=\s*\S{6,}"                                  # KEY=value
    r"|\b(?:sk|pk|rk|ghp|gho|ghu|ghs|xox[baprs]|AKIA|ASIA)[-_A-Za-z0-9]{8,}"   # known token prefixes
    r"|\b[A-Za-z0-9+/]{24,}={0,2}\b")                                          # long base64-ish blob


def _looks_like_secret(note: str) -> bool:
    return bool(_SECRET_SHAPE.search(note))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Append one handoff gate attestation")
    ap.add_argument("--gate", required=True, help=f"one of {'|'.join(hg.GATES)}")
    ap.add_argument("--status", default="confirmed", help=f"one of {'|'.join(hg.STATUSES)}")
    ap.add_argument("--by", default="pm", choices=fs.BY_VOCABULARY)
    ap.add_argument("--note", default=None)
    ap.add_argument("--phase", default="handoff:gates")
    ap.add_argument("--cwd", default=".")
    args = ap.parse_args(argv)

    if args.gate not in hg.GATES:
        print(f"handoff_attest: --gate must be one of {'|'.join(hg.GATES)}", file=sys.stderr)
        return 2
    if args.status not in hg.STATUSES:
        print(f"handoff_attest: --status must be one of {'|'.join(hg.STATUSES)}", file=sys.stderr)
        return 2
    cwd = os.path.abspath(args.cwd)
    if not os.path.isdir(cwd):
        print(f"handoff_attest: --cwd is not a directory: {cwd}", file=sys.stderr)
        return 2
    if not fs.should_engage(cwd):
        print(f"handoff_attest: {cwd} is not a friday project — refusing to create a "
              "stray journal", file=sys.stderr)
        return 2

    if args.gate == "restore" and args.status == "confirmed" and not (args.note or "").strip():
        print("handoff_attest: the restore gate requires --note pointing at the evidence "
              "of a completed test restore (FR-85 / A1) — a bare status is not a tested "
              "restore.", file=sys.stderr)
        return 2
    if args.note and _looks_like_secret(args.note):
        print("handoff_attest: --note looks like it carries a secret VALUE "
              "(a KEY=value, a token, or a long credential blob). friday never "
              "records a value — describe the transfer without the secret, or omit "
              "--note (FR-84 / D-0056).", file=sys.stderr)
        return 2
    data = {"gate": args.gate, "status": args.status}
    if args.note:
        data["note"] = args.note
    try:
        line = fs.build_journal_line("handoff-attest", args.phase, by=args.by, data=data)
        fs.append_journal_line(cwd, line)
    except (ValueError, OSError) as exc:
        print(f"handoff_attest: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(line, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
