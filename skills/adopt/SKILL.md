---
name: adopt
description: bring a codebase that has never known friday under management, honestly
friday-lane: true
disable-model-invocation: true
---

You are the lead running `/friday:adopt` — bring a codebase that has never known friday under management **honestly**, without inventing a history it doesn't have (contract: the approved `/friday:adopt` behavior paragraph).

### 1. Read the whole codebase FIRST

Before asking anything: build the code graph and extract the real structure (run `/friday:reference` in full — the extractor's IR is exactly as trustworthy on foreign code, it is pure static analysis), and read whatever docs already exist. Adopt is **where the code graph matters most**: for a language friday's own extractor doesn't speak, recommend installing **graphify** (pinned package `graphifyy`, double-y — lookalikes are unaffiliated) *before* the deep read — as a recorded decision (`tools/decisions_append.py`), never silently. **Fail-closed extraction gate:** if a step cannot parse its input (unreadable tree, a zero-module IR on a repo that plainly has code — wrong `--src`), STOP and report; never guess a structure into the record.

### 2. Ask what code can't say — sharpened by the graph

Let the graph point the questions: the most-connected pieces everything flows through, the subsystems it found, the connections that surprised it. Reach the graph through one seam — `tools/graph_query.py` — which prefers graphify when installed and falls back to friday's own IR when not. **Cite EXTRACTED edges as evidence** when you name a load-bearing piece to the PM; `INFERRED` edges are leads to confirm in the interview, never asserted as fact. Ask about what is actually load-bearing, not generically — what this thing *is*, who uses it, what matters most, what is known to be fragile, where it is headed.

### 3. Write the starting record — marked for what it is

- A **reconstructed scope-of-work** at `docs/TECHNICAL_SOW.md`, titled as adopted/reconstructed and carrying `provenance: recovered-from-code` so no checker mistakes an adopted spec's authority for an interrogated one's — it lists what the system verifiably does, the oracle for future increments.
- A settings file (`CLAUDE.md`) describing the stack **as it actually is** — FRIDAY-CLAIMS verified against the real manifests before you write them (`tools/verify_claims.py --all` passes on your own seed) — plus FRIDAY-STATE.
- Reference docs generated from the code as it stands (the `/friday:reference` arc42 set), grounding discipline at its strictest: nearly every "why" is honestly **"Rationale not captured"** — write that, never invent; a "why" you can PROVE from an artifact (a commit message, an existing ADR) may be cited with its source.
- The project's native `.claude/` (committed settings.json + path-scoped `rules/*.md`) per `docs/contracts/claude-scaffold.md` — the contract owns the seeding rules; adopt's local part: every `paths:` glob comes from the **real extracted layout** (the same cite-EXTRACTED-edges discipline as §2), and a pre-existing `.claude/` file that contradicts what seeding would write is a **§5 finding** (adopt is a sanctioned findings-brief producer), never a silent overwrite.

### 4. No invented history — the decision log starts today

The decision log begins at adoption: **entry one is the adoption itself**, with everything the PM told you. Adopt **backdates nothing** — `--back-filled` dating is backfill's tool, not adopt's (a project that was never friday has no friday decisions to recover). Reconstructed structure lives in the recovered-from-code scope and the reference docs, never as fabricated decision entries.

### 5. Alarming finds → the PM, never silently fixed

Anything the read turns up that should worry someone — critical logic with no tests around it, secrets sitting in the repo, dependencies years stale — surfaces as a **finding for the PM's disposition** in the findings-brief grammar (`docs/contracts/findings-brief.md`), graded and dispositioned, never quietly patched.

### Close

From here the project is a **full friday citizen** — every door works, every guard armed — and the adopted record proves it by passing the full guardrail battery. Code that grew up without records now has records that tell the truth about *that*. Growth is `/friday:feature`; the standing deep-clean is `/friday:reconcile`. Commit on the PM's word; never push unless they say so.
