"""Authenticated HTTP service for the desktop and mobile gamepad editor."""
from __future__ import annotations

import json
import logging
import os
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import gamepad_layouts_loader


log = logging.getLogger("phonekb.gamepad_editor")
PORT = 9878


def _editor_root():
    source_root = os.path.dirname(os.path.abspath(__file__))
    bundled_root = getattr(sys, "_MEIPASS", None)
    for root in (os.path.join(source_root, "gamepad_editor"), os.path.join(bundled_root, "gamepad_editor") if bundled_root else None):
        if root and os.path.isfile(os.path.join(root, "index.html")):
            return root
    return os.path.join(source_root, "gamepad_editor")


class EditorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=_editor_root(), **kwargs)

    def log_message(self, format, *args):
        log.info("editor %s", format % args)

    def _json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _is_authorized(self):
        client_ip = str(self.client_address[0] or "")
        if client_ip in {"127.0.0.1", "::1"}:
            return True
        code = parse_qs(urlsplit(self.path).query).get("code", [""])[0]
        try:
            import server
            return server._check_secret(code)
        except Exception:
            log.exception("unable to validate gamepad editor request")
            return False

    def _reject_unauthorized(self):
        if urlsplit(self.path).path.startswith("/api/"):
            self._json(HTTPStatus.FORBIDDEN, {"ok": False, "msg": "pairing required"})
        else:
            self.send_error(HTTPStatus.FORBIDDEN, "pairing required")

    def do_GET(self):
        if not self._is_authorized():
            self._reject_unauthorized()
            return
        if urlsplit(self.path).path == "/api/gamepad-layouts":
            self._json(HTTPStatus.OK, gamepad_layouts_loader.load())
            return
        if urlsplit(self.path).path == "/api/health":
            self._json(HTTPStatus.OK, {"ok": True})
            return
        super().do_GET()

    def do_PUT(self):
        if not self._is_authorized():
            self._reject_unauthorized()
            return
        if urlsplit(self.path).path != "/api/gamepad-layouts":
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "msg": "not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 512 * 1024:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            saved = gamepad_layouts_loader.save(payload)
            try:
                import server
                server.notify_gamepad_layouts_changed()
            except Exception:
                log.exception("unable to notify connected phones about gamepad layout changes")
            self._json(HTTPStatus.OK, {"ok": True, "data": saved})
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "msg": str(error)})
        except Exception as error:
            log.exception("save gamepad layout failed")
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "msg": str(error)})


def run(port=PORT):
    httpd = ThreadingHTTPServer(("0.0.0.0", int(port)), EditorHandler)
    httpd.daemon_threads = True
    log.info("gamepad editor listening on http://0.0.0.0:%s", port)
    httpd.serve_forever(poll_interval=0.5)
