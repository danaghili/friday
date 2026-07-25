"""Shared harness for per-guard AC-13/AC-14 tests (TECHNICAL_SOW_REBUILD §7
pin "Fail-open under real failure modes").

Every BLOCKING guard ships the 5-test pattern:
  1 positive control — its seeded lie produces the block emission; plus
  4 fail-open controls — its checker deleted / crashing / timing out /
  emitting an invalid-or-empty verdict, each of which must ALLOW.

`broken_plugin()` builds a disposable copy of the plugin tree with one named
checker broken in one of those four modes; `run_hook()` drives a hook exactly
as the harness does (event JSON on stdin, plugin root as argv[1], block —
if any — as JSON on stdout, always exit 0). The timeout mode pairs with
env FRIDAY_GUARD_TIMEOUT_S=1 so the control runs in ~1s instead of the
guard's real budget.
"""
import json
import os
import shutil
import subprocess
import sys

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAIL_OPEN_MODES = ("missing", "crash", "timeout", "invalid")

_BODIES = {
    "crash": "import sys\nsys.stderr.write('boom\\n')\nraise SystemExit(3)\n",
    "timeout": "import time\ntime.sleep(30)\n",
    "invalid": "print('{}')\n",  # JSON, but no verdict key — the empty verdict
}


def broken_plugin(tmp_path, checker_rel: str, mode: str) -> str:
    """A plugin-tree copy whose `checker_rel` (e.g. 'tools/trail_check.py')
    is broken per `mode` — one of FAIL_OPEN_MODES."""
    assert mode in FAIL_OPEN_MODES, mode
    pr = tmp_path / f"plugin-{mode}"
    shutil.copytree(os.path.join(BUILD_ROOT, "hooks"), pr / "hooks",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(BUILD_ROOT, "tools"), pr / "tools",
                    ignore=shutil.ignore_patterns("__pycache__"))
    target = pr / checker_rel
    if mode == "missing":
        target.unlink()
    else:
        target.write_text(_BODIES[mode], encoding="utf-8")
    return str(pr)


def run_hook(plugin_root: str, hook_name: str, event: dict,
             env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    full_env.update(env or {})
    proc = subprocess.run(
        [sys.executable, os.path.join(plugin_root, "hooks", hook_name), plugin_root],
        input=json.dumps(event), capture_output=True, text=True,
        cwd=event.get("cwd") or None, env=full_env)
    assert proc.returncode == 0, (hook_name, proc.stderr)  # hooks ALWAYS exit 0
    return proc
