"""Focused interaction tests for the single-layer native control editor."""
import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6 import QtCore, QtGui, QtWidgets

from pages import editor_page
from pages.editor_page import CanvasView, EditorPage, InspectorPanel, _binding_display


def _state():
    return {
        "version": 3,
        "activeLayoutId": "test",
        "layouts": [{
            "id": "test", "name": "Test", "background": {"id": "mobile-dark"},
            "controls": [{
                "id": "stick", "type": "leftStick", "label": "Move",
                "x": 25.0, "y": 60.0, "size": 100.0, "opacity": 100.0,
                "visible": True, "locked": False,
                "bindings": {
                    "up": {"type": "key", "key": "w"},
                    "left": {"type": "key", "key": "a"},
                    "down": {"type": "key", "key": "s"},
                    "right": {"type": "key", "key": "d"},
                },
                "appearance": {"shape": "round"},
            }],
        }],
    }


class CanvasViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.state = _state()
        self.canvas = CanvasView()
        self.canvas.set_state(self.state)
        self.canvas.resize(1200, 600)
        self.canvas.show()
        self.app.processEvents()
        self.canvas.rebuild()
        self.app.processEvents()

    def tearDown(self):
        self.canvas.close()
        self.canvas.deleteLater()
        self.app.processEvents()

    @staticmethod
    def _drag(item, dx, dy=0):
        local = QtCore.QPointF(item.rect().center())
        global_start = QtCore.QPointF(item.mapToGlobal(item.rect().center()))
        item.mousePressEvent(QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonPress, local, global_start,
            QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier,
        ))
        offset = QtCore.QPointF(dx, dy)
        item.mouseMoveEvent(QtGui.QMouseEvent(
            QtCore.QEvent.MouseMove, local + offset, global_start + offset,
            QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier,
        ))
        item.mouseReleaseEvent(QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonRelease, local, global_start + offset,
            QtCore.Qt.LeftButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier,
        ))

    def test_items_scale_with_phone_frame(self):
        wide_frame = self.canvas._phone_rect.width()
        wide_item = self.canvas._control_items["stick"].width()
        self.canvas.resize(600, 300)
        self.app.processEvents()
        self.assertAlmostEqual(
            self.canvas._control_items["stick"].width() / wide_item,
            self.canvas._phone_rect.width() / wide_frame,
            delta=0.02,
        )

    def test_drag_updates_model_and_widget_geometry_immediately(self):
        item = self.canvas._control_items["stick"]
        control = self.state["layouts"][0]["controls"][0]
        original_geometry = item.geometry()
        original_x = control["x"]
        snapshots = []
        self.canvas.item_drag_started.connect(lambda: snapshots.append(control["x"]))
        self._drag(item, 120)
        self.assertEqual(snapshots, [original_x])
        self.assertGreater(control["x"], original_x)
        self.assertGreater(item.geometry().x(), original_geometry.x())

    def test_hidden_control_remains_editable_as_a_dimmed_ghost(self):
        control = self.state["layouts"][0]["controls"][0]
        control["visible"] = False
        self.canvas.update_control_visual(control)
        item = self.canvas._control_items["stick"]
        self.assertTrue(item.isVisible())
        self.assertAlmostEqual(item._visual_opacity, 0.18)
        self.assertFalse(item.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents))

    def test_binding_display_supports_shortcuts(self):
        self.assertEqual(_binding_display({"type": "key", "key": "space"}), "Space")
        self.assertEqual(
            _binding_display({"type": "shortcut", "modifiers": ["ctrl", "shift"], "key": "s"}),
            "Ctrl + Shift + S",
        )

    def test_editor_undo_restores_position_from_before_drag(self):
        with mock.patch.object(editor_page.gamepad_layouts_loader, "load", return_value=_state()), \
                mock.patch.object(editor_page.gamepad_layouts_loader, "load_component_presets", return_value={"version": 2, "presets": []}):
            page = EditorPage()
            page.resize(1500, 700)
            page.show()
            page.refresh()
            self.app.processEvents()
            control = page._active_layout()["controls"][0]
            original_x = control["x"]
            self._drag(page._canvas._control_items["stick"], 120)
            self.assertGreater(control["x"], original_x)
            self.assertEqual(len(page._history), 1)
            page._undo()
            self.assertEqual(page._active_layout()["controls"][0]["x"], original_x)
            page.close()
            page.deleteLater()
            self.app.processEvents()

    def test_new_component_gets_direct_default_bindings(self):
        with mock.patch.object(editor_page.gamepad_layouts_loader, "load", return_value=_state()), \
                mock.patch.object(editor_page.gamepad_layouts_loader, "load_component_presets", return_value={"version": 2, "presets": []}):
            page = EditorPage()
            page.refresh()
            page._add_control("macro")
            control = page._selected_control()
            self.assertEqual(control["bindings"]["press"]["modifiers"], ["ctrl", "shift"])
            self.assertEqual(control["bindings"]["press"]["key"], "s")
            self.assertNotIn("keys", page._active_layout())
            page.close()
            page.deleteLater()

    def test_size_editor_expands_past_legacy_limit_and_accepts_direct_input(self):
        state = _state()
        panel = InspectorPanel()
        panel.set_state(state)
        panel.set_selected_control("stick")
        self.app.processEvents()
        slider = panel.findChild(QtWidgets.QSlider, "controlSizeSlider")
        output = panel.findChild(QtWidgets.QLineEdit, "controlSizeInput")
        self.assertIsNotNone(slider)
        self.assertIsNotNone(output)
        old_maximum = slider.maximum()
        slider.setValue(old_maximum)
        self.assertGreater(slider.maximum(), old_maximum)
        output.setText("725%")
        output.editingFinished.emit()
        self.assertEqual(state["layouts"][0]["controls"][0]["size"], 725)
        panel.close()
        panel.deleteLater()
        self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
