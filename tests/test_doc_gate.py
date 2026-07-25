"""Document-gate family tests — U1 foundation (TECHNICAL_SOW_REBUILD US-12:
FR-64 "load-bearing fields present, IDs unique, grammar parsed"; FR-67
provenance; FR-65 empty cases; AC-16 seeded-malformed refusals).

Guard #9 is this checker's consumption-time wrapper. Four kinds:

- spec: a `provenance:` claim (born-from-discovery|recovered-from-code) +
  at least one requirement-ID DECLARATION, declared once each. Uniqueness is
  judged over line-start declarations only — a bold mid-prose mention (the
  rebuild oracle's own "**FR-78's** relocation…" amendments line is the live
  example) is a reference, not a second declaration.
- increment: dotted IDs only (FR-n.m — undotted would collide with the
  parent's space), at least one; with --parent, the parent's `## Increments`
  section must point at this file (an orphan increment being consumed is a
  provable failure; an unreadable parent degrades to structural-only).
- findings-brief: delegates to findings_brief_check (one grammar, one home).
- intake-brief: contract docs/contracts/intake-brief.md — formal half
  (goals/scope/exclusions/budget/timeline/approver + the PM-amendment-4
  fields data-sovereignty/hosting-sla/payment-ip-exit/client-tier), informal
  half, glossary (populated or exactly the sentinel empty case).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks"))
import doc_gate  # noqa: E402
import _guard  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, "tools", "doc_gate.py")

GLOSSARY_NONE = "glossary: none — no client-specific terms arose"


# --- spec ------------------------------------------------------------------------

SPEC = """# TSOW — testproj

provenance: born-from-discovery

## Requirements
- **FR-1** The thing works.
- **FR-2** The thing keeps working.
- **AC-1** Both are demonstrated.
"""


def test_spec_valid_passes():
    res = doc_gate.check_spec(SPEC)
    assert res["verdict"] == "valid-pass", res


def test_spec_recovered_provenance_also_passes():
    res = doc_gate.check_spec(SPEC.replace("born-from-discovery", "recovered-from-code"))
    assert res["verdict"] == "valid-pass", res


def test_spec_missing_provenance_fails():
    res = doc_gate.check_spec(SPEC.replace("provenance: born-from-discovery\n", ""))
    assert res["verdict"] == "valid-fail"
    assert any("provenance" in e for e in res["errors"]), res["errors"]


def test_spec_unknown_provenance_fails():
    res = doc_gate.check_spec(SPEC.replace("born-from-discovery", "found-in-a-drawer"))
    assert res["verdict"] == "valid-fail", res


def test_spec_duplicate_declared_id_fails():
    res = doc_gate.check_spec(SPEC + "- **FR-1** Declared again.\n")
    assert res["verdict"] == "valid-fail"
    assert any("FR-1" in e for e in res["errors"]), res["errors"]


def test_spec_bold_prose_mention_is_not_a_second_declaration():
    # The FR-78 regression: the rebuild oracle mentions "**FR-78's**" in its
    # amendments prose; a reference must never read as a re-declaration.
    res = doc_gate.check_spec(SPEC + "\nNote that **FR-1's** consequence is far-reaching.\n")
    assert res["verdict"] == "valid-pass", res


def test_spec_empty_case_zero_requirements_is_refused():
    res = doc_gate.check_spec("# TSOW\n\nprovenance: born-from-discovery\n\nAll vibes.\n")
    assert res["verdict"] == "valid-fail"
    assert any("requirement" in e.lower() for e in res["errors"]), res["errors"]


# --- increment --------------------------------------------------------------------

INC = """# INC-2 — export to CSV

Pointer-linked from the main TSOW.

- **FR-2.1** Rows export in declared column order.
- **AC-2.1** A seeded export round-trips.
"""

PARENT = """# TSOW — testproj

- **FR-1** The thing works.

## Increments
- INC-2 — export to CSV → docs/increments/INC-002.md (approved 2026-07-14)
"""


def test_increment_valid_structural_only():
    res = doc_gate.check_increment(INC, basename="INC-002.md")
    assert res["verdict"] == "valid-pass", res


def test_increment_undotted_id_fails():
    res = doc_gate.check_increment(INC + "- **FR-3** An undotted intruder.\n",
                                   basename="INC-002.md")
    assert res["verdict"] == "valid-fail"
    assert any("dotted" in e.lower() for e in res["errors"]), res["errors"]


def test_increment_empty_case_zero_ids_is_refused():
    res = doc_gate.check_increment("# INC-2 — export\n\nNo ids here.\n", basename="INC-002.md")
    assert res["verdict"] == "valid-fail", res


def test_increment_parent_pointer_found():
    res = doc_gate.check_increment(INC, basename="INC-002.md", parent_text=PARENT)
    assert res["verdict"] == "valid-pass", res


def test_increment_orphan_fails_against_readable_parent():
    res = doc_gate.check_increment(INC, basename="INC-999.md", parent_text=PARENT)
    assert res["verdict"] == "valid-fail"
    assert any("Increments" in e for e in res["errors"]), res["errors"]


def test_increment_parent_without_increments_section_fails():
    res = doc_gate.check_increment(INC, basename="INC-002.md",
                                   parent_text="# TSOW\n- **FR-1** x\n")
    assert res["verdict"] == "valid-fail", res


def test_increment_unreadable_parent_degrades_to_structural():
    res = doc_gate.check_increment(INC, basename="INC-002.md", parent_error="no such file")
    assert res["verdict"] == "valid-pass"
    assert "not cross-checked" in res["summary"], res


# --- findings-brief (delegation) ---------------------------------------------------

BRIEF = """findings-brief: source=harden count=1

## F-1 — Loose bolt (severity: track)
evidence: hooks/x.py:3
explained: the bolt is loose
fixed-when: the bolt is tight
"""


def test_findings_brief_delegates_valid():
    res = doc_gate.check("findings-brief", BRIEF)
    assert res["verdict"] == "valid-pass", res


def test_findings_brief_delegates_malformed():
    res = doc_gate.check("findings-brief", BRIEF.replace("count=1", "count=7"))
    assert res["verdict"] == "valid-fail", res


def test_findings_brief_empty_case_through_the_gate():
    res = doc_gate.check("findings-brief",
                         "findings-brief: source=adopt count=0\n\n## Checked\n- everything\n")
    assert res["verdict"] == "valid-pass", res


# --- intake-brief -------------------------------------------------------------------

def make_intake(*, header="intake-brief: client=Acme Pty date=2026-07-14",
                formal=None, informal="rapport: prefers calls before 10am\n",
                glossary="- runsheet — the daily job list the crew works from",
                brownfield=None) -> str:
    formal_fields = {
        "goals": "one place to see the day's jobs",
        "scope": "scheduling + the crew view",
        "exclusions": "payroll stays in Xero",
        "budget": "$8k fixed",
        "timeline": "pilot by September",
        "approver": "Sam (owner)",
        "data-sovereignty": "job data stays in AU region; no PII beyond names",
        "hosting-sla": "client's own Hetzner box; we own uptime during pilot only",
        "payment-ip-exit": "50/50 split; code is theirs on final payment",
        "client-tier": "solo-operator tier — no SSO, no audit trail",
    }
    if formal is not None:
        formal_fields.update(formal)
    formal_text = "\n".join(f"{k}: {v}" for k, v in formal_fields.items() if v)
    text = (f"{header}\n\n## Formal — for sign-off\n{formal_text}\n\n"
            f"## Informal — workroom notes\n{informal}\n\n## Glossary\n{glossary}\n")
    if brownfield is not None:
        bf = {"assessment": "WP 5.2 site, dead UA analytics, keep the 40 blog posts",
              "direction": "rebuild on Astro — the PHP stack is EOL",
              "keys": "domain on owner's GoDaddy; host held by prior dev (transfer risk)"}
        if isinstance(brownfield, dict):
            bf.update(brownfield)
        bf_text = "\n".join(f"{k}: {v}" for k, v in bf.items() if v)
        text += f"\n## Brownfield — current state & direction\n{bf_text}\n"
    return text


def test_intake_valid_passes():
    res = doc_gate.check_intake(make_intake())
    assert res["verdict"] == "valid-pass", res


def test_intake_glossary_empty_case_sentinel_passes():
    res = doc_gate.check_intake(make_intake(glossary=GLOSSARY_NONE))
    assert res["verdict"] == "valid-pass", res


def test_intake_missing_approver_fails():
    res = doc_gate.check_intake(make_intake(formal={"approver": ""}))
    assert res["verdict"] == "valid-fail"
    assert any("approver" in e for e in res["errors"]), res["errors"]


def test_intake_missing_amendment_field_fails():
    # PM amendment 4: the consumer-expected fields are load-bearing.
    for field in ("data-sovereignty", "hosting-sla", "payment-ip-exit", "client-tier"):
        res = doc_gate.check_intake(make_intake(formal={field: ""}))
        assert res["verdict"] == "valid-fail", (field, res)


def test_intake_missing_informal_half_fails():
    text = make_intake().replace("## Informal — workroom notes", "## Sidebar")
    res = doc_gate.check_intake(text)
    assert res["verdict"] == "valid-fail", res


def test_intake_empty_glossary_without_sentinel_fails():
    res = doc_gate.check_intake(make_intake(glossary=""))
    assert res["verdict"] == "valid-fail"
    assert any("glossary" in e.lower() for e in res["errors"]), res["errors"]


def test_intake_bad_header_fails():
    res = doc_gate.check_intake(make_intake(header="intake-brief: client=Acme Pty date=whenever"))
    assert res["verdict"] == "valid-fail", res


def test_intake_brownfield_block_valid_passes():
    # D-0042: an existing-site brief carries the optional Brownfield block.
    res = doc_gate.check_intake(make_intake(brownfield={}))
    assert res["verdict"] == "valid-pass", res


def test_intake_brownfield_present_but_field_empty_fails():
    # Present → its three fields are load-bearing.
    for field in ("assessment", "direction", "keys"):
        res = doc_gate.check_intake(make_intake(brownfield={field: ""}))
        assert res["verdict"] == "valid-fail", (field, res)
        assert any(field in e for e in res["errors"]), (field, res["errors"])


def test_intake_greenfield_omits_brownfield_block_and_passes():
    # First-class optional: a greenfield brief has no Brownfield block and still passes.
    text = make_intake()
    assert "## Brownfield" not in text
    assert doc_gate.check_intake(text)["verdict"] == "valid-pass"


# --- CLI + skeleton integration -----------------------------------------------------

def test_cli_spec_pass(tmp_path):
    p = tmp_path / "spec.md"
    p.write_text(SPEC, encoding="utf-8")
    proc = subprocess.run([sys.executable, CHECKER, "--kind", "spec", "--file", str(p)],
                          capture_output=True, text=True)
    out = json.loads(proc.stdout)
    assert out["verdict"] == "valid-pass"
    assert proc.returncode == 0


def test_cli_increment_with_parent(tmp_path):
    inc = tmp_path / "INC-002.md"
    inc.write_text(INC, encoding="utf-8")
    parent = tmp_path / "TSOW.md"
    parent.write_text(PARENT, encoding="utf-8")
    proc = subprocess.run([sys.executable, CHECKER, "--kind", "increment",
                           "--file", str(inc), "--parent", str(parent)],
                          capture_output=True, text=True)
    assert json.loads(proc.stdout)["verdict"] == "valid-pass"


def test_cli_missing_file_is_valid_fail(tmp_path):
    proc = subprocess.run([sys.executable, CHECKER, "--kind", "spec",
                           "--file", str(tmp_path / "no.md")],
                          capture_output=True, text=True)
    out = json.loads(proc.stdout)
    assert out["verdict"] == "valid-fail"
    assert proc.returncode == 1


def test_cli_unknown_kind_exits_2_with_no_verdict():
    proc = subprocess.run([sys.executable, CHECKER, "--kind", "memo", "--file", "x.md"],
                          capture_output=True, text=True)
    assert proc.returncode == 2
    assert not proc.stdout.strip()


# --- S-4: research consumer-citation check (AC-12) --------------------------------

BRIEF_NAMING = """consumer: the main spec (spec.md) — stack risk row
lane-model: sonnet

## Findings
Things were found.
"""

BRIEF_PROSE = """consumer: rebuild build pass
lane-model: sonnet

## Findings
Prose-named consumer — never blockable, guard #14's warn territory.
"""


def _research(tmp_path, name, text):
    d = tmp_path / "research"
    d.mkdir(exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")
    return str(d)


def test_s4_uncited_brief_naming_this_doc_blocks(tmp_path):
    rd = _research(tmp_path, "stack-risk.md", BRIEF_NAMING)
    res = doc_gate.check("spec", SPEC, basename="spec.md", research_dir=rd)
    assert res["verdict"] == "valid-fail"
    assert any("stack-risk.md" in e for e in res["errors"]), res["errors"]


def test_s4_cited_brief_passes(tmp_path):
    rd = _research(tmp_path, "stack-risk.md", BRIEF_NAMING)
    spec = SPEC + "\n## Sources\n- stack-risk.md — consumed for FR-2.\n"
    res = doc_gate.check("spec", spec, basename="spec.md", research_dir=rd)
    assert res["verdict"] == "valid-pass", res


def test_s4_dispositioned_brief_passes(tmp_path):
    rd = _research(tmp_path, "stack-risk.md", BRIEF_NAMING)
    spec = SPEC + "\n## Sources\n- stack-risk.md superseded — probe answered the row directly.\n"
    res = doc_gate.check("spec", spec, basename="spec.md", research_dir=rd)
    assert res["verdict"] == "valid-pass", res


def test_s4_prose_consumer_never_blocks(tmp_path):
    # A brief whose consumer: line does not NAME this file is not a provable
    # lie against it — that ambiguity belongs to guard #14's warn sweep.
    rd = _research(tmp_path, "vague.md", BRIEF_PROSE)
    res = doc_gate.check("spec", SPEC, basename="spec.md", research_dir=rd)
    assert res["verdict"] == "valid-pass", res


def test_s4_empty_or_absent_research_dir_is_the_empty_case(tmp_path):
    res = doc_gate.check("spec", SPEC, basename="spec.md",
                         research_dir=str(tmp_path / "nope"))
    assert res["verdict"] == "valid-pass", res
    assert doc_gate.check("spec", SPEC, basename="spec.md",
                          research_dir=None)["verdict"] == "valid-pass"


def test_s4_match_is_token_anchored_never_substring(tmp_path):
    # U2 interim gate F-1/F-2: `my-sow.md`'s brief must not bind a doc named
    # `sow.md` (and TECHNICAL_SOW.md's brief must not block SOW.md) — a
    # substring is not a naming (constitutional principle 3: false blocks).
    rd = _research(tmp_path, "brief.md",
                   "consumer: the main plan (TECHNICAL_SOW.md)\n\nfindings\n")
    res = doc_gate.check("spec", SPEC, basename="SOW.md", research_dir=rd)
    assert res["verdict"] == "valid-pass", res


def test_s4_citation_dodge_by_superstring_fails(tmp_path):
    # `release-notes.md` in the doc must NOT satisfy a brief named notes.md.
    rd = _research(tmp_path, "notes.md",
                   "consumer: the main spec (spec.md)\n\nfindings\n")
    spec = SPEC + "\n## Sources\n- release-notes.md — unrelated.\n"
    res = doc_gate.check("spec", spec, basename="spec.md", research_dir=rd)
    assert res["verdict"] == "valid-fail", res


def test_s4_case_variants_bind_and_satisfy(tmp_path):
    # Case tricks neither dodge the binding nor invalidate a real citation.
    rd = _research(tmp_path, "stack-risk.md",
                   "consumer: the main spec (SPEC.MD)\n\nfindings\n")
    res = doc_gate.check("spec", SPEC, basename="spec.md", research_dir=rd)
    assert res["verdict"] == "valid-fail", res  # binds despite case
    cited = SPEC + "\n## Sources\n- STACK-RISK.MD — consumed.\n"
    res = doc_gate.check("spec", cited, basename="spec.md", research_dir=rd)
    assert res["verdict"] == "valid-pass", res  # cites despite case


def test_s4_non_utf8_brief_never_disables_the_gate(tmp_path):
    # U2 interim gate F-5: a binary .md under research must not crash
    # check() — a crash would fail the WHOLE consumption gate open.
    rd = _research(tmp_path, "stack-risk.md", BRIEF_NAMING)
    (tmp_path / "research" / "junk.md").write_bytes(b"\xff\xfe\x00binary")
    res = doc_gate.check("spec", SPEC, basename="spec.md", research_dir=rd)
    assert res["verdict"] == "valid-fail"          # the real brief still binds
    assert any("stack-risk.md" in e for e in res["errors"])


def test_s4_applies_to_every_kind(tmp_path):
    rd = _research(tmp_path, "intake-notes.md",
                   "consumer: the intake record (intake-brief.md)\n\nnotes\n")
    res = doc_gate.check("intake-brief", make_intake(), basename="intake-brief.md",
                         research_dir=rd)
    assert res["verdict"] == "valid-fail", res


def test_skeleton_consumes_the_gate(tmp_path):
    p = tmp_path / "spec.md"
    p.write_text("# TSOW\n\nno provenance, no ids\n", encoding="utf-8")
    v = _guard.run_checker([sys.executable, CHECKER, "--kind", "spec", "--file", str(p)])
    assert v["verdict"] == "valid-fail"
    assert _guard.decide(v, "block", "reason").kind == "block"
