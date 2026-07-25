#!/usr/bin/env python3
"""friday shared substrate library — THE single home for `.friday/` writes.

Why one module (ISSUE-006 / NFR-4, D-0003): old friday's journal writer was
duplicated across three files under a "self-contained hook" rule, and 9+ of
~14 spawning surfaces never got instrumented because instrumentation was
retrofitted piecemeal. vnext inverts that: every hook, CLI tool, and command
surface that touches `.friday/` goes through this module — exactly one code
path per write kind. Hooks import it via the plugin root they already receive;
an import failure degrades to "no telemetry" (hooks always exit 0), never a
broken session.

Worktree rule (Appendix B, LANDMINE): git worktrees do not share gitignored
files, so `.friday/` is keyed to the CANONICAL repo, never the working tree —
`resolve_project_root()` uses `git rev-parse --git-common-dir` (the shared
`.git` even from inside a linked worktree) and takes its parent. Worktrees
isolate code; they share substrate. Never resolve `.friday/` against cwd.
Tracked files (docs/DECISIONS.md etc.) belong to the CHECKOUT instead —
`resolve_worktree_root()` — because code isolation is the point of a worktree.

Journal envelope (kept verbatim from old friday, D-0005): one JSON object per
line — {"ts","feature","phase","event","by"[,"data"]} — written as a single
O_APPEND write of one newline-terminated line <= 4096 bytes (atomic on POSIX).
A larger line is OUR contract violation: raised, never truncated.

Session liveness (Appendix B.3): per-session lock files under
`.friday/sessions/<session-id>.lock` (multiple concurrent worktree sessions
each need honest liveness); absence-of-ticking is the crash signal — locks are
never removed on unclean death.

ISSUE-007 (harness fact, anthropics/claude-code#27755): SubagentStop matchers
cannot be trusted to filter by agent type — `agent_type` may arrive empty or
missing. `event_matches_agent()` is the in-hook identity check every
SubagentStop-scoped hook must call; a foreign event never arms and NEVER
clears an armed gate.

Pure stdlib.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone

# Pinned writer vocabulary. Readers tolerate unknown values; writers emitting
# one is a contract violation of our own emission — rejected at the boundary.
BY_VOCABULARY = ("lead", "pm", "session", "tool")

# Journal event vocabulary (extended from old friday; readers skip unknowns).
# U1 stamping pass (D-0010) adds four guard-journaled kinds: file-edited
# (#17 thrash detector), elicitation (#16, covers PermissionDenied too),
# install-self-check (#19), config-change (#21). Guard #20 (clean-exit stamp)
# needed no new kind — session_lifecycle.py's existing session-end event on
# SessionEnd already covers it; nothing emits a separate "clean-exit".
EVENT_VOCABULARY = (
    "session-start", "session-end", "usage", "question-answered",
    "spawn", "accept", "done",
    "decision-captured", "state-transition",
    "file-edited", "elicitation", "install-self-check", "config-change",
    "lane-opened", "lane-cleared",
    "graph-refreshed",  # U6/FR-71: the code graph re-stamped at a commit.
    "handoff-attest",  # US-18/FR-85: an operator-attested handoff completion gate.
    "compaction-filed",  # INC-001/FR-1.2: a compaction summary filed to its drawer.
)

_SESSION_ID_SAFE = re.compile(r"[^A-Za-z0-9._-]")
_GIT_SHA = re.compile(r"[0-9a-fA-F]{7,40}\Z")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --- root resolution (Appendix B) ---------------------------------------------

def _git(cwd: str, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", cwd, *args],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out or None


def resolve_project_root(cwd: str = ".") -> str:
    """The CANONICAL project root — parent of the shared git common dir. From a
    linked worktree this is the MAIN repo, so every worktree reads/writes one
    `<main-repo>/.friday/`. Falls back to abspath(cwd) outside any git repo
    (the substrate still works un-gitted; it just can't be worktree-shared)."""
    cwd = os.path.abspath(cwd)
    common = _git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common is None:  # older git without --path-format
        common = _git(cwd, "rev-parse", "--git-common-dir")
        if common is not None and not os.path.isabs(common):
            common = os.path.join(cwd, common)
    if common is None:
        return cwd
    return os.path.dirname(os.path.normpath(os.path.abspath(common)))


def resolve_worktree_root(cwd: str = ".") -> str:
    """The CHECKOUT root (`--show-toplevel`) — where tracked files live. In a
    linked worktree this differs from resolve_project_root() by design."""
    cwd = os.path.abspath(cwd)
    top = _git(cwd, "rev-parse", "--show-toplevel")
    return os.path.abspath(top) if top else cwd


def friday_dir(cwd: str = ".") -> str:
    return os.path.join(resolve_project_root(cwd), ".friday")


# --- engagement guard -----------------------------------------------------------

def is_friday_project(cwd: str = ".") -> bool:
    """Engage only where a friday project exists or is plausibly in progress —
    never lazily create a stray `.friday/` in an arbitrary directory."""
    root = resolve_worktree_root(cwd)
    if os.path.isfile(os.path.join(root, "docs", "TECHNICAL_SOW.md")):
        return True
    try:
        with open(os.path.join(root, "CLAUDE.md"), encoding="utf-8") as fh:
            text = fh.read()
        return "FRIDAY-CLAIMS:BEGIN" in text or "FRIDAY-STATE:BEGIN" in text
    except OSError:
        return False


def should_engage(cwd: str = ".") -> bool:
    """Union guard: an existing shared `.friday/` is sufficient on its own
    (covers the first session of a project whose markers are still being
    seeded), OR the project heuristic passes."""
    return os.path.isdir(friday_dir(cwd)) or is_friday_project(cwd)


# --- journal (the single writer) --------------------------------------------------

def build_journal_line(event: str, phase: str, feature: str = "-", by: str = "lead",
                       data: dict | None = None, ts: str | None = None) -> dict:
    """Assemble one envelope line, core keys in canonical order. Raises
    ValueError on any boundary violation; performs no I/O."""
    if not event or not event.strip():
        raise ValueError("event must be a non-empty string")
    if event not in EVENT_VOCABULARY:
        raise ValueError(f"event must be one of {'|'.join(EVENT_VOCABULARY)}, got {event!r}")
    if not phase or not phase.strip():
        raise ValueError("phase must be a non-empty string")
    if by not in BY_VOCABULARY:
        raise ValueError(f"by must be one of {'|'.join(BY_VOCABULARY)}, got {by!r}")
    if data is not None and not isinstance(data, dict):
        raise ValueError("data must be a JSON object (the envelope's only extension slot)")
    line: dict = {"ts": ts or now_iso(), "feature": feature or "-",
                  "phase": phase, "event": event, "by": by}
    if data is not None:
        line["data"] = data
    return line


def append_journal_line(cwd: str, line: dict) -> None:
    """One O_APPEND write of a single newline-terminated JSON line <= 4096
    bytes, lazy-creating `<shared>/.friday/journal.jsonl`."""
    fdir = friday_dir(cwd)
    os.makedirs(fdir, exist_ok=True)
    path = os.path.join(fdir, "journal.jsonl")
    payload = (json.dumps(line, separators=(",", ":")) + "\n").encode("utf-8")
    if len(payload) > 4096:
        raise ValueError(f"journal line exceeds 4096 bytes: {len(payload)}")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


# --- lane-open sentinel (contract: docs/contracts/lane-open.md; D-0023/U3) ---------

LANES = ("bug", "patch", "feature")


def lane_open(cwd: str, *, lane: str, id: str, trail: str,
              regression_test: str | None = None,
              blast_radius: list[str] | None = None) -> str:
    """Open a maintenance lane: write the guard-#6/#11/#12 arming sentinel
    through the single substrate writer (never by hand — house rule). One
    lane at a time: an already-open lane raises naming it (an open lane is a
    stalled question, not a stack). Contract fields enforced at write time:
    lane=bug REQUIRES regression_test; lane=patch REQUIRES a non-empty
    blast_radius. Returns the sentinel path. Disarm is NOT here: the owning
    guard removes the sentinel on pass; `lane_clear()` removes it deliberately
    — `by=pm` (escalation) or `by=lead` (a door's honest re-route/close)."""
    if lane not in LANES:
        raise ValueError(f"lane must be one of {LANES}, got {lane!r}")
    if not id or not trail:
        raise ValueError("lane_open requires a non-empty id and trail path")
    if lane == "bug" and not regression_test:
        raise ValueError("a bug lane opens WITH its regression-test path "
                         "(docs/contracts/lane-open.md) — no bug closes without one")
    if lane == "patch" and not blast_radius:
        raise ValueError("a patch lane opens WITH its declared blast-radius list "
                         "(docs/contracts/lane-open.md) — an undeclared radius is the lie")
    fdir = friday_dir(cwd)
    os.makedirs(fdir, exist_ok=True)
    path = os.path.join(fdir, "lane-open")
    data: dict = {"lane": lane, "id": id, "trail": trail}
    if regression_test:
        data["regression-test"] = regression_test
    if blast_radius:
        data["blast-radius"] = list(blast_radius)
    # A9: claim the single-lane sentinel ATOMICALLY (O_CREAT|O_EXCL) — the old
    # isfile()-then-os.replace() was a TOCTOU two shared-substrate worktrees both
    # passed, silently clobbering each other's open lane.
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        try:
            with open(path, encoding="utf-8") as fh:
                existing = json.load(fh).get("id", "?")
        except Exception:
            existing = "?"
        raise ValueError(f"a lane is already open ({existing}) — close it or "
                         "lane_clear() it before opening another")
    try:
        os.write(fd, json.dumps(data).encode("utf-8"))
    finally:
        os.close(fd)
    try:
        append_journal_line(cwd, build_journal_line(
            "lane-opened", "maintenance", by="lead",
            data={"lane": lane, "id": id}))
    except Exception:
        pass
    return path


def lane_clear(cwd: str, *, by: str = "pm") -> bool:
    """Remove an open lane's sentinel, recording who did it. Two real callers:
    `by="pm"` (the default) is the conscious PM-escalation removal named in the
    block message; `by="lead"` is a door's own honest re-route or close — a
    patch outgrowing its radius (FR-18), a bug closing unpindownable (FR-8) —
    where no PM is in the loop and stamping it as an escalation would lie. True
    if a sentinel was removed; False when none was open (the defined empty case)."""
    if by not in ("pm", "lead"):
        raise ValueError(f"lane_clear by= must be 'pm' or 'lead', got {by!r}")
    path = os.path.join(friday_dir(cwd), "lane-open")
    try:
        os.remove(path)
    except OSError:
        return False
    try:
        append_journal_line(cwd, build_journal_line(
            "lane-cleared", "maintenance", by=by, data={}))
    except Exception:
        pass
    return True


# --- code-graph freshness stamp (FR-71; guard #8 reads it) -------------------------

def graph_stamp_write(cwd: str, commit: str) -> str:
    """Record the commit the ADOPTED code graph was last refreshed at, at
    `<shared .friday>/graph.stamp` — the counterpart guard #8
    (graph_freshness_check.py) reads back to compute "N commits behind". Written
    ONLY by the refresh flow (graph_refresh.py), and only AFTER docs regenerate:
    the code → docs → graph ordering (FR-71) lives in the caller's sequencing,
    this writer just records the result. Atomic same-dir temp + os.replace so the
    guard never reads a torn stamp. A non-SHA is rejected here rather than passed
    through, because guard #8 turns an unresolvable stamp into no-verdict
    (fail-open) — which would silently hide staleness. Returns the stamp path."""
    commit = (commit or "").strip()
    if not _GIT_SHA.match(commit):
        raise ValueError(f"graph.stamp needs a git commit SHA, got {commit!r}")
    fdir = friday_dir(cwd)
    os.makedirs(fdir, exist_ok=True)
    path = os.path.join(fdir, "graph.stamp")
    fd, tmp = tempfile.mkstemp(prefix=".graph.stamp.", dir=fdir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(commit + "\n")
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise
    with contextlib.suppress(Exception):
        append_journal_line(cwd, build_journal_line(
            "graph-refreshed", "reference", by="lead", data={"commit": commit}))
    return path


# --- per-session locks (Appendix B.3) ----------------------------------------------

def _lock_path(cwd: str, session_id: str) -> str:
    safe = _SESSION_ID_SAFE.sub("_", session_id) or "unknown"
    return os.path.join(friday_dir(cwd), "sessions", f"{safe}.lock")


def write_session_lock(cwd: str, session_id: str, lock: dict) -> None:
    """Atomic same-dir temp + os.replace — a reader never observes a torn lock;
    an externally-corrupted lock self-heals on the next tick."""
    path = _lock_path(cwd, session_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".lock.", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(lock, fh)
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


def read_session_locks(cwd: str) -> dict[str, dict]:
    """{session_id: lock} for every parseable lock; unreadable files skipped."""
    sess_dir = os.path.join(friday_dir(cwd), "sessions")
    out: dict[str, dict] = {}
    try:
        names = os.listdir(sess_dir)
    except OSError:
        return out
    for name in sorted(names):
        if not name.endswith(".lock"):
            continue
        try:
            with open(os.path.join(sess_dir, name), encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            out[name[:-5]] = data
    return out


def remove_session_lock(cwd: str, session_id: str) -> None:
    with contextlib.suppress(OSError):
        os.remove(_lock_path(cwd, session_id))


# --- ISSUE-007 in-hook identity check -----------------------------------------------

_TYPE_KEYS = ("agent_type", "subagent_type", "agentType", "subagentType")


def agent_type_from_event(event: dict) -> str | None:
    """Best-effort extraction of the stopping subagent's type. `agent_type` is
    the documented field; #27755 records it empty/missing in the wild."""
    for key in _TYPE_KEYS:
        val = event.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    agent = event.get("agent")
    if isinstance(agent, dict):
        for key in ("type", *_TYPE_KEYS):
            val = agent.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def event_matches_agent(event: dict, needle: str) -> str:
    """'match' | 'foreign' | 'typeless'. Callers decide the typeless posture
    per hook (documented in each hook's docstring, TEST-07/TEST-08); a
    'foreign' event must never arm and NEVER clear an armed gate."""
    agent_type = agent_type_from_event(event)
    if agent_type is None:
        return "typeless"
    return "match" if needle.lower() in agent_type.lower() else "foreign"


# --- compaction package (INC-001; contract: docs/contracts/compaction-package.md) --

COMPACTION_UNATTRIBUTED = "unattributed"
COMPACTION_UNKEYED_SESSION = "unkeyed"


def current_session_id(cwd: str = ".") -> str:
    """Best-effort current session: the newest session lock by mtime (the
    session-lifecycle hook maintains locks), else the unkeyed sentinel. CLIs
    use this so a lead never has to know its own session id; hooks prefer the
    event payload's session_id."""
    sess_dir = os.path.join(friday_dir(cwd), "sessions")
    newest, newest_mtime = None, -1.0
    try:
        for name in os.listdir(sess_dir):
            if not name.endswith(".lock"):
                continue
            try:
                mtime = os.path.getmtime(os.path.join(sess_dir, name))
            except OSError:
                continue
            if mtime > newest_mtime:
                newest, newest_mtime = name[:-5], mtime
    except OSError:
        pass
    return newest or COMPACTION_UNKEYED_SESSION
COMPACTION_LAYERS = ("mission", "orientation")
_HANDOFF_HEADER_RE = re.compile(r"^handoff-of:\s*([a-z0-9][a-z0-9-]{0,63})\s*(?:—.*)?$")


def strip_summarizer_envelope(summary: str) -> str:
    """The raw compact_summary payload arrives wrapped in the summarizer's
    <analysis>…</analysis><summary>…</summary> envelope (fixture-proven on
    CLI 2.1.210); the handoff the steering spec mandated lives INSIDE the
    summary block. Returns the summary-block body when the envelope is
    present (unclosed tag: to end of text), the text unchanged otherwise."""
    m = re.search(r"<summary>\s*\n?(.*?)(?:</summary>|\Z)", summary, re.DOTALL)
    return m.group(1) if m else summary


def parse_handoff_header(summary: str) -> str | None:
    """The self-ID header (FR-1.4): `handoff-of: <slug>[ — <scope>]` on the
    first non-empty line, seen through the summarizer envelope. Returns the
    agent slug, or None when the line is missing/garbled — the caller's
    fallback is archive-only filing, never a current-pointer touch."""
    for line in strip_summarizer_envelope(summary).splitlines():
        if line.strip():
            m = _HANDOFF_HEADER_RE.match(line.strip())
            if m is None or m.group(1) == COMPACTION_UNATTRIBUTED:
                # the fallback drawer's name is reserved — a summary claiming
                # it would grow a current.md inside the one drawer the
                # contract forbids one in
                return None
            return m.group(1)
    return None


def _compaction_drawer(cwd: str, session_id: str, agent: str) -> str:
    def _safe(name: str) -> str:
        s = _SESSION_ID_SAFE.sub("_", name)
        s = re.sub(r"\.{2,}", "_", s).lstrip(".")
        return s or "_"
    return os.path.join(friday_dir(cwd), "compaction", _safe(session_id), _safe(agent))


def compaction_file_summary(cwd: str, *, session_id: str, summary: str,
                            ts: str | None = None) -> dict:
    """File one finished compaction summary (FR-1.2): ALWAYS an append-only
    timestamped generation in the authoring agent's drawer (the RAW payload —
    the complete record); the drawer's `current.md` is updated ONLY when the
    self-ID header parses, and holds the envelope-stripped handoff body (the
    re-orientation reader injects it; summarizer scratch would waste its
    cap). An unattributed summary is archived under the shared unattributed
    drawer and can never touch any current pointer. Nothing is ever
    overwritten."""
    agent = parse_handoff_header(summary)
    attributed = agent is not None
    drawer = _compaction_drawer(cwd, session_id, agent or COMPACTION_UNATTRIBUTED)
    gen_dir = os.path.join(drawer, "generations")
    os.makedirs(gen_dir, exist_ok=True)
    stamp = (ts or now_iso()).replace(":", "-")
    path = os.path.join(gen_dir, f"{stamp}.md")
    n = 1
    while os.path.exists(path):  # same-second filing: bump, never overwrite
        n += 1
        path = os.path.join(gen_dir, f"{stamp}-{n}.md")
    with open(path, "x", encoding="utf-8") as fh:
        fh.write(summary)
    if attributed:
        tmp = os.path.join(drawer, ".current.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(strip_summarizer_envelope(summary))
        os.replace(tmp, os.path.join(drawer, "current.md"))
    generation_rel = os.path.relpath(path, friday_dir(cwd))
    try:
        append_journal_line(cwd, build_journal_line(
            "compaction-filed", "compaction", by="tool",
            data={"agent": agent or COMPACTION_UNATTRIBUTED,
                  "attributed": attributed, "generation": generation_rel}))
    except (ValueError, OSError):
        pass  # telemetry never blocks the filing itself
    return {"agent": agent or COMPACTION_UNATTRIBUTED, "attributed": attributed,
            "generation": generation_rel, "current_updated": attributed}


def compaction_write_layer(cwd: str, *, session_id: str, agent: str,
                           layer: str, text: str) -> str:
    """Persist a deterministic package layer (FR-1.5 mission / FR-1.6
    orientation) into the agent's drawer. Overwrite is allowed — these are
    living records their owner updates; the never-overwrite rule protects
    the generations archive, not the layers."""
    if layer not in COMPACTION_LAYERS:
        raise ValueError(f"layer must be one of {'|'.join(COMPACTION_LAYERS)}, got {layer!r}")
    if agent == COMPACTION_UNATTRIBUTED:
        raise ValueError(f"agent name {COMPACTION_UNATTRIBUTED!r} is reserved "
                         "for the fallback drawer")
    drawer = _compaction_drawer(cwd, session_id, agent)
    os.makedirs(drawer, exist_ok=True)
    tmp = os.path.join(drawer, f".{layer}.tmp")
    path = os.path.join(drawer, f"{layer}.md")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)
    return path


def compaction_read_package(cwd: str, *, session_id: str, agent: str) -> dict:
    """The four-layer read side (FR-1.8/FR-1.13): mission, orientation, the
    current floor summary, and the archive depth. The empty case — no
    compaction state at all — is a valid, all-None package, never an error."""
    drawer = _compaction_drawer(cwd, session_id, agent)

    def _read(name: str) -> str | None:
        try:
            with open(os.path.join(drawer, name), encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return None

    gen_dir = os.path.join(drawer, "generations")
    try:
        generations = len([f for f in os.listdir(gen_dir) if f.endswith(".md")])
    except OSError:
        generations = 0
    return {"mission": _read("mission.md"), "orientation": _read("orientation.md"),
            "current": _read("current.md"), "generations": generations}
