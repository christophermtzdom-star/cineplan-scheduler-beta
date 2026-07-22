import unittest

from modules.breakdown.props_resources import PROP_CONFIG
from modules.breakdown.extras_resources import EXTRA_CONFIG, VEHICLE_CONFIG
from modules.breakdown.vfx_resources import PRACTICAL_FX_CONFIG, SOUND_CONFIG, VFX_CONFIG


class WorkspaceSpanishTests(unittest.TestCase):
    def test_visible_resource_definitions_are_spanish(self):
        visible = []
        for config in (PROP_CONFIG, VFX_CONFIG, PRACTICAL_FX_CONFIG, SOUND_CONFIG,
                       EXTRA_CONFIG, VEHICLE_CONFIG):
            visible.extend((config.label, *config.categories, *config.statuses))
            for field in config.inspector_fields:
                visible.extend((field.label, field.section, *field.options))
        forbidden = {
            "Visual Effects", "Practical Effects", "Sound", "Cleanup", "Compositing",
            "Green Screen", "Wire Removal", "Set Extension", "Particles", "Other",
            "Smoke", "Fire", "Rain", "Blood", "Dust", "Wind", "Breakaway Props",
            "Atmospherics", "Pyrotechnics", "Production Sound", "Wireless", "Room Tone",
            "Music Cue", "Ambience", "Pending", "Planned", "Filmed", "In Progress",
            "Review", "Approved", "Final", "Postproduction", "Production", "Safety",
            "Stunts", "Vendor", "Sound Supervisor", "Yes", "Set Dressing",
        }
        self.assertEqual(forbidden.intersection(visible), set())

    def test_intentionally_preserved_technical_terms_remain_available(self):
        visible_categories = set(VFX_CONFIG.categories + SOUND_CONFIG.categories)
        self.assertTrue({"Tracking", "Matte Painting", "Boom", "ADR", "Foley",
                         "Playback", "Wild Track"}.issubset(visible_categories))


if __name__ == "__main__":
    unittest.main()
