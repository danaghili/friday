---
name: starting-a-project
description: Use this the moment the PM voices intent to build or start something new but has not typed a friday command — "I want to build…", "I have an idea for…", "let's make…", "I'm thinking of creating…", "can you help me build…". Idea-shaped intent that has not yet entered a friday project. Offers /friday:init and never runs it without an explicit yes.
---

# Starting a project — recognise the intent, offer the door

> **Iron law: OFFER, NEVER ENTER. Nothing runs without the PM's explicit yes.**
> Auto-running the command "to be helpful" violates the spirit of this law as surely as ignoring it.

## Anti-scope — what this skill is NOT

This skill does **not** start the project, run discovery, choose a stack, or write a single file. It recognises idea-shaped intent and offers the door. The instant the PM confirms, its job is over and `/friday:init` takes the wheel. If the PM already typed `/friday:init`, this skill is irrelevant — **typed commands are canonical** and never need an offer.

## Triggers (counted, not vibes)

Fires on idea-shaped phrasing — at least one of these five shapes:

1. "I want to build / make / create …"
2. "I have an idea for …"
3. "let's build / start / spin up …"
4. "I'm thinking of building …"
5. "can you help me build …"

Deliberately ambiguous phrasing ("I want to fix the thing", "help me with my site") → **offer OR stay silent, never a silent entry.** When unsure whether it's a new build or existing work, offer and let the PM's answer disambiguate.

## The move (scripted)

Say, in this shape: **"This sounds like the start of a new project — want me to run /friday:init? It takes stock of what's here first and routes you to the right door."** Then **wait.** One offer, then silence until the PM answers.

## Quick reference

| Phase | Key activity | Success criterion |
|---|---|---|
| Recognise | Match idea-shaped intent against the five triggers | A trigger matched, or you stay silent |
| Offer | Surface the one-line offer above, its own message | The door is *named*, not opened |
| Confirm | Wait for an explicit yes | Nothing runs without it |
| Hand off | The PM's yes → `/friday:init` runs | Terminal state reached |

## Excuse | Reality

| Excuse | Reality |
|---|---|
| "They obviously want to build — just run init." | Obvious-looking intent still gets a confirm; a wrong auto-entry costs more than one question. |
| "Asking first is friction." | One yes is cheaper than backing out of the wrong door. |
| "They said *build*, so build." | `build` is a discovery *outcome*, not a first move — init routes there when it's right. |

Human signal phrases that mean you got it wrong: *"I didn't ask you to start anything"*, *"why did it just run"*, *"wait, I was still thinking."*

## Terminal state

The named terminal state is exactly one of: **the PM confirms and `/friday:init` runs**, or **the PM declines and nothing happens.** There is no third outcome — this skill never does the work itself, and never chains into another skill.
