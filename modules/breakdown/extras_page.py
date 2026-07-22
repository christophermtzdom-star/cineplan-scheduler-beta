"""Extras and vehicles instantiation of the shared Breakdown Workspace."""

import pandas as pd
import streamlit as st

from components.header import render_section_header
from components.icons import EXTRAS
from modules.breakdown.extras_resources import (
    EXTRA_CONFIG,
    EXTRAS_RESOURCE_CONFIGS,
    legacy_extras_projection,
    migrate_legacy_extras,
)
from modules.breakdown.framework.breakdown_workspace import render_workspace
from modules.breakdown.framework.resource_engine import MasterResourceEngine
from modules.breakdown.props_resources import migrate_legacy_props
from modules.breakdown.vfx_resources import migrate_legacy_vfx
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


def ensure_extras_resource_store():
    store = st.session_state.get("breakdown_resource_store")
    if not isinstance(store, dict):
        store = migrate_legacy_props(
            st.session_state.get("breakdown_props_data", {}), scene_locations=_locations()
        )
        store = migrate_legacy_vfx(
            st.session_state.get("breakdown_vfx_sound_data", {}), store,
            scene_locations=_locations(),
        )
    store = migrate_legacy_extras(
        st.session_state.get("breakdown_extras_data", {}), store,
        scene_locations=_locations(),
    )
    st.session_state.breakdown_resource_store = store
    st.session_state.breakdown_extras_data = legacy_extras_projection(store)
    return store


def _persist_projection():
    st.session_state.breakdown_extras_data = legacy_extras_projection(
        st.session_state.breakdown_resource_store
    )
    st.session_state.project_dirty = True


def render_extras_page():
    render_section_header(
        icon=EXTRAS, title="Extras / Vehículos",
        description="Extras y vehículos únicos del proyecto, asignados por referencia a cada escena.",
    )
    options = _scene_options()
    if not options:
        st.warning("No hay escenas disponibles.")
        return
    selected = st.selectbox("Escena de trabajo", options, index=scene_option_index(options),
                            key="extras_workspace_scene")
    scene_id = selected.split(" | ", 1)[0]
    record = _scene_record(scene_id)
    notify_scene_record(record, "Extras / Vehículos")
    engine = MasterResourceEngine(ensure_extras_resource_store())
    render_workspace(
        engine, EXTRA_CONFIG, scene_id, record, on_change=_persist_projection,
        resource_configs=EXTRAS_RESOURCE_CONFIGS,
    )
