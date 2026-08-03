---
name: reconcile
description: run before a moment that deserves a clean conscience — the PM asks for a deep clean
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:reconcile` — offer it before any work: “A clean-conscience moment is coming up — run `/friday:reconcile` for the standing deep clean?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:reconcile` — the deep clean before a moment that deserves a clean conscience: a merge, a release, a handover. You make the record and reality **agree in writing** — or you hand the PM a short list of exactly where they don't, and what they decided about each (contract: the approved `/friday:reconcile` behavior paragraph). This is the deep clean, not the daily rhythm — landing a change already re-verifies what it touched; this is the full sweep. Granularity: the whole project — the default, and the deep clean's home ground before a merge, release, or handover — or one unit via a `--unit` hint in `$ARGUMENTS` when a single unit's record needs the same full sweep in isolation (D-0038).

### 1. Re-verify every record claim against reality

Run each, quoting real output — never summarize a verifier you didn't run:

1. **State record:** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_state.py" --root . --json` — the K-rules (K0/K4 always; K1–K3/K5/K7/K8 when closed; K6 capture-integrity warn).
2. **Claims drift:** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_claims.py" --root . --all --json` — FRIDAY-CLAIMS (stack, thresholds, non-goals, `world=`, `provenance=`) vs real manifests (string-mechanical; `unverifiable` is a disposition for the PM, not drift).
3. **Requirement coverage:** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_coverage.py" --root . --json` (add `--tsow`/`--ledger` to close a second oracle — the two ID spaces never join). **Then cross-check who verified each line (INC-200).** Each disposition now carries a verifier channel, and an unmarked line reads as `lead-authored` — appended by the lead in the same context that built the slice, not by an independent tester (`docs/reviews/coverage.md` header). That is exactly the class reconcile re-examines, the same way it re-examines `model-autonomous` deviations in §2: read the `lead-authored` lines, and for each one either **re-verify it here** — the evidence it cites is a file, a grep, or a test you can run right now — or **hand it to the PM as a line that has never been independently checked**. Silence is not a pass; a line nobody re-checked is reported as such, never quietly upgraded to `independently-tested`.
4. **Synthesis freshness:** re-run the extractor + `synthesis_diff` (see `/friday:reference` Phase 3). A diff here means the code moved after the docs — the docs are stale, not wrong-by-authorship.
5. **Capture integrity:** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/capture_integrity.py" --root . --json` — DECISIONS.md timestamp spread (self-recorded entries clustered at one end are a retro-fabrication smell; `back-filled: true` is exempt by design).
6. **Receipts:** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/receipt.py" check --root . --verifier state` — the out-of-band backstop.

Recorded-as-passing tests are re-run; the tester's release gate is re-derived, not trusted (`docs/reviews/` verdicts are claims like any other).

### 2. Re-prove the living system's promises

The record isn't only files — a deployed system makes promises too. Compose every briefing from `${CLAUDE_PLUGIN_ROOT}/docs/dispatch-briefing-template.md` and save it at dispatch with `--prompt-file` — from the file, never from memory: a reassembled briefing drops pieces silently, and every briefing on disk before INC-208 was missing one. Spawn the two operations experts to re-prove their reconcile rows (models named, telemetry via `spawn_telemetry.py --phase reconcile:ops` / `reconcile:cost`; each spawn message carries the `friday-docs: available` stamp — or a plain-Read pointer to `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md` — and the explicit Read list):

- **`friday-operations`** (model: **sonnet**) runs the **operations battery**: the row set, each row's kind, the verdict grammar, and every row's ask live in `docs/contracts/ops-battery.md` — the battery's single home, cited never restated (INC-102 D8). Every row comes back **proven**, **not proven**, or **not applicable** under that grammar, real output quoted, never a narrative.
- **`friday-running-cost`** (model: **sonnet**) owns: the **monthly bill against its projection** — within the projection's stated tolerance, or flagged with what changed (a price hike, a growth surprise, an unprojected vendor). **The projection it re-checks against is `docs/ops/cost-projection.md`** — written at stack confirmation by the same role (`agents/bootstrap/strategist.md` §1, INC-200), cited here by name so the row has a real oracle instead of a remembered number. No projection on disk (a project that declined the offer, or one with nothing vendor-priced) means this row reports "no projection recorded" — never an invented baseline.

Each expert's rows come back under its own grammar — the battery's from its contract, the cost row within-projection or flagged with what changed. The lead surfaces every finding and every row short of proven to the PM.

**Maintainability deep sweep (INC-008 D8 — reconcile is its on-demand home).** When the project declares maintainability bars, spawn `friday-maintainability-judge` (model: **sonnet**; telemetry via the single primitive: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-maintainability-judge --phase reconcile:maintainability`; its spawn message carries the resolved plugin tools path — expanded, never the literal `${CLAUDE_PLUGIN_ROOT}`) for the full pass over the whole tree — the standing deep clean the harden/close passes do per-build. Two reconcile-only extras: **cross-check the `model-autonomous` deviations** in `docs/STANDARDS-DEVIATIONS.md` (contract: `docs/contracts/standards-deviation.md`; a justification the judge recorded without PM ratification is exactly what reconcile re-examines — a stale or weak one becomes a finding), and the optional **code-health readout** — complexity/size/duplication counts, the three metrics the measurer actually computes (`python3 "${CLAUDE_PLUGIN_ROOT}/tools/maintainability_measure.py"` — an informational trend, never a gate; it computes no composite "Maintainability Index"). A bars-less project skips this entirely.

### 3. Run the full guardrail battery, deliberately

Reconcile **is** the on-demand invocation mode of the entire check library: every guard that normally fires on an event runs here, across the whole project, so the guards themselves get exercised — not just trusted. The worklist is `hooks/hooks.json` — the wired registry mapping every event to its guard's checker; walk it entry by entry, run each guard's checker over its scope, and report the tier (block / warn / silent) each returns. A registered guard whose checker can no longer run is itself a finding — and the registry is what makes "can no longer run" detectable at all, because it is the complete set to check against. One checker rides beside the registry rather than in it (OQ-202.8): in a repo carrying the proposal pipeline (friday's self-build), run `python3 tools/proposal_pipeline_check.py --root .` here in reporting mode — every finding, the retired-folder class included, is surfaced to the PM like a warn tier, never a block (; the checker's blocking home is the feature close).

**The secret-store posture row (INC-204).** Run `python3 "${CLAUDE_PLUGIN_ROOT}/tools/secret_posture_check.py" --root . --json` — value-blind by construction (it classifies dotenv files by name and never opens one): the declaration exists or an accepted risk is on record, no value-carrying file is tracked, the ignore rules hold. Reported like a warn tier, never a block — a real reconcile run continues past a finding; the increment's one bite lives at handoff's keys completion gate (D4), nowhere here.

**The prose-rot probe rides beside the battery too (INC-203 D5/D6 — the deep clean is its only run-moment; per-project since INC-101).** In any project this lane runs in, spawn the shipped **`friday-doc-truth-checker`** (model: **opus** — named at the call site, INC-203 D8 and INC-101 D3, no cheap tier for any class of the read; telemetry via the single primitive: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-doc-truth-checker --phase reconcile:doc-truth`) over the project's **whole record set** — derived at run time by `python3 "${CLAUDE_PLUGIN_ROOT}/tools/doc_probe_scope.py" --root . --json` against the project's own size bar, with everything not read named unread in the report and never folded into a clean verdict — never a changed-file scope:
the one divergence class no authoring rule prevents is a sentence that was true when typed and rotted when the code changed under it, and only a deliberate prose-against-code read finds it — the flagship specimen sat in a file no build had touched, invisible to every changed-file-scoped check.
spawn-unnamed: friday-doc-truth-checker
The probe **reports, never blocks** (D7: a model's reading of prose can be wrong in both directions — the measured cheap-tier false cleans are the proof;: it never edits, never fixes). Its outcome is always written: each finding gets a disposition at the close — **fixed**, or **kept with its reason** (a frozen or append-only record is the standing reason) — and a run with nothing to report records **clean** as a distinct outcome, never silence. What this probe surfaces is exactly what the PARKED entry's revisit condition reads (KH-4): a rot-class finding the authoring rules did not prevent is the evidence that brings the parked machinery back through §5's roundup.

### 4. Disposition drift — refresh or flag, never silently patch

- **Mechanically fixable → refresh it**: regenerate stale generated docs; a stale code graph regenerates (code → docs → graph, in that order); re-stamp the dirty liveness bit **only on a clean run** — `python3 "${CLAUDE_PLUGIN_ROOT}/tools/state_record.py" --mark verified --root .` flips `record-status: stale` → `verified` and re-dates `last-verified:` in one move. This clear is reconcile's exclusive: feature, patch and bug set the bit, nothing else lowers it (D-0106; contract: `docs/contracts/state-record.md`).
- **Everything else → flag to the PM with what changed and its severity.** Never edit `docs/TECHNICAL_SOW*.md` — drift against an oracle is a finding for the PM; the oracle stays the oracle (amendments are the PM's, on the record).

These are the same checkers the closer runs at a build's close — but the closer GATES one build; reconcile is the standing deep-clean across the whole project. Same instruments, different occasions.

### 5. The parked-pile roundup

Round up everything that was ever parked **with a recorded decision** and present it for a fresh call — *still deferred / worth doing now / no longer relevant*:

- **the PARKED ledger — first, and mechanically**: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/parked.py" list --root .` (contract: `docs/contracts/parked-ledger.md`). Every live entry is re-presented with its `revisit-when:` condition — has it arrived? On the PM's fresh call, resolve what moves or dies (`parked.py resolve --root . --id PARK-NNN --by reconcile`; the call itself is captured where decisions live) and leave the rest waiting. A malformed line in the list is a finding, never skipped;
- deferred findings (harden/security/redteam dispositions marked defer);
- deferred requirement work;
- **what is waiting on validation evidence, and for how long (pipeline projects only — D12):** every resident of `proposals/03-pending-validation/`, each with its waiting time — waiting-since is the built/closed date its header `note:` records, else the date git shows the file arriving in `03` (`git log --diff-filter=A --format=%as -- <path>`). Built-but-unproven work comes back to the PM here and nowhere else — signals at natural moments only, no session-start nagging, no thresholds (D-0111);
- **accepted risks — which age**: an accepted risk resurfaces for re-decision, because a reason that held at acceptance may have expired — including every battery row ratified not-applicable (`python3 "${CLAUDE_PLUGIN_ROOT}/tools/ops_battery.py" read --root .`, the rows carrying a `ratified:` date; contract: `docs/contracts/ops-battery.md`): each reason is re-presented for a fresh call, so a decline never hardens into a permanent exemption;
- waiting-room ideas not yet in the ledger (discovery's conscious exclusions predating D-0108, feature supersessions) whose reasons may have lapsed.

This pile is *dispositioned deferrals* — each one waits BY a recorded PM decision. That is the whole rule: a decision itself never waits (it is made, or it stalls the work until it's made), but a decision *to defer* is a wait the PM chose — and reconcile is where those chosen waits come back for a fresh call.

### Close

Battery rows proposed not-applicable are ratified here, by the lead on the PM's ruling and never before it: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/ops_battery.py" ratify --root . --row <key>` — the ruling the deep clean's accepted-risk aging will re-present (contract: `docs/contracts/ops-battery.md`).

At the end: the record and reality agree, in writing — or the PM holds a short list of exactly where they don't and what they decided about each. Commit on the PM's word; never push unless they say so.
