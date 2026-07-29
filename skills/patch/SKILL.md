---
name: patch
description: run when the PM asks for a genuinely small change — text, copy, a config value, a pin
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:patch` — offer it before any work: “That's a genuinely small change — run `/friday:patch` to land it with a light trail?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:patch` — a genuinely small change: text, a color, copy, a config value, a dependency pin. One tap of confirmation is the whole ceremony, and the trail still exists (contract: the approved `/friday:patch` behavior paragraph). If routed from `/friday:feedback`, the conversation arrived with it — consume it.

### 1. Restate the change with its EXACT blast radius — the PM's one confirm is the gate

Say back, concretely: "this touches these two files and changes what the renewal email says; nothing else moves." Name the files and the behavior that changes, and what does NOT. Then arm the lane with that declared radius:

```
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lane.py" open --lane patch --id PATCH-NNN \
  --trail docs/trails/PATCH-NNN.md \
  --blast-radius <path-or-glob> [--blast-radius <path-or-glob> ...]
```

This writes the `.friday/lane-open` sentinel (contract: `docs/contracts/lane-open.md`). From now, guard #12 blocks any edit outside the declared radius at action time, with a Stop-time backstop warning (guard #12b) — the declaration makes an out-of-radius change provable, not deniable. Mint `PATCH-NNN` from `docs/PATCHES.md` (create with an H1 if absent; growing-log discipline: cap 100, archive the oldest half to `docs/patches/archive-NNN.md`). **Get the PM's single confirm before making the change.**

### 2. Make the change, prove it landed

Make exactly the declared change. Prove it: the build still passes, the affected surface is checked, real output quoted — an executable, fail-loud check, never prose self-report.

### 3. The full trail in miniature

Write `docs/trails/PATCH-NNN.md` in the change-trail grammar (`docs/contracts/change-trail.md`): what was asked, any judgment made along the way (D-NNNN pointers, or the explicit `decisions: none` line), proof with the quoted output — plus its one changelog line. *"Too small to record" does not exist.* If docs or the code graph describe what changed, they refresh (re-run `/friday:reference` Phase 1 when a generated file's source moved).

### 4. If it isn't small after all — stop and re-route

The moment the "text tweak" turns out to feed the entitlement check — or touch a behavior contract, or anything a TSOW ID covers — **stop**. Clear the patch lane (`python3 "${CLAUDE_PLUGIN_ROOT}/tools/lane.py" clear --by lead` — your own honest re-route, recorded as exactly that, never a PM escalation) and route honestly to `/friday:bug` (it's broken) or `/friday:feature` (it's new scope). A patch never quietly grows into a slice.

### Close

The lane's guards disarm on a passing close (the trail present and valid); a blocked close names what's missing. Then flip the record dirty — the change landed on a project whose record still claims it was verified: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/state_record.py" --mark stale --root .` (quiet no-op unless the project is closed; `last-verified:` untouched by design, and only a clean `/friday:reconcile` clears it — D-0106, contract: `docs/contracts/state-record.md`). Commit on the PM's word; never push unless they say so.
