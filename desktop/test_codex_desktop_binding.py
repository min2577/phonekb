import tempfile
import unittest
import json
from pathlib import Path
from unittest import mock

import codex_desktop_binding


class CodexDesktopBindingsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_path = Path(self.temp_dir.name) / "bindings.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_bind_current_persists_deeplink_and_metadata(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        deeplink = "codex://threads/019f7b95-f4be-7143-918d-849d60695e34"
        with mock.patch.object(codex_desktop_binding, "_copy_current_deeplink", return_value=(deeplink, "")), \
                mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={"title": "手机键盘", "workspace": "C:/repo"}):
            result = manager.bind_current(1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["binding"]["title"], "手机键盘")
        restored = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        self.assertEqual(restored.snapshot()["1"]["thread_id"], "019f7b95-f4be-7143-918d-849d60695e34")

    def test_focus_acknowledges_immediately_after_opening_bound_deeplink(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        deeplink = "codex://threads/019f7b95-f4be-7143-918d-849d60695e34"
        with mock.patch.object(codex_desktop_binding, "_copy_current_deeplink", return_value=(deeplink, "")), \
                mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={}):
            manager.bind_current(1)
        with mock.patch.object(codex_desktop_binding, "_open_deeplink") as opener, \
                mock.patch.object(codex_desktop_binding, "_copy_current_deeplink") as verifier:
            result = manager.focus(1)
        self.assertTrue(result["ok"])
        self.assertFalse(result["verified"])
        opener.assert_called_once_with(deeplink)
        verifier.assert_not_called()
        restored = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        self.assertEqual(restored._active_slot, 1)

    def test_all_six_slots_are_supported(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        deeplink = "codex://threads/019f7b95-f4be-7143-918d-849d60695e34"
        with mock.patch.object(codex_desktop_binding, "_copy_current_deeplink", return_value=(deeplink, "")), \
                mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={}):
            for slot in range(1, 7):
                self.assertTrue(manager.bind_current(slot)["ok"])
        self.assertFalse(manager.bind_current(7)["ok"])

    def test_prefers_sidebar_title_and_syncs_renames(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        deeplink = "codex://threads/019f7b95-f4be-7143-918d-849d60695e34"
        with mock.patch.object(codex_desktop_binding, "_copy_current_deeplink", return_value=(deeplink, "")), \
                mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={"sidebar_title": "侧栏名称", "title": "首条消息"}):
            result = manager.bind_current(2)
        self.assertEqual(result["binding"]["title"], "侧栏名称")
        with mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={"sidebar_title": "侧栏新名称"}):
            self.assertEqual(manager.snapshot()["2"]["title"], "侧栏新名称")

    def test_custom_title_overrides_sidebar_until_cleared(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        deeplink = "codex://threads/019f7b95-f4be-7143-918d-849d60695e34"
        with mock.patch.object(codex_desktop_binding, "_copy_current_deeplink", return_value=(deeplink, "")), \
                mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={"sidebar_title": "侧栏名称"}):
            manager.bind_current(3)
            renamed = manager.rename(3, "我的自定义名称")
        self.assertEqual(renamed["binding"]["title"], "我的自定义名称")
        with mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={"sidebar_title": "侧栏新名称"}):
            self.assertEqual(manager.snapshot()["3"]["title"], "我的自定义名称")
            restored = manager.rename(3, "")
        self.assertEqual(restored["binding"]["title"], "侧栏新名称")

    def test_rollout_status_changes_are_detected_incrementally(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        rollout = Path(self.temp_dir.name) / "rollout.jsonl"
        started = {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-1"}}
        completed = {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "turn-1"}}
        rollout.write_text(json.dumps(started) + "\n", encoding="utf-8")
        deeplink = "codex://threads/019f7b95-f4be-7143-918d-849d60695e34"
        with mock.patch.object(codex_desktop_binding, "_copy_current_deeplink", return_value=(deeplink, "")), \
                mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={"sidebar_title": "任务", "rollout_path": str(rollout)}):
            result = manager.bind_current(1)
        self.assertEqual(result["binding"]["state"], "running")
        with rollout.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(completed) + "\n")
        changed = manager.refresh_statuses()
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]["state"], "completed")

    def test_visible_task_state_cannot_complete_another_running_binding(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        rollout = Path(self.temp_dir.name) / "rollout.jsonl"
        started = {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-1"}}
        rollout.write_text(json.dumps(started) + "\n", encoding="utf-8")
        manager._bindings["1"] = {
            "slot": 1,
            "thread_id": "thread-1",
            "rollout_path": str(rollout),
            "state": "running",
            "detail": "Codex 正在处理",
        }
        manager._active_slot = 1
        manager.refresh_statuses()
        with mock.patch.object(codex_desktop_binding.codex_voice, "detect_codex_turn_state", return_value="completed", create=True) as desktop_state:
            changed = manager.refresh_statuses()
        self.assertEqual(changed, [])
        self.assertEqual(manager._bindings["1"]["state"], "running")
        desktop_state.assert_not_called()

    def test_snapshot_refreshes_each_binding_from_its_rollout(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        rollout = Path(self.temp_dir.name) / "rollout.jsonl"
        started = {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-1"}}
        completed = {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "turn-1"}}
        rollout.write_text(json.dumps(started) + "\n", encoding="utf-8")
        manager._bindings["1"] = {
            "slot": 1,
            "thread_id": "thread-1",
            "rollout_path": str(rollout),
            "state": "running",
            "detail": "Codex 正在处理",
        }
        self.assertEqual(manager.snapshot()["1"]["state"], "running")
        with rollout.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(completed) + "\n")
        self.assertEqual(manager.snapshot()["1"]["state"], "completed")

    def test_task_complete_with_error_is_failed(self):
        event = {
            "timestamp": "2026-07-30T00:00:00Z",
            "type": "event_msg",
            "payload": {
                "type": "task_complete",
                "turn_id": "turn-failed",
                "error": {"message": "Selected model is at capacity"},
            },
        }
        status = codex_desktop_binding._status_from_line(json.dumps(event).encode("utf-8"))
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["detail"], "Selected model is at capacity")

    def test_unanswered_user_input_request_is_waiting_input(self):
        rollout = Path(self.temp_dir.name) / "rollout.jsonl"
        events = [
            {"timestamp": "2026-07-30T00:00:00Z", "type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-1"}},
            {
                "timestamp": "2026-07-30T00:00:01Z",
                "type": "response_item",
                "payload": {"type": "function_call", "name": "request_user_input", "call_id": "call-input-1", "arguments": "{}"},
            },
        ]
        rollout.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")

        status = codex_desktop_binding._latest_rollout_status(rollout)

        self.assertEqual(status["state"], "waiting_input")
        self.assertEqual(status["attention_id"], "call-input-1")
        self.assertEqual(status["turn_id"], "turn-1")

    def test_user_input_answer_restores_running_state_incrementally(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        rollout = Path(self.temp_dir.name) / "rollout.jsonl"
        started = {"timestamp": "2026-07-30T00:00:00Z", "type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-1"}}
        request = {
            "timestamp": "2026-07-30T00:00:01Z",
            "type": "response_item",
            "payload": {"type": "function_call", "name": "request_user_input", "call_id": "call-input-1", "arguments": "{}"},
        }
        answer = {
            "timestamp": "2026-07-30T00:00:02Z",
            "type": "response_item",
            "payload": {"type": "function_call_output", "call_id": "call-input-1", "output": "{}"},
        }
        rollout.write_text(json.dumps(started) + "\n" + json.dumps(request) + "\n", encoding="utf-8")
        manager._bindings["1"] = {
            "slot": 1,
            "thread_id": "thread-1",
            "rollout_path": str(rollout),
            "state": "running",
            "detail": "Codex 正在处理",
        }

        self.assertEqual(manager.snapshot()["1"]["state"], "waiting_input")
        with rollout.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(answer) + "\n")
        changed = manager.refresh_statuses()

        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]["state"], "running")
        self.assertEqual(changed[0]["attention_id"], "")

    def test_answering_one_of_multiple_requests_keeps_latest_request_waiting(self):
        rollout = Path(self.temp_dir.name) / "rollout.jsonl"
        events = [
            {"timestamp": "2026-07-30T00:00:00Z", "type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-1"}},
            {"timestamp": "2026-07-30T00:00:01Z", "type": "response_item", "payload": {"type": "function_call", "name": "request_user_input", "call_id": "call-1"}},
            {"timestamp": "2026-07-30T00:00:02Z", "type": "response_item", "payload": {"type": "function_call", "name": "request_user_input", "call_id": "call-2"}},
            {"timestamp": "2026-07-30T00:00:03Z", "type": "response_item", "payload": {"type": "function_call_output", "call_id": "call-1", "output": "{}"}},
        ]
        rollout.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")

        status = codex_desktop_binding._latest_rollout_status(rollout)

        self.assertEqual(status["state"], "waiting_input")
        self.assertEqual(status["attention_id"], "call-2")

    def test_set_reasoning_focuses_bound_slot_and_persists_verified_value(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        deeplink = "codex://threads/019f7b95-f4be-7143-918d-849d60695e34"
        with mock.patch.object(codex_desktop_binding, "_copy_current_deeplink", return_value=(deeplink, "")), \
                mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={"reasoning_effort": "medium"}):
            manager.bind_current(4)
        with mock.patch.object(manager, "focus", return_value={"ok": True}) as focus, \
                mock.patch.object(codex_desktop_binding, "_select_desktop_reasoning", return_value={"ok": True, "label": "5.6 Sol 中"}), \
                mock.patch.object(codex_desktop_binding, "_thread_metadata", return_value={"reasoning_effort": "medium"}):
            result = manager.set_reasoning(4, "medium")
        self.assertTrue(result["ok"])
        self.assertEqual(result["binding"]["reasoning_effort"], "medium")
        focus.assert_called_once_with(4)

    def test_set_reasoning_requires_a_bound_slot(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        result = manager.set_reasoning(5, "high")
        self.assertFalse(result["ok"])
        self.assertIn("绑定", result["msg"])

    def test_snapshot_marks_active_bound_slot_as_attention(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        manager._bindings["1"] = {
            "slot": 1,
            "thread_id": "thread-1",
            "title": "等待审批",
            "custom_title": "等待审批",
            "state": "running",
            "detail": "Codex 正在处理",
        }
        manager._active_slot = 1
        manager._approval_controller = mock.Mock()
        manager._approval_controller.scan.return_value = {
            "pending": True,
            "ambiguous": False,
            "fingerprint": "fingerprint-1",
            "msg": "Codex 正在等待批准终端操作",
        }
        snapshot = manager.snapshot()
        self.assertEqual(snapshot["1"]["state"], "attention")
        self.assertEqual(snapshot["1"]["approval"]["fingerprint"], "fingerprint-1")

    def test_resolve_approval_requires_matching_bound_task_and_fingerprint(self):
        manager = codex_desktop_binding.CodexDesktopBindings(self.state_path)
        manager._bindings["2"] = {"slot": 2, "thread_id": "thread-2", "title": "任务 2"}
        manager._active_slot = 2
        pending = {
            "pending": True,
            "ambiguous": False,
            "fingerprint": "fingerprint-2",
            "msg": "Codex 正在等待批准终端操作",
        }
        cleared = {"pending": False, "ambiguous": False, "fingerprint": "", "msg": ""}
        manager._approval_controller = mock.Mock()
        manager._approval_controller.scan.side_effect = [pending, cleared]
        manager._approval_controller.resolve.return_value = {"ok": True, "msg": "已允许一次"}
        result = manager.resolve_approval(2, "thread-2", "fingerprint-2", "approve")
        self.assertTrue(result["ok"])
        manager._approval_controller.resolve.assert_called_once_with("approve", "fingerprint-2")
        self.assertFalse(result["approval"]["pending"])


if __name__ == "__main__":
    unittest.main()
