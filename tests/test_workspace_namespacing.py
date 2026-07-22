import unittest

from streamlit.testing.v1 import AppTest

from modules.breakdown.framework.breakdown_workspace import _key
from modules.breakdown.props_resources import PROP_CONFIG
from modules.breakdown.vfx_resources import VFX_CONFIG


class WorkspaceNamespacingTests(unittest.TestCase):
    def test_keys_are_scoped_by_resource_type(self):
        self.assertEqual(_key(PROP_CONFIG, "new"), "prop_new")
        self.assertEqual(_key(VFX_CONFIG, "new"), "vfx_new")
        self.assertNotEqual(_key(PROP_CONFIG, "duplicate"), _key(VFX_CONFIG, "duplicate"))

    def test_props_and_vfx_can_render_together(self):
        app = AppTest.from_string("""
from modules.breakdown.framework.breakdown_workspace import render_workspace
from modules.breakdown.framework.resource_engine import MasterResourceEngine
from modules.breakdown.props_resources import PROP_CONFIG
from modules.breakdown.vfx_resources import VFX_CONFIG

store = {
    "schema_version": 1,
    "resources": {},
    "assignments": {},
    "sequences": {},
    "events": [],
}
render_workspace(MasterResourceEngine(store), PROP_CONFIG, "1")
render_workspace(MasterResourceEngine(store), VFX_CONFIG, "1")
""").run(timeout=20)
        self.assertEqual(list(app.exception), [])

    def test_multi_resource_workspace_renders_without_duplicate_widgets(self):
        app = AppTest.from_string("""
from modules.breakdown.framework.breakdown_workspace import render_workspace
from modules.breakdown.framework.resource_engine import MasterResourceEngine
from modules.breakdown.vfx_resources import VFX_CONFIG, VFX_RESOURCE_CONFIGS

store = {"schema_version": 1, "resources": {}, "assignments": {}, "sequences": {}, "events": []}
render_workspace(MasterResourceEngine(store), VFX_CONFIG, "1", resource_configs=VFX_RESOURCE_CONFIGS)
""").run(timeout=20)
        self.assertEqual(list(app.exception), [])

    def test_props_vfx_and_extras_workspaces_coexist(self):
        app = AppTest.from_string("""
from modules.breakdown.framework.breakdown_workspace import render_workspace
from modules.breakdown.framework.resource_engine import MasterResourceEngine
from modules.breakdown.props_resources import PROP_CONFIG
from modules.breakdown.vfx_resources import VFX_CONFIG, VFX_RESOURCE_CONFIGS
from modules.breakdown.extras_resources import EXTRA_CONFIG, EXTRAS_RESOURCE_CONFIGS

store = {"schema_version": 1, "resources": {}, "assignments": {}, "sequences": {}, "events": []}
engine = MasterResourceEngine(store)
render_workspace(engine, PROP_CONFIG, "1")
render_workspace(engine, VFX_CONFIG, "1", resource_configs=VFX_RESOURCE_CONFIGS)
render_workspace(engine, EXTRA_CONFIG, "1", resource_configs=EXTRAS_RESOURCE_CONFIGS)
""").run(timeout=20)
        self.assertEqual(list(app.exception), [])


if __name__ == "__main__":
    unittest.main()
