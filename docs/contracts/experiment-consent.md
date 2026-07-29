# Contract: the experiment consent record

The producer/consumer contract for the PM's yes to one experiment batch
(INC-201 FR-201.3 / FR-201.5 / FR-201.6; AC-201.4 / AC-201.5 / AC-201.6 /
AC-201.7; S-201.3; D4 / D5 / D8). **Producer:** the lead, at the moment the PM
says yes — harden's Step 3 (`skills/harden/SKILL.md`), through
`tools/friday_consent.py` (`consent_write`), which owns this record end to end and
reaches `tools/friday_substrate.py` for the shared primitives (worktree-shared
root, the journal, time) — the same shape `tools/decisions.py` and
`tools/standards_deviations.py` use for theirs. **Consumers:**
the `friday-experiments` server (`tools/experiments/server.py`), which reads and
spends it, and `agents/roles/experiment-runner.md`, which names the batch and
holds nothing else. Both sides cite THIS file; neither invents its own shape.

Sibling contract: `docs/contracts/experiment-request.md` — the request document
this record approves. Neither is complete without the other.

## Why this record exists at all

Before it, the runner typed its own batch id and the executor compared that
against the batch id written inside the request document. Both are things the
runner could read — and, while it held a shell, **write**. So the check proved
the runner was being *consistent with itself*. It never proved the PM had said
anything.

That is not a hypothetical gap. With a shell the runner could author the entire
request: its own target, its own `target-class: non-production`, its own
`consent: pm-yes <batch>`, its own worktree. Every clause in the request
contract's enforcement table would then pass honestly, because the document
every clause is read from was written by the thing being constrained.

This record is the half that could not exist until the shell was gone. **A
record the runner cannot forge is a new thing in the world**, and it is only new
because `agents/roles/experiment-runner.md` now holds no `Bash` and no `Write`.

## The shape

One file per batch, at `<shared .friday>/consent/<batch-id>.md`, carrying a
single typed block in the house grammar (`tools/taglines.py`):

```
<!-- FRIDAY-CONSENT:BEGIN -->
batch: batch-7
request: /abs/path/to/docs/reviews/experiments/batch-7.md
fingerprint: sha256:<64 hex>
granted: 2026-07-29T09:14:02Z
spent: no
<!-- FRIDAY-CONSENT:END -->
```

| Field | Meaning |
| --- | --- |
| `batch` | the batch id the PM approved; matches the request's `consent: pm-yes <id>` |
| `request` | the request document this yes is attached to |
| `fingerprint` | `sha256:` over that document's **exact bytes** at the moment of the yes |
| `granted` | when the yes was given |
| `spent` | `no`, or the timestamp of the run that consumed it |

## The clauses, and what enforces each

| Clause | Enforced by | Tested by |
| --- | --- | --- |
| Only the lead writes it | `friday_consent.consent_write` (the record's only writer); the runner holds no `Write` and no shell | `test_the_record_lands_under_the_friday_substrate` |
| It lives where the runner cannot reach | path under the shared `.friday/` substrate | same |
| One batch, one approval | `O_EXCL` claim — a second write refuses | `test_a_second_yes_for_the_same_batch_is_refused` |
| The yes is bound to what the PM READ | `fingerprint` over raw bytes; `consent_matches()` | `test_the_fingerprint_follows_the_bytes_the_pm_read` |
| One yes, one run | `consent_spend()` refuses a spent record | `test_a_spent_approval_cannot_be_spent_again` |
| No approval is never an implicit yes | `consent_read()` returns `None`; fail-closed reads it | `test_no_record_is_a_distinct_valid_outcome` |
| A batch id cannot escape the substrate | shape check `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` | `test_a_batch_id_that_would_escape_the_substrate_is_refused` |

All in `tests/test_inc201_consent_record.py`.

**The id is checked by shape, never by denylist.** The batch id reaches a
filename here and again where the run record's path is derived (FR-201.7). A
separator or `..` would escape `.friday/` — handing back a write primitive at
the exact moment this increment removes one. So what is *legal* is enumerated,
rather than what is dangerous: a denylist is a list of the attacks somebody
already thought of (S-200.1's rejected shape, the same reasoning as the request
grammar's).

**The fingerprint is over bytes, not parsed content.** Re-parsing would forgive
exactly the invisible drift D-0131 refused. That entry made the request a human
reads the request that runs *at parse time*; this holds the same property
**across time**.

## Two places carry the batch id, and they must agree (D8)

The batch id lives here and inside the request document. That duplication is
deliberate: removing it from the request would take the batch name out of the
only document the PM actually reads when approving, which works against the
fingerprint above.

*Accepted cost, recorded rather than glossed (the KH-4 discipline):* two places
that must agree can drift apart. Here the drift is at least **caught** — this
record is the authority and the door refuses when they differ — which is better
than the usual shape of this problem, where drift is silent.

## What this record does NOT do

- **It does not authenticate its reader.** The `friday-experiments` server
  cannot tell the runner from the lead and does not try (S-201.1). Containment
  is that the runner holds *only* those tools, on the un-named spawn path. Any
  reader who assumes the door checks identity is reading it wrong.
- **It does not survive into project history.** `.friday/` is git-ignored, so
  this is working state. The durable trail rides the run record instead, which
  names its batch and states that the approval was found and matched (D7) — and
  that is sound **only because friday derives the run record's path** (D6). If
  D6 is ever revisited alone, this clause rots with it.
- **It does not make hostile target output safe.** Unchanged by this increment;
  `agents/roles/experiment-runner.md`'s data-never-instruction rule (D-0127)
  stands exactly as written.
