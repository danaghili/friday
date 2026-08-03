"""Task #25 / D-0109 — adopt reaches greenfield parity, pinned on the surface.

The gap (PM triage 2026-07-28, NF6): security-reviewer, architect, red-team
and operations all read the exposure profile, scale envelope and the
intolerable-event answer "from the record forever" — but only greenfield init
ever asked them, so every adopted project handed those roles blanks. And
adopt's close NARRATED "every guard armed, full battery passing" without one
mechanical check. These are content pins in the test_bug_002 style: read the
real lane surface, assert the beats exist and sit in the right order.
Ratified close design (2026-07-29): a `closed` target produces its close
artifacts FOR REAL (a dated review, a real release-gate run, an evidence-backed
coverage ledger) — declining leaves `substrate-seeded` + a finding, never a
thinner `closed`.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _adopt():
    return _read(os.path.join("skills", "adopt", "SKILL.md"))


# --- the elicitation: the context greenfield gets, asked here once -------------------

def test_adopt_elicits_the_strategist_context_set():
    text = _adopt()
    for needle in ("exposure", "scale", "environments"):
        assert needle in text.lower(), (
            f"adopt never elicits the {needle} answer — the strategist-parity "
            "context the reviewer roles read from the record forever (D-0109)")
    assert "agents/bootstrap/strategist.md" in text, (
        "the question set is single-homed in the strategist's file — adopt "
        "must cite it, not restate it (D-0083 single-homing)")


def test_the_strategist_block_names_adopt_as_its_second_citer():
    # "friday:adopt" specifically — a bare "adopt" false-passes on the
    # "non-adopter invariant" phrasing that lives elsewhere in the file.
    assert "friday:adopt" in _read(os.path.join(
        "agents", "bootstrap", "strategist.md")).lower(), (
        "both sides of a shared block cite each other by name — the strategist "
        "side must say /friday:adopt consumes its §2 question set")


def test_adopt_asks_the_intolerable_event_as_a_recorded_scenario():
    text = _adopt().lower()
    assert "intolerable" in text or "could not tolerate" in text, (
        "the one tolerance question (data loss / leak / downtime / wrong "
        "charge) is required permanent context for security + architect + "
        "operations — adopt must ask it once (D-0109)")
    assert "forever" in text, (
        "the point of asking ONCE is that the answer is read from the record "
        "forever — the surface must say so, or every role re-asks")


def test_the_answers_land_in_the_same_claude_md_fields_as_greenfield():
    text = _adopt()
    idx = text.find("CLAUDE.md")
    assert idx != -1
    for field in ("exposure", "scale", "intolerable"):
        assert field in text[idx:].lower(), (
            f"the {field} answer must be RECORDED in CLAUDE.md in the same "
            "fields greenfield seeds — parity is where the answers live, not "
            "just that they were asked")


# --- the close: pinned state, mechanically verified, artifacts produced for real -----

def test_the_close_verifies_mechanically_never_narratively():
    text = _adopt()
    assert "verify_state.py" in text, (
        "NF6: adopt's close narrated guardrail passage; D-0109 demands the "
        "mechanical check — verify_state.py must be invoked by name")
    assert "--json" in text and "quote" in text.lower(), (
        "the close must QUOTE verify_state's real output, not summarize it — "
        "the same real-output-quoted bar every other gate holds")


def test_the_close_pins_a_target_state_with_the_dirty_bit_fields():
    text = _adopt()
    assert "build-in-progress" in text and "closed" in text, (
        "the target state derives from reality (backfill's mapping): "
        "delivered -> closed, in flight -> build-in-progress")
    assert "last-verified" in text and "record-status" in text, (
        "a closed record without the PROP-028 dirty-bit fields fails K5 — "
        "adopt must carry them (adoption IS the verification moment)")


def test_a_closed_target_produces_its_close_artifacts_for_real():
    text = _adopt()
    assert "friday-reviewer" in text and "friday-tester" in text, (
        "closed demands K2 (review envelope) + K3 (release gate) — a "
        "never-friday project has neither, so adopt spawns the reviewer and "
        "tester to produce them AT adoption, dated honestly (ratified "
        "2026-07-29: produce for real, never invent)")
    assert "coverage" in text.lower(), (
        "K7: every reconstructed-TSOW ID needs a disposition line — the "
        "ledger comes from what the read verifiably confirmed")
    assert "independently-tested" in text, (
        "the ledger is the TESTER's artifact at adopt close (house-style "
        "review finding 2): every line verified cold and channel-tagged — "
        "an untagged line reads as lead-authored, the class reconcile "
        "re-examines")
    assert "substrate-seeded" in text, (
        "the declined-offer shape: a PM who skips the heavier close leaves "
        "the record honestly at substrate-seeded with the gap recorded — "
        "never a thinner closed")


def test_the_new_spawn_sites_carry_the_house_discipline():
    text = _adopt()
    assert "spawn_telemetry.py" in text, (
        "every spawning surface is instrumented (verify_spawn_coverage.py "
        "closes over them) — adopt's new reviewer/tester spawns included")
    # INC-208 D4: the required-pieces checklist (the friday-docs stamp among
    # them) moved to the shared briefing template, so a spawn site now proves
    # the rule by pointing at its home rather than by restating it. The rule
    # itself did not weaken — the assertion follows it to where it lives, and
    # the second half below pins that the home actually carries it.
    assert "dispatch-briefing-template.md" in text, (
        "task #11's rule, INC-208 form: a spawn site cites the briefing "
        "template, which carries the friday-docs stamp among its slots")


def test_the_briefing_template_still_carries_the_docs_stamp_rule():
    """The other half of the move (INC-208 KH-2): thinning a playbook is only
    safe if the piece it dropped is genuinely in the template. This test is
    the one that would fail if a future edit thinned the template instead."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "docs", "dispatch-briefing-template.md"),
              encoding="utf-8") as fh:
        tpl = fh.read()
    assert "friday-docs: available" in tpl
    assert "teammate-contract.md" in tpl        # the plain-Read alternative
    assert "drawer" in tpl                       # the piece both briefings lost


# --- two doors, never a pipeline (J8) -------------------------------------------------

def test_adopt_and_backfill_are_disjoint_front_doors():
    adopt = _adopt().lower()
    assert "backfill" in adopt and "pipeline" in adopt, (
        "J8's correction must live on adopt's surface: adopt (never-friday "
        "code) and backfill (old-friday projects) are disjoint doors, not "
        "stages — finding old-friday artifacts mid-adopt means wrong lane")
    backfill = _read(os.path.join("skills", "backfill", "SKILL.md")).lower()
    assert "adopt" in backfill, (
        "the other side of the door distinction cites back — backfill names "
        "adopt as the never-friday door")
