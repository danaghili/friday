---
name: harden
description: post-build independent hardening — the one review ceremony after the build completes
friday-lane: true
disable-model-invocation: true
---

You are the lead running `/friday:harden` — post-build independent hardening: the one review ceremony, run after the build completes (never per-task), and again post-incremental (`/friday:feature`) for blast-radius topics. The build's own interim checks (DF-021) **borrow** this roster's tester + reviewer — dispatched by the build lead over a sealed unit's diff, writing interim artifacts (`docs/reviews/interim-<unit>-*.md`), never a full run of this playbook.

Doctrine (verbatim, governs every step): **untrusted self-report + mechanical, independently-reproducible re-verification, with asymmetric tolerance — a false block is worse than a miss.**

Dispatch discipline for every spawn below: name `model:` explicitly (omission inherits the session's most expensive model); one unit of work per dispatch, never the session's history; briefs/reports/diffs as files, never pasted; project `CLAUDE.md` reaches ZERO subagents — everything a checker must know goes in its spawn message or Read list. Telemetry through the single primitive at spawn/accept/done: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent <name> --phase harden:<step>`.

### Step 0 — Explore pass (pointed invocation only)

By default the build hands over and Step 1 begins straight away. A **direct, pointed** invocation ("harden the payment sync") opens instead with an explore pass to gather context on that area first — reach it through the code graph, not by rummaging: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/graph_query.py" "<area>" --root .` prefers graphify when installed and falls back to friday's own IR when not. **Grep is the fallback, not the plan.** Cite `EXTRACTED` edges as evidence; `INFERRED` edges are leads.

### Step 1 — Layer-1 mechanical claim-audit (you, no spawn)

Re-derive every completion claim: `git status --porcelain` scoped to the reported paths (**never `git diff --stat`** — it misses untracked new files); re-run the stated test/build commands and quote their literal output. Prose self-report is proven insufficient.

If the build regenerated architecture docs, confirm the generated set still carries provenance (skipped-is-OK, never fabricated), real output quoted: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_generated.py" --cmd reference --files docs/architecture/generated/architecture-ir.json docs/architecture/generated/dependency-graph.md docs/architecture/generated/api-surface.md --json`. Absent files are expected (the PM skipped `/friday:reference` — hence `--files`, not `--require`); a *present* file that is empty or stamp-less is a finding (`"ok": false`), a hand-edit or a mis-stamped extractor slipping past the diff oracle.

### Step 2 — Review package

Assemble `.friday/review-package.diff`: the consolidated diff of the whole build/branch — additions AND removals — plus the file list. The reviewer reads THIS, not your summary.

### Step 3 — Independent passes (spawned; fresh context)

- **Tester** (`friday-tester`, model: sonnet) — release-gate scope: full suite + production build + migration verification + regression discipline + `S-n` security-criteria coverage. Writes `docs/reviews/release-gate.md` (FRIDAY-RELEASE-GATE block: `suite:` / `build:` / `migration:`) and the coverage ledger `docs/reviews/coverage.md` (FRIDAY-DISPOSITIONS: one `disposition: <ID> implemented|deferred — <note>` line per TSOW FR/NFR/AC/S ID). Gets the stack-risk register + context7 as shared facts, independent verdicts — it re-verifies load-bearing assertions itself.
- **Layer-2 fresh-context skeptics** (2 × `general-purpose`, model: **sonnet** — pinned) — refute-oriented prompts over the review package + record only: "find the claim that is false". They replace the lead's self-audit, never supplement it.
- **Reviewer** (`friday-reviewer`, model: sonnet) — whole-build review against the TSOW oracle. Its artifact carries the machine-checkable envelope (FRIDAY-REVIEW: reviewer/iteration/verdict/**spec-compliance**/finding lines). Rules: you never pre-rate a finding's severity or tell it what not to flag; a stated rationale never downgrades a finding. **`model-autonomous` DECISIONS.md entries are scrutinized FIRST** — those are the un-ratified judgments.
- **Security** (`/friday:security`) + **Redteam** (`/friday:redteam`) — the find pass **invokes both**: each spawns its sandboxed reviewer over the sanitized mirror (`tools/sanitized_mirror.py`), and harden consumes their findings through the findings-brief grammar (`docs/contracts/findings-brief.md`) — **persisting each consumed brief to `docs/reviews/findings-*.md` (or `docs/hardening/`) and running `findings_brief_check.py` on it BEFORE dispositioning, so the structural gate binds whether the brief arrived as a file or a teammate message (the delivery channel never decides whether it's validated)**. Harden owns what the read-only reviewers cannot: it **pre-runs the deterministic scans** as a plain pipeline step, and runs an **experiment-runner lane** (its own scoped grant against a scratch instance — never the reviewers, never the source tree) so a designed experiment actually executes. For a genuinely huge system, scale each reviewer's lanes through the **finding engine** — narrow fresh-context finders, every candidate refute-verified by independent skeptics, survivors handed to the reviewer as feedstock (recommend-and-ask, never silent-auto-run; the reviewer stays the synthesis mind and owns the report): `docs/research/rebuild/adversarial-finding-engine.md`.

### Step 3b — Fix discipline (governs every change made because of a finding)

The build's scoped Iron Law does not expire at hardening. **A reproduced defect gets a FAILING repro test first**, then the fix to green — a test written after the fix proves nothing about the defect (it asserts the code you just wrote, not the failure you found). Logic-core changes remain under delete-and-restart if written implementation-first. A TSOW-named item the build silently dropped is completed here under the same rule. **Net-new scope never enters during hardening** — anything the TSOW doesn't name routes to `/friday:feature` after close, with a `DECISIONS.md` entry marking the deferral.

**Artifact placement (the docs/reviews/ contract):** `docs/reviews/` holds **typed, enveloped verdict artifacts only** — FRIDAY-REVIEW reviews, the FRIDAY-RELEASE-GATE release gate, the FRIDAY-DISPOSITIONS coverage ledger (the format sentinel verifies each against its own grammar). Working notes, fix-round ledgers, and prose summaries live in `docs/hardening/` and are cited by path — never force a verdict envelope onto a document that carries no verdict.

### Step 4 — Receipts + verdict

`python3 "${CLAUDE_PLUGIN_ROOT}/tools/receipt.py" write --root . --verifier state` (and `claims`). Surface all findings to the PM with your recommendation; the reviewer's verdict + the release gate feed the closer's K-gated close. Capture any decision revised by a finding into `DECISIONS.md` (verification findings fire capture too).
