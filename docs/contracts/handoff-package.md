# Contract: the client handoff package

The producer/consumer contract for the client-ownership handover package
(TECHNICAL_SOW_REBUILD US-18: FR-83/FR-84/FR-85/FR-86; AC-26). Producer:
`/friday:handoff`. Consumers: the client (a non-technical owner, or the next
developer they hire, reads the package), `tools/handoff_gate.py` (the
completion-gate reader), and the final harden's coverage ledger. Both sides
cite THIS file; neither invents its own shape.

## The package — `docs/handoff/` (client-facing, plain language)

A "start here" summary plus a supporting folder. Required members:

| File | What it holds |
| --- | --- |
| `README.md` | the "start here" summary: what you own, how to run it, what it costs, who to call, and where the rest is |
| `what-it-is-and-why.md` | the system in plain words + the decision log's "why", rewritten for a non-technical owner |
| `user-guide.md` | everyday use, post-login (the guide the owner personally reads) |
| `admin-guide.md` | accounts, permissions, the more technical operations (the guide handed to a hired developer) |
| `operations-runbook.md` | deploy, backups, monitoring, "when X breaks", the maintenance schedule (what / cadence / owner / last-done) |
| `ownership-and-keys.md` | the key/account inventory — one row per item: name, plain-language purpose, owning account, current holder, target owner (NEVER a value) — plus the transfer runbook |
| `running-cost.md` | the plain monthly upkeep figure |
| `honest-state.md` | what's solid, what's known-fragile, what was deferred |
| `promised-and-proven.md` | what was promised (the requirements) and how to re-run the checks/tests to prove it works |
| `warranty.md` | the bug-fix warranty note (default 30-day, in-scope only, operator-adjustable) |

Optional member — present ONLY if the operator chooses to offer ongoing support:

| File | What it holds |
| --- | --- |
| `stay-on-proposal.md` | a clearly-separated managed-service offer — a plain monthly figure, never bundled into the summary |

## Invariants

1. **Names and purposes, never values (FR-84; D-0056/D-0057)** — *tool-enforced.*
   `ownership-and-keys.md` inventories each item by NAME (enumerated by
   `tools/secret_names.py`) with its plain-language purpose, owning account, current
   holder, and target owner — never a value. friday has no code path that reads a
   value; the actual value transfer is an operator step inside their own secrets
   manager (Infisical the reference adapter). The package and the journal carry zero
   secret values.
2. **who-can-do-this tag + required members (FR-83)** — *tool-enforced.* Every
   operate-or-maintain line in `operations-runbook.md` — bullet, numbered step, or
   table row (tag in the first cell) — opens with `[you]` (owner self-serve) or
   `[hired]` (needs a hired hand), and every required member above is present;
   `tools/handoff_package_check.py` flags any untagged line or missing member
   (code fences and table header/separator rows are structure, not operate lines).
3. **Plain language (NFR-1)** — *review + AC-26 field test.* Every page is plain English a
   stranger can act on; not mechanically checkable, so enforced by house review and the AC-26
   handover field test, not a script.

## Completion gates (FR-85) — the record, not the package

handoff refuses to report done until all four gates are confirmed, read by
`tools/handoff_gate.py` from `handoff-attest` journal events (gates: `reconcile`
· `keys` · `restore` · `receiver`). Attestations are written ONLY through
`tools/handoff_attest.py` (the single substrate writer) — the PM confirms each;
friday records who and when, never the secret behind a transfer. The empty case
(no attestations) is "all four outstanding".

## Reconcile-first (FR-86; D-0058)

Before compiling anything, handoff runs the deterministic record-drift verifiers
only (`verify_state` / `verify_claims` / `verify_coverage` / generated freshness)
and, on drift, STOPS and OFFERS `/friday:reconcile` — it never reconciles inline
and never proceeds on drift.

## Verification

- Package invariants (required members + who-can-do-this tags): `python3 tools/handoff_package_check.py --root . --json` — exit 0 ok/not-built · 1 findings · 2 bad invocation.
- Completion gates: `python3 tools/handoff_gate.py --root . --json` — exit 0 all four confirmed · 1 outstanding · 2 bad invocation. Attestations are written ONLY via `python3 tools/handoff_attest.py --gate <reconcile|keys|restore|receiver> --status confirmed --by pm`.
- Secret NAMES: `python3 tools/secret_names.py --root . --json` — names only, never a value.

Tests: `tests/test_handoff_package_check.py`, `tests/test_handoff_gate.py`, `tests/test_secret_names.py`.
