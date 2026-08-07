# Building blocks — friday (vnext)

Synthesized from `docs/DECISIONS.md` + the generated IR
(`generated/architecture-ir.json`); the inventory and diagram below are grounded
in the extractor and verified against it by the diff oracle
(`tools/doc-synthesis/synthesis_diff.py`). Contract:
`docs/contracts/synthesis-handoff.md`. This file is re-synthesized, not
hand-curated: it carries **every** module the extractor sees and **every**
import edge, so it can never quietly drift into a flattering subset — the
counts live in the IR, and the diff oracle proves the "every" on each
regeneration (INC-203 D4).

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
- `hooks.due_signal` — SessionStart warn: standing-care due-signals on a closed project (reconcile due / handover missing) [why: DECISIONS.md D-0111]
- `hooks.elicitation_journal` — journals companion clicks / hesitation as elicitation events (FR-74)
- `hooks.foundation_gate` — Stop gate: the foundation unit's interim check passes before any downstream unit
- `hooks.graph_freshness_guard` — guard #8: warns 'N commits behind' when the code graph is stale (never blocks)
- `hooks.lane_close_gate` — Stop gate: a change lane closes only against a satisfied record
- `hooks.maintainability_gate` — close-time gate: blocks (armed) or warns (warn-first) on an un-dispositioned maintainability breach; fail-open on its own faults [why: DECISIONS.md D-0119]
- `hooks.open_risks_guard` — guard: an open risk row blocks the move it endangers absent a decision
- `hooks.oracle_edit_guard` — guard #9: the TSOW oracle is PM-only — edits need a typed override-grant [why: DECISIONS.md D-0065]
- `hooks.profile_guard` — guard: the profile write stays inside its declared shape
- `hooks.research_orphan_warn` — warn: a research brief with no consumer citation
- `hooks.review_format_sentinel` — review-envelope bounce (strict-on-Write)
- `hooks.review_format_stop_gate` — review-envelope Stop backstop (fail-open on no valid verdict)
- `hooks.session_lifecycle` — session locks + heartbeat spawn + session-start/end journal
- `hooks.setup_selfcheck` — SessionStart: verifies the friday install is wired correctly
- `hooks.spec_write_guard` — guard: a spec / increment write must carry provenance
- `hooks.state_advisory` — PreToolUse warn: lane×state contradictions surfaced before the write lands [why: DECISIONS.md D-0107]
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
- `tools.compaction_seed` — the compaction guardrail: reports which of three states a project is in (the half-configured one named distinctly), and inserts the missing half under the doctrine's narrow consented exception, refusing any write that would alter an existing line (INC-209 KH-1)
- `tools.conformance_checks` — the written conformance check: a declared convention's typed check line in the FRIDAY-CONFORMANCE block beside the measured bars, four closed kinds, self-excluding anchor (INC-105 FR-105.2/FR-105.3) [why: DECISIONS.md D-1047]
- `tools.conformance_envelope_check` — the sibling envelope's checker: the judge's written answers to rule breaches, closed answer vocabulary, every answer anchored to the rule it reasoned from (INC-105 FR-105.7) [why: DECISIONS.md D-1050]
- `tools.conformance_sweep` — layer-1 mechanical full recall over the written checks and the switched-on baseline invariants; counts and never judges, three silences named as themselves (INC-105 FR-105.5/FR-105.8/FR-105.9) [why: DECISIONS.md D-1049]
- `tools.consumer_scan` — the two mechanical enumeration sources over one walk: declared citations + exact-name match, value-blind evidence, the too-common bound stated rather than truncated (INC-104 FR-104.2, OQ-104.3) [why: DECISIONS.md D-1040]
- `tools.decisions_append` — the shared append CLI, both capture channels [why: DECISIONS.md D-0007]
- `tools.design_contract_check` — verifies a locked design contract is unedited absent a decision
- `tools.dispatch_briefing_check` — report-only: every recorded dispatch accounted for against its saved briefing's typed line; scopes off the journal so the orchestrator's own lane-entry note is never mistaken for a briefing (INC-208 KH-1)
- `tools.dispatch_liveness_check` — the role-orphan + phantom-contract checker — a role file that exists must be spawned somewhere or carry a declared exception [why: DECISIONS.md D-0121]
- `tools.doc_gate` — the document-gate family: build-feeding docs consumed + consumer-cited (S-4)
- `tools.doc_probe_scope` — the document-truth probe's record-set derivation: roles' declared outputs + the front page, split against the project's own read bar, with every unresolvable declaration named in its honest bucket (missing / patterned / out-of-tree / unreadable) [why: INC-101 FR-101.3/FR-101.4, D-1020 era]
- `tools.experiment_request` — the experiment runner's closed menu — four moves, closed key set, site-relative paths; a command is structurally unrepresentable [why: DECISIONS.md D-0122]
- `tools.experiment_run` — the executor: does exactly the planned calls, re-checks egress per call, redacts the credential, never starts a process [why: DECISIONS.md D-0122/D-0124]
- `tools.findings_brief_check` — findings-brief grammar gate — concrete evidence required above informational
- `tools.foundation_check` — the foundation-unit interim-gate logic
- `tools.friday_consent` — the PM's recorded yes for one experiment batch: fingerprint over the request's exact bytes, spent by the run it authorises [why: DECISIONS.md D-0134/D-0135]
- `tools.friday_substrate` — sole owner of the .friday path + git-common-dir root resolution (record-owning modules write their own records) [why: DECISIONS.md D-0003/D-0135]
- `tools.gen_command_index` — single-field -> generated README table over both lane homes, commands/*.md line-1 openers + lane-skill frontmatter, with shadow detection (escapes table-breaking chars)
- `tools.graph_freshness_check` — computes 'N commits behind' for the code graph (guard #8 logic)
- `tools.graph_query` — the one explore seam: routes to graphify or friday's IR, EXTRACTED-only (FR-70)
- `tools.graph_refresh` — refreshes + stamps the code graph AFTER the docs (FR-71)
- `tools.handoff_attest` — records an operator gate attestation; refuses secret-shaped notes (FR-84)
- `tools.handoff_gate` — the handoff completion gate: gates need the pm channel + restore evidence (FR-85)
- `tools.handoff_package_check` — verifies the handoff package's required members + who-can-do tags
- `tools.import_cycles` — import-cycle detection as a strongly-connected-component walk over the IR's own edge array — deferred edges are evidence, absence is out-of-reach (INC-105 FR-105.6) [why: DECISIONS.md D-1048]
- `tools.lane` — the lane-sentinel CLI (open / clear, O_EXCL atomic claim) [why: DECISIONS.md D-0023]
- `tools.loose_deferral_envelope_check` — validates — and write-through lands — the deep clean's loose-deferral envelope against its contract (INC-107 FR-107.10) [why: DECISIONS.md D-1072]
- `tools.loose_deferral_scan` — the loose-deferral scan: candidate deferrals in comment blocks, generous vocabulary on flattened text, unreached files named (INC-107 FR-107.1) [why: DECISIONS.md D-1069]
- `tools.loose_deferrals` — the answered set: single writer for docs/LOOSE-DEFERRALS.md, the flatten-stable candidate identity, the recognition split, the presentation-cap read (INC-107 FR-107.6) [why: DECISIONS.md D-1070, D-1072]
- `tools.maintainability_envelope_check` — validates the judge's typed disposition envelope against its contract [why: DECISIONS.md D-0120]
- `tools.maintainability_gate_check` — the gate's decision logic — measured breaches against the envelope's dispositions [why: DECISIONS.md D-0119]
- `tools.maintainability_measure` — the layer-1 measurer: complexity, size, duplication against a project's declared bars [why: DECISIONS.md D-0119]
- `tools.open_risks_check` — the open-risk-row gate logic
- `tools.ops_battery` — the operations battery's verdict record: one typed line per row, three distinct states, drill expiry against real history (INC-102 FR-102.3/FR-102.4) [why: DECISIONS.md D-1027, D-1028]
- `tools.oracle_edit_check` — guard #9 logic: oracle edits need a structured override-grant
- `tools.parked` — the PARKED ledger: single writer for deferred-idea rows and their three exit routes [why: DECISIONS.md D-0108]
- `tools.profile_check` — validates the profile write path
- `tools.proposal_pipeline` — the single pipeline authority: stage vocabulary, by-name lookup, fenced-header read/write, the mover [why: DECISIONS.md D-0156]
- `tools.proposal_pipeline_check` — six-class ledger drift checker over the mover's own core; blocking at the feature close, reporting at reconcile [why: DECISIONS.md D-0156/D-0158]
- `tools.receipt` — tree-hash receipts backstop (hooks fail open; this does not)
- `tools.reckoning` — the consumer reckoning record's one writer: closed answer set locked to the contract, the clearance rule enforced at the only door, derived not-covered, oldest-whole-change archival (INC-104 FR-104.4/104.5/104.8) [why: DECISIONS.md D-1039/D-1045]
- `tools.reckoning_sweep` — the deep clean's consumer catch-up: changes since the state record's last-verified stamp carrying no reckoning record, closed outcome set (INC-104 FR-104.9) [why: DECISIONS.md D-1041]
- `tools.research_orphan_check` — scans docs/research/** for a `consumer:` tag on every brief (S-4)
- `tools.sanitized_mirror` — the reviewer-sandbox sanitized mirror (invisible-char strip; S-3)
- `tools.seam_handoff` — the seam-handoff build-model primitive (NOT /friday:handoff)
- `tools.scheduled_jobs` — the committed job list: photograph → confirm → diff, value-blind by refusal (INC-102 FR-102.7) [why: DECISIONS.md D-1029]
- `tools.secret_names` — enumerates env-var NAMES only from example dotenv / source; never opens a real .env (FR-84)
- `tools.secret_posture_check` — value-blind secret-store posture: declaration, tracked value files, ignore class — opens only CLAUDE.md (INC-204 FR-204.3)
- `tools.sensitive_store_scan` — the deep clean's store enumeration: exact schema patterns + the IR's data_models, every unread/unparsed storage named, compare() the catch-up's worklist (INC-108 FR-108.13) [why: DECISIONS.md D-1077]
- `tools.sensitivity_declaration` — single writer for docs/SENSITIVITY.md: the treatment-set declaration, the floor, the shared-copy rule, requirements_check (INC-108 FR-108.5) [why: DECISIONS.md D-1076, D-1077]
- `tools.session_heartbeat` — per-session liveness ticker; a stale ts IS the crash signal
- `tools.skill_standard_check` — the two-kinds skill floor over skills/*/SKILL.md: FR-81 strict standard for noticing-skills, FR-2.5 lighter floor for lane-skills
- `tools.spawn_grant_check` — every grant-binding role is dispatched un-named, so its tools list actually binds [why: DECISIONS.md D-0132]
- `tools.spawn_telemetry` — THE spawn / accept / done telemetry primitive
- `tools.spec_id_strip_check` — ship-gate: flags surviving FR- / US- / S-n tags on user surfaces, incl. bundled files inside lane folders via the surface-aware --skills-dir mode [why: DECISIONS.md D-0044]
- `tools.standards_deviations` — the PM-ratified standards-deviation ledger writer [why: DECISIONS.md D-0119/D-0120]
- `tools.state_advisory_check` — the judgement half of the state-advisory + due-signal hooks (policy: docs/contracts/state-record.md)
- `tools.state_record` — the PROP-028 dirty bit's ONE writer: --mark stale|verified on a closed record [why: DECISIONS.md D-0106]
- `tools.taglines` — typed tag-line grammar family, empty-case-tested
- `tools.trail_check` — the change-trail grammar checker (FR-62 / FR-65)
- `tools.usage_report` — journal usage-event roll-up (NFR-2 cost visibility)
- `tools.verify_claims` — FRIDAY-CLAIMS drift detector (string-mechanical)
- `tools.verify_coverage` — TSOW requirement-ID coverage closure; deferrals cite a D-NNNN (K7)
- `tools.verify_generated` — verifies the generated doc set is present + provenance-stamped
- `tools.verify_review_format` — FRIDAY-REVIEW envelope checks + canonical-file provenance
- `tools.verify_spawn_coverage` — anti-orphan-spawn coverage check over both lane homes (commands/ + lane-skills in skills/)
- `tools.verify_state` — K0-K8 state verifier (Appendix A.3; corpus-driven)
- `tools.watcher_coverage` — counts the project's package ecosystems from its own tree and compares them against the dependabot config's declared watchers, gaps named per ecosystem (INC-103 FR-103.1) [why: DECISIONS.md D-1034]
- `tools.worktree_create_check` — the WorktreeCreate provisioner logic (returns the substrate path)

**tools/doc-index/ — the friday-docs MCP retrieval triad (never RAG)**

- `tools.doc-index.mdparse` — exact-after-normalization heading matcher [why: DECISIONS.md D-0006]
- `tools.doc-index.registry` — sync-on-query sqlite index (documents / decisions / actions)
- `tools.doc-index.server` — friday-docs MCP: live-parse triad + advisory aggregates (never RAG)

**tools/experiments/ — the friday-experiments MCP door (the runner's only reach)**

- `tools.experiments.server` — plan/run over one batch id (plus an argument-less `status`); derives the request, the root and the run-record path from the consent record so none of them is caller-supplied. The runner is granted only `plan` and `run` — the door declares three tools, its reach is two [why: DECISIONS.md D-0134/D-0138]

**tools/doc-synthesis/ — the extract -> synthesize -> diff loop**

- `tools.doc-synthesis.extract_architecture` — the A.1 IR extractor (stdlib ast, pure static)
- `tools.doc-synthesis.extract_js` — the JS/TS side of the same pass: imports (tsconfig-alias aware, refusal on ambiguity), Next/Express routes, exported components — merged into the one IR, never executing project code (INC-207)
- `tools.doc-synthesis.synthesis_diff` — the extractor-vs-synthesis QA oracle (this file's judge)

**tools/codex-adapter/ — the fail-closed Codex port**

- `tools.codex-adapter.state_stop_gate` — fail-closed Codex port of the K-gate (quota-continuity divergence)

**tools/visual-companion/ — the local stdlib discovery companion**

- `tools.visual-companion.companion_server` — zero-dep stdlib companion server + CompanionState (US-15)
- `tools.visual-companion.offer` — the JIT companion offer / route logic (FR-76 offer-never-enter)

**tests/ — the verification mirror (pytest; every grammar tests its empty case)**

- `tests.conftest` — pytest configuration + shared fixtures
- `tests.guardkit` — shared guard-test harness (1 positive control + fail-open controls per blocking guard)
- `tests.test_adopt_parity` — content pins: adopt reaches greenfield parity (D-0109/D-0149)
- `tests.test_batch_edit` — regression pins: the batch editor's destruction cases (multi/zero-match, missing file, empty list, dry-run, nothing-written-on-refusal)
- `tests.test_bug_001_verify_claims_stack` — regression pins: BUG-001 stack-claim verification
- `tests.test_bug_002_bug_close_gate_pause` — regression pins: BUG-002 bug-lane arm point
- `tests.test_bug_003_check_readme_sync` — regression pins: BUG-003 README-table sync ownership (`--check` detects, hook resplices via `--write`, D-0096)
- `tests.test_bug_004_decision_capture_multiquestion` — regression: per-question decision capture, all answers kept (BUG-004)
- `tests.test_capture_ask_mode` — the decision-ask capture on the record owner's CLI side: ask-shape captures pm-ratified, ordinary dialogs never, floors force one-way (D-1084 follow-on)
- `tests.test_capture_integrity` — regression pins: capture_integrity
- `tests.test_committed_test_check` — regression pins: committed test check
- `tests.test_compaction_capture` — regression pins: compaction capture doors
- `tests.test_companion_offer` — regression pins: companion offer
- `tests.test_companion_server` — regression pins: companion server
- `tests.test_conformance_baseline` — the shipped baseline catalog is a deliverable of typed lines and can rot like any record: malformed lines and non-compiling patterns named, never silently skipped (INC-105 FR-105.4, OQ-105.2)
- `tests.test_conformance_checks` — the written check's typed line: grammar, the add/list CLI, the self-excluding anchor, empty case (INC-105 FR-105.2/FR-105.3)
- `tests.test_conformance_envelope_check` — the sibling envelope: closed answer vocabulary, every answer anchored to its written rule, refusals both directions (INC-105 FR-105.7)
- `tests.test_conformance_sweep` — the sweep counts and never judges; the three named silences stay honest (INC-105 FR-105.5/FR-105.8/FR-105.9)
- `tests.test_consumer_scan` — regression pins: the mechanical needles, value-blindness over a planted value, the too-common bound, stated unrunnable sources (INC-104)
- `tests.test_decision_lanes` — regression pins: decision-id lane enforcement, incl. the D-1007 cross-lane incident byte-exact (D-0154)
- `tests.test_decisions` — regression pins: decisions
- `tests.test_doc_gate` — regression pins: doc gate
- `tests.test_doc_synthesis` — regression pins: doc synthesis
- `tests.test_due_event_arm` — the due signal's second arm: trail-counted closes, strictly-later boundary, could-not-count never zero, malformed per arm, one message (INC-109 FR-109.1/109.2/109.11)
- `tests.test_due_signals` — regression pins: due-signal checker modes
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
- `tests.test_guard_maintainability` — the maintainability gate's four fail-open fault modes
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
- `tests.test_import_cycles` — the cycle walk over the extracted IR: strongly-connected components, deferred-edge evidence, friday's own convicted cycle pinned (INC-105 FR-105.6)
- `tests.test_inc008_deviations` — the deviation ledger's grammar and its empty case
- `tests.test_inc008_envelope` — the disposition envelope's grammar and its empty case
- `tests.test_bug_005_increment_gate_authoring` — the increment gate fires at consumption, not at authoring [why: DECISIONS.md D-0133]
- `tests.test_inc008_gate` — gate verdicts over measured breaches and their dispositions
- `tests.test_inc008_maintainability_claim` — the declared-bar claim vocabulary and its well-formedness
- `tests.test_inc008_measurer` — the three metrics the measurer really computes
- `tests.test_inc200_coverage_channel` — the coverage ledger's verifier channel — additive, weaker-by-default
- `tests.test_inc200_dispatch_liveness` — role-orphan and phantom-contract catches, both empty cases, and the real tree
- `tests.test_inc200_state_advisory` — regression pins: state advisory + dirty-bit wiring
- `tests.test_inc201_consent_record` — the consent record: unforgeable, byte-bound, one yes one run
- `tests.test_inc201_experiments_server` — the two tools take one batch id and refuse everything else
- `tests.test_inc201_runner_grant` — the runner's frontmatter holds no shell and no write
- `tests.test_inc202_checker` — the pipeline checker's finding classes + empty cases (KH-6)
- `tests.test_inc101_doc_probe_scope` — the record set is derived not listed; the bar splits and the unread buckets stay honest, unreadable included (FR-101.3/FR-101.4, AC-101.3/AC-101.4)
- `tests.test_inc101_handover_gate` — the reconcile gate refuses a bare confirmation naming both real answers; both accepts roundtrip (FR-101.7, AC-101.6)
- `tests.test_inc203_dispatch_workshop` — the orphan-detector sees `.claude/agents/` and its `.claude/skills/` callers; mention-without-model still orphans (AC-203.6); membership updated at the INC-101 promotion (D-1021)
- `tests.test_inc202_frozen_body` — the D3 freeze line enforced: link-moment baseline, --follow across stage moves (AC-202.11)
- `tests.test_inc202_header_grammar` — KH-1 measured: the fenced header parses through taglines unchanged (AC-202.1)
- `tests.test_inc202_mover` — both-halves-or-neither moves; evidence/reason/increment gate refusals
- `tests.test_inc204_keys_gate` — the single bite: keys refuses on tracked value files, proceeds under accepted-risk (FR-204.5/D4)
- `tests.test_inc204_posture_check` — the value-blind checker: grammar states, open-set proof, verdict semantics (FR-204.3, KH-1)
- `tests.test_inc207_extract_js` — the JS pass, fixture by fixture: path-with-extension identity, resolution refusals, routes, components, every empty case (AC-207.7)
- `tests.test_inc207_size_rule` — the inventory size rule: pointer sentinel accepted only above the declared threshold; below it, today's contract character for character (FR-207.3)
- `tests.test_inc208_dispatch_check` — the dispatch checker's two defect classes, its unchecked non-verdict, the cross-session and instance-suffixed drawer cases, and fail-open (AC-208.1)
- `tests.test_inc209_decline` — a recorded decline silences every later retrofit door, both directions, on a project with no decision record yet (AC-209.4)
- `tests.test_inc209_doctrine` — the scaffold doctrine's wording pinned: standard seed, the values single-homed, the exception scoped inside never-clobber, and the pin proven to fail when demoted (AC-209.7)
- `tests.test_inc209_seed` — the make-or-break round: consented insertion byte for byte, refusal without consent, the planted reformatting merge, and the check's three states (AC-209.1, AC-209.2, AC-209.3)
- `tests.test_inc209_surfaces` — every retrofit door wired and citing the doctrine, init deliberately not, the announcement's four pieces, and no surface restating a value (FR-209.2, FR-209.5)
- `tests.test_ops_battery` — the verdict record: grammar refusals, the three states, the row-key lock to the contract table, expiry both directions on real histories (INC-102 FR-102.3/FR-102.4, AC-102.3/AC-102.7)
- `tests.test_loose_deferral_envelope` — the envelope checker: truthful count, malformed candidate errors, the home answer's three ruled words, the empty case's Scanned section, write-through landing only valid (INC-107 FR-107.10)
- `tests.test_loose_deferral_scan` — the scan: block unit, quote-parity, wrapped-phrase matching, value masking, unread/unparsed named (INC-107 FR-107.1/107.2/107.8)
- `tests.test_loose_deferrals` — the answered set: KH-2's three-way identity at unit level, counted recognition, the closed answer vocabulary, the cap bar (INC-107 FR-107.6/107.7)
- `tests.test_parked_ledger` — regression pins: parked
- `tests.test_scheduled_jobs` — the job list: photograph/confirm/diff both directions, the value-blind refusal per field (INC-102 FR-102.7, AC-102.6/AC-102.10)
- `tests.test_session_heartbeat` — regression pins: session_heartbeat
- `tests.test_spawn_grant_check` — the un-named dispatch rule over every grant-binding role
- `tests.test_standards_deviations` — the deviations ledger widened to the rule-shaped entry beside the number-shaped ones (INC-105 FR-105.10)
- `tests.test_state_record_dirty_bit` — regression pins: state_record
- `tests.test_usage_telemetry` — regression pins: usage_telemetry
- `tests.test_verify_review_format_dispositions` — review-format verdicts against the disposition ledger
- `tests.test_inc200_experiment_e2e` — the end-to-end run against a deliberately-broken toy target
- `tests.test_inc200_experiment_request` — the closed menu attacked adversarially — 14 hostile requests, all unrepresentable
- `tests.test_lane_cli` — regression pins: lane cli
- `tests.test_lane_open_helper` — regression pins: lane open helper
- `tests.test_mdparse` — regression pins: mdparse
- `tests.test_reckoning` — regression pins: the reckoning record — vocabulary lock to the contract, both clearance halves, derived not-covered, person states, has() both directions, archival discipline, empty case, malformed preservation, the anchor rule (INC-104)
- `tests.test_reckoning_sweep` — regression pins: the catch-up sweep — outcome vocabulary locked to the contract, both AC-104.9 directions, anchor rules, record-only commits excluded (INC-104)
- `tests.test_registry` — regression pins: registry
- `tests.test_review_format_interim` — regression pins: review format interim
- `tests.test_sanitized_mirror` — regression pins: sanitized mirror
- `tests.test_recurrence_register` — regression pins: the recurrence register's typed-line grammar, the widened bundle verdict, and both empty cases (INC-004, renamed and widened INC-208)
- `tests.test_seam_handoff` — the seam-handoff record's expiry and cross-check
- `tests.test_secret_names` — regression pins: secret names
- `tests.test_sensitive_store_scan` — the enumeration: schema patterns + IR models, unparsed/unread named, data files never opened, compare's two directions (INC-108 FR-108.13)
- `tests.test_sensitivity_declaration` — the record: blank=finding, the floor as a floor, shared copy answered once, empty case dated, malformed kept (INC-108 FR-108.2/108.5/108.8)
- `tests.test_sensitivity_requirements` — the requirement check: dangling id, declaration-only incomplete, all-not-applicable owes nothing, unread oracle named (INC-108 FR-108.4)
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
- `tests.test_watcher_coverage` — regression pins: tree-side ecosystem detection against real fixture trees, config-side both config spellings, the schema-enum and vendor-provenance locks (INC-103)

## Component diagram

Every module and import edge the extractor found, grouped by subsystem. Solid
edges are module-level imports; `-.->|deferred|` marks a function-local import
(the fail-open pattern — a broken dependency degrades a feature, never the
session). The graph is dense by design — the tests/ mirror carries roughly
half the edges, and the current counts live in the generated pair's own
header (`docs/architecture/generated/dependency-graph.md`), never here (a
figure in prose rots — INC-203 D2, and the 2026-08-03 probe run caught this
sentence's previous figures doing exactly that); read it through the
layering below, not left-to-right.

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
        hooks_due_signal["hooks.due_signal"]
        hooks_elicitation_journal["hooks.elicitation_journal"]
        hooks_foundation_gate["hooks.foundation_gate"]
        hooks_graph_freshness_guard["hooks.graph_freshness_guard"]
        hooks_lane_close_gate["hooks.lane_close_gate"]
        hooks_maintainability_gate["hooks.maintainability_gate"]
        hooks_open_risks_guard["hooks.open_risks_guard"]
        hooks_oracle_edit_guard["hooks.oracle_edit_guard"]
        hooks_profile_guard["hooks.profile_guard"]
        hooks_research_orphan_warn["hooks.research_orphan_warn"]
        hooks_review_format_sentinel["hooks.review_format_sentinel"]
        hooks_review_format_stop_gate["hooks.review_format_stop_gate"]
        hooks_session_lifecycle["hooks.session_lifecycle"]
        hooks_setup_selfcheck["hooks.setup_selfcheck"]
        hooks_spec_write_guard["hooks.spec_write_guard"]
        hooks_state_advisory["hooks.state_advisory"]
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
        tools_compaction_seed["tools.compaction_seed"]
        tools_conformance_checks["tools.conformance_checks"]
        tools_conformance_envelope_check["tools.conformance_envelope_check"]
        tools_conformance_sweep["tools.conformance_sweep"]
        tools_consumer_scan["tools.consumer_scan"]
        tools_decisions_append["tools.decisions_append"]
        tools_design_contract_check["tools.design_contract_check"]
        tools_dispatch_briefing_check["tools.dispatch_briefing_check"]
        tools_dispatch_liveness_check["tools.dispatch_liveness_check"]
        tools_doc_gate["tools.doc_gate"]
        tools_doc_probe_scope["tools.doc_probe_scope"]
        tools_experiment_request["tools.experiment_request"]
        tools_experiment_run["tools.experiment_run"]
        tools_findings_brief_check["tools.findings_brief_check"]
        tools_foundation_check["tools.foundation_check"]
        tools_friday_consent["tools.friday_consent"]
        tools_friday_substrate["tools.friday_substrate"]
        tools_gen_command_index["tools.gen_command_index"]
        tools_graph_freshness_check["tools.graph_freshness_check"]
        tools_graph_query["tools.graph_query"]
        tools_graph_refresh["tools.graph_refresh"]
        tools_handoff_attest["tools.handoff_attest"]
        tools_handoff_gate["tools.handoff_gate"]
        tools_handoff_package_check["tools.handoff_package_check"]
        tools_import_cycles["tools.import_cycles"]
        tools_lane["tools.lane"]
        tools_loose_deferral_envelope_check["tools.loose_deferral_envelope_check"]
        tools_loose_deferral_scan["tools.loose_deferral_scan"]
        tools_loose_deferrals["tools.loose_deferrals"]
        tools_maintainability_envelope_check["tools.maintainability_envelope_check"]
        tools_maintainability_gate_check["tools.maintainability_gate_check"]
        tools_maintainability_measure["tools.maintainability_measure"]
        tools_open_risks_check["tools.open_risks_check"]
        tools_ops_battery["tools.ops_battery"]
        tools_oracle_edit_check["tools.oracle_edit_check"]
        tools_scheduled_jobs["tools.scheduled_jobs"]
        tools_watcher_coverage["tools.watcher_coverage"]
        tools_parked["tools.parked"]
        tools_profile_check["tools.profile_check"]
        tools_proposal_pipeline["tools.proposal_pipeline"]
        tools_proposal_pipeline_check["tools.proposal_pipeline_check"]
        tools_receipt["tools.receipt"]
        tools_reckoning["tools.reckoning"]
        tools_reckoning_sweep["tools.reckoning_sweep"]
        tools_research_orphan_check["tools.research_orphan_check"]
        tools_sanitized_mirror["tools.sanitized_mirror"]
        tools_seam_handoff["tools.seam_handoff"]
        tools_secret_names["tools.secret_names"]
        tools_secret_posture_check["tools.secret_posture_check"]
        tools_sensitive_store_scan["tools.sensitive_store_scan"]
        tools_sensitivity_declaration["tools.sensitivity_declaration"]
        tools_session_heartbeat["tools.session_heartbeat"]
        tools_skill_standard_check["tools.skill_standard_check"]
        tools_spawn_grant_check["tools.spawn_grant_check"]
        tools_spawn_telemetry["tools.spawn_telemetry"]
        tools_spec_id_strip_check["tools.spec_id_strip_check"]
        tools_standards_deviations["tools.standards_deviations"]
        tools_state_advisory_check["tools.state_advisory_check"]
        tools_state_record["tools.state_record"]
        tools_taglines["tools.taglines"]
        tools_trail_check["tools.trail_check"]
        tools_usage_report["tools.usage_report"]
        tools_verify_claims["tools.verify_claims"]
        tools_verify_coverage["tools.verify_coverage"]
        tools_verify_generated["tools.verify_generated"]
        tools_verify_review_format["tools.verify_review_format"]
        tools_verify_spawn_coverage["tools.verify_spawn_coverage"]
        tools_verify_state["tools.verify_state"]
        tools_watcher_coverage["tools.watcher_coverage"]
        tools_worktree_create_check["tools.worktree_create_check"]
    end
    subgraph sg_docidx [tools/doc-index/]
        tools_doc_index_mdparse["tools.doc-index.mdparse"]
        tools_doc_index_registry["tools.doc-index.registry"]
        tools_doc_index_server["tools.doc-index.server"]
    end
    subgraph sg_experiments [tools/experiments/]
        tools_experiments_server["tools.experiments.server"]
    end
    subgraph sg_docsyn [tools/doc-synthesis/]
        tools_doc_synthesis_extract_architecture["tools.doc-synthesis.extract_architecture"]
        tools_doc_synthesis_extract_js["tools.doc-synthesis.extract_js"]
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
        tests_test_adopt_parity["tests.test_adopt_parity"]
        tests_test_batch_edit["tests.test_batch_edit"]
        tests_test_bug_001_verify_claims_stack["tests.test_bug_001_verify_claims_stack"]
        tests_test_bug_002_bug_close_gate_pause["tests.test_bug_002_bug_close_gate_pause"]
        tests_test_bug_003_check_readme_sync["tests.test_bug_003_check_readme_sync"]
        tests_test_bug_004_decision_capture_multiquestion["tests.test_bug_004_decision_capture_multiquestion"]
        tests_test_capture_ask_mode["tests.test_capture_ask_mode"]
        tests_test_capture_integrity["tests.test_capture_integrity"]
        tests_test_committed_test_check["tests.test_committed_test_check"]
        tests_test_compaction_capture["tests.test_compaction_capture"]
        tests_test_companion_offer["tests.test_companion_offer"]
        tests_test_companion_server["tests.test_companion_server"]
        tests_test_conformance_baseline["tests.test_conformance_baseline"]
        tests_test_conformance_checks["tests.test_conformance_checks"]
        tests_test_conformance_envelope_check["tests.test_conformance_envelope_check"]
        tests_test_conformance_sweep["tests.test_conformance_sweep"]
        tests_test_consumer_scan["tests.test_consumer_scan"]
        tests_test_decision_lanes["tests.test_decision_lanes"]
        tests_test_decisions["tests.test_decisions"]
        tests_test_doc_gate["tests.test_doc_gate"]
        tests_test_doc_synthesis["tests.test_doc_synthesis"]
        tests_test_due_event_arm["tests.test_due_event_arm"]
        tests_test_due_signals["tests.test_due_signals"]
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
        tests_test_guard_maintainability["tests.test_guard_maintainability"]
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
        tests_test_import_cycles["tests.test_import_cycles"]
        tests_test_inc008_deviations["tests.test_inc008_deviations"]
        tests_test_inc008_envelope["tests.test_inc008_envelope"]
        tests_test_inc101_doc_probe_scope["tests.test_inc101_doc_probe_scope"]
        tests_test_bug_005_increment_gate_authoring["tests.test_bug_005_increment_gate_authoring"]
        tests_test_inc101_handover_gate["tests.test_inc101_handover_gate"]
        tests_test_inc200_state_advisory["tests.test_inc200_state_advisory"]
        tests_test_inc201_consent_record["tests.test_inc201_consent_record"]
        tests_test_inc201_experiments_server["tests.test_inc201_experiments_server"]
        tests_test_inc201_runner_grant["tests.test_inc201_runner_grant"]
        tests_test_inc202_checker["tests.test_inc202_checker"]
        tests_test_inc203_dispatch_workshop["tests.test_inc203_dispatch_workshop"]
        tests_test_inc202_frozen_body["tests.test_inc202_frozen_body"]
        tests_test_inc202_header_grammar["tests.test_inc202_header_grammar"]
        tests_test_inc202_mover["tests.test_inc202_mover"]
        tests_test_inc204_keys_gate["tests.test_inc204_keys_gate"]
        tests_test_inc204_posture_check["tests.test_inc204_posture_check"]
        tests_test_inc207_extract_js["tests.test_inc207_extract_js"]
        tests_test_inc207_size_rule["tests.test_inc207_size_rule"]
        tests_test_inc208_dispatch_check["tests.test_inc208_dispatch_check"]
        tests_test_inc209_decline["tests.test_inc209_decline"]
        tests_test_inc209_doctrine["tests.test_inc209_doctrine"]
        tests_test_inc209_seed["tests.test_inc209_seed"]
        tests_test_inc209_surfaces["tests.test_inc209_surfaces"]
        tests_test_ops_battery["tests.test_ops_battery"]
        tests_test_loose_deferral_envelope["tests.test_loose_deferral_envelope"]
        tests_test_loose_deferral_scan["tests.test_loose_deferral_scan"]
        tests_test_loose_deferrals["tests.test_loose_deferrals"]
        tests_test_parked_ledger["tests.test_parked_ledger"]
        tests_test_scheduled_jobs["tests.test_scheduled_jobs"]
        tests_test_session_heartbeat["tests.test_session_heartbeat"]
        tests_test_spawn_grant_check["tests.test_spawn_grant_check"]
        tests_test_standards_deviations["tests.test_standards_deviations"]
        tests_test_state_record_dirty_bit["tests.test_state_record_dirty_bit"]
        tests_test_usage_telemetry["tests.test_usage_telemetry"]
        tests_test_verify_review_format_dispositions["tests.test_verify_review_format_dispositions"]
        tests_test_inc008_gate["tests.test_inc008_gate"]
        tests_test_inc008_maintainability_claim["tests.test_inc008_maintainability_claim"]
        tests_test_inc008_measurer["tests.test_inc008_measurer"]
        tests_test_inc200_coverage_channel["tests.test_inc200_coverage_channel"]
        tests_test_inc200_dispatch_liveness["tests.test_inc200_dispatch_liveness"]
        tests_test_inc200_experiment_e2e["tests.test_inc200_experiment_e2e"]
        tests_test_inc200_experiment_request["tests.test_inc200_experiment_request"]
        tests_test_lane_cli["tests.test_lane_cli"]
        tests_test_lane_open_helper["tests.test_lane_open_helper"]
        tests_test_mdparse["tests.test_mdparse"]
        tests_test_reckoning["tests.test_reckoning"]
        tests_test_reckoning_sweep["tests.test_reckoning_sweep"]
        tests_test_registry["tests.test_registry"]
        tests_test_review_format_interim["tests.test_review_format_interim"]
        tests_test_sanitized_mirror["tests.test_sanitized_mirror"]
        tests_test_recurrence_register["tests.test_recurrence_register"]
        tests_test_seam_handoff["tests.test_seam_handoff"]
        tests_test_secret_names["tests.test_secret_names"]
        tests_test_sensitive_store_scan["tests.test_sensitive_store_scan"]
        tests_test_sensitivity_declaration["tests.test_sensitivity_declaration"]
        tests_test_sensitivity_requirements["tests.test_sensitivity_requirements"]
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
        tests_test_watcher_coverage["tests.test_watcher_coverage"]
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
    hooks_design_contract_guard --> hooks__guard
    hooks_design_contract_guard --> hooks__hookutil
    hooks_doc_consumption_guard --> hooks__guard
    hooks_doc_consumption_guard --> hooks__hookutil
    hooks_due_signal --> hooks__guard
    hooks_due_signal --> hooks__hookutil
    hooks_elicitation_journal --> hooks__hookutil
    hooks_foundation_gate --> hooks__guard
    hooks_foundation_gate --> hooks__hookutil
    hooks_graph_freshness_guard --> hooks__guard
    hooks_graph_freshness_guard --> hooks__hookutil
    hooks_lane_close_gate --> hooks__guard
    hooks_lane_close_gate --> hooks__hookutil
    hooks_maintainability_gate --> hooks__guard
    hooks_maintainability_gate --> hooks__hookutil
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
    hooks_state_advisory --> hooks__guard
    hooks_state_advisory --> hooks__hookutil
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
    tests_test_bug_004_decision_capture_multiquestion --> tools_decisions
    tests_test_capture_ask_mode --> tools_decisions
    tests_test_capture_integrity --> tools_capture_integrity
    tests_test_capture_integrity --> tools_decisions
    tests_test_committed_test_check --> tools_committed_test_check
    tests_test_compaction_capture --> tools_friday_substrate
    tests_test_companion_offer --> tests_guardkit
    tests_test_companion_offer --> tools_visual_companion_offer
    tests_test_companion_server --> tests_guardkit
    tests_test_companion_server --> tools_visual_companion_companion_server
    tests_test_conformance_baseline --> tools_conformance_sweep
    tests_test_conformance_checks --> tools_conformance_checks
    tests_test_conformance_envelope_check --> tools_conformance_envelope_check
    tests_test_conformance_sweep --> tools_conformance_sweep
    tests_test_consumer_scan --> tools_consumer_scan
    tests_test_consumer_scan --> tools_reckoning
    tests_test_reckoning --> tools_reckoning
    tests_test_reckoning_sweep --> tools_reckoning
    tests_test_reckoning_sweep --> tools_reckoning_sweep
    tests_test_decision_lanes --> tools_decisions
    tests_test_decisions --> tools_decisions
    tests_test_doc_gate --> hooks__guard
    tests_test_doc_gate --> tools_doc_gate
    tests_test_doc_synthesis --> tools_doc_synthesis_extract_architecture
    tests_test_doc_synthesis --> tools_doc_synthesis_synthesis_diff
    tests_test_due_event_arm --> tools_state_advisory_check
    tests_test_due_signals --> tools_state_advisory_check
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
    tests_test_guard_maintainability -.->|deferred| hooks_maintainability_gate
    tests_test_guard_maintainability --> tests_guardkit
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
    tests_test_inc101_handover_gate --> tools_handoff_attest
    tests_test_inc101_handover_gate --> tools_handoff_gate
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
    tests_test_import_cycles --> tools_import_cycles
    tests_test_inc008_deviations --> tools_standards_deviations
    tests_test_inc008_envelope -.->|deferred| tools_friday_substrate
    tests_test_inc008_envelope --> tools_maintainability_envelope_check
    tests_test_inc008_gate --> tools_maintainability_gate_check
    tests_test_inc008_maintainability_claim --> tools_taglines
    tests_test_inc008_maintainability_claim --> tools_verify_claims
    tests_test_inc008_measurer --> tools_maintainability_measure
    tests_test_inc200_coverage_channel --> tools_verify_coverage
    tests_test_inc200_dispatch_liveness --> tools_dispatch_liveness_check
    tests_test_inc203_dispatch_workshop --> tools_dispatch_liveness_check
    tests_test_inc200_experiment_e2e --> tools_experiment_request
    tests_test_inc200_experiment_e2e --> tools_experiment_run
    tests_test_bug_005_increment_gate_authoring --> tests_guardkit
    tests_test_inc200_experiment_e2e --> tools_friday_consent
    tests_test_inc200_state_advisory --> tools_state_advisory_check
    tests_test_inc200_state_advisory --> tools_state_record
    tests_test_inc201_consent_record --> tools_friday_consent
    tests_test_inc201_consent_record --> tools_taglines
    tests_test_inc201_experiments_server --> tools_experiment_run
    tests_test_inc201_experiments_server --> tools_friday_consent
    tests_test_inc202_checker --> tools_proposal_pipeline
    tests_test_inc202_checker --> tools_proposal_pipeline_check
    tests_test_inc202_frozen_body --> tools_proposal_pipeline
    tests_test_inc202_frozen_body --> tools_proposal_pipeline_check
    tests_test_inc202_header_grammar --> tools_taglines
    tests_test_inc202_mover --> tools_proposal_pipeline
    tests_test_inc204_keys_gate --> tools_handoff_attest
    tests_test_inc204_keys_gate --> tools_handoff_gate
    tests_test_inc204_posture_check --> tools_secret_names
    tests_test_inc204_posture_check --> tools_secret_posture_check
    tests_test_inc208_dispatch_check --> tools_dispatch_briefing_check
    tests_test_inc209_decline --> tools_compaction_seed
    tests_test_inc209_seed --> tools_compaction_seed
    tests_test_inc209_surfaces --> tools_compaction_seed
    tools_dispatch_briefing_check --> tools_friday_substrate
    tools_dispatch_briefing_check --> tools_taglines
    tests_test_inc207_extract_js --> tools_doc_synthesis_extract_architecture
    tests_test_inc207_extract_js --> tools_doc_synthesis_extract_js
    tests_test_inc207_size_rule --> tools_doc_synthesis_synthesis_diff
    tests_test_ops_battery --> tools_ops_battery
    tests_test_loose_deferral_envelope --> tools_loose_deferral_envelope_check
    tests_test_loose_deferral_scan --> tools_loose_deferral_scan
    tests_test_loose_deferrals --> tools_loose_deferrals
    tests_test_parked_ledger --> tools_parked
    tests_test_scheduled_jobs --> tools_scheduled_jobs
    tests_test_watcher_coverage --> tools_watcher_coverage
    tests_test_seam_handoff -.->|deferred| tools_decisions
    tests_test_session_heartbeat --> tools_friday_substrate
    tests_test_session_heartbeat --> tools_session_heartbeat
    tests_test_spawn_grant_check --> tools_spawn_grant_check
    tests_test_standards_deviations --> tools_standards_deviations
    tests_test_state_record_dirty_bit --> tools_state_record
    tests_test_usage_telemetry --> hooks_usage_telemetry
    tests_test_usage_telemetry --> tools_friday_substrate
    tests_test_verify_review_format_dispositions --> tools_verify_coverage
    tests_test_verify_review_format_dispositions --> tools_verify_review_format
    tools_experiments_server --> tools_experiment_request
    tools_experiments_server --> tools_experiment_run
    tools_experiments_server --> tools_friday_consent
    tools_experiments_server --> tools_spawn_telemetry
    tools_friday_consent --> tools_friday_substrate
    tools_friday_consent --> tools_taglines
    tools_loose_deferral_envelope_check -.->|deferred| tools_friday_substrate
    tools_loose_deferral_envelope_check --> tools_taglines
    tools_loose_deferrals --> tools_friday_substrate
    tools_loose_deferrals --> tools_taglines
    tools_sensitive_store_scan --> tools_sensitivity_declaration
    tools_sensitivity_declaration --> tools_friday_substrate
    tools_sensitivity_declaration --> tools_taglines
    tools_maintainability_envelope_check -.->|deferred| tools_friday_substrate
    tools_ops_battery --> tools_friday_substrate
    tools_ops_battery --> tools_taglines
    tools_parked --> tools_friday_substrate
    tools_parked --> tools_taglines
    tools_scheduled_jobs --> tools_friday_substrate
    tools_scheduled_jobs --> tools_taglines
    tools_proposal_pipeline --> tools_taglines
    tools_proposal_pipeline_check --> tools_proposal_pipeline
    tools_state_advisory_check --> tools_friday_substrate
    tools_state_advisory_check --> tools_taglines
    tools_state_record --> tools_friday_substrate
    tools_state_record --> tools_taglines
    tools_verify_review_format --> tools_verify_coverage
    tests_test_inc200_experiment_request --> tools_experiment_request
    tests_test_lane_open_helper --> tools_friday_substrate
    tests_test_mdparse --> tools_doc_index_mdparse
    tests_test_registry --> tools_doc_index_registry
    tests_test_sanitized_mirror --> tools_sanitized_mirror
    tests_test_seam_handoff --> tools_friday_substrate
    tests_test_seam_handoff --> tools_seam_handoff
    tests_test_secret_names --> tools_secret_names
    tests_test_sensitive_store_scan --> tools_sensitive_store_scan
    tests_test_sensitive_store_scan --> tools_sensitivity_declaration
    tests_test_sensitivity_declaration --> tools_sensitivity_declaration
    tests_test_sensitivity_requirements --> tools_sensitivity_declaration
    tests_test_skill_standard_check --> tests_guardkit
    tests_test_skill_standard_check --> tools_skill_standard_check
    tests_test_spec_id_strip_bundled --> tools_spec_id_strip_check
    tests_test_server --> tools_doc_index_server
    tests_test_batch_edit --> tools_batch_edit
    tests_test_recurrence_register --> tools_taglines
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
    tests_test_watcher_coverage -.->|deferred| tools_watcher_coverage
    tools_bug_close_check --> tools_trail_check
    tools_capture_integrity --> tools_decisions
    tools_capture_integrity --> tools_friday_substrate
    tools_conformance_checks --> tools_friday_substrate
    tools_conformance_checks --> tools_taglines
    tools_conformance_envelope_check --> tools_friday_substrate
    tools_conformance_envelope_check --> tools_taglines
    tools_conformance_sweep --> tools_conformance_checks
    tools_conformance_sweep --> tools_friday_substrate
    tools_conformance_sweep --> tools_import_cycles
    tools_conformance_sweep --> tools_taglines
    tools_consumer_scan --> tools_reckoning
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
    tools_doc_synthesis_extract_architecture -.->|deferred| tools_doc_synthesis_extract_js
    tools_doc_synthesis_synthesis_diff -.->|deferred| tools_decisions
    tools_doc_synthesis_synthesis_diff -.->|deferred| tools_doc_index_mdparse
    tools_doc_gate --> tools_findings_brief_check
    tools_doc_gate --> tools_taglines
    tools_experiment_request --> tools_friday_substrate
    tools_experiment_request --> tools_taglines
    tools_experiment_run --> tools_experiment_request
    tools_findings_brief_check --> tools_taglines
    tools_foundation_check --> tools_taglines
    tools_foundation_check --> tools_verify_claims
    tools_graph_freshness_check --> tools_friday_substrate
    tools_graph_refresh --> tools_friday_substrate
    tools_handoff_attest --> tools_friday_substrate
    tools_handoff_attest --> tools_handoff_gate
    tools_handoff_attest --> tools_secret_posture_check
    tools_secret_posture_check --> tools_secret_names
    tools_secret_posture_check --> tools_taglines
    tools_handoff_gate --> tools_friday_substrate
    tools_import_cycles --> tools_friday_substrate
    tools_lane --> tools_friday_substrate
    tools_maintainability_envelope_check --> tools_taglines
    tools_maintainability_gate_check --> tools_maintainability_envelope_check
    tools_maintainability_gate_check --> tools_verify_claims
    tools_maintainability_gate_check --> tools_maintainability_measure
    tools_maintainability_measure --> tools_taglines
    tools_open_risks_check --> tools_decisions
    tools_open_risks_check --> tools_taglines
    tools_oracle_edit_check --> tools_decisions
    tools_oracle_edit_check --> tools_taglines
    tools_receipt --> tools_friday_substrate
    tools_reckoning --> tools_friday_substrate
    tools_reckoning --> tools_taglines
    tools_reckoning_sweep --> tools_friday_substrate
    tools_reckoning_sweep --> tools_reckoning
    tools_reckoning_sweep --> tools_taglines
    tools_receipt -.->|deferred| tools_verify_claims
    tools_receipt -.->|deferred| tools_verify_coverage
    tools_receipt -.->|deferred| tools_verify_spawn_coverage
    tools_receipt -.->|deferred| tools_verify_state
    tools_research_orphan_check --> tools_taglines
    tools_seam_handoff --> tools_decisions
    tools_seam_handoff --> tools_friday_substrate
    tools_session_heartbeat --> tools_friday_substrate
    tools_spawn_telemetry --> tools_friday_substrate
    tools_standards_deviations --> tools_friday_substrate
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

1. **The foundation — `tools.friday_substrate`.** The single-*path* invariant made visible in the graph: nearly every tool edge points into it. The rule itself is single-homed in the project `CLAUDE.md` § Conventions (D-0135); what the extraction shows is the shape that rule mandates — record-owning modules write their own record and come here for the shared primitives (root, journal, locks, time).
   `tools.decisions` + `tools.taglines` sit just above it as the shared record
   and grammar.
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

**Last-verified:** 2026-08-03 (INC-101 close: doc_probe_scope + its two test files into inventory; the INC-209 additions confirmed present from the 950fe4b close that left this stamp untouched; the dense-graph sentence's rotted figures replaced with a pointer per INC-203 D2 — both caught by the promoted probe's own first run over this tree; synthesis_diff exit 0) · **Record-status:** verified
