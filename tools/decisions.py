#!/usr/bin/env python3
"""DECISIONS.md schema library — parser / serializer / monotonic-ID allocator.

Net-new machinery (TSOW §6.6 — the scope correction is explicit: no
DECISIONS.md existed anywhere in old friday; only the ask-mirror MECHANISM is
reused). This module is the single schema authority (A.6): both capture
channels — the hook-fired pm-ratified path and the model-autonomous
log-and-proceed path — append through `append_entry()`.

Serialization (D-0004, contract: docs/contracts/decision-capture.md):

    ## D-0001 — <title>
    **When:** <ISO-8601Z> · **Channel:** pm-ratified|model-autonomous ·
    **Weight:** one-way|two-way · **Floor:** none|<category>[ · **Back-filled:** true]
    - **Decision:** ...
    - **Why:** ...
    - **Rejected:** ...

Empty form (A.2, MUST-NAME): the pinned H1 plus the single sentinel line
`_No decisions captured yet._` — NOT a zero-byte file, a missing file, or a
bare heading. `empty_form()` produces it; `parse()` accepts exactly it as the
valid zero-entry state and rejects sentinel+entries coexisting.

Mechanical classifier checks (A.5 #4): the three-part worthiness JUDGMENT is
the model's; what is mechanical is the closed vocabularies and the PROP-044
categorical override — a floor-category decision is one-way regardless of the
three-part conclusion (`validate_fields`).

Monotonic D-NNNN (A.5 #7, Appendix B.2): allocated under an advisory
`fcntl.flock` on `<shared .friday>/decisions.lock` against a counter file in
the SHARED substrate root, so concurrent writers — including writers in
different worktrees, whose docs/DECISIONS.md checkouts differ — can never
collide or reuse an id. The counter is regenerable: next id is
max(counter, max id in the local file) + 1 — counting ONLY ids inside this
clone's lane (D-0152; `git config friday.decision-id-base`, unset = the low
lane [1, 1000)). Pre-merge the lanes held by construction because each log
held one machine's entries; the 2026-07-29 merged log broke that silently
(first post-merge mint came out D-1007, in the other machine's lane), so the
lane is now enforced here: `_lane_bounds()`.

Growing-log discipline (PROP-023, hard-won lesson #9): entry cap (default
100) with archive-on-overflow — the oldest half MOVES to
docs/decisions/archive-NNN.md, schema-valid, ids preserved. Completion is a
move, not a flag; retrofitting this later is exactly what PROP-023 forbids.

Pure stdlib.
"""
from __future__ import annotations

import fcntl
import os
import re
import subprocess

import friday_substrate as fs
import taglines

EMPTY_SENTINEL = "_No decisions captured yet._"
FLOORS = ("schema-data", "auth-security", "external-api", "friday-claims", "spend")
CHANNELS = ("pm-ratified", "model-autonomous")
WEIGHTS = ("one-way", "two-way")
DEFAULT_PATH = os.path.join("docs", "DECISIONS.md")
DEFAULT_CAP = 100

_H1_RE = re.compile(r"^# Decisions\b")
_ENTRY_RE = re.compile(r"^## (D-(\d{4,})) — (.+?)\s*$")
_META_KEY_RE = re.compile(r"\*\*([A-Za-z-]+):\*\*\s*(.+?)\s*$")
_BULLET_RE = re.compile(r"^- \*\*(Decision|Why|Rejected):\*\*\s*(.*)$")

_MARKER_COMMENT = (
    "<!-- FRIDAY-DECISIONS v1 — append entries via tools/decisions_append.py (never hand-edit\n"
    "     past entries). Schema contract: docs/contracts/decision-capture.md. Growing-log\n"
    "     discipline (PROP-023): entry cap {cap}; overflow MOVES the oldest half to\n"
    "     docs/decisions/archive-NNN.md — completion is a move, not a flag. -->"
)


# --- serializer -----------------------------------------------------------------

def empty_form(project: str = "friday project", cap: int = DEFAULT_CAP) -> str:
    """The A.2 zero-decision serialization — exact, tested, produced on init."""
    return (f"# Decisions — {project}\n\n"
            f"{_MARKER_COMMENT.format(cap=cap)}\n\n"
            f"{EMPTY_SENTINEL}\n")


def format_entry(*, id_num: int, title: str, when: str, channel: str, weight: str,
                 floor: str, back_filled: bool, decision: str, why: str,
                 rejected: str, override_grant: str | None = None) -> str:
    meta = (f"**When:** {when} · **Channel:** {channel} · "
            f"**Weight:** {weight} · **Floor:** {floor}")
    if back_filled:
        meta += " · **Back-filled:** true"
    out = (f"## D-{id_num:04d} — {title}\n"
           f"{meta}\n"
           f"- **Decision:** {decision}\n"
           f"- **Why:** {why}\n"
           f"- **Rejected:** {rejected}\n")
    if override_grant:
        out += f"override-grant: {override_grant}\n"
    return out


def has_override_grant(decisions_text: str, target: str) -> bool:
    """True iff a typed `override-grant: <value>` line names `target` — the
    structured, affirmative authorization every frozen-artifact guard (#3/#5/#7/
    #10) requires before an edit to a frozen artifact is permitted. A bare mention
    of the target anywhere in the log, or a mention inside a rejection, NEVER
    counts (that substring hole was the harden's finding A3). FR-55."""
    tgt = target.strip().lower()
    base = os.path.basename(target).strip().lower()
    words = re.findall(r"[a-z0-9]+", tgt)
    distinctive = max(words, key=len) if words else tgt  # longest token (a path base or an element name)
    needles = {n for n in (tgt, base, distinctive) if n and len(n) >= 3}
    for line in decisions_text.splitlines():
        parsed = taglines.parse_typed_line(line)
        if not parsed or parsed[0] != "override-grant":
            continue
        val = parsed[1].lower()
        if any(n in val for n in needles):
            return True
    return False


# --- mechanical classifier checks (A.5 #4) -----------------------------------------

def validate_fields(channel: str, weight: str, floor: str) -> list[str]:
    """Closed vocabularies + the PROP-044 categorical override. Returns [] when
    valid, else human-readable errors (never raises — callers decide)."""
    errs: list[str] = []
    if channel not in CHANNELS:
        errs.append(f"channel must be one of {'|'.join(CHANNELS)}, got {channel!r}")
    if weight not in WEIGHTS:
        errs.append(f"weight must be one of {'|'.join(WEIGHTS)}, got {weight!r}")
    if floor != "none" and floor not in FLOORS:
        errs.append(f"floor must be 'none' or one of {'|'.join(FLOORS)}, got {floor!r}")
    if floor != "none" and floor in FLOORS and weight != "one-way":
        errs.append(f"floor category {floor!r} forces weight one-way "
                    "(PROP-044 categorical override) — got two-way")
    return errs


# --- parser --------------------------------------------------------------------------

def parse(text: str) -> dict:
    """{ok, empty, entries[], errors[]}. Precision-first: unknown prose between
    entries is tolerated; structural violations of the pinned grammar are not."""
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or not _H1_RE.match(lines[0]):
        return {"ok": False, "empty": False, "entries": [],
                "errors": ["missing pinned H1 '# Decisions …' on line 1"]}

    has_sentinel = any(ln.strip() == EMPTY_SENTINEL for ln in lines)
    entries: list[dict] = []
    current: dict | None = None

    def close(entry: dict | None) -> None:
        if entry is None:
            return
        for field in ("when", "channel", "weight", "floor"):
            if field not in entry:
                errors.append(f"{entry['id_str']}: missing **{field.capitalize()}:** on the meta line")
        for field in ("decision", "why", "rejected"):
            if field not in entry:
                errors.append(f"{entry['id_str']}: missing - **{field.capitalize()}:** bullet")
        errors.extend(f"{entry['id_str']}: {e}" for e in validate_fields(
            entry.get("channel", ""), entry.get("weight", ""), entry.get("floor", "none")))
        entries.append(entry)

    for ln in lines[1:]:
        m = _ENTRY_RE.match(ln)
        if m:
            close(current)
            current = {"id_str": m.group(1), "id": int(m.group(2)),
                       "title": m.group(3), "back_filled": False}
            continue
        if current is None:
            continue
        bm = _BULLET_RE.match(ln)
        if bm:
            current[bm.group(1).lower()] = bm.group(2)
            continue
        if ln.startswith("**When:**"):
            for part in ln.split(" · "):
                km = _META_KEY_RE.search(part)
                if not km:
                    continue
                key, val = km.group(1).lower(), km.group(2)
                if key == "back-filled":
                    current["back_filled"] = val.strip().lower() == "true"
                else:
                    current[key] = val
    close(current)

    if entries and has_sentinel:
        errors.append("sentinel line coexists with entries — the first append "
                      "must REPLACE the empty form's sentinel")
    if not entries and not has_sentinel:
        errors.append(f"zero entries but no '{EMPTY_SENTINEL}' sentinel — not a "
                      "valid empty form (A.2)")
    ids = [e["id"] for e in entries]
    if len(set(ids)) != len(ids):
        errors.append("duplicate D-NNNN ids")

    return {"ok": not errors, "empty": (not entries and has_sentinel),
            "entries": entries, "errors": errors}


def parse_file(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return parse(fh.read())
    except OSError as exc:
        return {"ok": False, "empty": False, "entries": [],
                "errors": [f"unreadable: {exc}"]}


# --- decision-ask shape (Channel A contract) ---------------------------------------

_ASK_MARKER_RE = re.compile(r"^\[FRIDAY-DECISION\]\s+(.+?)\s*$")


def parse_decision_ask(question_text: str) -> dict | None:
    """The narrow decision-ask shape the Channel-A hook fires on — and ONLY it
    (ordinary permission dialogs / clarifying questions never parse, so the
    log is never flooded with permission-grant noise). First line:
    `[FRIDAY-DECISION] <title>`; then typed lines decision:/why:/rejected:/
    floor:/weight: (tag-line grammar)."""
    lines = question_text.strip().splitlines()
    if not lines:
        return None
    m = _ASK_MARKER_RE.match(lines[0].strip())
    if not m:
        return None
    out = {"title": m.group(1), "decision": "", "why": "", "rejected": "",
           "floor": "none", "weight": "two-way"}
    import taglines
    for ln in lines[1:]:
        parsed = taglines.parse_typed_line(ln)
        if parsed and parsed[0] in ("decision", "why", "rejected", "floor", "weight"):
            out[parsed[0]] = parsed[1]
    return out


# --- monotonic append (A.5 #7 / Appendix B.2) ----------------------------------------

def _locked(root: str):
    """Advisory-lock context on the SHARED substrate root's decisions.lock."""
    fdir = fs.friday_dir(root)
    os.makedirs(fdir, exist_ok=True)
    return open(os.path.join(fdir, "decisions.lock"), "a+")


def _lane_bounds(root: str) -> tuple[int, int]:
    """This clone's decision-id lane [lo, hi) — D-0152's rule, enforced.

    `git config friday.decision-id-base`: unset/invalid = 0 → the low lane
    [1, 1000); a machine configured with base N mints only inside
    [N, N+1000) — the same 'next = highest inside my range + 1, or the base
    when empty' shape as INC/PROP allocation (D-0113). Enforcement exists
    because the merged log killed the by-construction guarantee: allocation
    is highest-seen + 1, and post-merge 'seen' includes the other machine's
    entries."""
    base = 0
    try:
        out = subprocess.run(
            ["git", "-C", root, "config", "--get", "friday.decision-id-base"],
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            base = int(out.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        base = 0
    return (max(base, 1), base + 1000)


def _read_counter(root: str) -> int:
    try:
        with open(os.path.join(fs.friday_dir(root), "decisions.counter"), encoding="utf-8") as fh:
            return int(fh.read().strip() or "0")
    except (OSError, ValueError):
        return 0


def _write_counter(root: str, value: int) -> None:
    path = os.path.join(fs.friday_dir(root), "decisions.counter")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(str(value))
    os.replace(tmp, path)


def append_entry(root: str, *, title: str, decision: str, why: str, rejected: str,
                 channel: str = "model-autonomous", weight: str = "two-way",
                 floor: str = "none", back_filled: bool = False,
                 when: str | None = None, path: str = DEFAULT_PATH,
                 cap: int = DEFAULT_CAP, project: str | None = None,
                 override_grant: str | None = None) -> tuple[str, str]:
    """Append one schema-valid entry; returns (id_str, entry_text). Raises
    ValueError on invalid fields (nothing written). The file written is the
    CHECKOUT's copy (worktrees isolate code); the id counter is the SHARED
    substrate's (worktrees share substrate) — Appendix B resolved."""
    errs = validate_fields(channel, weight, floor)
    if errs:
        raise ValueError("; ".join(errs))
    wroot = fs.resolve_worktree_root(root)
    abs_path = os.path.join(wroot, path)

    with _locked(root) as lockfh:
        fcntl.flock(lockfh, fcntl.LOCK_EX)
        try:
            if os.path.isfile(abs_path):
                with open(abs_path, encoding="utf-8") as fh:
                    text = fh.read()
            else:
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                text = empty_form(project or os.path.basename(wroot), cap)
            parsed = parse(text)
            lane_lo, lane_hi = _lane_bounds(root)
            local_max = max((e["id"] for e in parsed["entries"]
                             if lane_lo <= e["id"] < lane_hi),
                            default=lane_lo - 1)
            counter = _read_counter(root)
            if not (lane_lo <= counter < lane_hi):
                counter = lane_lo - 1  # other lane's (or stale) counter never steers this one
            next_id = max(counter, local_max) + 1
            if next_id >= lane_hi:
                raise ValueError(
                    f"decision-id lane [{lane_lo}, {lane_hi}) is exhausted — "
                    "agree a new boundary FIRST (the id-lane rule: git config "
                    "friday.decision-id-base); nothing was written")

            entry = format_entry(id_num=next_id, title=title,
                                 when=when or fs.now_iso(), channel=channel,
                                 weight=weight, floor=floor, back_filled=back_filled,
                                 decision=decision, why=why, rejected=rejected,
                                 override_grant=override_grant)
            if parsed["empty"]:
                text = "\n".join(ln for ln in text.splitlines()
                                 if ln.strip() != EMPTY_SENTINEL).rstrip() + "\n"
            text = text.rstrip() + "\n\n" + entry
            _atomic_write(abs_path, text)
            _write_counter(root, next_id)
            _archive_if_needed(wroot, abs_path, cap)
        finally:
            fcntl.flock(lockfh, fcntl.LOCK_UN)

    # Best-effort provenance event through the single journal writer.
    try:
        if fs.should_engage(root):
            fs.append_journal_line(root, fs.build_journal_line(
                "decision-captured", "session", by="lead",
                data={"id": f"D-{next_id:04d}", "channel": channel,
                      "weight": weight, "floor": floor}))
    except Exception:
        pass
    return f"D-{next_id:04d}", entry


def _atomic_write(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _archive_if_needed(wroot: str, abs_path: str, cap: int) -> None:
    """PROP-023: when the live log exceeds `cap` entries, MOVE the oldest half
    to docs/decisions/archive-NNN.md (ids preserved, schema-valid)."""
    with open(abs_path, encoding="utf-8") as fh:
        text = fh.read()
    parsed = parse(text)
    if not parsed["ok"] or len(parsed["entries"]) <= cap:
        return
    keep_from = len(parsed["entries"]) - (cap // 2)
    moved, kept = parsed["entries"][:keep_from], parsed["entries"][keep_from:]

    arch_dir = os.path.join(wroot, "docs", "decisions")
    os.makedirs(arch_dir, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(arch_dir, f"archive-{n:03d}.md")):
        n += 1
    arch_text = f"# Decisions — archive {n:03d}\n\n" + "\n".join(
        _reformat(e) for e in moved)
    _atomic_write(os.path.join(arch_dir, f"archive-{n:03d}.md"), arch_text)

    head = text.splitlines()
    h1 = head[0] if head else "# Decisions"
    marker = "\n".join(ln for ln in head[1:8] if ln.startswith("<!--") or ln.startswith("    "))
    live = h1 + "\n\n" + (marker + "\n\n" if marker else "") + "\n".join(
        _reformat(e) for e in kept)
    _atomic_write(abs_path, live)


def _reformat(e: dict) -> str:
    return format_entry(id_num=e["id"], title=e["title"], when=e.get("when", "?"),
                        channel=e.get("channel", "model-autonomous"),
                        weight=e.get("weight", "two-way"), floor=e.get("floor", "none"),
                        back_filled=e.get("back_filled", False),
                        decision=e.get("decision", "?"), why=e.get("why", "?"),
                        rejected=e.get("rejected", "?"))
