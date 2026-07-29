#!/usr/bin/env python3
"""The experiment request grammar — the wall the experiment runner acts through
(INC-200 FR-200.4 / FR-200.5, contract: docs/contracts/experiment-request.md).

friday's reviewers have always DESIGNED experiments and never run them. The
runner is the first friday role that acts on a system instead of reading one,
so its reach is defined by what this grammar can express — and the point of the
design is that it can express very little.

**A closed, parameterized menu, and nothing else.** Four moves exist:

    move: request <METHOD> <path>                       — issue this request
    move: swap-identifier <METHOD> <path{id}> <a> <b>    — swap this identifier
    move: replay-token <METHOD> <path>                   — replay this token
    move: drop-credential <METHOD> <path>                — repeat without it

There is **no free-form entry and never a shell entry** — not a filtered one, a
nonexistent one. No key in the closed key set and no move in the closed move
set carries anything that becomes a command; nothing in this module or its
executor hands a string to a process. A request attempting command execution is
refused because the shape has nowhere to put it — at parse, structurally — and
never because something matched a list of dangerous words. A denylist is the
explicitly rejected shape (INC-200 S-200.1): it is a list of the attacks
somebody already thought of. Widening this later means deleting a line that
forbids it.

Everything else the runner is allowed to do is decided here too, so that every
boundary is a real refusal a test can trigger rather than a promise in prose:
egress is pinned to the PM-declared target, the target must be declared
non-production, each batch needs its own explicit PM yes, work happens in an
isolated worktree and never the live tree, the shared `.friday/` substrate is
read-only to the runner, and with no declared target the runner stands down
with findings capped at `informational`.

Empty case: a present-but-empty FRIDAY-EXPERIMENT block is a VALID request with
nothing to run (distinct from an absent block, which is an error).

Exit codes (as a CLI): 0 the request is runnable · 1 refused · 2 bad
invocation. Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taglines  # noqa: E402

BLOCK = "FRIDAY-EXPERIMENT"

# The closed vocabularies. These two tuples ARE the runner's reach: it can do
# what they name and there is no other door. Note what is absent by design —
# no key or move that could name a command, a host, a file to execute, or a
# program to invoke.
KEYS = ("experiment", "designed-by", "target", "target-class", "worktree",
        "consent", "credential-from", "move", "expect")
REPEATABLE = ("move", "expect")
MOVES = ("request", "swap-identifier", "replay-token", "drop-credential")
METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")

# A path, not a URL and not an argument list: it must be site-relative (so a
# move can never name a host), and it may contain only characters that are
# literally part of a path. Everything a quoting trick needs — whitespace,
# semicolons, ampersands, pipes, backticks, dollars, parentheses, quotes — is
# outside the class, so those requests do not parse.
_PATH_RE = re.compile(r"^/(?!/)[A-Za-z0-9._~/-]*(?:\{id\}[A-Za-z0-9._~/-]*)?$")
_ID_RE = re.compile(r"^[A-Za-z0-9._~-]+$")
_CONSENT_RE = re.compile(r"^pm-yes\s+([A-Za-z0-9._~-]+)$")

# The plan you READ is the plan that runs. Python's str.splitlines() — which
# every taglines block goes through — breaks on far more than "\n": vertical
# tab, form feed, the file/group/record separators, NEL, and the Unicode line
# and paragraph separators. Dropped into a free-text field (`expect:`,
# `experiment:`, `designed-by:` — the ones no shape constrains), any of them
# becomes a line break the parser honours and a human reading the document as
# prose cannot see, silently adding a whole extra legal `move:`.
#
# That is not a KH-1 breach — the smuggled line is still confined to the closed
# menu and the declared target — but it defeats something the runner's safety
# genuinely rests on: the PM consents to a batch by READING it, and the
# reviewer designs it by writing something a human checks. A request whose
# visible text disagrees with its parsed text is refused outright rather than
# silently reconciled. Found by the INC-200 independent hardening pass.
_INVISIBLE_BREAKS = ("\v", "\f", "\r", "\x1c", "\x1d", "\x1e", "\x85",
                     " ", " ")

# How each move's arguments are shaped and what it does with the credential the
# target issued. `arity` counts the whole line including the verb.
_MOVE_SPEC = {
    "request": {"arity": 3, "credential": "as-issued"},
    "replay-token": {"arity": 3, "credential": "replayed"},
    "drop-credential": {"arity": 3, "credential": "none"},
    "swap-identifier": {"arity": 5, "credential": "as-issued"},
}


def _parse_move(value: str) -> tuple[dict | None, str | None]:
    """One `move:` value → (move, error). Verb first, then a method and a
    site-relative path, then whatever that verb takes. Any surprise is an
    error about the SHAPE, never about the content."""
    parts = value.split()
    verb = parts[0] if parts else ""
    if verb not in MOVES:
        return None, (f"unknown move {verb!r} — not one of the "
                      f"{len(MOVES)} moves the menu defines "
                      f"({', '.join(MOVES)})")
    spec = _MOVE_SPEC[verb]
    if len(parts) != spec["arity"]:
        return None, (f"move {verb!r} takes exactly {spec['arity'] - 1} "
                      f"argument(s); got {len(parts) - 1} — extra arguments "
                      f"are refused, never passed through")
    method, path = parts[1], parts[2]
    if method not in METHODS:
        return None, f"unknown method {method!r} in move {verb!r}"
    if not _PATH_RE.match(path):
        return None, (f"{path!r} is not a site-relative path — a move names a "
                      f"path on the declared target, never a host, and never "
                      f"anything outside path characters")
    move = {"verb": verb, "method": method, "path": path,
            "credential": spec["credential"], "ids": parts[3:]}
    return _check_ids(move)


def _check_ids(move: dict) -> tuple[dict | None, str | None]:
    """swap-identifier's two identifiers, and the template that consumes them."""
    if move["verb"] != "swap-identifier":
        return move, None
    if "{id}" not in move["path"]:
        return None, ("swap-identifier needs a path containing {id} — that is "
                      "where the identifier it swaps goes")
    for ident in move["ids"]:
        if not _ID_RE.match(ident):
            return None, f"{ident!r} is not an identifier"
    return move, None


def _credential_source_ok(value: str) -> bool:
    parts = value.split()
    return (len(parts) == 2 and parts[0] in METHODS
            and bool(_PATH_RE.match(parts[1])))


def parse_request(text: str) -> dict:
    """{'ok', 'errors', 'request'} for one experiment request document."""
    lines = taglines.block_lines(text, BLOCK)
    if lines is None:
        return {"ok": False, "request": {"moves": []},
                "errors": [f"no {BLOCK} block in the experiment request"]}
    hidden = [ch for ch in _INVISIBLE_BREAKS if ch in text]
    if hidden:
        # Refused whole, never sanitized: silently stripping the character
        # would leave a document that still reads differently from what runs.
        return {"ok": False, "request": {"moves": []},
                "errors": [f"invisible line boundary {hidden[0]!r} in the "
                           f"request — it would split a line a reader cannot "
                           f"see splitting, so the batch that runs would not "
                           f"be the batch the PM read"]}
    req: dict = {"moves": [], "expect": []}
    errors: list[str] = []
    for ln in lines:
        parsed = taglines.parse_typed_line(ln)
        if not parsed:
            errors.append(f"not a typed line: {ln!r}")
            continue
        errors.extend(_absorb(req, parsed[0], parsed[1]))
    return {"ok": not errors, "errors": errors, "request": req}


def _absorb(req: dict, key: str, value: str) -> list[str]:
    """Fold one typed line into the request under the closed key set."""
    if key not in KEYS:
        return [f"unknown key {key!r} — the request grammar defines exactly "
                f"{', '.join(KEYS)} and nothing else"]
    if key == "move":
        move, err = _parse_move(value)
        if err:
            return [err]
        req["moves"].append(move)
        return []
    if key == "expect":
        req["expect"].append(value)
        return []
    if key == "credential-from" and not _credential_source_ok(value):
        # Same shape rule as a move: a METHOD and a site-relative path on the
        # declared target. The credential the runner handles is therefore
        # issued BY that target, by construction (S-200.4).
        return [f"credential-from must be `<METHOD> <path>` on the declared "
                f"target; got {value!r}"]
    if key in req:
        return [f"{key!r} given twice — it takes a single value"]
    req[key] = value
    return []


def egress_allowed(url: str, target: str) -> bool:
    """True only when `url` lands on exactly the declared target's origin.

    Asked again by the executor immediately before each connection, so a plan
    that was altered after planning still cannot reach another host. Scheme,
    host AND port must match — a sibling host that merely starts with the
    target's name is a different origin.
    """
    got, want = urlsplit(url), urlsplit(target)
    if got.scheme not in ("http", "https"):
        return False
    return (got.scheme, got.netloc.lower()) == (want.scheme, want.netloc.lower())


def write_allowed(path: str, root: str) -> bool:
    """False for anything inside the shared `.friday/` substrate.

    Worktrees isolate code and deliberately SHARE the substrate (the journal
    and decision ids must not fragment), so the runner's read-only relationship
    to it is enforced here rather than inherited from the worktree boundary.
    """
    substrate = os.path.abspath(os.path.join(root, ".friday"))
    target = os.path.abspath(path)
    return not (target == substrate or target.startswith(substrate + os.sep))


def _check_envelope(req: dict, live_root: str, batch: str | None) -> list[str]:
    """The containment envelope, every clause a real refusal (FR-200.5)."""
    errors: list[str] = []
    if req.get("target-class") != "non-production":
        errors.append("the declared target must be marked "
                      "`target-class: non-production` — an undeclared or "
                      "production target is refused (S-200.4)")
    if not egress_allowed(req.get("target", "") + "/", req.get("target", "")):
        errors.append(f"target {req.get('target')!r} is not an http(s) origin")
    errors.extend(_check_consent(req, batch))
    errors.extend(_check_worktree(req, live_root))
    return errors


def _check_consent(req: dict, batch: str | None) -> list[str]:
    m = _CONSENT_RE.match(req.get("consent", ""))
    if not m:
        return ["no explicit PM yes for this batch — a batch runs only on "
                "`consent: pm-yes <batch-id>`"]
    if batch is not None and m.group(1) != batch:
        return [f"this request carries the PM's yes for batch "
                f"{m.group(1)!r}, not {batch!r} — consent is per batch, "
                f"never a standing grant"]
    return []


def _check_worktree(req: dict, live_root: str) -> list[str]:
    wt = req.get("worktree")
    if not wt:
        return ["no `worktree:` declared — the runner works in an isolated "
                "worktree, never the live tree"]
    if os.path.abspath(wt) == os.path.abspath(live_root):
        return [f"{wt!r} IS the live tree — the runner never operates there"]
    if not os.path.isdir(wt):
        return [f"declared worktree {wt!r} does not exist"]
    return []


def _plan_calls(req: dict) -> list[dict]:
    target = req["target"].rstrip("/")
    calls: list[dict] = []
    for move in req["moves"]:
        ids = move["ids"] or [None]
        for ident in ids:
            path = (move["path"].replace("{id}", ident) if ident
                    else move["path"])
            calls.append({"move": move["verb"], "method": move["method"],
                          "url": target + path,
                          "credential": move["credential"]})
    return calls


def plan(text: str, *, live_root: str, batch: str | None = None) -> dict:
    """Parse + contain → the exact calls the runner may make, or a refusal.

    `live_root` is the real project tree the runner must stay out of; `batch`
    is the batch id the caller holds the PM's yes for (None = don't check).
    """
    parsed = parse_request(text)
    out = {"ok": False, "errors": list(parsed["errors"]), "stand_down": False,
           "finding_cap": None, "calls": []}
    if not parsed["ok"]:
        return out
    req = parsed["request"]
    if not req.get("target"):
        # Not an error — a refusal to act. Nothing was demonstrated, so the cap
        # that has always applied to an undemonstrated finding stays on.
        out.update(ok=True, stand_down=True, finding_cap="informational")
        return out
    out["errors"].extend(_check_envelope(req, live_root, batch))
    if out["errors"]:
        return out
    out.update(ok=True, calls=_plan_calls(req))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate + plan one experiment request")
    ap.add_argument("--request", required=True, help="path to the request document")
    ap.add_argument("--live-root", default=".", help="the tree the runner stays out of")
    ap.add_argument("--batch", default=None, help="batch id the PM's yes covers")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        with open(args.request, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"experiment_request: cannot read {args.request}: {exc}", file=sys.stderr)
        return 2
    res = plan(text, live_root=args.live_root, batch=args.batch)
    if args.json:
        print(json.dumps(res, indent=2))
    elif res["stand_down"]:
        print("stood down: no declared target — findings capped at informational")
    elif res["ok"]:
        print(f"runnable: {len(res['calls'])} call(s) against the declared target")
    else:
        print("refused:\n  " + "\n  ".join(res["errors"]))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
