# friday-vnext — Technical Scope of Work (TSOW)

provenance: born-from-discovery

**Status:** Approved — structure signed off by the PM (2026-07-12). · **Author:** friday Brainstormer (discovery phase). · **Target:** friday-vnext — the next `friday` version, replace-in-place, bumped from `0.4.0`.

> **This TSOW is external to the build and is never rewritten by it** — it stays the oracle for the post-build review/reconcile (preserve-list §6 / PROP-060c). Any drift the build discovers is recorded in `DECISIONS.md`, never back-edited into this file.

---

## 1. Problem & The Bet

friday is a battle-tested Claude Code plugin (v0.4.0) — a PM-gated feature-delivery framework whose documentation and audit strength is real, but was bought with **too much ceremony per unit of maintainable code**. The build-engine study proved heavy per-feature ceremony did **not** buy first-run usability: a detailed TSOW + a bare free-run was as usable at ~¼ the cost, and every unusable build in the study was Opus + heavy ceremony. The failure was always mis-allocation, not incapacity.

**The bet:** invert the investment profile — **heavy front (discovery/TSOW) · light middle (one-shot build + as-you-go capture) · synthesized back (docs)** — and bet on **one-shot continuity** over task-gated decomposition. The mechanism hypothesis: a single unbroken build context keeps cross-cutting concerns coherent; every handoff seam is where integration failures live (in the study, the terminal; in a framework, the shared primitives — see §5).

**Named design goal (the PM's north star, in their words):** *"while [old friday] was strong on documentation, its ceremony was too heavy for the purpose of creating a maintainable codebase … relocate the ceremony to optimize build time and token efficiency, and redesign the mechanisms that create the documentation, maintainability, and sustainable infrastructure of friday."* The outcomes — documentation, maintainability, sustainable infrastructure — are **kept**; the per-unit **ceremony cost** is what gets engineered out. This goal is **measurable** and is a gating leg of the Definition of Done (§14).

**⚠️ REBUILD, not greenfield — the #1 risk.** vnext is a rebuild of an existing, hard-won system using the new recipe. A one-shot build **drops anything this TSOW does not name.** Every must-name item (§12) and landmine (§13) is a hard requirement precisely because the failure mode of ISSUE-001/002/008 is a build reaching a plausible-but-wrong version of an unstated convention. When in doubt, this TSOW names it.

**Posture (PM-approved):** **faithful relocation as the spine, with two deliberate hard swings** — (1) collapse the 32-command surface into a small, legible verb set; (2) design the net-new mid-build state model freely (it replaces the 8-checkpoint lifecycle — no legacy to preserve). Every audit-earned KEEP is preserved; only what the levers force is changed.

---

## 2. Criticality & Priority (the make-or-break primitive)

Per lever 2, this TSOW marks criticality so the build allocates effort correctly (the study's core lesson: mis-allocation sank the terminal while polishing the doc-viewer).

- **MAKE-OR-BREAK PRIMITIVE — build to destruction:** the **discovery → build → synthesis loop working end-to-end.** This is the entire thesis under test. It is built and verified **first** (as the foundation unit — §5), and its validation is a **hard gate**: if the loop does not work end-to-end, the build **stops and the approach is re-planned** (PM decision). Within it, the load-bearing components are **decision-capture fidelity** (`DECISIONS.md`, §6) and **doc-synthesis fidelity** (deterministic-extractor-vs-LLM-synthesis diff, §6).
- **Secondary surface — build to "adequate":** the breadth of commands, maintenance-mode surfaces, and ancillary tooling. Correct and preserved, but not gold-plated.

---

## 3. Solution Overview

vnext keeps friday's durable substrate and relocates its ceremony:

- **Discovery (heavy front):** brainstormer + strategist author the TSOW (the crown jewel), sharpened by the `grilling` protocol + `to-spec` completeness template + lever-2 additions (criticality, known-hard pins, dependency ordering, stack-risk register). A conditional researcher fanout fires only on flagged stack risks.
- **Build (light middle):** one-shot free-run against the TSOW + **as-you-go `DECISIONS.md` capture** with PM-engaged surfacing of architecture decisions (three-part test ∘ PROP-044 floor). Selective TDD on the TSOW-flagged logic core; manual verification for the interactive/visual surface.
- **Independent hardening (the one surviving ceremony, post-build not per-task):** claim-audit + fresh-context skeptics + security + redteam + tree-hash receipts.
- **Synthesis (synthesized back):** deterministic extractors for structure + LLM synthesis for rationale, grounded in `DECISIONS.md`; the diff between them is the QA oracle. Target arc42 + C4 + sparse ADRs.
- **Maintenance & growth (friday's other moat):** incremental `/feature`-equivalent slices, `adopt` (cold synthesis onto never-friday code), `backfill` (migrate already-friday projects), `reassess` (TSOW-anchored gap analysis).

Surface at a glance (corrected ledger, §6): commands **6 KEEP · 20 KEEP+CHANGE · 6 RETIRE**; roster collapses toward **architect / developer / tester / reviewer + security / redteam** (Planner & Scaffolder retire); hooks shift **ceremony-enforcement → substrate-invariant-enforcement**.

---

## 4. Numbered User Stories (with the requirement-ID spine)

> Carries the **FR/NFR/AC/S requirement-ID traceability spine** (PROP-051) relocated off the retired Planner into the TSOW. IDs are stable for the build's lifetime; the tester/reviewer inherit them and the post-build verify pass closes over them. Security criteria (`S{n}`, PROP-036) are owned by the architect hat. *(These IDs are the anchors the "must-test seams" in §7 and the coverage gate in §8 reference.)*

**US-1 — Discovery (PM).** As a PM, I run one discovery pass (brainstormer + strategist) that interrogates my idea and produces a TSOW I approve once up front, so I get walk-away autonomy during the build.
- **FR-1** Discovery uses the grilling protocol: dependency-ordered design tree, one-question-with-a-recommended-answer, look-up-before-ask, hard non-proceed gate.
- **FR-2** The TSOW carries criticality marking, known-hard pins with mandated verification, dependency ordering, a stack-risk register, and the `to-spec` completeness sections.
- **NFR-1** Every PM-facing artifact is calibrated to the PM's Audience / Learning-Preference / Awareness profile.
- **AC-1** No TSOW is written until the PM explicitly approves the shape; a post-write self-QA + a second PM read of the actual file precede DONE.

**US-2 — One-shot build (build agent).** As the build agent, I build the whole TSOW in one continuous context (target) with as-you-go capture, so cross-cutting concerns stay coherent and rationale survives.
- **FR-3** Build defaults to one-shot; falls back to foundation-ordered units only when the measured TSOW scope *verifies* too-large; ~120k in-flight backstop; `seam-handoff` carries `DECISIONS.md` + arc42 + code-map forward.
- **FR-4** Two-channel `DECISIONS.md` capture (pm-ratified harness-guaranteed; model-autonomous self-recorded), gated by the three-part worthiness test ∘ PROP-044 floor.
- **AC-2** The make-or-break loop is built + verified **first**, under a hard gate (fail → stop and re-plan).
- **NFR-2** Build-time and token spend **beat old-friday's ceremony baseline** (measurable; gating leg of the DoD).

**US-3 — JIT decision surfacing (PM).** As a PM, load-bearing architecture decisions are surfaced JIT with a recommendation + rationale + real alternatives, so I redirect the calls that matter without a per-feature approval wall.
- **FR-5** The decision-ask shape carries recommendation / rationale / alternatives; the hook writes `DECISIONS.md` on that shape only; parks as a file when the PM isn't watching (async ask-park-and-drain).
- **S-1** Any decision touching `schema-data` / `auth-security` / `external-api` / `friday-claims` / `spend` is surfaced + treated one-way regardless of the three-part conclusion.

**US-4 — Synthesized docs (maintainer).** As a maintainer, the delivered docs are accurate-by-construction (structure) and honest about rationale, carrying a liveness bit so "closed" never means "frozen."
- **FR-6** Deterministic extractors emit structure (dependency graph, API/route surface, data model, config, deploy topology); LLM synthesizes rationale from `DECISIONS.md` grounded in the generated diagrams; **the diff is the QA oracle**.
- **FR-7** Every closed record carries the dirty-bit (`Last-verified` / `Record-status`); a reconcile pass clears it; mutation flips it stale.
- **NFR-3** friday-docs retrieves via **live-parse + exact-after-normalization heading match** (never embeddings/RAG).

**US-5 — Independent hardening (hardening roster).** As the post-build hardening pass, I review the whole build distrusting self-report, so unreviewed judgment and security gaps are caught.
- **FR-8** Layer-1 claim-audit + Layer-2 fresh-context skeptics + security + redteam + tree-hash receipts, **post-build, not per-task**.
- **FR-9** Review envelope carries distinct `spec-compliance:` + `verdict:` lines; a stated rationale never downgrades a finding; the lead never pre-rates severity; the reviewer sees a `review-package` diff (additions *and removals*).
- **S-2** `model-autonomous` `DECISIONS.md` entries are scrutinized first (the un-ratified judgment / solo-build weakness).

**US-6 — Incremental growth (maintainer).** As a maintainer, I add a feature or adopt an existing repo through the same discovery→scoped-TSOW path, so growth reuses the recipe.
- **FR-10** `/feature` = mini-one-shot vs a TSOW slice; `adopt` = cold synthesis onto never-friday code (with the `0-imported.md` honesty marker); `backfill` = migrate an already-friday project; `reassess` = TSOW-anchored gap analysis + decision-log review.
- **AC-3** The incremental path is exercised once, with a good outcome, before "done" (§14).

**US-7 — Recovery & portability (operator).** As an operator, the build survives crashes/compaction and continues on Codex CLI when the Anthropic quota is exhausted.
- **FR-11** The `.friday/` substrate supports crash-resume (journal + session.lock + files-authoritative reconstruction); the Codex adapter ports the enforcement gate only, fail-closed.
- **NFR-4** Exactly one shared spawn-telemetry primitive writes the journal (ISSUE-006); every SubagentStop-scoped hook self-verifies agent identity in-hook (ISSUE-007).

---

## 5. Build Model (one-shot target; verified-units fallback)

**Decision rule (PM-set):** **one-shot is the TARGET; foundation-ordered units are the FALLBACK.** The fallback fires **only when the scope measurement of the written TSOW verifies the build is too large** — it is never presumed in advance. The evidence for leaning one-shot is the PM's experimental record, cited here as the rule's justification: **every chunked-context build in the experiments degraded quality and raised cost, every time.**

- **Upfront (scope metric):** after this TSOW is written, measure its real scope. If it measures within the smart zone, run one-shot. If it verifiably exceeds it, plan foundation-ordered units.
- **In-flight (backstop):** the **~120k-token smart-zone** is the in-flight backstop — if a one-shot run approaches it, fall back to a forced seam rather than push past.
- **Make-or-break loop first:** whether one-shot or units, build + verify the discovery→build→synthesis loop **to destruction as the first thing**, under the hard gate (§2).

**Forced-seam handoff (fallback shape).** When a seam is forced: build the **shared primitives + substrate first, in one unbroken head** (that is where continuity matters and where ISSUE-006-style fragmentation lives), then let seams fall at **clean foundation boundaries** downstream (MCP server, hooks, agents, commands, doc-synthesis tooling are separable and consume a now-frozen foundation, so continuity risk is low). Each unit **carries the substrate forward** to the next: `DECISIONS.md` + arc42 + code-map. This carry-forward is a **net-new primitive named `seam-handoff`** (PM-decided; see §13 — it is NOT `commands/handoff.md`, which is a client-facing deliverable) — an internal build-model mechanism, not a user command.

**Why the framework's seams are load-bearing.** A framework's cross-cutting concerns are its **shared primitives**: the typed tag-line grammar, the single journal/telemetry writer (ISSUE-006), the one-contract-file-per-handoff rule, the detector→sentinel→stop-gate shape. ISSUE-006 is the framework's version of the terminal bug — it is still OPEN in old friday precisely because journal instrumentation was retrofitted piecemeal across separate command work. One-shot continuity (or foundation-first sequencing under the fallback) is what prevents that fragmentation.

---

## 6. Implementation Decisions

### 6.1 Roster (agents)
- **Build agent wears architect + developer hats in one continuous context** (continuity thesis). Independence is reserved for the **post-build hardening roster** (reviewer / tester / security-reviewer / redteam-reviewer) where independence is the whole point.
- **KEEP (near-verbatim):** profiler (per-user prefs — friday-only asset), researcher (conditional fanout), security-reviewer, redteam-reviewer.
- **KEEP+STRENGTHEN:** brainstormer (fold in grilling protocol + lever-2 TSOW additions).
- **KEEP+CHANGE:** strategist (Stage 2 substrate-seeding survives near-verbatim — tech-stack fitness verdicts PROP-046, exposure PROP-036, environments PROP-038, scale profile, FRIDAY-CLAIMS, reuse catalog; Stage 1 largely subsumed by the TSOW; **Stage 3 roadmap + Stages 4/5 phase-maintenance cut**); architect (drop the four wave modes + cross-feature contract registry; single upfront architecture pass + JIT decision surfacing; owns trust-boundary sketches PROP-053, ADRs, `docs/architecture/README.md`, and the relocated security-criteria PROP-036); tester (Release-gate scope → post-build adversarial pass; iteration scope cut; **selective-TDD-for-logic-core is net-new**); reviewer (two-verdict severity + machine-checkable envelope carry forward; scope → whole build/branch; review-size tripwire PROP-047 becomes the normal case); debugger (add the counted 3-fails→escalate trigger + human-signal phrases); closer (slim once-per-build wrap-up: claim-liveness, size/structure, requirement-coverage-vs-TSOW-IDs, CHANGELOG, commit-never-push, teach-back payload — **NOT a doc synthesizer**); ux-designer (fold into front discovery — design the UI once, coherently).
- **RETIRE:** planner (content relocated: FR/NFR/AC/S spine → TSOW template; PROP-036 → architect), scaffolder (no phase/wave tree to materialize; the payload→materialize→self-verify *pattern* survives as a design precedent for the doc-synthesis writer).
- **CUT:** N>1 parallel developer lanes (PROP-022) — fragments cross-cutting coherence, the failure mode the redesign removes.
- Doc synthesis (arc42/ADR generation) is **new machinery owned by the extended architect hat**, not the closer.

### 6.2 Commands (corrected ledger: 6 KEEP · 20 KEEP+CHANGE · 6 RETIRE)
Collapse the mental model to a small legible verb set (swing #1). Dispositions from the verified audit:
- **KEEP:** profile, intake, redteam, secrev, feedback, help.
- **RETIRE:** phase, wave-design, orchestrate, implement, loop, archive. *(These are the ceremony being dropped — but their preserve-worthy mechanics are relocated, not lost — see §12 and below.)*
- **KEEP+CHANGE (20):** init (drop Stage 3/4 scaffold-into-phase/wave; keep detect-idempotence + CLIENT-INTAKE-BRIEF injection + git-baseline), brainstorm, research (TSOW stack-risk trigger), build (**becomes THE one-shot free-run + as-you-go capture command** — the single largest transformation), feature (mini-one-shot vs a TSOW slice), patch, bug, design-system, reassess (TSOW-anchored gap analysis + decision-log review), approvals (shrinks to the async-ask drain primitive), review (strategic health-check — retarget evidence sourcing; likely unified with reassess), wave-review (**retarget: post-build for blast-radius topics + post-incremental-feature-addition** — it is independent-hardening machinery, not wave ceremony), reconcile (substrate-invariant enforcer — keep near-as-is; per-feature dirty-bit granularity → per-build-unit/whole-project), reference (**becomes the central doc-synthesis engine** — extractor + `DECISIONS.md`-grounded synthesis, index-don't-duplicate, regenerate-via-git-diff), handoff (client deliverable — keep; source list updates), sweep (retarget source to open markers in the new substrate), backfill (retarget target to arc42 + `DECISIONS.md`), adopt (**becomes cold doc-synthesis** onto never-friday code; keep the `0-imported.md` honesty marker), resume (crash reconnaissance — rewrite classification against the new mid-build state model), autopilot (closest existing analog to lever-3 decision-surfacing — strip loop-machinery, retarget at gates within one build).

Preserve-worthy mechanics that cut across retired commands (must not be lost): the **Layer-1 mechanical claim-audit + Layer-2 adversarial skeptic** contract (from implement/orchestrate — relocate cadence to post-build + architecture-decision points); **decision-weight tiering** PROP-044 (reconcile explicitly with the three-part test, don't build a parallel mechanism); the **async ask-park-and-drain** primitive (PROP 2/F007 — a JIT-surfaced PM decision parks as a file, drained later); the **crash-resume journal**; autopilot's **escalation floor + auto/batch/escalate gate-policy dial**; loop's **wave-boundary maintenance-menu precedence ordering**; the **fail-closed extraction-gate** principle (archive).

### 6.3 Hooks (ceremony-enforcement → substrate-invariant-enforcement)
The **detector → sentinel → stop-gate** triple is preserved as the enforcement *shape* (§13). Per-hook fate:
- **KEEP as-is:** `session_lifecycle.py`, `usage_telemetry.py` (cost visibility — *more* load-bearing in vnext given the efficiency goal).
- **KEEP:** `substrate_ask_cleanup.py` (resolution tracking / orphan-sweep).
- **KEEP+EXTEND (mechanism reused, content net-new):** `substrate_ask_mirror.py` — see §6.6.
- **KEEP+CHANGE (substantial redesign):** the checkpoint pair (`checkpoint_sentinel.py` / `checkpoint_stop_gate.py`) — the mechanism survives; the C1–C9 content is 100% checkpoint-file-specific and is **replaced by a net-new mid-build state model** (swing #2 — no legacy to preserve). Plausible shape: *TSOW-approved → build-in-progress (DECISIONS.md actively written) → post-build-review-verdict-recorded → closed*, with the same verify-from-disk / arm-on-mismatch / block-Stop / self-clear shape.
- **CHANGE:** the review-format pair (`review_format_sentinel.py` / `review_format_stop_gate.py`) — cleanest to carry forward; only the path/regex moves (to `docs/reviews/…`) and the strict-on-Write rule relaxes if the post-build review is written once.
- **RETIRE:** `scaffold_sentinel.py` + `bootstrap_stop_gate.py` (~85% guards the retired scaffolder tree) — re-instantiate the *pattern* as a much smaller "init/TSOW-substrate gate" carrying the 2 surviving Strategist-owned checks (`CLAUDE.md` exists + well-formed `FRIDAY-CLAIMS`; plus "`docs/TECHNICAL_SOW.md` exists").
- **CHANGE:** `hooks.json` (rewire to the surviving set).

### 6.4 friday-docs MCP (vehicle keep · cargo rewrite)
- **Reproduce precisely (must-name §3.1):** the reader triad `list_sections` / `get_section` / `search_in` **live-parses the target file on every call** (no cache in the read path); `get_section` does **exact-after-normalization heading match** (strip → drop numbering → strip trailing `#` → casefold → collapse whitespace → strip emphasis), **NOT fuzzy, NOT embeddings, NOT keyword ranking**. Origin: PROP-024 was built inverse to a vector-DB instinct after transcript study showed semantic search was 3% of demand, 87% served under a 25%-of-file-bytes threshold. **A one-shot build asked for "a docs MCP" would reach for RAG — the exact-match/live-parse design is the whole point.**
- Keep the `plugin:` prefix escape hatch + path-safety containment (§3.2), the advisory sync-on-query SQLite index for lead-only aggregates (`resolve`/`status`, §3.3), the `plugin.json` `${CLAUDE_PLUGIN_ROOT}`-relative server path.
- **Cargo rewrite:** retrieval targets move from phase/wave/feature docs to the **arc42 / DECISIONS substrate**.

### 6.5 `.friday/` runtime substrate (regenerable-but-load-bearing, gitignored)
- `journal.jsonl` (append-only event log; **the single shared spawn-telemetry primitive** — §13/ISSUE-006), `session.lock` (heartbeat liveness; absence-of-ticking is the honest crash signal), `asks/` (decision-capture mirror dir), `index.db` (derived, sync-on-query, gitignored). **Name explicitly:** regenerable but not optional — losing it loses crash-resume, cost telemetry, and decision-capture provenance; must stay gitignored (the Closer's `git add -A` would otherwise commit it).

### 6.6 Decision capture (`DECISIONS.md`) — **net-new, not an "extend"**
> **Scope correction (verified by repo-grep):** `substrate_ask_mirror.py` writes **no** `DECISIONS.md`; **no** `DECISIONS.md` exists anywhere in old friday; the iron-agent `DECISIONS.md` the levers doc cites is a *different* codebase (the study's build target). Reused: the **mechanism** (fire-before-the-dialog harness capture, atomic writes, resolution tracking, orphan-sweep). Net-new: the schema, the fold-target, and the narrower ask-shape.

- **Schema:** `DECISIONS.md` = one entry per decision — **decision / why / rejected-alternative / timestamp** — with **PROP-023 growing-log archive discipline from day one** ("completion is a move, not a flag"; entry-cap + archive, not retrofitted).
- **Surfacing gate:** the **three-part decision-worthiness test** (hard-to-reverse + surprising-without-context + genuine trade-off between real alternatives) **composed with PROP-044's five-category floor** (`schema-data` / `auth-security` / `external-api` / `friday-claims` / `spend`) as a **categorical override** — anything touching a floor category is surfaced + one-way regardless of the three-part conclusion (guards against the model rationalizing away a schema change's "surprise"). PROP-044's two-way/one-way weight grammar + consequence-forward scaffolding shapes the ceremony once surfaced.
- **Two capture channels (same schema, provenance-marked `pm-ratified` vs `model-autonomous`):**
  - **Channel A — PM-ratified (harness-guaranteed):** when the builder decides something clears the gate *and* warrants a PM gate, it surfaces the decision using a **distinct, narrower decision-ask shape** (recommendation + rationale + real-alternatives). A **PostToolUse hook fires the `DECISIONS.md` write only for that shape** — never for ordinary permission dialogs — so **the model's judgment picks the shape, the harness guarantees the write**, without flooding the log with permission-grant noise.
  - **Channel B — model-autonomous (self-recorded):** decisions the builder makes autonomously that **clear the three-part worthiness bar but don't warrant a PM gate** (an obvious-but-consequential call — hard-to-reverse, but not a genuine PM trade-off) must still land in `DECISIONS.md`, **self-recorded by the builder**, marked `model-autonomous`. This is exactly the un-gated judgment a solo build is weakest at (record-native/Fable rationalized its own open read-surface in self-review), so it must not be silently omitted.
- **Honesty story for Channel B** (it cannot be harness-guaranteed — no PM dialog fires the hook, so say how it's kept honest — this is precisely the unstated convention a one-shot would fumble): capture-integrity for the self-recorded channel is enforced **by post-build reconciliation, not the harness.** Because structure is extracted deterministically (§6.7), a load-bearing decision visible in the code/architecture with **no corresponding `DECISIONS.md` entry** is surfaced by the **extractor-vs-synthesis-vs-DECISIONS diff** as an "uncaptured why" gap — a silent omission becomes a visible finding, not a vanished decision. Reinforced by the **capture-integrity timestamp-spread check** (self-recorded entries clustered at the end are a retro-fabrication smell, not decisions made as-you-go). And the `model-autonomous` marker is a **signal to the hardening pass** (§8): those are the un-ratified judgments, so the reviewer/security/redteam scrutinize them first.
- **Fire capture on verification findings too** (lever 3, both channels): a decision *revised by testing* (the RUN-2 ADR-002-class "bug the drill caught") is written back like any other. This is the one axis ceremony won in RUN-2; closing it makes the recipe strictly dominate.
- Built + verified in the **first (loop/foundation) unit** (§2).

### 6.7 Doc synthesis (structure deterministic · rationale synthesized · the diff is the oracle)
- **Structure → deterministic extractors** (dependency graph, API/route surface, data model, config surface, deploy topology): accurate-by-construction, regenerate on commit, a generated build artifact (C4/mermaid). Proven: a stdlib-`ast` extractor emitted 21 modules/57 edges + full route surface, 100% accurate, and caught the LLM's omitted `config` node.
- **Rationale → LLM synthesis from `DECISIONS.md`**, grounded in the generated diagrams (forbidden from inventing structure), honest where the why is uncaptured.
- **The diff between deterministic structure and LLM synthesis is the QA oracle** (catches LLM omissions *and* hallucinations) — this is the structural half of the verify pass.
- **Runtime/sequence flows:** **LLM-assembled grounded in an extracted call-graph** (not a noisy auto-graph).
- Target **arc42 + C4 + sparse high-value ADRs** (lean toward domain-modeling's ADR sparsity — few, high-value, gated by the three-part test — while keeping friday's richer template for the ones that clear the bar).
- **arc42 is new cargo, not a preserved convention** (§12 note). Adopt heading-pinning **as a pattern** (a fixed heading contract for any script-parsed doc; nothing renames a heading a tool depends on without updating the tool in the same change) but **derive the heading set** for the new structure.
- Preserve the **doc liveness dirty-bit** (`**Last-verified:**` / `**Record-status:** verified|stale`, PROP-028) — closed ≠ frozen; mutation flips dirty; a reconciliation pass clears it. Origin: a real external audit found CI/doc/stack drift on a live client project.

### 6.8 Enforcement doctrine (untrusted self-report)
- **Core doctrine, verbatim:** untrusted self-report + mechanical, independently-reproducible re-verification, with an explicit **asymmetric tolerance — "a false block is worse than a miss"** (precedent: v2's bootstrap-hook false-positive incident). Name this as a top-level principle governing every verification mechanism.
- **Three layers:** Layer-1 mechanical claim-audit (`git status --porcelain` scoped to reported paths — never `git diff --stat`, which misses untracked new files — + re-run the stated test/build command); Layer-2 fresh-context sonnet-pinned skeptics with refute-oriented prompts; **receipts backstop** (`receipt.py`) — each verifier run leaves a `{tree_hash, ok, blocking, ts}` sha256 over `CLAUDE.md` + `docs/`, and an out-of-band CI job re-runs the verifier fresh **and** checks the receipt's tree-hash matches current — because hooks fail open and MCP is advisory, so the durable backstop is out-of-band.
- **Content-independent verifiers to preserve in concept:** `verify_claims.py` (FRIDAY-CLAIMS vs real ground truth, string-mechanical), `verify_generated.py` (any generated artifact proves its own provenance).
- **Grafts (from compare-verification-review):** add a machine-checkable **`spec-compliance:` verdict** line to the review envelope (distinct from `verdict:`); the rule **"a stated rationale never downgrades a finding's severity"**; the rule **the lead never pre-rates a finding's severity / never tells the reviewer what not to flag** in a live dispatch; a **`review-package` consolidated diff** (additions *and removals*) on the reviewer's read list. Optional/low-priority: bind journal completion events to a git commit range.

### 6.9 Dispatch discipline (for ad-hoc hardening/synthesis/research subagents)
- **Never omit the model** — omission inherits the session's most expensive model. Every ad-hoc dispatch names `model:` explicitly. (Standing per-role tiering is already sound; this targets net-new ad-hoc dispatch points.)
- **A dispatch describes one unit of work, not the session's history** (guards the cited 42k-char context blowup at one-shot horizon). Apply concretely: fold resolved, already-written-to-`DECISIONS.md` entries **out** of any carried-forward block rather than letting it grow for the whole build.
- **File-handoff discipline** (brief / report / diff as files, never pasted).

### 6.10 Plugin manifest / marketplace / version / Codex adapter (product surface)
- **`plugin.json`** (single version source of truth): `name: "friday"` (unchanged — replace-in-place), **version bumped from `0.4.0`**, `mcpServers.friday-docs` at `${CLAUDE_PLUGIN_ROOT}/tools/doc-index/server.py`. Description rewritten for the vnext recipe (current one is stale "Friday v3 / Planner…Designer").
- **`marketplace.json`**: self-hosted single-plugin marketplace, `source: "./"`, **version deliberately omitted** (no duplicate-version drift). Description rewritten.
- **Replace-in-place** (same name, version bump) — **not** side-by-side. Expect the lockstep-rename surface if any name changes (precedent: `friday-v3`→`friday` was 1,346 lines/121 files in lockstep).
- **Codex portability KEPT in scope:** port the **enforcement gate only** (`tools/codex-adapter/`) to Codex CLI — the "cannot end while the record is verifiably broken" guarantee — with the deliberate **fail-closed** divergence (Codex versions verify directly on every Stop, block on missing/crashing verifier). This is a real, working quota-exhaustion-continuity capability and validates that the file-based-record architecture is substrate-agnostic (preserve-list §3.5).

---

## 7. Testing Decisions

- **Selective TDD (scoped Iron Law):** amend the Developer's absolute "YOU DO NOT TOUCH TESTS" → **"NO LOGIC-CORE CODE WITHOUT A FAILING TEST FIRST."** Logic-core is flagged by **TSOW criticality marking, not builder discretion**. The build agent writes those tests itself in-context (option (a) — a separate TDD→build handoff reintroduces the seam the one-shot bet removes). Pair with **delete-and-restart** discipline scoped to those units, and the anti-rationalization guard (friday has none today because the Developer never wrote tests).
- **Manual verification kept** for the interactive/visual surface (a friday-only capability superpowers lacks) — click-through / real-browser verification, a first-class mode, not an excuse.
- **Known-hard requirements pinned with mandated verification** (lever 2): compound cases spelled out (e.g. for app builds: terminal reattach + PTY-to-viewport sizing; multi-question/multi-answer forms) with **mandated real-verification**. For the vnext build itself, the analogous known-hard pins are the make-or-break loop's fidelity points (§2).
- **Test coverage placement (PM: both):** the TSOW **pins must-test seams** (logic core + the known-hard requirements) with mandated verification, **AND** a **post-build independent adversarial test pass** (§8) covers the rest.
- Builder *and* tester both get the **stack-risk register + context7** as *shared facts, independent verdicts* — a hallucinated expected value is worse than a hallucinated API; the tester re-verifies load-bearing assertions independently.

---

## 8. Independent Hardening (post-build, NOT per-task — the one surviving ceremony)

One lightweight **independent** pass after the build (relocated cadence, not per-feature):
- **Adversarial tests** (Release-gate scope: full suite + production-build + migration verification + BUG-XXX regression discipline + `S{n}` security-criteria coverage).
- **Layer-1 claim-audit + Layer-2 fresh-context skeptics** + **security-reviewer** (L1 scans / L3 file-level / L6 ops-readiness, may author starter `docs/ops/` runbooks PROP-048) + **redteam-reviewer** (seven lenses) + **tree-hash receipt backstop**.
- **Verification grafts** folded in (§6.8): `spec-compliance:` verdict, stated-rationale-never-downgrades, lead-never-pre-judges, review-package diff.
- **Debug grafts:** the counted **"3 failed fixes → treat as architecture problem, escalate before attempt #4"** trigger + the **human-signal phrase list** ("Is that not happening?", "Stop guessing", "We're stuck?") into `debugger`/`bug`.
- **Parallel independent-bug fan-out (superpowers adoption #2, accepted narrowly):** for genuinely independent bugs in disjoint subsystems only (no shared state) — debugging-only; NOT parallel build lanes.

---

## 9. Human-in-the-loop

- **Front:** the TSOW agreement (this document) — the relocated primary gate.
- **JIT:** architecture-decision surfacing during the build (three-part test ∘ PROP-044 floor, §6.6) — the surviving JIT human-in-the-loop; PM can rubber-stamp the recommendation at near-zero friction or redirect the load-bearing calls. Parked as files when the PM isn't watching (async ask-park-and-drain).
- **Worktree isolation + finish menu (superpowers adoption #1, accepted):** at build start, offer **worktree-isolation consent** (skip if a standing preference is declared); at the end (after the post-build review), present the **merge / push+PR / keep / discard** menu with **typed `discard` confirmation** for the destructive path. Directly fits the one-shot all-or-nothing failure shape (friday has no discard path today).
- **4-tier teammate-comms → principle only:** keep *scope-changes route through the lead* + *recipients self-flag escapes*; do not reproduce the full A/B/C/D tier bureaucracy for the leaner roster + post-build-only independent passes.
- **Post-write gate (this TSOW, and every authored artifact):** a self-QA pass + a **second PM read of the actual written file** — never report done off approved-content-plus-a-blind-write.

---

## 10. Dependency / Foundation Ordering

1. **Foundation unit (built first, in one head):** the shared primitives — typed tag-line grammar, the single journal/telemetry primitive (ISSUE-006 fix), the one-contract-file-per-handoff discipline, the detector→sentinel→stop-gate shape — plus the `.friday/` substrate and the **make-or-break discovery→build→synthesis loop** (with `DECISIONS.md` capture + doc-synthesis extractor). **Hard-gated (§2).**
2. friday-docs MCP (vehicle) + doc-synthesis engine.
3. Enforcement hooks (substrate-invariant set) + the mid-build state model.
4. Agents (build hat + hardening roster) + the collapsed command surface.
5. Plugin manifest / marketplace / Codex adapter.
6. Maintenance/growth surfaces (feature/adopt/backfill/reassess).

Under one-shot (target) this is the internal build order; under the verified-units fallback these are the seam boundaries, foundation-first.

---

## 11. Out of Scope (cites preserve-list §8 — do NOT reintroduce)

Retired ceremony a builder must not reintroduce out of habit (preserve-list §8):
- The phase/wave/feature **8-checkpoint-directory shape** and `scaffold.py`'s wave/phase materialization.
- **BOILERPLATE / EXPRESS / FULL** as three named ceremony tiers with per-tier rosters (the *triage-and-calibrate-effort* principle survives; the three-tier structure does not).
- The **async batch-approval queue** as per-feature gate machinery (`4-approval-request.md`, per-gate autopilot policies) — approval relocates to front + JIT.
- `wave-design` / `wave-review`-as-ceremony / `phase` commands and artifacts. *(Note: `wave-review`'s independent-hardening mechanism is KEPT and retargeted — §6.2 — only its wave-ceremony framing is out.)*
- `orchestrate` / `implement` as a manual two-command split; **Planner / Scaffolder** roles.
- The full **A/B/C/D teammate-comms** elaboration + `inter-team-notes.md` bureaucracy (principle only kept).
- The **3-lane parallel autopilot engine** + N>1 parallel developer lanes.
- **PROP-tracking ceremony as a runtime feature** (`shipped/open/rejected.md`, `Validated:` gate) — friday's own dev governance, not a product feature to reproduce.
- arc42/C4 is **not** a preserved convention — it is new cargo (do not mis-file as preserve).

---

## 12. Preserve List (must-name — "preserve these + why")

Every item below is a hard requirement (preserve-list §§1–6). Named because a one-shot build has no organic reason to reinvent them.

**Documentation-standards system (§1):** typed-tag-line grammar family (one fact/line, grep-able, attributed — every script-checked claim is a typed line, never prose; `[ACTION]`/`[INFO]`/`[DONE]`/`[OBSOLETE]` + FRIDAY-CLAIMS/REVIEW/DISPOSITIONS/weight/Traces-to families); doc dirty-bit liveness stamp (PROP-028); heading-pinning as a pattern (§6.7); doc-access decision rule (the ~25 KB `get_section`-vs-Read threshold) + the measured harness facts; teammate-contract governance principles (self-flagging; plan-mode-fit heuristic; consequence-forward phrasing); feed `docs/customizing.md`'s "don't customize" list in as an input.

**Honesty-invariant machinery (§2):** the core doctrine + asymmetric tolerance (verbatim); the detector→sentinel→stop-gate shape; **ISSUE-007 (§13)**; untrusted-self-report layers + receipts; content-independent verifiers (`verify_claims.py`, `verify_generated.py`).

**friday-docs MCP + extractor tooling (§3):** the live-parse + exact-after-normalization retrieval design (NOT embeddings); `plugin:` prefix + path-safety; advisory sync-on-query index; scaffold/registry engineering pattern (validate input, refuse silent clobber, self-verify output); **Codex adapter (§3.5)**.

**`.friday/` substrate (§4):** `index.db`, `journal.jsonl` (+ ask-mirror mechanism), `session.lock`, `asks/`; regenerable-but-load-bearing, gitignored.

**Plugin/marketplace/manifest (§5):** `plugin.json` single version source; `${CLAUDE_PLUGIN_ROOT}`-relative MCP path; self-hosted `marketplace.json` `source: "./"` no version; replace-in-place decision.

**Hard-won lessons (§6):** (1) one canonical producer/consumer contract file per filesystem handoff; (2) executable fail-loud completion checks quoting real output; (3) ISSUE-007 SubagentStop self-verify; (4) **ISSUE-006 single shared spawn-telemetry primitive**; (5) lightest tier still keeps a minimal audit-trail artifact; (6) structured grammars define+test their empty case; (7) liveness bit on closed records; (8) independent fresh-context re-verification + reproducible receipt; (9) growing logs get entry-cap+archive from day one (PROP-023 — applies to `DECISIONS.md`); (10) PM gates force understanding + named consequence for one-way doors (PROP-039 teach-back + PROP-044 floor).

**§7 supplementary:** decision-density→expensive-role heuristic; anti-premature-codification stance; consequence-forward phrasing; **the Audience/Learning-Preference/Awareness calibration system** (Profiler-driven — the persistent cross-project behavioral contract, not a nice onboarding survey).

**PROP-060c (external oracle):** whatever intermediate record vnext keeps must stay genuinely **external to the build's self-report** — the TSOW is authored before the build and never rewritten by it, so review/reconcile has a real oracle.

---

## 13. Landmines (name every one — a one-shot re-breaks them otherwise)

- **detector → sentinel → stop-gate** is the enforcement shape for every mechanical invariant (not a single point-in-time check).
- **SubagentStop matchers can't be trusted to filter by agent type** (`anthropics/claude-code#27755`, ISSUE-007): every SubagentStop-scoped hook **self-verifies agent identity in-hook**; a foreign/typeless event **never clears an armed gate**. This is a harness fact, not a friday choice — a naive port re-breaks it (the `hooks.json` matcher visually implies it filters reliably).
- **One canonical producer/consumer contract file** per filesystem handoff, cited by name on both sides (4 past incidents: ISSUE-001/002/005/008).
- **ISSUE-006 (OPEN):** exactly **one** shared spawn/accept/done telemetry primitive; every spawning surface calls it; **none hand-rolls its own journal write.**
- **friday-docs = live-parse + exact-after-normalization heading match, NOT embeddings/RAG** (semantic search was 3% of real demand).
- **Typed, grep-able tag-line grammar** for any script-checked claim; specify + test the empty/zero-entry case.
- **`CLAUDE.md` reaches ZERO spawned subagents** — anything a teammate/checker must know goes in the spawn message or its explicit Read list, never assumed from ambient inheritance. Use `get_section` over reading any doc >~25 KB.
- **Plugin manifest + self-hosted marketplace + single version source** — the manifest *is* the product surface for a Claude Code plugin (a code-focused build treats it as out of scope).
- **The "handoff" name collision:** the levers §7 build-unit-ceiling handoff (fork-with-compacted-brief) is a **net-new primitive named `seam-handoff`** (PM-decided); `commands/handoff.md` is a **different, existing client-facing deliverable** and keeps the `handoff` name. Never conflate the two.

---

## 14. Definition of Done (dogfood-validate)

**NOT done** until friday-vnext runs its **own discovery → build → synthesis loop** on a **real test project** and produces a good outcome. Test-project **shape pinned** (specific project chosen later): a **small but real app-with-a-UI** — exercises the kept design/UX surface, gives a clean comparison to the iron-agent evidence, and is small enough to hit the one-shot **target** path.

**Good-outcome bar (three-part gate, all three must pass):**
1. The built app is **usable/correct** on hands-on verification.
2. The **synthesized docs are good** — blind-judged against a baseline (RUN-2 method).
3. **Efficiency beats old-friday's ceremony baseline** — build-time and token spend. *(This leg is gating — it turns the ceremony-relocation design goal into a measured number.)*

**Incremental-growth in the DoD:** vnext is not done until the **incremental path is exercised once** with a good outcome — add a feature to the dogfooded app, or adopt an existing repo — so friday's maintenance moat does not ship unvalidated.

---

## 15. Open Questions

These are genuinely open and deferred to build-time — none gate this TSOW's approval; each is resolved in the unit that owns it, and its resolution is captured in `DECISIONS.md`.

- **OQ-1 — mid-build state model.** The exact state set that replaces the 8-checkpoint lifecycle (swing #2). Designed freely in the foundation unit; plausible shape in §6.3.
- **OQ-2 — `reviewer-strategic` vs `reassess`.** Whether the strategic health-check merges fully into the redesigned `reassess` or stays a distinct periodic role (the audits lean merge).
- **OQ-3 — `sweep` retarget source.** What replaces closed-feature-README `[ACTION]` notes as the source of deferred cross-cutting follow-ups in the new substrate.
- **OQ-4 — runtime-flow diagram fidelity.** How much review the LLM-grounded-in-extracted-call-graph output needs before it's trusted (the extractor-vs-synthesis diff is the oracle; the residual is the human-review budget).
- **OQ-5 — the scope metric + threshold** that decides one-shot-vs-units (§5), computed once this TSOW's real scope is measured.
- **OQ-6 — the specific dogfood test project.** Shape pinned (§14); the concrete instance is chosen at dogfood time.

## Increments

- INC-1 — Compaction continuity: hook-steered summaries, filed handoffs, four-layer re-orientation (approved 2026-07-15)
- INC-2 — Lanes become skills: pilot migration + skill-aware machinery (approved 2026-07-15)
- INC-3 — Lane bundling: the single-homing boundary rule, the machinery guarantee, and ship-gate coverage for bundled files (approved 2026-07-15)
- INC-4 — Runtime scriptification: a ranked candidate register, one proven tool, and a recurrence-watch habit (approved 2026-07-16)
- INC-5 — Proposals ledger: one file per proposal, folders as status (approved 2026-07-16)
- INC-6 — Project-owned .claude/ scaffold: doctrine contract, settings + path-scoped rules seeded at init, never-clobber parity (approved 2026-07-16)
- INC-7 — Lanes become model-invocable: retire the typed-only wall, move the discriminator to an explicit marker (approved 2026-07-16)
- INC-8 — Ship friday public: a fresh clean marketplace repo, MIT-licensed, the lab kept private (approved 2026-07-25)
