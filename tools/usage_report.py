#!/usr/bin/env python3
"""Usage/cost roll-up over the journal's `usage` events — cost visibility is a
gating concern in vnext (NFR-2: efficiency beats the ceremony baseline).
Tokens are the durable record; usd is the write-time convenience.

Usage: python3 tools/usage_report.py [--root .] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402


def report(root: str) -> dict:
    path = os.path.join(fs.friday_dir(root), "journal.jsonl")
    per: dict[tuple[str, str], dict] = {}
    events = 0
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                try:
                    line = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if line.get("event") != "usage":
                    continue
                d = line.get("data") or {}
                key = (d.get("agent", "?"), d.get("model", "?"))
                agg = per.setdefault(key, {"input": 0, "output": 0, "cache_read": 0,
                                           "cache_write": 0, "usd": 0.0})
                for k in ("input", "output", "cache_read", "cache_write"):
                    agg[k] += d.get(k, 0) if isinstance(d.get(k), int) else 0
                if isinstance(d.get("usd"), (int, float)):
                    agg["usd"] += d["usd"]
                events += 1
    except OSError:
        return {"ok": True, "events": 0, "rows": [], "total_usd": 0.0,
                "summary": "usage: no journal yet"}
    rows = [{"agent": a, "model": m, **v} for (a, m), v in sorted(per.items())]
    total = round(sum(r["usd"] for r in rows), 4)
    return {"ok": True, "events": events, "rows": rows, "total_usd": total,
            "summary": f"usage: {events} events · ${total} across {len(rows)} agent/model rows"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = report(os.path.abspath(args.root))
    if args.json:
        print(json.dumps(res))
    else:
        print(res["summary"])
        for r in res["rows"]:
            print(f"  {r['agent']:24s} {r['model']:32s} in={r['input']} out={r['output']} "
                  f"cr={r['cache_read']} cw={r['cache_write']} ${round(r['usd'], 4)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
