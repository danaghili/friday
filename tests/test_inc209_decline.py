"""INC-209 FR-209.6 / AC-209.4 / OQ-209.4 — a decline is recorded, and read.

The failure this closes: three separate retrofit doors would each offer the seed,
and nothing anywhere would remember that the PM had already said no. An offer that
keeps coming back after a decline is what teaches a PM to click past friday's
questions without reading them — the same nagging the every-reconcile check was
rejected for (D4, D7).

The precedent applied rather than invented: friday's optional code-graph offer at
setup already records the PM's answer either way, so downstream work reads a
settled answer instead of re-asking.

OQ-209.4 asked where a decline lands on a project that has no decision record yet —
adopt can meet a project mid-reconstruction. The answer needed no new machinery: the
existing decisions writer creates the record when it is absent, which
`test_a_decline_is_durable_on_a_project_with_no_record_yet` proves against a bare
directory rather than assuming.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import compaction_seed as seed  # noqa: E402

_REASON = "this project runs short sessions; the guardrail would never fire"


def _settings(tmp_path, payload):
    claude = tmp_path / ".claude"
    claude.mkdir(exist_ok=True)
    (claude / "settings.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_a_decline_is_durable_on_a_project_with_no_record_yet(tmp_path):
    """OQ-209.4 — a bare directory, the state adopt can genuinely meet."""
    assert seed.decline_recorded(str(tmp_path)) is False
    result = seed.record_decline(str(tmp_path), _REASON)
    assert result["ok"] is True
    assert os.path.isfile(os.path.join(str(tmp_path), "docs", "DECISIONS.md"))
    assert seed.decline_recorded(str(tmp_path)) is True


def test_the_decline_carries_the_pm_reason_as_given(tmp_path):
    """FR-209.6 — the reason is the PM's, recorded verbatim, not paraphrased.

    Months later the record has to answer 'why does this project not carry it',
    which a summary of the reason cannot do.
    """
    seed.record_decline(str(tmp_path), _REASON)
    with open(os.path.join(str(tmp_path), "docs", "DECISIONS.md"), encoding="utf-8") as fh:
        text = fh.read()
    assert _REASON in text


def test_a_recorded_decline_silences_a_later_door(tmp_path):
    """AC-209.4, direction one — the door offers nothing and changes nothing."""
    _settings(tmp_path, {"env": {}})
    before = (tmp_path / ".claude" / "settings.json").read_bytes()

    seed.record_decline(str(tmp_path), _REASON)
    offer, why = seed.should_offer(str(tmp_path))

    assert offer is False
    assert why == "declined"
    assert (tmp_path / ".claude" / "settings.json").read_bytes() == before


def test_without_the_record_the_same_door_offers(tmp_path):
    """AC-209.4, direction two — proving the silence came from the record."""
    _settings(tmp_path, {"env": {}})
    offer, why = seed.should_offer(str(tmp_path))
    assert offer is True
    assert why == "neither"


def test_a_door_offers_nothing_when_the_pair_is_already_there(tmp_path):
    """Nothing to offer is its own answer, distinct from a decline."""
    _settings(tmp_path, {"env": dict(seed.doctrine_values())})
    offer, why = seed.should_offer(str(tmp_path))
    assert offer is False
    assert why == "both"


def test_a_door_offers_on_the_half_configured_project(tmp_path):
    """KH-2 — the state that looks fine is exactly the one worth offering on."""
    _settings(tmp_path, {"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "40"}})
    offer, why = seed.should_offer(str(tmp_path))
    assert offer is True
    assert why == "half-configured"


def test_recording_a_decline_appends_rather_than_replacing(tmp_path):
    """The project's existing record is not friday's to overwrite."""
    seed.record_decline(str(tmp_path), "first reason")
    seed.record_decline(str(tmp_path), "second reason")
    with open(os.path.join(str(tmp_path), "docs", "DECISIONS.md"), encoding="utf-8") as fh:
        text = fh.read()
    assert "first reason" in text and "second reason" in text


def test_the_decline_marker_is_a_typed_tag_line(tmp_path):
    """House convention — a script-checked claim is a typed tag line, never prose.

    The next door greps for this line. If the marker were a sentence, a reworded
    entry would silently stop being findable and the door would start re-asking.
    """
    seed.record_decline(str(tmp_path), _REASON)
    with open(os.path.join(str(tmp_path), "docs", "DECISIONS.md"), encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh]
    assert seed.DECLINE_TAG in lines, (
        f"{seed.DECLINE_TAG!r} does not appear as its own line — the marker must be a "
        "tag line the next door can grep, not prose it has to interpret"
    )


def test_declining_never_writes_the_settings_file(tmp_path):
    """S-209.2 / never-clobber — a no touches nothing in `.claude/`."""
    _settings(tmp_path, {"env": {}})
    before = (tmp_path / ".claude" / "settings.json").read_bytes()
    seed.record_decline(str(tmp_path), _REASON)
    assert (tmp_path / ".claude" / "settings.json").read_bytes() == before
    assert not (tmp_path / ".claude" / "settings.local.json").exists()
