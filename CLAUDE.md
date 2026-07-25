# friday — plugin development guide

friday is a Claude Code plugin: pure-stdlib Python 3 tooling + markdown
command/agent surfaces. It was built with its own recipe (the self-build) —
the story is in `docs/BUILD-STORY.md`, the recipe in `docs/TECHNICAL_SOW.md`.

stack: path:python3
stack: path:pytest
non-goal: third-party runtime dependencies (stdlib only, by design)
non-goal: RAG/embeddings anywhere in the retrieval path

## Conventions (the short list)

- Logic-core changes are test-first (`tests/`); run `python3 -m pytest tests/ -q`.
- Every script-checked claim is a typed tag line (`tools/taglines.py`);
  every grammar defines + tests its empty case.
- Contracts in `docs/contracts/` are cited by name on both sides of every
  filesystem handoff — never rename them.
- Generated docs (`docs/architecture/generated/`) stamp their generator in
  line 1 and are regenerated, never hand-edited.
- A file only one lane uses lives in that lane's `skills/<lane>/` folder;
  anything two or more lanes share stays single-homed in `docs/`, cited by
  name from both sides.
- Hooks fail open (a false block is worse than a miss); durable guarantees
  live in out-of-band backstops (receipts, gates).
