"""handoff_package_check tests — the package invariants that ARE mechanical
(docs/contracts/handoff-package.md): required members present + the FR-83
who-can-do-this tag on every runbook bullet. The not-built case is a clean
'nothing to check', never a failure (lesson #6)."""
import handoff_package_check as hpc


def _pkg(tmp_path, *, drop=(), runbook="- [you] read the status page\n"):
    d = tmp_path / "docs" / "handoff"
    d.mkdir(parents=True)
    for m in hpc.REQUIRED_MEMBERS:
        if m in drop or m == "operations-runbook.md":
            continue
        (d / m).write_text(f"# {m}\n", encoding="utf-8")
    if "operations-runbook.md" not in drop:
        (d / "operations-runbook.md").write_text("# runbook\n\n" + runbook, encoding="utf-8")
    return tmp_path


def test_required_members_includes_promised_and_proven():
    assert "promised-and-proven.md" in hpc.REQUIRED_MEMBERS
    assert "ownership-and-keys.md" in hpc.REQUIRED_MEMBERS


def test_not_built_is_not_a_failure(tmp_path):
    r = hpc.check_package(str(tmp_path))
    assert r["built"] is False
    assert r["ok"] is True
    assert r["findings"] == []


def test_full_package_passes(tmp_path):
    _pkg(tmp_path)
    r = hpc.check_package(str(tmp_path))
    assert r["built"] is True
    assert r["ok"] is True, r["findings"]
    assert r["findings"] == []


def test_missing_member_flagged(tmp_path):
    _pkg(tmp_path, drop=("warranty.md",))
    r = hpc.check_package(str(tmp_path))
    assert r["ok"] is False
    assert any("warranty.md" in f for f in r["findings"])


def test_untagged_runbook_bullet_flagged(tmp_path):
    _pkg(tmp_path, runbook="- [you] read the status page\n- rotate the TLS certificate\n")
    r = hpc.check_package(str(tmp_path))
    assert r["ok"] is False
    assert any("rotate the TLS certificate" in f for f in r["findings"])


def test_hired_tag_accepted(tmp_path):
    _pkg(tmp_path, runbook="- [hired] rotate the TLS certificate\n- [you] check the status page\n")
    r = hpc.check_package(str(tmp_path))
    assert r["ok"] is True, r["findings"]


def test_numbered_steps_checked(tmp_path):
    _pkg(tmp_path, runbook="1. [you] open the dashboard\n2. restart the app server\n")
    r = hpc.check_package(str(tmp_path))
    assert r["ok"] is False
    assert any("restart the app server" in f for f in r["findings"])


def test_table_rows_checked_headers_exempt(tmp_path):
    runbook = (
        "| Task | Cadence | Owner |\n"
        "| --- | --- | --- |\n"
        "| [you] check backups ran | weekly | owner |\n"
        "| renew the TLS certificate | yearly | ? |\n")
    _pkg(tmp_path, runbook=runbook)
    r = hpc.check_package(str(tmp_path))
    assert r["ok"] is False
    flagged = [f for f in r["findings"] if "untagged" in f]
    assert len(flagged) == 1                          # header+separator exempt, tagged row passes
    assert "renew the TLS certificate" in flagged[0]


def test_code_fence_content_exempt(tmp_path):
    runbook = (
        "- [hired] redeploy the app:\n"
        "```\n"
        "1. ssh into the box\n"
        "- run the deploy script\n"
        "```\n")
    _pkg(tmp_path, runbook=runbook)
    r = hpc.check_package(str(tmp_path))
    assert r["ok"] is True, r["findings"]
