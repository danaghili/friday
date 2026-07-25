#!/usr/bin/env python3
"""friday-docs MCP server — the JIT doc-access layer (vehicle kept verbatim,
cargo retargeted to the arc42/DECISIONS substrate).

Reader triad (teammate-facing):
  list_sections(path) · get_section(path, heading) · search_in(path, query)
Lead-only aggregates:
  resolve(id) — D-NNNN → decision entry + related ADRs
  status(scope) — decisions|actions roll-ups from the advisory index
Verify-wrapping (advisory; enforcement lives in hooks + receipts):
  verify_state() · verify_claims()

BINDING architecture (PROP-024 — the whole point, must never regress):
- The reader triad LIVE-PARSES the target file on every call — no cache in
  the read path, so results can never be stale.
- get_section is EXACT-AFTER-NORMALIZATION heading match (strip → drop
  numbering → strip trailing # → casefold → collapse whitespace → strip
  emphasis) — NOT fuzzy, NOT embeddings, NOT keyword ranking. Origin:
  transcript study showed semantic search was 3% of real demand; 87% of
  weighted traffic served under a 25%-of-file-bytes threshold.
- resolve/status ride the ADVISORY sqlite index, re-synced at the top of
  EVERY tools/call (registry.ensure_fresh) and never the source of truth for
  single-document content.
- `plugin:`-prefixed paths resolve against the SERVER's own install location
  (symlink-safe containment under <plugin_root>/docs/), so any teammate in
  any project can reach the plugin's bundled methodology docs.
- Pure stdlib; newline-delimited JSON-RPC 2.0 over stdio; logs to stderr.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mdparse  # noqa: E402
import registry  # noqa: E402

SERVER_VERSION = "2.0.0"
PLUGIN_PREFIX = "plugin:"
PLUGIN_ROOT = str(pathlib.Path(__file__).resolve().parents[2])
PLUGIN_DOCS_ROOT = os.path.realpath(os.path.join(PLUGIN_ROOT, "docs"))
PLUGIN_DOCS_HINT = ("plugin: paths map to <plugin_root>/<rest> and must resolve "
                    "(symlink-safe) under <plugin_root>/docs/ and end in .md — "
                    "e.g. plugin:docs/teammate-contract.md.")


def log(msg: str) -> None:
    print(f"[friday-docs] {msg}", file=sys.stderr, flush=True)


def send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def result(req_id, payload: dict) -> None:
    send({"jsonrpc": "2.0", "id": req_id, "result": payload})


TOOLS = [
    {"name": "list_sections",
     "description": ("Heading map of one markdown doc with line ranges and "
                     "approximate byte sizes per section. Use before get_section "
                     "when you don't know the exact heading, or to judge whether "
                     "a doc is small enough to just Read whole (~25 KB rule, "
                     "docs/doc-access.md). Path may start with 'plugin:' for the "
                     "plugin's own bundled docs."),
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string", "description": "Project-relative .md path."}},
         "required": ["path"]}},
    {"name": "get_section",
     "description": ("One section of a markdown doc by heading — instead of "
                     "Reading the whole file for one part. Matching is exact "
                     "after normalization (case-insensitive, '1.'-style numbering "
                     "stripped) — never fuzzy. On a miss you get the available "
                     "headings back: retry once with one of those, then fall "
                     "back to a whole-file Read. 'plugin:' paths reach the "
                     "plugin's bundled docs (the teammate contract etc.)."),
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string"}, "heading": {"type": "string"}},
         "required": ["path", "heading"]}},
    {"name": "search_in",
     "description": ("Case-insensitive line search WITHIN one markdown doc; "
                     "returns lines with numbers and enclosing section. 'plugin:' "
                     "paths supported."),
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string"}, "query": {"type": "string"}},
         "required": ["path", "query"]}},
    {"name": "resolve",
     "description": ("LEAD-ONLY. D-NNNN decision id → the decision entry + "
                     "related ADR files. Advisory index — cite the real file."),
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string", "description": "e.g. D-0007"}},
         "required": ["id"]}},
    {"name": "status",
     "description": ("LEAD-ONLY. Project roll-up: scope='decisions' (default — "
                     "state, counts by channel/floor, parked asks, latest) or "
                     "scope='actions' (open [ACTION] tag lines across docs/). "
                     "Advisory — re-verify at gate decision points."),
     "inputSchema": {"type": "object", "properties": {
         "scope": {"type": "string", "enum": ["decisions", "actions"]}},
         "required": []}},
    {"name": "verify_state",
     "description": ("LEAD-ONLY. Run the K-rule state verifier in-process and "
                     "return its structured result. Advisory — blocking "
                     "enforcement lives in the host's hooks; a run leaves a "
                     "receipt."),
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "verify_claims",
     "description": ("LEAD-ONLY. Run the FRIDAY-CLAIMS drift checker in-process "
                     "and return its structured result. Advisory."),
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
]

STRUCTURED_TOOLS = {"verify_state", "verify_claims"}


def safe_doc_path(root: str, path: str) -> tuple[str | None, dict | None]:
    """Two containment regimes: plugin:<rest> under <plugin_root>/docs/, else
    project-root containment. Structured refusals, never raw exceptions."""
    if path.startswith(PLUGIN_PREFIX):
        rest = path[len(PLUGIN_PREFIX):]
        real = os.path.realpath(os.path.join(PLUGIN_ROOT, rest))
        if not (real == PLUGIN_DOCS_ROOT or real.startswith(PLUGIN_DOCS_ROOT + os.sep)):
            return None, {"ok": False, "error": "path_outside_project",
                          "path": path, "hint": PLUGIN_DOCS_HINT}
    else:
        candidate = path if os.path.isabs(path) else os.path.join(root, path)
        real = os.path.realpath(candidate)
        if not (real == root or real.startswith(root + os.sep)):
            return None, {"ok": False, "error": "path_outside_project", "path": path,
                          "hint": "friday-docs only serves files under the project root."}
    if os.path.isdir(real):
        return None, {"ok": False, "error": "is_a_directory", "path": path,
                      "hint": "Reader tools need a file path — pick a .md file."}
    if not os.path.isfile(real):
        return None, {"ok": False, "error": "file_not_found", "path": path}
    if not real.endswith(".md"):
        return None, {"ok": False, "error": "not_markdown", "path": path,
                      "hint": "Reader tools parse markdown headings; Read other files directly."}
    return real, None


def handle_list_sections(root, args, freshness):
    abs_path, err = safe_doc_path(root, args["path"])
    if err:
        return err
    doc = mdparse.parse_file(abs_path)
    return {"ok": True, "path": os.path.relpath(abs_path, root) if not
            args["path"].startswith(PLUGIN_PREFIX) else args["path"],
            "headings": [{"level": h.level, "text": h.text, "norm": h.norm,
                          "line": h.line, "end_line": h.end_line,
                          "approx_bytes": h.approx_bytes} for h in doc.headings],
            "total_bytes": doc.total_bytes, "line_count": doc.line_count,
            "freshness": freshness}


def handle_get_section(root, args, freshness):
    abs_path, err = safe_doc_path(root, args["path"])
    if err:
        return err
    doc = mdparse.parse_file(abs_path)
    rel = (args["path"] if args["path"].startswith(PLUGIN_PREFIX)
           else os.path.relpath(abs_path, root))
    heading, dup_count = mdparse.find_section(doc, args["heading"])
    if heading is None:
        return {"ok": False, "error": "heading_not_found", "path": rel,
                "query": args["heading"],
                "query_norm": mdparse.normalize_heading(args["heading"]),
                "available": [{"level": h.level, "text": h.text, "norm": h.norm}
                              for h in doc.headings],
                "hint": "No exact-after-normalization match. Retry once with a "
                        "heading from `available`, else Read the whole file."}
    payload = {"ok": True, "path": rel,
               "heading": {"level": heading.level, "text": heading.text,
                           "line": heading.line},
               "content": mdparse.section_text(doc, heading),
               "start_line": heading.line, "end_line": heading.end_line,
               "cite": f"{rel}:{heading.line}-{heading.end_line}",
               "freshness": freshness}
    if dup_count > 1:
        payload["duplicate_heading_count"] = dup_count
        payload["hint"] = (f"{dup_count} headings normalize the same; returned "
                           f"the first (line {heading.line}).")
    return payload


def handle_search_in(root, args, freshness):
    abs_path, err = safe_doc_path(root, args["path"])
    if err:
        return err
    doc = mdparse.parse_file(abs_path)
    rel = (args["path"] if args["path"].startswith(PLUGIN_PREFIX)
           else os.path.relpath(abs_path, root))
    matches = mdparse.search_lines(doc, args["query"])
    for m in matches:
        m["cite"] = f"{rel}:{m['line']}"
    return {"ok": True, "path": rel, "query": args["query"], "matches": matches,
            "match_count": len(matches), "freshness": freshness}


def _reject_plugin_prefix(args: dict) -> dict | None:
    for value in args.values():
        if isinstance(value, str) and value.startswith(PLUGIN_PREFIX):
            return {"ok": False, "error": "plugin_path_not_supported",
                    "hint": "plugin: paths only work with the reader triad."}
    return None


def handle_resolve(root, conn, args, freshness):
    rejected = _reject_plugin_prefix(args)
    if rejected:
        return rejected
    out = registry.resolve(conn, root, args["id"])
    out["freshness"] = freshness
    return out


def handle_status(root, conn, args, freshness):
    rejected = _reject_plugin_prefix(args)
    if rejected:
        return rejected
    out = registry.status(conn, root, args.get("scope", "decisions"))
    out["freshness"] = freshness
    return out


def handle_verify_state(root, conn, args, freshness):
    import verify_state as vst
    out = vst.verify_state(root)
    out["freshness"] = freshness
    return out


def handle_verify_claims(root, conn, args, freshness):
    import verify_claims as vc
    out = vc.check_all(root)
    try:
        import receipt
        receipt.leave_receipt(root, "claims", out["ok"],
                              out.get("drift_count", 0))
    except Exception:
        pass
    out["freshness"] = freshness
    return out


READER_TOOLS = {"list_sections": handle_list_sections,
                "get_section": handle_get_section,
                "search_in": handle_search_in}
LEAD_TOOLS = {"resolve": handle_resolve, "status": handle_status,
              "verify_state": handle_verify_state,
              "verify_claims": handle_verify_claims}


def call_tool(name: str, args: dict, conn, root: str) -> dict:
    try:
        freshness = registry.ensure_fresh(conn, root)
    except Exception as e:  # never let index trouble break a reader call
        log(f"ensure_fresh failed: {e!r}")
        freshness = {"resynced": [], "stale_possible": True, "sync_error": str(e)}
    try:
        if name in READER_TOOLS:
            return READER_TOOLS[name](root, args, freshness)
        if name in LEAD_TOOLS:
            return LEAD_TOOLS[name](root, conn, args, freshness)
        return {"ok": False, "error": "unknown_tool", "tool": name}
    except Exception as e:
        log(f"tool {name} failed: {e!r}")
        return {"ok": False, "error": "internal_error", "tool": name,
                "detail": str(e), "hint": "Fall back to plain Read for this query."}


def main() -> None:
    root = registry.project_root()
    log(f"started (root={root})")
    conn = registry.connect(root)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log(f"unparseable line: {line[:120]}")
            continue
        method, req_id = msg.get("method"), msg.get("id")
        if method == "initialize":
            proto = msg.get("params", {}).get("protocolVersion", "2024-11-05")
            result(req_id, {"protocolVersion": proto,
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "friday-docs",
                                           "version": SERVER_VERSION}})
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            result(req_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = msg.get("params", {})
            name, args = params.get("name"), params.get("arguments") or {}
            if name not in READER_TOOLS and name not in LEAD_TOOLS:
                send({"jsonrpc": "2.0", "id": req_id,
                      "error": {"code": -32602, "message": f"unknown tool: {name}"}})
                continue
            payload = call_tool(name, args, conn, root)
            response = {"content": [{"type": "text",
                                     "text": json.dumps(payload, ensure_ascii=False)}],
                        "isError": not payload.get("ok", False)}
            if name in STRUCTURED_TOOLS:
                response["structuredContent"] = payload
            result(req_id, response)
        elif method == "ping":
            result(req_id, {})
        elif req_id is not None:
            send({"jsonrpc": "2.0", "id": req_id,
                  "error": {"code": -32601, "message": f"method not supported: {method}"}})
    log("stdin closed — exiting")


if __name__ == "__main__":
    main()
