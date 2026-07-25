# Introduction and goals

friday is a Claude Code plugin for PM-gated software delivery. vnext keeps
v0.4.0's outcomes — documentation, maintainability, sustainable
infrastructure — and engineers out the per-unit ceremony cost that bought
them (the PM's named design goal, TSOW §1).

## Quality goals (ranked)

1. **Loop fidelity** — the discovery→build→synthesis loop works end-to-end;
   decision-capture and doc-synthesis fidelity are its load-bearing parts
   (TSOW §2: make-or-break, built first, verified to destruction).
2. **Honesty by mechanism** — untrusted self-report; every mechanical claim
   independently re-derivable (verifiers + receipts + the synthesis diff);
   asymmetric tolerance: a false block is worse than a miss.
3. **Efficiency** — build-time and token spend must beat the v0.4.0 ceremony
   baseline (NFR-2, a gating DoD leg; usage telemetry exists to measure it).

## Stakeholders

The PM (one approval gate up front, JIT decision-asks, walk-away autonomy);
the build agent (one continuous context); the hardening roster (independent,
post-build); future maintainers (synthesized, liveness-stamped docs).
`[Grounding: docs/TECHNICAL_SOW.md §1-§2; docs/DECISIONS.md D-0001]`
