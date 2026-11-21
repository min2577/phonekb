import json
import os
import tempfile
import unittest
from unittest import mock

import layouts_loader


class LayoutsLoaderAddLayoutTest(unittest.TestCase):
    def test_phone_layout_is_added_to_layouts_not_global_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir, \
                mock.patch.object(layouts_loader, "_write_root", return_value=temp_dir), \
                mock.patch.object(layouts_loader, "_read_roots", return_value=[temp_dir]):
            created = layouts_loader.add_layout({
                "id": "phone-layout",
                "name": "Phone layout",
                "pages": [{"id": "phone-page", "name": "Page 1", "slots": []}],
            })
            self.assertEqual(created["id"], "phone-layout")
            with open(os.path.join(temp_dir, "layouts.json"), "r", encoding="utf-8") as handle:
                saved = json.load(handle)

        self.assertTrue(any(item["id"] == "phone-layout" for item in saved["layouts"]))
        self.assertFalse(any(item["id"] == "phone-layout" for item in saved["global_pages"]))
        self.assertEqual(saved["active_layout_id"], "phone-layout")
        self.assertEqual(saved["active_page_id"], "phone-page")

    def test_misplaced_layout_is_migrated_out_of_global_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data = layouts_loader._default_data()
            data["global_pages"].append({
                "id": "broken-layout",
                "name": "Broken",
                "pages": [{"id": "broken-page", "name": "Page", "slots": []}],
            })
            with open(os.path.join(temp_dir, "layouts.json"), "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False)
            with mock.patch.object(layouts_loader, "_write_root", return_value=temp_dir), \
                    mock.patch.object(layouts_loader, "_read_roots", return_value=[temp_dir]):
                loaded = layouts_loader.load()
        self.assertTrue(any(item["id"] == "broken-layout" for item in loaded["layouts"]))
        self.assertFalse(any(item["id"] == "broken-layout" for item in loaded["global_pages"]))

    def test_archive_restore_and_delete_support_every_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir, \
                mock.patch.object(layouts_loader, "_write_root", return_value=temp_dir), \
                mock.patch.object(layouts_loader, "_read_roots", return_value=[temp_dir]):
            layouts_loader.save(layouts_loader._default_data())
            self.assertTrue(layouts_loader.archive_layout("default"))
            archived = layouts_loader.load()
            self.assertTrue(any(item["id"] == "default" for item in archived["archived_layouts"]))
            self.assertTrue(layouts_loader.restore_layout("default"))
            restored = layouts_loader.load()
            self.assertTrue(any(item["id"] == "default" for item in restored["layouts"]))
            self.assertTrue(layouts_loader.delete_layout("default"))
            deleted = layouts_loader.load()
            self.assertTrue(deleted["layouts"])
            self.assertNotEqual(deleted["active_layout_id"], "default")


if __name__ == "__main__":
    unittest.main()
