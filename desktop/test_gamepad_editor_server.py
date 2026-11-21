"""LAN authentication checks for the shared desktop/mobile gamepad editor."""

import json
import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import gamepad_editor_server
import gamepad_layouts_loader
import pairing
import server


class GamepadEditorServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = "ED1T23"
        cls.secret = cls.code + "GamepadEditorSecret0123456789"
        server.configure(cls.code, cls.secret, 9876)
        cls.httpd = ThreadingHTTPServer(("0.0.0.0", 0), gamepad_editor_server.EditorHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)

    def request(self, host, path, method="GET", body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"http://{host}:{self.port}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=3) as response:
            return response.status, response.read()

    def test_loopback_remains_available_without_code(self):
        status, body = self.request("127.0.0.1", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": True})

    def test_lan_requires_pairing_code(self):
        with self.assertRaises(HTTPError) as caught:
            self.request(pairing._get_lan_ip(), "/api/gamepad-layouts")
        self.assertEqual(caught.exception.code, 403)

    def test_lan_code_loads_same_editor_and_data(self):
        lan_ip = pairing._get_lan_ip()
        status, page = self.request(lan_ip, f"/?code={self.code}&mobile=1")
        self.assertEqual(status, 200)
        self.assertIn(b"PhoneKB Studio", page)
        self.assertIn(b"AUTH_QUERY", page)

        status, body = self.request(lan_ip, f"/api/gamepad-layouts?code={self.code}&mobile=1")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), gamepad_layouts_loader.load())


if __name__ == "__main__":
    unittest.main()
