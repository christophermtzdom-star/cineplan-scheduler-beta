import json
import unittest
from unittest.mock import patch

from project.runtime_environment import is_web_runtime


class RuntimeEnvironmentTests(unittest.TestCase):
    def test_windows_desktop_stays_native(self):
        self.assertFalse(is_web_runtime({}, "win32"))

    def test_cloud_marker_selects_browser_transport(self):
        self.assertTrue(is_web_runtime({"STREAMLIT_SHARING_MODE": "true"}, "win32"))

    def test_non_windows_selects_browser_transport(self):
        self.assertTrue(is_web_runtime({}, "linux"))


class BrowserProjectTransportTests(unittest.TestCase):
    def test_browser_bytes_use_canonical_container_builder(self):
        from project.project_manager import project_download_bytes

        metadata = {
            "file_type": "CinePlan Scheduler Project",
            "extension": ".cps",
            "schema_version": 1,
            "cineplan_version": "3.0",
            "project_id": "id",
            "created_at": "created",
            "last_saved": "saved",
        }
        with patch("project.project_manager._build_container", return_value={
            **metadata, "workspace_context": {}, "project": {"name": "Prueba"}
        }):
            result = json.loads(project_download_bytes(lambda: {}).decode("utf-8"))
        self.assertEqual(result["project"], {"name": "Prueba"})
        self.assertEqual(result["extension"], ".cps")


if __name__ == "__main__":
    unittest.main()
