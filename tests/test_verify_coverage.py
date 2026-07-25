"""Logic-core — the requirement-coverage verifier (K7 set-closure).

Two claims under test. (1) Baseline: every anchored FR/NFR/AC/S ID in the TSOW
needs a disposition; prose mentions don't mint requirements; the empty TSOW is
vacuously closed. (2) DF-023: increments live as SEPARATE oracles under
docs/increments/INC-*.md (the TSOW gets a pointer, never the spec) — their
dotted IDs (`FR-1.1`) are part of the closure set, extracted whole (never
truncated to a colliding parent `FR-1`), and an absent/empty increments dir is
the defined empty case (identical to TSOW-only behavior).
"""
import os

import verify_coverage as vc

LEDGER_TMPL = """# coverage

<!-- FRIDAY-DISPOSITIONS:BEGIN -->
{lines}
<!-- FRIDAY-DISPOSITIONS:END -->
"""


def _project(tmp_path, tsow: str, ledger_lines: list[str],
             increments: dict[str, str] | None = None):
    docs = tmp_path / "docs"
    (docs / "reviews").mkdir(parents=True)
    (docs / "TECHNICAL_SOW.md").write_text(tsow, encoding="utf-8")
    (docs / "reviews" / "coverage.md").write_text(
        LEDGER_TMPL.format(lines="\n".join(ledger_lines)), encoding="utf-8")
    for name, text in (increments or {}).items():
        inc = docs / "increments"
        inc.mkdir(exist_ok=True)
        (inc / name).write_text(text, encoding="utf-8")
    return str(tmp_path)


TSOW = """# TSOW
## 4. Numbered User Stories
- **FR-1** the thing works
- **AC-1** proven on a real device

## Increments
- INC-001 — scrollback fetch → docs/increments/INC-001.md (approved 2026-07-13)
"""

INC_001 = """# INC-001 — scrollback fetch
- **FR-1.1** fetch scrollback on demand
- **AC-1.1** verified against a live session
"""


# --- baseline (pins existing behavior) ---------------------------------------

def test_tsow_ids_all_dispositioned_is_closed(tmp_path):
    root = _project(tmp_path, TSOW.split("## Increments")[0], [
        "disposition: FR-1 implemented — src/thing.py",
        "disposition: AC-1 implemented — run log quoted",
    ])
    res = vc.check(root)
    assert res["ok"] and res["ids"] == ["FR-1", "AC-1"]


def test_missing_disposition_is_a_gap(tmp_path):
    root = _project(tmp_path, TSOW.split("## Increments")[0],
                    ["disposition: FR-1 implemented — src/thing.py"])
    res = vc.check(root)
    assert not res["ok"]
    assert any(g["id"] == "AC-1" for g in res["gaps"])


def test_prose_mention_mints_nothing(tmp_path):
    root = _project(tmp_path, "# TSOW\nA sentence discussing FR-9 casually.\n", [])
    res = vc.check(root)
    assert res["ok"] and res["ids"] == []


# --- DF-023: increments are separate oracles in the closure set --------------

def test_increment_ids_join_the_closure_set(tmp_path):
    """An approved increment's IDs are requirements; a ledger that only covers
    the TSOW body must FAIL closure."""
    root = _project(tmp_path, TSOW, [
        "disposition: FR-1 implemented — src/thing.py",
        "disposition: AC-1 implemented — run log quoted",
    ], increments={"INC-001.md": INC_001})
    res = vc.check(root)
    assert not res["ok"]
    gap_ids = {g["id"] for g in res["gaps"]}
    assert {"FR-1.1", "AC-1.1"} <= gap_ids


def test_increment_ids_dispositioned_closes(tmp_path):
    root = _project(tmp_path, TSOW, [
        "disposition: FR-1 implemented — src/thing.py",
        "disposition: AC-1 implemented — run log quoted",
        "disposition: FR-1.1 implemented — src/scrollback.py",
        "disposition: AC-1.1 implemented — live-session log quoted",
    ], increments={"INC-001.md": INC_001})
    res = vc.check(root)
    assert res["ok"]
    assert "FR-1.1" in res["ids"] and "AC-1.1" in res["ids"]


def test_dotted_id_extracted_whole_never_truncated(tmp_path):
    """`**FR-1.1**` must mint FR-1.1 — not a bare FR-1 colliding with the body."""
    root = _project(tmp_path, "# TSOW\n- **FR-2** body req\n", [
        "disposition: FR-2 implemented — x",
        "disposition: FR-1.1 implemented — y",
    ], increments={"INC-001.md": "- **FR-1.1** inc req\n"})
    res = vc.check(root)
    assert res["ok"]
    assert "FR-1.1" in res["ids"] and "FR-1" not in res["ids"]


def test_absent_increments_dir_is_the_empty_case(tmp_path):
    """No docs/increments/ → behavior identical to TSOW-only (defined empty case)."""
    root = _project(tmp_path, TSOW.split("## Increments")[0], [
        "disposition: FR-1 implemented — src/thing.py",
        "disposition: AC-1 implemented — run log quoted",
    ])
    assert not os.path.isdir(os.path.join(root, "docs", "increments"))
    assert vc.check(root)["ok"]


# --- the second oracle (Open Question 1, resolved in U1): --tsow / --ledger ------

REBUILD_TSOW = """# TSOW — rebuild
- **FR-1** the rebuilt thing works
- **AC-1** proven under the rebuild's own gate
"""

REBUILD_LEDGER = "docs/reviews/coverage-rebuild.md"


def _with_rebuild_oracle(tmp_path, ledger_lines: list[str], **project_kw):
    root = _project(tmp_path, TSOW, [
        "disposition: FR-1 implemented — src/thing.py",
        "disposition: AC-1 implemented — run log quoted",
    ], **project_kw)
    (tmp_path / "docs" / "TECHNICAL_SOW_REBUILD.md").write_text(
        REBUILD_TSOW, encoding="utf-8")
    (tmp_path / "docs" / "reviews" / "coverage-rebuild.md").write_text(
        LEDGER_TMPL.format(lines="\n".join(ledger_lines)), encoding="utf-8")
    return root


def test_second_oracle_closes_with_its_own_ledger(tmp_path):
    """The rebuild TSOW closes as a SECOND oracle against its own disposition
    file — the two ID spaces are never joined (both mint an FR-1 here, on
    purpose: same spelling, different oracles, separate closures)."""
    root = _with_rebuild_oracle(tmp_path, [
        "disposition: FR-1 implemented — hooks/_guard.py",
        "disposition: AC-1 implemented — pytest output quoted",
    ])
    res = vc.check(root, tsow_path="docs/TECHNICAL_SOW_REBUILD.md",
                   ledger_path=REBUILD_LEDGER)
    assert res["ok"], res
    assert res["ids"] == ["FR-1", "AC-1"]


def test_second_oracle_gap_is_its_own_gap(tmp_path):
    """A disposition in the MAIN ledger never closes a rebuild-oracle ID."""
    root = _with_rebuild_oracle(tmp_path, [
        "disposition: FR-1 implemented — hooks/_guard.py",
    ])
    res = vc.check(root, tsow_path="docs/TECHNICAL_SOW_REBUILD.md",
                   ledger_path=REBUILD_LEDGER)
    assert not res["ok"]
    assert any(g["id"] == "AC-1" for g in res["gaps"]), res["gaps"]


def test_second_oracle_never_folds_in_increments(tmp_path):
    """Increments are minted against the main TSOW (skills/feature/SKILL.md); a
    non-default oracle closes over exactly its own file."""
    root = _with_rebuild_oracle(tmp_path, [
        "disposition: FR-1 implemented — hooks/_guard.py",
        "disposition: AC-1 implemented — pytest output quoted",
    ], increments={"INC-001.md": INC_001})
    res = vc.check(root, tsow_path="docs/TECHNICAL_SOW_REBUILD.md",
                   ledger_path=REBUILD_LEDGER)
    assert res["ok"], res
    assert "FR-1.1" not in res["ids"]


def test_second_oracle_missing_file_reported_by_its_own_name(tmp_path):
    root = _project(tmp_path, TSOW.split("## Increments")[0], [
        "disposition: FR-1 implemented — x",
        "disposition: AC-1 implemented — y",
    ])
    res = vc.check(root, tsow_path="docs/NOPE.md", ledger_path=REBUILD_LEDGER)
    assert not res["ok"]
    assert "docs/NOPE.md" in res["summary"]


def test_cli_tsow_and_ledger_flags(tmp_path, capsys):
    root = _with_rebuild_oracle(tmp_path, [
        "disposition: FR-1 implemented — hooks/_guard.py",
        "disposition: AC-1 implemented — pytest output quoted",
    ])
    rc = vc.main(["--root", root, "--tsow", "docs/TECHNICAL_SOW_REBUILD.md",
                  "--ledger", REBUILD_LEDGER])
    capsys.readouterr()
    assert rc == 0
