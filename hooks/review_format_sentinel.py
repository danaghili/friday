#!/usr/bin/env python3
"""Review-format sentinel — PostToolUse bounce, retargeted to docs/reviews/.

Engages ONLY for a review-shaped write (a .md under docs/reviews/, never
_archive/) and runs tools/verify_review_format.py against just that file.

Interim carve-out (DF-021 / D-0009 / D-0021): `interim-*.md` files under
docs/reviews/ are interim findings-brief artifacts — the seam plan mandates
both the path and the grammar — so they are validated by
tools/findings_brief_check.py instead of the FRIDAY-REVIEW envelope. A
malformed brief still BOUNCES (writer fixes it in-context) but never arms
the Stop-gate sentinel: an interim report's consumer is the disposition
step, not the session close.
Unlike the state sentinel it also BOUNCES: on failure it emits
{"decision":"block","reason": line-precise failures} so the Reviewer that
just wrote the file fixes it while it still holds context — the fail-closed
alternative to a script ever "repairing" an envelope. Strictness follows the
write shape: Write ⇒ --strict-missing (a fresh review cannot be "legacy");
Edit/MultiEdit ⇒ sweep. Arms `<shared .friday>/review-format-invalid`
(line 1: artifact relpath · line 2: strict|sweep · rest: summary) for the
Stop gate; a pass for the SAME artifact disarms. Always exits 0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402


def _review_shaped_write(event: dict) -> str:
    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    norm = path.replace(os.sep, "/")
    if "docs/reviews/" not in norm or "/_archive/" in norm or not norm.endswith(".md"):
        return ""
    return path


def main() -> int:
    plugin_root = plugin_root_from(sys.argv)
    fs = load_substrate(plugin_root)
    event = read_event()
    cwd = event.get("cwd") or os.getcwd()
    if fs is None:
        return 0
    path = _review_shaped_write(event)
    if not path:
        return 0
    try:
        if not fs.is_friday_project(cwd):
            return 0
        abs_path = path if os.path.isabs(path) else os.path.join(cwd, path)
        if not os.path.isfile(abs_path):
            return 0

        if os.path.basename(abs_path).startswith("interim-"):
            checker = os.path.join(plugin_root, "tools", "findings_brief_check.py")
            if not os.path.isfile(checker):
                return 0
            proc = subprocess.run(
                [sys.executable, checker, "--file", abs_path],
                capture_output=True, text=True, timeout=60)
            try:
                verdict = json.loads(proc.stdout or "{}")
            except ValueError:
                return 0  # no usable verdict — fail open
            sentinel = os.path.join(fs.friday_dir(cwd), "review-format-invalid")
            try:
                rel_path = os.path.relpath(abs_path, cwd)
            except ValueError:
                rel_path = abs_path
            if verdict.get("verdict") == "valid-pass":
                try:
                    with open(sentinel, encoding="utf-8") as fh:
                        if fh.readline().strip() == rel_path:
                            os.remove(sentinel)
                except OSError:
                    pass
            elif verdict.get("verdict") == "valid-fail":
                errs = "\n".join(f"  x {e}" for e in verdict.get("errors") or [])
                print(json.dumps({"decision": "block", "reason": (
                    f"The interim report you just wrote ({rel_path}) does not "
                    "parse as a findings brief — fix it before reporting DONE "
                    "(contract: docs/contracts/findings-brief.md):\n" + errs)}))
            return 0
        verifier = os.path.join(plugin_root, "tools", "verify_review_format.py")
        if not os.path.isfile(verifier):
            return 0
        strict = event.get("tool_name") == "Write"
        cmd = [sys.executable, verifier, "--file", abs_path, "--json"]
        if strict:
            cmd.append("--strict-missing")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        result = json.loads(proc.stdout or "{}")

        sentinel = os.path.join(fs.friday_dir(cwd), "review-format-invalid")
        try:
            rel_path = os.path.relpath(abs_path, cwd)
        except ValueError:
            rel_path = abs_path

        if result.get("ok"):
            try:
                with open(sentinel, encoding="utf-8") as fh:
                    armed_for = fh.readline().strip()
                    armed_mode = fh.readline().strip()
                still_missing = any(f.get("check") == "R1" and f.get("severity") == "warn"
                                    for f in result.get("failures") or [])
                # a sweep pass that merely re-warns "no envelope" does NOT
                # release a strict arming — the envelope is still absent.
                if armed_for == rel_path and not (armed_mode == "strict" and still_missing):
                    os.remove(sentinel)
            except OSError:
                pass
            return 0

        detail = "\n".join(f"  x {f['check']} — {f['detail']}"
                           for f in result.get("failures") or []
                           if f.get("severity") == "blocking")
        try:
            os.makedirs(os.path.dirname(sentinel), exist_ok=True)
            with open(sentinel, "w", encoding="utf-8") as fh:
                fh.write(rel_path + "\n" + ("strict" if strict else "sweep") + "\n"
                         + result.get("summary", "review format failure") + "\n")
        except OSError:
            pass
        print(json.dumps({"decision": "block", "reason": (
            f"The review artifact you just wrote ({rel_path}) fails its "
            "FRIDAY-REVIEW format checks — fix the file before reporting DONE "
            "(contract: docs/teammate-contract.md, Review envelope; the "
            "envelope must always describe the file as it now stands):\n"
            + detail)}))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
