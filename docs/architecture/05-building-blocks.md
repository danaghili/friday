# Building blocks — friday (vnext)

Synthesized from `docs/DECISIONS.md` + the generated IR
(`generated/architecture-ir.json`); the inventory and diagram below are grounded
in the extractor and verified against it by the diff oracle
(`tools/doc-synthesis/synthesis_diff.py`). Contract:
`docs/contracts/synthesis-handoff.md`. This file is re-synthesized, not
hand-curated: it carries **every** module the extractor sees (150) and
**every** import edge (210), so it can never quietly drift into a
flattering subset.

## Component inventory

**hooks/ — the enforcement layer (thin; block only on a valid FAIL)**

- `hooks._guard` — the blocking-guard skeleton — parse the verdict, block only on a valid FAIL, fail-open otherwise [why: DECISIONS.md D-0011]
- `hooks._hookutil` — hook plumbing: plugin-root resolution + substrate import (deferred, fail-open)
- `hooks.blast_radius_backstop` — Stop-time backstop for a patch's declared blast-radius honesty
- `hooks.blast_radius_guard` — PreToolUse: rejects an edit escaping the declared blast radius [why: DECISIONS.md D-0040]
- `hooks.bug_close_gate` — Stop gate: a bug lane closes only with a trail + a committed regression test
- `hooks.committed_test_guard` — guard #7: the regression test must be committed before the fix [why: DECISIONS.md D-0011]
- `hooks.compaction_filing` — PostCompact: files the finished summary via the substrate (attributed current + append-only archive) [why: DECISIONS.md D-0071/D-0072]
- `hooks.compaction_reorient` — SessionStart(compact): pushes the main session's four-layer package + deterministic backfill [why: DECISIONS.md D-0073]
- `hooks.compaction_steering` — PreCompact: prints the agent-generic steering spec the summarizer follows [why: DECISIONS.md D-0072]
- `hooks.config_change_journal` — journals guard-config / hook changes for the tamper trail
- `hooks.decision_capture` — Channel A: the harness-guaranteed pm-ratified decision write
- `hooks.design_contract_guard` — guard: a locked design contract can't be edited without an override-grant
- `hooks.doc_consumption_guard` — guard: a build-feeding doc must be read before it is cited (S-4)
- `hooks.elicitation_journal` — journals companion clicks / hesitation as elicitation events (FR-74)
- `hooks.foundation_gate` — Stop gate: the foundation unit's interim check passes before any downstream unit
- `hooks.graph_freshness_guard` — guard #8: warns 'N commits behind' when the code graph is stale (never blocks)
- `hooks.lane_close_gate` — Stop gate: a change lane closes only against a satisfied record
- `hooks.open_risks_guard` — guard: an open risk row blocks the move it endangers absent a decision
- `hooks.oracle_edit_guard` — guard #9: the TSOW oracle is PM-only — edits need a typed override-grant [why: DECISIONS.md D-0065]
- `hooks.profile_guard` — guard: the profile write stays inside its declared shape
- `hooks.research_orphan_warn` — warn: a research brief with no consumer citation
- `hooks.review_format_sentinel` — review-envelope bounce (strict-on-Write)
- `hooks.review_format_stop_gate` — review-envelope Stop backstop (fail-open on no valid verdict)
- `hooks.session_lifecycle` — session locks + heartbeat spawn + session-start/end journal
- `hooks.setup_selfcheck` — SessionStart: verifies the friday install is wired correctly
- `hooks.spec_write_guard` — guard: a spec / increment write must carry provenance
- `hooks.state_sentinel` — K-rule detector (dual-bound; identity gate in-hook)
- `hooks.state_stop_gate` — blocks conclusion while the state record is broken
- `hooks.substrate_ask_cleanup` — decision-ask resolution tracking + orphan sweep
- `hooks.substrate_ask_mirror` — fire-before-the-dialog decision-ask mirror (crash durability)
- `hooks.teammate_idle_nudge` — nudges an idle teammate agent in an agent-team build
- `hooks.thrash_detector` — detects repeated failed-edit thrash and surfaces it
- `hooks.usage_telemetry` — per-model token / cost journal lines from transcripts
- `hooks.worktree_create_guard` — WorktreeCreate provisioner: returns the shared-substrate path [why: DECISIONS.md D-0019]
- `hooks.worktree_remove_warn` — warns on worktree removal with unsynced substrate
- `hooks.worktree_substrate_warn` — SessionStart: warns on a shadow .friday inside a worktree

**tools/ — the logic core (checkers, grammars, the substrate)**

- `tools.batch_edit` — batch find-and-replace with the exactly-once refusal: validates the whole edit list, applies all or nothing (promoted from the ad-hoc assert-unique heredoc) [why: DECISIONS.md D-0088, D-0089]
- `tools.blast_radius_check` — computes / validates a patch's declared blast radius (rejects `..` escape)
- `tools.bug_close_check` — verifies a bug lane's trail + regression test before close
- `tools.capture_integrity` — timestamp-spread smell detector for Channel-B decision-log honesty
- `tools.committed_test_check` — guard #7 logic: the regression test is committed before the fix
- `tools.compaction_note` — the mission/orientation write door for compaction packages (stdin/--file, substrate-only writes) [why: DECISIONS.md D-0073]
- `tools.decisions` — decision-log schema / parser / monotonic-ID allocator + override-grant [why: DECISIONS.md D-0004]
- `tools.decisions_append` — the shared append CLI, both capture channels [why: DECISIONS.md D-0007]
- `tools.design_contract_check` — verifies a locked design contract is unedited absent a decision
- `tools.doc_gate` — the document-gate family: build-feeding docs consumed + consumer-cited (S-4)
- `tools.findings_brief_check` — findings-brief grammar gate — concrete evidence required above informational
- `tools.foundation_check` — the foundation-unit interim-gate logic
- `tools.friday_substrate` — single .friday writer + git-common-dir root resolution [why: DECISIONS.md D-0003]
- `tools.gen_command_index` — single-field -> generated README table over both lane homes, commands/*.md line-1 openers + lane-skill frontmatter, with shadow detection (escapes table-breaking chars)
- `tools.graph_freshness_check` — computes 'N commits behind' for the code graph (guard #8 logic)
- `tools.graph_query` — the one explore seam: routes to graphify or friday's IR, EXTRACTED-only (FR-70)
- `tools.graph_refresh` — refreshes + stamps the code graph AFTER the docs (FR-71)
- `tools.handoff_attest` — records an operator gate attestation; refuses secret-shaped notes (FR-84)
- `tools.handoff_gate` — the handoff completion gate: gates need the pm channel + restore evidence (FR-85)
- `tools.handoff_package_check` — verifies the handoff package's required members + who-can-do tags
- `tools.lane` — the lane-sentinel CLI (open / clear, O_EXCL atomic claim) [why: DECISIONS.md D-0023]
- `tools.open_risks_check` — the open-risk-row gate logic
- `tools.oracle_edit_check` — guard #9 logic: oracle edits need a structured override-grant
- `tools.profile_check` — validates the profile write path
- `tools.receipt` — tree-hash receipts backstop (hooks fail open; this does not)
- `tools.research_orphan_check` — scans docs/research/** for a `consumer:` tag on every brief (S-4)
- `tools.sanitized_mirror` — the reviewer-sandbox sanitized mirror (invisible-char strip; S-3)
- `tools.seam_handoff` — the seam-handoff build-model primitive (NOT /friday:handoff)
- `tools.secret_names` — enumerates env-var NAMES only from example dotenv / source; never opens a real .env (FR-84)
- `tools.session_heartbeat` — per-session liveness ticker; a stale ts IS the crash signal
- `tools.skill_standard_check` — the two-kinds skill floor over skills/*/SKILL.md: FR-81 strict standard for noticing-skills, FR-2.5 lighter floor for lane-skills
- `tools.spawn_telemetry` — THE spawn / accept / done telemetry primitive
- `tools.spec_id_strip_check` — ship-gate: flags surviving FR- / US- / S-n tags on user surfaces, incl. bundled files inside lane folders via the surface-aware --skills-dir mode [why: DECISIONS.md D-0044]
- `tools.taglines` — typed tag-line grammar family, empty-case-tested
- `tools.trail_check` — the change-trail grammar checker (FR-62 / FR-65)
- `tools.usage_report` — journal usage-event roll-up (NFR-2 cost visibility)
- `tools.verify_claims` — FRIDAY-CLAIMS drift detector (string-mechanical)
- `tools.verify_coverage` — TSOW requirement-ID coverage closure; deferrals cite a D-NNNN (K7)
- `tools.verify_generated` — verifies the generated doc set is present + provenance-stamped
- `tools.verify_review_format` — FRIDAY-REVIEW envelope checks + canonical-file provenance
- `tools.verify_spawn_coverage` — anti-orphan-spawn coverage check over both lane homes (commands/ + lane-skills in skills/)
- `tools.verify_state` — K0-K8 state verifier (Appendix A.3; corpus-driven)
- `tools.worktree_create_check` — the WorktreeCreate provisioner logic (returns the substrate path)

**tools/doc-index/ — the friday-docs MCP retrieval triad (never RAG)**

- `tools.doc-index.mdparse` — exact-after-normalization heading matcher [why: DECISIONS.md D-0006]
- `tools.doc-index.registry` — sync-on-query sqlite index (documents / decisions / actions)
- `tools.doc-index.server` — friday-docs MCP: live-parse triad + advisory aggregates (never RAG)

**tools/doc-synthesis/ — the extract -> synthesize -> diff loop**

- `tools.doc-synthesis.extract_architecture` — the A.1 IR extractor (stdlib ast, pure static)
- `tools.doc-synthesis.synthesis_diff` — the extractor-vs-synthesis QA oracle (this file's judge)

**tools/codex-adapter/ — the fail-closed Codex port**

- `tools.codex-adapter.state_stop_gate` — fail-closed Codex port of the K-gate (quota-continuity divergence)

**tools/visual-companion/ — the local stdlib discovery companion**

- `tools.visual-companion.companion_server` — zero-dep stdlib companion server + CompanionState (US-15)
- `tools.visual-companion.offer` — the JIT companion offer / route logic (FR-76 offer-never-enter)

**tests/ — the verification mirror (pytest; every grammar tests its empty case)**

- `tests.conftest` — pytest configuration + shared fixtures
- `tests.guardkit` — shared guard-test harness (1 positive control + fail-open controls per blocking guard)
- `tests.test_batch_edit` — regression pins: the batch editor's destruction cases (multi/zero-match, missing file, empty list, dry-run, nothing-written-on-refusal)
- `tests.test_bug_001_verify_claims_stack` — regression pins: BUG-001 stack-claim verification
- `tests.test_bug_002_bug_close_gate_pause` — regression pins: BUG-002 bug-lane arm point
- `tests.test_bug_003_check_readme_sync` — regression pins: BUG-003 README-table sync ownership (`--check` detects, hook resplices via `--write`, D-0096)
- `tests.test_committed_test_check` — regression pins: committed test check
- `tests.test_compaction_capture` — regression pins: compaction capture doors
- `tests.test_companion_offer` — regression pins: companion offer
- `tests.test_companion_server` — regression pins: companion server
- `tests.test_decisions` — regression pins: decisions
- `tests.test_doc_gate` — regression pins: doc gate
- `tests.test_doc_synthesis` — regression pins: doc synthesis
- `tests.test_findings_brief_check` — regression pins: findings brief check
- `tests.test_gen_command_index_skills` — regression pins: the skill-aware lane index (INC-002 — both lane homes, shadow detection, A8 escaping on frontmatter)
- `tests.test_graph_query` — regression pins: graph query
- `tests.test_graph_refresh` — regression pins: graph refresh
- `tests.test_graph_stamp` — regression pins: graph stamp
- `tests.test_guard_blast_radius` — regression pins: guard blast radius
- `tests.test_guard_blast_radius_backstop` — regression pins: guard blast radius backstop
- `tests.test_guard_bug_close` — regression pins: guard bug close
- `tests.test_guard_committed_test` — regression pins: guard committed test
- `tests.test_guard_config_change` — regression pins: guard config change
- `tests.test_guard_design_contract` — regression pins: guard design contract
- `tests.test_guard_doc_consumption` — regression pins: guard doc consumption
- `tests.test_guard_elicitation_journal` — regression pins: guard elicitation journal
- `tests.test_guard_foundation` — regression pins: guard foundation
- `tests.test_guard_graph_freshness` — regression pins: guard graph freshness
- `tests.test_guard_lane_close` — regression pins: guard lane close
- `tests.test_guard_open_risks` — regression pins: guard open risks
- `tests.test_guard_oracle_edit` — regression pins: guard oracle edit
- `tests.test_guard_profile` — regression pins: guard profile
- `tests.test_guard_research_orphan` — regression pins: guard research orphan
- `tests.test_guard_setup_selfcheck` — regression pins: guard setup selfcheck
- `tests.test_guard_skeleton` — regression pins: guard skeleton
- `tests.test_guard_spec_write` — regression pins: guard spec write
- `tests.test_guard_teammate_idle` — regression pins: guard teammate idle
- `tests.test_guard_thrash` — regression pins: guard thrash
- `tests.test_guard_worktree_create` — regression pins: guard worktree create
- `tests.test_guard_worktree_remove` — regression pins: guard worktree remove
- `tests.test_guard_worktree_substrate` — regression pins: guard worktree substrate
- `tests.test_handoff_attest` — regression pins: handoff attest
- `tests.test_handoff_gate` — regression pins: handoff gate
- `tests.test_handoff_package_check` — regression pins: handoff package check
- `tests.test_harden_fixes` — regression pins: harden fixes
- `tests.test_hooks` — regression pins: hooks
- `tests.test_hooks_compaction` — regression pins: compaction hooks
- `tests.test_lane_cli` — regression pins: lane cli
- `tests.test_lane_open_helper` — regression pins: lane open helper
- `tests.test_mdparse` — regression pins: mdparse
- `tests.test_registry` — regression pins: registry
- `tests.test_review_format_interim` — regression pins: review format interim
- `tests.test_sanitized_mirror` — regression pins: sanitized mirror
- `tests.test_secret_names` — regression pins: secret names
- `tests.test_server` — regression pins: server
- `tests.test_session_lifecycle` — regression pins: session-start journals the SessionStart source label (the auto-compact label trap)
- `tests.test_skill_standard_check` — regression pins: skill standard check
- `tests.test_spec_id_strip_bundled` — regression pins: the ship gate's surface-aware bundled-file mode (INC-003 — planted-tag catch, binary-sibling safety, empty cases)
- `tests.test_stop_gate_failopen` — regression pins: stop gate failopen
- `tests.test_substrate` — regression pins: substrate
- `tests.test_substrate_compaction` — regression pins: compaction substrate verbs
- `tests.test_taglines` — regression pins: taglines
- `tests.test_trail_check` — regression pins: trail check
- `tests.test_verify_claims` — regression pins: verify claims
- `tests.test_verify_coverage` — regression pins: verify coverage
- `tests.test_verify_generated` — regression pins: verify generated
- `tests.test_verify_state` — regression pins: verify state

## Component diagram

Every module and import edge the extractor found, grouped by subsystem. Solid
edges are module-level imports; `-.->|deferred|` marks a function-local import
(the fail-open pattern — a broken dependency degrades a feature, never the
session). The graph is dense by design (the tests/ mirror alone carries
94 of the 210
edges); read it through the layering below, not left-to-right.

```mermaid
graph LR
    subgraph sg_hooks [hooks/]
        hooks__guard["hooks._guard"]
        hooks__hookutil["hooks._hookutil"]
        hooks_blast_radius_backstop["hooks.blast_radius_backstop"]
        hooks_blast_radius_guard["hooks.blast_radius_guard"]
        hooks_bug_close_gate["hooks.bug_close_gate"]
        hooks_committed_test_guard["hooks.committed_test_guard"]
        hooks_compaction_filing["hooks.compaction_filing"]
        hooks_compaction_reorient["hooks.compaction_reorient"]
        hooks_compaction_steering["hooks.compaction_steering"]
        hooks_config_change_journal["hooks.config_change_journal"]
        hooks_decision_capture["hooks.decision_capture"]
        hooks_design_contract_guard["hooks.design_contract_guard"]
        hooks_doc_consumption_guard["hooks.doc_consumption_guard"]
        hooks_elicitation_journal["hooks.elicitation_journal"]
        hooks_foundation_gate["hooks.foundation_gate"]
        hooks_graph_freshness_guard["hooks.graph_freshness_guard"]
        hooks_lane_close_gate["hooks.lane_close_gate"]
        hooks_open_risks_guard["hooks.open_risks_guard"]
        hooks_oracle_edit_guard["hooks.oracle_edit_guard"]
        hooks_profile_guard["hooks.profile_guard"]
        hooks_research_orphan_warn["hooks.research_orphan_warn"]
        hooks_review_format_sentinel["hooks.review_format_sentinel"]
        hooks_review_format_stop_gate["hooks.review_format_stop_gate"]
        hooks_session_lifecycle["hooks.session_lifecycle"]
        hooks_setup_selfcheck["hooks.setup_selfcheck"]
        hooks_spec_write_guard["hooks.spec_write_guard"]
        hooks_state_sentinel["hooks.state_sentinel"]
        hooks_state_stop_gate["hooks.state_stop_gate"]
        hooks_substrate_ask_cleanup["hooks.substrate_ask_cleanup"]
        hooks_substrate_ask_mirror["hooks.substrate_ask_mirror"]
        hooks_teammate_idle_nudge["hooks.teammate_idle_nudge"]
        hooks_thrash_detector["hooks.thrash_detector"]
        hooks_usage_telemetry["hooks.usage_telemetry"]
        hooks_worktree_create_guard["hooks.worktree_create_guard"]
        hooks_worktree_remove_warn["hooks.worktree_remove_warn"]
        hooks_worktree_substrate_warn["hooks.worktree_substrate_warn"]
    end
    subgraph sg_tools [tools/]
        tools_batch_edit["tools.batch_edit"]
        tools_blast_radius_check["tools.blast_radius_check"]
        tools_bug_close_check["tools.bug_close_check"]
        tools_capture_integrity["tools.capture_integrity"]
        tools_committed_test_check["tools.committed_test_check"]
        tools_compaction_note["tools.compaction_note"]
        tools_decisions["tools.decisions"]
        tools_decisions_append["tools.decisions_append"]
        tools_design_contract_check["tools.design_contract_check"]
        tools_doc_gate["tools.doc_gate"]
        tools_findings_brief_check["tools.findings_brief_check"]
        tools_foundation_check["tools.foundation_check"]
        tools_friday_substrate["tools.friday_substrate"]
        tools_gen_command_index["tools.gen_command_index"]
        tools_graph_freshness_check["tools.graph_freshness_check"]
        tools_graph_query["tools.graph_query"]
        tools_graph_refresh["tools.graph_refresh"]
        tools_handoff_attest["tools.handoff_attest"]
        tools_handoff_gate["tools.handoff_gate"]
        tools_handoff_package_check["tools.handoff_package_check"]
        tools_lane["tools.lane"]
        tools_open_risks_check["tools.open_risks_check"]
        tools_oracle_edit_check["tools.oracle_edit_check"]
        tools_profile_check["tools.profile_check"]
        tools_receipt["tools.receipt"]
        tools_research_orphan_check["tools.research_orphan_check"]
        tools_sanitized_mirror["tools.sanitized_mirror"]
        tools_seam_handoff["tools.seam_handoff"]
        tools_secret_names["tools.secret_names"]
        tools_session_heartbeat["tools.session_heartbeat"]
        tools_skill_standard_check["tools.skill_standard_check"]
        tools_spawn_telemetry["tools.spawn_telemetry"]
        tools_spec_id_strip_check["tools.spec_id_strip_check"]
        tools_taglines["tools.taglines"]
        tools_trail_check["tools.trail_check"]
        tools_usage_report["tools.usage_report"]
        tools_verify_claims["tools.verify_claims"]
        tools_verify_coverage["tools.verify_coverage"]
        tools_verify_generated["tools.verify_generated"]
        tools_verify_review_format["tools.verify_review_format"]
        tools_verify_spawn_coverage["tools.verify_spawn_coverage"]
        tools_verify_state["tools.verify_state"]
        tools_worktree_create_check["tools.worktree_create_check"]
    end
    subgraph sg_docidx [tools/doc-index/]
        tools_doc_index_mdparse["tools.doc-index.mdparse"]
        tools_doc_index_registry["tools.doc-index.registry"]
        tools_doc_index_server["tools.doc-index.server"]
    end
    subgraph sg_docsyn [tools/doc-synthesis/]
        tools_doc_synthesis_extract_architecture["tools.doc-synthesis.extract_architecture"]
        tools_doc_synthesis_synthesis_diff["tools.doc-synthesis.synthesis_diff"]
    end
    subgraph sg_codex [tools/codex-adapter/]
        tools_codex_adapter_state_stop_gate["tools.codex-adapter.state_stop_gate"]
    end
    subgraph sg_vc [tools/visual-companion/]
        tools_visual_companion_companion_server["tools.visual-companion.companion_server"]
        tools_visual_companion_offer["tools.visual-companion.offer"]
    end
    subgraph sg_tests [tests/]
        tests_conftest["tests.conftest"]
        tests_guardkit["tests.guardkit"]
        tests_test_batch_edit["tests.test_batch_edit"]
        tests_test_bug_001_verify_claims_stack["tests.test_bug_001_verify_claims_stack"]
        tests_test_bug_002_bug_close_gate_pause["tests.test_bug_002_bug_close_gate_pause"]
        tests_test_bug_003_check_readme_sync["tests.test_bug_003_check_readme_sync"]
        tests_test_committed_test_check["tests.test_committed_test_check"]
        tests_test_compaction_capture["tests.test_compaction_capture"]
        tests_test_companion_offer["tests.test_companion_offer"]
        tests_test_companion_server["tests.test_companion_server"]
        tests_test_decisions["tests.test_decisions"]
        tests_test_doc_gate["tests.test_doc_gate"]
        tests_test_doc_synthesis["tests.test_doc_synthesis"]
        tests_test_findings_brief_check["tests.test_findings_brief_check"]
        tests_test_gen_command_index_skills["tests.test_gen_command_index_skills"]
        tests_test_graph_query["tests.test_graph_query"]
        tests_test_graph_refresh["tests.test_graph_refresh"]
        tests_test_graph_stamp["tests.test_graph_stamp"]
        tests_test_guard_blast_radius["tests.test_guard_blast_radius"]
        tests_test_guard_blast_radius_backstop["tests.test_guard_blast_radius_backstop"]
        tests_test_guard_bug_close["tests.test_guard_bug_close"]
        tests_test_guard_committed_test["tests.test_guard_committed_test"]
        tests_test_guard_config_change["tests.test_guard_config_change"]
        tests_test_guard_design_contract["tests.test_guard_design_contract"]
        tests_test_guard_doc_consumption["tests.test_guard_doc_consumption"]
        tests_test_guard_elicitation_journal["tests.test_guard_elicitation_journal"]
        tests_test_guard_foundation["tests.test_guard_foundation"]
        tests_test_guard_graph_freshness["tests.test_guard_graph_freshness"]
        tests_test_guard_lane_close["tests.test_guard_lane_close"]
        tests_test_guard_open_risks["tests.test_guard_open_risks"]
        tests_test_guard_oracle_edit["tests.test_guard_oracle_edit"]
        tests_test_guard_profile["tests.test_guard_profile"]
        tests_test_guard_research_orphan["tests.test_guard_research_orphan"]
        tests_test_guard_setup_selfcheck["tests.test_guard_setup_selfcheck"]
        tests_test_guard_skeleton["tests.test_guard_skeleton"]
        tests_test_guard_spec_write["tests.test_guard_spec_write"]
        tests_test_guard_teammate_idle["tests.test_guard_teammate_idle"]
        tests_test_guard_thrash["tests.test_guard_thrash"]
        tests_test_guard_worktree_create["tests.test_guard_worktree_create"]
        tests_test_guard_worktree_remove["tests.test_guard_worktree_remove"]
        tests_test_guard_worktree_substrate["tests.test_guard_worktree_substrate"]
        tests_test_handoff_attest["tests.test_handoff_attest"]
        tests_test_handoff_gate["tests.test_handoff_gate"]
        tests_test_handoff_package_check["tests.test_handoff_package_check"]
        tests_test_harden_fixes["tests.test_harden_fixes"]
        tests_test_hooks["tests.test_hooks"]
        tests_test_hooks_compaction["tests.test_hooks_compaction"]
        tests_test_lane_cli["tests.test_lane_cli"]
        tests_test_lane_open_helper["tests.test_lane_open_helper"]
        tests_test_mdparse["tests.test_mdparse"]
        tests_test_registry["tests.test_registry"]
        tests_test_review_format_interim["tests.test_review_format_interim"]
        tests_test_sanitized_mirror["tests.test_sanitized_mirror"]
        tests_test_secret_names["tests.test_secret_names"]
        tests_test_server["tests.test_server"]
        tests_test_session_lifecycle["tests.test_session_lifecycle"]
        tests_test_skill_standard_check["tests.test_skill_standard_check"]
        tests_test_spec_id_strip_bundled["tests.test_spec_id_strip_bundled"]
        tests_test_stop_gate_failopen["tests.test_stop_gate_failopen"]
        tests_test_substrate["tests.test_substrate"]
        tests_test_substrate_compaction["tests.test_substrate_compaction"]
        tests_test_taglines["tests.test_taglines"]
        tests_test_trail_check["tests.test_trail_check"]
        tests_test_verify_claims["tests.test_verify_claims"]
        tests_test_verify_coverage["tests.test_verify_coverage"]
        tests_test_verify_generated["tests.test_verify_generated"]
        tests_test_verify_state["tests.test_verify_state"]
    end

    hooks__hookutil -.->|deferred| tools_friday_substrate
    hooks_blast_radius_backstop --> hooks__guard
    hooks_blast_radius_backstop --> hooks__hookutil
    hooks_blast_radius_guard --> hooks__guard
    hooks_blast_radius_guard --> hooks__hookutil
    hooks_bug_close_gate --> hooks__guard
    hooks_bug_close_gate --> hooks__hookutil
    hooks_committed_test_guard --> hooks__guard
    hooks_committed_test_guard --> hooks__hookutil
    hooks_compaction_filing --> hooks__hookutil
    hooks_compaction_reorient --> hooks__hookutil
    hooks_compaction_steering --> hooks__hookutil
    hooks_config_change_journal --> hooks__hookutil
    hooks_decision_capture --> hooks__hookutil
    hooks_decision_capture -.->|deferred| tools_decisions
    hooks_design_contract_guard --> hooks__guard
    hooks_design_contract_guard --> hooks__hookutil
    hooks_doc_consumption_guard --> hooks__guard
    hooks_doc_consumption_guard --> hooks__hookutil
    hooks_elicitation_journal --> hooks__hookutil
    hooks_foundation_gate --> hooks__guard
    hooks_foundation_gate --> hooks__hookutil
    hooks_graph_freshness_guard --> hooks__guard
    hooks_graph_freshness_guard --> hooks__hookutil
    hooks_lane_close_gate --> hooks__guard
    hooks_lane_close_gate --> hooks__hookutil
    hooks_open_risks_guard --> hooks__guard
    hooks_open_risks_guard --> hooks__hookutil
    hooks_oracle_edit_guard --> hooks__guard
    hooks_oracle_edit_guard --> hooks__hookutil
    hooks_profile_guard --> hooks__guard
    hooks_profile_guard --> hooks__hookutil
    hooks_research_orphan_warn --> hooks__guard
    hooks_research_orphan_warn --> hooks__hookutil
    hooks_review_format_sentinel --> hooks__hookutil
    hooks_review_format_stop_gate --> hooks__hookutil
    hooks_session_lifecycle --> hooks__hookutil
    hooks_setup_selfcheck --> hooks__hookutil
    hooks_spec_write_guard --> hooks__guard
    hooks_spec_write_guard --> hooks__hookutil
    hooks_state_sentinel --> hooks__hookutil
    hooks_state_stop_gate --> hooks__hookutil
    hooks_substrate_ask_cleanup --> hooks__hookutil
    hooks_substrate_ask_mirror --> hooks__hookutil
    hooks_teammate_idle_nudge --> hooks__guard
    hooks_teammate_idle_nudge --> hooks__hookutil
    hooks_thrash_detector --> hooks__guard
    hooks_thrash_detector --> hooks__hookutil
    hooks_usage_telemetry --> hooks__hookutil
    hooks_worktree_create_guard --> hooks__guard
    hooks_worktree_create_guard --> hooks__hookutil
    hooks_worktree_remove_warn --> hooks__guard
    hooks_worktree_remove_warn --> hooks__hookutil
    hooks_worktree_substrate_warn --> hooks__guard
    hooks_worktree_substrate_warn --> hooks__hookutil
    tests_test_bug_001_verify_claims_stack --> tools_verify_claims
    tests_test_bug_002_bug_close_gate_pause --> tools_bug_close_check
    tests_test_bug_003_check_readme_sync --> tools_gen_command_index
    tests_test_committed_test_check --> tools_committed_test_check
    tests_test_compaction_capture --> tools_friday_substrate
    tests_test_companion_offer --> tests_guardkit
    tests_test_companion_offer --> tools_visual_companion_offer
    tests_test_companion_server --> tests_guardkit
    tests_test_companion_server --> tools_visual_companion_companion_server
    tests_test_decisions --> tools_decisions
    tests_test_doc_gate --> hooks__guard
    tests_test_doc_gate --> tools_doc_gate
    tests_test_doc_synthesis --> tools_doc_synthesis_extract_architecture
    tests_test_doc_synthesis --> tools_doc_synthesis_synthesis_diff
    tests_test_findings_brief_check --> hooks__guard
    tests_test_findings_brief_check --> tools_findings_brief_check
    tests_test_graph_query --> tests_guardkit
    tests_test_graph_query --> tools_graph_query
    tests_test_graph_refresh --> tests_guardkit
    tests_test_graph_refresh --> tools_friday_substrate
    tests_test_graph_refresh --> tools_graph_freshness_check
    tests_test_graph_refresh --> tools_graph_refresh
    tests_test_graph_stamp --> tests_guardkit
    tests_test_graph_stamp --> tools_friday_substrate
    tests_test_graph_stamp --> tools_graph_freshness_check
    tests_test_guard_blast_radius --> tests_guardkit
    tests_test_guard_blast_radius --> tools_blast_radius_check
    tests_test_guard_blast_radius_backstop --> tests_guardkit
    tests_test_guard_bug_close --> tests_guardkit
    tests_test_guard_bug_close --> tools_bug_close_check
    tests_test_guard_committed_test --> tests_guardkit
    tests_test_guard_config_change --> tests_guardkit
    tests_test_guard_design_contract --> tests_guardkit
    tests_test_guard_design_contract --> tools_design_contract_check
    tests_test_guard_doc_consumption --> tests_guardkit
    tests_test_guard_elicitation_journal --> tests_guardkit
    tests_test_guard_foundation --> tests_guardkit
    tests_test_guard_foundation --> tools_foundation_check
    tests_test_guard_graph_freshness --> tests_guardkit
    tests_test_guard_graph_freshness --> tools_graph_freshness_check
    tests_test_guard_lane_close --> tests_guardkit
    tests_test_guard_open_risks --> tests_guardkit
    tests_test_guard_open_risks --> tools_open_risks_check
    tests_test_guard_oracle_edit --> tests_guardkit
    tests_test_guard_oracle_edit --> tools_oracle_edit_check
    tests_test_guard_profile --> tests_guardkit
    tests_test_guard_profile --> tools_profile_check
    tests_test_guard_research_orphan --> tests_guardkit
    tests_test_guard_research_orphan -.->|deferred| tools_research_orphan_check
    tests_test_guard_setup_selfcheck --> tests_guardkit
    tests_test_guard_skeleton --> hooks__guard
    tests_test_guard_spec_write --> tests_guardkit
    tests_test_guard_teammate_idle --> tests_guardkit
    tests_test_guard_thrash --> tests_guardkit
    tests_test_guard_worktree_create --> tests_guardkit
    tests_test_guard_worktree_create --> tools_worktree_create_check
    tests_test_guard_worktree_remove --> tests_guardkit
    tests_test_guard_worktree_substrate --> tests_guardkit
    tests_test_handoff_attest --> tools_friday_substrate
    tests_test_handoff_attest --> tools_handoff_attest
    tests_test_handoff_attest --> tools_handoff_gate
    tests_test_handoff_gate --> tools_handoff_gate
    tests_test_handoff_package_check --> tools_handoff_package_check
    tests_test_gen_command_index_skills --> tools_gen_command_index
    tests_test_harden_fixes --> tools_blast_radius_check
    tests_test_harden_fixes --> tools_findings_brief_check
    tests_test_harden_fixes --> tools_friday_substrate
    tests_test_harden_fixes --> tools_gen_command_index
    tests_test_harden_fixes --> tools_handoff_attest
    tests_test_harden_fixes --> tools_handoff_gate
    tests_test_harden_fixes --> tools_sanitized_mirror
    tests_test_harden_fixes --> tools_spec_id_strip_check
    tests_test_harden_fixes --> tools_verify_state
    tests_test_hooks --> tools_decisions
    tests_test_hooks --> tools_verify_review_format
    tests_test_hooks_compaction --> tools_friday_substrate
    tests_test_lane_open_helper --> tools_friday_substrate
    tests_test_mdparse --> tools_doc_index_mdparse
    tests_test_registry --> tools_doc_index_registry
    tests_test_sanitized_mirror --> tools_sanitized_mirror
    tests_test_secret_names --> tools_secret_names
    tests_test_server --> tools_doc_index_server
    tests_test_skill_standard_check --> tests_guardkit
    tests_test_skill_standard_check --> tools_skill_standard_check
    tests_test_spec_id_strip_bundled --> tools_spec_id_strip_check
    tests_test_batch_edit --> tools_batch_edit
    tests_test_substrate --> tools_friday_substrate
    tests_test_substrate -.->|deferred| tools_verify_spawn_coverage
    tests_test_substrate_compaction --> tools_friday_substrate
    tests_test_taglines --> tools_taglines
    tests_test_trail_check --> hooks__guard
    tests_test_trail_check --> tools_trail_check
    tests_test_verify_claims --> tools_taglines
    tests_test_verify_claims --> tools_verify_claims
    tests_test_verify_coverage --> tools_verify_coverage
    tests_test_verify_generated --> tools_verify_generated
    tests_test_verify_state --> tools_decisions
    tests_test_verify_state --> tools_verify_state
    tools_bug_close_check --> tools_trail_check
    tools_capture_integrity --> tools_decisions
    tools_capture_integrity --> tools_friday_substrate
    tools_committed_test_check -.->|deferred| tools_decisions
    tools_committed_test_check -.->|deferred| tools_friday_substrate
    tools_committed_test_check --> tools_taglines
    tools_compaction_note --> tools_friday_substrate
    tools_decisions --> tools_friday_substrate
    tools_decisions --> tools_taglines
    tools_decisions_append --> tools_decisions
    tools_decisions_append --> tools_friday_substrate
    tools_design_contract_check -.->|deferred| tools_decisions
    tools_doc_index_registry --> tools_decisions
    tools_doc_index_registry --> tools_friday_substrate
    tools_doc_index_registry --> tools_taglines
    tools_doc_index_server --> tools_doc_index_mdparse
    tools_doc_index_server --> tools_doc_index_registry
    tools_doc_index_server -.->|deferred| tools_receipt
    tools_doc_index_server -.->|deferred| tools_verify_claims
    tools_doc_index_server -.->|deferred| tools_verify_state
    tools_doc_synthesis_synthesis_diff -.->|deferred| tools_decisions
    tools_doc_synthesis_synthesis_diff -.->|deferred| tools_doc_index_mdparse
    tools_doc_gate --> tools_findings_brief_check
    tools_doc_gate --> tools_taglines
    tools_findings_brief_check --> tools_taglines
    tools_foundation_check --> tools_taglines
    tools_foundation_check --> tools_verify_claims
    tools_graph_freshness_check --> tools_friday_substrate
    tools_graph_refresh --> tools_friday_substrate
    tools_handoff_attest --> tools_friday_substrate
    tools_handoff_attest --> tools_handoff_gate
    tools_handoff_gate --> tools_friday_substrate
    tools_lane --> tools_friday_substrate
    tools_open_risks_check --> tools_decisions
    tools_open_risks_check --> tools_taglines
    tools_oracle_edit_check --> tools_decisions
    tools_oracle_edit_check --> tools_taglines
    tools_receipt --> tools_friday_substrate
    tools_receipt -.->|deferred| tools_verify_claims
    tools_receipt -.->|deferred| tools_verify_coverage
    tools_receipt -.->|deferred| tools_verify_spawn_coverage
    tools_receipt -.->|deferred| tools_verify_state
    tools_research_orphan_check --> tools_taglines
    tools_seam_handoff --> tools_decisions
    tools_seam_handoff --> tools_friday_substrate
    tools_session_heartbeat --> tools_friday_substrate
    tools_spawn_telemetry --> tools_friday_substrate
    tools_trail_check --> tools_decisions
    tools_trail_check --> tools_taglines
    tools_usage_report --> tools_friday_substrate
    tools_verify_claims --> tools_taglines
    tools_verify_coverage --> tools_taglines
    tools_verify_review_format --> tools_taglines
    tools_verify_state --> tools_decisions
    tools_verify_state --> tools_friday_substrate
    tools_verify_state -.->|deferred| tools_receipt
    tools_verify_state --> tools_taglines
    tools_verify_state --> tools_verify_claims
    tools_verify_state --> tools_verify_coverage
    tools_visual_companion_companion_server -.->|deferred| tools_friday_substrate
    tools_worktree_create_check --> tools_friday_substrate
```

## Layering (the reading of the graph)

Read bottom-up, four layers:

1. **The foundation — `tools.friday_substrate`.** The single-writer invariant
   made visible: nearly every tool edge points into it (every `.friday/` write
   goes through one place; the worktree-shared root via the git common dir —
   Appendix B). `tools.decisions` + `tools.taglines` sit just above it as the
   shared record and grammar.
2. **The logic core — `tools/`.** The checker/verifier family
   (`verify_*`, `*_check`, the `*_gate` logic) builds on `taglines` + `decisions`
   + the substrate. This is where every script-checked claim actually lives; the
   grammars each test their own empty case.
3. **The enforcement layer — `hooks/`.** Deliberately thin. Hooks **shell out**
   to the logic-core checkers rather than importing them — the subprocess
   boundary is what keeps a hook failure fail-open (a crashing checker ALLOWS the
   action; only a valid FAIL verdict blocks). `hooks._guard` is the shared
   blocking-guard skeleton; `hooks._hookutil` deferred-imports the substrate so a
   broken install degrades to no-telemetry, never a broken session.
4. **The subsystems.** `tools/doc-index/` is the friday-docs MCP retrieval triad
   (live-parse, never RAG); `tools/doc-synthesis/` is the extract → synthesize →
   diff loop that produced this very file; `tools/visual-companion/` is the local
   zero-dependency discovery companion; `tools/codex-adapter/` is the one
   deliberately fail-**closed** port (Codex quota-continuity, not friday's
   fail-open default). `tests/` mirrors the core one-to-one, with `tests.guardkit`
   supplying each blocking guard its positive control + fail-open controls.
   `.claude/hooks/` is repo CI, not shipped plugin runtime.

**Last-verified:** 2026-07-24 (reconcile deep clean: BUG-003 test module back-filled into inventory + graph; synthesis_diff clean) · **Record-status:** verified
