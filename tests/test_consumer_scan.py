"""INC-104 FR-104.2/104.7/104.8 — the mechanical half of the enumeration
(tools/consumer_scan.py).

Two needles over one walk: what declares itself (citations of the changed
thing's path) and what carries the changed thing's own name (exact-name
match). Every candidate carries its source and openable evidence; evidence
is a path and the fact of a match, never the matched line's content
(S-104.4, AC-104.7); a name too common to search usefully is reported as
exactly that, never as a silently truncated list (OQ-104.3); the two
sources the scan structurally cannot run are stated (FR-104.8).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import consumer_scan  # noqa: E402
import reckoning  # noqa: E402


def _seed(root):
    """A little project: two scripts naming the deploy tag (one beside a
    credential), a supervisor plist, a surface citing a contract, and noise
    the scan must skip."""
    os.makedirs(os.path.join(root, "scripts"))
    os.makedirs(os.path.join(root, "docs", "contracts"))
    os.makedirs(os.path.join(root, ".git"))
    with open(os.path.join(root, "scripts", "deploy.sh"), "w") as fh:
        fh.write("#!/bin/sh\n"
                 "export DEPLOY_TOKEN=sekret123value\n"
                 "docker run app:sha-tag\n")
    with open(os.path.join(root, "scripts", "rollback.sh"), "w") as fh:
        fh.write("#!/bin/sh\n# falls back when sha-tag is absent\n"
                 "docker run app:sha-tag || docker run app:latest\n")
    with open(os.path.join(root, "com.app.keepalive.plist"), "w") as fh:
        fh.write("<plist><string>app:sha-tag</string></plist>\n")
    with open(os.path.join(root, "docs", "contracts", "deploy.md"), "w") as fh:
        fh.write("# Contract: deploy\n")
    with open(os.path.join(root, "README.md"), "w") as fh:
        fh.write("Deploys follow docs/contracts/deploy.md to the letter.\n")
    with open(os.path.join(root, ".git", "config"), "w") as fh:
        fh.write("sha-tag\n")
    with open(os.path.join(root, "blob.bin"), "wb") as fh:
        fh.write(b"\x00\x01sha-tag\x00")
    with open(os.path.join(root, "docs", "RECKONINGS.md"), "w") as fh:
        fh.write("searched: change=X 2026-08-01 ... name: sha-tag ...\n")


def test_name_match_finds_consumers_with_openable_evidence(tmp_path):
    _seed(str(tmp_path))
    out = consumer_scan.scan(str(tmp_path), name="sha-tag")
    nm = out["name_match"]
    assert nm["state"] == "ran"
    whats = {c["what"] for c in nm["candidates"]}
    assert whats == {"scripts/deploy.sh", "scripts/rollback.sh",
                     "com.app.keepalive.plist"}
    dep = next(c for c in nm["candidates"]
               if c["what"] == "scripts/deploy.sh")
    assert dep["source"] == "name-match"
    assert dep["evidence"].startswith("scripts/deploy.sh:3 names sha-tag")


def test_evidence_never_reproduces_line_content(tmp_path):
    """AC-104.7: the matching line carries a credential in the clear; the
    scan reports the path and the fact of the match, never the value."""
    _seed(str(tmp_path))
    out = consumer_scan.scan(str(tmp_path), name="sha-tag")
    import json
    dumped = json.dumps(out)
    assert "sekret123value" not in dumped
    assert "DEPLOY_TOKEN" not in dumped


def test_process_shaped_files_carry_the_hint(tmp_path):
    _seed(str(tmp_path))
    out = consumer_scan.scan(str(tmp_path), name="sha-tag")
    hints = {c["what"]: c["kind_hint"] for c in out["name_match"]["candidates"]}
    assert hints["com.app.keepalive.plist"] == "process"
    assert hints["scripts/deploy.sh"] == "code"


def test_declared_scan_needs_the_path_and_cites_by_line(tmp_path):
    _seed(str(tmp_path))
    out = consumer_scan.scan(str(tmp_path), name="deploy",
                             path="docs/contracts/deploy.md")
    dec = out["declared"]
    assert dec["state"] == "ran"
    (cand,) = dec["candidates"]
    assert cand["what"] == "README.md"
    assert cand["source"] == "declared"
    assert cand["evidence"] == "README.md:1 cites docs/contracts/deploy.md"
    out2 = consumer_scan.scan(str(tmp_path), name="sha-tag")
    assert out2["declared"]["state"] == "skipped"


def test_noise_is_skipped_and_the_record_is_not_a_consumer(tmp_path):
    _seed(str(tmp_path))
    out = consumer_scan.scan(str(tmp_path), name="sha-tag")
    whats = {c["what"] for c in out["name_match"]["candidates"]}
    assert not any(w.startswith(".git") for w in whats)
    assert "blob.bin" not in whats
    assert "docs/RECKONINGS.md" not in whats
    assert out["scanned"]["skipped_binary"] == 1


def test_too_common_reports_itself_never_a_truncated_list(tmp_path):
    """OQ-104.3: over the bound the scan returns NO candidates and says
    why with the measured spread — a partial list would lie by omission."""
    _seed(str(tmp_path))
    for i in range(4):
        with open(os.path.join(str(tmp_path), f"note{i}.md"), "w") as fh:
            fh.write("app everywhere\n")
    out = consumer_scan.scan(str(tmp_path), name="app", too_common_files=3)
    nm = out["name_match"]
    assert nm["state"] == "too-common"
    assert nm["candidates"] == []
    assert nm["files_matched"] > 3
    out2 = consumer_scan.scan(str(tmp_path), name="app", too_common_files=100)
    assert out2["name_match"]["state"] == "ran"


def test_the_two_unrunnable_sources_are_stated(tmp_path):
    """FR-104.8: the scan says what it cannot do — the model's read and the
    person's answer — and carries the name search's honest limit from its
    single home."""
    _seed(str(tmp_path))
    out = consumer_scan.scan(str(tmp_path), name="sha-tag")
    assert set(out["cannot_run"]) == {"reading", "person"}
    assert reckoning.NAMELESS_LIMIT in out["limits"]


def test_empty_tree_is_a_valid_distinct_outcome(tmp_path):
    out = consumer_scan.scan(str(tmp_path), name="sha-tag")
    assert out["name_match"]["state"] == "ran"
    assert out["name_match"]["candidates"] == []
    assert out["scanned"]["files"] == 0


def test_one_candidate_per_file_with_the_match_count(tmp_path):
    _seed(str(tmp_path))
    out = consumer_scan.scan(str(tmp_path), name="sha-tag")
    rb = next(c for c in out["name_match"]["candidates"]
              if c["what"] == "scripts/rollback.sh")
    assert rb["evidence"].startswith("scripts/rollback.sh:2 names sha-tag")
    assert "2 matching line" in rb["evidence"]


def test_no_completeness_sentence_in_the_report(tmp_path):
    _seed(str(tmp_path))
    out = consumer_scan.scan(str(tmp_path), name="sha-tag",
                             path="docs/contracts/deploy.md")
    import json
    dumped = json.dumps(out).lower()
    for phrase in ("complete", "all consumers", "everything that depends"):
        assert phrase not in dumped
