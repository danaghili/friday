#!/usr/bin/env python3
"""INC-001 FR-1.1 — compaction steering (PreCompact, exit-0 stdout becomes
the summarizer's custom instructions; probe-proven path,
docs/research/probe-compaction-hooks.md). Contract:
docs/contracts/compaction-package.md.

Attribution-blind by necessity (KH-5): the PreCompact payload carries no
agent identity, so the spec is agent-GENERIC — it instructs whoever is being
summarized to self-identify (the agent knows who it is even though the
payload doesn't) and to carry the floor sections. Agent-specific content
(the declared addendum) rides the conversation itself, where the summarizer
can see it.

Fail-open: any error prints nothing (no steering injected) and exits 0 — a
compaction is never broken or blocked by this hook. The static CLAUDE.md
backstop section (D-0074) covers the no-steering case in this repo.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_SPEC = """Structure the summary as a compaction handoff (contract: compaction-package):
Line 1 must be EXACTLY of the form `handoff-of: <agent-slug> — <scope in a few words>`
(lowercase slug of the role you are, e.g. `friday-lead` for the main session,
or your role name if you are a spawned agent; then an em-dash and your scope).
Keep the summary SMALL — carry only what lives nowhere but this conversation —
with these labeled sections:
1. `Current objective` — where the work has got to, 1-3 lines.
2. `Tried and ruled out` — EVERY approach already attempted and rejected, with
   why. This is the highest-value section; never drop or thin it.
3. `Outstanding work` — do NOT enumerate tasks; state that the live task list
   is the source of truth for what remains, and that it must be re-read.
4. `Recovery` — preserve verbatim: "After any compaction, re-read your
   compaction package under .friday/compaction/ before continuing."
If the conversation contains notes the agent explicitly marked for its future
self, carry them verbatim in an `Addendum` section. Never include secret
values of any kind. Decisions, project state, and git history are rebuilt
from friday's records automatically — do not spend the summary on them."""


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        if not fs.should_engage(cwd):
            return 0
        print(_SPEC)
    except Exception as exc:
        print(f"compaction_steering: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
