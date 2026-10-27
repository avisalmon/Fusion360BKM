"""CopilotBridge - run Python inside Fusion 360 from outside (chat / CLI).

Starts a tiny HTTP server on 127.0.0.1 inside Fusion. Scripts POSTed to /exec
are executed on Fusion's main thread (via a CustomEvent, because the Fusion API
is not thread-safe). stdout, a `result` variable and any traceback are returned
as JSON.

Endpoints
  GET  /ping              -> {"ok": true, "fusion": "...", "doc": "..."}
  POST /exec              -> body: {"code": "...", "name": "...", "timeout": 120}
                             or raw python text (Content-Type: text/plain)
  POST /screenshot        -> body: {"path": "...png", "width": 1280, "height": 800, "fit": true}

Script namespace: adsk, app, ui, traceback, plus helpers from bridge_helpers.
Set a JSON-serialisable variable named `result` to return structured data.
"""

import io
import json
import os
import threading
import traceback
import uuid
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer

import adsk.cam
import adsk.core
import adsk.fusion

BRIDGE_VERSION = "0.1.1"
HOST = "127.0.0.1"
PREFERRED_PORT = 8787
EVENT_ID = "CopilotBridge_ExecEvent"
# realpath() resolves the AddIns junction so the port file always lands in the project's bridge/ dir
_ADDIN_DIR = os.path.dirname(os.path.realpath(__file__))
PORT_FILE = os.path.join(os.path.dirname(_ADDIN_DIR), "bridge", "port.txt")
_SINGLETON_KEY = (
    "_copilot_bridge_singleton"  # attribute on sys: guards against Fusion loading us twice
)

app = adsk.core.Application.get()
ui = app.userInterface

_handlers = []  # keep handler refs alive
_server = None
_server_thread = None
_jobs = {}  # job_id -> {'code','name','done','result'}
_jobs_lock = threading.Lock()


def _helpers_namespace():
    """Build the globals a script runs with. Reloads helpers each call so edits are live."""
    ns = {
        "__name__": "__copilot__",
        "adsk": adsk,
        "app": app,
        "ui": ui,
        "traceback": traceback,
        "json": json,
        "os": os,
    }
    try:
        import importlib
        import sys

        if _ADDIN_DIR not in sys.path:
            sys.path.insert(0, _ADDIN_DIR)
        import bridge_helpers

        importlib.reload(bridge_helpers)
        for k in getattr(bridge_helpers, "__all__", []):
            ns[k] = getattr(bridge_helpers, k)
    except Exception:
        ns["_helpers_error"] = traceback.format_exc()
    return ns


def _run_job(job):
    out = io.StringIO()
    res = {"ok": True, "stdout": "", "result": None, "error": None}
    try:
        ns = _helpers_namespace()
        with redirect_stdout(out), redirect_stderr(out):
            exec(compile(job["code"], job.get("name") or "<copilot>", "exec"), ns)
        if "result" in ns:
            try:
                json.dumps(ns["result"])
                res["result"] = ns["result"]
            except Exception:
                res["result"] = repr(ns["result"])
        if "_helpers_error" in ns:
            res["helpers_error"] = ns["_helpers_error"]
    except Exception:
        res["ok"] = False
        res["error"] = traceback.format_exc()
    res["stdout"] = out.getvalue()
    return res


class ExecEventHandler(adsk.core.CustomEventHandler):
    """Runs on Fusion's main thread."""

    def notify(self, args):
        job_id = args.additionalInfo
        with _jobs_lock:
            job = _jobs.get(job_id)
        if not job:
            return
        try:
            job["result"] = _run_job(job)
        except Exception:
            job["result"] = {
                "ok": False,
                "stdout": "",
                "result": None,
                "error": traceback.format_exc(),
            }
        finally:
            job["done"].set()


def _submit(code, name="<copilot>", timeout=120):
    """Called from the HTTP thread: queue code for the main thread and wait."""
    job_id = uuid.uuid4().hex
    job = {"code": code, "name": name, "done": threading.Event(), "result": None}
    with _jobs_lock:
        _jobs[job_id] = job
    app.fireCustomEvent(EVENT_ID, job_id)
    finished = job["done"].wait(timeout)
    with _jobs_lock:
        _jobs.pop(job_id, None)
    if not finished:
        return {
            "ok": False,
            "stdout": "",
            "result": None,
            "error": f"Timed out after {timeout}s waiting for Fusion main thread "
            "(is a modal dialog open in Fusion?)",
        }
    return job["result"]


PING_CODE = (
    """
doc = app.activeDocument
result = {
    'fusion': app.version,
    'bridge': %r,
    'doc': doc.name if doc else None,
    'product': app.activeProduct.productType if app.activeProduct else None,
}
"""
    % BRIDGE_VERSION
)

SCREENSHOT_CODE = """
import os
path = %(path)r
os.makedirs(os.path.dirname(path), exist_ok=True)
vp = app.activeViewport
if %(fit)r:
    vp.fit()
ok = vp.saveAsImageFile(path, %(width)d, %(height)d)
result = {'saved': bool(ok), 'path': path}
"""


class BridgeHTTPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):  # silence console spam
        pass

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8") if n else ""
        ctype = (self.headers.get("Content-Type") or "").lower()
        if "json" in ctype and raw.strip():
            return json.loads(raw)
        return {"code": raw}

    def do_GET(self):
        if self.path.startswith("/ping"):
            self._send_json(_submit(PING_CODE, "<ping>", 30))
        else:
            self._send_json({"ok": False, "error": "unknown endpoint"}, 404)

    def do_POST(self):
        try:
            payload = self._read_body()
        except Exception:
            self._send_json({"ok": False, "error": traceback.format_exc()}, 400)
            return

        if self.path.startswith("/exec"):
            code = payload.get("code", "")
            name = payload.get("name") or "<copilot>"
            timeout = float(payload.get("timeout") or 120)
            self._send_json(_submit(code, name, timeout))
        elif self.path.startswith("/screenshot"):
            params = {
                "path": payload.get("path")
                or os.path.join(os.path.dirname(PORT_FILE), "screenshot.png"),
                "width": int(payload.get("width") or 1280),
                "height": int(payload.get("height") or 800),
                "fit": bool(payload.get("fit", True)),
            }
            self._send_json(_submit(SCREENSHOT_CODE % params, "<screenshot>", 60))
        else:
            self._send_json({"ok": False, "error": "unknown endpoint"}, 404)


class _ReusableHTTPServer(HTTPServer):
    allow_reuse_address = (
        False  # on Windows SO_REUSEADDR lets two servers share a port - never want that
    )
    daemon_threads = True


def _start_server():
    global _server, _server_thread
    last_err = None
    for port in range(PREFERRED_PORT, PREFERRED_PORT + 10):
        try:
            _server = _ReusableHTTPServer((HOST, port), BridgeHTTPHandler)
            break
        except OSError as e:
            last_err = e
            _server = None
    if _server is None:
        raise RuntimeError(f"CopilotBridge: no free port near {PREFERRED_PORT}: {last_err}")
    _server_thread = threading.Thread(
        target=_server.serve_forever, name="CopilotBridgeHTTP", daemon=True
    )
    _server_thread.start()
    os.makedirs(os.path.dirname(PORT_FILE), exist_ok=True)
    with open(PORT_FILE, "w", encoding="utf-8") as f:
        f.write(str(_server.server_address[1]))
    return _server.server_address[1]


def run(context):
    import sys

    try:
        existing = getattr(sys, _SINGLETON_KEY, None)
        if existing is not None and existing.get("server") is not None:
            # Fusion sometimes loads the same add-in via both the junction and its real path
            try:
                app.log(
                    f"CopilotBridge: already running on port {existing['port']} "
                    f"(from {existing['path']}), skipping duplicate load of {__file__}"
                )
            except Exception:
                pass
            return
        try:
            app.unregisterCustomEvent(EVENT_ID)  # in case of a stale registration
        except Exception:
            pass
        ev = app.registerCustomEvent(EVENT_ID)
        handler = ExecEventHandler()
        ev.add(handler)
        _handlers.append(handler)
        port = _start_server()
        setattr(sys, _SINGLETON_KEY, {"server": _server, "port": port, "path": __file__})
        try:
            app.log(f"CopilotBridge {BRIDGE_VERSION} listening on http://{HOST}:{port}")
        except Exception:
            pass
    except Exception:
        ui.messageBox("CopilotBridge failed to start:\n" + traceback.format_exc())


def stop(context):
    global _server
    import sys

    try:
        if _server:
            _server.shutdown()
            _server.server_close()
            _server = None
            app.unregisterCustomEvent(EVENT_ID)
            _handlers.clear()
            setattr(sys, _SINGLETON_KEY, None)
            if os.path.exists(PORT_FILE):
                os.remove(PORT_FILE)
    except Exception:
        pass
