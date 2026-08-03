#!/usr/bin/env python3
"""The watcher-coverage comparison, counted from the project (INC-103 FR-103.1/.2).

Compares the kinds of dependency a tree ACTUALLY CONTAINS against the kinds
its own update-watcher configuration DECLARES it watches, and names every
uncovered kind with the file proving it exists. The coverage figure is derived
at run time from tree + config — no part of it is authored, and no output
states a coverage scope in prose (KH-1, S-103.2). Report-only: findings never
block anything (S-103.1); the only non-zero exit is caller misuse.

Verbs:
    compare --root <project> [--json]   the comparison (FR-103.2's outcomes)
    kinds   --root <project> [--json]   tree side only (FR-103.7's seed input)

Outcomes (typed tokens, each tested, empty case first-class):
    nothing-to-watch   no dependency kind found, no watcher config — friday's
                       own shape (FR-103.10); distinct from every other result
    no-watcher-config  kinds present, no watcher configuration at all — a
                       distinct loud outcome, never a clean result (FR-103.2)
    gaps               at least one kind present and not declared
    all-covered        every present kind declared (idle declarations still
                       reported)

THE MAP IS TRANSCRIBED VENDOR DECLARATION, NEVER FRIDAY'S AUTHORSHIP
(OQ-103.4, resolved in docs/DECISIONS.md: D-1034): every indicator below is
lifted from a dated vendor source — the pinned scanner's declared extractor
capability (google/osv-scalibr docs/supported_inventory_types.md), the
watcher's own config schema (json.schemastore.org/dependabot-2.0.json
package-ecosystem enum), the watcher vendor's manager→value folding
(github/docs data/reusables/dependabot/supported-package-managers.md), the
watcher vendor's own docker filename rule (dependabot-core
docker/lib/dependabot/docker/file_fetcher.rb), or the named tool's own spec
where the spec fixes a single canonical filename. Each entry cites its source
in `src`; a committed test refuses an entry without one. Refresh is a re-vet:
re-fetch the sources, re-derive, diff — recorded in the decision log like the
pin itself (D9). A config value outside the schema enum is reported as
unknown, never silently matched, so map staleness fails loud, not calm.

Contract: cited from docs/contracts/ops-battery.md's dependency-advisory row
and skills/ surfaces by name. Pure stdlib.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys

# The watcher's legal package-ecosystem vocabulary — the config side's schema
# enum, transcribed 2026-08-03 from json.schemastore.org/dependabot-2.0.json
# (definitions.package-ecosystem-values). A declared value outside this set is
# reported as unknown (map-or-config staleness made loud).
DEPENDABOT_ECOSYSTEMS = frozenset({
    "bazel", "bun", "bundler", "cargo", "composer", "conda", "deno",
    "devcontainers", "docker", "docker-compose", "dotnet-sdk", "elm",
    "github-actions", "gitsubmodule", "gomod", "gradle", "helm", "julia",
    "maven", "mix", "nix", "npm", "nuget", "opentofu", "pip", "pre-commit",
    "pub", "rust-toolchain", "sbt", "swift", "terraform", "uv", "vcpkg",
})

# Indicator sources, abbreviated in entries below:
#   scalibr    google/osv-scalibr docs/supported_inventory_types.md (fetched
#              2026-08-03; the pinned scanner's declared capability, D-1033)
#   dependabot-docs   github/docs reusables/dependabot/supported-package-
#              managers.md (fetched 2026-08-03; manager→YAML-value folding:
#              yarn/pnpm→npm, poetry/pipenv/pip-compile→pip)
#   dependabot-core   dependabot-core docker/lib/dependabot/docker/
#              file_fetcher.rb (fetched 2026-08-03): /dockerfile|containerfile/i
#   spec       the named tool's own specification fixes this single filename
KIND_INDICATORS = {
    "npm": {
        "names": ["package.json", "package-lock.json", "npm-shrinkwrap.json",
                  "yarn.lock", "pnpm-lock.yaml"],
        "src": "scalibr javascript/* rows; dependabot-docs folds yarn,pnpm under npm",
    },
    "bun": {"names": ["bun.lock"], "src": "scalibr javascript/bunlock; dependabot-docs bun row"},
    "deno": {"names": ["deno.json", "deno.lock"], "src": "scalibr javascript/denojson; dependabot-docs deno row"},
    "pip": {
        "names": ["requirements.txt", "pyproject.toml", "poetry.lock",
                  "Pipfile.lock", "pdm.lock", "setup.py"],
        "src": "scalibr python/* rows; dependabot-docs folds poetry,pipenv,pip-compile under pip",
    },
    "uv": {"names": ["uv.lock"], "src": "scalibr python/uvlock; dependabot-docs uv row"},
    "gomod": {"names": ["go.mod"], "src": "scalibr go/gomod"},
    "cargo": {"names": ["Cargo.lock", "Cargo.toml"], "src": "scalibr rust/cargolock, rust/cargotoml"},
    "composer": {"names": ["composer.lock", "composer.json"], "src": "scalibr php/composerlock; composer.json the spec's manifest"},
    "bundler": {"names": ["Gemfile.lock", "gems.locked", "Gemfile"], "src": "scalibr ruby/gemfilelock; Gemfile the spec's manifest"},
    "maven": {"names": ["pom.xml"], "src": "scalibr java/pomxml"},
    "gradle": {
        "names": ["gradle.lockfile", "verification-metadata.xml",
                  "libs.versions.toml", "build.gradle", "build.gradle.kts"],
        "src": "scalibr java/* lock rows; build.gradle(.kts) the spec's build file",
    },
    "mix": {"names": ["mix.lock", "mix.exs"], "src": "scalibr erlang|elixir/mixlock; mix.exs the spec's manifest"},
    "pub": {"names": ["pubspec.lock", "pubspec.yaml"], "src": "scalibr dart/pubspec; pubspec.yaml the spec's manifest"},
    "swift": {"names": ["Package.resolved", "Package.swift"], "src": "scalibr swift/packageresolved; Package.swift the spec's manifest"},
    "nuget": {
        "names": ["packages.lock.json", "packages.config"],
        "globs": ["*.csproj", "*.fsproj", "*.vbproj"],
        "src": "scalibr dotnet/packageslockjson, dotnet/packagesconfig, dotnet/csproj",
    },
    "julia": {"names": ["Project.toml", "Manifest.toml"], "src": "scalibr julia/projecttoml, julia/manifesttoml"},
    "elm": {"names": ["elm.json"], "src": "spec (elm.json is the manager's single manifest); dependabot-docs elm row"},
    "docker": {
        "basename_regex": r"dockerfile|containerfile",
        "src": "dependabot-core docker file_fetcher.rb DOCKER_REGEXP (/dockerfile|containerfile/i)",
    },
    "docker-compose": {
        "names": ["docker-compose.yml", "docker-compose.yaml",
                  "compose.yml", "compose.yaml"],
        "src": "scalibr containers/dockercomposeimage; the compose spec's default file names",
    },
    "github-actions": {
        "under": ".github/workflows",
        "globs": ["*.yml", "*.yaml"],
        "src": "scalibr github/actions (workflow dependencies); the platform fixes the directory",
    },
    "gitsubmodule": {"names": [".gitmodules"], "src": "scalibr misc/gitrepo (repositories and submodules)"},
    "terraform": {"globs": ["*.tf"], "src": "spec (.tf is the language's file extension); dependabot-docs terraform row"},
    "helm": {"names": ["Chart.yaml"], "src": "spec (Chart.yaml is a chart's fixed manifest name)"},
    "devcontainers": {
        "names": ["devcontainer.json", ".devcontainer.json"],
        "src": "spec (the devcontainer spec fixes these names)",
    },
    "dotnet-sdk": {"names": ["global.json"], "src": "spec (global.json is the SDK version file's fixed name)"},
    "pre-commit": {"names": [".pre-commit-config.yaml"], "src": "spec (the tool's fixed config name)"},
    "rust-toolchain": {"names": ["rust-toolchain", "rust-toolchain.toml"], "src": "spec (the toolchain file's fixed names)"},
    "sbt": {"names": ["build.sbt"], "src": "spec (build.sbt is the tool's fixed build file)"},
    "vcpkg": {"names": ["vcpkg.json"], "src": "spec (the manifest's fixed name)"},
    "nix": {"names": ["flake.nix", "flake.lock"], "src": "spec (flake file names are fixed); dependabot-docs nix row"},
    "bazel": {"names": ["MODULE.bazel", "WORKSPACE", "WORKSPACE.bazel"], "src": "spec (bazel's fixed module/workspace names)"},
}

# Walk hygiene only — never a scope statement: dependency trees vendored under
# these names belong to the packages already counted by their own manifests.
SKIP_DIRS = {".git", "node_modules"}

CONFIG_PATHS = (".github/dependabot.yml", ".github/dependabot.yaml")

_ECOSYSTEM_LINE = re.compile(r"""^\s*-?\s*package-ecosystem\s*:\s*["']?([A-Za-z0-9._-]+)""")


def derive_tree_kinds(root):
    """Tree side: every kind the tree contains, with its evidence paths."""
    docker_re = None
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        rel_dir = os.path.relpath(dirpath, root)
        for fname in sorted(filenames):
            rel = fname if rel_dir == "." else os.path.join(rel_dir, fname)
            for kind, entry in KIND_INDICATORS.items():
                under = entry.get("under")
                if under is not None:
                    if rel_dir.replace(os.sep, "/") != under:
                        continue
                    if any(fnmatch.fnmatch(fname, g) for g in entry.get("globs", [])):
                        found.setdefault(kind, []).append(rel)
                    continue
                if fname in entry.get("names", []):
                    found.setdefault(kind, []).append(rel)
                    continue
                if any(fnmatch.fnmatch(fname, g) for g in entry.get("globs", [])):
                    found.setdefault(kind, []).append(rel)
                    continue
                pattern = entry.get("basename_regex")
                if pattern:
                    if docker_re is None:
                        docker_re = re.compile(pattern, re.IGNORECASE)
                    if docker_re.search(fname):
                        found.setdefault(kind, []).append(rel)
    return [{"kind": k, "evidence": found[k]} for k in sorted(found)]


def _declared_values(path):
    """The package-ecosystem values one config file declares: (known, unknown)."""
    declared, unknown = [], []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = _ECOSYSTEM_LINE.match(line)
            if not m:
                continue
            value = m.group(1)
            if value in DEPENDABOT_ECOSYSTEMS:
                if value not in declared:
                    declared.append(value)
            elif value not in unknown:
                unknown.append(value)
    return declared, unknown


def read_watcher_config(root):
    """Config side: the declared kinds, from the project's own configuration.

    A shallow line-grammar read of package-ecosystem values — deliberately not
    a YAML parse (stdlib holds none); the value set is what the comparison
    needs, and an unknown value is reported, never guessed at.
    """
    for rel in CONFIG_PATHS:
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            declared, unknown = _declared_values(path)
            return rel, declared, unknown
    return None, [], []


def compare(root):
    kinds_present = derive_tree_kinds(root)
    config_rel, declared, unknown = read_watcher_config(root)
    present_keys = [k["kind"] for k in kinds_present]
    covered = [k for k in present_keys if k in declared]
    uncovered = [k for k in kinds_present if k["kind"] not in declared]
    declared_idle = [d for d in declared if d not in present_keys]
    if config_rel is None:
        outcome = "no-watcher-config" if kinds_present else "nothing-to-watch"
    else:
        outcome = "gaps" if uncovered else "all-covered"
    return {
        "root": os.path.abspath(root),
        "watcher_config": config_rel,
        "kinds_present": kinds_present,
        "kinds_declared": declared,
        "declared_unknown": unknown,
        "covered": covered,
        "uncovered": uncovered,
        "declared_idle": declared_idle,
        "outcome": outcome,
    }


def print_text(report):
    if report["watcher_config"] is None:
        print("watcher-config: absent")
    else:
        print(f"watcher-config: {report['watcher_config']}")
    for item in report["covered"]:
        print(f"covered: {item}")
    for item in report["uncovered"]:
        print(f"uncovered: {item['kind']} — {', '.join(item['evidence'])}")
    for value in report["declared_unknown"]:
        print(f"declared-unknown: {value} — not a value the watcher's schema knows; config typo or a stale map, re-vet per D-1034")
    for value in report["declared_idle"]:
        print(f"declared-idle: {value} — declared, no matching file found")
    print(f"outcome: {report['outcome']}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Watcher-coverage comparison, counted from the project (INC-103)."
    )
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb in ("compare", "kinds"):
        p = sub.add_parser(verb)
        p.add_argument("--root", required=True)
        p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        parser.exit(2, f"error: --root {args.root} is not a directory\n")

    if args.verb == "kinds":
        report = {"root": os.path.abspath(args.root),
                  "kinds_present": derive_tree_kinds(args.root)}
        if args.json:
            print(json.dumps(report, indent=1))
        else:
            for item in report["kinds_present"]:
                print(f"present: {item['kind']} — {', '.join(item['evidence'])}")
            if not report["kinds_present"]:
                print("present: none")
        return 0

    report = compare(args.root)
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
