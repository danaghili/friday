# Solution strategy

## The shape

Heavy front (TSOW authored under the interrogation protocol, approved once) ·
light middle (one-shot free-run + as-you-go two-channel decision capture) ·
one independent post-build hardening pass · synthesized back (deterministic
extractor + DECISIONS-grounded prose, diff as oracle). Rationale: every
handoff seam is where integration failures live; the shared primitives were
therefore built first, in one head `[DECISIONS.md D-0001]`.

## Key mechanism choices and why

- **One substrate library, imported by hooks** — the ISSUE-006 single-writer
  invariant beat the old per-hook-duplication rule `[D-0003]`; it is also
  what made the Appendix-B worktree fix a one-place change.
- **`.friday/` keyed to the git common dir** — worktrees isolate code, share
  substrate; the D-NNNN counter and journal never fragment `[Appendix B;
  verified live in the loop-gate drill]`.
- **Decision log as markdown with typed meta lines** — PM-readable AND
  machine-parsed; JSON rejected for readability, YAML for append cost
  `[D-0004]`.
- **Harness-guaranteed Channel A** — a PostToolUse hook fires the write for
  exactly the `[FRIDAY-DECISION]` ask shape; the model picks the shape, the
  harness guarantees the write; ordinary dialogs never pollute the log.
- **Exact-after-normalization retrieval, never RAG** — semantic search was 3%
  of measured demand; live-parse means results can never be stale. One
  deliberate deviation from the v0.4.0 parser: markup chars strip everywhere
  `[D-0006]`.
- **K-model state (A.3, resolves OQ-1)** — project-level, precision-first,
  enforced by detector→sentinel→stop-gate + receipts + a fail-closed Codex
  gate.
- **Replace-in-place versioning** — humility before the DoD gate; rename
  costs are lockstep-wide; the current number lives in
  `.claude-plugin/plugin.json`, never restated here `[D-0002]`.

Rationale not captured: none known at this writing — every mechanism above
cites its decision entry or the TSOW section that mandated it.
