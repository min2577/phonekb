"""End-to-end protocol checks for QR pairing and login state roundtrip."""

import asyncio
import json
import os
import socket
import time
import unittest
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy
import websockets
from PySide6 import QtGui, QtWidgets
from websockets.asyncio.server import serve

import pairing
import server
from pages.pairing_page import PairingPage


class PairingFlowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.secret = "Ab3Def" + "QrLoginFlowSecret0123456789"
        self.code = self.secret[:6].upper()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]

        server.configure(self.code, self.secret, self.port)
        server._sessions.clear()
        self.ws_server = await serve(server.handle_client, "0.0.0.0", self.port)

    async def asyncTearDown(self):
        self.ws_server.close()
        await self.ws_server.wait_closed()
        server._sessions.clear()

    async def test_qr_to_session_to_login_status_roundtrip(self):
        lan_ip = pairing._get_lan_ip()
        info = pairing.refresh_pairing_info(self.secret, lan_ip, self.port)
        parsed = urlparse(info["ws_url"])
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.scheme, "ws")
        self.assertEqual(parsed.hostname, lan_ip)
        self.assertEqual(parsed.port, self.port)
        self.assertEqual(query["code"], [self.code])
        self.assertNotIn(self.secret, info["ws_url"])
        self.assertTrue(info["qr_png"].startswith(b"\x89PNG\r\n\x1a\n"))

        token = query["t"][0]
        async with websockets.connect(info["ws_url"]) as ws:
            await ws.send(json.dumps({"action": "pair", "secret": token, "ua": "android-e2e"}))
            reply = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))

            self.assertEqual(reply["action"], "paired")
            self.assertTrue(reply["ok"])
            self.assertEqual(reply["server"], "phonekb/1.0")
            self.assertEqual(reply["proto"], 1)
            self.assertEqual(len(server._sessions), 1)
            session = next(iter(server._sessions.values()))
            self.assertEqual(session["ip"], lan_ip)
            self.assertGreaterEqual(session["paired_at"], time.time() - 2)

            await ws.send(json.dumps({"action": "ping"}))
            pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
            self.assertEqual(pong, {"action": "pong"})

            await ws.send(json.dumps({"action": "list_devices"}))
            devices = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
            self.assertEqual(devices["action"], "devices")
            self.assertEqual(len(devices["devices"]), 1)
            self.assertEqual(devices["devices"][0]["ip"], lan_ip)
            self.assertEqual(devices["devices"][0]["ua"], "android-e2e")
            self.assertGreater(devices["devices"][0]["last_pong"], 0)

        for _ in range(20):
            if not server._sessions:
                break
            await asyncio.sleep(0.01)
        self.assertFalse(server._sessions)

    async def test_expired_qr_token_is_rejected(self):
        token = pairing._make_pairing_token(self.secret, int(time.time()) - 61)
        async with websockets.connect(f"ws://127.0.0.1:{self.port}/") as ws:
            await ws.send(json.dumps({"action": "pair", "secret": token}))
            reply = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
            self.assertEqual(reply, {"action": "paired", "ok": False})
            self.assertNotIn(ws, server._sessions)

    async def test_pairing_page_renders_decodable_android_payload(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        info = pairing.refresh_pairing_info(self.secret, pairing._get_lan_ip(), self.port)
        page = PairingPage(info)
        pixmap = page._qr_label.pixmap()
        self.assertFalse(pixmap.isNull())

        image = pixmap.toImage().convertToFormat(QtGui.QImage.Format_RGB888)
        raw = numpy.frombuffer(image.bits(), dtype=numpy.uint8)
        rows = raw.reshape((image.height(), image.bytesPerLine()))
        pixels = rows[:, : image.width() * 3].reshape((image.height(), image.width(), 3))
        decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(pixels)

        self.assertEqual(decoded, page._info["ws_url"])
        self.assertRegex(decoded, r"^ws://[^:/]+:\d+/\?t=\d+\.[0-9a-f]{16}&code=[A-Z0-9]{6}$")
        self.assertNotIn(self.secret, decoded)
        page.close()
        app.processEvents()


if __name__ == "__main__":
    unittest.main()
