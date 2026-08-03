# Crosscutting concepts

The invariants that bind every module (each is code, not aspiration):

- **Single-*path* substrate** — the rule is single-homed in the project `CLAUDE.md` § Conventions (D-0135, INC-203 D3); what the code shows: root resolution is `git rev-parse --git-common-dir` everywhere (never cwd), and the record-owning modules (the enumeration lives with the rule in that same conventions entry — a copy here disagreed with its cited home within days, caught by the 2026-08-03 probe run) write their own record and reach `tools/friday_substrate.py` only for the shared primitives — root, journal, locks, time. Journal lines: one O_APPEND write, ≤4096 bytes, envelope `{ts, feature, phase, event, by[, data]}`. *(An earlier synthesis said "every write goes through one module" — D-0135 records that as already untrue when written; the invariant is the path, not the write.)*
- **Typed tag lines** (`tools/taglines.py`) — the rule is single-homed in the project `CLAUDE.md` § Conventions; in the code, every checked grammar lives in a named marker block and its empty case is a defined, tested value (`_No decisions captured yet._`, `"generated-empty": true`, zero-findings envelopes, tagless docs → `[]`).
- **detector→sentinel→stop-gate** — state and review-format invariants each
  get the triple; sentinels live in the shared `.friday/`; gates re-verify and
  self-clear; a foreign SubagentStop event never arms and never clears
  (ISSUE-007 in-hook identity check, `friday_substrate.event_matches_agent`).
- **Fail-open hooks, fail-closed backstops** — the fail-open rule is single-homed in `docs/standards/coding-standards.md`; in the code, hooks always exit 0 and degrade to no-telemetry, while the durable guarantees are out-of-band: `tools/receipt.py` tree-hash receipts and the Codex gate that blocks on a missing verifier.
- **Contracts over convention** — the citation rule is single-homed in the project `CLAUDE.md` § Conventions; the contract set lives under `docs/contracts/`, and `tools/dispatch_liveness_check.py` proves every cited contract path resolves.
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
- **Secrets are names, never values** — the rule is single-homed in `docs/standards/coding-standards.md` (ADR-003 records the decision). In the code: `tools/secret_names.py` enumerates required env-var NAMES only (from `.env.example` / config / source refs, pure stdlib text parsing); values live in the operator's own secrets manager and transfer out-of-band; a file-scan for secret-shaped strings is the WRONG model (it presupposes a value already reached a friday-handled file).
- **Compaction continuity** — every agent crosses its own compaction seams:
  PreCompact steers the summarizer (`hooks/compaction_steering.py`, spec
  mandates a `handoff-of:` self-ID line — the payload carries no agent
  identity), PostCompact files the summary through the substrate
  (append-only generations; `current.md` only on a parsed header, envelope-
  stripped per D-0077), SessionStart(compact) re-orients the main session by
  push while subagents pull their drawer. Contract:
  `docs/contracts/compaction-package.md`; distinct from the seam handoff.

**Last-verified:** 2026-07-29 (task #42 re-synthesis, D-0151 tree) · **Record-status:** verified
