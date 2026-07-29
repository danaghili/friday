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

**Then the context greenfield gets — asked here once, sharpened by the read (D-0109).** The derive-and-confirm set is single-homed at `agents/bootstrap/strategist.md` §2 — run its beats, don't restate them — all four: the **exposure profile** (public-facing / internal / local-only, plus data stakes), **environments**, the **hosting family**, and the **scale envelope** (now / 10x / 100x). Derive each from what the read actually found — a Dockerfile, an nginx config, a tenants table are evidence to propose FROM, never a reason to skip confirming. Plus the question init asks every greenfield project and nobody ever asked this one: **which single event this project could not tolerate** (data loss, a leak, downtime, a wrong charge…) — one concrete scenario, asked once; the security reviewer, red-team, architect and operations read the answer from the record forever and never re-ask it.

### 3. Write the starting record — marked for what it is

- A **reconstructed scope-of-work** at `docs/TECHNICAL_SOW.md`, titled as adopted/reconstructed and carrying `provenance: recovered-from-code` so no checker mistakes an adopted spec's authority for an interrogated one's — it lists what the system verifiably does, the oracle for future increments.
- A settings file (`CLAUDE.md`) describing the stack **as it actually is** — FRIDAY-CLAIMS verified against the real manifests before you write them (`tools/verify_claims.py --all` passes on your own seed) — plus the §2 answers recorded in the SAME fields greenfield seeds (D-0109 parity — the reader roles grep the record, not the transcript): exposure/deployment profile, environments (under the exact heading `## Environments & deployment`), scale profile, and the intolerable-event answer — plus FRIDAY-STATE (target state: § Close).
- Reference docs generated from the code as it stands (the `/friday:reference` arc42 set), grounding discipline at its strictest: nearly every "why" is honestly **"Rationale not captured"** — write that, never invent; a "why" you can PROVE from an artifact (a commit message, an existing ADR) may be cited with its source.
- The project's native `.claude/` (committed settings.json + path-scoped `rules/*.md`) per `docs/contracts/claude-scaffold.md` — the contract owns the seeding rules; adopt's local part: every `paths:` glob comes from the **real extracted layout** (the same cite-EXTRACTED-edges discipline as §2), and a pre-existing `.claude/` file that contradicts what seeding would write is a **§5 finding** (adopt is a sanctioned findings-brief producer), never a silent overwrite.

### 4. No invented history — the decision log starts today

The decision log begins at adoption: **entry one is the adoption itself**, with everything the PM told you. Adopt **backdates nothing** — `--back-filled` dating is backfill's tool, not adopt's (a project that was never friday has no friday decisions to recover). Reconstructed structure lives in the recovered-from-code scope and the reference docs, never as fabricated decision entries.

### 5. Alarming finds → the PM, never silently fixed

Anything the read turns up that should worry someone — critical logic with no tests around it, secrets sitting in the repo, dependencies years stale — surfaces as a **finding for the PM's disposition** in the findings-brief grammar (`docs/contracts/findings-brief.md`), graded and dispositioned, never quietly patched.

### Close — pin the state, then prove it (D-0109)

From here the project is a **full friday citizen** — and that claim is **verified, never narrated** (NF6 was exactly this close asserting "every guard armed" with no mechanical check):

1. **Pin the target FRIDAY-STATE with the PM** — backfill's mapping, reused: delivered and in real use → `closed`, carrying the PROP-028 dirty-bit fields (`last-verified: <today> (adopt)` + `record-status: verified` — the adoption read IS the verification; the annotation names the writer-moment, because the bare-date form is reconcile's stamp, D-0141); work visibly in flight → `build-in-progress`. The vocabulary is closed (contract: `docs/contracts/state-record.md` — which names adopt as a producer); nothing in between is invented.
2. **A `closed` target earns its close artifacts for real — produced at adoption, dated honestly, never invented:**
   - `friday-reviewer` (model: **sonnet** — named, never inherited; telemetry: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-reviewer --phase adopt:close-review`) reviews the codebase against the reconstructed TSOW. **There is no diff at adoption and no review package — the spawn message says so**: its oracle pair is the reconstructed TSOW + the tree itself (the adopt-mode exception `agents/roles/reviewer.md` names), and the verdict is the full FRIDAY-REVIEW envelope at `docs/reviews/post-build-review.md` — the one path the K2 gate honors — stamped as a review performed at adoption.
   - `friday-tester` (model: **sonnet** — named, never inherited; telemetry: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-tester --phase adopt:release-gate`) runs the project's REAL suite/build for `docs/reviews/release-gate.md` (K3) — an adopted thing failing its own tests is a §5 finding, never a reason to soften the gate — **and writes the coverage ledger** (`docs/reviews/coverage.md` FRIDAY-DISPOSITIONS, K7 — the ledger is the tester's artifact, `agents/roles/tester.md`, never the lead's here): one `disposition:` line per reconstructed-TSOW ID, each verified cold in its fresh context — a real read, a real grep — and tagged `(independently-tested)`. An ID it cannot confirm comes back as a finding: the recovered SOW line was wrong — fix the record, never pad the ledger.
   - Both spawn messages carry the `friday-docs: available` stamp (or the plain-Read pointer to `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md`), the explicit Read list, and the agent's compaction drawer path.
3. **The mechanical gate:** `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_state.py" --root . --json` passes — real output quoted, never summarized. A blocking K-rule routes back to the step tagged with it above — the (K2)/(K3)/(K7) tags in this section are the adopt mapping; the tool's own owner labels name roles (it says `closer` even here, where no closer ran). Then the full guardrail battery, as the citizenship proof.
4. **The declined-offer shape:** a PM who does not want the heavier close leaves the record honestly at `substrate-seeded`, with the distance to `closed` recorded as a §5 finding with a named owner — never a thinner `closed`.

**Two doors, never a pipeline (journey audit J8):** adopt is the door for code that has **never known friday**; a project built by an OLDER friday goes through `/friday:backfill`. Old-friday artifacts discovered mid-adopt (a FRIDAY-STATE block, a decision log, journal files) mean you are in the wrong lane — stop and reroute; neither door hands off to the other.

Growth is `/friday:feature`; the standing deep-clean is `/friday:reconcile`. Commit on the PM's word; never push unless they say so.
