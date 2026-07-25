# friday Codex adapter — the enforcement gate, ported

Quota-exhaustion continuity: when the Anthropic quota is gone, work continues
on Codex CLI with the same "cannot end while the record is verifiably broken"
guarantee. Only the GATE is ported — roles, commands, and hooks stay
Claude-Code-native; the record they maintain is plain files, which is why this
works at all (file-based state was earned for parallel-safety and
auditability; substrate independence fell out for free).

## What ships

- `state_stop_gate.py` — runs `tools/verify_state.py` (the K1–K8 verifier)
  directly on every stop event. **Fail-closed by design** (deliberate
  divergence from the Claude hooks, which fail open by platform fact): a
  missing or crashing verifier blocks. No sentinel precondition — Codex has
  no reliable SubagentStop typing to arm one (the ISSUE-007 lesson applied:
  never trust harness event filtering you haven't verified).
- `codex-hooks.json` — the binding snippet for the Codex hooks config.

## Wiring

Point the Codex stop hook at the gate, e.g. in the Codex hooks config:

```json
{"stop": [{"command": "python3 <plugin-root>/tools/codex-adapter/state_stop_gate.py"}]}
```

(`codex-hooks.json` in this directory carries the same snippet; substitute the
real install path — Codex has no `${CLAUDE_PLUGIN_ROOT}` expansion.)

## What is deliberately NOT ported

Decision-capture hooks (Channel A needs the AskUserQuestion PostToolUse
surface), the ask mirror, session telemetry. On Codex, capture is Channel-B
only (`tools/decisions_append.py` by hand) — the post-build reconciliation
diff still keeps it honest, because that check is substrate-independent too.
