# Contract: extractor ↔ synthesis handoff (doc-synthesis)

The single contract between the deterministic extractor and the LLM synthesis
— the make-or-break loop's structural seam. Producer of facts:
`tools/doc-synthesis/extract_architecture.py` (the A.1 IR). Producer of prose:
`/friday:reference` Phase 2. Judge: `tools/doc-synthesis/synthesis_diff.py`
(the QA oracle). All three cite THIS file.

## The IR (docs/architecture/generated/architecture-ir.json)

Arrays always present: `modules[]` (id, path, loc) · `edges[]` (from, to,
kind, line, deferred) · `routes[]` · `config_surface[]` · `data_models[]` ·
`deploy_topology[]` · `unparseable[]`. **Zero modules = all arrays empty +
`"generated-empty": true`** — a well-formed document, never a missing file or
a crash; every consumer accepts it (A.2). Provenance-stamped
(`generated-by`/`generated-at`), regenerated on commit, never hand-edited.

## What the synthesized 05-building-blocks.md MUST carry (heading-pinned)

1. `## Component inventory` — every IR module id as inline code, one per
   list line (`- \`the.id\` — description [why: DECISIONS.md D-NNNN]`), OR the
   exact sentinel `_No components identified._` for the zero-module case.
   Renaming this heading breaks the oracle — nothing renames a heading a tool
   depends on without updating the tool in the same change.
2. A mermaid `graph LR` whose node declarations are `safe_id["real.id"]`
   (the extractor's sanitize transform: non-alphanumerics → `_`) and whose
   edges use those node ids. `-.->|deferred|` marks function-local imports.

## The oracle's verdicts

omitted-module / omitted-edge / hallucinated-module / hallucinated-edge /
missing-inventory → **blocking** (fix the SYNTHESIS — the extractor is ground
truth). no-diagram → warn. uncaptured-why (structure exists, zero DECISIONS
entries) → info: the §6.6 honesty backstop — back-fill honestly or leave the
"Rationale not captured" marker; never paper over it.
