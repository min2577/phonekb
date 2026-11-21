import asyncio
import json
import unittest
from unittest import mock

import server
import usb_server


class FakeWebSocket:
    def __init__(self, messages, remote_address=("127.0.0.1", 43210)):
        self.remote_address = remote_address
        self._messages = iter(json.dumps(item, ensure_ascii=False) for item in messages)
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


class CodexTransportTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "action": "codex_snapshot",
            "available": True,
            "defaults": {"reasoning_effort": "high", "model": ""},
            "tasks": [],
        }

    def test_wifi_routes_paired_codex_message(self):
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        ws = FakeWebSocket([
            {"action": "pair", "secret": "ABC123"},
            {"action": "codex_get_snapshot"},
        ], remote_address=("192.168.1.20", 43210))
        try:
            with mock.patch.object(server.codex_bridge, "handle_message", return_value=self.snapshot) as handler:
                asyncio.run(server.handle_client(ws))
            handler.assert_called_once_with({"action": "codex_get_snapshot"})
            self.assertTrue(any(item.get("action") == "paired" and item.get("ok") for item in ws.sent))
            self.assertTrue(any(item.get("action") == "codex_snapshot" for item in ws.sent))
        finally:
            server.SECRET_CODE = old_code

    def test_usb_routes_local_codex_message(self):
        ws = FakeWebSocket([], remote_address=("127.0.0.1", 43211))

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "codex_get_snapshot"})

        try:
            with mock.patch.object(usb_server.codex_bridge, "handle_message", return_value=self.snapshot) as handler:
                asyncio.run(exercise())
            handler.assert_called_once_with({"action": "codex_get_snapshot"})
            self.assertTrue(any(item.get("action") == "paired" and item.get("ok") for item in ws.sent))
            self.assertTrue(any(item.get("action") == "codex_snapshot" for item in ws.sent))
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)

    def test_wifi_routes_approval_payload_unchanged(self):
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        message = {
            "action": "codex_approve",
            "slot": 3,
            "thread_id": "thread-3",
            "fingerprint": "approval-3",
        }
        ws = FakeWebSocket([{"action": "pair", "secret": "ABC123"}, message], remote_address=("192.168.1.25", 43220))
        ack = {"action": "codex_approve_ack", "ok": True, "slot": 3, "msg": "已允许一次"}
        try:
            with mock.patch.object(server.codex_bridge, "handle_message", return_value=ack) as handler:
                asyncio.run(server.handle_client(ws))
            handler.assert_called_once_with(message)
            self.assertTrue(any(item.get("action") == "codex_approve_ack" and item.get("ok") for item in ws.sent))
        finally:
            server.SECRET_CODE = old_code

    def test_usb_routes_rejection_payload_unchanged(self):
        message = {
            "action": "codex_reject",
            "slot": 4,
            "thread_id": "thread-4",
            "fingerprint": "approval-4",
        }
        ws = FakeWebSocket([], remote_address=("127.0.0.1", 43221))
        ack = {"action": "codex_reject_ack", "ok": True, "slot": 4, "msg": "已拒绝"}

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, message)

        try:
            with mock.patch.object(usb_server.codex_bridge, "handle_message", return_value=ack) as handler:
                asyncio.run(exercise())
            handler.assert_called_once_with(message)
            self.assertTrue(any(item.get("action") == "codex_reject_ack" and item.get("ok") for item in ws.sent))
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)

    def test_wifi_voice_dictation_uses_captured_target(self):
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        ws = FakeWebSocket([
            {"action": "pair", "secret": "ABC123"},
            {"action": "codex_voice_start"},
            {"action": "codex_dictate", "text": "你好 Codex", "append_space": True},
        ], remote_address=("192.168.1.21", 43212))
        target = {"ok": True, "hwnd": 77, "title": "Codex", "looks_like_codex": True}
        typed = {"ok": True, "sent": 17, "chars": 9, "title": "Codex"}
        try:
            with mock.patch.object(server.codex_voice, "capture_current_target", return_value=target), \
                    mock.patch.object(server.codex_voice, "type_into_target", return_value=typed) as type_into:
                asyncio.run(server.handle_client(ws))
            type_into.assert_called_once_with(77, "你好 Codex", True)
            self.assertTrue(any(item.get("action") == "codex_voice_start_ack" and item.get("hwnd") == 77 for item in ws.sent))
            self.assertTrue(any(item.get("action") == "codex_dictate_ack" and item.get("ok") for item in ws.sent))
        finally:
            server.SECRET_CODE = old_code

    def test_usb_voice_dictation_uses_captured_target(self):
        ws = FakeWebSocket([], remote_address=("127.0.0.1", 43213))
        target = {"ok": True, "hwnd": 88, "title": "Codex", "looks_like_codex": True}
        typed = {"ok": True, "sent": 11, "chars": 6, "title": "Codex"}

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "codex_voice_start"})
            await usb_server._process_msg(ws, {"action": "codex_dictate", "text": "测试语音", "append_space": False})

        try:
            with mock.patch.object(usb_server.codex_voice, "capture_current_target", return_value=target), \
                    mock.patch.object(usb_server.codex_voice, "type_into_target", return_value=typed) as type_into:
                asyncio.run(exercise())
            type_into.assert_called_once_with(88, "测试语音", False)
            self.assertTrue(any(item.get("action") == "codex_dictate_ack" and item.get("ok") for item in ws.sent))
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)

    def test_wifi_test_input_is_one_atomic_request(self):
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        ws = FakeWebSocket([
            {"action": "pair", "secret": "ABC123"},
            {"action": "codex_test_input", "request_id": "phone-1"},
        ], remote_address=("192.168.1.22", 43214))
        result = {"ok": True, "stage": "done", "sent": 14, "chars": 14, "title": "Codex"}
        try:
            with mock.patch.object(server.codex_voice, "enter_test_phrase", return_value=result) as enter:
                asyncio.run(server.handle_client(ws))
            enter.assert_called_once_with()
            ack = next(item for item in ws.sent if item.get("action") == "codex_test_input_ack")
            self.assertTrue(ack["ok"])
            self.assertEqual(ack["stage"], "done")
            self.assertEqual(ack["request_id"], "phone-1")
        finally:
            server.SECRET_CODE = old_code

    def test_usb_test_input_returns_failure_stage(self):
        ws = FakeWebSocket([], remote_address=("127.0.0.1", 43215))
        result = {"ok": False, "stage": "locate_codex", "sent": 0, "msg": "没有找到 Codex 对话输入框"}

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "codex_test_input", "request_id": "phone-2"})

        try:
            with mock.patch.object(usb_server.codex_voice, "enter_test_phrase", return_value=result):
                asyncio.run(exercise())
            ack = next(item for item in ws.sent if item.get("action") == "codex_test_input_ack")
            self.assertFalse(ack["ok"])
            self.assertEqual(ack["stage"], "locate_codex")
            self.assertEqual(ack["request_id"], "phone-2")
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)

    def test_wifi_trigger_slot_routes_saved_codex_key(self):
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        ws = FakeWebSocket([
            {"action": "pair", "secret": "ABC123"},
            {"action": "trigger_slot", "id": "codex-key-1"},
        ], remote_address=("192.168.1.23", 43216))
        layouts = {"layouts": [{"pages": [{"slots": [{
            "key": {"id": "codex-key-1", "type": "codex", "codex": {"action": "focus_task", "slot": 1}}
        }]}]}]}
        result = {"ok": True, "msg": "已切换到任务槽 1", "layout_action": "focus_task", "slot": 1}
        try:
            with mock.patch.object(server.layouts_loader, "load", return_value=layouts), \
                    mock.patch.object(server.codex_bridge, "handle_layout_action", return_value=result) as handler:
                asyncio.run(server.handle_client(ws))
            handler.assert_called_once()
            ack = next(item for item in ws.sent if item.get("action") == "trigger_ack")
            self.assertTrue(ack["ok"])
            self.assertEqual(ack["type"], "codex")
            self.assertEqual(ack["slot"], 1)
        finally:
            server.SECRET_CODE = old_code

    def test_usb_trigger_slot_routes_saved_codex_key(self):
        ws = FakeWebSocket([], remote_address=("127.0.0.1", 43217))
        layouts = {"layouts": [{"pages": [{"slots": [{
            "key": {"id": "codex-key-2", "type": "codex", "codex": {"action": "reject", "slot": 2}}
        }]}]}]}
        result = {"ok": False, "msg": "当前 CLI Bridge 没有待批准请求", "layout_action": "reject", "slot": 2}

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "trigger_slot", "id": "codex-key-2"})

        try:
            with mock.patch.object(usb_server.layouts_loader, "load", return_value=layouts), \
                    mock.patch.object(usb_server.codex_bridge, "handle_layout_action", return_value=result) as handler:
                asyncio.run(exercise())
            handler.assert_called_once()
            ack = next(item for item in ws.sent if item.get("action") == "trigger_ack")
            self.assertFalse(ack["ok"])
            self.assertEqual(ack["type"], "codex")
            self.assertEqual(ack["slot"], 2)
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)

    def test_wifi_long_press_routes_saved_codex_key(self):
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        ws = FakeWebSocket([
            {"action": "pair", "secret": "ABC123"},
            {"action": "trigger_slot_long", "id": "codex-bind-1"},
        ], remote_address=("192.168.1.24", 43218))
        layouts = {"layouts": [{"pages": [{"slots": [{
            "key": {"id": "codex-bind-1", "type": "codex", "codex": {
                "action": "focus_task", "slot": 4, "long_press_action": "bind_current_task"
            }}
        }]}]}]}
        result = {"action": "codex_bind_current_slot_ack", "ok": True, "slot": 4, "binding": {"slot": 4}}
        try:
            with mock.patch.object(server.layouts_loader, "load", return_value=layouts), \
                    mock.patch.object(server.codex_bridge, "handle_layout_long_action", return_value=result) as handler:
                asyncio.run(server.handle_client(ws))
            handler.assert_called_once()
            ack = next(item for item in ws.sent if item.get("action") == "codex_bind_current_slot_ack")
            self.assertTrue(ack["ok"])
            self.assertEqual(ack["slot"], 4)
        finally:
            server.SECRET_CODE = old_code

    def test_usb_long_press_routes_saved_codex_key(self):
        ws = FakeWebSocket([], remote_address=("127.0.0.1", 43219))
        result = {"action": "codex_bind_current_slot_ack", "ok": True, "slot": 5, "binding": {"slot": 5}}

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "trigger_slot_long", "id": "codex-bind-2"})

        try:
            with mock.patch.object(server, "_codex_long_action_for_slot_message", return_value=result) as handler:
                asyncio.run(exercise())
            handler.assert_called_once()
            ack = next(item for item in ws.sent if item.get("action") == "codex_bind_current_slot_ack")
            self.assertTrue(ack["ok"])
            self.assertEqual(ack["slot"], 5)
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)


if __name__ == "__main__":
    unittest.main()
