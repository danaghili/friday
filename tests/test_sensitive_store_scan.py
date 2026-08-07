"""INC-108 OQ-108.3 / FR-108.13 — the catch-up's store enumeration.

The mechanical half of the deep-clean catch-up: enumerate the stores a
project's own schema artefacts declare, so the stores never asked about
(a column somebody added by hand, a table that arrived outside any door)
can be put to the PM. Exact matching only (the standing non-goal): pgTable-
family calls, CREATE TABLE, prisma models, __tablename__. Everything
storage-shaped the scanner cannot parse is NAMED — a store that could not
be examined is never a store with nothing to declare (S-108.2). The model
reads candidates against the floor; nothing here judges sensitivity, and
nothing here opens a data file (S-108.3 — schema text is shapes, not rows).
"""
import json
import os
import stat
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import sensitive_store_scan as scan_mod  # noqa: E402
import sensitivity_declaration as sd  # noqa: E402


def _scan(root):
    return scan_mod.scan(str(root))


def test_pgtable_family_enumerates(tmp_path):
    (tmp_path / "schema.ts").write_text(
        'export const profiles = pgTable("subscriber_profiles", {\n'
        '  id: uuid("id"),\n});\n'
        'export const tokens = sqliteTable("payment_tokens", {});\n',
        encoding="utf-8")
    out = _scan(tmp_path)
    names = {s["store"] for s in out["stores"]}
    assert names == {"subscriber_profiles", "payment_tokens"}
    assert all(s["file"] == "schema.ts" for s in out["stores"])


def test_create_table_enumerates(tmp_path):
    (tmp_path / "0001_init.sql").write_text(
        "CREATE TABLE users (id serial);\n"
        'CREATE TABLE IF NOT EXISTS "gift_codes" (id uuid);\n',
        encoding="utf-8")
    out = _scan(tmp_path)
    assert {s["store"] for s in out["stores"]} == {"users", "gift_codes"}


def test_prisma_and_sqlalchemy_enumerate(tmp_path):
    (tmp_path / "schema.prisma").write_text(
        "model HealthProfile {\n  id String @id\n}\n", encoding="utf-8")
    (tmp_path / "models.py").write_text(
        'class Profile(Base):\n    __tablename__ = "profiles"\n',
        encoding="utf-8")
    out = _scan(tmp_path)
    assert {s["store"] for s in out["stores"]} == {"HealthProfile", "profiles"}


def test_duplicate_sightings_collapse_to_one_store(tmp_path):
    (tmp_path / "a.sql").write_text("CREATE TABLE users (id int);\n",
                                    encoding="utf-8")
    (tmp_path / "b.sql").write_text("CREATE TABLE users (id int);\n",
                                    encoding="utf-8")
    out = _scan(tmp_path)
    assert len([s for s in out["stores"] if s["store"] == "users"]) == 1


def test_storage_hint_it_cannot_parse_is_named(tmp_path):
    """A migrations directory carrying a syntax the scanner does not read is
    a place stores could hide — named, never absorbed into a clean result."""
    mig = tmp_path / "migrations"
    mig.mkdir()
    (mig / "0001_init.clj").write_text("(create-table :users)\n",
                                       encoding="utf-8")
    out = _scan(tmp_path)
    assert out["stores"] == []
    assert "migrations/0001_init.clj" in out["unparsed_storage"]


def test_unreadable_schema_file_is_named(tmp_path):
    p = tmp_path / "schema.sql"
    p.write_text("CREATE TABLE hidden (id int);\n", encoding="utf-8")
    os.chmod(p, 0)
    try:
        out = _scan(tmp_path)
        assert "schema.sql" in out["unread"]
    finally:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)


def test_data_files_are_never_opened(tmp_path):
    """S-108.3 structurally: a dotenv value file and a sqlite database in
    the tree are not read — no store enumerated from them, no content in
    the report."""
    (tmp_path / ".env").write_text("SECRET=sk_live_do_not_read\n",
                                   encoding="utf-8")
    (tmp_path / "app.sqlite3").write_bytes(b"SQLite format 3\0" + b"x" * 64)
    (tmp_path / "schema.sql").write_text("CREATE TABLE t (id int);\n",
                                         encoding="utf-8")
    out = _scan(tmp_path)
    dumped = json.dumps(out)
    assert "sk_live_do_not_read" not in dumped
    assert {s["store"] for s in out["stores"]} == {"t"}


def test_architecture_ir_data_models_are_candidates(tmp_path):
    """The IR's data_models ride along (the task's second mechanical source):
    a dataclass-shaped model no schema regex sees still reaches the
    candidate list, pointing at its own module. A corrupt IR is named in
    unread, never crashed on; an absent IR is a quiet no-op — the walk is
    the primary source and a project that never ran /friday:reference owes
    no finding for that."""
    gen = tmp_path / "docs" / "architecture" / "generated"
    gen.mkdir(parents=True)
    (gen / "architecture-ir.json").write_text(json.dumps({
        "data_models": [{"name": "SessionRow", "kind": "dataclass",
                         "module": "app/models.py", "fields": ["id"],
                         "line": 10}]}), encoding="utf-8")
    out = _scan(tmp_path)
    assert {"store": "SessionRow", "file": "app/models.py"} in out["stores"]

    (gen / "architecture-ir.json").write_text("{not json", encoding="utf-8")
    out2 = _scan(tmp_path)
    assert out2["stores"] == []
    assert "docs/architecture/generated/architecture-ir.json" in out2["unread"]


def test_compare_names_undeclared_candidates(tmp_path):
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    (root / "schema.sql").write_text(
        "CREATE TABLE profiles (id int);\nCREATE TABLE sessions (id int);\n",
        encoding="utf-8")
    answers = {"at-rest": "x", "copies": "cites project-copies",
               "deletion": "x", "reach": "x", "basis": "x", "told": "x"}
    sd.declare(str(root), store="profiles", store_class="health",
               answers=answers, requirements=["FR-1.1"], when="2026-08-04")
    out = scan_mod.compare(str(root))
    assert [c["store"] for c in out["undeclared"]] == ["sessions"]
    assert out["declared_not_seen"] == []


def test_compare_names_declared_stores_the_tree_no_longer_shows(tmp_path):
    """The read-back's mechanical assist: a declared store the enumeration
    cannot find any more is surfaced — dropped table, renamed store, or a
    storage shape the scan cannot read; the reader decides which."""
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    answers = {"at-rest": "x", "copies": "cites project-copies",
               "deletion": "x", "reach": "x", "basis": "x", "told": "x"}
    sd.declare(str(root), store="ghost_table", store_class="health",
               answers=answers, requirements=["FR-1.1"], when="2026-08-04")
    out = scan_mod.compare(str(root))
    assert out["declared_not_seen"] == ["ghost_table"]


def test_cli_emits_json(tmp_path):
    import subprocess
    (tmp_path / "s.sql").write_text("CREATE TABLE a (id int);\n",
                                    encoding="utf-8")
    tool = os.path.join(os.path.dirname(__file__), "..", "tools",
                        "sensitive_store_scan.py")
    r = subprocess.run([sys.executable, tool, "--root", str(tmp_path),
                        "--json"], capture_output=True, text=True)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert len(out["stores"]) == 1
