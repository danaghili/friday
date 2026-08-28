#!/usr/bin/env python3
"""Guard #7's checker — committed-test edit detection (TECHNICAL_SOW_REBUILD
FR-55 guard #7; §7 pin "Committed-test edit guard"; probe brief:
docs/research/rebuild/probe-guard7-committed-test.md, prototype rebuilt
test-first per its own instruction).

Question answered, mechanically, at tool-call time: is the file this edit is
about to touch a test that was ALREADY COMMITTED before the current build
started, with no PM permission record on file? Committed tests are the
build's oracle — changing one mid-build can quietly change what "passing"
means (the same doctrine that keeps the TSOW un-editable).

The definition that survived the probe fixtures:

1. Repo-relative path outside the watch scope → valid-pass. The scope is
   `tests/*.py` (this project declares its tests there — CLAUDE.md) plus
   the dotted test-file family: a basename carrying `.test.` or `.spec.`,
   any case, any directory (the JS/TS convention — BUG-011, D-0186; the
   old tests/*.py-only scope left every committed .test.ts unwatched on
   TS/Vitest projects). Deliberately narrower than guard #11's loose rule:
   this guard fires unprompted on every edit, and a false block is worse
   than a miss.
2. Build epoch: CLAUDE.md FRIDAY-STATE `since:` when `state:
   build-in-progress` (checkout copy, tag-line grammar); else the newest
   `state-transition` line in the shared journal (substrate root via
   friday_substrate — worktrees share it). Neither → no-verdict.
3. `git log --follow -M100% --name-status --format=%cI -- <path>`. Empty →
   valid-pass (untracked / authored in-build). The chain is walked newest →
   oldest and TRUNCATED at the first C (copy) record: git's --follow
   attributes a byte-identical new file's history to a still-existing older
   file as a copy (found while pinning fixture d harder than the probe did),
   and honoring that history would false-block genuinely new tests — worse
   than a miss. An R (rename) record keeps the chain: a pure `git mv` is
   still caught (probe fixture g). Effective-oldest commit > epoch →
   valid-pass. Oldest <= epoch → docs/DECISIONS.md must contain the literal
   repo-relative path (a permission record) → valid-pass; else valid-fail.
   `-M100%` is load-bearing: default `-M50%` misattributed unrelated
   boilerplate stubs to older files (false FAIL on ordinary new-test
   authoring). Accepted residual, pinned by test: rename+edit in ONE commit
   reads as a fresh file (a deliberate two-part evasion; a miss, never a
   false block).
4. Any internal error → no-verdict (fail-open doctrine; hooks/_guard.py
   normalizes it to allow).

Verdict rides stdout as ONE JSON object. Exit 0 pass/no-verdict · 1 fail ·
2 bad invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

TEST_PREFIX = "tests/"
TEST_SUFFIX = ".py"
GIT_TIMEOUT_S = 5


def _git(repo: str, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", repo, *args], capture_output=True,
                              text=True, timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _parse_iso(ts: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _epoch_from_state(checkout_root: str) -> datetime | None:
    try:
        with open(os.path.join(checkout_root, "CLAUDE.md"), encoding="utf-8") as fh:
            typed = taglines.block_typed(fh.read(), "FRIDAY-STATE")
    except OSError:
        return None
    if not typed or typed.get("state", [""])[0] != "build-in-progress":
        return None
    return _parse_iso(typed.get("since", [""])[0])


def _epoch_from_journal(checkout_root: str) -> datetime | None:
    try:
        import friday_substrate as fs
        journal = os.path.join(fs.friday_dir(checkout_root), "journal.jsonl")
        with open(journal, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except Exception:
        return None
    newest = None
    for ln in lines:
        try:
            obj = json.loads(ln)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("event") == "state-transition":
            dt = _parse_iso(obj.get("ts") or "")
            if dt and (newest is None or dt > newest):
                newest = dt
    return newest


def check(path: str, repo: str | None = None) -> dict:
    """The probe algorithm as a pure-ish function; tests drive this directly."""
    def v(kind: str, why: str) -> dict:
        return {"verdict": kind, "summary": why}

    try:
        candidate = os.path.abspath(path)
        start = os.path.abspath(repo) if repo else os.path.dirname(candidate)
        toplevel = _git(start, "rev-parse", "--show-toplevel")
        if not toplevel:
            return v("no-verdict", "the file is not inside a git repository")
        root = os.path.realpath(toplevel.strip())
        rel = os.path.relpath(os.path.realpath(candidate), root).replace(os.sep, "/")
        if rel.startswith(".."):
            return v("no-verdict", "the file escapes the repository root")

        watched = ((rel.startswith(TEST_PREFIX) and rel.endswith(TEST_SUFFIX))
                   or re.search(r"\.(test|spec)\.", os.path.basename(rel),
                                re.IGNORECASE))
        if not watched:
            return v("valid-pass",
                     f"{rel} is not a watched test path (tests/*.py or a "
                     "dotted *.test.* / *.spec.* name) — not watched")

        epoch = _epoch_from_state(root) or _epoch_from_journal(root)
        if epoch is None:
            return v("no-verdict", "no build epoch resolvable from FRIDAY-STATE "
                                   "or the journal")

        log = _git(root, "log", "--follow", "-M100%", "--name-status",
                   "--format=%cI", "--", rel)
        if log is None:
            return v("no-verdict", "git log failed for the file")

        # Parse (commit date, status records) blocks, newest first.
        commits: list[tuple[datetime | None, list[str]]] = []
        for ln in log.splitlines():
            if not ln.strip():
                continue
            dt = _parse_iso(ln)
            if dt is not None:
                commits.append((dt, []))
            elif commits:
                commits[-1][1].append(ln.strip())
        if not commits:
            return v("valid-pass", f"{rel} has no commit history — new in this build")
        if any(dt is None for dt, _ in commits):
            return v("no-verdict", "unparseable commit timestamp in git log output")

        # Truncate the follow chain at the first copy record: the candidate
        # was BORN at that commit; older history belongs to a different,
        # still-existing file and honoring it would false-block new tests.
        included: list[datetime] = []
        for dt, statuses in commits:
            included.append(dt)
            if any(s.startswith("C") for s in statuses):
                break
        oldest = min(included)
        if oldest > epoch:
            return v("valid-pass", f"{rel} first committed after the build epoch — "
                                   "authored during this build")

        try:
            import decisions
            with open(os.path.join(root, "docs", "DECISIONS.md"), encoding="utf-8") as fh:
                permitted = decisions.has_override_grant(fh.read(), rel)
        except OSError:
            permitted = False
        if permitted:
            return v("valid-pass", f"{rel} predates the build but docs/DECISIONS.md "
                                   "names it — PM permitted")
        return v("valid-fail", f"{rel} was committed before this build started "
                               f"({oldest.isoformat()} <= epoch {epoch.isoformat()}) "
                               "and no permission record in docs/DECISIONS.md "
                               "names it")
    except Exception as exc:
        return v("no-verdict", f"internal error: {type(exc).__name__}: {exc}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guard #7 checker: committed-test edit")
    ap.add_argument("--path", required=True, help="file the tool call is about to touch")
    ap.add_argument("--repo", default=None, help="repo hint (default: the file's dir)")
    args = ap.parse_args(argv)
    res = check(args.path, repo=args.repo)
    print(json.dumps(res))
    return 1 if res["verdict"] == "valid-fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
