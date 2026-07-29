---
name: handoff
description: run when a client-ownership handover package is due — written for a non-technical owner
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:handoff` — offer it before any work: “Sounds like ownership is changing hands — run `/friday:handoff` to assemble the non-technical owner's package?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:handoff` — the client-ownership handover package: the plain-language set a non-technical owner receives at the end of a project so they can run, understand, budget for, and prove their product, then take it to any other developer and leave with confidence (contract: the approved `/friday:handoff` behavior paragraph; `docs/contracts/handoff-package.md`). This is the **client's** package — distinct from `/friday:reference` (friday-internal arc42), `/friday:backfill` (friday's own records), and the internal build-model `seam_handoff.py` (a between-units engineering primitive, not a client artifact). Its bar is the highest in friday: a stranger who never met this project can act on every page.

### 1. Reconcile-first — the deterministic drift gate (D-0058)

Handing a client a record that lies about itself defeats the point. Before compiling anything, run ONLY the mechanical record-vs-reality drift verifiers — never the full reconcile battery — quoting real output:

- `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_state.py" --root . --json`
- `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_claims.py" --root . --all --json`
- `python3 "${CLAUDE_PLUGIN_ROOT}/tools/verify_coverage.py" --root . --json`
- generated-doc freshness: re-run the extractor + `synthesis_diff` (the `/friday:reference` Phase 3 oracle) — a diff means the code moved after the docs.

**Clean → proceed.** **Any drift → STOP and OFFER `/friday:reconcile`** — present exactly what drifted in plain words and let the PM run the deep-clean deliberately. Never reconcile inline; never proceed on drift. (The heavier "does a backup *actually* restore" re-proof is not done here — that is the operations consult in §2 and the restore gate in §5.)

### 2. Gather the record + consult the experts

The package is assembled from records and experts friday already has — never invented. Read: the intake brief (`docs/contracts/intake-brief.md` — the ownership/keys and client-tier source), the reference set (`docs/architecture/` arc42), `docs/DECISIONS.md` (the "why", to be rewritten client-plain), and the requirement-coverage ledger (the "promised and proven" list). Spawn the two operations experts (models named; telemetry via `spawn_telemetry.py`; each spawn message carries the `friday-docs: available` stamp — or a plain-Read pointer to `${CLAUDE_PLUGIN_ROOT}/docs/teammate-contract.md` — and the explicit Read list):

- **`friday-operations`** (model: **sonnet**, `--phase handoff:ops`): a **short, practical runbook — "when X breaks, do Y", never a fat incident manual** — deploy, backups with a **demonstrated restore** (the evidence the restore gate needs), monitoring that is actually watching, and the maintenance schedule (what / cadence / owner / last-done).
- **`friday-running-cost`** (model: **sonnet**, `--phase handoff:cost`): the plain monthly figure for keeping it running — **grounded in `docs/ops/cost-projection.md`** where one exists (written at stack confirmation, INC-200; cited by name so the owner's figure traces to what was projected before the money was committed, and any drift from it is stated rather than silently replaced). No projection on disk means the figure is derived here from scratch and says so.

### 3. Build the ownership inventory — names and purposes, never a value (D-0056/D-0057)

friday is structurally incapable of handling a secret value. Enumerate the NAMES the app declares:

`python3 "${CLAUDE_PLUGIN_ROOT}/tools/secret_names.py" --root . --json` — reads example dotenv files and source references; it never opens a real `.env`. Then build `ownership-and-keys.md` as an inventory the owner can act on — one row per item: the **name**, its **plain-language purpose** (what stops working without it), the **owning account**, the **current holder**, and **whose name it should end up under** — drawn from those names, the intake brief's key-ownership rows, and the PM's answers (ask; never guess). A config-only variable (a path, a port) is marked "not a secret — just a setting." Close the file with the **transfer runbook the PM runs inside their own secrets manager** (Infisical the reference adapter), where the values live and move to the client's vault. The one thing that never appears is a value: no value enters the package or the chat — the tool cannot read one, and neither do you.

### 4. Compile the client package (the plain-language narrative)

Write `docs/handoff/` (shape: `docs/contracts/handoff-package.md`): the "start here" `README.md` summary + the supporting members. Deterministic where it can be (the inventory, the maintenance table), model-synthesized for the plain-language guides. Bars:

- **Plain language:** every page is plain English a stranger can act on.
- **Right-sized (client-tier):** read the intake brief's `client-tier` row and scale the package's depth to it — a sole trader gets the lean runbook and guides; a larger client the fuller detail. Over-scoping a one-person business is its own failure.
- **Two guides, kept separate:** the everyday **user guide** (post-login, what the owner personally reads) and the more technical **admin guide** (accounts, permissions, what they hand a hired developer) — one file each, never merged; both grounded in the reference set and the real screens.
- **who-can-do-this tag:** every operate/maintain line in the runbook — bullet, numbered step, or table row — opens `[you]` (owner self-serve) or `[hired]` (needs a hired hand) — no untagged line.
- **Warranty (D-0055):** `warranty.md` pre-filled with the 30-day, in-scope-only industry norm — covering only what was already in scope, not new requests — which the PM can change or waive.
- **Honest state:** name what's solid, what's known-fragile, what was deferred — candour, not polish.
- **Promised & proven:** `promised-and-proven.md` lists what was promised (the requirements) and how the client re-runs the checks/tests to prove it works — from the coverage ledger read in §2.
- **Optional stay-on (D-0053):** include `stay-on-proposal.md` ONLY if the PM chooses to offer ongoing support — a plain monthly figure, clearly separate, never bundled into the summary.

Then verify the package mechanically, real output quoted: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/handoff_package_check.py" --root . --json` — every required member present, every runbook line tagged `[you]`/`[hired]`; fix any finding before the gates.

### 5. The four completion gates

handoff refuses to report done until all four are confirmed. Walk the PM through each with a question card (`AskUserQuestion`) — confirm or defer; record each confirmation ONLY through the single writer, then check:

- Record each: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/handoff_attest.py" --gate <reconcile|keys|restore|receiver> --status confirmed --by pm [--note "..."]`.
- Check, real output quoted — never assert a gate the tool didn't confirm: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/handoff_gate.py" --root . --json` — exit 0 = all four confirmed; exit 1 = the outstanding list, surfaced in plain words.

The gates: **reconcile** (§1 clean, or `/friday:reconcile` run); **keys** (the PM attests every account/key moved into the client's name inside their secrets manager, builder access + recovery removed — friday never sees the values); **restore** (a successful test restore evidenced, from §2's operations consult); **receiver** (a named client-side person has acknowledged the package). Never report done with any gate outstanding; show exactly what remains.

### Close

At the end: the client holds a package they can run, understand, budget for, prove, and carry to any other developer — and the four gates are confirmed on the record. Commit on the PM's word; never push unless they say so.
