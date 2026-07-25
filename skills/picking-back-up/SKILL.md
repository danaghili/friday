---
name: picking-back-up
description: Use this when the PM signals a session was interrupted and wants to continue a friday-managed project but has not typed the command — "we got cut off", "where were we?", "did we lose that?", "picking up where we left off", "my session died", "did that finish?". Crash-shaped re-entry. Offers /friday:resume and never runs it without an explicit yes.
---

# Picking back up — recognise the interruption, offer the door

> **Iron law: OFFER, NEVER ENTER. Nothing runs, and no half-done work is touched, without the PM's explicit yes.**
> Silently "continuing where we left off" — re-doing or finishing work — violates this law's spirit as much as running resume uninvited.

## Anti-scope — what this skill is NOT

This skill does **not** reconstruct state, re-run checks, finish half-done work, or re-surface a stalled question. That verification-before-belief work is exactly what `/friday:resume` does. This skill only recognises crash-shaped re-entry and offers that door. If the PM typed `/friday:resume` themselves, this skill is irrelevant — **typed commands are canonical.**

## Triggers (counted, not vibes)

Fires on crash-shaped phrasing — at least one of these five shapes:

1. "we got cut off" / "we lost connection"
2. "where were we?" / "where did we leave off?"
3. "did we lose that?" / "did that finish?"
4. "picking up where we left off"
5. "my session / laptop / connection died"

Deliberately ambiguous phrasing ("what's next?", "let's keep going") when no interruption is evident → **offer OR stay silent, never a silent entry.** A forward-looking question is not automatically a crash.

## The move (scripted)

Say, in this shape: **"Sounds like a session got interrupted — want me to run /friday:resume? It checks what actually finished before trusting where things claim to stand."** Then **wait.**

## Quick reference

| Phase | Key activity | Success criterion |
|---|---|---|
| Recognise | Match crash-shaped re-entry against the five triggers | A trigger matched, or you stay silent |
| Offer | Surface the one-line offer above, its own message | The door is *named*, not opened |
| Confirm | Wait for an explicit yes | Nothing runs without it |
| Hand off | The PM's yes → `/friday:resume` runs | Terminal state reached |

## Excuse | Reality

| Excuse | Reality |
|---|---|
| "Obviously crashed — just resume." | Resume verifies claims before believing them; auto-running skips the PM's chance to say "no, start fresh." |
| "I'll just finish what was in flight." | A session that died mid-write may have died mid-corruption; only resume's checks make continuing safe. |
| "Re-running is harmless." | Re-doing completed work, or trusting a stale claim, is the exact failure resume exists to prevent. |

Human signal phrases that mean you got it wrong: *"I didn't say to pick anything up"*, *"why did it start re-running things"*, *"I wanted to start over, not resume."*

## Terminal state

The named terminal state is exactly one of: **the PM confirms and `/friday:resume` runs**, or **the PM declines and nothing happens.** There is no third outcome — this skill never reconstructs state itself, and never chains into another skill.
