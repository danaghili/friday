---
name: intake
description: run when client work arrives — capture the client's world before discovery begins
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:intake` — offer it before any work: “This is client work — run `/friday:intake` to capture the client's world before discovery begins?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:intake` — for client work, the door that captures the client's world **before** any decision could need it; these answers can't be retrofitted once discovery starts (contract: the approved `/friday:intake` behavior paragraph). Intake is lead-driven: you run the structured capture with the freelancer — `AskUserQuestion` for the structured choices (teammates can't call it, which is why intake spawns none). Any helper you do dispatch emits telemetry via `tools/spawn_telemetry.py`.

### 1. Prepare before you ask

Research the client's industry first — its standard workflow, common tools, regulatory basics — and bring all of it as *hypotheses to correct* ("usually this works like X — is it different for you?"), so interview time goes to what's unique. Everything derivable gets derived; what's left arrives as concrete choices, never a quiz — the client may not know the answers either. (Interview craft, source-grounded: `docs/research/rebuild/client-intake-practice.md`.)

### 2. Open with their world, not the project

A grand tour in their own words ("walk me through a typical booking"); the concrete past over the hypothetical future ("when did that last happen — what did you do?"); their vocabulary captured into a **shared glossary and never translated away**; and where you can, **watch a real task done live** ("show me — share your screen") — the workarounds and tolerated annoyances there are requirements nobody states. Handed a solution ("build me an app"), pivot to what they need to *do*, then walk the short chain of whys to the real problem.

### 3. Map the environment as a system, not a tool list

What connects to what; where each kind of data lives and *which copy is the truth*; how clean it is; the industry rulebook that silently constrains everything. Read their existing documents first, and talk to the people who actually touch the systems, not only the boss. For an existing site (brownfield), the current-state assessment is largely mechanical — the crawl, the ownership picture, the content audit, the redirect map, the locked-out-domain route all live as operational craft in `docs/research/rebuild/client-environment-discovery.md` (§F). Right-size the whole pass to the engagement (the tiers in `docs/research/rebuild/client-intake-practice.md`) — over-scoping a one-person business is its own failure mode.

### 4. The professional half

Complete, before proposals form: **why this project** before what to build; goals and success *in the client's words*; audience, assets, technical needs; **budget as a design input** (you spec to the budget, not the reverse); timeline against the real "why now"; who maintains it after; the **decision-maker** and everyone else who must approve; accounts, access, and **ownership** ("who is the domain registered to?"); what's explicitly **not** included; deliverables bounded with counts and revision rounds; content responsibility with a deadline; and the **change process, agreed before it's ever needed**.

### 5. Set greenfield-or-brownfield as a standing claim

Does this land in an occupied world — an existing site, users, data to preserve or not break? Decide it here and record it once in the project's FRIDAY-CLAIMS block, the fact every downstream expert reads forever. It lives in the claims, not in the brief.

### 6. Emit the intake brief

The output is one intake brief in the intake-brief grammar (contract: `docs/contracts/intake-brief.md`): the **Formal** half for sign-off — goals, scope, exclusions, budget, timeline, approver, plus data-sovereignty, hosting-SLA, payment/IP-exit, and client-tier — separated from the **Informal** half (rapport, working preferences, the glossary; its empty case is a defined line, never a silent blank). **For a brownfield engagement the brief also carries the `## Brownfield` block — the current-state assessment summary, the chosen direction (re-platform like-for-like / re-platform + tools / rebuild), and the keys/ownership picture; greenfield omits it (a defined case the gate does not flag).** Show the PM the full brief and gate it (approve / edit / cancel — amend and re-show until approved; on cancel nothing is written). The brief passes the document gate (guard #9, `python3 "${CLAUDE_PLUGIN_ROOT}/tools/doc_gate.py" --kind intake-brief --file <brief>`) and feeds discovery and the strategist directly, so the client's world arrives before any proposal forms.

### Close

At the end: a signed brief, a map of their world, and their own words for success — every later "the client expected…" has a document to point at. Commit on the PM's word; never push unless they say so.
