"""Localhost-only HTTP UI. The browser never supplies raw CE commands or Lua."""
from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .bridge import BridgeError
from .diagnostics import DiagnosticError
from .service import TrainerService
from .store import StoreError

STATIC = Path(__file__).with_name("static")
MAX_BODY = 64 * 1024


def make_handler(service: TrainerService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AITrainer/0.1"

        def _headers(self, status: int, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'self'",
            )

        def _json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._headers(status, "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _same_origin(self):
            allowed = {"127.0.0.1:" + str(self.server.server_port),
                       "localhost:" + str(self.server.server_port)}
            if self.headers.get("Host", "") not in allowed:
                return False
            origin = self.headers.get("Origin")
            return origin is None or origin in {"http://" + x for x in allowed}

        def _route(self, path, payload):
            if path == "/api/games":
                return service.store.add_game(payload["name"], payload["exe"])
            if path == "/api/features/capture":
                return service.capture(
                    payload["game_id"], payload["title"], payload["record_description"]
                )
            if path == "/api/diagnostics/self-test":
                return service.selftest()
            if path == "/api/features/toggle":
                return service.toggle(payload["feature_id"], payload["enabled"])
            raise StoreError("未知操作")

        def do_GET(self):
            if not self._same_origin():
                return self._json(403, {"error": "Invalid host or origin"})
            parsed = urlsplit(self.path)
            try:
                if parsed.path == "/api/state":
                    return self._json(200, service.snapshot())
                if parsed.path == "/api/bridge":
                    return self._json(200, service.status())
                if parsed.path == "/api/records":
                    game_id = parse_qs(parsed.query).get("game_id", [""])[0]
                    return self._json(200, {"records": service.records(game_id)})
                if parsed.path == "/api/health":
                    return self._json(200, {"ok": True})
                assets = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
                filename = assets.get(parsed.path)
                if filename:
                    data = (STATIC / filename).read_bytes()
                    mime = {"index.html": "text/html", "app.js": "application/javascript",
                            "style.css": "text/css"}[filename]
                    self._headers(200, mime + "; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                return self._json(404, {"error": "Not found"})
            except (StoreError, DiagnosticError, ValueError, KeyError, TypeError) as exc:
                return self._json(400, {"error": str(exc)})
            except BridgeError as exc:
                return self._json(502, {"error": str(exc)})

        def do_POST(self):
            if not self._same_origin():
                return self._json(403, {"error": "Invalid host or origin"})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self._json(415, {"error": "Expected application/json"})
            try:
                size = int(self.headers.get("Content-Length", "-1"))
                if size < 0 or size > MAX_BODY:
                    return self._json(413, {"error": "Invalid request size"})
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("JSON body must be an object")
                result = self._route(urlsplit(self.path).path, payload)
                return self._json(200, result)
            except (StoreError, ValueError, KeyError, TypeError) as exc:
                return self._json(400, {"error": str(exc)})
            except BridgeError as exc:
                return self._json(502, {"error": str(exc)})

    return Handler


def serve(service: TrainerService, port: int = 8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(service))
    print("AI Game Trainer ready: http://127.0.0.1:" + str(server.server_port))
    return server
