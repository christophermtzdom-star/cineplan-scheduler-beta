"""Placeholder controls for future Stripboard filtering and saved views."""

import streamlit as st
from project.workspace_runtime import register_workspace_provider, set_day, set_filter

from modules.stripboard.config import VISIBLE_INFORMATION_OPTIONS


def _section_heading(icon, title):
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0 10px;">'
        f'<span class="material-symbols-rounded" style="font-size:19px;color:#f8b400;">{icon}</span>'
        f'<strong style="font-size:14px;color:#f8fafc;">{title}</strong></div>',
        unsafe_allow_html=True,
    )


def render_design_filters():
    _section_heading("filter_alt", "Filtros")
    visibility = st.selectbox(
        "Mostrar escenas",
        ("Todas las escenas", "Solo seleccionadas", "Ocultar seleccionadas"),
        disabled=True,
        key="stripboard_filter_scene_visibility",
    )
    scene_types = st.multiselect(
        "INT / EXT / I-E / Especial",
        ("INT", "EXT", "I/E", "Especial"),
        disabled=True,
        key="stripboard_filter_scene_type",
    )
    times = st.multiselect(
        "Tiempo",
        ("Día", "Noche", "Amanecer", "Atardecer"),
        disabled=True,
        key="stripboard_filter_time",
    )
    location = st.selectbox("Locación", ("Todas",), disabled=True, key="stripboard_filter_location")
    characters = st.selectbox("Personajes", ("Todos",), disabled=True, key="stripboard_filter_characters")
    status = st.selectbox("Estado", ("Todos",), disabled=True, key="stripboard_filter_status")
    filters = {
        "scene_visibility": visibility, "scene_type": scene_types, "time": times,
        "location": location, "characters": characters, "status": status,
    }
    for name, value in filters.items():
        set_filter(name, value)
    register_workspace_provider("stripboard:filters", lambda: {"filters": filters})

    st.divider()
    _section_heading("visibility", "Información visible")
    for index, option in enumerate(VISIBLE_INFORMATION_OPTIONS):
        st.checkbox(
            option,
            value=option in {"Página", "Octavos", "Personajes", "Props", "Estado", "Notas"},
            disabled=True,
            key=f"stripboard_visible_{index}",
        )

    st.divider()
    _section_heading("bookmark", "Vistas guardadas")
    st.button("Guardar vista", icon=":material/bookmark_add:", disabled=True, use_container_width=True)
    left, right = st.columns(2)
    with left:
        st.button("Cargar vista", disabled=True, use_container_width=True)
    with right:
        st.button("Nueva vista", disabled=True, use_container_width=True)


def render_planning_filters():
    _section_heading("tune", "Filtros de planificación")
    st.selectbox("Unidad", ("Todas las unidades",), disabled=True, key="planning_filter_unit")
    day = st.selectbox("Jornada", ("Todas las jornadas",), disabled=True, key="planning_filter_day")
    set_day(day)
    register_workspace_provider("planning:day", lambda: {"day": day})
    st.multiselect(
        "Disponibilidad",
        ("Reparto", "Locaciones", "Equipo"),
        disabled=True,
        key="planning_filter_availability",
    )
    st.caption("Los controles se habilitarán cuando exista información de planificación.")
