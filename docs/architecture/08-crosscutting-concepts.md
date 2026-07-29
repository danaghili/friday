# Crosscutting concepts

The invariants that bind every module (each is code, not aspiration):

- **Single-*path* substrate** — every `.friday/` path resolves through
  `tools/friday_substrate.py`, the one owner of the worktree-shared root; root
  resolution is `git rev-parse --git-common-dir` everywhere (never cwd), and
  nothing hand-builds a `.friday/` path. A module owning a whole record type
  writes that record itself and reaches the substrate only for the shared
  primitives — root, journal, locks, time (`decisions.py`,
  `standards_deviations.py`, `friday_consent.py`, `state_record.py`). Journal
  lines: one O_APPEND write, ≤4096 bytes, envelope `{ts, feature, phase, event,
  by[, data]}`. *(Was stated as "every write goes through one module", which
  D-0135 records as already untrue when written — the invariant is the path, not
  the write.)*
- **Typed tag lines** (`tools/taglines.py`) — every script-checked claim is a
  grep-able line inside a named marker block; every grammar defines + tests
  its empty case (`_No decisions captured yet._`, `"generated-empty": true`,
  zero-findings envelopes, tagless docs → `[]`).
- **detector→sentinel→stop-gate** — state and review-format invariants each
  get the triple; sentinels live in the shared `.friday/`; gates re-verify and
  self-clear; a foreign SubagentStop event never arms and never clears
  (ISSUE-007 in-hook identity check, `friday_substrate.event_matches_agent`).
- **Fail-open hooks, fail-closed backstops** — hooks always exit 0 and
  degrade to no-telemetry (a false block is worse than a miss); the durable
  guarantees are out-of-band: `tools/receipt.py` tree-hash receipts and the
  Codex gate that blocks on a missing verifier.
- **Contracts over convention** — every filesystem handoff has one canonical
  contract file under `docs/contracts/`, cited by name on both sides.
- **Trust boundaries** — the doc-index MCP server contains paths under the
  project root (or the plugin's own `docs/` for `plugin:` paths),
  realpath-checked; the experiments MCP server (INC-201) accepts only the
  closed request menu, re-checks egress per call, and spends a
  fingerprint-bound PM consent before any run; substrate CLIs refuse to run
  outside a friday project rather than lazy-create stray state; the ask
  mirror never alters the dialog it mirrors.
- **Provenance** — generated artifacts stamp their generator in line 1 and are
  regenerated, never edited; receipts bind verdicts to tree hashes; decision
  entries carry channel + weight + floor + optional back-filled provenance.
- **Secrets are names, never values** — no friday code path reads a secret
  value. `tools/secret_names.py` enumerates required env-var NAMES only (from
  `.env.example` / config / source refs, pure stdlib text parsing); values live
  in the operator's own secrets manager and transfer out-of-band; a file-scan
  for secret-shaped strings is the WRONG model (it presupposes a value already
  reached a friday-handled file). See ADR-003.
- **Compaction continuity** — every agent crosses its own compaction seams:
  PreCompact steers the summarizer (`hooks/compaction_steering.py`, spec
  mandates a `handoff-of:` self-ID line — the payload carries no agent
  identity), PostCompact files the summary through the substrate
  (append-only generations; `current.md` only on a parsed header, envelope-
  stripped per D-0077), SessionStart(compact) re-orients the main session by
  push while subagents pull their drawer. Contract:
  `docs/contracts/compaction-package.md`; distinct from the seam handoff.

**Last-verified:** 2026-07-29 (task #42 re-synthesis, D-0151 tree) · **Record-status:** verified
