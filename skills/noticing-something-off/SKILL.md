---
name: noticing-something-off
description: Use this when the PM reports something that feels wrong, confusing, or not-quite-right about a friday-managed project but has not typed a lane command — "something's off with…", "this feels wrong", "why does it do…", "I don't understand why…", "that's not what I expected", "the colour looks weird". Observation-shaped, un-triaged noticing. Offers /friday:feedback and never runs it without an explicit yes.
---

# Noticing something off — recognise the observation, offer the door

> **Iron law: OFFER, NEVER ENTER. Nothing runs, and nothing gets classified, without the PM's explicit yes.**
> Guessing it's "a bug" and opening the bug lane yourself violates this law's spirit as much as running feedback uninvited.

## Anti-scope — what this skill is NOT

This skill does **not** triage, diagnose, classify, or fix. It does not decide whether the thing is a bug, a patch, or a feature — that judgement belongs to `/friday:feedback`, whose whole point is *understanding before classification*. This skill only recognises observation-shaped noticing and offers that door. If the PM already knows what it is and typed `/friday:bug` (or patch/feature/feedback), this skill is irrelevant — **typed commands are canonical.**

## Triggers (counted, not vibes)

Fires on observation-shaped phrasing — at least one of these five shapes:

1. "something's off / wrong with …"
2. "this feels wrong / weird / not right"
3. "why does it … / why is it doing …"
4. "I don't understand why …"
5. "that's not what I expected" / "the {colour, text, layout} looks off"

Deliberately ambiguous phrasing ("hmm", "that's interesting") → **offer OR stay silent, never a silent entry.** Do not infer a bug from a frown.

## The move (scripted)

Say, in this shape: **"That sounds like something worth looking at — want me to run /friday:feedback? It figures out what's actually going on before deciding whether anything needs to change."** Then **wait.**

## Quick reference

| Phase | Key activity | Success criterion |
|---|---|---|
| Recognise | Match observation-shaped noticing against the five triggers | A trigger matched, or you stay silent |
| Offer | Surface the one-line offer above, its own message | The door is *named*, not opened, and not pre-classified |
| Confirm | Wait for an explicit yes | Nothing runs without it |
| Hand off | The PM's yes → `/friday:feedback` runs | Terminal state reached |

## Excuse | Reality

| Excuse | Reality |
|---|---|
| "It's clearly a bug — just open the bug lane." | Feedback exists precisely because "clearly a bug" is often a misunderstanding; understanding comes before classification. |
| "They're annoyed, so something's broken." | An annoyance can end in "it does X because we decided Y" — an answer, not work. Don't manufacture a fix. |
| "Routing straight to a lane saves a step." | The wrong lane is the expensive step; feedback routes correctly on purpose. |

Human signal phrases that mean you got it wrong: *"I was just wondering, not asking you to fix it"*, *"why did you decide it's a bug"*, *"I didn't want a whole process."*

## Terminal state

The named terminal state is exactly one of: **the PM confirms and `/friday:feedback` runs**, or **the PM declines and nothing happens.** There is no third outcome — this skill never triages the observation itself, and never chains into a lane.
