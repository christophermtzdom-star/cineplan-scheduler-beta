"""VFX instantiation of the shared Breakdown Workspace."""

import pandas as pd
import streamlit as st

from components.header import render_section_header
from components.icons import VFX
from modules.breakdown.framework.breakdown_workspace import render_workspace
from modules.breakdown.framework.resource_engine import MasterResourceEngine
from modules.breakdown.props_resources import migrate_legacy_props
from modules.breakdown.vfx_resources import (
    VFX_CONFIG,
    VFX_RESOURCE_CONFIGS,
    legacy_vfx_projection,
    migrate_legacy_vfx,
)
from project.workspace_runtime import notify_scene_record, scene_option_index


def _scene_options():
    scenes = st.session_state.get("scenes_df", pd.DataFrame())
    return [f'{row.get("Escena", "")} | {row.get("Encabezado de escena", "")}'
            for _, row in scenes.iterrows()]


def _scene_record(scene_id):
    scenes = st.session_state.get("scenes_df", pd.DataFrame())
    matches = scenes[scenes.get("Escena", pd.Series(dtype=str)).astype(str) == str(scene_id)]
    return matches.iloc[0].to_dict() if not matches.empty else {}


def _locations():
    scenes = st.session_state.get("scenes_df", pd.DataFrame())
    return {str(row.get("Escena", "")): row.get("Locación", row.get("LocaciÃ³n", ""))
            for _, row in scenes.iterrows()}


def ensure_vfx_resource_store():
    store = st.session_state.get("breakdown_resource_store")
    if not isinstance(store, dict):
        store = migrate_legacy_props(
            st.session_state.get("breakdown_props_data", {}),
            scene_locations=_locations(),
        )
    store = migrate_legacy_vfx(
        st.session_state.get("breakdown_vfx_sound_data", {}),
        store,
        scene_locations=_locations(),
    )
    st.session_state.breakdown_resource_store = store
    st.session_state.breakdown_vfx_sound_data = legacy_vfx_projection(store)
    return store


def _persist_projection():
    st.session_state.breakdown_vfx_sound_data = legacy_vfx_projection(
        st.session_state.breakdown_resource_store
    )
    st.session_state.project_dirty = True


def render_vfx_page():
    render_section_header(
        icon=VFX, title="VFX / Efectos Prácticos / Sonido",
        description="Recursos únicos del proyecto, asignados por referencia a cada escena.",
    )
    options = _scene_options()
    if not options:
        st.warning("No hay escenas disponibles.")
        return
    selected = st.selectbox("Escena de trabajo", options, index=scene_option_index(options),
                            key="vfx_workspace_scene")
    scene_id = selected.split(" | ", 1)[0]
    record = _scene_record(scene_id)
    notify_scene_record(record, "VFX / Efectos Prácticos / Sonido")
    engine = MasterResourceEngine(ensure_vfx_resource_store())
    render_workspace(
        engine, VFX_CONFIG, scene_id, record, on_change=_persist_projection,
        resource_configs=VFX_RESOURCE_CONFIGS,
    )
