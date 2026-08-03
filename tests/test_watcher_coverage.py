"""INC-103 FR-103.1/FR-103.2 — the coverage comparison, counted from the project.

The make-or-break mechanism: tree-side dependency kinds derived from the real
tree, config-side kinds from the project's own watcher configuration, the
difference reported with evidence paths — no authored coverage figure anywhere
(KH-1), no prose scope statement in any output (S-103.2), nothing blocking
(S-103.1). AC-103.1/AC-103.2's fixture mechanics are exercised here at unit
level; the acceptance runs re-prove them over real trees.
"""
import json
import subprocess
import sys
from pathlib import Path

TOOL = str(Path(__file__).resolve().parent.parent / "tools" / "watcher_coverage.py")


def run(args, cwd=None):
    return subprocess.run(
        [sys.executable, TOOL] + args, capture_output=True, text=True, cwd=cwd
    )


def compare_json(root):
    proc = run(["compare", "--root", str(root), "--json"])
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def write(root, rel, content=""):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def seed_config(root, ecosystems):
    lines = ["version: 2", "updates:"]
    for eco in ecosystems:
        lines += [f'  - package-ecosystem: "{eco}"', '    directory: "/"',
                  "    schedule:", "      interval: weekly"]
    return write(root, ".github/dependabot.yml", "\n".join(lines) + "\n")


# --- the empty case (AC-103.10's shape) ------------------------------------

def test_empty_tree_is_nothing_to_watch(tmp_path):
    report = compare_json(tmp_path)
    assert report["outcome"] == "nothing-to-watch"
    assert report["kinds_present"] == []
    assert report["watcher_config"] is None
    assert report["uncovered"] == []


# --- tree-side derivation (FR-103.1) ----------------------------------------

def test_kinds_detected_with_evidence_paths(tmp_path):
    write(tmp_path, "package-lock.json")
    write(tmp_path, "requirements.txt")
    write(tmp_path, "Dockerfile")
    write(tmp_path, ".github/workflows/ci.yml")
    report = compare_json(tmp_path)
    kinds = {k["kind"]: k["evidence"] for k in report["kinds_present"]}
    assert set(kinds) == {"npm", "pip", "docker", "github-actions"}
    assert "package-lock.json" in kinds["npm"]
    assert "requirements.txt" in kinds["pip"]
    assert "Dockerfile" in kinds["docker"]
    assert ".github/workflows/ci.yml" in kinds["github-actions"]


def test_dockerfile_variants_all_detected(tmp_path):
    # dependabot-core's own filename rule: /dockerfile|containerfile/i
    write(tmp_path, "Containerfile")
    write(tmp_path, "app.dockerfile")
    write(tmp_path, "Dockerfile.prod")
    report = compare_json(tmp_path)
    kinds = {k["kind"]: k["evidence"] for k in report["kinds_present"]}
    assert set(kinds["docker"]) == {"Containerfile", "app.dockerfile", "Dockerfile.prod"}


def test_monorepo_subdirectory_manifests_detected(tmp_path):
    write(tmp_path, "packages/web/package.json", "{}")
    report = compare_json(tmp_path)
    kinds = {k["kind"]: k["evidence"] for k in report["kinds_present"]}
    assert kinds["npm"] == ["packages/web/package.json"]


def test_walk_skips_node_modules_and_git(tmp_path):
    write(tmp_path, "node_modules/dep/package.json", "{}")
    write(tmp_path, ".git/package-lock.json")
    report = compare_json(tmp_path)
    assert report["kinds_present"] == []
    assert report["outcome"] == "nothing-to-watch"


# --- config-side derivation + the comparison (FR-103.2) ---------------------

def test_no_watcher_config_with_kinds_is_loud_never_clean(tmp_path):
    write(tmp_path, "package-lock.json")
    report = compare_json(tmp_path)
    assert report["outcome"] == "no-watcher-config"
    assert [u["kind"] for u in report["uncovered"]] == ["npm"]


def test_partial_watcher_convicted_with_evidence(tmp_path):
    write(tmp_path, "package-lock.json")
    write(tmp_path, "Dockerfile")
    write(tmp_path, ".github/workflows/ci.yml")
    seed_config(tmp_path, ["github-actions"])
    report = compare_json(tmp_path)
    assert report["outcome"] == "gaps"
    uncovered = {u["kind"]: u["evidence"] for u in report["uncovered"]}
    assert set(uncovered) == {"npm", "docker"}
    assert "package-lock.json" in uncovered["npm"]
    assert "Dockerfile" in uncovered["docker"]
    assert report["covered"] == ["github-actions"]


def test_widened_config_reports_covered(tmp_path):
    write(tmp_path, "package-lock.json")
    write(tmp_path, "Dockerfile")
    write(tmp_path, ".github/workflows/ci.yml")
    seed_config(tmp_path, ["github-actions", "npm", "docker"])
    report = compare_json(tmp_path)
    assert report["outcome"] == "all-covered"
    assert report["uncovered"] == []
    assert set(report["covered"]) == {"npm", "docker", "github-actions"}


def test_new_family_reported_with_no_other_change(tmp_path):
    # AC-103.2's mechanism: the run derives, nothing is edited.
    write(tmp_path, "package-lock.json")
    seed_config(tmp_path, ["npm"])
    assert compare_json(tmp_path)["outcome"] == "all-covered"
    write(tmp_path, "Cargo.lock")
    report = compare_json(tmp_path)
    assert report["outcome"] == "gaps"
    assert [u["kind"] for u in report["uncovered"]] == ["cargo"]


def test_removed_family_stops_the_finding(tmp_path):
    write(tmp_path, "package-lock.json")
    cargo = write(tmp_path, "Cargo.lock")
    seed_config(tmp_path, ["npm"])
    assert compare_json(tmp_path)["outcome"] == "gaps"
    cargo.unlink()
    assert compare_json(tmp_path)["outcome"] == "all-covered"


def test_unknown_declared_value_reported_never_matched(tmp_path):
    write(tmp_path, "package-lock.json")
    seed_config(tmp_path, ["npmm"])
    report = compare_json(tmp_path)
    assert report["declared_unknown"] == ["npmm"]
    assert [u["kind"] for u in report["uncovered"]] == ["npm"]
    assert report["outcome"] == "gaps"


def test_declared_kind_with_no_manifest_reported_idle(tmp_path):
    write(tmp_path, "package-lock.json")
    seed_config(tmp_path, ["npm", "cargo"])
    report = compare_json(tmp_path)
    assert report["declared_idle"] == ["cargo"]
    assert report["outcome"] == "all-covered"


def test_dependabot_yaml_spelling_found_too(tmp_path):
    write(tmp_path, "package-lock.json")
    write(tmp_path, ".github/dependabot.yaml",
          'version: 2\nupdates:\n  - package-ecosystem: "npm"\n'
          '    directory: "/"\n    schedule:\n      interval: weekly\n')
    report = compare_json(tmp_path)
    assert report["watcher_config"] == ".github/dependabot.yaml"
    assert report["outcome"] == "all-covered"


# --- the kinds verb (FR-103.7's seed feeds on this) --------------------------

def test_kinds_verb_reports_tree_side_only(tmp_path):
    write(tmp_path, "package-lock.json")
    write(tmp_path, "Dockerfile")
    proc = run(["kinds", "--root", str(tmp_path), "--json"])
    assert proc.returncode == 0
    kinds = json.loads(proc.stdout)["kinds_present"]
    assert {k["kind"] for k in kinds} == {"npm", "docker"}


# --- posture (S-103.1, S-103.2) ----------------------------------------------

def test_findings_exit_zero_nothing_blocks(tmp_path):
    write(tmp_path, "package-lock.json")
    proc = run(["compare", "--root", str(tmp_path), "--json"])
    assert proc.returncode == 0


def test_missing_root_is_invocation_error(tmp_path):
    proc = run(["compare", "--root", str(tmp_path / "absent")])
    assert proc.returncode == 2


def test_text_output_is_typed_lines_not_prose(tmp_path):
    write(tmp_path, "package-lock.json")
    write(tmp_path, "Dockerfile")
    seed_config(tmp_path, ["npm"])
    proc = run(["compare", "--root", str(tmp_path)])
    assert proc.returncode == 0
    lines = proc.stdout.strip().splitlines()
    assert any(l.startswith("uncovered: docker — ") for l in lines)
    assert any(l.startswith("covered: npm") for l in lines)
    assert lines[-1] == "outcome: gaps"


# --- the map's own invariants (locked, vendor-declared) ----------------------

def test_every_map_kind_is_a_legal_dependabot_value():
    sys.path.insert(0, str(Path(TOOL).parent))
    import watcher_coverage as wc
    assert set(wc.KIND_INDICATORS) <= set(wc.DEPENDABOT_ECOSYSTEMS)


def test_every_map_entry_carries_vendor_provenance():
    sys.path.insert(0, str(Path(TOOL).parent))
    import watcher_coverage as wc
    for kind, entry in wc.KIND_INDICATORS.items():
        assert entry.get("src"), f"map entry {kind} carries no vendor provenance"
