# Contract: decision capture (DECISIONS.md)

The single producer/consumer contract for the decision log. Producers:
`tools/decisions_append.py` (BOTH channels — A.6 single-writer invariant),
`hooks/decision_capture.py` (Channel A). Consumers: `tools/decisions.py`
parser, K6, `tools/capture_integrity.py`, `/friday:reference` synthesis
grounding, the registry index, the hardening pass (S-2). Both sides cite THIS
file; neither invents its own shape (ISSUE-001/002/005/008 class).

## Serialization (D-0004)

- Pinned H1: `# Decisions — <project>`.
- One entry: `## D-NNNN — <title>` + one meta line of ` · `-joined typed pairs
  `**When:** <ISO-8601Z>` · `**Channel:** pm-ratified|model-autonomous` ·
  `**Weight:** one-way|two-way` · `**Floor:** none|schema-data|auth-security|external-api|friday-claims|spend`
  [` · **Back-filled:** true`] + three mandatory bullets
  `- **Decision:**` / `- **Why:**` / `- **Rejected:**`.
- **Empty form (A.2, byte-exact):** the H1 + marker comment + the single line
  `_No decisions captured yet._` — never a zero-byte file, a missing file, or
  a bare heading. The first append REPLACES the sentinel; sentinel+entries
  coexisting is malformed.
- IDs are monotonic, allocated under an advisory lock against
  `<shared .friday>/decisions.counter` (Appendix B: worktree writers share the
  counter; entries land in the CHECKOUT's file).
- Growing-log discipline (PROP-023): cap 100; overflow MOVES the oldest half
  to `docs/decisions/archive-NNN.md`, ids preserved, schema-valid.

## The surfacing gate

Three-part worthiness test (hard-to-reverse ∘ surprising-without-context ∘
genuine trade-off between real alternatives), COMPOSED with the PROP-044
five-category floor as a categorical override: a floor-touching decision is
surfaced + `one-way` regardless of the three-part conclusion (the writer
enforces floor⇒one-way mechanically). Verification findings that revise a
decision fire capture like any other entry.

## The decision-ask shape (Channel A trigger — and ONLY it)

An `AskUserQuestion` whose first question's text is:

```
[FRIDAY-DECISION] <title>
decision: <what is being decided>
why: <rationale for the recommendation>
rejected: <alternatives and why not>
floor: none|<category>
weight: one-way|two-way
```

with the real alternatives as options. `hooks/decision_capture.py` fires the
append for exactly this shape — ordinary permission dialogs and clarifying
questions never parse, so the log carries no permission-grant noise. The
harness guarantees the write; the model's judgment picks the shape.

## Channel B honesty (cannot be harness-guaranteed)

Enforced by reconciliation, not the harness: the extractor-vs-synthesis diff
surfaces "uncaptured why" gaps (a silent omission becomes a visible finding);
`capture_integrity.py` flags end-clustered timestamps (back-filled entries
exempt via the tag); the `model-autonomous` marker routes hardening scrutiny
first (S-2).
