"""Props configuration and legacy CPS/report compatibility projection."""

from collections.abc import Mapping

import pandas as pd

from modules.breakdown.framework.resource_engine import MasterResourceEngine
from modules.breakdown.framework.resource_models import InspectorField, ResourceModuleConfig, empty_store


PROP_CONFIG = ResourceModuleConfig(
    resource_type="prop", id_prefix="PROP", label="Utilería",
    categories=("Utilería de mano", "Decoración de Escenario", "Utilería especial", "Utilería de riesgo"),
    statuses=("Pendiente", "Asignado", "En preparación", "Listo"),
    inspector_fields=(
        InspectorField("responsible", "Responsable", "select",
                       ("Utilería", "Arte", "Decoración", "Vestuario", "Producción", "Otro")),
        InspectorField("character", "Personaje asignado"),
        InspectorField("supplier", "Proveedor", section="Producción", scope="resource"),
        InspectorField("estimated_cost", "Costo estimado", "number", section="Producción", scope="resource"),
        InspectorField("acquisition", "Compra / renta", "select",
                       ("", "Compra", "Renta", "Propio", "Por definir"), section="Producción"),
        InspectorField("required_date", "Fecha requerida", section="Producción"),
        InspectorField("production_notes", "Notas de producción", "textarea", section="Producción"),
        InspectorField("photo", "Foto de referencia", section="Continuidad"),
        InspectorField("continuity", "Notas de continuidad", "textarea", section="Continuidad"),
        InspectorField("tags", "Etiquetas", section="Continuidad", scope="custom"),
        InspectorField("attachments", "Archivos adjuntos", section="Continuidad", scope="custom"),
        InspectorField("custom_fields_text", "Campos personalizados", "textarea", section="Proyecto", scope="custom"),
        InspectorField("notes", "Notas del proyecto", "textarea", section="Proyecto", scope="resource"),
        InspectorField("relationships", "Relaciones", section="Proyecto", read_only=True),
    ),
)

LEGACY = {
    "props_mano": ("Utilería de mano", "Prop"),
    "set_dressing": ("Decoración de Escenario", "Elemento"),
    "props_especiales": ("Utilería especial", "Prop especial"),
    "utileria_riesgo": ("Utilería de riesgo", "Elemento"),
}

_VISIBLE_CATEGORIES = {
    "Props de mano": "Utilería de mano",
    "Set Dressing": "Decoración de Escenario",
    "Props especiales": "Utilería especial",
}


def _records(value):
    if isinstance(value, pd.DataFrame):
        return value.fillna("").to_dict(orient="records")
    return value if isinstance(value, list) else []


def migrate_legacy_props(legacy_data, store=None, scene_locations=None):
    """Idempotently import old per-scene rows into stable project resources."""
    engine = MasterResourceEngine(store if isinstance(store, dict) else empty_store())
    for resource in engine.resources("prop"):
        category = _VISIBLE_CATEGORIES.get(resource.get("category"))
        if category:
            engine.update(resource["id"], category=category)
        for assignment in engine.assignments_for_resource(resource["id"]):
            if assignment.get("responsible") == "Props":
                engine.assign(resource["id"], assignment["scene_id"], responsible="Utilería")
    if engine.store["resources"] or engine.store["assignments"]:
        return engine.store
    scene_locations = scene_locations or {}
    if not isinstance(legacy_data, Mapping):
        return engine.store
    for scene_id, categories in legacy_data.items():
        if str(scene_id).startswith("__") or not isinstance(categories, Mapping):
            continue
        for key, (category, name_column) in LEGACY.items():
            for row in _records(categories.get(key, [])):
                name = str(row.get(name_column, "")).strip()
                if not name:
                    continue
                resource = engine.exact_name(name, "prop", category)
                if resource is None:
                    resource = engine.create(PROP_CONFIG, name, category)
                values = {
                    "quantity": row.get("Cantidad", 1) or 1,
                    "character": row.get("Personaje que lo usa", ""),
                    "location": scene_locations.get(str(scene_id), ""),
                    "continuity": row.get("Continuidad", ""),
                    "area": row.get("Área / Set", row.get("Ãrea / Set", "")),
                    "fx": row.get("FX asociado", ""),
                    "risk_type": row.get("Tipo", ""),
                    "safety": row.get("Seguridad requerida", ""),
                    "responsible": row.get("Responsable", ""),
                    "notes": row.get("Notas", ""),
                }
                engine.assign(resource["id"], str(scene_id), **values)
    return engine.store


def legacy_props_projection(store):
    """Generate the historical tables consumed by Export Breakdown."""
    engine = MasterResourceEngine(store)
    output = {}
    reverse = {category: (key, name) for key, (category, name) in LEGACY.items()}
    for scene_id, assignments in engine.store["assignments"].items():
        scene = {key: [] for key in LEGACY}
        counters = {key: 0 for key in LEGACY}
        for assignment in assignments:
            resource = engine.store["resources"].get(assignment.get("resource_id"), {})
            if resource.get("resource_type") != "prop" or resource.get("category") not in reverse:
                continue
            key, name_column = reverse[resource["category"]]
            counters[key] += 1
            row = {"ID": counters[key], name_column: resource.get("name", ""),
                   "Cantidad": assignment.get("quantity", 1), "Notas": assignment.get("notes", resource.get("notes", ""))}
            if key == "props_mano":
                row.update({"Personaje que lo usa": assignment.get("character", ""), "Continuidad": assignment.get("continuity", "")})
            elif key == "set_dressing":
                row["Área / Set"] = assignment.get("area", "")
            elif key == "props_especiales":
                row.update({"FX asociado": assignment.get("fx", ""), "Responsable": assignment.get("responsible", "")})
            else:
                row.update({"Tipo": assignment.get("risk_type", ""), "Seguridad requerida": assignment.get("safety", ""), "Responsable": assignment.get("responsible", "")})
            scene[key].append(row)
        output[str(scene_id)] = {key: pd.DataFrame(rows) for key, rows in scene.items()}
    return output
