"""tools/session_heartbeat.py — the detached liveness ticker (task #14).

Popen'd on every session start and it had zero coverage despite being built
WITH injectable seams (`sleep` and `alive` on `run()`) that nothing used.
The stakes: a heartbeat that keeps ticking after its session died writes a
forever-fresh lock, which silently defeats the crash signal the whole design
leans on (a stale `ts` IS the crash detection — there is no other).
Time and process-liveness are the two true externals here; both are injected.
The lock write itself is real substrate against a real tmp repo.
"""
import json
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_BASE, "tools"))
import friday_substrate as fs  # noqa: E402
import session_heartbeat as sh  # noqa: E402


def _proj(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _lock(root, session_id="s1"):
    path = root / ".friday" / "sessions" / f"{session_id}.lock"
    return json.loads(path.read_text()) if path.exists() else None


def _scripted(*answers):
    """An `alive` probe that replays a fixed script, then says dead forever."""
    it = iter(answers)
    return lambda pid: next(it, False)


def test_refreshes_the_lock_each_tick_while_the_pid_lives(tmp_path):
    root = _proj(tmp_path)
    sleeps = []
    sh.run(4242, str(root), "s1", "2026-07-29T00:00:00Z",
           {"remote_control": False}, 20.0,
           sleep=sleeps.append, alive=_scripted(True, True, True))
    lock = _lock(root)
    assert lock is not None
    assert lock["pid"] == 4242 and lock["session_id"] == "s1"
    assert lock["mode"] == "supervised" and lock["flags"] == {"remote_control": False}
    assert lock["ts"].endswith("Z")            # a real write-time stamp, not the start time
    # three live ticks + the waking check that found the pid dead
    assert sleeps == [20.0, 20.0, 20.0, 20.0]


def test_a_pid_that_died_mid_sleep_never_gets_a_stale_refresh(tmp_path):
    """The ordering pin: sleep FIRST, re-check liveness AFTER waking. A dead
    session must exit with zero writes — the SessionStart hook already wrote
    the t+0 lock, and one 'refresh' on behalf of a corpse would push the
    stale-ts crash signal a full interval into the future."""
    root = _proj(tmp_path)
    sh.run(4242, str(root), "s1", "2026-07-29T00:00:00Z", {}, 20.0,
           sleep=lambda s: None, alive=_scripted())   # dead at the first check
    assert _lock(root) is None
    assert not (root / ".friday").exists()            # it never even touched the substrate


def test_a_failed_lock_write_skips_the_tick_and_keeps_watching(tmp_path, monkeypatch):
    """One missed tick is the contract for a transient IO failure — the
    watcher must neither crash (orphaning the liveness signal early) nor
    stop probing the pid."""
    root = _proj(tmp_path)
    calls = {"writes": 0, "probes": 0}
    real_write = fs.write_session_lock       # bound BEFORE the patch below shadows it

    def flaky_write(cwd, session_id, lock):
        calls["writes"] += 1
        if calls["writes"] == 1:
            raise OSError("disk hiccup")
        real_write(cwd, session_id, lock)

    def probe(pid):
        calls["probes"] += 1
        return calls["probes"] <= 2

    monkeypatch.setattr(sh.fs, "write_session_lock", flaky_write)
    sh.run(4242, str(root), "s1", "2026-07-29T00:00:00Z", {}, 20.0,
           sleep=lambda s: None, alive=probe)
    assert calls["writes"] == 2                # tick 1 failed, tick 2 landed
    assert _lock(root) is not None


def test_pid_alive_against_real_processes():
    """The un-injected probe, checked both ways against reality: our own pid
    lives; a child we have already reaped does not."""
    assert sh._pid_alive(os.getpid()) is True
    child = subprocess.Popen(["true"])
    child.wait()
    assert sh._pid_alive(child.pid) is False


def test_main_survives_malformed_flags_json(monkeypatch):
    """The flags arrive from a shell one-liner in session_lifecycle — a
    quoting accident must fall back to the safe defaults, never crash the
    spawn or invent permissive flags."""
    seen = {}
    monkeypatch.setattr(sh, "run",
                        lambda pid, cwd, sid, started, flags, interval, **kw:
                        seen.update(flags=flags, interval=interval))
    rc = sh.main(["4242", "/tmp/x", "s1", "2026-07-29T00:00:00Z",
                  "{not json", "--interval", "5"])
    assert rc == 0
    assert seen["flags"] == sh._DEFAULT_FLAGS and seen["interval"] == 5.0
    # a JSON scalar is equally not a flags dict — same fallback
    sh.main(["4242", "/tmp/x", "s1", "2026-07-29T00:00:00Z", "42"])
    assert seen["flags"] == sh._DEFAULT_FLAGS
