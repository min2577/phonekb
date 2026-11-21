import asyncio
import json
import unittest
from unittest import mock

import keytrigger
import server
import usb_server


class FakeWebSocket:
    def __init__(self, messages, remote_address=("127.0.0.1", 43220)):
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


def _ack(ws, action):
    matches = [item for item in ws.sent if item.get("action") == action]
    if not matches:
        raise AssertionError("missing ack: " + action)
    return matches[-1]


class WifiZhipuVoiceTest(unittest.TestCase):
    def setUp(self):
        self._old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"

    def tearDown(self):
        server.SECRET_CODE = self._old_code

    def _pair_then(self, msgs):
        return FakeWebSocket(
            [{"action": "pair", "secret": "ABC123"}] + msgs,
            remote_address=("192.168.1.30", 43220),
        )

    def test_start_holds_rctrl_after_focusing_codex(self):
        ws = self._pair_then([{"action": "codex_zhipu_start"}])
        focused = {"ok": True, "stage": "focused", "title": "Codex"}
        with mock.patch.object(server.codex_voice, "focus_codex_composer", return_value=focused), \
                mock.patch.object(server.codex_voice.keytrigger, "key_down", return_value=True) as key_down:
            asyncio.run(server.handle_client(ws))
        key_down.assert_called_once_with("rctrl")
        ack = _ack(ws, "codex_zhipu_start_ack")
        self.assertTrue(ack["ok"])
        self.assertEqual(ack["stage"], "listening")
        self.assertEqual(ack["title"], "Codex")

    def test_start_skips_key_down_when_focus_fails(self):
        ws = self._pair_then([{"action": "codex_zhipu_start"}])
        failed = {"ok": False, "stage": "focused", "msg": "没有找到 Codex 对话输入框"}
        with mock.patch.object(server.codex_voice, "focus_codex_composer", return_value=failed), \
                mock.patch.object(server.codex_voice.keytrigger, "key_down") as key_down:
            asyncio.run(server.handle_client(ws))
        key_down.assert_not_called()
        ack = _ack(ws, "codex_zhipu_start_ack")
        self.assertFalse(ack["ok"])
        self.assertEqual(ack["stage"], "locate_codex")
        self.assertIn("没有找到", ack["msg"])

    def test_start_reports_key_down_failure(self):
        ws = self._pair_then([{"action": "codex_zhipu_start"}])
        focused = {"ok": True, "stage": "focused", "title": "Codex"}
        with mock.patch.object(server.codex_voice, "focus_codex_composer", return_value=focused), \
                mock.patch.object(server.codex_voice.keytrigger, "key_down", return_value=False):
            asyncio.run(server.handle_client(ws))
        ack = _ack(ws, "codex_zhipu_start_ack")
        self.assertFalse(ack["ok"])
        self.assertEqual(ack["stage"], "key_down")
        self.assertEqual(ack["msg"], "右 Ctrl 按下失败")

    def test_stop_releases_rctrl(self):
        ws = self._pair_then([{"action": "codex_zhipu_stop"}])
        with mock.patch.object(server.codex_voice.keytrigger, "key_up", return_value=True) as key_up:
            asyncio.run(server.handle_client(ws))
        self.assertGreaterEqual(key_up.call_count, 1)
        key_up.assert_any_call("rctrl")
        ack = _ack(ws, "codex_zhipu_stop_ack")
        self.assertTrue(ack["ok"])
        self.assertEqual(ack["stage"], "released")

    def test_stop_reports_key_up_failure(self):
        ws = self._pair_then([{"action": "codex_zhipu_stop"}])
        with mock.patch.object(server.codex_voice.keytrigger, "key_up", return_value=False):
            asyncio.run(server.handle_client(ws))
        ack = _ack(ws, "codex_zhipu_stop_ack")
        self.assertFalse(ack["ok"])
        self.assertEqual(ack["stage"], "key_up")
        self.assertEqual(ack["msg"], "右 Ctrl 释放失败")

    def test_submit_enter_focuses_codex_and_returns_ack(self):
        ws = self._pair_then([{"action": "codex_submit_enter"}])
        submitted = {"ok": True, "stage": "submitted", "title": "Codex"}
        with mock.patch.object(server.codex_voice, "submit_codex_composer", return_value=submitted) as submit:
            asyncio.run(server.handle_client(ws))
        submit.assert_called_once_with(0)
        ack = _ack(ws, "codex_submit_enter_ack")
        self.assertTrue(ack["ok"])
        self.assertEqual(ack["stage"], "submitted")

    def test_disconnect_always_releases_rctrl(self):
        ws = self._pair_then([{"action": "codex_zhipu_start"}])
        focused = {"ok": True, "stage": "focused", "title": "Codex"}
        with mock.patch.object(server.codex_voice, "focus_codex_composer", return_value=focused), \
                mock.patch.object(server.codex_voice.keytrigger, "key_down", return_value=True), \
                mock.patch.object(server.keytrigger, "key_up", return_value=True) as key_up:
            asyncio.run(server.handle_client(ws))
        key_up.assert_any_call("rctrl")


class UsbZhipuVoiceTest(unittest.TestCase):
    def _exercise(self, msgs):
        ws = FakeWebSocket([], remote_address=("127.0.0.1", 43221))

        async def run():
            for msg in [{"action": "pair", "secret": ""}] + msgs:
                await usb_server._process_msg(ws, msg)

        return ws, run

    def _cleanup(self, ws):
        usb_server._unregister_codex_client(ws)
        usb_server._usb_sessions.pop(ws, None)
        usb_server._usb_targets.pop(ws, None)

    def test_usb_start_holds_rctrl_after_focus(self):
        ws, run = self._exercise([{"action": "codex_zhipu_start"}])
        focused = {"ok": True, "stage": "focused", "title": "Codex"}
        try:
            with mock.patch.object(usb_server.codex_voice, "focus_codex_composer", return_value=focused), \
                    mock.patch.object(usb_server.codex_voice.keytrigger, "key_down", return_value=True) as key_down:
                asyncio.run(run())
            key_down.assert_called_once_with("rctrl")
            ack = _ack(ws, "codex_zhipu_start_ack")
            self.assertTrue(ack["ok"])
            self.assertEqual(ack["stage"], "listening")
        finally:
            self._cleanup(ws)

    def test_usb_stop_releases_rctrl(self):
        ws, run = self._exercise([{"action": "codex_zhipu_stop"}])
        try:
            with mock.patch.object(usb_server.codex_voice.keytrigger, "key_up", return_value=True) as key_up:
                asyncio.run(run())
            self.assertGreaterEqual(key_up.call_count, 1)
            key_up.assert_any_call("rctrl")
            ack = _ack(ws, "codex_zhipu_stop_ack")
            self.assertTrue(ack["ok"])
            self.assertEqual(ack["stage"], "released")
        finally:
            self._cleanup(ws)

    def test_usb_submit_enter_uses_captured_target(self):
        ws, run = self._exercise([{"action": "codex_submit_enter"}])
        usb_server._usb_targets[ws] = 88
        submitted = {"ok": True, "stage": "submitted", "title": "Codex"}
        try:
            with mock.patch.object(usb_server.codex_voice, "submit_codex_composer", return_value=submitted) as submit:
                asyncio.run(run())
            submit.assert_called_once_with(88)
            self.assertTrue(_ack(ws, "codex_submit_enter_ack")["ok"])
        finally:
            self._cleanup(ws)


class CodexVoiceModuleTest(unittest.TestCase):
    def test_start_module_calls_key_down_on_rctrl(self):
        import codex_voice
        focused = {"ok": True, "stage": "focused", "title": "Codex"}
        with mock.patch.object(codex_voice, "focus_codex_composer", return_value=focused), \
                mock.patch.object(codex_voice.keytrigger, "key_down", return_value=True) as key_down:
            result = codex_voice.start_zhipu_dictation()
        key_down.assert_called_once_with("rctrl")
        self.assertTrue(result["ok"])
        self.assertEqual(result["stage"], "listening")

    def test_stop_module_releases_rctrl(self):
        import codex_voice
        with mock.patch.object(codex_voice.keytrigger, "key_up", return_value=True) as key_up:
            result = codex_voice.stop_zhipu_dictation()
        key_up.assert_called_once_with("rctrl")
        self.assertTrue(result["ok"])
        self.assertEqual(result["stage"], "released")

    def test_submit_module_focuses_target_before_pressing_enter(self):
        import codex_voice
        focused = {"ok": True, "stage": "focused", "title": "Codex", "hwnd": 99}
        with mock.patch.object(codex_voice, "focus_codex_composer", return_value=focused) as focus, \
                mock.patch.object(codex_voice.keytrigger, "simulate_key", return_value=True) as simulate:
            result = codex_voice.submit_codex_composer(99)
        focus.assert_called_once_with(99)
        simulate.assert_called_once_with([], "enter")
        self.assertTrue(result["ok"])
        self.assertEqual(result["stage"], "submitted")

    def test_submit_module_does_not_press_enter_when_focus_fails(self):
        import codex_voice
        failed = {"ok": False, "msg": "没有找到 Codex 对话输入框"}
        with mock.patch.object(codex_voice, "focus_codex_composer", return_value=failed), \
                mock.patch.object(codex_voice.keytrigger, "simulate_key") as simulate:
            result = codex_voice.submit_codex_composer()
        simulate.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "locate_codex")


if __name__ == "__main__":
    unittest.main()
