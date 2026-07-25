"""secret_names enumerator tests — FR-84 / D-0056-0057: friday lists secret
NAMES only and, by construction, never reads a value source or returns a value.
Structured output tests its empty case (hard-won lesson #6)."""
import json

import secret_names


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_enumerate_from_env_example(tmp_path):
    _write(tmp_path / ".env.example",
           "# database\nDATABASE_URL=postgres://placeholder\nexport STRIPE_KEY=sk_test_xxx\n\n")
    names = [e["name"] for e in secret_names.enumerate_names(str(tmp_path))]
    assert "DATABASE_URL" in names
    assert "STRIPE_KEY" in names


def test_values_never_returned(tmp_path):
    _write(tmp_path / ".env.example", "API_TOKEN=super-secret-should-never-appear\n")
    result = secret_names.enumerate_names(str(tmp_path))
    blob = json.dumps(result)
    assert "API_TOKEN" in blob
    assert "super-secret-should-never-appear" not in blob   # the placeholder value never surfaces
    assert all(set(e.keys()) <= {"name", "sources"} for e in result)  # no value field exists


def test_enumerate_from_python_refs(tmp_path):
    _write(tmp_path / "app.py",
           'import os\n'
           'a = os.environ["OPENAI_API_KEY"]\n'
           "b = os.getenv('SESSION_SECRET')\n"
           'c = os.environ.get("REDIS_URL", "")\n')
    names = [e["name"] for e in secret_names.enumerate_names(str(tmp_path))]
    for n in ("OPENAI_API_KEY", "SESSION_SECRET", "REDIS_URL"):
        assert n in names


def test_enumerate_from_js_refs(tmp_path):
    _write(tmp_path / "server.js",
           "const a = process.env.JWT_SECRET;\n"
           "const b = process.env['SENDGRID_KEY'];\n")
    names = [e["name"] for e in secret_names.enumerate_names(str(tmp_path))]
    assert "JWT_SECRET" in names
    assert "SENDGRID_KEY" in names


def test_dedup_and_sorted(tmp_path):
    _write(tmp_path / ".env.example", "SHARED=x\nBETA=y\n")
    _write(tmp_path / "app.py", 'import os\nos.environ["SHARED"]\nos.environ["ALPHA"]\n')
    result = secret_names.enumerate_names(str(tmp_path))
    names = [e["name"] for e in result]
    assert names == sorted(names)                       # sorted output
    assert names.count("SHARED") == 1                   # deduped across sources
    shared = next(e for e in result if e["name"] == "SHARED")
    assert len(shared["sources"]) == 2                  # both sources recorded


def test_empty_case(tmp_path):
    assert secret_names.enumerate_names(str(tmp_path)) == []


def test_never_reads_real_env_file(tmp_path):
    # A real .env holds VALUES; the enumerator must never open it, so a name that
    # exists ONLY there must not surface (that absence proves the file was not read).
    _write(tmp_path / ".env", "ONLY_IN_REAL_ENV=live-secret-value\n")
    _write(tmp_path / ".env.local", "ALSO_ONLY_REAL=another\n")
    result = secret_names.enumerate_names(str(tmp_path))
    names = [e["name"] for e in result]
    assert "ONLY_IN_REAL_ENV" not in names
    assert "ALSO_ONLY_REAL" not in names
    assert "live-secret-value" not in json.dumps(result)


def test_example_vs_value_classification():
    for ex in (".env.example", ".env.sample", ".env.template", ".env.dist", "env.example"):
        assert secret_names.is_example_env_file(ex)
        assert not secret_names.is_value_env_file(ex)
    for val in (".env", ".env.local", ".env.production", ".env.development", ".env.test"):
        assert secret_names.is_value_env_file(val)
        assert not secret_names.is_example_env_file(val)


def test_skips_vendor_dirs(tmp_path):
    _write(tmp_path / "node_modules" / "pkg" / "index.js", "process.env.VENDOR_LEAK;\n")
    _write(tmp_path / "src" / "main.py", 'import os\nos.environ["REAL_APP_KEY"]\n')
    names = [e["name"] for e in secret_names.enumerate_names(str(tmp_path))]
    assert "REAL_APP_KEY" in names
    assert "VENDOR_LEAK" not in names
