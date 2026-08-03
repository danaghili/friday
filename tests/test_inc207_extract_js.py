"""INC-207 FR-207.1/.2/.4/.5/.6 — the deterministic JS/TS pass (tests first).

Fixtures are built per-test in tmp trees; nothing here reads a real project
(KH-3: friday's own tree cannot validate this work, and a real-application
proving run happens at AC-207.1 outside the suite). Every added array's empty
case is exercised (AC-207.7).
"""
import json
import os
import subprocess
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools", "doc-synthesis")
sys.path.insert(0, TOOLS)

import extract_architecture as ea  # noqa: E402
import extract_js  # noqa: E402


def _write(root, rel, text=""):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def _ir(root):
    return ea.extract(str(root))


# --- module identity (FR-207.6, D8) -----------------------------------------

def test_js_module_id_is_real_path_with_extension(tmp_path):
    _write(tmp_path, "src/app/page.tsx", "export default function Home() {}\n")
    ir = _ir(tmp_path)
    ids = [m["id"] for m in ir["modules"]]
    assert "src/app/page.tsx" in ids


def test_same_stem_ts_and_tsx_stay_distinct(tmp_path):
    _write(tmp_path, "lib/index.ts", "export const x = 1\n")
    _write(tmp_path, "lib/index.tsx", "export function Widget() {}\n")
    ir = _ir(tmp_path)
    ids = [m["id"] for m in ir["modules"]]
    assert "lib/index.ts" in ids and "lib/index.tsx" in ids


def test_python_module_identity_unchanged(tmp_path):
    _write(tmp_path, "pkg/mod.py", "x = 1\n")
    _write(tmp_path, "web/app.ts", "export const y = 2\n")
    ir = _ir(tmp_path)
    ids = [m["id"] for m in ir["modules"]]
    assert "pkg.mod" in ids and "web/app.ts" in ids


# --- import resolution (FR-207.2, D2) ---------------------------------------

def test_relative_import_with_extension(tmp_path):
    _write(tmp_path, "src/a.ts", "import { b } from './b.ts'\n")
    _write(tmp_path, "src/b.ts", "export const b = 1\n")
    ir = _ir(tmp_path)
    assert {"from": "src/a.ts", "to": "src/b.ts"} in [
        {"from": e["from"], "to": e["to"]} for e in ir["edges"]]


def test_relative_extensionless_and_index_resolution(tmp_path):
    _write(tmp_path, "src/a.ts", "import { b } from './b'\nimport { c } from './cdir'\n")
    _write(tmp_path, "src/b.tsx", "export const b = 1\n")
    _write(tmp_path, "src/cdir/index.ts", "export const c = 1\n")
    ir = _ir(tmp_path)
    pairs = [(e["from"], e["to"]) for e in ir["edges"]]
    assert ("src/a.ts", "src/b.tsx") in pairs
    assert ("src/a.ts", "src/cdir/index.ts") in pairs


def test_tsconfig_alias_with_comments_and_trailing_commas(tmp_path):
    _write(tmp_path, "tsconfig.json",
           '{\n// comment\n"compilerOptions": {\n'
           '  "baseUrl": ".", /* block */\n'
           '  "paths": { "@/*": ["./src/*"], },\n},\n}\n')
    _write(tmp_path, "src/components/button.tsx", "export function Button() {}\n")
    _write(tmp_path, "src/page.tsx", "import { Button } from '@/components/button'\n")
    ir = _ir(tmp_path)
    pairs = [(e["from"], e["to"]) for e in ir["edges"]]
    assert ("src/page.tsx", "src/components/button.tsx") in pairs
    assert ir["js_unresolved"] == []


def test_unresolved_alias_is_named_refusal_never_guessed(tmp_path):
    _write(tmp_path, "tsconfig.json",
           '{"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["./src/*"]}}}')
    _write(tmp_path, "src/a.ts", "import { gone } from '@/missing/file'\n")
    ir = _ir(tmp_path)
    assert all(e["to"] != "src/missing/file" for e in ir["edges"] if e["from"] == "src/a.ts")
    refusals = [r for r in ir["js_unresolved"] if r["from"] == "src/a.ts"]
    assert len(refusals) == 1
    assert refusals[0]["name"] == "@/missing/file"
    assert refusals[0]["kind"] == "import"
    assert "line" in refusals[0]


def test_external_package_import_is_not_a_refusal(tmp_path):
    _write(tmp_path, "src/a.ts", "import React from 'react'\n")
    ir = _ir(tmp_path)
    assert ir["js_unresolved"] == []
    assert ir["edges"] == []


def test_dynamic_import_marks_deferred(tmp_path):
    _write(tmp_path, "src/a.ts", "const m = await import('./b')\n")
    _write(tmp_path, "src/b.ts", "export const b = 1\n")
    ir = _ir(tmp_path)
    edge = next(e for e in ir["edges"] if e["from"] == "src/a.ts")
    assert edge["deferred"] is True


def test_specifier_inside_string_or_comment_is_ignored(tmp_path):
    _write(tmp_path, "src/a.ts",
           "// import { x } from './ghost'\n"
           "const url = 'https://example.com/from'\n"
           "const s = \"import { y } from './ghost2'\"\n")
    ir = _ir(tmp_path)
    assert ir["edges"] == [] and ir["js_unresolved"] == []


# --- routes (FR-207.4, D4, KH-4) --------------------------------------------

def test_next_app_router_conventions(tmp_path):
    _write(tmp_path, "app/page.tsx", "export default function Home() {}\n")
    _write(tmp_path, "app/(member)/live/page.tsx", "export default function Live() {}\n")
    _write(tmp_path, "app/blog/[slug]/page.tsx", "export default function Post() {}\n")
    _write(tmp_path, "app/docs/[...path]/page.tsx", "export default function Doc() {}\n")
    _write(tmp_path, "app/_private/page.tsx", "export default function Hidden() {}\n")
    ir = _ir(tmp_path)
    pages = {r["path"] for r in ir["routes"] if r["method"] == "PAGE"}
    assert pages == {"/", "/live", "/blog/[slug]", "/docs/[...path]"}


def test_next_app_router_api_methods_from_exports(tmp_path):
    _write(tmp_path, "app/api/items/route.ts",
           "export async function GET() {}\nexport async function POST() {}\n")
    ir = _ir(tmp_path)
    api = {(r["method"], r["path"]) for r in ir["routes"] if r["method"] in ("GET", "POST")}
    assert api == {("GET", "/api/items"), ("POST", "/api/items")}


def test_next_route_named_export_list_with_as(tmp_path):
    """The NextAuth shape — caught by the real-project proving run: the
    handler is exported via a named-export list, not a function declaration."""
    _write(tmp_path, "app/api/auth/[...nextauth]/route.ts",
           "const handler = NextAuth(config)\n"
           "export { handler as GET, handler as POST }\n")
    _write(tmp_path, "app/api/plain/route.ts",
           "function GET() {}\nexport { GET }\n")
    ir = _ir(tmp_path)
    api = {(r["method"], r["path"]) for r in ir["routes"] if r["method"] != "PAGE"}
    assert api == {("GET", "/api/auth/[...nextauth]"),
                   ("POST", "/api/auth/[...nextauth]"),
                   ("GET", "/api/plain")}


def test_next_pages_router(tmp_path):
    _write(tmp_path, "pages/index.tsx", "export default function Home() {}\n")
    _write(tmp_path, "pages/blog/[slug].tsx", "export default function Post() {}\n")
    _write(tmp_path, "pages/_app.tsx", "export default function App() {}\n")
    _write(tmp_path, "pages/api/hello.ts", "export default function handler() {}\n")
    ir = _ir(tmp_path)
    pages = {r["path"] for r in ir["routes"] if r["method"] == "PAGE"}
    assert pages == {"/", "/blog/[slug]"}
    api = {(r["method"], r["path"]) for r in ir["routes"] if r["path"].startswith("/api")}
    assert api == {("ANY", "/api/hello")}


def test_express_same_file_certain_and_cross_file_refused(tmp_path):
    _write(tmp_path, "server/app.js",
           "const express = require('express')\n"
           "const app = express()\n"
           "app.get('/health', (req, res) => res.send('ok'))\n")
    _write(tmp_path, "server/routes/users.js",
           "const express = require('express')\n"
           "const router = express.Router()\n"
           "router.get('/list', handler)\n"
           "module.exports = router\n")
    ir = _ir(tmp_path)
    assert ("GET", "/health") in {(r["method"], r["path"]) for r in ir["routes"]}
    assert all(r["path"] != "/list" for r in ir["routes"])
    refusals = [r for r in ir["js_unresolved"] if r["kind"] == "route-prefix"]
    assert len(refusals) == 1 and refusals[0]["from"] == "server/routes/users.js"


def test_express_same_file_mount_composes(tmp_path):
    _write(tmp_path, "server/app.js",
           "const express = require('express')\n"
           "const app = express()\n"
           "const admin = express.Router()\n"
           "admin.get('/stats', h)\n"
           "app.use('/admin', admin)\n")
    ir = _ir(tmp_path)
    assert ("GET", "/admin/stats") in {(r["method"], r["path"]) for r in ir["routes"]}


# --- components (FR-207.5, D5) ----------------------------------------------

def test_components_exported_capitalised_in_jsx_tsx_only(tmp_path):
    _write(tmp_path, "src/Button.tsx",
           "export function Button() {}\nexport const IconButton = () => {}\n"
           "export default function Wrapper() {}\nexport function helper() {}\n")
    _write(tmp_path, "src/util.ts", "export const NotAComponent = 1\n")
    ir = _ir(tmp_path)
    names = {c["name"] for c in ir["components"]}
    assert names == {"Button", "IconButton", "Wrapper"}
    mods = {c["module"] for c in ir["components"]}
    assert mods == {"src/Button.tsx"}
    assert all("line" in c for c in ir["components"])


def test_file_with_no_capitalised_export_yields_no_component(tmp_path):
    _write(tmp_path, "src/hooks.tsx", "export function useThing() {}\n")
    ir = _ir(tmp_path)
    assert ir["components"] == []


# --- empty cases (FR-207.1, AC-207.7) ---------------------------------------

def test_js_free_tree_produces_todays_output_byte_identical(tmp_path):
    _write(tmp_path, "pkg/mod.py", "x = 1\n")
    ir = _ir(tmp_path)
    assert "components" not in ir and "js_unresolved" not in ir
    assert set(ir.keys()) == {"modules", "edges", "routes", "config_surface",
                              "data_models", "deploy_topology",
                              "ambiguous_imports", "unparseable"}


def test_js_tree_with_nothing_to_report_emits_present_and_empty_arrays(tmp_path):
    _write(tmp_path, "src/plain.ts", "export const x = 1\n")
    ir = _ir(tmp_path)
    assert ir["components"] == [] and ir["js_unresolved"] == []
    assert ir["routes"] == [] and ir["edges"] == []


def test_zero_module_tree_keeps_generated_empty_shape(tmp_path):
    ir = _ir(tmp_path)
    assert ir.get("generated-empty") is True
    assert "components" not in ir


# --- never executes, cli surface stays green (S-207.1 smoke) -----------------

def test_check_mode_runs_clean_over_a_mixed_tree(tmp_path):
    _write(tmp_path, "app/page.tsx", "export default function Home() {}\n")
    _write(tmp_path, "pkg/mod.py", "x = 1\n")
    res = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "extract_architecture.py"),
         "--root", str(tmp_path), "--check"],
        capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
