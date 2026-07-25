#!/usr/bin/env python3
"""Token-cost telemetry hook — KEPT from v0.4.0 (cost visibility is MORE
load-bearing in vnext: NFR-2 makes efficiency a gating DoD leg).

Bound on SubagentStop (every teammate) and Stop (the lead): reads the NEW
portion of the transcript since the last pass (byte cursor in
`.friday/usage-cursor.json`; shrunken file resets; a partial trailing line is
left for the next pass) and appends one `usage` journal line per model seen.
Token counts are the durable record; `usd` is a write-time convenience from
the price table (omitted for unrecognized models).

Always exits 0; any failure degrades to "no telemetry". Substrate via
friday_substrate (worktree-shared cursor + journal).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hookutil import load_substrate, plugin_root_from, read_event  # noqa: E402

# USD per MILLION tokens: (input, output); substring-matched, specific first.
# Cache: reads 0.1x input, writes 1.25x input. Reprice from tokens if changed.
PRICE_PER_MTOK: tuple[tuple[str, tuple[float, float]], ...] = (
    ("fable", (10.0, 50.0)),
    ("opus", (5.0, 25.0)),
    ("sonnet", (3.0, 15.0)),
    ("haiku", (1.0, 5.0)),
)
CACHE_READ_MULT = 0.1
CACHE_WRITE_MULT = 1.25
CURSOR_BASENAME = "usage-cursor.json"


def _price_usd(model: str, tokens: dict) -> float | None:
    model_lower = model.lower()
    for needle, (p_in, p_out) in PRICE_PER_MTOK:
        if needle in model_lower:
            usd = (tokens["input"] * p_in + tokens["output"] * p_out
                   + tokens["cache_read"] * p_in * CACHE_READ_MULT
                   + tokens["cache_write"] * p_in * CACHE_WRITE_MULT) / 1_000_000
            return round(usd, 4)
    return None


def _read_new_usage(transcript_path: str, offset: int) -> tuple[dict, int]:
    size = os.path.getsize(transcript_path)
    if offset > size:
        offset = 0
    per_model: dict[str, dict[str, int]] = {}
    consumed = offset
    with open(transcript_path, "rb") as fh:
        fh.seek(offset)
        for raw in fh:
            if not raw.endswith(b"\n"):
                break
            consumed += len(raw)
            try:
                obj = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            message = obj.get("message") if isinstance(obj, dict) else None
            if not isinstance(message, dict):
                continue
            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue
            model = message.get("model") or obj.get("model") or "unknown"
            if not isinstance(model, str):
                model = "unknown"
            sums = per_model.setdefault(model, {"input": 0, "output": 0,
                                                "cache_read": 0, "cache_write": 0})
            for out_key, in_key in (("input", "input_tokens"),
                                    ("output", "output_tokens"),
                                    ("cache_read", "cache_read_input_tokens"),
                                    ("cache_write", "cache_creation_input_tokens")):
                val = usage.get(in_key)
                sums[out_key] += val if isinstance(val, int) and val >= 0 else 0
    return per_model, consumed


def process_event(fs, event: dict) -> None:
    if event.get("hook_event_name") not in ("Stop", "SubagentStop"):
        return
    cwd = event.get("cwd") or os.getcwd()
    if not fs.should_engage(cwd):
        return
    transcript_path = event.get("transcript_path")
    if not isinstance(transcript_path, str) or not os.path.isfile(transcript_path):
        return

    cursor_path = os.path.join(fs.friday_dir(cwd), CURSOR_BASENAME)
    try:
        with open(cursor_path, encoding="utf-8") as fh:
            cursor = json.load(fh)
        if not isinstance(cursor, dict):
            cursor = {}
    except (OSError, json.JSONDecodeError):
        cursor = {}
    offset = cursor.get(transcript_path)
    if not isinstance(offset, int) or offset < 0:
        offset = 0
    per_model, consumed = _read_new_usage(transcript_path, offset)

    if event.get("hook_event_name") == "Stop":
        agent = "lead"
    else:
        agent = fs.agent_type_from_event(event) or "subagent"
    ts = fs.now_iso()
    for model, tokens in sorted(per_model.items()):
        if not any(tokens.values()):
            continue
        data = {"agent": agent, "model": model, **tokens}
        usd = _price_usd(model, tokens)
        if usd is not None:
            data["usd"] = usd
        fs.append_journal_line(cwd, fs.build_journal_line(
            "usage", "session", by="session", data=data, ts=ts))

    if consumed != offset or transcript_path not in cursor:
        cursor[transcript_path] = consumed
        os.makedirs(os.path.dirname(cursor_path), exist_ok=True)
        tmp = cursor_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cursor, fh, separators=(",", ":"))
        os.replace(tmp, cursor_path)


def main() -> int:
    fs = load_substrate(plugin_root_from(sys.argv))
    if fs is None:
        return 0
    try:
        process_event(fs, read_event())
    except Exception:
        return 0  # failure contract: degrade to no telemetry
    return 0


if __name__ == "__main__":
    sys.exit(main())
