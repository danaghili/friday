#!/usr/bin/env python3
"""Session lifecycle hook — heartbeat locks + session-start/end journal lines.

Bound on SessionStart and SessionEnd (one file, dispatch on hook_event_name):
  SessionStart: resolve the real `claude` session pid (walk the ancestry —
    never os.getppid(), which can be a transient shell wrapper), detect the
    ignition flags (--dangerously-skip-permissions from permission_mode with a
    cmdline fallback; --remote-control only from the cmdline), write
    `.friday/sessions/<session-id>.lock` (Appendix B.3: PER-SESSION under the
    SHARED substrate root), spawn the detached heartbeat, journal
    `session-start` — this is what puts a bypassed-permissions session INTO
    the record.
  SessionEnd: journal `session-end` and remove this session's lock. The
    heartbeat notices the watched pid died on its own.

`mode` is a DECLARED CONSTANT ("supervised") — never sniffed; a mode change is
journal-only via a `mode-change` line from the command that made it.

Hook discipline: always exits 0; failure degrades to "no telemetry".
Substrate access via tools/friday_substrate (D-0003 — single writer,
worktree-safe root resolution).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

_TEST_PID_ENV = "FRIDAY_TEST_SESSION_PID"
_TEST_CMDLINE_ENV = "FRIDAY_TEST_SESSION_CMDLINE"
_CLAUDE_COMM_BASENAMES = {"claude"}


def _ps_field(pid: int, field: str, timeout: float = 3.0) -> str | None:
    """One `ps` field at a time (`comm`/`command` contain spaces that corrupt
    multi-column parsing); -ww disables truncation."""
    try:
        proc = subprocess.run(["ps", "-ww", "-o", f"{field}=", "-p", str(pid)],
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _resolve_claude_pid(start_pid: int | None = None, max_hops: int = 40) -> int | None:
    """Nearest ancestor whose executable basename is `claude` — watching a
    wrapper pid would let the lock go stale mid-session (a false orphan)."""
    override = os.environ.get(_TEST_PID_ENV)
    if override:
        try:
            return int(override)
        except ValueError:
            pass
    pid = start_pid if start_pid is not None else os.getpid()
    seen: set[int] = set()
    for _ in range(max_hops):
        if pid in seen or pid <= 1:
            return None
        seen.add(pid)
        comm = _ps_field(pid, "comm")
        if comm and os.path.basename(comm) in _CLAUDE_COMM_BASENAMES:
            return pid
        ppid_raw = _ps_field(pid, "ppid")
        if not ppid_raw:
            return None
        try:
            pid = int(ppid_raw)
        except ValueError:
            return None
    return None


def _detect_flags(claude_pid: int, event: dict) -> tuple[dict, str | None]:
    """(flags, flags_source): source 'partial' when a flag could not be
    conclusively determined. permission_mode is the primary skip-permissions
    signal; the resolved cmdline is the fallback for it and the ONLY signal
    for --remote-control."""
    partial = False
    permission_mode = event.get("permission_mode")
    cmdline = os.environ.get(_TEST_CMDLINE_ENV)
    if cmdline is None:
        cmdline = _ps_field(claude_pid, "command")

    if permission_mode is not None:
        skip = permission_mode == "bypassPermissions"
    elif cmdline is not None:
        skip = "--dangerously-skip-permissions" in cmdline.split()
    else:
        skip, partial = False, True

    if cmdline is None:
        remote, partial = False, True
    else:
        remote = "--remote-control" in cmdline.split()
    return ({"remote_control": remote, "dangerously_skip_permissions": skip},
            "partial" if partial else None)


def _spawn_heartbeat(plugin_root: str, pid: int, cwd: str, session_id: str,
                     started_at: str, flags: dict) -> None:
    helper = os.path.join(plugin_root, "tools", "session_heartbeat.py")
    if not os.path.isfile(helper):
        print("session_lifecycle: session_heartbeat.py not found; no heartbeat",
              file=sys.stderr)
        return
    subprocess.Popen(
        [sys.executable, helper, str(pid), cwd, session_id, started_at,
         json.dumps(flags)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True)


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    hook_event_name = event.get("hook_event_name") or ""
    session_id = event.get("session_id")
    session_id = session_id if isinstance(session_id, str) and session_id else "unknown"

    if fs is None:
        return 0  # substrate unimportable — degrade to no telemetry
    try:
        if not fs.should_engage(cwd):
            return 0
        if hook_event_name == "SessionStart":
            claude_pid = _resolve_claude_pid()
            if claude_pid is None:
                print("session_lifecycle: no claude ancestor; skipping session-start",
                      file=sys.stderr)
                return 0
            flags, flags_source = _detect_flags(claude_pid, event)
            now = fs.now_iso()
            fs.write_session_lock(cwd, session_id, {
                "pid": claude_pid, "session_id": session_id, "started_at": now,
                "ts": now, "flags": flags, "mode": "supervised"})
            _spawn_heartbeat(plugin_root, claude_pid, cwd, session_id, now, flags)
            data: dict = {"pid": claude_pid, "session": session_id,
                          "flags": flags, "mode": "supervised",
                          # always present, null when absent — journaled after the
                          # INC-001 live run saw the reorient push not engage
                          # (docs/research/inc001-live-validation.md); first catch
                          # 2026-07-16: auto-compact sent source="compact" and the
                          # push engaged, so the matcher stands — kept as telemetry
                          "source": event.get("source")}
            if flags_source:
                data["flags_source"] = flags_source
            fs.append_journal_line(cwd, fs.build_journal_line(
                "session-start", "session", by="session", data=data, ts=now))
        elif hook_event_name == "SessionEnd":
            data = {"session": session_id}
            reason = event.get("reason")
            if reason:
                data["reason"] = reason
            fs.append_journal_line(cwd, fs.build_journal_line(
                "session-end", "session", by="session", data=data))
            fs.remove_session_lock(cwd, session_id)
    except Exception as exc:  # hook boundary — never break the session
        print(f"session_lifecycle: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
