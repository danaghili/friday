# Contract: the operations battery (the row set, the verdict grammar, the record)

The battery is the named set of operational promises the operations expert (`agents/roles/operations.md`) is asked to prove on any project friday manages, at the two moments friday re-proves a living system: the deep clean's operations dispatch (`skills/reconcile/SKILL.md` §2) and the client handover's operations consult (`skills/handoff/SKILL.md` §2). This file is the row set's single home (INC-102 FR-102.1, D8): each consuming surface cites it by name and never restates a row's text — the cite-never-restate rule (D3, project CLAUDE.md § Conventions) governs. **Producer:** the operations role, which runs the rows and writes each verdict as a typed line in the project's own operations record (FR-102.3). **Consumers:** the deep clean, which surfaces verdicts and findings to the PM at its close, and the handover package, which carries each row's verdict and date in the maintenance table whose shape `docs/contracts/handoff-package.md` owns (FR-102.8 — that contract owns the table, this one only says the verdicts ride in it). Both sides cite THIS file.

## The verdict grammar (FR-102.2 — defined once, here)

Every row returns exactly one of three verdicts, and a document is none of them (INC-102 D1):

- **proven** — somebody ran it; the date and what happened are recorded. A drill row's proven line also names the paths the drill proves, because that is what its expiry reads (FR-102.4).
- **not proven** — the honest default. A draft drill document, a named owner, a scheduled date, and a stated intention — singly or together — resolve to this verdict, never to a pass. Where a drill cannot be run from here, the drill document is still produced, stranger-readable and addressed to a human: producing it is mandatory, and producing it closes nothing.
- **not applicable** — with the reason written down. Proposed by the role, ratified by the PM at the close, and the ratification is structural: the verdict line carries `ratified: <date>` once the PM has ruled (D-1031), which makes the line itself the accepted-risk record the deep clean's existing aging reads back and re-presents for a fresh call (FR-102.10); a decline never hardens into a permanent exemption, and a not-applicable line with no `ratified:` date is a proposal still awaiting the close.

## The two kinds, and the one that expires (INC-102 D7)

- **Drill rows** need a human to perform an act. Their verdicts carry a date and the proved paths; at each run, a proven drill row asks the project's own history whether any named path changed since that date — if one did, the row returns not proven **and names the change that invalidated it**; if none did, the recorded result stands (FR-102.4). Calendar age alone never expires a drill: the innocent-calendar, killer-change asymmetry is the increment's founding evidence.
- **Inspection rows** are things friday can simply look at on every run. They re-derive their answer each time and carry no expiry — an expiry clock here would invent staleness where there is none.
- **Judged rows** predate the proof grammar and are carried unchanged, labelled judged (INC-102 D8): their conversion to the proof grammar is deferred by name (INC-102 §10), and nothing in this file upgrades or weakens them.

## The rows

Each row is one stack-agnostic invariant sentence; the model is its adapter to whatever the project in front of it actually runs, under the proof rule (INC-102 FR-102.5 — the tier reserved for controls that cannot be mechanized across arbitrary stacks). A project a row genuinely does not fit answers not applicable with a reason — a first-class verdict, not a failure; friday's own repository, which deploys nothing and schedules nothing, is the standing example (INC-102 D9).

| key | kind | invariant |
| --- | --- | --- |
| `restore` | drill | A backup that has never been restored is a hope, not a backup: the drill restores into something disposable and checks what came back. |
| `undo` | drill | A rollback that has never been drilled is a hope, not a rollback: the drill returns the system to its previous version and back, and proves the previous version was genuinely previous. |
| `restart` | drill | A machine that has never been restarted on purpose will be restarted by accident: the drill restarts the host and proves the system comes back on the version it went down on. |
| `job-list` | inspection | Every job running on the machine is named in a committed file, and the installed schedule matches it. |
| `job-freshness` | inspection | Every scheduled job has something that notices when it stops running. |
| `isolation` | inspection | Starting the development environment cannot read, write, or displace anything production owns. |
| `runtime-parity` | inspection | The software version the tests pass on is the version production runs. |
| `client-visibility` | inspection | A failure inside a user's browser reaches somebody who can act on it. |
| `dependency-advisory` | inspection | Somebody or something finds out when the outside code this project runs gets a published security warning, and how long it has been outstanding is known. |
| `monitoring` | judged | Monitoring means someone finds out before the user emails: "a user emails us" recorded as the monitoring story is a finding, stated plainly. |
| `runbook` | judged | Deploy is a runbook, not a memory: the steps are written where someone who is not their author can repeat them, and a deploy that lives in one person's shell history is a finding. |

## The asks (FR-102.6 — stranger-proof, and never an instruction to the model)

Each proof-grammar row's ask lives here and nowhere else: what the test is, why it matters, what to run, and what a pass looks like — plain language, short sentences, concrete before abstract, held to the cold-reader criterion (AC-102.4). Drill asks are addressed to **you, the operator**: friday prepares the steps, records what you report, and stays out — it never restarts, rolls back, or deletes anything running for real (S-102.1, KH-3). The role adapts each "what to run" to the project's actual stack; the examples here are examples. The two judged rows carry no ask: they are the role's own read under their table sentences, carried unchanged (INC-102 D8).

### `restore` — bring a backup back, somewhere disposable (drill)

**What the test is.** Take a real backup file and restore it into something disposable — a scratch database, an empty folder. Then check the data is actually in it.

**Why it matters.** A backup you have never restored is only a file that might be one. The day you need it is the worst day to find out.

**What to run.** friday rehearses this half itself where the project allows — for example a `pg_restore` into a scratch database, or unpacking the backup archive into an empty folder — and quotes the result. Nothing touches the live system.

**What a pass looks like.** The restored copy opens and holds real, recent data — for example, yesterday's records are in it — and the steps are written down where anyone could repeat them.

### `undo` — roll back to the previous version, then return (drill — performed by you, the operator)

**What the test is.** You deploy the previous version of the application on purpose, see it running, then bring the current version back.

**Why it matters.** When a bad release ships, undo is the first thing you reach for. The system this battery learned from had an undo that would have "rolled back" to the version already running — a rollback that does nothing, sitting unnoticed in production.

**What to run.** You run your rollback procedure once — for example your rollback script, or redeploying the previous image tag. First check the recorded "previous version" really is different from what is running now. friday never performs this; it writes the steps and stays out.

**What a pass looks like.** For a moment the application demonstrably runs the previous version — an older version number, an older behaviour — and one more step returns the current one.

### `restart` — reboot the machine on purpose (drill — performed by you, the operator)

**What the test is.** You restart the machine the system runs on, at a quiet moment, and watch what comes back.

**Why it matters.** Every machine restarts eventually — a power cut, a host migration, a forced update. The system this battery learned from came back on the wrong software version on its first deliberate reboot, because nobody had rebooted since the deploy method changed.

**What to run.** You reboot the host — for example `sudo reboot` — wait for it to come up, and look at the application. friday never restarts anything; it gives you this drill and records what you report.

**What a pass looks like.** The system serves again with no hands beyond the reboot itself, and it runs the exact version it ran before — check the version number or image tag, not just "the page loads".

### `job-list` — what the machine runs matches what is written down (inspection)

**What the test is.** friday reads what the machine is actually scheduled to run — cron entries, systemd timers, CI schedules — and compares it to the committed list at `docs/ops/scheduled-jobs.md`.

**Why it matters.** A job someone added by hand and forgot is invisible until it breaks. The system this battery learned from called hand-edited schedules its most frequent operational failure, and had nothing comparing written to installed.

**What to run.** friday runs the comparison itself on every deep clean. The first time, it photographs the machine and asks you once per job: does this belong here, and what is it for?

**What a pass looks like.** Every job on the machine is in the list, every job in the list is on the machine, the schedules match, and every entry carries your recorded confirmation.

### `job-freshness` — something notices when a job stops (inspection)

**What the test is.** For each scheduled job, friday asks one question: if this silently stopped running tonight, what would notice?

**Why it matters.** A dead nightly backup looks exactly like a living one until the day you need the backup. "It has always run" is not a watcher.

**What to run.** friday inspects each job for evidence of watching — a heartbeat ping, an alert on a missed run, a dated output somebody reads — and reports each job's answer.

**What a pass looks like.** Every job names the thing that notices its absence within about a day. "Nobody would notice" against any job is the finding, stated plainly.

### `isolation` — development cannot touch what production owns (inspection)

**What the test is.** friday checks where the day-to-day development set-up points — and that none of it lands on the live system's database, stored files, or addresses.

**Why it matters.** The cheapest way to destroy production data is a development environment quietly pointed at the production database.

**What to run.** friday reads the development and production configurations side by side — the names: hosts, database names, storage paths, ports — without ever opening a real secrets file. Where the names are indirect, it asks you to confirm what each points at.

**What a pass looks like.** Development points at its own database, its own storage, its own addresses — sharing nothing production owns. Any shared name is a finding naming it.

### `runtime-parity` — tested on what production actually runs (inspection)

**What the test is.** friday compares the software versions the tests run against with the versions production runs — the language runtime, the database, the base image.

**Why it matters.** Tests that pass on a version production does not run prove things about a system that is not the one serving users.

**What to run.** friday reads both sides — the CI configuration and toolchain files on one, the deploy configuration and the host's declared versions on the other — and names each pair.

**What a pass looks like.** Each pair matches, or the difference is written down with the PM's recorded acceptance of it.

### `client-visibility` — a failure in the user's hands reaches somebody (inspection)

**What the test is.** friday follows what happens after the running client breaks — the page in someone's browser, the app on someone's device — and asks who ends up seeing it.

**Why it matters.** Server logs stay silent when the failure lives in the client. If the page breaks in the user's hands, the first report should not have to be an email from a stranger.

**What to run.** friday reads the client code for its error path — an error reporter, a logging endpoint, even a "something went wrong, tell us" route — and follows where a failure actually lands.

**What a pass looks like.** A client-side failure demonstrably lands somewhere a named person reads — a dashboard, an inbox, an alert. Otherwise the row reports "nobody would know", stated plainly.

### `dependency-advisory` — published warnings against the outside code this project runs (inspection)

**What the test is.** friday checks the outside code the project runs for security warnings the world has already published, and counts how long each one has been sitting outstanding.

**Why it matters.** The system this battery learned from ran a published critical flaw in its login library for months. Nobody was careless on the day it was chosen; the world moved afterwards, and nothing was looking. Time passing unseen is the failure this row exists to make visible.

**What to run.** friday reads the advisory report the project's own delivery pipeline already produced, where one exists; where none does, friday runs the advisory scan itself and reads that. Either way the row produces its verdict — it never depends on a person having read a pipeline's output.

**What a pass looks like.** Nothing outstanding — and "nothing found" means a scan that ran clean, never one that did not run. Anything outstanding is named with its public reference and its age, counted from the day the warning was published rather than the day friday noticed it. A warning that has no fix anywhere is put to you once; on your recorded acceptance it stops re-listing, and it returns the moment a fix is published.

## The advisory row's sources, and the no-fix acceptance (INC-103 FR-103.5/FR-103.6, D4)

The row's review-time scan command is pinned in the security lane (`skills/security/SKILL.md` §2 — the review-time home); the delivery pipeline's copy rides the seeded workflow whose template `docs/contracts/claude-scaffold.md` § The dependency-update seeds owns. The row reads that pipeline's evidence where it exists and runs the pinned scan itself where none does, so its verdict never depends on anybody having read a pipeline's output (KH-5). An advisory the scanner reports as having no fixed version anywhere is recorded once through the parked ledger on the PM's word (`docs/contracts/parked-ledger.md`; `tools/parked.py append --source lead`, the entry carrying the advisory's reference, revisit-when: a fixed version is published): it stops re-listing as live, the deep clean's existing roundup re-presents it unchanged, an advisory whose fix later publishes returns to the live list, and a row whose only outstanding warnings are recorded acceptances is proven with the acceptances named.

The `job-list` row is the only row that owns a committed file of its own; its list lives at `docs/ops/scheduled-jobs.md`, written by `tools/scheduled_jobs.py` only (the D-0135 pattern — photograph, confirm, diff are its three verbs). On a project with no committed list, it photographs what is installed, states in the file itself that the copy was taken off the machine and ratifies nothing, and asks the PM once per job whether it belongs and what it is for; the confirmation is recorded with its date. Before that confirmation, a machine/file difference is a pending baseline and the row's verdict is not proven with the pending confirmation named; after it, any difference between machine and confirmed list is a finding naming the job (INC-102 D6). The list records a job's name, its schedule, and its purpose — the value-bearing parts of a command line are never copied into the list, a verdict line, a report, or the journal (S-102.3, KH-4); the repository-carries-names, store-carries-values invariant (INC-204 D2) is untouched by this row.

## Safety rails (S-102.1, S-102.2, S-102.6)

- **friday never performs the destructive half of a drill (FR-102.9).** The role restarts nothing, rolls nothing back, and deletes nothing on a system that is running for real. Where a drill can be rehearsed safely against something that is not production — the restore row's scratch-copy pattern is the model — the role runs it; where it cannot, the drill goes to a human as instructions and the row records not proven. Row asks are written so they cannot read as an instruction to the model to perform the act (KH-3).
- **The battery reports and never blocks (S-102.2).** It gates nothing, fails no build, stops no close, and adds no confirmation to the handover — the handover's gate set is untouched (INC-102 D4) — and a row that is missing, broken, or unsure allows.
- **Nothing here nags (S-102.6).** Every row runs inside one of the two lanes the PM invokes deliberately; no scheduled trigger, no session-start prompt, and no threshold is added — the no-cron, no-nagging ruling's single home (D-0111) governs. The hardening pass is deliberately not a run-moment: its operations dispatch routes approved findings to a fixer, which is a different job from standing re-proof (INC-102 D9).

## The verdict record (FR-102.3)

One typed line per row, in a marker-fenced block in the project's own operations record, carrying the row key (the closed vocabulary is this file's table), the verdict, its date, — for a drill row — the proved paths, and — for a ratified not-applicable row — the PM's ratification date. Grammar and empty case follow the house tag-line module (`tools/taglines.py`): an empty block means nothing has been proven yet and is reported as exactly that — never as clean, never as absent (S-102.4). The record lives at `docs/ops/battery.md`, block `FRIDAY-OPS-BATTERY`, written by `tools/ops_battery.py` only (D-1027, the D-0135 pattern — both sides of this seam cite each other): `record` upserts one line per row, latest call wins, history in git; `ratify` stamps the PM's dated ruling on an existing not-applicable row and refuses every other verdict — the PM ratifies a decline, never a proof (D-1031); `check` is the drill-expiry read (FR-102.4, D-1028); `read` returns the three distinct states; `init` writes the empty block. A fresh recording always arrives unratified: a new proposal needs the PM's fresh ruling, never an inherited one.

## What this battery is NOT

- Not a new gate: the battery itself blocks nothing and adds no confirmation anywhere (INC-102 D4, S-102.2) — the handover's pre-existing restore gate keeps consuming the `restore` row's evidence exactly as it always has, and that gate's own refusal is its contract's business, not this file's.
- Not the user's experience of failure: loading states, error boundaries, and retry behaviour belong to the sibling increment INC-102 §10 names, so neither builds the other's half — this battery owns only whether a client-side failure becomes visible to somebody who can act (`client-visibility`).
- Not the redteam's operational adversary: disk guardrails, resource limits, and single points of failure stay attacked there, deliberately not rows here (INC-102 §2).
- Not the running-cost row: the bill-vs-projection re-check belongs to `friday-running-cost` against its own oracle (`docs/ops/cost-projection.md`), not to this set.
- Not a new hard-failing check on a managed project (S-102.5).

## Verification

- The verdict record: `python3 tools/ops_battery.py read --root . ` — JSON, the three distinct states; `record` refuses what the grammar refuses (exit 1, the refusal named); `ratify` refuses every verdict but not-applicable.
- Drill expiry: `python3 tools/ops_battery.py check --root .` — report only, always exit 0 (S-102.2).
- The job list: `python3 tools/scheduled_jobs.py read|photograph|confirm|diff --root .` — `diff` report-only, always exit 0; a value-shaped field is refused at exit 1 naming the field and never echoing the content (S-102.3).

Tests: `tests/test_ops_battery.py` (carries the row-key lock to this file's table), `tests/test_scheduled_jobs.py`.
