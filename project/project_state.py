from collections.abc import Mapping
from datetime import datetime

import pandas as pd
import streamlit as st


_WORKFLOW_KEYS = (
    "importar", "revision", "breakdown",
    "stripboard", "plan_rodaje", "hojas_llamado",
)
_COMPLETE_VALUES = {"completado", "completa", "revisado", "revisada", "sí", "si", "listo"}
_BREAKDOWN_COMPLETE_VALUES = {"revisado", "listo para exportar"}


def _clean_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _as_dataframe(value):
    if isinstance(value, pd.DataFrame):
        return value.fillna("").copy()
    if isinstance(value, (list, tuple)):
        try:
            return pd.DataFrame(value).fillna("")
        except (TypeError, ValueError):
            pass
    return pd.DataFrame()


def register_recent_activity(
    title, detail="", icon="history", category="general", scene=None
):
    """Registra una actividad real, evitando duplicados inmediatos."""
    activity = st.session_state.get("recent_activity", [])
    if not isinstance(activity, list):
        activity = []

    now = datetime.now()
    record = {
        "title": _clean_text(title),
        "detail": _clean_text(detail),
        "time": now.strftime("%d/%m/%Y %H:%M"),
        "icon": _clean_text(icon) or "history",
        "category": _clean_text(category) or "general",
        "scene": _clean_text(scene),
        "created_at": now.isoformat(timespec="seconds"),
    }
    if not record["title"]:
        return

    if activity:
        latest = activity[0] if isinstance(activity[0], Mapping) else {}
        same_event = all(
            _clean_text(latest.get(key)) == record[key]
            for key in ("title", "detail", "category", "scene")
        )
        try:
            latest_time = datetime.fromisoformat(_clean_text(latest.get("created_at")))
            immediate = (now - latest_time).total_seconds() < 5
        except ValueError:
            immediate = False
        if same_event and immediate:
            st.session_state.recent_activity = activity[:10]
            return

    st.session_state.recent_activity = [record, *activity][:10]


def _has_script():
    return any(_clean_text(st.session_state.get(key)) for key in (
        "nombre_archivo_guion", "script_text"
    ))


def _scene_key(value):
    text = _clean_text(value)
    try:
        number = float(text)
        return str(int(number)) if number.is_integer() else text
    except ValueError:
        return text


def _octavos_complete(row):
    return any(_clean_text(row.get(key)) not in {"", "0", "0/8"} for key in (
        "Octavos finales", "Octavos", "octavos"
    ))


def _review_metrics(scenes_df, project_info):
    total = len(scenes_df)
    if not total:
        return 0.0, False, 0

    if "Estado" in scenes_df.columns:
        reviewed = int(
            scenes_df["Estado"].map(_clean_text).str.casefold().eq("revisado").sum()
        )
    else:
        reviewed = 0
    octavos = sum(_octavos_complete(row) for row in scenes_df.to_dict(orient="records"))
    locations = 0
    if "Locación" in scenes_df.columns:
        locations = int(scenes_df["Locación"].map(_clean_text).ne("").sum())

    checklist = _as_dataframe(st.session_state.get("validation_checklist"))
    checklist_ratio = 0.0
    if not checklist.empty and "Estado" in checklist.columns:
        values = checklist["Estado"].map(_clean_text).str.casefold()
        checklist_ratio = float(values.isin(_COMPLETE_VALUES).mean())

    characters = _as_dataframe(st.session_state.get("characters_df"))
    project_name = _clean_text(project_info.get("nombre"))
    project_ready = bool(project_name and project_name.casefold() != "proyecto sin título")
    fraction = (
        0.60 * (reviewed / total)
        + 0.25 * (octavos / total)
        + 0.05 * (locations / total)
        + 0.05 * (1.0 if not characters.empty else 0.0)
        + 0.05 * checklist_ratio
    )
    complete = reviewed == total and octavos == total and project_ready
    return min(1.0, fraction), complete, reviewed


def _nested_record_count(value):
    if isinstance(value, pd.DataFrame):
        return len(value)
    if isinstance(value, Mapping):
        nested = [
            item for item in value.values()
            if isinstance(item, (Mapping, pd.DataFrame, list, tuple))
        ]
        if nested:
            return sum(_nested_record_count(item) for item in nested)
        return int(any(_clean_text(item) for item in value.values()))
    if isinstance(value, (list, tuple)):
        return sum(_nested_record_count(item) for item in value)
    return 0


def _breakdown_metrics(scenes_df):
    total = len(scenes_df)
    saved = st.session_state.get("breakdown_scene_data", {})
    if not total or not isinstance(saved, Mapping):
        return 0.0, False, 0

    valid = complete = 0
    for row in scenes_df.to_dict(orient="records"):
        scene_number = _scene_key(row.get("Escena"))
        record = saved.get(scene_number, saved.get(_clean_text(row.get("Escena")), {}))
        if not isinstance(record, Mapping) or not record:
            continue
        has_scene_info = bool(
            _clean_text(record.get("Escena", scene_number))
            and _clean_text(record.get("Encabezado de escena", row.get("Encabezado de escena")))
        )
        if has_scene_info:
            valid += 1
            if _clean_text(record.get("Estado breakdown")).casefold() in _BREAKDOWN_COMPLETE_VALUES:
                complete += 1

    department_keys = (
        "breakdown_cast_data", "breakdown_props_data",
        "breakdown_wardrobe_makeup_data", "breakdown_vfx_sound_data",
        "breakdown_extras_data", "breakdown_production_notes_data",
    )
    department_records = sum(
        _nested_record_count(st.session_state.get(key)) for key in department_keys
    )
    is_complete = valid == total and complete == total
    fraction = 0.70 * (valid / total) + 0.25 * (complete / total)
    fraction += 0.05 * min(1.0, department_records / total)
    return (1.0 if is_complete else min(1.0, fraction)), is_complete, complete


def _workflow_caption(workflow):
    active = next(
        (index for index, key in enumerate(_WORKFLOW_KEYS, start=1)
         if workflow[key] == "en_progreso"),
        None,
    )
    if active == 1:
        return "Importación del guion en progreso", "Importar y analizar el guion", active
    if active == 2:
        return "Revisión en progreso", "Completar la revisión del guion", active
    if active == 3:
        return "Breakdown en progreso", "Completar el Breakdown", active
    completed = sum(workflow[key] == "completado" for key in _WORKFLOW_KEYS)
    if completed:
        return f"Paso {completed} de 6", "Continuar con el flujo de trabajo", completed
    return "Proyecto sin iniciar", "Importar un guion", 0


def _track_dashboard_changes(workflow, project_info):
    project_signature = tuple(
        _clean_text(project_info.get(key))
        for key in ("nombre", "director", "productor", "version_guion")
    )
    previous_project = st.session_state.get("_dashboard_project_signature")
    if previous_project is not None and tuple(previous_project) != project_signature:
        register_recent_activity(
            "Información del proyecto actualizada",
            project_signature[0] or "Datos generales del proyecto",
            "edit_note", "proyecto",
        )
    st.session_state._dashboard_project_signature = project_signature

    previous_workflow = st.session_state.get("_dashboard_workflow_snapshot")
    if isinstance(previous_workflow, Mapping):
        transition_labels = {
            "importar": "Importación del guion",
            "revision": "Revisión del proyecto",
            "breakdown": "Breakdown del proyecto",
        }
        for key, label in transition_labels.items():
            old, new = previous_workflow.get(key), workflow.get(key)
            if old != new and new in {"en_progreso", "completado"}:
                status = "completado" if new == "completado" else "en progreso"
                register_recent_activity(
                    f"{label}: {status}",
                    "El estado del flujo de trabajo cambió.",
                    "timeline", "flujo",
                )
    st.session_state._dashboard_workflow_snapshot = dict(workflow)


def get_dashboard_data():
    """Devuelve información dinámica y segura para el Dashboard."""
    scenes_df = _as_dataframe(st.session_state.get("scenes_df"))
    characters_df = _as_dataframe(st.session_state.get("characters_df"))
    project_info = st.session_state.get("project_info", {})
    project_info = project_info if isinstance(project_info, Mapping) else {}
    scenes_count = len(scenes_df)

    script_exists = _has_script()
    import_fraction = 1.0 if scenes_count else (0.5 if script_exists else 0.0)
    import_status = "completado" if scenes_count else ("en_progreso" if script_exists else "bloqueado")

    review_fraction, review_complete, reviewed_count = _review_metrics(scenes_df, project_info)
    breakdown_fraction, breakdown_complete, breakdown_count = _breakdown_metrics(scenes_df)
    workflow = {
        "importar": import_status,
        "revision": "bloqueado",
        "breakdown": "bloqueado",
        "stripboard": "bloqueado",
        "plan_rodaje": "bloqueado",
        "hojas_llamado": "bloqueado",
    }
    if scenes_count:
        workflow["revision"] = "completado" if review_complete else "en_progreso"
    if review_complete:
        workflow["breakdown"] = "completado" if breakdown_complete else "en_progreso"

    progress = round(100 * (import_fraction + review_fraction + breakdown_fraction) / 6)
    progress = max(0, min(progress, 100))
    caption, next_step, current_step = _workflow_caption(workflow)
    _track_dashboard_changes(workflow, project_info)

    locations_count = 0
    if "Locación" in scenes_df.columns:
        locations_count = scenes_df["Locación"].map(_clean_text).replace("", pd.NA).nunique()

    activity = st.session_state.get("recent_activity", [])
    if not isinstance(activity, list):
        activity = []
        st.session_state.recent_activity = activity

    return {
        "project": {
            "name": project_info.get("nombre", "Proyecto sin título"),
            "director": project_info.get("director", ""),
            "producer": project_info.get("productor", ""),
        },
        "script": {
            "name": st.session_state.get("nombre_archivo_guion", ""),
            "type": st.session_state.get("tipo_archivo_guion", ""),
            "date": st.session_state.get("fecha_importacion_guion", ""),
        },
        "stats": {
            "scenes": scenes_count,
            "characters": len(characters_df),
            "locations": int(locations_count),
            "total_eighths": sum(_octavos_complete(row) for row in scenes_df.to_dict(orient="records")),
            "estimated_duration": "-",
            "shoot_days": 0,
            "call_sheets": 0,
            "completed_breakdown": breakdown_count,
            "reviewed_scenes": reviewed_count,
        },
        "progress": progress,
        "progress_caption": caption,
        "current_step": current_step,
        "next_step": next_step,
        "workflow": workflow,
        "recent_activity": activity[:10],
        "quick_actions": [
            {"id": "importar", "title": "Importar Guion"},
            {"id": "revision", "title": "Revisar y Modificar"},
            {"id": "breakdown", "title": "Breakdown"},
            {"id": "stripboard", "title": "Stripboard"},
            {"id": "plan_rodaje", "title": "Plan de Rodaje"},
            {"id": "hojas_llamado", "title": "Hojas de Llamado"},
        ],
    }
