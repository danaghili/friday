# Doc access — the decision rule + measured harness facts

How to read project documentation efficiently. These are MEASURED facts, not
preferences — a fresh rebuild cannot rediscover them except by repeating the
live probes, so they are carried verbatim.

## The decision rule

**If you would otherwise Read a doc bigger than ~25 KB just to use one part
of it, use friday-docs `get_section` instead** (after `list_sections` if you
don't know the exact heading). Under ~25 KB, a plain Read is fine and simpler.
Origin: transcript study behind PROP-024 — semantic search was only **3% of
real demand**; **87% of weighted traffic** was served under a
25%-of-file-bytes threshold. That is why friday-docs is exact-match live-parse
and NOT embeddings/RAG — the design is validated, not a default.

Observed failure mode (live build): a bare "friday-docs: available" flag with
no load-and-use instruction caused all three teammates to whole-file-read a
50 KB doc three times over. Spawn messages must say WHAT to fetch and HOW.

## The subagent context fact (harness-level; probed 2026-07-10, CC 2.1.206)

A project-level `CLAUDE.md` reaches **ZERO** spawned Agent-tool subagents
(the user-global `~/.claude/CLAUDE.md`, env block, and git snapshot do reach
them). Design consequence, binding on every dispatching surface: **anything a
teammate or checker must know goes in the spawn message or its explicit Read
list — never assumed from ambient CLAUDE.md inheritance.**

## plugin: paths

Any friday-docs path starting `plugin:` resolves against the plugin's own
install (contained under its `docs/`), so a teammate in ANY project can fetch
the shared methodology docs — e.g. `plugin:docs/teammate-contract.md`.

## Heading pinning (the pattern)

Every document a script parses declares a fixed heading contract, and nothing
renames a heading a tool depends on without updating the tool in the same
change — `get_section` misses are silent until a consumer breaks. Pinned sets
live in `docs/contracts/*`.
