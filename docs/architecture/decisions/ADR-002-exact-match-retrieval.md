# ADR-002 — friday-docs retrieval is live-parse + exact-after-normalization, never RAG

**Context.** Teammates need JIT access to sections of large project docs. The
instinctive 2026 build is embeddings + a vector store.

**Decision.** The reader triad live-parses the target file on every call (no
cache in the read path — results can never be stale) and `get_section`
matches headings exactly after a pinned normalization (strip → drop numbering
→ strip trailing `#` → casefold → collapse whitespace → strip emphasis; vnext
strips backtick/asterisk everywhere so "`Config` Surface" matches the query a
human types). No fuzzy matching, no ranking model that can silently
misretrieve. Cross-document aggregates ride an ADVISORY sqlite index,
re-synced at the top of every call and never the source of truth for content.

**Alternatives rejected.** Embeddings/RAG — transcript study (PROP-024)
showed semantic search was **3% of real demand** and 87% of weighted traffic
served under a 25%-of-file-bytes threshold; RAG reintroduces staleness and
silent misretrieval for a use case that does not exist. Fuzzy heading match —
a near-miss that silently returns the wrong section is worse than a miss that
returns the available headings.

**Consequences.** A heading rename breaks retrieval loudly-at-the-consumer,
so script-parsed docs pin their heading sets (docs/contracts/*); misses
return the available headings for a one-retry-then-Read fallback.

`[Sources: TSOW §6.4; DECISIONS.md D-0006; preserve-list §3.1]`
