# Understanding the client's world at intake — practices worth encoding into the intake role contract

consumer: commands/intake.md — cited by the intake door for the brownfield current-state craft

_Research brief #2 on intake, 2026-07-13 — companion to client-intake-practice.md (which covers
scope/logistics: goals-before-features, budget/timeline/decision-maker, out-of-scope, bounds,
change process, access/ownership, sign-offs). This brief: the client's technical environment,
business domain, and real requirements — especially with NON-TECHNICAL clients._

## A. Audit their technical environment before proposing anything

1. **Build a system map, not a tool list.** For every tool/platform they use, record what it connects to, and for each connection the new work must touch: standard hookup available, custom work needed, or known limits. Integration surprises are the classic mid-project blowup. (Digital-agency redesign-requirements practice — LowCode Agency, Classic City Consulting questionnaires.)
2. **Trace the data separately from the tools:** where each kind of data lives, which copy is the "real" one when copies disagree, and how clean it is. Bad data surfaces at migration time if not at intake. (IT discovery/due-diligence practice — ScienceSoft, DevCom.)
3. **Ask for the industry's rulebook up front** — privacy laws, accessibility standards, sector regulations — because these silently constrain design, data handling, and analytics. (Agency discovery checklists — Clear Digital, LowCode.)
4. **Read before you ask:** existing manuals, spreadsheets, reports, and prior vendor docs are a first-class information source, not a formality. (BABOK's nine elicitation techniques include document analysis and interface analysis.)
5. **Interview beyond the boss** — the people who actually touch the systems (sales, support, admin) hold requirements the owner can't state. (Agency discovery practice; NN/g workshop guidance.)

## B. Learn how their business actually works

6. **Take the apprentice stance:** treat the client as the master of their craft and yourself as the trainee — learn in their setting, ask "obvious" questions, and say your understanding back mid-conversation so they can correct it on the spot. (Beyer & Holtzblatt, *Contextual Design* — the four principles: context, partnership, interpretation, focus.)
7. **Map the process WITH them,** service-blueprint style: what the customer sees vs. what happens behind the scenes. Co-drawing the map turns it into a live fact-check — "participants ensure the artifact represents reality, not assumptions." (NN/g service-blueprinting guides.)
8. **Walk the business as a timeline of events** in the client's own words, zero tech jargon — a lightweight version of Brandolini's Big Picture Event Storming, which is explicitly designed for businesspeople, not developers.

## C. Interview craft for non-technical clients

9. **Open with a "grand tour":** "walk me through a typical order/day/booking" — description before opinion. This is the foundational move of ethnographic interviewing. (Spradley, *The Ethnographic Interview*.)
10. **Concrete past over hypothetical future:** "when did this last happen — what did you do?" beats "what do you need?"; people are honest about what they did and unreliable about what they would do. (Rob Fitzpatrick, *The Mom Test*.)
11. **Adopt their vocabulary and write it down as a shared glossary;** never translate their terms into tech terms or make them learn yours — the constant back-and-forth translation is where meaning gets lost. (Eric Evans' "ubiquitous language" from Domain-Driven Design; Fowler.)
12. **When handed a solution ("build me X"), pivot to "what do you need to *do* with it?"** — Wiegers shows this recovers the underlying need — then a short chain of "why" (laddering, ~3 max) to reach the real problem. (Karl Wiegers, *Software Requirements Essentials*; IxDF on laddering.)

## D. Weight observation over statements

13. **Trust what they do over what they say** — self-reports of one's own work are roughly "three steps removed from the truth." (Jakob Nielsen, "First Rule of Usability? Don't Listen to Users," NN/g.)
14. **Solo-viable version: one screen-share session on a real, current task** — "show me how you do it today." Watch specifically for workarounds and tolerated annoyances; those are requirements nobody will ever state. Ask to see the actual spreadsheet or paper form — artifacts encode the process people forget to mention. (NN/g "Remote Contextual Inquiry"; BABOK observation/shadowing.)

## E. Pre-research the domain so interview time goes to what's unique

15. **Before the interview, research the industry's standard workflow, common tools of that trade, and regulatory basics** — this buys trust ("speak the industry language") and frees interview time for this client's specifics. (Consulting/sales pre-call research practice — Aircover, Zendesk, management.org.)
16. **Treat pre-research as hypotheses, not facts:** present it for correction — "usually this works like X; is it different for you?" This also gives the interview a deliberate lens, Beyer & Holtzblatt's "focus" principle.

## F. Brownfield current-state assessment — operational craft (friday field lessons)

_When intake runs against an existing site, these are the execution details the
generic practices above assume but don't spell out. Salvaged from the pre-rebuild
intake command (D-0041) so the lean door can cite them instead of carrying them._

17. **Crawl with `curl`, not `WebFetch`.** `WebFetch` force-upgrades HTTP→HTTPS and
    `ECONNRESET`s on the HTTP-only legacy stacks brownfield is full of. Parse the
    fetched pages for structure (pages, nav), stack fingerprints (`Server` /
    `X-Powered-By` headers, generator meta, JS libs), SEO (titles, meta
    descriptions, analytics), and security posture (HTTPS presence, admin-login
    exposure, EOL components).
18. **Ownership picture via `WHOIS` + `dig`** (A / NS / MX / TXT) → registrar, host,
    email host, domain-expiry. This is the "who holds the keys" evidence the
    ownership-probing practice (#12) needs, gathered mechanically.
19. **Content audit: classify every page Keep / Kill / Consolidate / Create,** with an
    action + reason per URL; pull ≥12 months of analytics if available. Where the
    legacy analytics is dead or absent (common — e.g. sunset Universal Analytics),
    the audit and the success-baseline drop to **qualitative** — flag it, reconstruct
    from Search Console if present.
20. **Delivery-footprint scan (best-effort, never blocking):** intake usually predates
    repo/hosting handover, so only if the client has already granted a checkout or
    hosting-panel access — scan for `.github/workflows/*`, `netlify.toml`,
    `vercel.json`, `supabase/config.toml`, `Dockerfile`/compose. Record what's found,
    or "not assessed — no repo access yet," so the strategist reconciles against what
    exists instead of proposing blind.
21. **Migration prep: a one-to-one 301 redirect map** of every existing URL to its best
    new destination — never a blanket redirect to the homepage (Google reads that as a
    soft-404).
22. **Locked-out domain recovery (`.uk`):** if the client can't get their domain because
    the original developer holds it and won't transfer, the formal route is **Nominet
    DRS**: complaint → free mediation → Expert decision (£750+VAT) → appeal
    (£3,000+VAT). Two-part test — you must prove **rights** AND **abusive
    registration** — so a developer legitimately holding it may not lose it; it's
    fact-dependent. (From 7 Jul 2026 DRS filing moves to WIPO; rules/fees/experts
    unchanged.) Distinct from the ordinary developer-handover of the new work product.

Sources: [NN/g contextual inquiry](https://www.nngroup.com/articles/contextual-inquiry/) · [NN/g don't-listen-to-users](https://www.nngroup.com/articles/first-rule-of-usability-dont-listen-to-users/) · [NN/g remote contextual inquiry](https://www.nngroup.com/articles/remote-contextual-inquiry/) · [NN/g blueprint workshops](https://www.nngroup.com/articles/service-blueprinting-workshops/) · [Wiegers elicitation practice](https://www.informit.com/articles/article.aspx?p=3172445) · [Fowler, Ubiquitous Language](https://martinfowler.com/bliki/UbiquitousLanguage.html) · [Big Picture Event Storming](https://www.qlerify.com/event-storming-concepts/what-is-big-picture-event-storming) · [Spradley descriptive questions](https://jan.ucc.nau.edu/~pms/cj355/readings/spradley.pdf) · [Mom Test summary](https://readingraphics.com/book-summary-the-mom-test/) · [BABOK elicitation](https://www.iiba.org/knowledgehub/business-analysis-body-of-knowledge-babok-guide/4-elicitation-and-collaboration/) · [redesign requirements capture](https://www.lowcode.agency/blog/website-redesign-requirements-what-to-capture) · [integration questionnaire](https://classiccity.com/website-functionality-and-integration-questionnaire/) · [pre-call research](https://www.aircover.ai/blog/discovery-call-pre-call-research) · [IxDF laddering](https://ixdf.org/literature/article/laddering-questions-drilling-down-deep-and-moving-sideways-in-ux-research)
