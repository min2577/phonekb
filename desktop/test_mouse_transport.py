import asyncio
import json
import unittest
from unittest import mock

import server
import usb_server


class FakeWebSocket:
    def __init__(self, messages=None, remote_address=("127.0.0.1", 40100)):
        self.remote_address = remote_address
        self._messages = iter(json.dumps(item) for item in (messages or []))
        self.sent = []

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._messages)
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, payload):
        self.sent.append(json.loads(payload))


class MouseTransportTest(unittest.TestCase):
    def test_zoom_holds_ctrl_only_for_wheel_event(self):
        with mock.patch.object(server.mouse.keytrigger, "key_down") as key_down, \
             mock.patch.object(server.mouse.keytrigger, "key_up") as key_up, \
             mock.patch.object(server.mouse, "wheel", return_value=1) as wheel:
            self.assertEqual(server.mouse.zoom(120), 1)
        key_down.assert_called_once_with("ctrl")
        wheel.assert_called_once_with(120)
        key_up.assert_called_once_with("ctrl")

    def test_wifi_relative_move_is_inline_and_has_no_ack(self):
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        ws = FakeWebSocket([
            {"action": "pair", "secret": "ABC123"},
            {"action": "mouse", "op": "move", "dx": 7, "dy": -4},
        ], remote_address=("192.168.1.8", 40101))
        try:
            with mock.patch.object(server.mouse, "move") as move:
                asyncio.run(server.handle_client(ws))
            move.assert_called_once_with(7, -4)
            self.assertFalse(any(item.get("action") == "mouse_ack" for item in ws.sent))
        finally:
            server.SECRET_CODE = old_code

    def test_usb_relative_move_is_inline_and_has_no_ack(self):
        ws = FakeWebSocket()

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "mouse", "op": "move", "dx": -3, "dy": 9})

        try:
            with mock.patch.object(usb_server.mouse, "move") as move:
                asyncio.run(exercise())
            move.assert_called_once_with(-3, 9)
            self.assertFalse(any(item.get("action") == "mouse_ack" for item in ws.sent))
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)

    def test_wifi_zoom_routes_to_mouse_zoom(self):
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        ws = FakeWebSocket([
            {"action": "pair", "secret": "ABC123"},
            {"action": "mouse", "op": "zoom", "delta": 120},
        ], remote_address=("192.168.1.8", 40102))
        try:
            with mock.patch.object(server.mouse, "zoom") as zoom:
                asyncio.run(server.handle_client(ws))
            zoom.assert_called_once_with(120)
        finally:
            server.SECRET_CODE = old_code

    def test_usb_zoom_routes_to_mouse_zoom(self):
        ws = FakeWebSocket()
        try:
            with mock.patch.object(usb_server.mouse, "zoom") as zoom:
                async def exercise():
                    await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
                    await usb_server._process_msg(ws, {"action": "mouse", "op": "zoom", "delta": -120})
                asyncio.run(exercise())
            zoom.assert_called_once_with(-120)
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)


if __name__ == "__main__":
    unittest.main()
