import unittest
from unittest import mock

import codex_approval


class FakeRectangle:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom


class FakeInfo:
    def __init__(self, label, index, visible=True, enabled=True):
        self.visible = visible
        self.enabled = enabled
        self.automation_id = "button-" + str(index)
        self.control_id = index
        self.process_id = 10
        self.rectangle = FakeRectangle(index * 10, 20, index * 10 + 8, 30)


class FakeButton:
    def __init__(self, label, index, visible=True, enabled=True):
        self.label = label
        self.element_info = FakeInfo(label, index, visible, enabled)
        self.invoked = False

    def window_text(self):
        return self.label

    def invoke(self):
        self.invoked = True


class FakeWindow:
    def __init__(self, buttons, handle=77):
        self.buttons = buttons
        self.handle = handle
        self.focused = False

    def descendants(self, control_type=None):
        return list(self.buttons) if control_type == "Button" else []

    def set_focus(self):
        self.focused = True


class CodexApprovalControllerTest(unittest.TestCase):
    def test_detects_chinese_approval_pair(self):
        window = FakeWindow([FakeButton("拒绝", 1), FakeButton("允许一次", 2)])
        status = codex_approval.CodexApprovalController(lambda: [window]).scan()
        self.assertTrue(status["pending"])
        self.assertTrue(status["fingerprint"])

    def test_detects_english_approval_pair(self):
        window = FakeWindow([FakeButton("Reject", 1), FakeButton("Allow once", 2)])
        status = codex_approval.CodexApprovalController(lambda: [window]).scan()
        self.assertTrue(status["pending"])

    def test_ignores_disabled_button(self):
        window = FakeWindow([FakeButton("拒绝", 1), FakeButton("允许一次", 2, enabled=False)])
        status = codex_approval.CodexApprovalController(lambda: [window]).scan()
        self.assertFalse(status["pending"])
        self.assertTrue(status["ambiguous"])

    def test_multiple_groups_are_ambiguous(self):
        first = FakeWindow([FakeButton("拒绝", 1), FakeButton("允许一次", 2)], 77)
        second = FakeWindow([FakeButton("Reject", 3), FakeButton("Allow once", 4)], 88)
        status = codex_approval.CodexApprovalController(lambda: [first, second]).scan()
        self.assertFalse(status["pending"])
        self.assertTrue(status["ambiguous"])

    def test_rejects_stale_fingerprint(self):
        window = FakeWindow([FakeButton("拒绝", 1), FakeButton("允许一次", 2)])
        result = codex_approval.CodexApprovalController(lambda: [window]).resolve("approve", "stale")
        self.assertFalse(result["ok"])
        self.assertIn("变化", result["msg"])

    def test_approve_invokes_exact_button_and_verifies_disappearance(self):
        reject = FakeButton("拒绝", 1)
        approve = FakeButton("允许一次", 2)
        window = FakeWindow([reject, approve])
        calls = {"count": 0}

        def windows():
            calls["count"] += 1
            return [window] if calls["count"] <= 2 else []

        controller = codex_approval.CodexApprovalController(windows)
        fingerprint = controller.scan()["fingerprint"]
        with mock.patch.object(codex_approval.codex_voice, "_activate_window"):
            result = controller.resolve("approve", fingerprint)
        self.assertTrue(result["ok"])
        self.assertTrue(approve.invoked)
        self.assertFalse(reject.invoked)


if __name__ == "__main__":
    unittest.main()
