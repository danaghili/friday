#!/usr/bin/env python3
"""friday-experiments — the door the experiment runner reaches its executor through.

The runner used to hold a shell. It was told to use it for exactly one command,
and the containment lived in that command's code — which is a promise about
behaviour, not a property of the system. This server is the replacement: two
tools, `plan` and `run`, and no shell at all
(INC-201 FR-201.2 / FR-201.4 ... FR-201.7; contracts:
`docs/contracts/experiment-consent.md`, `docs/contracts/experiment-request.md`).

**What the runner supplies is one thing: which batch (D3).** Not the request
document's path, not which tree is the live one, not where the record of the run
is written. Each of those, in the caller's hands, is a way around a promise made
somewhere else — a caller-named live root makes the worktree clause meaningless,
a caller-named request path attaches the PM's approval to a document they never
read, and a caller-named output path is an arbitrary file write carrying up to
200 bytes of target-chosen text. So they are not filtered out of the interface;
there is nowhere in the interface to put them. Everything else is derived here:

    batch id -> consent record (.friday/, which the runner cannot write)
             -> the request document that record is bound to
             -> that document's approved fingerprint
             -> the run record's path

**The root is the server's own** (`CLAUDE_PROJECT_DIR` or its cwd), exactly as
`tools/doc-index/registry.py` does it, and never an argument.

**Nothing about containment is reimplemented here.** Parsing, the closed move
menu, egress pinning, the worktree clause and the substrate write ban stay in
`experiment_request` / `experiment_run`, where their tests live; the consent
record stays behind `friday_consent`, which owns it. A second copy of that logic
would be free to drift from the first. What moved is the door, not the wall.

**It does not authenticate its caller and does not try** (S-201.1). It cannot
tell the runner from the lead. Containment is that the runner holds only these
tools, on the un-named spawn path that makes a role's tool list actually bind
(D-0132) — not that the door recognises anyone.

Protocol plumbing follows `tools/doc-index/server.py`: line-delimited JSON-RPC
on stdin/stdout, `initialize` / `tools/list` / `tools/call` / `ping`. Pure stdlib.
"""
from __future__ import annotations

import contextlib
import json
import os
import pathlib
import sys

SERVER_VERSION = "1.0.0"
PLUGIN_ROOT = str(pathlib.Path(__file__).resolve().parents[2])
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "tools"))

import experiment_request as er  # noqa: E402
import experiment_run as ex  # noqa: E402
import friday_consent as consent  # noqa: E402
import spawn_telemetry as telemetry  # noqa: E402

# The runner used to emit its own accept/done through the telemetry CLI, under
# the Bash grant this increment removes. Something still has to, or the runner
# becomes a lane that dispatches and never reports — the exact silent gap
# ISSUE-006 exists to prevent. So the door emits them (FR-201.9), through the
# same single primitive, never a hand-rolled journal write.
#
# Honest limit: the server cannot tell the runner from the lead (S-201.1), so
# these events mean "the experiments door was used for this phase", not "that
# specific agent did it". The lead's own `spawn` emission at dispatch is
# unchanged and remains the authority on who was sent.
TELEMETRY_AGENT = "friday-experiment-runner"
TELEMETRY_PHASE = "harden:experiment"
_accepted = False

# Where a run record lands: beside the request documents it answers, inside the
# project and therefore inside git history. That placement is load-bearing, not
# tidiness — the consent record lives under `.friday/`, which is git-ignored
# working state, so the durable answer to "which experiments did I approve, and
# when" rides the run record instead (D7). It is sound only because friday
# derives this path rather than taking one (D6).
RUN_RECORD_DIR = os.path.join("docs", "reviews", "experiments", "runs")


def log(msg: str) -> None:
    print(f"[friday-experiments] {msg}", file=sys.stderr, flush=True)


def send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def result(req_id, payload: dict) -> None:
    send({"jsonrpc": "2.0", "id": req_id, "result": payload})


def project_root() -> str:
    """The server's own root — never supplied by a caller (D3, FR-201.4)."""
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


_BATCH_ARG = {
    "type": "object",
    "properties": {
        "batch": {"type": "string",
                  "description": ("the batch id the PM approved. The ONLY thing "
                                  "you supply: everything else — the request "
                                  "document, the project root, where the record "
                                  "is written — is derived from the consent "
                                  "record this id names.")},
    },
    "required": ["batch"],
    "additionalProperties": False,
}

TOOLS = [
    {"name": "plan",
     "description": ("Show exactly what batch <batch> would do — the calls, or "
                     "the reason it is refused. Reads only; it never contacts "
                     "the target and never spends the PM's approval."),
     "inputSchema": _BATCH_ARG},
    {"name": "run",
     "description": ("Run the approved experiment batch <batch> and return the "
                     "transcript. Requires a consent record the lead wrote when "
                     "the PM said yes; that approval covers one run and is spent "
                     "by this one."),
     "inputSchema": _BATCH_ARG},
    {"name": "status",
     "description": ("Report what this server can see. Takes no arguments and "
                     "reaches nothing outside this repository."),
     "inputSchema": {"type": "object", "properties": {},
                     "additionalProperties": False}},
]


def _emit(event: str, root: str, **data) -> None:
    """One telemetry event, through the single primitive (FR-201.9).

    Two things it must never do. It must never raise: a journal that cannot be
    written is not a reason to refuse an approved experiment. And it must never
    write to **stdout** — that is the JSON-RPC channel, and `spawn_telemetry`
    echoes the line it appends, which would land in the middle of a response and
    break the protocol for every later call.
    """
    argv = ["--emit", event, "--agent", TELEMETRY_AGENT, "--phase", TELEMETRY_PHASE,
            "--by", "tool", "--cwd", root]
    if data:
        argv += ["--data", json.dumps(data)]
    try:
        with contextlib.redirect_stdout(sys.stderr):
            telemetry.main(argv)
    except Exception as exc:                       # noqa: BLE001 — never break the door
        log(f"telemetry {event!r} not written (ignored): {exc!r}")


def _refuse(reason: str, **extra) -> dict:
    """Every no looks the same and says which clause said it. A refusal is a
    real answer, not a crash — the caller reports it and stops."""
    return dict({"ok": False, "refused": reason}, **extra)


def _check_args(name: str, args: dict) -> str | None:
    """The argument surface, enforced rather than documented (AC-201.3).

    An unknown key is refused, never ignored: silently dropping it would look
    identical from outside, so nobody would learn that a seeded `live_root` had
    been attempted — and the day someone added a parameter, the silence would
    become acceptance.
    """
    declared = next(t for t in TOOLS if t["name"] == name)["inputSchema"]
    allowed = set(declared.get("properties", {}))
    extra = sorted(set(args) - allowed)
    if extra:
        return (f"unexpected argument(s) {', '.join(repr(e) for e in extra)} — "
                f"{name} takes {sorted(allowed) or 'nothing'} and nothing else. "
                f"The request document, the project root and the run record's "
                f"path are derived here, never supplied (INC-201 D3).")
    for req in declared.get("required", []):
        if not isinstance(args.get(req), str) or not args[req]:
            return f"missing required argument {req!r}"
    return None


def _approved(root: str, batch: str) -> tuple[dict | None, dict]:
    """The gate both tools pass through: consent, then the document it approved.

    Returns `(refusal, context)` — a refusal, or the request text and the record
    that authorises it. Every clause here is the consent contract's; none of it
    trusts anything the caller said beyond the batch id.
    """
    try:
        rec = consent.consent_read(root, batch)
    except ValueError as exc:                      # malformed id, refused by shape
        return _refuse(str(exc)), {}
    if rec is None:
        # The defined empty case, and never an implicit yes (D10).
        return _refuse(
            f"no consent record for batch {batch!r} — the PM's yes is written by "
            f"the lead when they give it, and without it nothing runs "
            f"(docs/contracts/experiment-consent.md)"), {}
    if rec.get("spent", "no") != "no":
        return _refuse(
            f"batch {batch!r} was already spent at {rec['spent']} — one yes, one "
            f"run (INC-201 D5). A retry needs a fresh approval on a new batch id."), {}
    request_path = rec.get("request", "")
    if not consent.consent_matches(root, batch=batch, request_path=request_path):
        return _refuse(
            f"the request document has changed since the PM read it: "
            f"{request_path} no longer matches the approved fingerprint "
            f"{rec.get('fingerprint')}. The approval covers the bytes that were "
            f"read, so it no longer covers this document (FR-201.5)."), {}
    try:
        with open(request_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return _refuse(f"cannot read the approved request {request_path}: {exc}"), {}
    return None, {"record": rec, "request_path": request_path, "text": text}


def _consent_summary(rec: dict) -> dict:
    """What the run record carries about the approval, so the durable trail
    answers 'was this approved, and to what' on its own (D7)."""
    return {"matched": True, "fingerprint": rec.get("fingerprint"),
            "granted": rec.get("granted"), "request": rec.get("request")}


def handle_plan(root: str, batch: str) -> dict:
    """What this batch would do — inspection, and inspection alone.

    It must not spend the approval: if looking cost the run, nobody would look.
    """
    refusal, ctx = _approved(root, batch)
    if refusal:
        return refusal
    planned = er.plan(ctx["text"], live_root=root, batch=batch)
    if not planned["ok"]:
        return _refuse("the request does not pass its own containment envelope",
                       batch=batch, errors=planned["errors"])
    return {"ok": True, "batch": batch, "request": ctx["request_path"],
            "stand_down": planned["stand_down"],
            "finding_cap": planned["finding_cap"], "calls": planned["calls"],
            "consent": _consent_summary(ctx["record"]),
            "note": "nothing was contacted and no approval was spent"}


def handle_run(root: str, batch: str) -> dict:
    """Run the approved batch, once.

    Order is deliberate: validate, **then** spend, then make the calls. Spending
    before any outward call means the approval is consumed by the attempt rather
    than by its success — a run that half-completed cannot be retried on the same
    yes. Validating first means a request that never reaches the target does not
    burn the PM's approval on a refusal.
    """
    refusal, ctx = _approved(root, batch)
    if refusal:
        return refusal
    planned = er.plan(ctx["text"], live_root=root, batch=batch)
    if not planned["ok"]:
        return _refuse("the request does not pass its own containment envelope",
                       batch=batch, errors=planned["errors"])
    try:
        consent.consent_spend(root, batch=batch)
    except ValueError as exc:                      # raced, or spent in between
        return _refuse(str(exc))
    # Past this line the approval is gone, and anything that fails from here may
    # already have reached the target — `experiment_run.run` fetches a credential
    # from it before the first move. So a failure here is reported as exactly
    # that, never as "nothing happened": the generic message would be a lie in
    # the one case where the PM most needs the truth.
    try:
        transcript = ex.run(ctx["text"], live_root=root, batch=batch)
        transcript["batch"] = batch
        transcript["request"] = ctx["request_path"]
        transcript["consent"] = _consent_summary(ctx["record"])
        path = os.path.join(root, RUN_RECORD_DIR, f"{batch}.json")
        ex.write_transcript(transcript, path, root)
    except Exception as exc:                       # noqa: BLE001 — fail closed, honestly
        log(f"run failed after the approval was spent: {exc!r}")
        return _refuse(
            f"batch {batch!r} failed while running ({type(exc).__name__}: {exc}). "
            f"Its approval was already spent, and calls may have reached the "
            f"target before the failure — so this batch will not run again on it. "
            f"A retry needs a fresh PM yes on a new batch id.", batch=batch,
            approval="spent")
    return dict(transcript, transcript_path=path)


def handle_status(root: str) -> dict:
    contract = os.path.join(root, "docs", "contracts", "experiment-consent.md")
    return {"ok": True, "server": "friday-experiments", "version": SERVER_VERSION,
            "project_root": root, "plugin_root": PLUGIN_ROOT,
            "root_source": ("CLAUDE_PROJECT_DIR"
                            if os.environ.get("CLAUDE_PROJECT_DIR") else "cwd"),
            "consent_contract_present": os.path.isfile(contract),
            "tools": [t["name"] for t in TOOLS]}


def call_tool(name: str, args: dict, root: str) -> dict:
    """One tool call → one answer. Never raises (FR-201.10).

    An unexpected failure becomes a refusal, because the alternative is a
    stack trace crossing the protocol boundary as something the caller has to
    interpret. A door whose failure mode is ambiguous is a door that opens.
    """
    try:
        if name not in {t["name"] for t in TOOLS}:
            return _refuse(f"unknown tool {name!r} — this server exposes "
                           f"{', '.join(t['name'] for t in TOOLS)} and nothing else")
        bad = _check_args(name, args or {})
        if bad:
            return _refuse(bad)
        if name == "status":
            return handle_status(root)
        global _accepted
        if not _accepted:
            # First real use of the door: the work was taken up.
            _emit("accept", root, batch=args["batch"], tool=name)
            _accepted = True
        if name == "plan":
            return handle_plan(root, args["batch"])
        out = handle_run(root, args["batch"])
        # `run` is terminal either way — a refusal ends the runner's work as
        # surely as a transcript does, and a lane that only reports its
        # successes is the half-instrumented shape ISSUE-006 names.
        _emit("done", root, batch=args["batch"], ok=bool(out.get("ok")))
        return out
    except Exception as exc:                       # noqa: BLE001 — fail closed
        log(f"{name} failed closed: {exc!r}")
        return _refuse(f"{name} failed and therefore did nothing: "
                       f"{type(exc).__name__}: {exc}")


def _initialize_reply(msg: dict) -> dict:
    proto = msg.get("params", {}).get("protocolVersion", "2024-11-05")
    return {"protocolVersion": proto, "capabilities": {"tools": {}},
            "serverInfo": {"name": "friday-experiments", "version": SERVER_VERSION}}


def _call_reply(payload: dict) -> dict:
    """One tool answer in the shape `tools/call` returns.

    `isError` tracks the refusal: a no at this boundary IS an error, and it must
    be loud in the caller's transcript rather than a quiet field they might read
    past.
    """
    return {"content": [{"type": "text",
                         "text": json.dumps(payload, ensure_ascii=False)}],
            "structuredContent": payload,
            "isError": not payload.get("ok", False)}


def dispatch(msg: dict, root: str) -> dict | None:
    """One JSON-RPC message → the reply to send, or None for no reply.

    Split out of the read loop so the loop reads as a loop. Every branch is a
    single expression; nothing here decides anything about an experiment.
    """
    method = msg.get("method")
    if method == "initialize":
        return _initialize_reply(msg)
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        params = msg.get("params", {})
        return _call_reply(call_tool(params.get("name"),
                                     params.get("arguments") or {}, root))
    if method == "ping":
        return {}
    return None


def main() -> None:
    root = project_root()
    log(f"started (root={root})")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log(f"unparseable line: {line[:120]}")
            continue
        req_id, method = msg.get("id"), msg.get("method")
        reply = dispatch(msg, root)
        if reply is not None:
            result(req_id, reply)
        elif req_id is not None and method != "notifications/initialized":
            send({"jsonrpc": "2.0", "id": req_id,
                  "error": {"code": -32601,
                            "message": f"method not supported: {method}"}})
    log("stdin closed — exiting")


if __name__ == "__main__":
    main()
