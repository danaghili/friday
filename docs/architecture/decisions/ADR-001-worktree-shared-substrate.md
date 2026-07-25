# ADR-001 — `.friday/` is keyed to the git common dir (worktrees share substrate)

**Context.** vnext adopts worktree isolation twice (the build worktree and
parallel-bug fan-out), but git worktrees do not share gitignored files, and
the entire runtime substrate is gitignored. Naive adoption fragments the
journal, the D-NNNN counter, and crash-resume — breaking the single-writer
invariants the whole design depends on (ISSUE-006 / NFR-4).

**Decision.** Every substrate writer resolves `.friday/` via
`git rev-parse --git-common-dir` and uses its parent — one shared substrate
per canonical repo (`tools/friday_substrate.resolve_project_root`). Tracked
files (docs/DECISIONS.md) belong to the checkout instead
(`resolve_worktree_root`). The D-NNNN counter lives in the SHARED substrate
under an advisory flock, so concurrent worktree writers cannot collide even
though their DECISIONS.md checkouts differ. Session locks are per-session
(`.friday/sessions/<id>.lock`). The substrate must stay gitignored —
`decisions_append --init` enforces the rule mechanically after a live drill
incident where a committed `.friday/` produced a stale shadow copy in a
worktree checkout.

**Alternatives rejected.** Per-worktree substrate with merge-on-finish
(re-introduces the fragmentation + an unsolvable id-merge problem); resolving
against cwd with an env override (the exact landmine Appendix B names);
committing the substrate (noisy diffs + the shadow-copy incident above).

**Consequences.** All worktree tooling is zero-config; discarding a worktree
never destroys the audit trail; anything writing `.friday/` outside
`friday_substrate` is a review finding by definition.

`[Sources: DECISIONS.md D-0003, D-0007; TSOW Appendix B; verified live in the loop-gate drill]`
