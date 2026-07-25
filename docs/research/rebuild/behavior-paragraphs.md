# Behavior paragraphs — the agreed per-command contracts

_Working document of the 2026-07-13 design session (Dan + Claude). Each paragraph is
interrogated one at a time and approved by Dan; the approved text is BOTH the contract the
command audit enforces AND the user-manual page a marketplace stranger reads. Shape: what you
type → what it asks first → what it refuses without → what it writes down → what you end with.
(Same night, PM decision: the questioning protocol formerly called "grilling" is renamed
**interrogation** — term updated throughout this file; the approved content is otherwise
untouched.)_

_Status legend: ✅ approved by Dan · 🔎 draft under interrogation · ⬜ not yet drafted._

## Vocabulary used in these paragraphs

- **question card** — the harness's structured question interface (formal tool name:
  `AskUserQuestion`): clickable options with the recommended one first, multiple-choice where
  answers aren't exclusive, side-by-side previews for comparing concrete things, and always a
  write-your-own field.
- **decision-ask** — a question card with consequences: used at big decisions, its answer is
  automatically written into the decision log as a permanent record.

---

## Spine

### ✅ /friday:profile (approved 2026-07-13)

When I type this, friday first checks whether I already have a profile. **If I don't:** it
interviews me about who I am and how I like to work — how technical I am and how technical it
should be with me (down to "explain it like I don't work in software"; I never hand-edit a
settings file to stop the jargon), how much explanation I want, how hands-on I am with
decisions, how strict reviews should be, how I like things formatted, and how it should check my
understanding (teach-backs on every big decision, only the biggest, or trust me to ask). It looks
up what it can already see before asking, then plays back its picture of me in plain words for my
confirmation — a wrong guess about me dies here, not three projects later — and saves the
confirmed answers **in a structured form** to my personal settings file, where every friday
project inherits them. **If I do:** it shows me my current profile as a pick-list and I choose
exactly what to change — it updates only that, never re-runs the whole interview, never clobbers
the rest. At the end, every other command quietly reads this — the same expert advice arrives
tuned to me, changing *how things are explained, never what gets checked* — and friday verifies a
valid profile actually exists on disk before calling the run done.

_Hook candidate #1 attached: post-write profile validity check (structured, complete, parses);
blocks only on a provably broken/missing profile._

### ✅ /friday:brainstorm (approved 2026-07-13)

When I type this with an idea — even one sentence — friday's discovery expert first checks the
idea's *size*: if it's really several independent projects, we split it before refining anything,
and each piece gets its own discovery. Then it interrogates the idea with me, one question card
at a time, in dependency order, telling me where we are in the tree. It opens with the problem,
never the solution — why this, who's affected, what happens if we do nothing — and any
requirement that arrives dressed as a technology gets unwrapped back to the need underneath.
Every question carries a recommendation, its reasons, and the real-life consequence of each
option; it looks things up before asking me. When something would be clearer *shown* than said,
it offers — just then, never upfront — the **visual companion**: a browser tab beside our chat
where I see mockups and diagrams and click to choose, my clicks and even my hesitations feeding
the conversation. It walks the life of the thing with me in concrete stories ("a member's card
fails on renewal day — what should have happened?"), because the requirements I'd never think to
mention only surface in stories, not in "anything else?" — and it asks what the system must
*prevent*, not just do. It asks how big this could get — and whether I even want it to — because
"we will never need that" is as load-bearing as any feature, and the downstream experts (stack,
operations, running-cost) inherit my answer instead of re-asking it. Behind the conversation it
keeps a **coverage ledger** I can see: every standard concern — speed, security, failure, growth,
legal, look-and-feel — either answered or marked *excluded on purpose*, never silently skipped,
because the known killer of interviews like this is the question that never got asked. And it
holds one standing question it asks *itself*, never me — **"what is the PM missing here?"** —
raising unprompted the blind spots I can't see from my seat: the consequence I haven't imagined,
the industry lesson I don't know, the thing a second PM in the room would catch. Before
writing, it shows me two or three genuinely different shapes with trade-offs and its pick; the
chosen shape is played back **in sections**, each confirmed before the next. Hard-to-reverse
decisions get a teach-back — I say my understanding back before we lock. It refuses to write a
spec from an unexplored idea, ever: for tiny projects the *document* shrinks, the *gates* don't.
What it writes is the scope-of-work: plain English in a formal skeleton — numbered requirements,
each with a concrete "how we'd know it's done"; boundary-case examples carried in as acceptance
tests; what's out of scope, with reasons; a **waiting room** for ideas we rejected, so
"consciously excluded" can never be mistaken for "forgotten"; and every open question named, with
an owner. Then a fresh pair of eyes — an agent that wasn't in our conversation — reviews the
written file for contradictions and anything readable two ways, and finally *I* read the actual
file. Only my confirmation completes the run. At the end I have the one document the build treats
as law, and my big decisions are behind me — made while they were still cheap to change.

_Role-contract techniques (not user-facing promises; carried with citations into the rebuild
TSOW): context-free opening questions; goal→actor→impact chain; event-timeline walkthrough with
parked hotspots; CRUD/lifecycle check per data entity; cross-consistency check against earlier
answers; JTBD adoption-forces probe. Sources: superpowers-brainstorming-foldins.md +
ba-requirements-practice.md. GROWTH SPLIT (Dan): brainstormer elicits growth appetite ONCE as a
requirement/non-goal; strategist/operations/cost experts consume the answer — never re-ask._

### ✅ /friday:init (approved 2026-07-13)

When I type this in a project, friday takes stock before doing anything — and its first question
is ***what kind of project is this?*** A brand-new idea; existing code that's never had friday; a
project built by an older friday; client work carrying someone else's requirements; something
with screens, or a headless tool — because the kind decides which experts show up, and some kinds
belong behind a different door entirely (existing code routes to adopt, an old friday project to
backfill; init sends me there rather than pretending). And independently of the code: **is the
world this lands in empty or occupied — greenfield or brownfield?** A brand-new codebase can
still be replacing a live system with real users and real data; when it is, migration, cutover,
and don't-break-what-exists become *named requirements*, not surprises. The answer is recorded
as a standing claim where every downstream expert reads it. Alongside kind, it checks what already
exists: **a client intake brief** — and if this is client work without one, it offers that
interview *first*, because those answers can't be retrofitted after decisions are made — then my
profile, a scope-of-work, designs, the project settings file, a build record, a git repository.
It reports what it found, proposes only the missing stages, and asks before starting any of
them — re-running init can never overwrite what exists. Then the missing stages run in order,
each an expert consulting me: the profile interview if I've never done one; discovery, exactly as
promised above; the design stage for anything with a screen, settled once before any building;
and the strategist — who asks me *first* what I already run, own, prefer, and can afford, then
proposes technical foundations grounded in my answers, never a menu of guesses, recording both
its recommendation and my decision when we disagree. Every proposal is confirmed with me before
it's written down. At the end it lays the mechanical groundwork and **verifies the foundation is
actually valid — quoting the real check output, never asserting it**. Then the hand-off, which is
*not* always one decision: if the trail is clean, building is mine to start. If any risk was
flagged open along the way, **friday refuses the bare hand-off** — the road goes through research
first, and overriding that refusal takes an explicit, on-the-record decision from me, never a
shrug. Sometimes the honest end of init is "not yet — and here is exactly why."

_Hook candidates #4 (foundation-valid gate, exists as the K0 check — needs stranger-proof
messaging) and #5 (build refusal past open risks, override only via on-the-record decision-ask)
attached — see task #5._
### ✅ /friday:build (approved 2026-07-13)

When I type this, friday checks the ground first: the approved scope-of-work exists, the
foundation checks out, and no flagged risk is still open — if one is, it refuses and points to
research, the same rule init enforces, because I might type this days later having forgotten. It
offers to build in a **worktree** — a second folder linked to the same repository, so my real
copy never changes while the build runs and "discard" means deleting a folder (the decision
trail is shared between both copies automatically; a plain branch is fine for quick builds — the
worktree earns its keep when the build is long or my main copy needs to stay live). Before any
code, it reads the whole spec, sketches the architecture, and **sizes the job honestly**: a
worked estimate of whether the whole build fits one continuous session at full quality, recorded
either way. If it fits: one uninterrupted run — a single mind holding every cross-cutting
decision, which is the entire bet. If it doesn't: the units are declared *up front*, the spec's
own dependency ordering becoming the plan before the first line of code — each unit its own
one-shot, with the make-or-break foundation **independently checked before anything builds on
top of it**. While building: when a decision needs me — anything hard to reverse, surprising, or
touching money, security, or people's data — **the build stops and asks**, with a decision-ask
whose answer becomes a permanent record. It never guesses, and it never builds past an
unanswered question. Smaller judgment calls it records as it goes — **each with its reasoning
and the road not taken**, because finished code can never show *why* the alternatives lost. The
spec's critical logic gets test-first treatment — the failing test exists before the code that
passes it, **and is committed before implementation begins**. The tests are the contract, not an
obstacle: **it never rewrites a test so that the code it just wrote can pass**; if it believes a
test is genuinely wrong, it stops, explains why, and asks my permission before touching it — and
because the tests were committed first, **any edit to an already-committed test is detectable,
not deniable**. Anything the spec marked "prove it for real" gets proven for real: the actual
broadcast, the actual payment webhook, the actual restore, with output quoted. It **never edits
the spec** — where reality disagrees with it, the disagreement is recorded, not painted over.
When building is done it re-runs everything, quotes the results, and hands itself straight into
the independent hardening pass — no gap for me to remember to fill — then regenerates the docs
from the *hardened* code, never a stale snapshot. At the end I choose: merge, open a pull
request, keep the worktree to inspect, or discard — and even a discarded build keeps its
decision trail, because knowing why we abandoned something is worth as much as the thing itself.

_Hook candidate #7 attached: the committed-test edit guard (mechanical: tests committed before
implementation → any in-build edit to them is a provable event; blocked unless a PM permission
record exists). Carries DF-010/018/019/020/021 + the stall decision._
### ✅ /friday:harden (approved 2026-07-13)

By default I never type this: the build hands itself over. I can also invoke it directly,
pointed at an area ("harden the payment sync"); a direct invocation starts with an **explore
pass** to gather context on that area before judging it — **querying the project's indexed docs
and code graph rather than rummaging the codebase** (grep is the fallback, not the plan).
Hardening's doctrine: the builder's word is not evidence. Its discipline: **it finds; it never
fixes.** Every claim is re-derived by checkers who weren't in the build: files actually changed,
tests re-run fresh, outputs quoted. An independent **tester** re-proves the suite, the
production build, and every "prove it for real" the spec mandated, and closes every numbered
requirement — done, or deferred with a reason, none skipped. **Skeptics** read the actual
diff — never the build's summary — briefed to find the claim that is false. A **reviewer** holds
the whole build against the spec, un-ratified judgment calls first. A **security review**
verifies the locks: who can log in, who can see what, how secrets are held, whether the seams to
outside services (payments, video, email) are protected — every finding proven with a
reproduction, never speculated. An **abuse review** attacks the business rules themselves: what
a motivated user could skip, fake, or break; what falls over operationally — the backup that's
never been restored, the single point of failure. All of it lands in a **findings brief**: each
finding numbered, evidenced, explained in plain words, with *how we'd know it's fixed* — and the
brief passes the same structural gate as any document a build consumes. The brief comes to me
once: I disposition every finding — **fix now, defer with a reason, or accept the risk on the
record.** Then the loop runs **autonomously**: a fix-build closes the fix-nows under full build
law — failing repro test committed first, tests are the contract — and a **fresh** hardening
pass re-checks, scoped to what changed. The fixer keeps its session across rounds; every
checking pass gets new eyes. Each round must tighten — fewer, smaller findings — and it
interrupts me mid-loop only if a genuine decision-ask arises (confirmed: autonomous otherwise).
**Three rounds maximum**; anything still open after the third comes back to me, not to a fourth
round. When the loop closes, the **full test suite runs one final time** to prove no regressions
crept in. New scope discovered along the way routes to the feature door. Standing tolerance: a
false alarm that blocks good work is worse than a miss — verdicts rest on evidence.

_Loop design (Dan): find → PM dispositions once → autonomous fix/re-check rounds (persistent
fixer session, fresh checker context each round, ≤3, must tighten) → full-suite regression
close. Supersedes the morning's Step-3b placement (repro-test-first moves INTO the fix-build).
Hook candidates #8 (code-graph freshness) and #9 (build-feeding document gate family) attached._
### ✅ /friday:reference (approved 2026-07-13)

When I type this (and automatically at the end of every build, after hardening), friday
regenerates the project's reference documentation from the code itself. The *structure* —
modules, what-connects-to-what, interfaces, the **code graph** — is extracted mechanically from
the code, so it is correct by construction. The *reasoning* — why things are the way they are —
is synthesized from the decision log, so every "why" traces to a recorded decision. The two are
then diffed against each other: where the code says one thing and the record says another, that
gap is reported as a finding, never papered over. Every connection in the graph is tagged as
either **read directly from the source or inferred** — and anything friday asserts as evidence
cites only the former. Every generated file is stamped as generated — hand-edits are pointless
and detectable — and generation always runs against the *hardened* tree, so the docs describe
what shipped, not a draft. The code graph doubles as the project's navigation index: explore
passes, hardening scouts, and future feature work query it through the docs service instead of
rummaging the codebase (**graphify when installed** — pinned as `graphifyy`, supply-chain
vetted — friday's own index when not), and a hook keeps it fresh when changes land — refreshing
*after* the docs regenerate so it never maps a stale description, and declaring itself stale
("N commits behind") rather than answering silently wrong. At the end I have documentation a
stranger could onboard from: structure that is provably current, reasoning that is provably
sourced.

_Carries DF-017/018 + the graphify adoption (soft, fallback, one-hook-author) + hook #8
(freshness, code→docs→graph ordering) + the EXTRACTED-only evidence rule._
### ✅ /friday:feature (approved 2026-07-13)

When I type this with a want ("add gift subscriptions"), friday treats it as a new requirement
entering a finished system — which means discovery, not obedience. The same discovery expert
from brainstorm runs the same interrogation, scaled to the change: it reads the spec, the decision
log, and the code graph *first*, then interrogates the want — what problem reopened, who's
affected, what this must **not** disturb (blast radius is a first-class question), and whether
it collides with anything we consciously excluded — **the waiting room gets checked**, because
maybe this exact idea was rejected before, and I should hear why before re-deciding. Nothing is
codified until the interrogation completes. What it writes is an **increment**: a small spec of its
own with the same skeleton — numbered requirements with fit criteria, in and out of scope,
criticality — filed *beside* the main spec, which gains exactly one pointer line. The main spec
never grows and is never edited. The increment passes the same structural gate as any document a
build consumes, and then *I read the actual increment file* — my approval is the gate. Then a
focused build runs under full build law — sized honestly, test-first with committed tests,
decisions stall, prove-it-for-real — with the increment as its oracle, followed by the hardening
loop scoped to the change's blast radius, and the docs and graph regenerated after. At the end
the system does the new thing, the record shows why, and any future reader can tell this
change's requirements from the original's at a glance — separate file, dotted numbering, one
pointer. This door also **re-opens**: when an approved increment hasn't been built yet and I've
changed my mind about it, the same interrogation re-runs against it — what changed my thinking gets
interrogated like any requirement — and a v2 **supersedes** the original, which moves to the
waiting room with its reason: consciously replaced, never deleted. My read of the rewritten file
is again the gate. Once an increment is **built**, its spec is history and never re-opens: if
reality diverges from what it promised, that's a bug; if I want different behavior, that's a new
increment.

_Carries DF-022/023 + the waiting-room re-entry check (Volere waiting room made load-bearing at
feature intake). Re-open mode added 2026-07-13 with the reassess kill: unbuilt spec =
renegotiable via supersession; built spec = frozen history._
### ✅ /friday:help (approved 2026-07-13)

When I type this, friday builds the command index *fresh from the command files themselves* —
never from a hand-maintained list that can drift — grouped by the life of a project: starting,
building, checking, changing, keeping the records honest. Each entry is the one-line version of
these very paragraphs. If I'm inside a friday project, it also reads the project's current state
and tells me **where I am and what the sensible next command is** — including when the honest
answer is "you have open risks; research comes first." For someone who just installed friday,
this is the front door: what friday is in three sentences, a pointer to the manual, and the
recommended first step (profile, then init). If a command and its documentation disagree, the
mismatch is *reported*, not hidden. **The index and the where-am-I readout come from a
deterministic script — same project, same answer every time, no tokens spent re-deriving it, and
no room to invent a command that doesn't exist. The model's only job here is to run the script
and show me its output verbatim**; anything past that — me asking "so what does harden actually
do?" — is conversation on top of the index, never a substitute for it. At the end I know exactly
what I can type, and why I'd type it.

_Post-reorg the directories ARE the groups (kills the DF-011 hand-map). Deterministic pin: Dan
2026-07-13 — model as verbatim pipe over gen_command_index + the state check's JSON._

## Spine-adjacent

### ✅ /friday:design-system (approved 2026-07-13)

When I type this (or init runs it, for anything with a screen), friday's design expert settles
the interface before any building — knowing its place in the toolchain: **friday conceptualizes;
claude-design designs; design-sync delivers.** The conceptual work happens here: who's looking
at each screen, on what device, in what context; the user journeys mapped to the spec's numbered
requirements; the screen inventory — *what screens exist and what each must do*. The visual
companion serves exactly this stage: rough layouts and flows I click through to settle the
concepts, up to three rounds — alignment sketches, never the design itself. Then the real design
system — tokens, components, polished screens — is created in **claude-design**, the proper
design environment, seeded with the agreed concepts and my existing brand assets; and
**design-sync** pulls the result into the project (and can be called on its own whenever designs
change upstream). What lands is the **locked design contract**: journeys tied to requirements,
the screen-by-screen build sheet, and the synced designs the build implements against. The lock
cuts both ways: the build may not invent screens, and a design change after approval is a
**recorded decision that re-syncs** — never a quiet redraw in either tool. I approve the actual
synced artifacts, not descriptions of them. At the end, every screen the build will create
already exists as a design I said yes to — made in the right tool, delivered into the project.

_Division of labor: friday owns what/why (screens, journeys, requirements); claude-design owns
how-it-looks; design-sync is the seam; re-sync-on-change keeps the sides from diverging._
### ✅ /friday:research (approved 2026-07-13)

When I type this with a question (or init and build route me here because a risk is still open),
friday fans out researchers — several at once, each attacking the same question from a different
angle: the official documentation, real-world reports of it working *and failing*, and the
hands-on spike for anything reading can't settle — a real broadcast, a real webhook, a real
restore. Every claim comes back with its **source named** and a **confidence grade** — proven,
reported, or inferred — never "I believe so." The answers land in the record as findings, and if
the question was one of the spec's open risk rows, the row is **closed with evidence** — or
honestly marked "still unknown, and here's the experiment that would settle it." Research never
decides — it informs: the decision that follows is mine or the relevant expert's, made *on* the
evidence and recorded with it. At the end, the "research first" that blocked my build is either
satisfied with receipts, or I know exactly what remains to be proven.
### ✅ /friday:resume (approved 2026-07-13)

When I type this after a session died — crash, closed laptop, lost connection — friday
reconstructs where things *actually* stood rather than trusting where they claimed to stand. It
reads the project's running journal and heartbeat (a stale heartbeat is the crash signal), the
decision log, and the state record — then **verifies the dead session's last claims before
believing them**: work it says finished gets spot-checked, files present, tests re-run, because
a session that died mid-sentence may have died mid-write too. If the build was **stalled on a
question for me** when it died, that question is re-surfaced first — an unanswered decision-ask
survives the crash; it doesn't evaporate. Then it re-enters cleanly: completed work is never
re-done, half-done work is finished or restarted from the last sound point, and the journal
records that a resume happened and what it found. If the record is too damaged to reconstruct
safely, it says so plainly and shows me the options — it never guesses its way forward. At the
end the project is moving again from where it truly was, and the record shows the seam.

_Stall-recovery promise is new (consequence of the parking kill: a killed session was the only
place a pending question lived — resume inherits it)._

## Maintenance (rebuild lane)

### ✅ /friday:feedback (approved 2026-07-13)

When I've noticed something — a maybe-bug I'm not sure about, a screen that feels wrong, text
that reads badly, a color that's off, or behavior I simply don't understand — I type this and
describe it in my own words. No taxonomy, no form: this door exists precisely for the things
that don't obviously belong anywhere. The triage expert's first job is **understanding, not
classification**: it asks what I saw and what I'd have wanted, investigates what's actually
happening — the record, the code graph, the decision that made it this way — and **explains it
back to me in plain words**. Sometimes that's the whole outcome: "it does X because we decided
Y" — I understand now, no work created, and the question and its answer are recorded so it never
needs asking twice. When something *should* change, it recommends the right size, with reasons:
a **bug** (broken against what the spec promises), a **patch** (text, color, copy — a small
change that needs a trail but not a spec), or a **feature** (new scope deserving real
discovery) — and I confirm before anything moves; the triager routes, it never fixes. Even a
"no" becomes recorded knowledge — *won't-fix*, *works-as-intended*, *duplicate-of*, each with
its reason. Whatever routes onward **carries the whole conversation with it**, so I never repeat
myself to the next expert. When I already know what it is, I skip this door and type the lane
directly. At the end, nothing I noticed is lost: it became work, a recorded decision not to
work, or an answer I didn't have before.

_Crux (Dan): free-form intake + explanation-as-first-class-outcome — the home for "help me
understand my own product." Typed outcomes from the triage research._
### ✅ /friday:bug (approved 2026-07-13)

When I know something's broken, I type this and report it: what I did, what I expected, what
happened instead. The expert completes that skeleton with me, captures the environment while
it's fresh, and takes **one bug per report** — mixed reports can't be closed cleanly. The
debugger's first act is **reproduction** — before any prioritizing, before any theorizing — and
it checks for duplicates and past rulings, so a known answer is never re-derived. If it can't
reproduce, it returns a *specific question*, not a stall — and a bug nobody can pin down is
closed as exactly that, honestly, reopenable when new evidence lands. Then it investigates like
a scientist, not a gambler: it reads the real evidence before proposing causes — the logs, the
stack, the actual state, and the boring assumptions first (right branch? fresh build? does the
test harness itself work?) — with *whatever changed most recently* as the first suspect. Every
investigative step is a written cycle — hypothesis, predicted result stated **before** the
experiment runs, one change per experiment, reverted if it didn't help — and every cycle lands
in an **audit trail, failures included**, because a disproved theory permanently shrinks the
search. It hunts the *earliest* point where good state went bad, tracing backward from where the
error appeared to where it began: **the fix lands at the source, never the symptom.** A
diagnosis isn't done until the why-chain bottoms out in specific code with a mechanism —
confirmed both ways: remove the cause and the failure vanishes; put it back and it returns.
*"It stopped happening" is never a closure.* What comes back to me is the **diagnosis, not a
patch**: reproduction, root cause, proposed fix and its blast radius — I confirm before a line
changes, with two one-word calls drafted for me: *how bad*, and *when*. **Three failed fix
attempts is a circuit breaker**: it stops and brings the question to me — at that point the
problem is probably the design, not the bug — handing over the audit trail and the raw symptoms
while *holding back its pet theory*, so fresh eyes start clean. The fix follows build law: the
reproduction becomes a **failing regression test, committed first**; the fix takes it to green;
the full suite proves nothing else broke. And by the middle rule: internal code is trusted until
it lies — **a path that actually carried this bug gets guards at the layers it fooled**, as part
of this fix, targeted, never scattered. At the end the bug's story — found, understood, fixed,
proven — lives in the record under its number, with its test standing guard against its return.

_Sources: bug-triage-practice.md + debugging-practice.md (Agans/Zeller/SRE + superpowers
systematic-debugging). Carries the show-your-diagnosis floor, the 3-strikes circuit breaker,
escalate-with-symptoms-not-theories, and the middle validation rule (fifteenth decision)._
### ✅ /friday:patch (approved 2026-07-13)

When the change is genuinely small — text, a color, copy, a config value, a dependency pin — I
type this and say what I want. The expert restates the change back with its **exact blast
radius** — "this touches these two files and changes what the renewal email says; nothing else
moves" — and my one tap of confirmation is the whole ceremony. Then it makes the change and
**proves it landed**: the build still passes, the affected surface checked, output quoted. Even
the smallest change leaves the full trail in miniature — what was asked, any judgment made along
the way, proof it works — plus its changelog line: *"too small to record" doesn't exist.* If the
docs or the code graph describe what changed, they refresh. And if mid-change the expert
discovers it isn't small after all — the "text tweak" turns out to feed the entitlement check —
it **stops and re-routes honestly** to the right lane instead of quietly growing. At the end the
change is live, proven, and findable — with a trail so light I never felt it.
### ✅ /friday:reconcile (absorbs sweep — approved 2026-07-13)

When I'm about to do something that deserves a clean conscience — merge, release, hand the
project to someone — I type this, and friday re-verifies **every claim the record makes against
reality itself**: the tests the record says pass are re-run; the docs and the graph are checked
against the code they describe; the settings file's standing claims — the stack, the thresholds,
the non-goals — are each re-proven; every requirement's disposition still holds; and the living
system's promises are re-proven with them — backups that actually restore, monitoring that's
actually watching, the monthly bill against its projection (the operations and cost experts own
those rows). Nothing is
taken on faith: records rot silently, and this is where rot gets caught. It also runs the **full
guardrail battery deliberately** — every check that normally fires on events runs here across
the whole project — so the guards themselves get exercised, not just trusted. Anything that
drifted is either mechanically refreshed (a stale graph regenerates) or **flagged to me with
what changed** — never silently patched over. It also rounds up everything that was ever parked
with a promise: deferred findings, deferred requirement work, accepted risks, waiting-room ideas
whose reasons may have expired — and presents the pile for decisions: *still deferred? worth
doing now? no longer relevant?* Between reconciles I don't think about any of this — landing a
change already re-verifies what it touched, automatically; this is the deep clean, not the daily
rhythm. At the end, the record and reality agree, in writing — or I hold a short list of exactly
where they don't, and what I decided about each.

_Hook relationship: reconcile IS the on-demand invocation mode of the entire check library
(architecture rule, task #5). Accepted risks age and resurface for re-decision._
## Entry doors

### ✅ /friday:adopt (approved 2026-07-13)

When I have an existing codebase that's never known friday, I type this to bring it under
management — *honestly*. The expert reads the whole thing first: builds the code graph —
**graphify when installed, and adopt is where it matters most**: for a codebase in a language
friday's own extractor doesn't speak, it recommends installing it before the deep read, as a
recorded decision — extracts the real structure, reads whatever docs exist. Then it asks me what
code can't say — **with its questions sharpened by what the graph surfaced**: the most-connected
pieces everything flows through, the subsystems it found, the connections that surprised it — so
it asks about what's actually load-bearing, not generically: what this thing *is*, who uses it,
what matters most, what's known to be fragile, where it's headed. From that it writes the
project's starting record: a **reconstructed scope-of-work, marked for what it is** — recovered
from code and my memory, not born from discovery — the settings file describing the stack *as it
actually is*, and reference docs generated from the code as it stands. What it never does is
pretend: **no invented history, no fabricated decisions** — the decision log starts today, and
entry one is the adoption itself with everything I told it. Anything alarming found during the
read — critical logic with no tests around it, secrets sitting in the repo, dependencies years
stale — is surfaced as **findings for my disposition**, never silently fixed. From then on the
project is a full friday citizen: every door works, every guard armed. At the end, code that
grew up without records has records that tell the truth about *that*.

_Hook beat: no new hooks — the reconstructed spec joins the doc-gate family (#9) with one
grammar extension: a provenance status field (born-from-discovery vs recovered-from-code), so no
checker mistakes an adopted spec's authority for an interrogated one's._
### ✅ /friday:backfill (approved 2026-07-13)

When a project was built by an older friday, I type this to migrate its records to the current
version — the marketplace promise that **an upgrade never orphans a project**. It reads the old
record shapes, maps them to the new ones, and shows me the **migration plan before touching
anything**: what carries over directly, what changes form, what the old version recorded that
the new one no longer needs — and, honestly, what the new version expects that the old records
simply don't contain. Those gaps are **declared, never fabricated**: a record the old friday
didn't keep stays an acknowledged blank, not an invented entry. The migration runs with the
originals preserved, is verified by the **full guardrail battery** against the migrated record,
and lands as one recorded decision — *migrated from version X to Y, with the map*. The old
records — and **all of the old friday's documentation**: its checkpoint files, feature trees,
generated docs, everything its ceremony produced — are **archived in their original form, never
deleted**; history stays readable as it was written. At the end the project speaks current
friday, and nothing about its past was invented or lost.

_Hook beat: no new hooks — post-migration validity IS the battery (#4 + doc-gate family #9 with
the provenance extension). First real fixtures when the rebuild ships: this repo's own v0.4-era
projects (katy_video_platform)._
### ✅ /friday:intake (approved 2026-07-13)

When the project is for a client, I type this *before anything else* — these answers can't be
retrofitted after decisions start. The intake expert **prepares before it asks**: it researches
the client's industry — the standard workflow, the common tools of that trade, the regulatory
basics — and brings all of it as *hypotheses to correct* ("usually this works like X — is it
different for you?"), so interview time goes to what's unique about this client. And it knows
the client may not know the answers either: everything derivable gets derived; what remains
arrives as concrete choices, never a quiz. The interview opens with **their world, not the
project**: a grand tour in their own words ("walk me through a typical booking"); the concrete
past over the hypothetical future ("when did that last happen — what did you do?"); their
vocabulary captured into a **shared glossary** and never translated away; and where possible,
**watching a real task done today** ("show me — share your screen"), because workarounds and
tolerated annoyances are requirements nobody will ever state. Handed a solution ("build me an
app"), it pivots to what the client needs to *do*, then walks the short chain of whys to the
real problem. It maps their environment as a **system, not a tool list** — what connects to
what, where each kind of data lives and *which copy is the truth*, how clean it is, and the
industry rulebook that silently constrains everything — reading their existing documents first,
and talking to the people who actually touch the systems, not only the boss. Then the
professional half: **why this project** before what to build; goals and success *in the
client's words*; audience, assets, technical needs; **budget as a design input**; timeline
against the real "why now"; who maintains it after; the **decision-maker**, and who else must
approve; accounts, access, and **ownership** ("who is the domain registered to?"); what's
explicitly **not** included; deliverables bounded with counts and revision rounds; content
responsibility with a deadline; and the **change process, agreed before it's ever needed**. The
output is the **intake brief**: the formal half for sign-off — goals, scope, exclusions, budget,
timeline, approver — separated from the informal half (rapport notes, working preferences, the
glossary), feeding discovery and the strategist directly, so the client's world arrives *before*
proposals form. At the end I have a signed brief, a map of their world, and their own words for
success — and every future "the client expected…" conversation has a document to point at.

_Sources: client-intake-practice.md + client-environment-discovery.md. Hook beat: intake brief
joins doc-gate family #9 (load-bearing fields present)._

## Specialists

### ✅ /friday:security (né secrev — approved 2026-07-13)

Hardening runs this automatically as part of its find pass; I can also run it standalone, or
pointed at one area. **It directs itself**: the worklist is *derived, never requested* — from
the spec's numbered security criteria (the locks we promised), the exposure and
greenfield/brownfield claims in the record, and the changed surface — and it shows me the
derived list to **confirm by exception**, never asking me what to check. The work is done by
**narrow specialists running experiments, not opinions**: an *access-control* reviewer that logs
in as the wrong person and swaps record IDs; a *secrets-and-dependencies* reviewer running the
verified scanners across the whole history; an *integration-seam* reviewer that forges the
webhook signature and replays the expired playback link; an *input* reviewer probing everything
user-supplied data can reach. Each is fresh-context and scoped to its one lane — narrow beats
broad; the evidence says reviewers drown in context — and each is bound by the proof rule:
**exact file and line, the condition that reaches it, and a working proof — no proof, nothing
above informational.** Where a deterministic tool can detect, the tool detects and the AI
explains. Every verdict declares its own limits: **"no issues found" means no easy issues found
by this pass, never "secure"**; a single run is advisory, logged with its model and version;
disputed or critical findings earn an independent second run; and the classes AI reviews worst —
access-control logic, exactly our make-or-break — *always* get the hands-on experiment, never
reasoning alone. The reviewers assume the code may fight back: read-only sandbox, repo bytes
treated as data never instructions, invisible characters stripped. Findings land graded as
decisions — **act now / attend before growth / track** — accepted risks carry my name and my
reason, and everything rides the findings brief and the loop. The one question that stays mine
arrives as scenarios, not a quiz — *which event could we not tolerate* — asked once at intake or
init, then read from the record forever. At the end I know which promised locks held, which
failed with proof in hand, and what I knowingly accepted — with the review's own limits stated
in writing.

_Sources: security-review-practice.md + ai-security-review-{tooling,failure-modes}.md. Hook
beat: #13 reviewer sandbox; proof rule + grading ride findings-brief grammar (#9)._

### ✅ /friday:redteam (approved 2026-07-13)

Where security verifies the locks we *promised*, redteam hunts the doors **nobody thought to
promise**. It runs inside hardening's find pass and standalone. Its worklist comes from
imagination disciplined by structure: it reads the spec and asks what the spec never imagined —
then attacks. Same machinery as security — narrow adversaries, fresh context, **experiments over
opinions** — pointed at different assumptions: a *business-rules* adversary that tries to skip
the workflow, buy the ticket without paying, keep watching after canceling — treating every rule
as an experiment some motivated user will eventually run; an *operational* adversary that asks
what falls over — the backup that's never been restored (*restore it*), the single point of
failure, the vendor that dies mid-class, the disk that fills; an *assumptions* adversary hunting
whatever everyone treats as given — client-side state trusted as truth, the "nobody would ever"
that somebody will. Findings obey the same proof law — demonstrated, never speculated: the
workflow actually skipped, the restore actually failed — graded act / attend / track, my name on
any accepted risk. And a redteam finding is **different in kind**: it usually means *the spec
had a blind spot*, so confirmed findings feed back as candidate requirements — into the waiting
room or a new increment — not merely fixes. At the end I know where the system bends when
someone leans on it who never read our spec — and the spec gets smarter every time.

_Hook beat: none new — #13 sandbox + findings-brief grammar (#9) cover it. Spec-blind-spot
feedback loop: confirmed redteam findings become candidate requirements._

### ✅ /friday:handoff (approved 2026-07-14)

When I type this at the end of a project, friday first runs a quick, mechanical check that the
project's own record still matches reality — the same drift-detectors `/friday:reconcile` uses. If
they come back clean it carries on; if the record and reality have drifted apart, it stops and
**offers** to run `/friday:reconcile` rather than reconciling inline or papering over it. Then it
assembles the **client-ownership handover package**: one plain-language "start here" summary I give
the client first — what they own, how to run it, what it costs to keep alive, and who to call —
backed by a folder of supporting pieces, each pulled from records and experts friday already has
rather than invented. Those pieces are: a short "when this breaks, do this" runbook from the
operations expert (deploy, backups, what to watch, crisis steps — the small, practical kind, not a
fat incident manual); the running-cost advisor's plain monthly figure for keeping it running; a
"what it is and why" guide that rewrites the technical docs and the decision log's reasoning into
language the owner can actually read; an everyday user guide kept separate from a more technical
admin guide; and an honest-state section naming what's solid, what's known-fragile, and what was
left for later — confidence coming from candour, not polish. Every operate-or-maintain line carries
a tag saying **who can actually do it** — the owner themselves, or someone they'd hire — because
every professional guide assumes a technical reader and friday's owner isn't one. For keys and
secrets, friday never sees a single value: it lists only the **names** of what the product uses
(each account and each setting by name and purpose, read from what the code itself declares) and
hands me a transfer runbook I carry out inside our own secrets manager, where the real values live
and move across to the client's own vault — friday has no way to read a value, by design, and only
records that I've confirmed each one moved. It writes down a bug-fix warranty note pre-filled with
the industry norm — 30 days, covering only what was already in scope, not new requests — which I can
change or waive, and, only if I choose to offer it, a clearly separate stay-on maintenance proposal
(a plain monthly figure, never bundled into the handover itself). And it refuses to call the
handover done until four things are true and I've confirmed each: the record reconciled, every key
confirmed moved into the client's name with my access and recovery removed, at least one real
restore actually tested, and a named person on the client side who has acknowledged receiving the
package — friday records who confirmed each and when, and shows me exactly what's still outstanding
instead of dead-ending. What I end with is a package a stranger who never met the project could act
on: the client can run it, understand it, budget for it, prove it works, and — whenever they want —
take it to any other developer and leave with confidence.

_Sources: handoff-industry-standards.md (synthesis of Lanes A–D). Decisions: D-0053 (scope: package
+ upkeep view + optional stay-on), D-0054 (four operator-attested hard gates), D-0055 (30-day
in-scope warranty, adjustable), D-0056/D-0057 (secrets — names only; values live in the operator's
secrets manager, never handled by friday), D-0058 (reconcile-first = deterministic drift check →
offer, never inline). Build shape: deterministic spine (gates, name-only inventory, cost/test
compilation, attestation via the substrate) + LLM narrative for the plain-language guides._

## Killed (no paragraphs — recorded for the manual's changelog)

- `review` — alias of reassess; one command, one name.
- `sweep` — absorbed into reconcile.
- `autopilot` — served the retired per-feature loop; irrelevant to the one-shot approach.
- `approvals` + the entire ask-parking mechanism — PM-gated decisions now STALL the build
  (if a question clears the bar for asking, it clears the bar for waiting).
- `reassess` — its reason to exist was drift between build and intent; the rebuilt front
  ceremony engineered that risk out. Jobs relocated: living-system health → reconcile's battery;
  amending an unbuilt increment → feature's re-open mode; the body-spec pivot → a documented
  re-discovery flow (superseding spec, full approval), not a standing command; discoverability →
  feedback's triage routes all "I changed my mind" cases.

consumer: rebuild build pass
