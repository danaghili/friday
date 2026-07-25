#!/usr/bin/env python3
"""Session heartbeat — detached ts-refresher spawned by session_lifecycle.py.

Keeps `.friday/sessions/<session-id>.lock`'s `ts` fresh every --interval
seconds (default 20) for as long as the watched pid — the resolved `claude`
session process, never this helper's own pid — stays alive, and exits the
moment it doesn't. It never removes the lock; on unclean death it simply
stops ticking — the stale `ts` IS the honest crash signal (no separate
crash-detection logic anywhere).

Appendix B.3 change from v0.4.0: locks are PER-SESSION under the SHARED
`.friday/sessions/` (resolved via git common dir by friday_substrate), so
multiple concurrent worktree sessions each keep honest liveness instead of
clobbering one repo-wide lock. Each tick rewrites the whole lock JSON from
this process's own in-memory copy (self-healing if clobbered) via atomic
temp-file + os.replace.

Usage:
  session_heartbeat.py <pid> <cwd> <session_id> <started_at_iso> <flags_json> [--interval S]

Pure stdlib (+ friday_substrate sibling import).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402

_DEFAULT_FLAGS = {"remote_control": False, "dangerously_skip_permissions": False}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _pid_alive(pid: int) -> bool:
    """os.kill(pid, 0) liveness probe: ProcessLookupError = gone;
    PermissionError = exists under another user (treated alive, not guessed)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run(pid: int, cwd: str, session_id: str, started_at: str, flags: dict,
        interval: float, sleep: Callable[[float], None] = time.sleep,
        alive: Callable[[int], bool] = _pid_alive) -> None:
    """Tick loop. Sleeps BEFORE the first write (the SessionStart hook already
    wrote the lock at t+0) and re-checks liveness after waking, so a pid that
    died mid-sleep never gets one stale-by-definition refresh. `sleep`/`alive`
    injectable (mock-external-only testing stance)."""
    while True:
        sleep(interval)
        if not alive(pid):
            return
        lock = {"pid": pid, "session_id": session_id, "started_at": started_at,
                "ts": _now_iso(), "flags": flags, "mode": "supervised"}
        try:
            fs.write_session_lock(cwd, session_id, lock)
        except OSError:
            pass  # one missed tick — never crash the watcher on a transient failure


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pid", type=int)
    ap.add_argument("cwd")
    ap.add_argument("session_id")
    ap.add_argument("started_at")
    ap.add_argument("flags_json")
    ap.add_argument("--interval", type=float, default=20.0)
    args = ap.parse_args(argv)
    try:
        flags = json.loads(args.flags_json)
        if not isinstance(flags, dict):
            flags = dict(_DEFAULT_FLAGS)
    except json.JSONDecodeError:
        flags = dict(_DEFAULT_FLAGS)
    run(args.pid, args.cwd, args.session_id, args.started_at, flags, args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
