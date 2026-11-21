"""Persistence and migration tests for single-layer gamepad layouts."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamepad_layouts_loader as loader


class GamepadLayoutsLoaderTest(unittest.TestCase):
    def test_normalize_creates_single_layer_version_three(self):
        data = loader.normalize({"layouts": [{"id": "l1", "name": "Blank", "controls": [], "keys": []}]})
        layout = data["layouts"][0]
        self.assertEqual(data["version"], 3)
        self.assertNotIn("keys", layout)
        self.assertNotIn("editor", layout)
        self.assertEqual(layout["background"]["id"], "mobile-light")
        self.assertEqual(layout["canvas"], {"width": 2400, "height": 1080})

    def test_canvas_size_is_normalized_to_supported_limits(self):
        data = loader.normalize({"layouts": [{
            "id": "canvas",
            "canvas": {"width": 12000, "height": 100},
        }]})
        self.assertEqual(data["layouts"][0]["canvas"], {"width": 7680, "height": 360})

    def test_control_size_keeps_minimum_without_an_upper_limit(self):
        data = loader.normalize({"layouts": [{
            "id": "sizes",
            "controls": [
                {"id": "large", "type": "key", "size": 725, "bindings": {}},
                {"id": "small", "type": "key", "size": 10, "bindings": {}},
            ],
        }]})
        controls = data["layouts"][0]["controls"]
        self.assertEqual(controls[0]["size"], 725)
        self.assertEqual(controls[1]["size"], 50)

    def test_mobile_button_style_and_behavior_survive_normalization(self):
        data = loader.normalize({"layouts": [{
            "id": "mobile-style",
            "controls": [{
                "id": "jump", "type": "key", "label": "Jump", "behavior": "toggle",
                "bindings": {"press": {"type": "key", "key": "space"}},
                "appearance": {
                    "shape": "square", "skin": "keycap", "labelMode": "both",
                    "pressEffect": "scale", "fill": "#FFFFFF",
                },
            }],
        }]})
        control = data["layouts"][0]["controls"][0]
        self.assertEqual(control["behavior"], "toggle")
        self.assertEqual(control["appearance"], {
            "shape": "square", "skin": "keycap", "labelMode": "both",
            "pressEffect": "scale", "fill": "#FFFFFF",
        })

    def test_legacy_spatial_keys_migrate_to_direct_bindings(self):
        data = loader.normalize({"layouts": [{
            "id": "legacy",
            "controls": [{
                "id": "stick", "type": "leftStick", "label": "Move",
                "x": 20, "y": 60, "size": 100, "bindings": {},
            }],
            "keys": [
                {"id": "w", "value": "W", "x": 20, "y": 47},
                {"id": "a", "value": "A", "x": 14, "y": 60},
                {"id": "s", "value": "S", "x": 20, "y": 73},
                {"id": "d", "value": "D", "x": 26, "y": 60},
            ],
        }]})
        control = data["layouts"][0]["controls"][0]
        self.assertEqual(control["bindings"]["up"], {"type": "key", "key": "w"})
        self.assertEqual(control["bindings"]["right"], {"type": "key", "key": "d"})
        self.assertNotIn("keys", data["layouts"][0])

    def test_legacy_id_binding_and_combo_value_migrate(self):
        data = loader.normalize({"layouts": [{
            "id": "legacy",
            "controls": [{"id": "macro", "type": "macro", "bindings": {"press": "combo"}}],
            "keys": [{"id": "combo", "value": "Ctrl + Shift + S", "x": 50, "y": 50}],
        }]})
        binding = data["layouts"][0]["controls"][0]["bindings"]["press"]
        self.assertEqual(binding, {"type": "shortcut", "modifiers": ["ctrl", "shift"], "key": "s"})

    def test_component_preset_round_trip_is_separate_from_layouts(self):
        with tempfile.TemporaryDirectory() as directory:
            layout_path = os.path.join(directory, "layouts.json")
            preset_path = os.path.join(directory, "presets.json")
            legacy_path = os.path.join(directory, "legacy-presets.json")
            with mock.patch.object(loader, "_path", return_value=layout_path), \
                    mock.patch.object(loader, "_presets_path", return_value=preset_path), \
                    mock.patch.object(loader, "_legacy_presets_path", return_value=legacy_path):
                original = loader.load()
                saved = loader.save_component_preset({
                    "id": "preset-wasd", "name": "移动组件",
                    "control": {
                        "type": "leftStick", "label": "移动", "x": 50, "y": 50,
                        "bindings": loader._default_bindings("leftStick"),
                    },
                })
                loaded = loader.load_component_presets()
                self.assertEqual(saved["id"], "preset-wasd")
                self.assertEqual(loaded["presets"][0]["control"]["bindings"]["up"]["key"], "w")
                self.assertEqual(loader.load(), original)
                self.assertTrue(os.path.exists(preset_path))

    def test_background_preset_round_trip_is_separate_from_layouts(self):
        with tempfile.TemporaryDirectory() as directory:
            layout_path = os.path.join(directory, "layouts.json")
            background_path = os.path.join(directory, "backgrounds.json")
            with mock.patch.object(loader, "_path", return_value=layout_path), \
                    mock.patch.object(loader, "_backgrounds_path", return_value=background_path):
                original = loader.load()
                saved = loader.save_background_preset({
                    "id": "background-work",
                    "name": "工作背景",
                    "baseId": "mobile-light",
                    "theme": {"stage_top": "#ffffff"},
                })
                self.assertEqual(saved["name"], "工作背景")
                self.assertEqual(loader.load_background_presets()["presets"][0]["theme"]["stage_top"], "#ffffff")
                self.assertEqual(loader.load(), original)
                self.assertTrue(loader.delete_background_preset("background-work"))
                self.assertEqual(loader.load_background_presets()["presets"], [])


if __name__ == "__main__":
    unittest.main()
