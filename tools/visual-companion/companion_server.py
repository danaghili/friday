#!/usr/bin/env python3
"""The visual companion's local server (FR-72) — a browser tab beside the
terminal, offered just-in-time so a question that is clearer SHOWN than told can
be seen and clicked. Adopted with credit from superpowers' visual-companion.md
(their server is bundled Node; friday's is pure-Python-stdlib, zero runtime
dependencies, so a marketplace stranger who has never heard of superpowers still
gets it — NFR-3).

Shape:
  CompanionState  — the pure, testable core: the current question, the recorded
                    selection (with its exploration path — a hesitation is data,
                    FR-74), and the render. A new question clears a stale choice;
                    "continue in terminal" clears the board.
  serve()         — thin http.server plumbing over one shared CompanionState:
                      GET  /            the page (server-rendered + self-polling)
                      GET  /state       {question, selection} JSON for polling
                      GET  /selection   {selection} JSON the agent reads back
                      POST /question    the agent sets the current question
                      POST /select      the browser records {choice, path}
                      POST /continue    "continuing in terminal…" — clears

Binds 127.0.0.1 only (local, never phones home — NFR-4). Pure stdlib.
"""
from __future__ import annotations

import html
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class CompanionState:
    """The companion's whole state, guarded by a lock so the agent's POSTs and
    the browser's POSTs never tear. journal_root, when set, routes each recorded
    selection into the elicitation event stream through the single substrate
    writer (FR-74); left None in tests, it is pure and does no I/O."""

    def __init__(self, journal_root: str | None = None):
        self._q: dict | None = None
        self._sel: dict | None = None
        self._lock = threading.Lock()
        self.journal_root = journal_root

    def set_question(self, question: dict) -> None:
        with self._lock:
            self._q = dict(question)
            self._sel = None  # a new question can never inherit the last choice

    def current_question(self) -> dict | None:
        with self._lock:
            return dict(self._q) if self._q else None

    def record_selection(self, choice: str, path: list | None = None) -> None:
        with self._lock:
            self._sel = {"choice": choice, "path": list(path or [])}
        self._journal_selection(choice, path or [])

    def read_selection(self) -> dict | None:
        with self._lock:
            return dict(self._sel) if self._sel else None

    def continue_in_terminal(self) -> None:
        with self._lock:
            self._q = None
            self._sel = None

    # --- rendering ------------------------------------------------------------

    def render(self) -> str:
        q = self.current_question()
        if not q:
            body = ('<div class="continuing">Continuing in the terminal — '
                    'choices cleared.</div>')
            title = ""
        else:
            title = q.get("title", "")
            opts = "".join(
                f'<button class="opt" data-choice="{html.escape(str(o))}">'
                f'{html.escape(str(o))}</button>'
                for o in q.get("options", []))
            prompt = html.escape(str(q.get("prompt", "")))
            body = (f'<h1>{html.escape(str(title))}</h1>'
                    f'{f"<p>{prompt}</p>" if prompt else ""}'
                    f'<div class="options">{opts}</div>'
                    f'<div class="recorded" id="recorded"></div>')
        return _PAGE.replace("__BODY__", body).replace(
            "__TITLE__", html.escape(json.dumps(title)))

    # --- FR-74: selections join the elicitation event stream ------------------

    def _journal_selection(self, choice: str, path: list) -> None:
        if not self.journal_root:
            return
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))))  # tools/
            import friday_substrate as fs  # noqa: E402
            fs.append_journal_line(self.journal_root, fs.build_journal_line(
                "elicitation", "discovery", by="session",
                data={"companion": True, "choice": choice, "path": list(path)}))
        except Exception:
            pass  # the UI never fails because telemetry did


# The whole page, self-contained (inline CSS/JS, no external anything — a strict
# offline artifact). It renders the server's current question, tracks the
# exploration path (every option the PM hovers before committing — the hesitation
# FR-74 wants), posts the click, and polls /state so a new question or a clear
# from the agent updates the tab without a manual refresh.
_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>friday · visual companion</title>
<style>
  :root { color-scheme: dark; }
  body { background:#0B0D0F; color:#E6E8EA; font:16px/1.5 system-ui, sans-serif;
         margin:0; display:flex; min-height:100vh; align-items:center; justify-content:center; }
  #app { max-width:640px; width:100%; padding:2rem; }
  h1 { font-size:1.4rem; margin:0 0 .5rem; }
  p { color:#9AA0A6; margin:0 0 1.5rem; }
  .options { display:flex; flex-direction:column; gap:.75rem; }
  .opt { text-align:left; background:#14171A; color:#E6E8EA; border:1px solid #23272B;
         border-radius:8px; padding:.9rem 1rem; font:inherit; cursor:pointer; }
  .opt:hover { border-color:#3DD8C4; }
  .opt.chosen { border-color:#3DD8C4; background:#14201F; }
  .recorded { margin-top:1.25rem; color:#3DD8C4; min-height:1.5rem; }
  .continuing { color:#9AA0A6; text-align:center; }
</style></head>
<body><div id="app">__BODY__</div>
<script>
(function () {
  let servedTitle = __TITLE__;
  let path = [];
  function wire() {
    document.querySelectorAll('.opt').forEach(function (b) {
      var label = b.getAttribute('data-choice');
      b.addEventListener('mouseenter', function () {
        if (path[path.length - 1] !== label) path.push(label);  // hesitation trail
      });
      b.addEventListener('click', function () {
        path.push(label);
        document.querySelectorAll('.opt').forEach(function (x){ x.classList.remove('chosen'); });
        b.classList.add('chosen');
        fetch('/select', { method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ choice: label, path: path }) });
        var r = document.getElementById('recorded');
        if (r) r.textContent = 'Recorded — you can change your mind, or return to the terminal.';
      });
    });
  }
  wire();
  setInterval(function () {
    fetch('/state').then(function (r){ return r.json(); }).then(function (s) {
      var now = s.question ? (s.question.title || '') : '';
      if (JSON.stringify(now) !== JSON.stringify(servedTitle)) location.reload();
    }).catch(function () {});
  }, 1000);
})();
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    state: CompanionState  # bound per-server below

    def log_message(self, *_a):  # keep the terminal quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        payload = body.encode("utf-8") if isinstance(body, str) else body
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, self.state.render(), "text/html; charset=utf-8")
        elif self.path == "/state":
            self._send(200, json.dumps({"question": self.state.current_question(),
                                        "selection": self.state.read_selection()}))
        elif self.path == "/selection":
            self._send(200, json.dumps({"selection": self.state.read_selection()}))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        body = self._read_json()
        if self.path == "/question":
            self.state.set_question(body)
            self._send(200, json.dumps({"ok": True}))
        elif self.path == "/select":
            self.state.record_selection(body.get("choice", ""), body.get("path"))
            self._send(200, json.dumps({"ok": True}))
        elif self.path == "/continue":
            self.state.continue_in_terminal()
            self._send(200, json.dumps({"ok": True}))
        else:
            self._send(404, json.dumps({"error": "not found"}))


def serve(state: CompanionState, host: str = "127.0.0.1", port: int = 0):
    """Start the companion server bound to `host`. Returns (httpd, base_url); the
    caller runs httpd.serve_forever() (usually on a thread) and shuts it down.
    port=0 picks a free ephemeral port — the real URL is in the returned base."""
    handler = type("_BoundHandler", (_Handler,), {"state": state})
    httpd = ThreadingHTTPServer((host, port), handler)
    real_port = httpd.server_address[1]
    return httpd, f"http://{host}:{real_port}"


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="friday visual companion server (FR-72)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--root", default=None,
                    help="project root — routes selections into the elicitation journal")
    args = ap.parse_args(argv)
    state = CompanionState(journal_root=os.path.abspath(args.root) if args.root else None)
    httpd, url = serve(state, host=args.host, port=args.port)
    print(json.dumps({"url": url}), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
