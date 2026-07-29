---
name: design-system
description: run when the PM wants the interface settled — once, coherently, before any building
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:design-system` — offer it before any work: “Interface decisions are piling up — run `/friday:design-system` to settle the whole interface once, before building?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:design-system` — settle the interface **once**, coherently, during discovery, before any building. You know your place in the toolchain: **friday conceptualizes; claude-design designs; design-sync delivers.** This command owns the first of those three.

Gate: runs during discovery (before or alongside `/friday:brainstorm`'s output) for any TSOW with a real screen; a UI change after approval routes through `/friday:feature`, never a quiet redraw here.

**Two doors in, one behaviour.** Besides a typed `/friday:design-system` or the offer-beat above, this lane is entered from **`/friday:init` Stage 3's fork** (D-0110 / INC-200): when the TSOW carries a substantial user-facing surface, init offers this pipeline before falling through to its lighter inline `friday-ux-designer` pass. An init-originated entry arrives already-offered and already-accepted — **do not re-offer** (the PM has answered that question once, in init) — and carries the TSOW path plus the Stage-0 artifact findings in its message. Everything downstream is identical; the entry door changes nothing about the work, and whatever this lane produces is cited by name in the TSOW's §5 *Design & UX artifacts* table so `/friday:build`'s pre-flight can read it.

### 1. Conceptualize (friday's half — the UX Designer)

Spawn the UX Designer (`friday-ux-designer`, model: sonnet; telemetry via the single primitive: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-ux-designer --phase design:system`). Its spawn message carries the `friday-docs: available` stamp (or a plain-Read pointer to `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md`) and the explicit Read list. Spawn message: the product intent, the audience profile (FRIDAY-PROFILE overlay), and an explicit Read list. Its conceptual deliverables into `docs/design/`:

- **Who is looking at each screen** — on what device, in what context.
- **User journeys mapped to the spec's numbered requirements** — every journey traces to an FR/US it serves.
- **The screen inventory** — what screens exist and what each one must *do*. Not how it looks.

### 2. The visual companion serves this stage

When a concept is clearer **shown** than told — a rough layout, two arrangements side by side, a flow — offer the visual companion, just-in-time: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/visual-companion/companion_server.py" --root .` opens a local tab (zero dependencies) where the PM clicks through **alignment sketches — never the design itself** — up to three rounds. Route per question with `tools/visual-companion/offer.py` (showable → the tab; a requirement or trade-off → the terminal); the PM's clicks and hesitations come back as elicitation data. The companion settles *concepts*; it does not draw the product.

### 3. Design, then deliver (claude-design → design-sync)

The real design system — tokens, components, polished screens — is created in **claude-design**, the proper design environment, seeded with the agreed concepts and the PM's existing brand assets. **design-sync** then pulls the result into the project (and is callable on its own whenever the designs change upstream). What lands is the **locked design contract**: journeys tied to requirements, the screen-by-screen build sheet, and the synced designs the build implements against.

### 4. The locked design contract (cuts both ways)

The PM approves the **actual synced artifacts**, not descriptions of them. Once locked:

- The build may **not invent screens** — a **build-lane rule verified at review**, backed by this lane's click-through, and carried to the build by the TSOW's §5 *Design & UX artifacts* table, which `/friday:build`'s pre-flight reads (INC-200). A screen the sheet does not carry is a `[FRIDAY-DECISION]` ask, never a silent addition. **No hook enforces this** — `design_contract_guard.py` (which this line used to credit) gates *edits to an already-locked contract or design file* against a decision-log re-sync record, which is a different job; `agents/roles/ux-designer.md` describes that guard correctly. A checker that could know what counts as a screen in an arbitrary stack is a research problem, deferred by name (INC-200 §9b). *The claim was corrected rather than kept: a promise that reads as enforced and is not is the failure class the 2026-07-28 audits kept finding (D-0123).*
- A design change after approval is a **recorded decision that re-syncs** (`tools/decisions_append.py`, then design-sync again) — never a quiet redraw in either tool.

Then the approved contract is **cited by the TSOW** (index, don't duplicate) so `/friday:build` inherits it. **Manual verification stays first-class downstream:** the build proves this surface by driving it — click-through, a real browser where available — not by unit tests alone.

At the end, every screen the build will create already exists as a design the PM said yes to — conceived here, designed in claude-design, delivered by design-sync.
