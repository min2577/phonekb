import json
import os
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

from codex_bridge import CodexBridge, _find_codex


class CodexBridgeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fake = self.root / "fake_codex.py"
        self.fake.write_text(
            textwrap.dedent(
                """
                import json
                import sys
                import time

                prompt = sys.argv[-1]
                print(json.dumps({"type": "thread.started", "thread_id": "session-test-1"}), flush=True)
                print(json.dumps({"type": "turn.started"}), flush=True)
                if "SLOW" in prompt:
                    time.sleep(5)
                print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "PHONEKB_BRIDGE_OK"}}), flush=True)
                print(json.dumps({"type": "turn.completed"}), flush=True)
                """
            ).strip(),
            encoding="utf-8",
        )
        self.state_path = self.root / "state.json"
        self.bridge = CodexBridge(
            state_path=self.state_path,
            codex_command=[sys.executable, str(self.fake)],
            workspace=self.root,
        )
        self.events = []
        self.bridge.register_client("test", self.events.append)

    def tearDown(self):
        self.temp.cleanup()

    def test_create_streams_real_status_and_result(self):
        ack = self.bridge.handle_message({
            "action": "codex_create",
            "slot": 1,
            "prompt": "reply",
            "reasoning_effort": "high",
            "workflow_id": "review",
        })
        self.assertTrue(ack["ok"], ack)
        task = self.bridge.wait_for_terminal(ack["task"]["task_id"], timeout=10)
        self.assertIsNotNone(task)
        self.assertEqual(task["state"], "completed")
        self.assertEqual(task["session_id"], "session-test-1")
        self.assertEqual(task["result"], "PHONEKB_BRIDGE_OK")
        deadline = time.time() + 1
        while time.time() < deadline and not any(event.get("action") == "codex_result" for event in self.events):
            time.sleep(0.01)
        self.assertTrue(any(event.get("action") == "codex_result" for event in self.events))
        self.assertTrue(self.state_path.is_file())

    def test_cancel_stops_bridge_owned_process(self):
        ack = self.bridge.handle_message({"action": "codex_create", "slot": 2, "prompt": "SLOW"})
        self.assertTrue(ack["ok"], ack)
        deadline = time.time() + 5
        while time.time() < deadline:
            task = self.bridge.snapshot()["tasks"][1]
            if task["state"] == "running":
                break
            time.sleep(0.05)
        cancel = self.bridge.handle_message({"action": "codex_cancel", "task_id": ack["task"]["task_id"]})
        self.assertTrue(cancel["ok"], cancel)
        task = self.bridge.wait_for_terminal(ack["task"]["task_id"], timeout=10)
        self.assertEqual(task["state"], "cancelled")

    def test_rejects_invalid_inputs(self):
        self.assertFalse(self.bridge.handle_message({"action": "codex_create", "slot": 0, "prompt": "x"})["ok"])
        self.assertFalse(self.bridge.handle_message({"action": "codex_create", "slot": 1, "prompt": ""})["ok"])
        self.assertFalse(self.bridge.handle_message({"action": "codex_set_defaults", "reasoning_effort": "extreme"})["ok"])
        self.assertTrue(self.bridge.handle_message({"action": "codex_set_defaults", "reasoning_effort": "xhigh"})["ok"])

    def test_layout_codex_actions_map_to_bridge_protocol(self):
        with mock.patch.object(self.bridge.desktop_bindings, "focus", return_value={"ok": True, "action": "codex_focus_slot_ack"}) as focus:
            result = self.bridge.handle_layout_action({"type": "codex", "codex": {"action": "focus_task", "slot": 2}})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["layout_action"], "focus_task")
        focus.assert_called_once_with(2)

    def test_focus_echoes_request_id(self):
        expected = {"action": "codex_focus_slot_ack", "ok": True, "slot": 2}
        with mock.patch.object(self.bridge.desktop_bindings, "focus", return_value=expected):
            result = self.bridge.handle_message({
                "action": "codex_focus_slot",
                "slot": 2,
                "request_id": "focus-2-123",
            })
        self.assertEqual(result["request_id"], "focus-2-123")

    def test_open_new_task_routes_to_desktop_and_echoes_request_id(self):
        expected = {"ok": True, "stage": "new_task_opened"}
        with mock.patch("codex_bridge.codex_voice.open_new_task", return_value=expected) as open_new_task:
            result = self.bridge.handle_message({
                "action": "codex_open_new_task",
                "request_id": "new-task-123",
            })
        open_new_task.assert_called_once_with()
        self.assertEqual(result["action"], "codex_open_new_task_ack")
        self.assertEqual(result["request_id"], "new-task-123")
        self.assertTrue(result["ok"])

    def test_layout_codex_approval_failure_is_not_hidden(self):
        result = self.bridge.handle_layout_action({"type": "codex", "codex": {"action": "approve", "slot": 1}})
        self.assertFalse(result["ok"])
        self.assertIn("请先长按任务槽绑定 Codex 任务", result["msg"])

    def test_approval_message_routes_to_desktop_binding(self):
        expected = {
            "action": "codex_approve_ack",
            "ok": True,
            "slot": 2,
            "msg": "已允许一次",
            "approval": {"pending": False},
        }
        with mock.patch.object(self.bridge.desktop_bindings, "resolve_approval", return_value=expected) as resolver:
            result = self.bridge.handle_message({
                "action": "codex_approve",
                "slot": 2,
                "thread_id": "thread-2",
                "fingerprint": "approval-2",
            })
        self.assertTrue(result["ok"])
        resolver.assert_called_once_with(2, "thread-2", "approval-2", "approve")
        self.assertTrue(any(event.get("action") == "codex_approval_status" for event in self.events))

    def test_layout_codex_rejects_invalid_action_and_slot(self):
        invalid_action = self.bridge.handle_layout_action({"type": "codex", "codex": {"action": "model", "slot": 1}})
        invalid_slot = self.bridge.handle_layout_action({"type": "codex", "codex": {"action": "focus_task", "slot": 9}})
        self.assertFalse(invalid_action["ok"])
        self.assertFalse(invalid_slot["ok"])

    def test_layout_codex_long_press_binds_current_task(self):
        expected = {
            "action": "codex_bind_current_slot_ack",
            "ok": True,
            "slot": 3,
            "binding": {"slot": 3, "thread_id": "thread-3"},
        }
        with mock.patch.object(self.bridge.desktop_bindings, "bind_current", return_value=expected) as bind_current:
            result = self.bridge.handle_layout_long_action({
                "type": "codex",
                "codex": {"action": "focus_task", "slot": 3, "long_press_action": "bind_current_task"},
            })
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["layout_long_action"], "bind_current_task")
        bind_current.assert_called_once_with(3)

    def test_layout_codex_long_press_can_be_disabled(self):
        result = self.bridge.handle_layout_long_action({
            "type": "codex",
            "codex": {"action": "focus_task", "slot": 1, "long_press_action": ""},
        })
        self.assertFalse(result["ok"])
        self.assertIn("没有启用", result["msg"])

    def test_resume_uses_global_workspace_and_sandbox_options(self):
        command, error = self.bridge._build_command(
            "continue",
            "medium",
            "gpt-test",
            session_id="session-test-1",
        )
        self.assertIsNone(error)
        exec_index = command.index("exec")
        resume_index = command.index("resume")
        self.assertLess(command.index("-C"), exec_index)
        self.assertLess(command.index("-s"), exec_index)
        self.assertEqual(command[resume_index + 1], "session-test-1")
        self.assertEqual(command[-1], "continue")

    def test_finds_a_launchable_codex_prefix(self):
        prefix = _find_codex()
        self.assertTrue(prefix, "Codex CLI should be discoverable on the test machine")
        self.assertIsInstance(prefix, list)
        self.assertTrue(prefix[0].lower().endswith((".exe", "node.exe")))


if __name__ == "__main__":
    unittest.main()
