#!/usr/bin/env python3
"""Guard #18b — worktree-remove warn (WorktreeRemove, WARN tier;
TECHNICAL_SOW_REBUILD FR-56 guard #18b). A doc-only harness event per
probe-hook-events.md (create fired via `-w` in the probe; remove did not,
create having failed first) — fine if it never fires.

**DISABLED — NOT WIRED (2026-07-14; docs/research/rebuild/
probe-worktree-hooks.md).** The sibling WorktreeCreate event turned out to
be an ACTIVE provisioner contract (a wired hook's stdout is load-bearing
and its absence FAILS the operation); WorktreeRemove could not be fired
even in a fresh live probe (the worktree persists after a headless `-w`
run), so its contract is unobserved. Wiring a warn hook whose stdout might
be load-bearing risks breaking `git worktree remove` flows — unwired until
a probe observes the event. PM disposition rides with #18a's.

No checker: the sentinel's mere presence IS the fact being warned about.
If the shared `.friday/lane-open` sentinel exists, an open lane's work may
be discarded without a recorded trail — this never blocks (worktree removal
already happened by the time this fires; a warning is all that's honest).
An unreadable sentinel still warns, generically — its presence alone is the
signal, parseability is not required for that.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    try:
        sentinel = os.path.join(fs.friday_dir(cwd), "lane-open")
        if not os.path.isfile(sentinel):
            return 0
        lane_name, lane_id = "?", "?"
        try:
            with open(sentinel, encoding="utf-8") as fh:
                lane = json.load(fh)
            lane_name = lane.get("lane", "?")
            lane_id = lane.get("id", "?")
        except Exception:
            pass  # unreadable sentinel — still warn, just without the specifics
        print(json.dumps(_guard.emit_warn(
            f"an open {lane_name} lane ({lane_id}) exists — removing this "
            "worktree may discard its work without a recorded trail")))
    except Exception as exc:
        print(f"worktree_remove_warn: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
