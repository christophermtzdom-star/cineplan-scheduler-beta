"""Workspace restoration dialog shown after opening a CinePlan project."""

from datetime import datetime, timezone
from html import escape

import streamlit as st

from project.project_metadata import CINEPLAN_VERSION
from project.workspace import format_saved_datetime
from project.workspace_runtime import (
    apply_workspace_context,
    go_to_dashboard,
    set_automatic_restore,
)


def _summary():
    scenes = st.session_state.get("scenes_df")
    characters = st.session_state.get("characters_df")
    scene_count = len(scenes) if hasattr(scenes, "__len__") else 0
    character_count = len(characters) if hasattr(characters, "__len__") else 0
    locations = 0
    if scene_count and hasattr(scenes, "columns") and "Locación" in scenes.columns:
        clean_locations = scenes["Locación"].fillna("").astype(str).str.strip()
        locations = int(clean_locations[clean_locations.ne("")].nunique())
    breakdown = st.session_state.get("breakdown_scene_data", {})
    breakdown_count = len(breakdown) if isinstance(breakdown, dict) else 0
    production_days = st.session_state.get("production_days", [])
    return {
        "Escenas": scene_count,
        "Personajes": character_count,
        "Locaciones": locations,
        "Breakdown": f"{breakdown_count}/{scene_count}",
        "Stripboard": f"{scene_count} escenas" if scene_count else "Sin escenas",
        "Rodaje": "En progreso" if production_days else "Pendiente",
        "Llamados": "Pendiente",
    }


def _scene_description(scene_number):
    records = st.session_state.get("breakdown_scene_data", {})
    if not isinstance(records, dict):
        return ""
    record = records.get(str(scene_number), {})
    if not isinstance(record, dict):
        return ""
    return str(record.get("Descripción") or record.get("Descripción breve") or "").strip()


def _relative_time(value):
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        minutes = max(0, int((datetime.now(timezone.utc) - moment).total_seconds() // 60))
        if minutes < 1:
            return "Ahora"
        if minutes < 60:
            return f"Hace {minutes} minutos"
        hours = minutes // 60
        return f"Hace {hours} hora{'s' if hours != 1 else ''}"
    except (TypeError, ValueError):
        return "—"


@st.dialog("Reanudar Proyecto", width="large")
def _workspace_dialog():
    workspace = st.session_state.get("workspace_pending_context", {})
    project_name = st.session_state.get("current_project_filename") or st.session_state.get(
        "project_info", {}
    ).get("nombre", "Proyecto CinePlan")
    saved_date, saved_time = format_saved_datetime(
        workspace.get("timestamp") or st.session_state.get("project_last_saved")
    )
    st.caption("Proyecto restaurado correctamente.")
    scene = workspace.get("scene", {})
    scene_number = scene.get("number", "")
    description = _scene_description(scene_number)
    scene_lines = "".join(
        f'<div style="margin-top:5px;color:#cbd5e1;">{escape(str(value))}</div>'
        for value in (
            f"Escena {scene_number}" if scene_number else "",
            scene.get("heading", ""),
            description,
        ) if value
    )
    last_modified = workspace.get("last_modified_at") or workspace.get("timestamp")
    st.markdown(
        f"**Proyecto**  \n{project_name}  \n\n"
        f"**Guardado:** {saved_date} · {saved_time}  \n"
        f"**CinePlan:** Versión {workspace.get('cineplan_version', CINEPLAN_VERSION)}"
    )
    st.markdown("### Último punto de trabajo")
    st.markdown(
        '<div style="padding:18px 20px;border:1px solid rgba(148,163,184,.2);'
        'border-radius:14px;background:#172033;box-shadow:0 8px 24px rgba(2,6,23,.14);">'
        f'<div style="font-size:18px;font-weight:750;color:#f8fafc;">{escape(str(workspace.get("module", "Proyecto")))}</div>'
        f'<div style="margin-top:3px;color:#f8b400;font-weight:650;">{escape(str(workspace.get("submodule", "Dashboard")))}</div>'
        f'{scene_lines}'
        f'<div style="margin-top:12px;font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:#94a3b8;">Última modificación</div>'
        f'<div style="color:#cbd5e1;">{_relative_time(last_modified)}</div>'
        f'<div style="margin-top:8px;color:#94a3b8;font-size:12px;">Última acción: {escape(str(workspace.get("last_action") or "—"))}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Estado del proyecto")
    stats = _summary()
    columns = st.columns(3)
    for index, (label, value) in enumerate(stats.items()):
        columns[index % 3].metric(label, value)

    history = workspace.get("history", [])
    duration = workspace.get("session_duration_seconds")
    if isinstance(duration, (int, float)):
        minutes = max(1, round(duration / 60))
        st.caption(f"Duración aproximada de la última sesión: {minutes} min")
    if history:
        with st.expander("Historial del Workspace"):
            for entry in history[:10]:
                date, time = format_saved_datetime(entry.get("timestamp"))
                detail = " · ".join(filter(None, (
                    entry.get("module"), entry.get("submodule"),
                    f"Escena {entry.get('scene')}" if entry.get("scene") else "",
                    entry.get("character", ""), entry.get("location", ""),
                    f"Día {entry.get('day')}" if entry.get("day") else "",
                    f"Strip {entry.get('strip')}" if entry.get("strip") else "",
                    entry.get("document", ""), entry.get("action", ""),
                )))
                st.caption(f"{date} · {time} — {detail}")

    remember = st.checkbox(
        "Recordar mi decisión para este proyecto",
        value=bool(workspace.get("automatic_restore", False)),
        key="workspace_remember_choice_dialog",
    )
    primary, secondary, close = st.columns((1.45, 1, .65))
    if primary.button("▶ Continuar donde lo dejé", type="primary", use_container_width=True):
        workspace["automatic_restore"] = remember
        set_automatic_restore(remember)
        apply_workspace_context(workspace)
        st.rerun()
    if secondary.button("🏠 Ir al Dashboard", use_container_width=True):
        set_automatic_restore(False)
        go_to_dashboard()
        st.rerun()
    if close.button("Cerrar", use_container_width=True):
        go_to_dashboard()
        st.rerun()


def render_workspace_restore_dialog():
    if st.session_state.get("workspace_restore_pending", False):
        _workspace_dialog()
