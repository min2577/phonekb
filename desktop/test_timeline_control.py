import unittest
from unittest import mock

import timeline_control


class TimelineControlTests(unittest.TestCase):
    @mock.patch("timeline_control.keytrigger.simulate_key", return_value=True)
    @mock.patch("timeline_control.keytrigger.focus_window", return_value=True)
    def test_scrub_focuses_and_steps(self, focus_window, simulate_key):
        ok, error = timeline_control.execute("scrub", 3, 123)
        self.assertTrue(ok)
        self.assertEqual(error, "")
        focus_window.assert_called_once_with(123)
        self.assertEqual(simulate_key.call_count, 3)
        simulate_key.assert_called_with([], "right")

    @mock.patch("timeline_control.keytrigger.simulate_key", return_value=True)
    @mock.patch("timeline_control.keytrigger.focus_window", return_value=True)
    def test_zoom_is_clamped(self, _focus_window, simulate_key):
        ok, _ = timeline_control.execute("zoom", -99, 123)
        self.assertTrue(ok)
        self.assertEqual(simulate_key.call_count, timeline_control.MAX_STEPS_PER_MESSAGE)
        simulate_key.assert_called_with(["ctrl"], "-")

    @mock.patch("timeline_control.keytrigger.focus_window", return_value=False)
    def test_invalid_bound_window_fails(self, _focus_window):
        ok, error = timeline_control.execute("scrub", 1, 456)
        self.assertFalse(ok)
        self.assertIn("重新绑定", error)


if __name__ == "__main__":
    unittest.main()
