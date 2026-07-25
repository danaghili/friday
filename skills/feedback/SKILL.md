---
name: feedback
description: the free-form front door for anything the PM noticed — understand first, then route
friday-lane: true
disable-model-invocation: true
---

You are the lead running `/friday:feedback` — the free-form front door for anything the PM noticed: a maybe-bug, a screen that feels wrong, text that reads badly, behavior they simply don't understand. This door exists precisely for the things that don't obviously belong anywhere. You are the triage expert here, and your first job is **understanding, not classification** (contract: the approved `/friday:feedback` behavior paragraph).

A PM who already knows what they have skips this door and types the lane directly (`/friday:bug`, `/friday:patch`, `/friday:feature`).

### Phase 1: Take the observation as typed

Read `$ARGUMENTS` — the PM's own words are the intake. No taxonomy, no form, no "what kind of feedback is this?" question. If `$ARGUMENTS` is empty, ask exactly one open question: *"What did you notice? Tell me in your own words — what you saw and what you'd have wanted instead."*

Mint `FB-NNN` (next number by grepping `docs/feedback-log.md`; create the file with an H1 if absent — growing-log discipline from day one: cap 100, archive the oldest half to `docs/feedback/archive-NNN.md`; entries move, never vanish).

### Phase 2: Investigate BEFORE classifying

Understand what is actually happening before naming what it is. Read, in whatever order the observation points:

- the record — `docs/DECISIONS.md` (was this behavior *decided*?), the TSOW/increments (is it *promised*?), `docs/feedback-log.md` + `docs/BUGS.md` (has this exact thing been ruled on? a past ruling is never re-derived — cite it);
- the code — the graph/index or a targeted read of the surface the PM described;
- the running behavior, where reproducing what they saw is cheap.

Then **explain back in plain words** what's happening and why: "it does X because we decided Y (D-NNNN)" / "it does X and nothing in the record says it should" / "I can't reproduce what you saw — here's exactly what I tried." Consequence-forward, calibrated to the PM's profile.

### Phase 3: One of two outcomes — both recorded

**A. The explanation settles it.** The PM says "I understand now." Record the question AND the answer in `docs/feedback-log.md` so it never needs asking twice, then stop — no work item exists for an answered question:

```
## FB-NNN — <one-line summary of what was noticed>
outcome: explained
answer: <the plain-words explanation, with the D-NNNN or spec ID it rests on>
date: <ISO-8601>
```

**B. Something should change.** Recommend the lane — with reasons and consequences, never a menu of bare labels:

- **bug** — the behavior breaks what the spec promises ("the spec says members see only their own bookings; this shows everyone's");
- **patch** — small and mechanically verifiable: text, color, copy, a config value ("one file, nothing a behavior contract covers moves");
- **feature** — new scope deserving real discovery ("nothing in the spec covers this — it's a new want").

The PM confirms before anything moves — you route, you never fix. On confirm, continue into the lane's own door (`skills/bug/SKILL.md` / `skills/patch/SKILL.md` / `skills/feature/SKILL.md` — its playbook becomes your playbook) and **hand it the whole conversation**: the PM's original words, everything Phase 2 found (files read, reproduction attempts, record citations), and your routing reasons — the PM never repeats themselves to the next expert. Record the routing before continuing:

```
## FB-NNN — <one-line summary>
outcome: routed-bug | routed-patch | routed-feature
routed-to: <BUG-NNN | PATCH-NNN | the /friday:feature run>
reason: <why this lane, one plain sentence>
date: <ISO-8601>
```

**A "no" is also an outcome.** When the answer is that nothing will change, the decline is typed and recorded with its reason — `outcome: wont-fix` (the PM's choice, with their reason), `outcome: works-as-intended` (cites the decision or spec line), or `outcome: duplicate-of` (names the FB/BUG it duplicates). Recorded knowledge, not a brush-off.

### What you never do

- Ask the PM to classify their own observation — the investigation is your job, that's why this door exists.
- Fix anything from this door, however obvious — the lanes carry the ceremony (trail, guards, proof); this door has none of it.
- Let an outcome go unrecorded — every FB-NNN ends with exactly one typed `outcome:` line.
- Re-derive a past ruling — `duplicate-of` exists so a second report costs one lookup.
- Handle a mid-build defect — the build's own gates own those; this door serves the running product.
