"""VFX resource definition and legacy Export Breakdown projection."""

from collections.abc import Mapping

import pandas as pd

from modules.breakdown.framework.resource_engine import MasterResourceEngine
from modules.breakdown.framework.resource_models import InspectorField, ResourceModuleConfig


VFX_CONFIG = ResourceModuleConfig(
    resource_type="vfx",
    id_prefix="VFX",
    label="Efectos Visuales",
    categories=(
        "Efectos Visuales", "CGI", "Limpieza Digital", "Composición", "Tracking",
        "Pantalla Verde", "Eliminación de Cables", "Extensión de Escenarios", "Partículas",
        "Matte Painting", "Otro",
    ),
    statuses=("Pendiente", "Planeado", "Filmado", "En Proceso", "En Revisión", "Aprobado", "Finalizado"),
    allow_duplicate_creation=False,
    inspector_fields=(
        InspectorField("responsible", "Responsable", "select",
                       ("VFX", "Postproducción", "Producción", "Supervisor", "Proveedor", "Otro")),
        InspectorField("scene", "Escena", read_only=True),
        InspectorField("supervisor", "Supervisor", section="Producción"),
        InspectorField("vendor", "Proveedor", section="Producción", scope="resource"),
        InspectorField("estimated_cost", "Costo estimado", "number", section="Producción", scope="resource"),
        InspectorField("software", "Software", section="Producción", scope="custom"),
        InspectorField("required_date", "Fecha requerida", section="Producción"),
        InspectorField("production_notes", "Notas de producción", "textarea", section="Producción"),
        InspectorField("reference_images", "Imágenes de referencia", section="Continuidad", scope="custom"),
        InspectorField("reference_video", "Video de referencia", section="Continuidad", scope="custom"),
        InspectorField("continuity", "Notas de continuidad", "textarea", section="Continuidad"),
        InspectorField("tags", "Etiquetas", section="Continuidad", scope="custom"),
        InspectorField("attachments", "Archivos adjuntos", section="Continuidad", scope="custom"),
        InspectorField("custom_fields_text", "Campos personalizados", "textarea", section="Proyecto", scope="custom"),
        InspectorField("notes", "Notas del proyecto", "textarea", section="Proyecto", scope="resource"),
        InspectorField("relationships", "Relaciones", section="Proyecto", read_only=True),
    ),
)

PRACTICAL_FX_CONFIG = ResourceModuleConfig(
    resource_type="practical_fx", id_prefix="SFX", label="Efectos Prácticos",
    categories=("Humo", "Fuego", "Lluvia", "Sangre", "Polvo", "Viento", "Utilería Rompible",
                "Efectos Atmosféricos", "Pirotecnia", "Otro"),
    statuses=("Pendiente", "Planeado", "Filmado", "En Proceso", "En Revisión", "Aprobado", "Finalizado"),
    allow_duplicate_creation=False,
    inspector_fields=(
        InspectorField("responsible", "Responsable", "select",
                       ("Efectos Prácticos", "Producción", "Seguridad", "Dobles de riesgo", "Proveedor", "Otro")),
        InspectorField("scene", "Escena", read_only=True),
        InspectorField("supervisor", "Supervisor", section="Producción"),
        InspectorField("vendor", "Proveedor", section="Producción", scope="resource"),
        InspectorField("estimated_cost", "Costo estimado", "number", section="Producción", scope="resource"),
        InspectorField("material", "Material requerido", section="Producción"),
        InspectorField("safety", "Seguridad", section="Producción"),
        InspectorField("required_date", "Fecha requerida", section="Producción"),
        InspectorField("production_notes", "Notas de producción", "textarea", section="Producción"),
        InspectorField("reference_images", "Imágenes de referencia", section="Continuidad", scope="custom"),
        InspectorField("continuity", "Notas de continuidad", "textarea", section="Continuidad"),
        InspectorField("tags", "Etiquetas", section="Continuidad", scope="custom"),
        InspectorField("attachments", "Archivos adjuntos", section="Continuidad", scope="custom"),
        InspectorField("custom_fields_text", "Campos personalizados", "textarea", section="Proyecto", scope="custom"),
        InspectorField("notes", "Notas del proyecto", "textarea", section="Proyecto", scope="resource"),
        InspectorField("relationships", "Relaciones", section="Proyecto", read_only=True),
    ),
)

SOUND_CONFIG = ResourceModuleConfig(
    resource_type="sound", id_prefix="SND", label="Sonido",
    categories=("Sonido Directo", "Boom", "Micrófonos Inalámbricos", "ADR", "Foley", "Wild Track",
                "Ambiente de Sala", "Playback", "Música en Escena", "Ambiente", "Otro"),
    statuses=("Pendiente", "Planeado", "Filmado", "En Proceso", "En Revisión", "Aprobado", "Finalizado"),
    allow_duplicate_creation=False,
    inspector_fields=(
        InspectorField("responsible", "Responsable", "select",
                       ("Sonido Directo", "Postproducción", "Producción", "Supervisor de sonido", "Proveedor", "Otro")),
        InspectorField("scene", "Escena", read_only=True),
        InspectorField("equipment", "Equipo", section="Producción"),
        InspectorField("special_recording", "Grabación especial", section="Producción"),
        InspectorField("adr_required", "ADR requerido", "select", ("No", "Sí"), section="Producción"),
        InspectorField("foley_required", "Foley requerido", "select", ("No", "Sí"), section="Producción"),
        InspectorField("room_tone", "Ambiente de sala", "select", ("No", "Sí"), section="Producción"),
        InspectorField("wild_track", "Wild Track", "select", ("No", "Sí"), section="Producción"),
        InspectorField("production_notes", "Notas", "textarea", section="Producción"),
        InspectorField("reference_audio", "Audio de referencia", section="Continuidad", scope="custom"),
        InspectorField("continuity", "Notas de continuidad", "textarea", section="Continuidad"),
        InspectorField("tags", "Etiquetas", section="Continuidad", scope="custom"),
        InspectorField("attachments", "Archivos adjuntos", section="Continuidad", scope="custom"),
        InspectorField("custom_fields_text", "Campos personalizados", "textarea", section="Proyecto", scope="custom"),
        InspectorField("notes", "Notas del proyecto", "textarea", section="Proyecto", scope="resource"),
        InspectorField("relationships", "Relaciones", section="Proyecto", read_only=True),
    ),
)

VFX_RESOURCE_CONFIGS = (VFX_CONFIG, PRACTICAL_FX_CONFIG, SOUND_CONFIG)


LEGACY = {
    "vfx": ("VFX requerido", "Efectos Visuales"),
    "sfx_practicos": ("SFX práctico", "Otro"),
    "sonido": ("Elemento sonoro", "Otro"),
    "requerimientos_tecnicos": ("Requerimiento", "Otro"),
}

_CONFIG_BY_LEGACY = {
    "vfx": VFX_CONFIG,
    "sfx_practicos": PRACTICAL_FX_CONFIG,
    "sonido": SOUND_CONFIG,
    "requerimientos_tecnicos": VFX_CONFIG,
}

_PRACTICAL_CATEGORIES = {
    "humo": "Humo", "fuego": "Fuego", "lluvia": "Lluvia", "sangre fx": "Sangre",
    "polvo / tierra": "Polvo", "viento": "Viento", "explosión": "Pirotecnia",
    "atmósferas": "Efectos Atmosféricos",
}
_SOUND_CATEGORIES = {
    "sonido directo": "Sonido Directo", "adr": "ADR", "foley": "Foley",
    "wild track": "Wild Track", "room tone": "Ambiente de Sala", "playback": "Playback",
    "ambiente": "Ambiente",
}

_VISIBLE_VALUES = {
    "Visual Effects": "Efectos Visuales", "Cleanup": "Limpieza Digital",
    "Compositing": "Composición", "Green Screen": "Pantalla Verde",
    "Wire Removal": "Eliminación de Cables", "Set Extension": "Extensión de Escenarios",
    "Particles": "Partículas", "Other": "Otro", "Smoke": "Humo", "Fire": "Fuego",
    "Rain": "Lluvia", "Blood": "Sangre", "Dust": "Polvo", "Wind": "Viento",
    "Breakaway Props": "Utilería Rompible", "Atmospherics": "Efectos Atmosféricos",
    "Pyrotechnics": "Pirotecnia", "Production Sound": "Sonido Directo",
    "Wireless": "Micrófonos Inalámbricos", "Room Tone": "Ambiente de Sala",
    "Music Cue": "Música en Escena", "Ambience": "Ambiente",
    "Pending": "Pendiente", "Planned": "Planeado", "Filmed": "Filmado",
    "In Progress": "En Proceso", "Review": "En Revisión", "Approved": "Aprobado",
    "Final": "Finalizado", "Postproduction": "Postproducción", "Production": "Producción",
    "Vendor": "Proveedor", "Practical Effects": "Efectos Prácticos", "Safety": "Seguridad",
    "Stunts": "Dobles de riesgo", "Sound Supervisor": "Supervisor de sonido", "Yes": "Sí",
}


def _records(value):
    if isinstance(value, pd.DataFrame):
        return value.fillna("").to_dict(orient="records")
    return value if isinstance(value, list) else []


def _category(row, fallback, config):
    value = str(row.get("Tipo", "")).strip()
    if value in config.categories:
        return value
    translated = _VISIBLE_VALUES.get(value)
    if translated in config.categories:
        return translated
    normalized = value.casefold()
    if config.resource_type == "practical_fx":
        return _PRACTICAL_CATEGORIES.get(normalized, fallback)
    if config.resource_type == "sound":
        return _SOUND_CATEGORIES.get(normalized, fallback)
    return fallback


def migrate_legacy_vfx(legacy_data, store, scene_locations=None):
    """Import legacy VFX/SFX/sound rows once into the shared resource store."""
    engine = MasterResourceEngine(store)
    for resource in engine.resources():
        if resource.get("resource_type") not in {"vfx", "practical_fx", "sound"}:
            continue
        changes = {}
        for field in ("category", "status"):
            translated = _VISIBLE_VALUES.get(resource.get(field))
            if translated:
                changes[field] = translated
        if changes:
            engine.update(resource["id"], **changes)
        for assignment in engine.assignments_for_resource(resource["id"]):
            assignment_changes = {
                key: _VISIBLE_VALUES.get(assignment.get(key), assignment.get(key))
                for key in ("responsible", "adr_required", "foley_required", "room_tone", "wild_track")
                if assignment.get(key)
            }
            if assignment_changes and any(
                assignment_changes[key] != assignment.get(key) for key in assignment_changes
            ):
                engine.assign(resource["id"], assignment["scene_id"], **assignment_changes)
    scene_locations = scene_locations or {}
    if not isinstance(legacy_data, Mapping):
        return engine.store
    for scene_id, groups in legacy_data.items():
        if str(scene_id).startswith("__") or not isinstance(groups, Mapping):
            continue
        for legacy_key, (name_column, fallback_category) in LEGACY.items():
            resource_config = _CONFIG_BY_LEGACY[legacy_key]
            for row in _records(groups.get(legacy_key, [])):
                name = str(row.get(name_column, "")).strip()
                if not name:
                    continue
                category = _category(row, fallback_category, resource_config)
                resource = engine.exact_name(name, resource_config.resource_type, category)
                if resource is None:
                    resource = engine.create(
                        resource_config, name, category,
                        notes=row.get("Notas", ""),
                    )
                if any(assignment.get("resource_id") == resource["id"]
                       for assignment in engine.assignments_for_scene(str(scene_id))):
                    continue
                engine.assign(resource["id"], str(scene_id),
                    quantity=row.get("Cantidad", 1) or 1,
                    location=scene_locations.get(str(scene_id), ""),
                    responsible=row.get("Responsable", row.get("Departamento", "")),
                    production_notes=row.get("Descripción", row.get("DescripciÃ³n", "")),
                    legacy_kind=legacy_key,
                    priority=row.get("Prioridad", ""),
                    complexity=row.get("Complejidad", ""),
                    material=row.get("Material requerido", ""),
                    safety=row.get("Seguridad", ""),
                    narrative=row.get("Narrativo", ""),
                    special_recording=row.get("Grabación especial", row.get("GrabaciÃ³n especial", "")),
                )
    # Phase 2 temporarily represented legacy SFX and sound rows as VFX. Once
    # their dedicated definitions exist, remove only those obsolete references.
    for resource in list(engine.resources("vfx")):
        misplaced = [assignment for assignment in engine.assignments_for_resource(resource["id"])
                     if assignment.get("legacy_kind") in {"sfx_practicos", "sonido"}]
        for assignment in misplaced:
            engine.unassign(resource["id"], assignment["scene_id"])
        if misplaced and not engine.assignments_for_resource(resource["id"]):
            engine.delete(resource["id"])
    return engine.store


def legacy_vfx_projection(store):
    """Generate the unchanged tables consumed by existing reports."""
    engine = MasterResourceEngine(store)
    output = {}
    for scene_id, assignments in engine.store["assignments"].items():
        scene = {key: [] for key in LEGACY}
        counters = {key: 0 for key in LEGACY}
        for assignment in assignments:
            resource = engine.store["resources"].get(assignment.get("resource_id"), {})
            if resource.get("resource_type") not in {"vfx", "practical_fx", "sound"}:
                continue
            default_key = {"practical_fx": "sfx_practicos", "sound": "sonido"}.get(
                resource.get("resource_type"), "vfx"
            )
            key = assignment.get("legacy_kind", default_key)
            if key not in LEGACY:
                key = "vfx"
            name_column, _ = LEGACY[key]
            counters[key] += 1
            row = {"ID": counters[key], name_column: resource.get("name", ""),
                   "Tipo": resource.get("category", ""),
                   "Responsable": assignment.get("responsible", ""),
                   "Notas": resource.get("notes", "")}
            description = assignment.get("production_notes", "")
            if key == "vfx":
                row.update({"Prioridad": assignment.get("priority", ""), "Descripción": description,
                            "Complejidad": assignment.get("complexity", ""), "Departamento": "VFX"})
            elif key == "sfx_practicos":
                row.update({"Material requerido": assignment.get("material", ""),
                            "Seguridad": assignment.get("safety", ""), "Descripción": description})
            elif key == "sonido":
                row.update({"Descripción": description, "Narrativo": assignment.get("narrative", ""),
                            "Grabación especial": assignment.get("special_recording", "")})
            else:
                row.update({"Departamento": assignment.get("responsible", ""),
                            "Prioridad": assignment.get("priority", "")})
            scene[key].append(row)
        output[str(scene_id)] = {key: pd.DataFrame(rows) for key, rows in scene.items()}
    return output
