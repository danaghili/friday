"""INC-201 FR-201.3 / FR-201.5 / FR-201.6 — the consent record, test-first.

**What this record is for.** Today the runner types its own batch id and the
executor checks it against the batch id written in the request document. Both
are things the runner can read, and — until this increment — write. So the check
confirms the runner is being *consistent*; it never proves the PM said anything
(D4, D5). This record is the PM's yes made unforgeable: written by the lead
through the single substrate writer, into `.friday/`, which the runner is
forbidden to write and — with no shell and no `Write` — structurally cannot.

Three properties, each tested here:

- **Bound to the document's contents** (FR-201.5). The record pins a fingerprint
  of the exact request bytes the PM read. One character's drift afterwards and
  the approval no longer matches. This finishes what D-0131 started: that entry
  refused invisible line breaks so the request a human reads is the request that
  runs; the fingerprint holds the same property *across time* rather than only
  at parse.
- **One yes, one run** (FR-201.6). The approval is spent by the run it
  authorises. `docs/contracts/experiment-request.md:74` already promises "each
  batch needs its own explicit PM yes", and
  `tests/test_inc200_experiment_request.py:204-212` proves only that batch 7's
  yes will not run *as batch 8*. Nothing stopped batch 7 running twice, and the
  menu is not read-only — `tools/experiment_request.py:63` permits POST, PUT,
  PATCH and DELETE.
- **The empty case is a real outcome** (house rule): no record at all is a
  distinct, valid, tested state — not an error and not an implicit yes.

**A hazard the increment implies but does not spell out.** The batch id reaches
a filename here, and again when the run record's path is derived (FR-201.7). An
id carrying a path separator or `..` would escape `.friday/`, which would hand
back a write primitive at the exact moment this increment is removing one. The
id shape is therefore validated at the writer, and the refusal is tested — a
shape check, not a denylist of bad strings (S-200.1's rejected shape).
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import friday_consent as fs  # noqa: E402

REQUEST = """experiment: broken-access-control
designed-by: friday-security-reviewer
target: http://127.0.0.1:8099
target-class: non-production
worktree: /tmp/exp-worktree
consent: pm-yes batch-7
move: request GET /api/me
"""


def _proj(tmp_path, text=REQUEST):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / ".friday").mkdir(parents=True)
    req = root / "docs" / "req.md"
    req.write_text(text, encoding="utf-8")
    return str(root), str(req)


# --- the empty case, defined and tested ---------------------------------------------

def test_no_record_is_a_distinct_valid_outcome(tmp_path):
    """No consent is not an error and never an implicit yes — it is a clean
    'nothing here', which is what fail-closed (D10) reads to stand down."""
    root, _ = _proj(tmp_path)
    assert fs.consent_read(root, "batch-7") is None


def test_reading_an_absent_batch_does_not_create_anything(tmp_path):
    root, _ = _proj(tmp_path)
    fs.consent_read(root, "batch-7")
    assert not os.path.exists(os.path.join(root, ".friday", "consent"))


# --- writing the yes ----------------------------------------------------------------

def test_write_pins_the_batch_the_request_and_its_fingerprint(tmp_path):
    root, req = _proj(tmp_path)
    path = fs.consent_write(root, batch="batch-7", request_path=req)
    assert os.path.isfile(path)
    rec = fs.consent_read(root, "batch-7")
    assert rec["batch"] == "batch-7"
    assert rec["request"].endswith("req.md")
    assert rec["fingerprint"].startswith("sha256:")
    assert rec["spent"] == "no"
    assert rec["granted"]  # an ISO stamp, so the record can be aged


def test_the_record_lands_under_the_friday_substrate(tmp_path):
    """It must live where the runner cannot write. With no shell and no Write
    the runner structurally cannot reach here — but the location is the reason
    that is true, so it is asserted rather than assumed."""
    root, req = _proj(tmp_path)
    path = fs.consent_write(root, batch="batch-7", request_path=req)
    assert os.path.realpath(path).startswith(
        os.path.realpath(os.path.join(root, ".friday")))


def test_a_second_yes_for_the_same_batch_is_refused(tmp_path):
    """One batch, one approval. A silent overwrite would let a fresh yes be
    minted for a batch already approved and spent."""
    root, req = _proj(tmp_path)
    fs.consent_write(root, batch="batch-7", request_path=req)
    try:
        fs.consent_write(root, batch="batch-7", request_path=req)
    except ValueError as exc:
        assert "batch-7" in str(exc)
    else:
        raise AssertionError("a second consent write for the same batch must refuse")


def test_a_missing_request_document_refuses(tmp_path):
    root, _ = _proj(tmp_path)
    try:
        fs.consent_write(root, batch="batch-7",
                         request_path=os.path.join(root, "docs", "nope.md"))
    except (ValueError, OSError):
        pass
    else:
        raise AssertionError("consent cannot be granted for a document that is not there")


# --- the batch id reaches a filename: shape, not denylist ---------------------------

def test_a_batch_id_that_would_escape_the_substrate_is_refused(tmp_path):
    """Shape check by construction. These are refused for not matching the legal
    id shape, NOT because they appear on a list of dangerous strings — a
    denylist is the rejected shape (S-200.1)."""
    root, req = _proj(tmp_path)
    for bad in ("../escape", "a/b", "..", "", "with space", "tab\tid", "x" * 200):
        try:
            fs.consent_write(root, batch=bad, request_path=req)
        except ValueError:
            continue
        raise AssertionError(f"batch id {bad!r} should have been refused")


def test_reading_a_malformed_batch_id_refuses_rather_than_probing_disk(tmp_path):
    root, _ = _proj(tmp_path)
    for bad in ("../escape", "a/b"):
        try:
            fs.consent_read(root, bad)
        except ValueError:
            continue
        raise AssertionError(f"batch id {bad!r} should have been refused on read")


# --- bound to the document's contents (FR-201.5) ------------------------------------

def test_the_fingerprint_follows_the_bytes_the_pm_read(tmp_path):
    root, req = _proj(tmp_path)
    fs.consent_write(root, batch="batch-7", request_path=req)
    before = fs.consent_read(root, "batch-7")["fingerprint"]
    assert fs.consent_matches(root, batch="batch-7", request_path=req)
    # one character, anywhere
    with open(req, encoding="utf-8") as fh:
        text = fh.read()
    with open(req, "w", encoding="utf-8") as fh:
        fh.write(text.replace("/api/me", "/api/mE"))
    assert not fs.consent_matches(root, batch="batch-7", request_path=req)
    # the record itself is unchanged — it is the document that drifted
    assert fs.consent_read(root, "batch-7")["fingerprint"] == before


def test_matching_an_absent_record_is_false_not_an_error(tmp_path):
    root, req = _proj(tmp_path)
    assert fs.consent_matches(root, batch="batch-7", request_path=req) is False


# --- one yes, one run (FR-201.6) ----------------------------------------------------

def test_an_approval_is_spent_by_its_run(tmp_path):
    root, req = _proj(tmp_path)
    fs.consent_write(root, batch="batch-7", request_path=req)
    assert fs.consent_spend(root, batch="batch-7") is True
    rec = fs.consent_read(root, "batch-7")
    assert rec["spent"] != "no"          # carries WHEN it was spent
    assert rec["fingerprint"]            # and keeps its binding for the audit trail


def test_a_spent_approval_cannot_be_spent_again(tmp_path):
    root, req = _proj(tmp_path)
    fs.consent_write(root, batch="batch-7", request_path=req)
    fs.consent_spend(root, batch="batch-7")
    try:
        fs.consent_spend(root, batch="batch-7")
    except ValueError as exc:
        assert "spent" in str(exc).lower()
    else:
        raise AssertionError("a second run on one approval must refuse")


def test_spending_an_absent_approval_refuses(tmp_path):
    root, _ = _proj(tmp_path)
    try:
        fs.consent_spend(root, batch="batch-7")
    except ValueError:
        pass
    else:
        raise AssertionError("there is no approval to spend")


# --- the record is typed, in the house grammar --------------------------------------

def test_the_record_is_a_typed_block_a_human_can_read_and_grep(tmp_path):
    root, req = _proj(tmp_path)
    path = fs.consent_write(root, batch="batch-7", request_path=req)
    text = open(path, encoding="utf-8").read()
    assert "FRIDAY-CONSENT:BEGIN" in text and "FRIDAY-CONSENT:END" in text
    import taglines
    typed = taglines.block_typed(text, "FRIDAY-CONSENT")
    assert typed is not None
    for key in ("batch", "request", "fingerprint", "granted", "spent"):
        assert key in typed, (key, typed)
