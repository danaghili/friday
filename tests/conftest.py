"""Test path setup: make tools/, tools/doc-index/, tools/doc-synthesis/ and hooks/
importable without installing anything (mirrors how the plugin resolves its own
modules at runtime via plugin-root-relative paths)."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("tools", os.path.join("tools", "doc-index"),
            os.path.join("tools", "doc-synthesis"), "hooks"):
    p = os.path.join(_ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

BUILD_ROOT = _ROOT
