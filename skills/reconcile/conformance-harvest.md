# The conformance harvest — reading a project's own writing for the rules it declared

The deep-clean-only half of the conformance capability (INC-105, D7): a whole-corpus read that finds the sentences in which the project states a rule about its own code — a single configuration surface, a required boundary check, an allowed direction of dependency, one wrapper per external service. The model is the adapter; no blessed file is parsed and no list of expected rules is carried.
This file is lane-homed here because exactly one lane consumes it (`${CLAUDE_PLUGIN_ROOT}/skills/reconcile/SKILL.md` §2); a second consumer moves it to the shared `docs/` home, cited from both sides (D-0083). Every plugin-side path in it is written from the plugin root, and the lead expands each one into the reader's spawn message — a bare relative path resolves against the PM's project instead, and `${CLAUDE_PLUGIN_ROOT}` does not expand for a spawned reader (INC-208 KH-3).
The check grammar this harvest writes into is single-homed at `${CLAUDE_PLUGIN_ROOT}/docs/contracts/conformance-envelope.md` § The check grammar — the closed kind vocabulary, each kind's required segments, and the orphan mirror all live there and are cited from here, never restated.

## The corpus, and where it stops (D13, OQ-105.4)

1. **The record set INC-101 derives** — `python3 "${CLAUDE_PLUGIN_ROOT}/tools/doc_probe_scope.py" --root . --json` (the lead runs it, or hands the resolved tool path in the spawn message), read whole under the size bar declared beside it. Cited, never defined a second time: this derivation is the one thing the harvest shares with the document-truth probe (D2).
2. **The bounded source-file pass** — the header region of every source file: the leading comment or docstring block, because that is where the drill found a declared convention living outside any document. The bound is the record set's own declared read bar, reused rather than given a second knob — resolved at build against real measurement: on friday's own tree the entire header pass across every source file weighs a small fraction of that bar. A file the pass does not reach is named **unread** in the sweep report, never folded into a clean verdict.
3. **The path-scoped rule files** — `.claude/rules/*.md` in the project's own tree (contract: `${CLAUDE_PLUGIN_ROOT}/docs/contracts/claude-scaffold.md`): each already carries a `paths:` glob beside its convention text, which is half an invariant written down. This is the one source friday's own tree cannot dogfood — it has none.

## What a harvested rule becomes (D1, KH-4)

- A rule the closed kind vocabulary can express becomes a **written check**, landed through the block's owning tool — `python3 "${CLAUDE_PLUGIN_ROOT}/tools/conformance_checks.py" --root . add --id <id> --kind <kind> --rule "<the rule>" --from <where it is written> --anchor "<the exact phrase>" …` — with the kind, its required segments and the remaining flags taken from the grammar's single home, and `--anchor` always supplied (the exact phrase from the source document; the orphan mirror it feeds is the contract's).
- A rule that is real but has no mechanical check yet becomes an **`unchecked`** line in the same block, through the same door — found-not-checked, first-class, never absent from the report and never counted clean.
- A check that already exists for a rule is **kept and improved, never re-derived** — the written check is the version somebody corrected, and the next sweep must run that one (D1; is this promise made checkable). The harvest edits a check only to fix a demonstrated misread of its rule, and never deletes a check whose rule still stands.

## Discipline

- The harvest read is **report-only**: the spawned reader proposes check lines and names its unread remainder; the lead lands every line through the owning tool. The reader edits nothing, exactly as the sweep edits nothing.
- **Never soften a rule to reconcile it with the code.** A violated mandate is not a rotted sentence — the document check owns sentence-truth, this harvest owns rule-discovery, and their remedies never merge (D2, KH-3). The two readers share a corpus, a moment and a model tier and stay distinct on what they produce: proposed check lines here, claim findings there.
- No secret value enters a proposed check line or the report — a rule about configuration surfaces is quoted from its document, never from the line a value sits on.
