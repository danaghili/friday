# The friday manual

A plain-English guide to driving friday — what each command does *for you*, the
shape of a project from start to finish, and which door to reach for when.

friday is a team of expert assistants for building software with Claude Code.
You bring an idea (or an existing codebase); friday interrogates it into a clear
plan you approve, builds it in one focused pass, then independently checks and
documents the result. Every decision that would be expensive to get wrong is put
in front of you *while it is still cheap to change* — and written down, so the
project can always explain itself later.

- **New here?** Read *Getting started* and *The life of a project* below.
- **Looking up one command?** Jump to the *Command reference*.
- **Met a word you don't know?** The *Glossary* defines every term and code.
- **Not sure what to run?** See *Which command when*.

---

## 1. Getting started

**What you need.** friday runs inside Claude Code. It uses Claude Code's agent
teams, so set this once in your environment:

```
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

**Install.** friday installs from its marketplace (this repo). Once installed,
its commands are available as `/friday:<name>` in any project.

**Your first three steps.**

1. `/friday:profile` — a one-time chat that learns how you like to work (how
   much detail you want, how strict to be, how it should explain things). You
   only do this once per person; every project inherits it.
2. `/friday:init` — point it at your idea (or an existing project) and it takes
   stock and starts you down the right path.
3. From there friday tells you the next step at every stage. If you are ever
   unsure, run `/friday:help` — inside a project it prints a **"you are here"**
   line and the sensible next command.

You never have to memorise the command list. friday is built to always show you
the next door.

---

## 2. The life of a project

Here is the whole arc, in order, in plain terms.

**Tune it to you — `/friday:profile`.** Once, up front. Sets your preferences.

**Turn an idea into a plan — `/friday:init` → `/friday:brainstorm`.** This is the
*heavy front*: friday interrogates your idea properly — asking the questions a
good engineer would — until it has a clear, build-ready plan (the **TSOW**, your
scope of work). **You approve that plan. That approval is the one big gate** —
everything after it is checked against it. Doing the hard thinking here is what
lets you walk away during the build. *(Building for a client? Start with
`/friday:intake` to capture their world first. Designing screens? `/friday:design-system`
settles the look once, up front. A risky technical unknown? `/friday:research`
sends parallel investigators at it before you commit.)*

**Build it — `/friday:build`.** friday builds the whole approved plan in one
continuous pass. It only stops to ask you the decisions that are genuinely yours
to make and costly to reverse; everything else it just does — and it writes down
every decision as it goes, so nothing is lost. *(If a build ever gets
interrupted, `/friday:resume` figures out exactly where it stopped and carries
on safely.)*

**Check it independently — `/friday:harden`.** A fresh set of eyes reviews,
tests, and security-checks the finished build. Crucially, hardening **only finds
problems — it never quietly fixes them**. You get a clear list, you decide what
to fix, and only then does it fix. *(It runs `/friday:security` and
`/friday:redteam` as part of this.)*

**Document it — `/friday:reference`.** friday auto-generates the architecture
docs straight from the code, then checks the docs against the code so they can
**never drift into a comfortable fiction**. You get an honest, always-current map
of what was built and why.

**Live with it — the maintenance loop.** Once a project is delivered, anything
you notice goes through **`/friday:feedback`** — the free-form front door for "this
feels off," "this seems broken," or "I don't understand this." friday figures out
what it really is and routes it: **`/friday:patch`** (a tiny change), **`/friday:bug`**
(something's broken — you get a diagnosis to confirm *before* any code changes),
or **`/friday:feature`** (a genuinely new capability, which gets its own small
plan-and-approve cycle).

**Before a big moment — `/friday:reconcile`.** Before you merge, release, or hand
over, this is the deep-clean audit: it makes the written record and the actual
reality **agree in writing**, or hands you a short list of exactly where they
don't and what you decided about each.

**Hand it to its owner — `/friday:handoff`.** At the end, this assembles the
**client-ownership package**: a plain-language set a non-technical owner can use
to run, understand, budget for, and prove their product — and take to any other
developer with confidence. (Secrets like passwords and keys are handled by *name
only* — friday tells you exactly what to transfer, but never touches a real
value; you move those yourself through your own password manager.)

---

## 3. Command reference

Every command, grouped by where it lives in a project's life — the same five
groups `/friday:help` sorts them into.

### Starting a project

- **`/friday:profile`** — a one-time interview that captures how you like to
  work (verbosity, strictness, how it explains things). Inherited by every
  project; re-run it anytime to update.
- **`/friday:init`** — the discovery front door. It takes stock of what already
  exists and runs only the missing steps (profile → plan → early design →
  setup). Highly interactive by design — this is the up-front thinking that
  earns you a hands-off build.
- **`/friday:intake`** — for client work: captures the client's world (their
  systems, data, rules, constraints) *before* discovery starts, because those
  answers can't be filled in later.
- **`/friday:brainstorm`** — the heart of discovery: it interrogates your idea
  and writes the build-ready plan (the TSOW). This is where a rough idea becomes
  something buildable.
- **`/friday:design-system`** — settles the interface *once*, coherently, during
  discovery, before any building. friday shapes the concept; the design tools
  take it from there.
- **`/friday:research`** — when there's a genuine technical unknown, it sends
  several investigators at one question in parallel and brings back evidence,
  before you commit to an approach.
- **`/friday:adopt`** — brings an existing codebase that never used friday under
  management *honestly* — it reads the code and records what's actually there,
  without inventing a history the project doesn't have.
- **`/friday:backfill`** — upgrades a project built by an *older* friday onto the
  current version. The promise: an upgrade never orphans a project and never
  invents its past.

### Building

- **`/friday:build`** — the main event: builds the whole approved plan in one
  continuous pass, asking you only the costly decisions and recording every
  decision as it goes.
- **`/friday:resume`** — if a build is interrupted (a crash, a closed laptop),
  this reconstructs exactly where it stopped and continues safely.

### Checking the work

- **`/friday:harden`** — the one review ceremony, run *after* the build is done
  (never per-task). A fresh, independent team reviews, tests, and probes the
  whole build. It **finds, it does not fix** — you decide what to act on.
- **`/friday:security`** — verifies the security promises the plan made actually
  hold, with proof or an honest statement of the limit. Runs automatically
  inside hardening, or on its own.
- **`/friday:redteam`** — the adversary: it hunts for the weak doors *nobody
  thought to promise*, and makes the plan smarter for what it finds.

### Changing a delivered project

- **`/friday:feedback`** — the front door for anything you noticed: a maybe-bug,
  a screen that feels wrong, wording that reads badly, behavior you don't
  understand. Its first job is *understanding* what you mean, then routing you to
  the right lane.
- **`/friday:patch`** — a genuinely small change (text, a color, a config value,
  a dependency bump). One tap of confirmation is the whole ceremony — and it
  still leaves a trail.
- **`/friday:bug`** — the lane for something known to be broken. You get a
  **diagnosis you confirm before any code changes**, and a fix that can't quietly
  come back (a test is born from the bug).
- **`/friday:feature`** — a new capability for an already-built project. It gets
  the same careful plan-and-approve cycle as the original build, scaled down.

### Keeping the records honest

- **`/friday:reference`** — auto-generates the architecture documentation from
  the code and checks the docs against the code, so they can never quietly drift.
- **`/friday:reconcile`** — the deep-clean audit before a merge, release, or
  handover: makes the record and reality agree in writing, or hands you the exact
  short list of where they don't.
- **`/friday:handoff`** — assembles the plain-language client-ownership package
  so a non-technical owner can run, understand, budget for, and prove their
  product — and take it to any developer.
- **`/friday:help`** — prints the full command list grouped by life-stage, plus a
  **"you are here"** readout and the sensible next command when you're inside a
  project. Reach for this whenever you're unsure.

---

## 4. Glossary

Plain definitions of every term and code you'll meet.

- **TSOW** (*Technical Scope of Work*) — the build-ready plan. friday
  interrogates your idea into this document, and **you approve it**. It's the
  fixed reference the build is measured against; the build never rewrites it.
- **Oracle** — a fixed reference that friday checks work against so it can't
  fool itself. The approved TSOW is the build's oracle; the code is the
  documentation's oracle.
- **Decision log** (`docs/DECISIONS.md`) — the running record of every decision
  made, each numbered **D-NNNN** (e.g. D-0042). friday writes to it as it works,
  so you can always see *why* something is the way it is.
- **The substrate** (`.friday/`) — friday's private working memory: crash-resume
  state, a running journal, cost tracking. It lives in a hidden folder and isn't
  part of your shipped code.
- **Harden** — the independent, after-the-build review/test/security pass. It
  only *finds*; you decide what to fix.
- **Reconcile** — the deep-clean audit that makes the written record and actual
  reality agree, run before big moments (merge, release, handover).
- **Increment / INC-NNN** — an addition to an already-built project (what
  `/friday:feature` produces), specced in its own small approved document.
- **Requirement codes (FR / NFR / AC / S)** — the internal numbering friday uses
  *inside* the plan to track that every promised thing got built (grouped by user
  story, `US-NNN`). You won't see these in the commands you read; they live in the
  plan and the coverage record.
- **State** — a project's lifecycle stage, tracked automatically: *plan approved
  → set up → building → reviewed → closed*. `/friday:help` reads it and tells you
  where you are. friday won't let a session end while the record is visibly
  broken.
- **FRIDAY-CLAIMS** — machine-checkable facts about your project (its tech stack,
  its non-goals, its limits), written as simple lines friday's checkers can
  verify.
- **Worktree** — a git feature that lets friday work on a separate copy of your
  code without disturbing your main one. friday shares its memory across
  worktrees automatically; you don't have to think about it.
- **Behavior paragraph** — the approved plain-English description of what a
  command does. These paragraphs are the source this manual is built from.
- **Grilling / interrogation** — friday's questioning style during discovery:
  it presses on an idea (the way a good engineer would) until the plan is
  genuinely clear, rather than taking a vague brief at face value.

---

## 5. Which command when

A quick "you are here" map. When in doubt, `/friday:help` prints this for your
actual project state.

| Your situation | The door |
| --- | --- |
| First time using friday | `/friday:profile`, then `/friday:init` |
| I have an idea to build | `/friday:init` (it runs `/friday:brainstorm` for you) |
| I'm building for a client | `/friday:intake` first, then `/friday:init` |
| I have a risky technical unknown | `/friday:research` |
| I have existing code friday's never seen | `/friday:adopt` |
| I have an old-friday project to upgrade | `/friday:backfill` |
| The plan is approved — build it | `/friday:build` |
| A build got interrupted | `/friday:resume` |
| The build is done — check it | `/friday:harden` |
| Something feels off / I noticed something | `/friday:feedback` (it routes you) |
| A tiny change (text, color, config) | `/friday:patch` |
| Something is broken | `/friday:bug` |
| I want a new capability | `/friday:feature` |
| I'm about to merge / release / hand over | `/friday:reconcile` |
| Handing the finished product to its owner | `/friday:handoff` |
| I want the architecture docs refreshed | `/friday:reference` |
| I don't know where I am | `/friday:help` |

---

*This manual is generated from friday's approved behavior paragraphs and the
command surfaces themselves. If a description here disagrees with what a command
actually does, that's a bug in the command — tell friday.*
