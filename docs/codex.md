# Codex portability

friday's spine — the CLAUDE.md record (FRIDAY-CLAIMS + FRIDAY-STATE), the
verify scripts, DECISIONS.md, and the friday-docs server — is substrate-
agnostic: it is all files plus stdlib Python. friday earned file-based state
for parallel-safety and auditability; substrate independence fell out for
free. That is what makes quota-exhaustion continuity real: when the Anthropic
quota is exhausted, work continues on Codex CLI against the same record.

What is ported (and only this): the **enforcement gate** —
`tools/codex-adapter/state_stop_gate.py` gives Codex sessions the same
"cannot end while the record is verifiably broken" guarantee, re-verifying
the K-rules directly on every stop. Two deliberate divergences, both
substrate-driven: no sentinel precondition (Codex has no trustworthy
subagent-stop typing to arm one), and **fail-closed** (a missing/crashing
verifier blocks — Claude's hook runner fails open by platform fact; Codex
lets us do better). Wiring and non-goals: `tools/codex-adapter/README.md`.

Capture on Codex is Channel-B only (`tools/decisions_append.py` by hand); the
post-build reconciliation diff keeps it honest there too, because the diff is
substrate-independent as well.
