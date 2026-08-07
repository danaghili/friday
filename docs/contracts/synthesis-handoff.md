# Contract: extractor ↔ synthesis handoff (doc-synthesis)

The single contract between the deterministic extractor and the LLM synthesis
— the make-or-break loop's structural seam. Producer of facts:
`tools/doc-synthesis/extract_architecture.py` (the A.1 IR). Producer of prose:
`/friday:reference` Phase 2. Judge: `tools/doc-synthesis/synthesis_diff.py`
(the QA oracle). All three cite THIS file.

## The IR (docs/architecture/generated/architecture-ir.json)

Arrays always present: `modules[]` (id, path, loc) · `edges[]` (from, to,
kind, line, deferred) · `routes[]` · `config_surface[]` · `data_models[]` ·
`deploy_topology[]` · `ambiguous_imports[]` (from, name, candidates, line —
the Python bare-import refusal record, D-0151; this line is its contract
home, corrected under INC-207 FR-207.7 after the array shipped without it) ·
`unparseable[]`. **Zero modules = all arrays empty +
`"generated-empty": true`** — a well-formed document, never a missing file or
a crash; every consumer accepts it (A.2). Provenance-stamped
(`generated-by`/`generated-at`), regenerated on commit, never hand-edited.

**JS-family arrays (INC-207 FR-207.1), present exactly when the tree carries
any `.js`/`.jsx`/`.ts`/`.tsx`/`.mjs`/`.cjs` file:** `components[]` (name,
module, line — exported capitalised bindings in `.jsx`/`.tsx`, D5) ·
`js_unresolved[]` (from, name, kind:`import`|`route-prefix`, candidates, line
— the named-refusal list, FR-207.2). On a JS tree they are present-and-empty
rather than absent; on a JS-free tree they are absent entirely, so a
Python-only project's IR is byte-identical to the eight-array document above
(AC-207.7). JS module ids are the real on-disk relative path, extension
included (D8) — never dotted. Producer of the JS facts:
`tools/doc-synthesis/extract_js.py`, merged by the extractor's driver.

## What the synthesized 05-building-blocks.md MUST carry (heading-pinned)

1. `## Component inventory` — every IR module id as inline code, one per
   list line (`- \`the.id\` — description [why: DECISIONS.md D-NNNN]`), OR the
   exact sentinel `_No components identified._` for the zero-module case.
   Renaming this heading breaks the oracle — nothing renames a heading a tool
   depends on without updating the tool in the same change.
2. A mermaid `graph LR` whose node declarations are `safe_id["real.id"]`
   (the extractor's sanitize transform: non-alphanumerics → `_`) and whose
   edges use those node ids. `-.->|deferred|` marks function-local imports.

**The size rule (INC-207 FR-207.3).** Above a declared per-project threshold
— the typed line `synthesis: inventory-threshold <= N` in
`docs/standards/coding-standards.md`, alongside the project's other measured
bars; no file or no line means the default the oracle declares
(`DEFAULT_INVENTORY_THRESHOLD` in `synthesis_diff.py`) — the inventory
section may instead carry the exact sentinel
`_Inventory: generated — see docs/architecture/generated/architecture-ir.json._`
plus area-level narrative. The oracle then proves the generated inventory is
the module source of record, still blocks any module the inventory section
names that the code does not contain, and skips the module-graph edge diff
(an area diagram is not a module graph). **Below the threshold the sentinel
is not accepted** — the full enumeration stays the contract unchanged, so a
small project can never opt out silently. The rule is language-blind (D10).

## Prose rules binding the synthesis (INC-203 FR-203.2)

A regenerated document cannot read an authoring convention, so the record-authoring rules bind here, at the contract the producer already reads. Their single home is the project `CLAUDE.md` § Conventions (D-0161); this section is the producer-side binding, not a second home — where wording differs, the home wins.

1. **No derivable figure in prose** — a number, count, or list that the IR or a tool owns is written as "every …" or as a pointer to its generated source, never as the figure.
2. **No restated single-homed rule** — a rule that has a home is pointed at, never re-worded into the synthesis.
3. **No reader-relative referent carrying a machine fact** — a regenerated sentence names the machine's committed anchor or the setting the tools read, never a phrase that rebinds to whoever opens the file (INC-110 D10).

`skills/reference/SKILL.md` Phase 2 cites this section from the producer side (D-0162).

## What the oracle cannot do (INC-203 FR-203.6)

`synthesis_diff.py` verifies the component inventory and the diagram against the IR and reads **no prose** — an oracle-clean verdict never means the document's sentences are true. Worked example: `05-building-blocks.md` once claimed every `.friday/` write goes through the substrate module — false at the time (D-0135 says so outright) — and the claim rode through a clean oracle verdict in the very file the oracle certifies, caught only when a reader checked the prose. The oracle proves the inventory; the prose stands on the rules above.

## The oracle's verdicts

omitted-module / omitted-edge / hallucinated-module / hallucinated-edge /
missing-inventory → **blocking** (fix the SYNTHESIS — the extractor is ground
truth). no-diagram → warn. uncaptured-why (structure exists, zero DECISIONS
entries) → info: the §6.6 honesty backstop — back-fill honestly or leave the
"Rationale not captured" marker; never paper over it.
