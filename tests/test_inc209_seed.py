"""INC-209 FR-209.4 / FR-209.7 / AC-209.1 / AC-209.2 / AC-209.3 / KH-1 / KH-2 — the
consented retrofit and the report-only check.

THIS IS THE MAKE-OR-BREAK ROUND. Every seed friday writes today goes into a file
that is absent; never-clobber's whole safety story is that an existing file is
skipped whole. This increment is the first time friday reaches INSIDE a file it has
declared the project's property — and the files it reaches into are the ones friday
itself created and the PM has since made their own. A merge that rewrites, reorders
or reformats anything beyond the inserted setting destroys a deliberate
configuration in a file the PM rarely opens, so the damage would be found late or
never (KH-1).

So the proof here is at the level of FILE CONTENT, not of parsed values: the
fixture carries its own env entries, its own explanatory comment, and its own value
for one of the two settings, and the assertion is that everything except the single
inserted line comes back byte-identical. `test_a_reformatting_merge_is_caught`
plants the failure this pin exists to catch, so a passing suite means the guard
works rather than that the case never arose.

The check's half (KH-2): a project carrying only one of the two settings is
documented to get no early tidy-up at all, and is the one state that reads as
healthy at a glance. It gets its own name in the report and its own fixture here.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import compaction_seed as seed  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOL = os.path.join(_ROOT, "tools", "compaction_seed.py")

# A settings file shaped like one a real project has lived in: friday's original
# seed, plus the PM's own additions, plus the PM's OWN value for one of the two
# settings — the case that must survive untouched.
_LIVED_IN = """{
  "$comment": "The PM's own note about this project. Do not lose me.",
  "env": {
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "25",
    "PROJECT_THING": "value the PM set"
  },
  "permissions": {
    "allow": ["Bash(pytest:*)"]
  }
}
"""


def _write(tmp_path, text, name="settings.json"):
    claude = tmp_path / ".claude"
    claude.mkdir(exist_ok=True)
    p = claude / name
    p.write_text(text, encoding="utf-8")
    return p


def _doctrine():
    """The two settings and their values, read from the doctrine that owns them."""
    return seed.doctrine_values()


# --------------------------------------------------------------------------
# The doctrine is the single home of the values (FR-209.1)
# --------------------------------------------------------------------------

def test_the_values_come_from_the_doctrine_not_from_this_tool():
    """FR-209.1 — the tool must not carry its own copy of the numbers.

    If the tool hard-coded them, editing the contract would leave the tool writing
    the old values and the doctrine would be decorative. Read as source text so a
    constant assigned in the module is caught too.
    """
    values = _doctrine()
    assert set(values) == {"CLAUDE_CODE_AUTO_COMPACT_WINDOW", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"}
    assert all(v and v.strip() for v in values.values())
    with open(_TOOL, encoding="utf-8") as fh:
        source = fh.read()
    for value in values.values():
        assert f'"{value}"' not in source, (
            f"the tool carries a literal copy of {value} — the doctrine is supposed to "
            "be the single home of the values (FR-209.1)"
        )


# --------------------------------------------------------------------------
# AC-209.2 — without an explicit yes, nothing moves
# --------------------------------------------------------------------------

def test_without_consent_the_file_is_byte_identical(tmp_path):
    """AC-209.2 — proven by comparing content, not by reading the instructions."""
    path = _write(tmp_path, _LIVED_IN)
    before = path.read_bytes()
    result = seed.apply(str(tmp_path), consented=False)
    assert result["applied"] is False
    assert result["reason"] == "no-consent"
    assert path.read_bytes() == before


def test_the_cli_refuses_to_apply_without_the_consent_flag(tmp_path):
    """The same refusal at the surface a lane actually calls."""
    path = _write(tmp_path, _LIVED_IN)
    before = path.read_bytes()
    proc = subprocess.run(
        [sys.executable, _TOOL, "--apply", "--root", str(tmp_path), "--json"],
        capture_output=True, text=True,
    )
    assert json.loads(proc.stdout)["applied"] is False
    assert path.read_bytes() == before


# --------------------------------------------------------------------------
# AC-209.1 — the consented insertion, byte for byte
# --------------------------------------------------------------------------

def test_consented_insert_adds_only_the_missing_setting(tmp_path):
    """AC-209.1 / KH-1 — the make-or-break case.

    The fixture already sets its OWN value for the percentage. After the retrofit
    that value must still be the PM's, the window setting must have appeared, and
    every other byte of the file must be exactly where it was.
    """
    path = _write(tmp_path, _LIVED_IN)
    before = path.read_text(encoding="utf-8")
    values = _doctrine()

    result = seed.apply(str(tmp_path), consented=True)
    assert result["applied"] is True
    assert result["added"] == ["CLAUDE_CODE_AUTO_COMPACT_WINDOW"]

    after = path.read_text(encoding="utf-8")
    parsed = json.loads(after)

    # the PM's own value survived — friday never overwrites one that is present
    assert parsed["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] == "25"
    # the missing half arrived, at the doctrine's value
    assert parsed["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == values["CLAUDE_CODE_AUTO_COMPACT_WINDOW"]
    # everything else is untouched
    assert parsed["env"]["PROJECT_THING"] == "value the PM set"
    assert parsed["permissions"]["allow"] == ["Bash(pytest:*)"]
    assert parsed["$comment"] == "The PM's own note about this project. Do not lose me."

    # ...and untouched at the level of bytes, not just of parsed values
    removed = [ln for ln in before.splitlines() if ln not in after.splitlines()]
    assert removed == [], f"the retrofit removed or rewrote existing lines: {removed}"
    added = [ln for ln in after.splitlines() if ln not in before.splitlines()]
    assert len(added) == 1, f"expected exactly one added line, got {added}"
    assert "CLAUDE_CODE_AUTO_COMPACT_WINDOW" in added[0]


def test_an_existing_explanatory_comment_is_never_rewritten(tmp_path):
    """FR-209.3 / OQ-209.3 — the explanation is reported, never forced.

    The file already carries a `$comment` the PM wrote. friday does not get to
    replace it with its own, so the explanation has nowhere to go and the result
    says so instead of quietly overwriting.
    """
    path = _write(tmp_path, _LIVED_IN)
    result = seed.apply(str(tmp_path), consented=True)
    assert result["comment_placed"] is False
    assert "$comment" in " ".join(result["notes"])
    assert json.loads(path.read_text(encoding="utf-8"))["$comment"].startswith("The PM's own note")


def test_the_explanation_is_placed_when_the_file_has_no_comment_of_its_own(tmp_path):
    """FR-209.3 — the ordinary case: nothing to preserve, so the block explains itself."""
    path = _write(tmp_path, '{\n  "env": {\n    "PROJECT_THING": "x"\n  }\n}\n')
    result = seed.apply(str(tmp_path), consented=True)
    assert result["comment_placed"] is True
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert "compaction" in parsed["$comment"].lower()


def test_a_file_with_no_env_block_gains_one(tmp_path):
    """A settings file that predates the env home still gets the guardrail."""
    path = _write(tmp_path, '{\n  "permissions": {\n    "allow": []\n  }\n}\n')
    values = _doctrine()
    result = seed.apply(str(tmp_path), consented=True)
    assert result["applied"] is True
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert parsed["env"] == values
    assert parsed["permissions"] == {"allow": []}


def test_a_project_already_carrying_both_is_left_alone(tmp_path):
    """Nothing to do is not the same as something to write."""
    values = _doctrine()
    path = _write(tmp_path, json.dumps({"env": dict(values)}, indent=2) + "\n")
    before = path.read_bytes()
    result = seed.apply(str(tmp_path), consented=True)
    assert result["applied"] is False
    assert result["reason"] == "already-present"
    assert path.read_bytes() == before


def test_a_malformed_settings_file_is_refused_rather_than_rewritten(tmp_path):
    """Fail fast on unexpected state — never 'repair' a file friday does not own."""
    path = _write(tmp_path, '{ "env": { "A": "b",, } }')
    before = path.read_bytes()
    result = seed.apply(str(tmp_path), consented=True)
    assert result["applied"] is False
    assert result["reason"] == "unparseable"
    assert path.read_bytes() == before


def test_a_reformatting_merge_is_caught(tmp_path, monkeypatch):
    """KH-1's planted failure — the guard proven to fire, not assumed to.

    A rewrite that re-dumps the whole file produces correct PARSED values and
    destroys the file's formatting, its key order and its comment. That is exactly
    the failure mode this increment is most exposed to, so here it is planted: the
    insertion step is swapped for a naive re-dump, and the self-check must refuse
    the write and leave the file alone.
    """
    path = _write(tmp_path, _LIVED_IN)
    before = path.read_bytes()

    def naive_redump(text, additions, indent_hint):
        data = json.loads(text)
        data.setdefault("env", {}).update(additions)
        return json.dumps(data, indent=4)  # different indent, comment order lost

    monkeypatch.setattr(seed, "_insert_keys", naive_redump)
    result = seed.apply(str(tmp_path), consented=True)
    assert result["applied"] is False
    assert result["reason"] == "unsafe-rewrite"
    assert path.read_bytes() == before


def test_the_personal_settings_file_is_never_written(tmp_path):
    """S-209.2 — the standing prohibition, on the retrofit path too."""
    _write(tmp_path, _LIVED_IN)
    seed.apply(str(tmp_path), consented=True)
    assert not (tmp_path / ".claude" / "settings.local.json").exists()


# --------------------------------------------------------------------------
# AC-209.3 — the report-only check, in all three states
# --------------------------------------------------------------------------

def test_check_reports_both_present(tmp_path):
    values = _doctrine()
    _write(tmp_path, json.dumps({"env": dict(values)}, indent=2))
    report = seed.check(str(tmp_path))
    assert report["state"] == "both"
    assert report["blocking"] is False


def test_check_names_the_half_configured_state_distinctly(tmp_path):
    """KH-2 — the one state that looks configured and is documented to do nothing."""
    _write(tmp_path, json.dumps({"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "40"}}, indent=2))
    report = seed.check(str(tmp_path))
    assert report["state"] == "half-configured", (
        "the half-configured state must have its own name — folding it into 'missing' "
        "or 'present' is what makes it invisible (KH-2)"
    )
    assert report["present"] == ["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"]
    assert report["missing"] == ["CLAUDE_CODE_AUTO_COMPACT_WINDOW"]


def test_check_reports_neither_present(tmp_path):
    _write(tmp_path, json.dumps({"env": {"OTHER": "x"}}, indent=2))
    assert seed.check(str(tmp_path))["state"] == "neither"


def test_check_on_a_project_with_no_settings_file_reports_and_allows(tmp_path):
    """S-209.1 — the empty case reports; it never blocks and never crashes."""
    report = seed.check(str(tmp_path))
    assert report["state"] == "no-settings-file"
    assert report["blocking"] is False


def test_check_reports_nothing_about_any_other_content(tmp_path):
    """S-209.3 — two named keys, and nothing else leaves the file.

    A project's settings carry that project's own env names and command
    allowances. None of it may appear in a report, a record, or the journal.
    """
    _write(tmp_path, json.dumps({
        "env": {"SECRET_LOOKING_NAME": "x", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "40"},
        "permissions": {"allow": ["Bash(rm:*)"]},
    }, indent=2))
    blob = json.dumps(seed.check(str(tmp_path)))
    assert "SECRET_LOOKING_NAME" not in blob
    assert "rm" not in blob


def test_the_check_exits_zero_in_every_state(tmp_path):
    """S-209.1 — it reports; it never gates. Proven at the exit status."""
    values = _doctrine()
    cases = [
        json.dumps({"env": dict(values)}),
        json.dumps({"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "40"}}),
        json.dumps({"env": {}}),
    ]
    for i, text in enumerate(cases):
        root = tmp_path / f"p{i}"
        root.mkdir()
        _write(root, text)
        proc = subprocess.run(
            [sys.executable, _TOOL, "--check", "--root", str(root), "--json"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"case {i} blocked with {proc.returncode}"
    # and the case with no settings file at all
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = subprocess.run(
        [sys.executable, _TOOL, "--check", "--root", str(empty), "--json"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
