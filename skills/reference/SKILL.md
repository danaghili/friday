---
name: reference
description: run when the docs must be regenerated from the code — structure plus grounded rationale
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:reference` — offer it before any work: “The docs and code may have drifted — run `/friday:reference` to regenerate the reference set from the code?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:reference` — the central doc-synthesis engine: deterministic structure + DECISIONS-grounded rationale, with the diff as the QA oracle.

### Phase 1: Extract (deterministic — accurate by construction)

`python3 "${CLAUDE_PLUGIN_ROOT}/tools/doc-synthesis/extract_architecture.py" --root .` — emits the A.1 IR (`docs/architecture/generated/architecture-ir.json`) + `dependency-graph.md` + `api-surface.md`, provenance-stamped, **regenerated on every run, never hand-edited**. Zero modules emits the well-formed empty document (`"generated-empty": true`), never a crash.

Then confirm those three stamped outputs mechanically, real output quoted: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_generated.py" --cmd reference --require docs/architecture/generated/architecture-ir.json docs/architecture/generated/dependency-graph.md docs/architecture/generated/api-surface.md --json` — present → non-empty → provenance stamp (a `/friday:reference` run always regenerates all three, so they are `--require`d, not optional). A failure here means the extractor mis-stamped or a hand-edit clobbered a header, not a synthesis problem; expected clean is `"ok": true`, `"checked": 3`.

### Phase 2: Synthesize (rationale — only as good as DECISIONS.md)

Write/refresh the arc42 set under `docs/architecture/` (one file per numbered section; mermaid only). Grounding discipline is the whole point:
- Descriptive sections (context, building blocks, runtime, deployment, crosscutting, glossary) reconstruct from **code + the generated IR** — name real files, functions, env vars.
- `05-building-blocks.md` MUST follow `docs/contracts/synthesis-handoff.md`: a `## Component inventory` listing every IR module id as inline code (or the `_No components identified._` sentinel), and a mermaid component graph whose node declarations are `safe_id["real.id"]`.
- Rationale sections (solution strategy, ADRs, risks) cite `DECISIONS.md: D-NNNN` or say **"Rationale not captured — the artifact shows the choice, not the alternatives weighed."** Never invent a rejected alternative to fill a template.
- **Runtime/sequence flows:** LLM-assembled, grounded in the extracted call/import graph — not a noisy auto-graph.
- ADRs (`docs/architecture/decisions/ADR-NNN-<slug>.md`): sparse, high-value, gated by the three-part test; format Context / Decision / Alternatives rejected / Consequences; cite their D-NNNN sources.
- **Regenerate-via-git-diff:** on re-runs, `git diff` since the last synthesis tells you which sections' grounding changed — re-synthesize those, don't rewrite the set. Index, don't duplicate: link to the generated files, never paste them.

### Phase 3: The oracle

`python3 "${CLAUDE_PLUGIN_ROOT}/tools/doc-synthesis/synthesis_diff.py" --ir docs/architecture/generated/architecture-ir.json --doc docs/architecture/05-building-blocks.md --decisions docs/DECISIONS.md`

- Blocking findings (omitted/hallucinated modules or edges) → fix the SYNTHESIS (the extractor is ground truth) and re-run until clean.
- `uncaptured-why` findings → load-bearing structure with no decision entry: back-fill honestly (`--back-filled` if the decision time is known) or leave the "rationale not captured" marker — a silent omission has become a visible finding; do not paper over it.

### Phase 4: Liveness

Stamp `**Last-verified:** <date>` / `**Record-status:** verified` on the arc42 README (PROP-028 — closed never means frozen; any later mutation flips it stale; `/friday:reconcile` clears it).

### Phase 5: Refresh the code graph — LAST

The graph refreshes **after** the docs, never before — code lands → docs regenerate (Phases 1–3) → the graph refreshes here. This ordering is the whole point: a graph built before the docs would map a description that is about to change.

- **Soft integration.** If **graphify** is installed (pinned package `graphifyy`, double-y — lookalikes are unaffiliated), refresh its graph for this project, then record freshness: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/graph_refresh.py" --root .` writes `.friday/graph.stamp` at HEAD, the counterpart guard #8 reads. If graphify is absent, the IR regenerated in Phase 1 (`architecture-ir.json`) **is** the graph — there is no adopted graph to stamp, and `graph_refresh.py` says so; friday's own index loses no function, only richness.
- **EXTRACTED only as evidence.** Every edge the graph carries is tagged `EXTRACTED` (read from the source) or `INFERRED` (a semantic lead). friday cites **EXTRACTED** edges as evidence; `INFERRED` edges are leads to verify, never proof. The explore consumers reach the graph through one seam — `tools/graph_query.py` — which routes to graphify when present and to friday's own IR when not, carrying this rule in every answer.
- **Between refreshes it stays honest.** Guard #8 flags a stale graph as "N commits behind" (warn, never block) until the next reference run re-stamps it.
