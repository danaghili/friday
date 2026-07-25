# The adversarial finding engine — harden's scaled fan-out (craft, salvaged)

consumer: commands/harden.md — cited by the harden find-pass for the scaled fan-out

_Field-validated craft for hardening's find pass. Salvaged (D-0041) from the
pre-rebuild security/redteam commands so the lean doors can cite it instead of
carrying it. Owner: `/friday:harden` — the reviewers (`friday-security-reviewer`,
`friday-redteam-reviewer`) DESIGN and INTERPRET under their read-only S-3 grant;
harden fans them out and runs experiments._

## When to reach for it

The single sandboxed reviewer is the right default **well past "large"** — one
opus reviewer produced a deep, fully-evidenced 20-finding report on a ~40-feature
system with no lens-starvation. Do NOT parallelize on feature-count alone. Reach
for the engine only when a genuinely huge system, or a prior single run that
visibly thinned on some lenses, justifies it — and it is real spend (~25–30 short
agents): **recommend-and-ask, never silent-auto-run.** No `Workflow` tool, or the
PM declines → the single-teammate default, unchanged.

## The shape that works

**Parallel finders for raw coverage + ONE synthesis pass whose load-bearing job
is cross-lens chaining** — NOT one agent per lens cluster. The highest-value
findings are chains *across* lenses (an observability gap is the multiplier on
every failure/recovery finding; a destructive-action risk spans abuse +
reversibility). Splitting blind agents by lens severs exactly those chains. So:
finders gather breadth, then a single mind that has seen everything hunts the
chains and writes the conforming report. **The workflow feeds the role; it never
replaces it** — the reviewer stays the synthesis mind and owns the artifact, and
the PM triage gate fires unchanged. Every candidate is adversarially
refute-verified by 3 independent skeptics and survives only on 2-of-3
not-refuted.

Lens rosters live in the reviewer contracts (redteam: three adversaries;
security: four lanes + business-logic + L6). The engine decomposes each grouping into finer
finder-lenses — redteam's three adversaries into the seven below, security's
four lanes into eight — so every finder stays narrow; the reviewer re-groups
them back to the contract in synthesis. Redteam's canonical seven-lens shape:

```js
export const meta = {
  name: 'redteam-finding-engine',
  description: 'Parallel lens finders + 3-skeptic adversarial refute-verification; survivors feed the redteam-reviewer',
  phases: [
    { title: 'Find', detail: 'one cold finder per lens, structured findings with evidence' },
    { title: 'Verify', detail: '3 independent skeptics per finding; survives on 2-of-3 not-refuted' },
  ],
}

const CONTEXT = `Build a model of the system READ-ONLY from the sanitized mirror:
docs/architecture/README.md + decisions/, docs/DECISIONS.md (model-autonomous entries first — S-2),
docs/architecture/generated/*.md, docs/ops/* if present. Reasoning-mode: no running the system. {scope hint}`

const LENSES = [
  { key: 'abuse',         focus: 'abuse cases — attack-chaining, privilege escalation, exfiltration' },
  { key: 'failure',       focus: 'failure injection (reasoned) — slow/down deps, races, stale cache, partial writes' },
  { key: 'postmortem',    focus: 'postmortem simulation — write the outage postmortem before it happens' },
  { key: 'scale',         focus: 'scalability stress — at 100x, what breaks first' },
  { key: 'regret',        focus: 'design regret — which architecture decisions hurt in 6-12 months' },
  { key: 'observability', focus: 'observability gaps — when it breaks, will we know, can we diagnose' },
  { key: 'recovery',      focus: 'recovery / reversibility — can each risky operation be undone' },
]

const FINDINGS = { type: 'object', required: ['findings'], properties: { findings: {
  type: 'array', items: { type: 'object', required: ['title', 'severity', 'evidence'],
    properties: {
      title:    { type: 'string' },
      severity: { type: 'string', description: 'act-now|before-growth|track|informational, context-calibrated' },
      evidence: { type: 'string', description: 'file:line / endpoint / flow — concrete and system-specific, or it does not count' },
      route:    { type: 'string', description: 'recommended destination: candidate requirement / [ACTION] / BUGS.md / ADR' },
    } } } } }

const VERDICT = { type: 'object', required: ['refuted', 'reason'], properties: {
  refuted: { type: 'boolean', description: 'true unless the evidence genuinely holds against your refutation attempt' },
  reason:  { type: 'string' } } }

const verified = await pipeline(
  LENSES,
  l => agent(`${CONTEXT}\nFind concrete robustness findings through ONE lens only — ${l.focus}.`,
             { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS }),
  (r, l) => parallel((r?.findings ?? []).map(f => () =>
    parallel([1, 2, 3].map(i => () =>
      agent(`${CONTEXT}\nAdversarially REFUTE this finding. Default refuted=true if the evidence does not hold:\n${JSON.stringify(f)}`,
            { label: `verify:${l.key}:${i}`, phase: 'Verify', schema: VERDICT })))
      .then(vs => ({ ...f, lens: l.key,
                     survives: vs.filter(Boolean).filter(v => !v.refuted).length >= 2 }))))
)
return { findings: verified.flat().filter(Boolean).filter(f => f.survives) }
```

Refute-killed candidates are gone — never resurrect them into the reviewer's
feedstock. On workflow error or interrupt, fall back to the single-teammate
default and say so.

## The security variant

Same engine, security's lens roster (auth-session, authz-idor, client-trust,
payments, injection, pii-exposure, llm-surface, business-logic — see
`agents/roles/security-reviewer.md`). Security L1 scans and L6 ops-readiness stay
with the role — scans are deterministic tool-runs harden pre-runs as a pipeline
step, and L6 findings route to `friday-operations` to own — neither benefits from
parallel finders. Only L3 (file-level review of security-critical code) fans out.
Severity calibration, the findings-brief grammar, and PM triage are unchanged.
