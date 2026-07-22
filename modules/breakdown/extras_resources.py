"""Extras and vehicles definitions with legacy report compatibility."""

from collections.abc import Mapping

import pandas as pd

from modules.breakdown.framework.resource_engine import MasterResourceEngine
from modules.breakdown.framework.resource_models import InspectorField, ResourceModuleConfig


EXTRA_CONFIG = ResourceModuleConfig(
    resource_type="extra", id_prefix="EXT", label="Extras", material_symbol="\ue7ef",
    categories=("Principal", "Secundario", "Multitud", "Especial", "Con Diálogo",
                "Sin Diálogo", "Doble", "Figuración Especial", "Otro"),
    statuses=("Pendiente", "Asignado", "Confirmado", "En Rodaje", "Finalizado"),
    allow_duplicate_creation=False,
    inspector_fields=(
        InspectorField("responsible", "Responsable", "select",
                       ("Casting", "Producción", "Dirección", "Coordinación de extras", "Otro")),
        InspectorField("scene", "Escena", read_only=True),
        InspectorField("coordinator", "Coordinador", section="Producción"),
        InspectorField("supplier", "Proveedor", section="Producción", scope="resource"),
        InspectorField("estimated_cost", "Costo estimado", "number", section="Producción", scope="resource"),
        InspectorField("required_date", "Fecha requerida", section="Producción"),
        InspectorField("production_notes", "Notas de producción", "textarea", section="Producción"),
        InspectorField("wardrobe", "Vestuario", section="Continuidad"),
        InspectorField("makeup", "Maquillaje", section="Continuidad"),
        InspectorField("accessories", "Accesorios", section="Continuidad"),
        InspectorField("continuity", "Continuidad", "textarea", section="Continuidad"),
        InspectorField("tags", "Etiquetas", section="Continuidad", scope="custom"),
        InspectorField("attachments", "Archivos adjuntos", section="Continuidad", scope="custom"),
        InspectorField("custom_fields_text", "Campos personalizados", "textarea", section="Proyecto", scope="custom"),
        InspectorField("notes", "Notas del proyecto", "textarea", section="Proyecto", scope="resource"),
        InspectorField("relationships", "Relaciones", section="Proyecto", read_only=True),
    ),
)

VEHICLE_CONFIG = ResourceModuleConfig(
    resource_type="vehicle", id_prefix="VEH", label="Vehículos", material_symbol="\ue531",
    categories=("Automóvil", "Camioneta", "Camión", "Motocicleta", "Bicicleta", "Maquinaria",
                "Vehículo Especial", "Animal de Tiro", "Otro"),
    statuses=("Pendiente", "Reservado", "Confirmado", "Disponible", "En Rodaje", "Finalizado"),
    allow_duplicate_creation=False,
    inspector_fields=(
        InspectorField("responsible", "Responsable", "select",
                       ("Transporte", "Producción", "Dirección", "Utilería", "Proveedor", "Otro")),
        InspectorField("scene", "Escena", read_only=True),
        InspectorField("supplier", "Proveedor", section="Producción", scope="resource"),
        InspectorField("driver", "Conductor", section="Producción"),
        InspectorField("plates", "Placas", section="Producción", scope="resource"),
        InspectorField("model", "Modelo", section="Producción", scope="resource"),
        InspectorField("color", "Color", section="Producción", scope="resource"),
        InspectorField("estimated_cost", "Costo estimado", "number", section="Producción", scope="resource"),
        InspectorField("required_date", "Fecha requerida", section="Producción"),
        InspectorField("production_notes", "Notas", "textarea", section="Producción"),
        InspectorField("visual_state", "Estado visual", section="Continuidad"),
        InspectorField("photos", "Fotografías", section="Continuidad", scope="custom"),
        InspectorField("tags", "Etiquetas", section="Continuidad", scope="custom"),
        InspectorField("attachments", "Archivos adjuntos", section="Continuidad", scope="custom"),
        InspectorField("custom_fields_text", "Campos personalizados", "textarea", section="Proyecto", scope="custom"),
        InspectorField("notes", "Notas del proyecto", "textarea", section="Proyecto", scope="resource"),
        InspectorField("relationships", "Relaciones", section="Proyecto", read_only=True),
    ),
)

EXTRAS_RESOURCE_CONFIGS = (EXTRA_CONFIG, VEHICLE_CONFIG)

_LEGACY = {
    "extras_atmosfera": (EXTRA_CONFIG, "Tipo extra", "Sin Diálogo"),
    "extras_dialogo": (EXTRA_CONFIG, "Personaje / Tipo", "Con Diálogo"),
    "animales": (EXTRA_CONFIG, "Animal", "Figuración Especial"),
    "vehiculos_pelicula": (VEHICLE_CONFIG, "Vehículo", "Otro"),
    "vehiculos_produccion": (VEHICLE_CONFIG, "Vehículo producción", "Otro"),
}


def _records(value):
    if isinstance(value, pd.DataFrame):
        return value.fillna("").to_dict(orient="records")
    return value if isinstance(value, list) else []


def migrate_legacy_extras(legacy_data, store, scene_locations=None):
    """Idempotently import extras, vehicles, drivers and animals."""
    engine = MasterResourceEngine(store)
    scene_locations = scene_locations or {}
    if not isinstance(legacy_data, Mapping):
        return engine.store
    for scene_id, groups in legacy_data.items():
        if str(scene_id).startswith("__") or not isinstance(groups, Mapping):
            continue
        for legacy_key, (config, name_column, category) in _LEGACY.items():
            for row in _records(groups.get(legacy_key, [])):
                name = str(row.get(name_column, "")).strip()
                if not name:
                    continue
                resource = engine.exact_name(name, config.resource_type, category)
                if resource is None:
                    resource = engine.create(config, name, category, notes=row.get("Notas", ""))
                if any(item.get("resource_id") == resource["id"]
                       for item in engine.assignments_for_scene(str(scene_id))):
                    continue
                engine.assign(
                    resource["id"], str(scene_id), quantity=row.get("Cantidad", 1) or 1,
                    location=scene_locations.get(str(scene_id), ""), legacy_kind=legacy_key,
                    responsible=row.get("Responsable", row.get("Departamento", "")),
                    wardrobe=row.get("Vestuario requerido", ""),
                    action=row.get("Acción", row.get("Acción escena", "")),
                    function=row.get("Línea o función", ""),
                    character=row.get("Personaje asociado", ""),
                    driver=row.get("Conductor", ""),
                    is_picture_vehicle=row.get("Vehículo película", ""),
                    handler_required=row.get("Handler requerido", ""),
                    handler=row.get("Nombre del Handler", ""),
                    production_notes=row.get("Notas", ""),
                )
    return engine.store


def legacy_extras_projection(store):
    """Regenerate the historical tables consumed by Export Breakdown."""
    engine = MasterResourceEngine(store)
    output = {}
    for scene_id, assignments in engine.store["assignments"].items():
        scene = {key: [] for key in _LEGACY}
        counters = {key: 0 for key in _LEGACY}
        for assignment in assignments:
            resource = engine.store["resources"].get(assignment.get("resource_id"), {})
            if resource.get("resource_type") not in {"extra", "vehicle"}:
                continue
            default_key = "extras_atmosfera" if resource.get("resource_type") == "extra" else "vehiculos_pelicula"
            key = assignment.get("legacy_kind", default_key)
            if key not in _LEGACY:
                key = default_key
            _, name_column, _ = _LEGACY[key]
            counters[key] += 1
            row = {"ID": counters[key], name_column: resource.get("name", ""),
                   "Responsable": assignment.get("responsible", ""),
                   "Notas": assignment.get("production_notes", resource.get("notes", ""))}
            if key == "extras_atmosfera":
                row.update({"Cantidad": assignment.get("quantity", 1),
                            "Vestuario requerido": assignment.get("wardrobe", ""),
                            "Acción": assignment.get("action", "")})
            elif key == "extras_dialogo":
                row.update({"Línea o función": assignment.get("function", ""),
                            "Cantidad": assignment.get("quantity", 1)})
            elif key == "vehiculos_pelicula":
                row.update({"Personaje asociado": assignment.get("character", ""),
                            "Conductor": assignment.get("driver", ""),
                            "Acción escena": assignment.get("action", ""),
                            "Vehículo película": assignment.get("is_picture_vehicle", "")})
            elif key == "animales":
                row.update({"Cantidad": assignment.get("quantity", 1),
                            "Handler requerido": assignment.get("handler_required", ""),
                            "Nombre del Handler": assignment.get("handler", "")})
            else:
                row.update({"Departamento": assignment.get("responsible", ""),
                            "Cantidad": assignment.get("quantity", 1)})
            scene[key].append(row)
        output[str(scene_id)] = {key: pd.DataFrame(rows) for key, rows in scene.items()}
    return output
