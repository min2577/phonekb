import unittest
from types import SimpleNamespace
from unittest import mock

import codex_voice


class CodexVoiceTest(unittest.TestCase):
    def test_current_edit_prosemirror_is_a_composer(self):
        control = SimpleNamespace(element_info=SimpleNamespace(
            control_type="Edit",
            class_name="ProseMirror ProseMirror-focused",
        ))
        self.assertTrue(codex_voice._is_codex_composer(control))

    def test_prosemirror_css_wrapper_is_not_a_composer(self):
        control = SimpleNamespace(element_info=SimpleNamespace(
            control_type="Group",
            class_name="root [&_.ProseMirror]:h-auto",
        ))
        self.assertFalse(codex_voice._is_codex_composer(control))

    def test_legacy_group_prosemirror_is_still_a_composer(self):
        control = SimpleNamespace(element_info=SimpleNamespace(
            control_type="Group",
            class_name="ProseMirror legacy-composer",
        ))
        self.assertTrue(codex_voice._is_codex_composer(control))

    def test_dictation_focuses_composer_before_typing(self):
        focused = {"ok": True, "hwnd": 123, "title": "ChatGPT", "looks_like_codex": True}
        with mock.patch.object(codex_voice, "focus_codex_composer", return_value=focused) as focus, \
                mock.patch.object(codex_voice.keytrigger, "type_text", return_value=6) as type_text:
            result = codex_voice.type_into_target(123, "你好", append_space=True)
        focus.assert_called_once_with(123)
        type_text.assert_called_once_with("你好 ")
        self.assertTrue(result["ok"])
        self.assertEqual(result["chars"], 3)

    def test_dictation_does_not_type_when_composer_is_missing(self):
        failed = {"ok": False, "msg": "没有找到 Codex 对话输入框"}
        with mock.patch.object(codex_voice, "focus_codex_composer", return_value=failed), \
                mock.patch.object(codex_voice.keytrigger, "type_text") as type_text:
            result = codex_voice.type_into_target(0, "不要误输入")
        type_text.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "locate_codex")

    def test_fixed_phrase_is_entered_atomically(self):
        typed = {"ok": True, "stage": "done", "sent": 14, "chars": 14, "title": "Codex"}
        with mock.patch.object(codex_voice, "type_into_target", return_value=typed) as type_into:
            result = codex_voice.enter_test_phrase()
        type_into.assert_called_once_with(0, codex_voice.CODEX_TEST_PHRASE, False)
        self.assertTrue(result["ok"])

    def test_open_new_task_invokes_only_the_topmost_matching_button(self):
        top_button = mock.Mock()
        top_button.window_text.return_value = "新建任务"
        top_button.is_visible.return_value = True
        top_button.is_enabled.return_value = True
        top_button.rectangle.return_value = SimpleNamespace(top=100)
        lower_button = mock.Mock()
        lower_button.window_text.return_value = "新建任务"
        lower_button.is_visible.return_value = True
        lower_button.is_enabled.return_value = True
        lower_button.rectangle.return_value = SimpleNamespace(top=500)
        window = mock.Mock(handle=123)
        window.descendants.return_value = [lower_button, top_button]
        window.window_text.return_value = "ChatGPT"

        with mock.patch.object(codex_voice, "_locate_codex_composer", return_value=(window, mock.Mock())), \
                mock.patch.object(codex_voice, "_activate_window") as activate:
            result = codex_voice.open_new_task()

        activate.assert_called_once_with(123)
        top_button.invoke.assert_called_once_with()
        lower_button.invoke.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertEqual(result["stage"], "new_task_opened")

if __name__ == "__main__":
    unittest.main()
