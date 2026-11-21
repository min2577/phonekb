import asyncio
import json
import os
import tempfile
import unittest
from unittest import mock

import app_registry
import desktop_actions
import server
import usb_server


class FakeWebSocket:
    def __init__(self, messages=(), remote_address=("127.0.0.1", 40120)):
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


class DesktopActionsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = os.path.join(self.temp_dir.name, "authorized_apps.json")
        self.original_registry_path = app_registry.REGISTRY_PATH
        app_registry.REGISTRY_PATH = self.registry_path
        self.exe_path = os.path.join(self.temp_dir.name, "Code.exe")
        with open(self.exe_path, "wb") as file:
            file.write(b"MZ")

    def tearDown(self):
        app_registry.REGISTRY_PATH = self.original_registry_path
        self.temp_dir.cleanup()

    def test_authorize_quoted_executable_and_launch_by_id(self):
        app, error = app_registry.authorize_path(f'"{self.exe_path}"')
        self.assertIsNone(error)
        self.assertEqual(app["name"], "Code")
        self.assertTrue(desktop_actions.is_authorized_app(app["id"]))

        with mock.patch("desktop_actions.subprocess.Popen") as popen:
            ok, reason = desktop_actions.launch_authorized_app(app["id"])

        self.assertTrue(ok, reason)
        popen.assert_called_once_with([os.path.realpath(self.exe_path)], shell=False, close_fds=True)

    def test_rejects_non_executable_and_unknown_app_id(self):
        text_path = os.path.join(self.temp_dir.name, "notes.txt")
        with open(text_path, "w", encoding="utf-8") as file:
            file.write("not an app")

        app, error = app_registry.authorize_path(text_path)
        self.assertIsNone(app)
        self.assertEqual(error, "请先在电脑上复制 .exe 软件的路径")

        ok, reason = desktop_actions.launch_authorized_app("app_not_authorized")
        self.assertFalse(ok)
        self.assertIn("尚未授权", reason)

    def test_url_validation_only_allows_http_and_https_without_credentials(self):
        self.assertEqual(desktop_actions.validate_url("https://example.com/docs")[0], "https://example.com/docs")
        for invalid in ("file:///C:/Windows/system32", "https://name:secret@example.com", "not-a-url"):
            with self.subTest(url=invalid):
                url, error = desktop_actions.validate_url(invalid)
                self.assertIsNone(url)
                self.assertTrue(error)

    def test_clipboard_authorization_uses_the_same_registry(self):
        with mock.patch("desktop_actions.read_windows_clipboard", return_value=(self.exe_path, None)):
            app, error = desktop_actions.authorize_clipboard_app()

        self.assertIsNone(error)
        self.assertEqual(app_registry.get_app(app["id"])["path"], os.path.realpath(self.exe_path))

    def test_clipboard_url_is_validated(self):
        with mock.patch("desktop_actions.read_windows_clipboard", return_value=("https://example.com/docs", None)):
            url, error = desktop_actions.read_clipboard_url()
        self.assertIsNone(error)
        self.assertEqual(url, "https://example.com/docs")

        with mock.patch("desktop_actions.read_windows_clipboard", return_value=("file:///C:/Windows", None)):
            url, error = desktop_actions.read_clipboard_url()
        self.assertIsNone(url)
        self.assertIn("http", error)

    def test_wifi_and_usb_reject_unapproved_app_definitions(self):
        app, error = app_registry.authorize_path(self.exe_path)
        self.assertIsNone(error)
        approved_key = {"type": "app", "app": {"id": app["id"]}}
        unapproved_key = {"type": "app", "app": {"id": "app_not_authorized"}}

        self.assertIsNone(server._validate_key_definition(approved_key))
        self.assertIsNone(usb_server._validate_key_definition(approved_key))
        self.assertIn("尚未授权", server._validate_key_definition(unapproved_key))
        self.assertIn("尚未授权", usb_server._validate_key_definition(unapproved_key))
        self.assertEqual(
            server._validate_key_definition({"type": "link", "link": {"url": "file:///C:/Windows/system32"}}),
            "只支持 http 或 https 网站地址",
        )

    def test_wifi_trigger_opens_saved_website(self):
        layouts = {"layouts": [{"pages": [{"slots": [{"key": {
            "id": "website-1", "type": "link", "link": {"url": "https://example.com"}
        }}]}]}]}
        old_code = server.SECRET_CODE
        server.SECRET_CODE = "ABC123"
        ws = FakeWebSocket([
            {"action": "pair", "secret": "ABC123"},
            {"action": "trigger_slot", "id": "website-1"},
        ], remote_address=("192.168.1.20", 40121))
        try:
            with mock.patch.object(server.layouts_loader, "load", return_value=layouts), \
                    mock.patch.object(server.desktop_actions, "open_url", return_value=(True, "")) as opener:
                asyncio.run(server.handle_client(ws))
            opener.assert_called_once_with("https://example.com")
            self.assertTrue(any(item.get("action") == "trigger_ack" and item.get("ok") for item in ws.sent))
        finally:
            server.SECRET_CODE = old_code

    def test_usb_trigger_launches_saved_authorized_app(self):
        layouts = {"layouts": [{"pages": [{"slots": [{"key": {
            "id": "app-1", "type": "app", "app": {"id": "app_authorized"}
        }}]}]}]}
        ws = FakeWebSocket()

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "trigger_slot", "id": "app-1"})

        try:
            with mock.patch.object(usb_server.layouts_loader, "load", return_value=layouts), \
                    mock.patch.object(usb_server.desktop_actions, "launch_authorized_app", return_value=(True, "")) as launcher:
                asyncio.run(exercise())
            launcher.assert_called_once_with("app_authorized")
            self.assertTrue(any(item.get("action") == "trigger_ack" and item.get("ok") for item in ws.sent))
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)

    def test_usb_returns_copied_website_to_phone(self):
        ws = FakeWebSocket()

        async def exercise():
            await usb_server._process_msg(ws, {"action": "pair", "secret": ""})
            await usb_server._process_msg(ws, {"action": "read_desktop_clipboard_url"})

        try:
            with mock.patch.object(usb_server.desktop_actions, "read_clipboard_url", return_value=("https://example.com/docs", None)):
                asyncio.run(exercise())
            self.assertTrue(any(
                item.get("action") == "clipboard_url" and item.get("ok") and item.get("url") == "https://example.com/docs"
                for item in ws.sent
            ))
        finally:
            usb_server._unregister_codex_client(ws)
            usb_server._usb_sessions.pop(ws, None)
            usb_server._usb_targets.pop(ws, None)


if __name__ == "__main__":
    unittest.main()
