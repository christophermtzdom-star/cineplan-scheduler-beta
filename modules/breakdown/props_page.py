"""Props & Utilería pilot for the Breakdown Workspace Framework."""

import pandas as pd
import streamlit as st

from components.header import render_section_header
from components.icons import PROPS
from modules.breakdown.framework.breakdown_workspace import render_workspace
from modules.breakdown.framework.resource_engine import MasterResourceEngine
from modules.breakdown.props_resources import PROP_CONFIG, legacy_props_projection, migrate_legacy_props
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
    result = {}
    for _, row in scenes.iterrows():
        result[str(row.get("Escena", ""))] = row.get("Locación", row.get("LocaciÃ³n", ""))
    return result


def ensure_props_resource_store():
    store = st.session_state.get("breakdown_resource_store")
    if not isinstance(store, dict):
        store = migrate_legacy_props(
            st.session_state.get("breakdown_props_data", {}),
            scene_locations=_locations(),
        )
        st.session_state.breakdown_resource_store = store
    # The old tables are a generated read model for current reports and APIs.
    st.session_state.breakdown_props_data = legacy_props_projection(store)
    return store


def _persist_projection():
    st.session_state.breakdown_props_data = legacy_props_projection(
        st.session_state.breakdown_resource_store
    )
    st.session_state.project_dirty = True


def render_props_page():
    render_section_header(
        icon=PROPS, title="Utilería",
        description="Recursos únicos del proyecto, asignados por referencia a cada escena.",
    )
    options = _scene_options()
    if not options:
        st.warning("No hay escenas disponibles.")
        return
    selected = st.selectbox("Escena de trabajo", options, index=scene_option_index(options),
                            key="props_workspace_scene")
    scene_id = selected.split(" | ", 1)[0]
    record = _scene_record(scene_id)
    notify_scene_record(record, "Utilería")
    engine = MasterResourceEngine(ensure_props_resource_store())
    render_workspace(engine, PROP_CONFIG, scene_id, record, on_change=_persist_projection)
