import unittest
from unittest import mock

import keytrigger


class KeytriggerTextTest(unittest.TestCase):
    def test_ascii_text_uses_scan_key_path(self):
        with mock.patch.object(keytrigger, "type_text_keys", return_value=True) as type_keys, \
                mock.patch.object(keytrigger, "paste_text") as paste:
            result = keytrigger.input_text("Hello 123!")
        self.assertEqual(result, {"ok": True, "method": "scan_keys", "sent": 10})
        type_keys.assert_called_once_with("Hello 123!")
        paste.assert_not_called()

    def test_chinese_text_uses_clipboard_paste(self):
        with mock.patch.object(keytrigger, "paste_text", return_value=True) as paste, \
                mock.patch.object(keytrigger, "type_text") as unicode_input:
            result = keytrigger.input_text("你好")
        self.assertEqual(result, {"ok": True, "method": "clipboard_paste", "sent": 2})
        paste.assert_called_once_with("你好")
        unicode_input.assert_not_called()

    def test_clipboard_failure_falls_back_to_unicode(self):
        with mock.patch.object(keytrigger, "paste_text", return_value=False), \
                mock.patch.object(keytrigger, "type_text", return_value=4) as unicode_input:
            result = keytrigger.input_text("你好")
        self.assertEqual(result, {"ok": True, "method": "unicode", "sent": 4})
        unicode_input.assert_called_once_with("你好")

    def test_paste_uses_ctrl_v_after_clipboard_write(self):
        with mock.patch.object(keytrigger, "_write_clipboard_text", return_value=True), \
                mock.patch.object(keytrigger, "simulate_key", return_value=True) as simulate, \
                mock.patch.object(keytrigger.time, "sleep"):
            self.assertTrue(keytrigger.paste_text("你好"))
        simulate.assert_called_once_with(["ctrl"], "v")


if __name__ == "__main__":
    unittest.main()
