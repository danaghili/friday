#!/usr/bin/env python3
"""The PM's consent record — the yes that authorises one experiment batch.

INC-201 FR-201.3 / FR-201.5 / FR-201.6. Contract:
`docs/contracts/experiment-consent.md`. **Producer:** the lead, at the moment the
PM says yes (harden Step 3). **Consumers:** the `friday-experiments` server
(`tools/experiments/server.py`), which reads and spends it.

The runner types its own batch id, and the executor compares it against the batch
id inside the request document. Both are things the runner can read — and, while
it held a shell, write. So that check proves the runner is being CONSISTENT; it
never proved the PM said anything (D4). These verbs are the PM's yes made
unforgeable: written by the lead, into `.friday/`, which the runner is forbidden
to write and — holding no shell and no `Write` — structurally cannot.

The record pins the request's BYTES, not just its name (D4 / FR-201.5). D-0131
refused invisible line breaks so the request a human reads is the request that
runs; the fingerprint holds that same property across time rather than only at
parse. And the approval is spent by the run it authorises (D5 / FR-201.6),
closing the gap between what `docs/contracts/experiment-request.md` promises and
what it enforced.

**Why this is its own module, not part of `friday_substrate`.** It owns one
record end to end — the id's legal shape, the path, the fingerprint, the block
format, and the read/write/match/spend lifecycle — which is a whole concept
rather than a substrate primitive, and it is the shape `tools/decisions.py` and
`tools/standards_deviations.py` already use: each owns its own record and reaches
`friday_substrate` for the shared primitives (root resolution, the journal, time).
The single-writer rule those all honour is about ONE owner of the shared
primitives, not one file that must hold every record type. Splitting it out is
also what took `friday_substrate.py` back under its declared 500-line bar rather
than spending a justified deviation on a file that had simply grown a tenth
concern.

Pure stdlib.
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import friday_substrate as fs  # noqa: E402
import taglines  # noqa: E402


# The batch id reaches a FILENAME here, and again where the run record's path is
# derived (FR-201.7). A separator or `..` would escape `.friday/` and hand back a
# write primitive at the exact moment this increment removes one. So the id is
# validated by SHAPE — a closed pattern of what is legal — never by a denylist of
# dangerous strings, which is the rejected shape (S-200.1): a denylist is a list
# of the attacks somebody already thought of. Leading char is alphanumeric, so
# `.`/`..` cannot parse.
_BATCH_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _check_batch_id(batch: str) -> str:
    if not isinstance(batch, str) or not _BATCH_ID_RE.match(batch):
        raise ValueError(
            f"batch id {batch!r} is not a legal id — it must match "
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63} (it becomes a filename under "
            ".friday/, so a separator or `..` would escape the substrate)")
    return batch


def _consent_path(cwd: str, batch: str) -> str:
    return os.path.join(fs.friday_dir(cwd), "consent", f"{_check_batch_id(batch)}.md")


def request_fingerprint(request_path: str) -> str:
    """`sha256:<hex>` over the request document's exact bytes.

    Bytes, never parsed content: the point is that what the PM READ is what runs,
    and a reparse would forgive exactly the invisible drift D-0131 refused.
    """
    h = hashlib.sha256()
    with open(request_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def consent_write(cwd: str, *, batch: str, request_path: str) -> str:
    """Record the PM's yes for one batch, bound to one request document.

    Written by the LEAD at the moment of the yes — never by the runner, which
    cannot reach here. Refuses a second yes for a batch that already has one: a
    silent overwrite would let a fresh approval be minted for a batch already
    approved and already spent. Returns the record's path.
    """
    _check_batch_id(batch)
    if not os.path.isfile(request_path):
        raise ValueError(f"no request document at {request_path} — consent cannot "
                         "be granted for a document that is not there")
    fingerprint = request_fingerprint(request_path)
    path = _consent_path(cwd, batch)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = _consent_block(batch=batch, request=request_path,
                          fingerprint=fingerprint, granted=fs.now_iso(), spent="no")
    # Atomic claim, same reason as lane_open's O_EXCL: two worktrees share this
    # substrate, and an isfile()-then-write would be a TOCTOU both could pass.
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        raise ValueError(
            f"batch {batch!r} already has a consent record — one batch, one "
            "approval (INC-201 D5). Use a new batch id for a corrected request.")
    try:
        os.write(fd, body.encode("utf-8"))
    finally:
        os.close(fd)
    with contextlib.suppress(Exception):
        fs.append_journal_line(cwd, fs.build_journal_line(
            "consent-granted", "harden:experiment", by="lead",
            data={"batch": batch}))
    return path


def _consent_block(*, batch: str, request: str, fingerprint: str,
                   granted: str, spent: str) -> str:
    """The record's bytes — a typed, greppable, human-readable block."""
    return (
        "# friday consent record\n\n"
        "<!-- Written by the LEAD at the PM's yes, through friday_substrate.\n"
        "     The experiment runner cannot write here and must never be given a\n"
        "     way to. Contract: docs/contracts/experiment-consent.md -->\n\n"
        + taglines.format_block("FRIDAY-CONSENT", [
            ("batch", batch),
            ("request", request),
            ("fingerprint", fingerprint),
            ("granted", granted),
            ("spent", spent),
        ]) + "\n")


def consent_read(cwd: str, batch: str) -> dict | None:
    """The consent record for one batch, or None when there is none.

    None is a real, valid outcome — the defined empty case — and it is never an
    implicit yes: the fail-closed path (D10) reads exactly this to stand down.
    """
    path = _consent_path(cwd, batch)
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    typed = taglines.block_typed(text, "FRIDAY-CONSENT")
    if not typed:
        return None
    return {k: v[0] for k, v in typed.items() if v}


def consent_matches(cwd: str, *, batch: str, request_path: str) -> bool:
    """True when a consent record exists for this batch AND the request document
    still hashes to the bytes the PM approved (FR-201.5).

    False — never an exception — when no record exists: an absent approval and a
    drifted one are both simply 'this batch does not run', and the caller reports
    which.
    """
    rec = consent_read(cwd, batch)
    if not rec:
        return False
    try:
        return rec.get("fingerprint") == request_fingerprint(request_path)
    except OSError:
        return False


def consent_spend(cwd: str, *, batch: str) -> bool:
    """Mark the approval spent by the run it authorises (FR-201.6).

    Refuses when there is nothing to spend, and refuses a second time — that
    refusal IS the one-yes-one-run promise. The record is kept rather than
    deleted: it carries the fingerprint and the timestamps the audit trail needs.
    """
    rec = consent_read(cwd, batch)
    if rec is None:
        raise ValueError(f"no consent record for batch {batch!r} — nothing to spend")
    if rec.get("spent", "no") != "no":
        raise ValueError(
            f"batch {batch!r} was already spent at {rec['spent']} — one yes, one "
            "run (INC-201 D5). A retry needs a fresh approval.")
    path = _consent_path(cwd, batch)
    body = _consent_block(batch=rec["batch"], request=rec["request"],
                          fingerprint=rec["fingerprint"], granted=rec["granted"],
                          spent=fs.now_iso())
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(body)
    os.replace(tmp, path)
    with contextlib.suppress(Exception):
        fs.append_journal_line(cwd, fs.build_journal_line(
            "consent-spent", "harden:experiment", by="lead",
            data={"batch": batch}))
    return True
