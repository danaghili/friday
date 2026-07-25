# ADR-003 — friday is structurally incapable of handling secret VALUES (names only, via a secrets manager)

**Context.** `/friday:handoff` assembles the client-ownership package, which
must account for every credential the running system needs (API keys, tokens,
2FA seeds, private keys). The instinctive design collects those values so the
package is complete, or — one step back — scans the assembled files for
secret-shaped strings to catch a leak. Both put secret material inside a path
an agent can read or that lands in chat, logs, or a friday-produced file.

**Decision.** No secret VALUE ever passes through friday. friday's key handling
is metadata-only: it enumerates the required secret **NAMES** from the
application's own declarations (`.env.example`, config schema,
`process.env`/`os.environ` references) via pure stdlib text parsing
(`tools/secret_names.py`), and emits an ownership inventory (each item by name,
purpose, location, owning account, current holder, target owner) plus a
transfer runbook the operator runs **externally**. Actual values live in and
move through the operator's own secrets manager (Infisical is the reference
adapter, never a friday runtime dependency — the client creates and owns their
own vault). friday's tooling has **no code path that returns a secret value** —
no `getSecretValue`, no value-returning CLI call. The 'keys verified'
completion gate is satisfied by the operator's out-of-band attestation, which
`tools/handoff_attest.py` records — and that tool refuses a secret-shaped
`--note`, so an attestation can never smuggle a value into the journal.

**Alternatives rejected.** Collecting/storing/relaying the actual credentials
while assembling the package — routes secrets through an agent-readable path,
the exact exposure being ruled out. **Scanning the assembled package for
secret-shaped strings** — backwards: a file-scan presupposes a value already
reached a file friday handled, which is itself the violation; the boundary must
be structural, not detective. Calling the secrets manager's value API to build
the inventory — hands the agent the values, same violation. Baking a specific
secrets manager into friday-core — violates the stdlib-only non-goal and locks
out non-Infisical users, so the manager stays a pluggable operator workflow.

**Consequences.** Leakage is impossible-by-construction rather than
caught-after-the-fact. The names friday enumerates are not secret (they live in
`.env.example`/code by convention). The transfer is a human, external step;
friday tells the operator exactly what to move and confirms it was moved,
without ever touching a value. Any future friday code path that reads a secret
value is a security regression by definition.

`[Sources: DECISIONS.md D-0056, D-0057; TSOW FR-84; [[secrets-never-through-agent]]]`
