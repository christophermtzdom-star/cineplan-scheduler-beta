import unittest

import pandas as pd

from modules.breakdown.framework.autocomplete_engine import autocomplete
from modules.breakdown.framework.resource_engine import MasterResourceEngine, ResourceConflictError
from modules.breakdown.extras_resources import (
    EXTRA_CONFIG,
    VEHICLE_CONFIG,
    legacy_extras_projection,
    migrate_legacy_extras,
)
from modules.breakdown.props_resources import PROP_CONFIG, legacy_props_projection, migrate_legacy_props
from modules.breakdown.vfx_resources import (
    PRACTICAL_FX_CONFIG,
    SOUND_CONFIG,
    VFX_CONFIG,
    legacy_vfx_projection,
    migrate_legacy_vfx,
)


class ResourceEngineTests(unittest.TestCase):
    def test_stable_id_reuse_rename_and_relationships(self):
        engine = MasterResourceEngine()
        prop = engine.create(PROP_CONFIG, "Teléfono", "Props de mano")
        self.assertEqual(prop["id"], "PROP-0001")
        engine.assign(prop["id"], "1", character="Sara", location="Casa")
        engine.assign(prop["id"], "5", character="Miguel", location="Hospital")
        engine.update(prop["id"], name="Teléfono rojo")
        self.assertEqual(engine.get(prop["id"])["name"], "Teléfono rojo")
        self.assertEqual(engine.get(prop["id"])["characters"], ["Miguel", "Sara"])
        self.assertEqual({a["scene_id"] for a in engine.assignments_for_resource(prop["id"])}, {"1", "5"})

    def test_duplicate_guard_and_autocomplete(self):
        engine = MasterResourceEngine()
        prop = engine.create(PROP_CONFIG, "Teléfono", "Props de mano")
        engine.assign(prop["id"], "12")
        with self.assertRaises(ResourceConflictError):
            engine.create(PROP_CONFIG, "teléfono", "Props de mano")
        match = autocomplete(engine, "Tel", "prop")[0]
        self.assertEqual(match["id"], prop["id"])
        self.assertEqual(match["scenes"], ["12"])

    def test_legacy_migration_is_idempotent_and_projection_preserves_reports(self):
        legacy = {
            "1": {"props_mano": pd.DataFrame([{
                "ID": 1, "Prop": "Llaves", "Personaje que lo usa": "Sara",
                "Cantidad": 2, "Continuidad": "Mantener posición", "Notas": "Primer plano",
            }])},
            "5": {"props_mano": pd.DataFrame([{
                "ID": 1, "Prop": "Llaves", "Personaje que lo usa": "Sara", "Cantidad": 1,
            }])},
        }
        store = migrate_legacy_props(legacy)
        self.assertEqual(len(store["resources"]), 1)
        self.assertEqual(len(store["assignments"]), 2)
        snapshot_events = len(store["events"])
        self.assertIs(migrate_legacy_props(legacy, store), store)
        self.assertEqual(len(store["events"]), snapshot_events)
        projection = legacy_props_projection(store)
        self.assertEqual(projection["1"]["props_mano"].iloc[0]["Prop"], "Llaves")
        self.assertEqual(projection["1"]["props_mano"].iloc[0]["Cantidad"], 2)

    def test_delete_cleans_scene_references(self):
        engine = MasterResourceEngine()
        prop = engine.create(PROP_CONFIG, "Vaso", "Props de mano")
        engine.assign(prop["id"], "1")
        engine.delete(prop["id"])
        self.assertEqual(engine.assignments_for_scene("1"), [])

    def test_vfx_legacy_migration_reuses_resource_and_preserves_report_schema(self):
        legacy = {
            "2": {"vfx": pd.DataFrame([{
                "ID": 1, "VFX requerido": "Eliminar cables", "Tipo": "Wire Removal",
                "Prioridad": "High", "Descripción": "Limpiar arnés",
                "Responsable": "VFX", "Notas": "Plano abierto",
            }])},
            "8": {"vfx": pd.DataFrame([{
                "ID": 1, "VFX requerido": "Eliminar cables", "Tipo": "Wire Removal",
                "Responsable": "Postproduction",
            }])},
        }
        store = migrate_legacy_vfx(legacy, MasterResourceEngine().store)
        resources = [r for r in store["resources"].values() if r["resource_type"] == "vfx"]
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0]["id"], "VFX-0001")
        self.assertEqual(len(MasterResourceEngine(store).assignments_for_resource("VFX-0001")), 2)
        projection = legacy_vfx_projection(store)
        row = projection["2"]["vfx"].iloc[0]
        self.assertEqual(row["VFX requerido"], "Eliminar cables")
        self.assertEqual(row["Prioridad"], "High")

    def test_vfx_definition_has_requested_categories_statuses_and_inspector(self):
        self.assertEqual(VFX_CONFIG.id_prefix, "VFX")
        self.assertFalse(VFX_CONFIG.allow_duplicate_creation)
        self.assertIn("Pantalla Verde", VFX_CONFIG.categories)
        self.assertIn("Finalizado", VFX_CONFIG.statuses)
        fields = {field.key: field.section for field in VFX_CONFIG.inspector_fields}
        self.assertEqual(fields["supervisor"], "Producción")
        self.assertEqual(fields["reference_video"], "Continuidad")
        self.assertEqual(fields["relationships"], "Proyecto")

    def test_practical_fx_and_sound_have_stable_prefixes_and_own_inspectors(self):
        engine = MasterResourceEngine()
        practical = engine.create(PRACTICAL_FX_CONFIG, "Lluvia ventana", "Lluvia")
        sound = engine.create(SOUND_CONFIG, "Ambiente cocina", "Ambiente de Sala")
        self.assertEqual(practical["id"], "SFX-0001")
        self.assertEqual(sound["id"], "SND-0001")
        practical_fields = {field.key for field in PRACTICAL_FX_CONFIG.inspector_fields}
        sound_fields = {field.key for field in SOUND_CONFIG.inspector_fields}
        self.assertIn("safety", practical_fields)
        self.assertIn("special_recording", sound_fields)
        self.assertIn("adr_required", sound_fields)

    def test_legacy_sfx_and_sound_migrate_to_dedicated_types_and_project_back(self):
        legacy = {"3": {
            "sfx_practicos": pd.DataFrame([{
                "SFX práctico": "Humo pasillo", "Tipo": "Humo",
                "Material requerido": "Máquina de humo", "Seguridad": "Supervisor",
            }]),
            "sonido": pd.DataFrame([{
                "Elemento sonoro": "Wild track mercado", "Tipo": "Wild Track",
                "Grabación especial": "Yes", "Responsable": "Production Sound",
            }]),
        }}
        store = migrate_legacy_vfx(legacy, MasterResourceEngine().store)
        resources = store["resources"]
        self.assertIn("SFX-0001", resources)
        self.assertIn("SND-0001", resources)
        self.assertEqual(resources["SFX-0001"]["resource_type"], "practical_fx")
        self.assertEqual(resources["SND-0001"]["resource_type"], "sound")
        projection = legacy_vfx_projection(store)["3"]
        self.assertEqual(projection["sfx_practicos"].iloc[0]["SFX práctico"], "Humo pasillo")
        self.assertEqual(projection["sonido"].iloc[0]["Elemento sonoro"], "Wild track mercado")

    def test_extras_and_vehicles_use_stable_ids_and_material_symbols(self):
        engine = MasterResourceEngine()
        extra = engine.create(EXTRA_CONFIG, "Peatones", "Multitud")
        vehicle = engine.create(VEHICLE_CONFIG, "Sedán rojo", "Automóvil")
        self.assertEqual(extra["id"], "EXT-0001")
        self.assertEqual(vehicle["id"], "VEH-0001")
        self.assertEqual(EXTRA_CONFIG.material_symbol, "\ue7ef")
        self.assertEqual(VEHICLE_CONFIG.material_symbol, "\ue531")

    def test_legacy_extras_vehicles_drivers_and_animals_round_trip(self):
        legacy = {"4": {
            "extras_atmosfera": pd.DataFrame([{
                "Tipo extra": "Peatones", "Cantidad": 12,
                "Vestuario requerido": "Invierno", "Acción": "Cruzan avenida",
            }]),
            "vehiculos_pelicula": pd.DataFrame([{
                "Vehículo": "Taxi amarillo", "Conductor": "Luis",
                "Personaje asociado": "Sara", "Acción escena": "Frena",
            }]),
            "animales": pd.DataFrame([{
                "Animal": "Caballo", "Cantidad": 2,
                "Handler requerido": "Sí", "Nombre del Handler": "Ana",
            }]),
        }}
        store = migrate_legacy_extras(legacy, MasterResourceEngine().store)
        self.assertIn("EXT-0001", store["resources"])
        self.assertIn("VEH-0001", store["resources"])
        projection = legacy_extras_projection(store)["4"]
        self.assertEqual(projection["extras_atmosfera"].iloc[0]["Cantidad"], 12)
        self.assertEqual(projection["vehiculos_pelicula"].iloc[0]["Conductor"], "Luis")
        self.assertEqual(projection["animales"].iloc[0]["Nombre del Handler"], "Ana")


if __name__ == "__main__":
    unittest.main()
