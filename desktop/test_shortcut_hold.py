import asyncio
import json
import unittest
from unittest import mock

import server
import usb_server


SHORTCUT_LAYOUTS = {
    "layouts": [{
        "pages": [{
            "slots": [{
                "key": {
                    "id": "copy",
                    "type": "shortcut",
                    "shortcut": {"modifiers": ["ctrl"], "key": "c"},
                }
            }]
        }]
    }]
}

PASTE_LAYOUTS = {
    "layouts": [{"pages": [{"slots": [{"key": {
        "id": "paste",
        "type": "shortcut",
        "shortcut": {"modifiers": ["lctrl"], "key": "v"},
    }}]}]}]
}


class FakeWebSocket:
    def __init__(self, messages=(), remote_address=("127.0.0.1", 43220)):
        self.remote_address = remote_address
        self._messages = iter(json.dumps(item) for item in messages)
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


class ShortcutHoldTest(unittest.TestCase):
    def tearDown(self):
        server._gamepad_held_keys.clear()

    def test_wifi_holds_and_releases_shortcut_in_reverse_order(self):
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        ws = FakeWebSocket([
            {"action": "pair", "secret": "ABC123"},
            {"action": "hold_slot", "id": "copy", "down": True},
            {"action": "hold_slot", "id": "copy", "down": False},
        ], remote_address=("192.168.1.30", 43221))
        calls = []
        try:
            with mock.patch.object(server.layouts_loader, "load", return_value=SHORTCUT_LAYOUTS), \
                    mock.patch.object(server.keytrigger, "key_down", side_effect=lambda key: calls.append(("down", key)) or True), \
                    mock.patch.object(server.keytrigger, "key_up", side_effect=lambda key: calls.append(("up", key)) or True):
                asyncio.run(server.handle_client(ws))
            self.assertEqual(calls[:4], [("down", "ctrl"), ("down", "c"), ("up", "c"), ("up", "ctrl")])
            self.assertEqual(len([item for item in ws.sent if item.get("action") == "hold_slot_ack" and item.get("ok")]), 2)
        finally:
            server.SECRET_CODE = old_code

    def test_usb_holds_and_releases_shortcut(self):
        ws = FakeWebSocket(remote_address=("127.0.0.1", 43222))
        calls = []

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "hold_slot", "id": "copy", "down": True})
            await usb_server._process_msg(ws, {"action": "hold_slot", "id": "copy", "down": False})

        try:
            with mock.patch.object(server.layouts_loader, "load", return_value=SHORTCUT_LAYOUTS), \
                    mock.patch.object(server.keytrigger, "key_down", side_effect=lambda key: calls.append(("down", key)) or True), \
                    mock.patch.object(server.keytrigger, "key_up", side_effect=lambda key: calls.append(("up", key)) or True):
                asyncio.run(exercise())
            self.assertEqual(calls, [("down", "ctrl"), ("down", "c"), ("up", "c"), ("up", "ctrl")])
        finally:
            server._release_gamepad_keys(ws)
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)

    def test_usb_paste_sends_ctrl_v(self):
        ws = FakeWebSocket(remote_address=("127.0.0.1", 43223))
        calls = []

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "hold_slot", "id": "paste", "down": True})
            await usb_server._process_msg(ws, {"action": "hold_slot", "id": "paste", "down": False})

        try:
            with mock.patch.object(server.layouts_loader, "load", return_value=PASTE_LAYOUTS), \
                    mock.patch.object(server.keytrigger, "key_down", side_effect=lambda key: calls.append(("down", key)) or True), \
                    mock.patch.object(server.keytrigger, "key_up", side_effect=lambda key: calls.append(("up", key)) or True):
                asyncio.run(exercise())
            self.assertEqual(calls, [("down", "lctrl"), ("down", "v"), ("up", "v"), ("up", "lctrl")])
        finally:
            server._release_gamepad_keys(ws)
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)


if __name__ == "__main__":
    unittest.main()
