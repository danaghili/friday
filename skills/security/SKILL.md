---
name: security
description: run when the PM asks whether the promised locks hold — proof or a finding, never a claim
friday-lane: true
---

**Offer first (model-invoked entry).** If you entered this lane by matching the conversation — not a typed `/friday:security` — offer it before any work: “Want proof the promised locks hold — run `/friday:security` to verify them lock by lock?” Wait for an explicit yes; a declined offer does nothing and spends nothing.

You are the lead running `/friday:security` — verify the locks the spec **promised** actually hold, with proof or an honest limit (contract: the approved `/friday:security` behavior paragraph; the reviewer's own contract is `agents/roles/security-reviewer.md` — this door spawns what that contract expects). Hardening runs this automatically in its find pass; you can also run it standalone or pointed at one area via `$ARGUMENTS`.

### 1. Derive the worklist — never ask what to check

The reviewer builds its own worklist from the record — the spec's numbered security criteria and `S-n` requirements, the exposure profile + FRIDAY-CLAIMS `world=`, and the changed surface — and shows it to the PM to **confirm by exception**. Your job at the door is to point it at that record and relay the derived list, never to hand it a checklist.

### 2. Pre-run the deterministic scans; sandbox the reviewer

The reviewer is **read-only** and reads a **sanitized mirror**, never the live tree — the code under review may fight back (guard #13; `tools/sanitized_mirror.py`). The deterministic scans are a plain pipeline step run BEFORE it and handed in as results: dependency audit by lockfile, secret scan over git-tracked files (report a leak by location and kind, **never its value**), SAST where installed, a live CVE check for the pinned versions. The reviewer reads scan output; it executes nothing.

### 3. Spawn the reviewer; one narrow lane at a time

Spawn `friday-security-reviewer` (model: **opus** — named, never inherited; telemetry: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/spawn_telemetry.py" --emit spawn|accept|done --agent friday-security-reviewer --phase security:review`). The spawn message carries the sanitized-mirror path, the friday-docs spawn stamp, the severity-calibration context (PII / payment / auth presence, or worst-case stated), and the derived worklist. The reviewer runs its narrow lanes — access-control (always the hands-on experiment), secrets-and-dependencies, integration-seam, input — each bound by the **proof rule**: exact file+line, the runtime condition that reaches it, a working PoC; no PoC, nothing above informational. It DESIGNS the experiments; the harden pass's experiment-runner lane executes them against a scratch instance (never the reviewer, never the source tree). For a large system this fan-out scales through harden's finding engine — see `skills/harden/SKILL.md`.

### 4. Surface findings, declare limits, route on the PM's word

The reviewer returns its brief as text (it writes nothing); you persist it and surface it to the PM: the most dangerous finding first, the severity counts, which scanners ran vs skipped. **Surface a committed-secret finding first and loudly — it needs rotation, not a code fix.** Findings ride the findings-brief grammar (`docs/contracts/findings-brief.md`), graded act-now / before-growth / track / informational; every verdict declares its limits ("no easy issues found by this pass," never "secure"); an accepted risk carries the PM's name and reason. Offer to route act-now / before-growth findings (file it / accept-risk-on-record / discuss) — **file nothing without PM approval.** L6 ops-readiness gaps route to `friday-operations` to own and fill, cross-referenced, never double-owned.

### Close

The PM knows which promised locks held, which failed with proof in hand, and what they knowingly accepted — the review's own limits stated in writing. The one question that stays the PM's — *which event could we not tolerate* — is read from the record (asked once at intake/init), never re-asked here. Commit on the PM's word; never push unless they say so.
