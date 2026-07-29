"""INC-201 FR-201.2 / FR-201.4 / FR-201.5 / FR-201.6 / FR-201.7 — the two tools.

The door the runner reaches its executor through. Two tools, **plan** and
**run**, and the whole security argument rests on what they will accept:

**The runner supplies one thing — which batch (D3, FR-201.4).** Not the request
path, not which tree is the live one, not where anything is written. Each of
those, left in the runner's hands, is a way around a promise made elsewhere: a
different live root makes the worktree clause meaningless, a different request
path attaches the PM's approval to a document they never read, and a caller-named
output path is an arbitrary file-write carrying up to 200 bytes of
attacker-chosen text per call (`tools/experiment_run.py:72`, `:78`) that
*persists* — worse than the shell in that one respect.

So a seeded attempt to influence any of them must have **nowhere to land**: it is
refused by the shape of the interface, not filtered out of it (AC-201.3). That
is the same reasoning as the request grammar's closed menu — a filter is a list
of the attacks somebody already thought of.

**The containment logic is not reimplemented (FR-201.2).** Both tools call the
existing modules, so every clause stays single-homed where its tests already
live. What moves is the door, not the wall.

Network is the one thing mocked here: `_fetch` is the external boundary, and
these tests are about the gate in front of it, not about HTTP. The real
end-to-end against a live toy target is AC-201.8's job and stays in
`tests/test_inc200_experiment_e2e.py`.
"""
import importlib.util
import json
import os
import sys

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
sys.path.insert(0, TOOLS)
import experiment_run  # noqa: E402
import friday_consent as fs  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "experiments_server", os.path.join(TOOLS, "experiments", "server.py"))
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)


REQUEST = """# experiment request

<!-- FRIDAY-EXPERIMENT:BEGIN -->
experiment: broken-access-control
designed-by: friday-security-reviewer
target: http://127.0.0.1:8099
target-class: non-production
worktree: {worktree}
consent: pm-yes {batch}
expect: the swap returns another user's record
move: request GET /api/me
<!-- FRIDAY-EXPERIMENT:END -->
"""


def _proj(tmp_path, *, batch="batch-7", doc_batch=None, friday_project=False):
    root = tmp_path / "proj"
    (root / "docs" / "reviews").mkdir(parents=True)
    (root / ".friday").mkdir(parents=True)
    if friday_project:
        # spawn_telemetry refuses outside a friday project, so a mistyped --cwd
        # cannot lazy-create a stray `.friday/`. Telemetry tests need a real one.
        (root / "docs" / "TECHNICAL_SOW.md").write_text("# tsow\n", encoding="utf-8")
    worktree = tmp_path / "exp-worktree"
    worktree.mkdir()
    req = root / "docs" / "reviews" / "req.md"
    req.write_text(REQUEST.format(worktree=str(worktree),
                                  batch=doc_batch or batch), encoding="utf-8")
    return str(root), str(req)


def _grant(root, req, batch="batch-7"):
    return fs.consent_write(root, batch=batch, request_path=req)


def _no_network(monkeypatch):
    """Mock the external boundary only — the gate in front of it is real."""
    monkeypatch.setattr(experiment_run, "_fetch", lambda url, method, cred, target: {
        "url": url, "method": method, "status": 200, "body_head": "ok",
        "body_is": "UNTRUSTED"})


# --- FR-201.4 / AC-201.3: the argument surface is one batch id ----------------------

def test_neither_tool_declares_a_path_a_root_or_a_target():
    """Structural, read off the tools' own declared schemas. Nothing
    safety-bearing can be supplied because there is nowhere to put it."""
    for tool in server.TOOLS:
        props = set(tool["inputSchema"].get("properties", {}))
        assert props <= {"batch"}, (tool["name"], props)
        for banned in ("path", "request", "root", "live_root", "out", "target",
                       "worktree", "output"):
            assert banned not in props, (tool["name"], banned)


def test_both_tools_refuse_unknown_arguments(tmp_path):
    """A seeded attempt to smuggle a root or an output path is refused by shape.
    Silently ignoring it would look identical from outside and would rot the
    moment someone added a parameter."""
    root, req = _proj(tmp_path)
    _grant(root, req)
    for name in ("plan", "run"):
        for sneak in ({"batch": "batch-7", "live_root": "/"},
                      {"batch": "batch-7", "out": "/etc/passwd"},
                      {"batch": "batch-7", "request": "/tmp/other.md"}):
            res = server.call_tool(name, sneak, root)
            assert res["ok"] is False, (name, sneak, res)
            assert "unexpected argument" in json.dumps(res).lower(), res


def test_a_missing_batch_argument_is_refused(tmp_path):
    root, _ = _proj(tmp_path)
    for name in ("plan", "run"):
        res = server.call_tool(name, {}, root)
        assert res["ok"] is False and "batch" in json.dumps(res).lower()


# --- AC-201.4: no consent, no run --------------------------------------------------

def test_without_a_consent_record_nothing_runs(tmp_path):
    root, _ = _proj(tmp_path)
    for name in ("plan", "run"):
        res = server.call_tool(name, {"batch": "batch-7"}, root)
        assert res["ok"] is False
        assert "consent" in json.dumps(res).lower()


def test_a_consent_record_for_another_batch_does_not_authorise_this_one(tmp_path):
    root, req = _proj(tmp_path)
    _grant(root, req, batch="batch-7")
    res = server.call_tool("run", {"batch": "batch-8"}, root)
    assert res["ok"] is False and "consent" in json.dumps(res).lower()


# --- AC-201.5: a changed request breaks the approval -------------------------------

def test_one_altered_character_refuses_and_names_the_document(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    root, req = _proj(tmp_path)
    _grant(root, req)
    text = open(req, encoding="utf-8").read()
    open(req, "w", encoding="utf-8").write(text.replace("/api/me", "/api/mE"))
    res = server.call_tool("run", {"batch": "batch-7"}, root)
    assert res["ok"] is False
    blob = json.dumps(res)
    assert "req.md" in blob, res          # says WHICH document drifted
    assert "changed" in blob.lower() or "fingerprint" in blob.lower(), res


def test_an_unchanged_request_runs(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    root, req = _proj(tmp_path)
    _grant(root, req)
    res = server.call_tool("run", {"batch": "batch-7"}, root)
    assert res["ok"] is True, res


# --- AC-201.6: one yes, one run ----------------------------------------------------

def test_the_same_approval_cannot_run_twice(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    root, req = _proj(tmp_path)
    _grant(root, req)
    first = server.call_tool("run", {"batch": "batch-7"}, root)
    assert first["ok"] is True, first
    second = server.call_tool("run", {"batch": "batch-7"}, root)
    assert second["ok"] is False
    assert "spent" in json.dumps(second).lower(), second


def test_plan_does_not_spend_the_approval(tmp_path):
    """Planning is inspection — it must not consume the PM's yes, or looking
    would cost the run."""
    root, req = _proj(tmp_path)
    _grant(root, req)
    assert server.call_tool("plan", {"batch": "batch-7"}, root)["ok"] is True
    assert fs.consent_read(root, "batch-7")["spent"] == "no"


# --- AC-201.7: the two batch-id sites must agree -----------------------------------

def test_a_request_whose_own_batch_id_disagrees_is_refused(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    root, req = _proj(tmp_path, batch="batch-7", doc_batch="batch-9")
    _grant(root, req, batch="batch-7")
    res = server.call_tool("run", {"batch": "batch-7"}, root)
    assert res["ok"] is False, res
    # pinned to the REASON: an earlier version of this test passed because the
    # fixture was malformed, which is the failure mode a green test hides best.
    assert "batch-9" in json.dumps(res), res
    assert fs.consent_read(root, "batch-7")["spent"] == "no"   # and cost nothing


# --- FR-201.7: the run record's path is derived, never supplied --------------------

def test_the_run_record_path_is_derived_from_the_batch(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    root, req = _proj(tmp_path)
    _grant(root, req)
    res = server.call_tool("run", {"batch": "batch-7"}, root)
    assert res["ok"] is True, res
    written = res["transcript_path"]
    assert "batch-7" in os.path.basename(written)
    assert os.path.isfile(written)
    # inside the project, and NOT in the git-ignored substrate — D7's durable
    # trail depends on it living somewhere history keeps.
    assert os.path.realpath(written).startswith(os.path.realpath(root))
    assert ".friday" not in os.path.realpath(written)


def test_the_run_record_states_its_batch_and_that_consent_matched(tmp_path, monkeypatch):
    """D7: the durable answer to 'which experiments did I approve, and when' rides
    here, because the consent record itself is git-ignored working state."""
    _no_network(monkeypatch)
    root, req = _proj(tmp_path)
    _grant(root, req)
    res = server.call_tool("run", {"batch": "batch-7"}, root)
    body = json.loads(open(res["transcript_path"], encoding="utf-8").read())
    assert body["batch"] == "batch-7"
    assert body["consent"]["matched"] is True
    assert body["consent"]["fingerprint"].startswith("sha256:")


# --- FR-201.9: telemetry, through the one primitive ---------------------------------

def test_running_a_batch_journals_accept_and_done(tmp_path, monkeypatch):
    """The runner used to emit these itself, under the Bash grant this increment
    removes. Without a replacement the lane would dispatch and never report —
    ISSUE-006's silent gap, reintroduced by a security fix."""
    _no_network(monkeypatch)
    root, req = _proj(tmp_path, friday_project=True)
    _grant(root, req)
    server._accepted = False
    assert server.call_tool("run", {"batch": "batch-7"}, root)["ok"] is True
    events = [json.loads(ln) for ln in
              open(os.path.join(root, ".friday", "journal.jsonl"), encoding="utf-8")
              if ln.strip()]
    emitted = [e["event"] for e in events]
    assert "accept" in emitted and "done" in emitted, emitted
    done = next(e for e in events if e["event"] == "done")
    assert done["phase"] == "harden:experiment"
    assert done["by"] == "tool"                     # the door emitted it, not an agent
    assert done["data"]["agent"] == "friday-experiment-runner"
    assert done["data"]["batch"] == "batch-7"


def test_a_refused_run_still_reports_done(tmp_path):
    """A lane that journals only its successes is half-instrumented: the gap it
    leaves looks exactly like an agent that hung."""
    root, req = _proj(tmp_path, friday_project=True)
    _grant(root, req)
    server._accepted = False
    open(req, "a", encoding="utf-8").write("\n<!-- drift -->\n")   # breaks the fingerprint
    assert server.call_tool("run", {"batch": "batch-7"}, root)["ok"] is False
    events = [json.loads(ln) for ln in
              open(os.path.join(root, ".friday", "journal.jsonl"), encoding="utf-8")
              if ln.strip()]
    done = [e for e in events if e["event"] == "done"]
    assert done and done[-1]["data"]["ok"] is False, events


def test_telemetry_never_writes_to_the_protocol_channel(tmp_path, monkeypatch, capsys):
    """spawn_telemetry echoes the line it appends. On stdout that lands inside a
    JSON-RPC response and breaks every later call on the connection — a failure
    that would look like the server dying at random."""
    _no_network(monkeypatch)
    root, req = _proj(tmp_path, friday_project=True)
    _grant(root, req)
    server._accepted = False
    capsys.readouterr()
    server.call_tool("run", {"batch": "batch-7"}, root)
    assert capsys.readouterr().out == "", "the door wrote to the JSON-RPC channel"


def test_a_failing_journal_never_refuses_an_approved_experiment(tmp_path, monkeypatch):
    """Telemetry is bookkeeping. A disk that will not take a journal line is not
    a reason to withhold a run the PM approved."""
    _no_network(monkeypatch)
    root, req = _proj(tmp_path, friday_project=True)
    _grant(root, req)
    server._accepted = False
    monkeypatch.setattr(server.telemetry, "main",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("read-only fs")))
    assert server.call_tool("run", {"batch": "batch-7"}, root)["ok"] is True


# --- FR-201.2: the logic moved, it was not reimplemented ---------------------------

def test_the_server_calls_the_existing_modules(tmp_path):
    """Guards against a second copy of the containment logic drifting from the
    first — the exact defect INC-200's tester found in verify_review_format."""
    src = open(os.path.join(TOOLS, "experiments", "server.py"), encoding="utf-8").read()
    assert "experiment_request" in src and "experiment_run" in src
    for reimplemented in ("MOVES =", "METHODS =", "def egress_allowed", "def parse_request"):
        assert reimplemented not in src, reimplemented


def test_unknown_tool_names_are_refused(tmp_path):
    root, _ = _proj(tmp_path)
    res = server.call_tool("exec", {"batch": "batch-7"}, root)
    assert res["ok"] is False


# --- FR-201.10: fail closed ---------------------------------------------------------

def test_an_internal_failure_becomes_a_refusal_and_never_escapes(tmp_path, monkeypatch):
    """A stack trace crossing this boundary would reach the runner as text it has
    to interpret — and the runner's whole design is that it never interprets. A
    door whose failure mode is ambiguous is a door that opens."""
    root, req = _proj(tmp_path)
    _grant(root, req)
    monkeypatch.setattr(server.consent, "consent_read",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk gone")))
    for name in ("plan", "run"):
        res = server.call_tool(name, {"batch": "batch-7"}, root)   # must not raise
        assert res["ok"] is False
        assert "did nothing" in json.dumps(res), res


def test_a_crash_mid_run_keeps_the_approval_spent_and_says_so(tmp_path, monkeypatch):
    """Fail-closed here means closed toward the TARGET, not toward convenience.

    Once the run has begun, calls may already have reached a live system —
    `experiment_run.run` fetches a credential from it before the first move. So a
    crash must NOT hand the approval back: the alternative is a retry that
    silently repeats real calls the PM approved once. The cost is that a crash
    before anything happened also burns an approval, which is the safe direction
    to be wrong in, and is why the refusal has to SAY the approval is gone rather
    than claim nothing happened.
    """
    root, req = _proj(tmp_path)
    _grant(root, req)
    monkeypatch.setattr(experiment_run, "run",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    res = server.call_tool("run", {"batch": "batch-7"}, root)
    assert res["ok"] is False
    assert fs.consent_read(root, "batch-7")["spent"] != "no"
    blob = json.dumps(res).lower()
    assert "spent" in blob and "fresh pm yes" in blob, res
    assert "did nothing" not in blob, "the generic message would be a lie here"


def test_a_refusal_before_the_run_starts_costs_nothing(tmp_path):
    """The other side of the same rule: every check that can fail without
    touching the target happens BEFORE the approval is spent, so an ordinary
    refusal never costs the PM a yes."""
    root, req = _proj(tmp_path, batch="batch-7", doc_batch="batch-9")
    _grant(root, req, batch="batch-7")
    assert server.call_tool("run", {"batch": "batch-7"}, root)["ok"] is False
    assert fs.consent_read(root, "batch-7")["spent"] == "no"


def test_the_door_failing_is_a_stand_down_not_a_workaround(tmp_path):
    """The contract's clause, checked where it is actually decided: a refusal is
    a complete, final answer — it carries a reason and nothing that reads as a
    retry hint, an alternative route, or a way to widen the request."""
    root, _ = _proj(tmp_path)                      # no consent record at all
    res = server.call_tool("run", {"batch": "batch-7"}, root)
    assert res["ok"] is False and res["refused"]
    blob = json.dumps(res).lower()
    for escape_hatch in ("bash", "shell", "python3", "--out", "--live-root", "instead try"):
        assert escape_hatch not in blob, (escape_hatch, res)
