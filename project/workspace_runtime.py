"""Thin Streamlit bridge for the framework-independent Workspace API."""

from collections.abc import Mapping
from uuid import uuid4

import streamlit as st

from project.workspace import (
    MODULE_KEYS,
    WorkspaceContext,
    build_workspace_context,
    empty_workspace_context,
    migrate_workspace_context,
    restore_workspace_context,
)


_CONTEXT_KEY = "cineplan_workspace_context"
_PROVIDERS_KEY = "cineplan_workspace_providers"
_RUNTIME_ID_KEY = "cineplan_workspace_runtime_id"
_PROVIDER_CALLBACKS = {}


def _runtime_id():
    runtime_id = st.session_state.get(_RUNTIME_ID_KEY)
    if not runtime_id:
        runtime_id = str(uuid4())
        st.session_state[_RUNTIME_ID_KEY] = runtime_id
    return runtime_id


def _load():
    value = st.session_state.get(_CONTEXT_KEY)
    return WorkspaceContext(value if isinstance(value, Mapping) else empty_workspace_context())


def _save(context):
    st.session_state[_CONTEXT_KEY] = context.to_dict()


def _mutate(method, *args, action="Contexto actualizado"):
    context = _load()
    before = context.to_dict()
    getattr(context, method)(*args)
    if context.to_dict() == before:
        return False
    context.record_event(action)
    _save(context)
    st.session_state.project_dirty = True
    return True


def begin_module(value): return _mutate("begin_module", value, action=f"Entró a {value}")
def begin_submodule(value): return _mutate("begin_submodule", value, action=f"Abrió {value}")
def set_scene(scene_id="", number="", heading=""): return _mutate("set_scene", scene_id, number, heading, action=f"Abrió escena {number}")
def set_character(value): return _mutate("set_character", value, action="Cambió personaje")
def set_location(value): return _mutate("set_location", value, action="Cambió locación")
def set_day(value): return _mutate("set_day", value, action="Cambió día de producción")
def set_strip(value): return _mutate("set_strip", value, action="Abrió Stripboard")
def set_document(value): return _mutate("set_document", value, action="Cambió documento")
def set_saved_view(value): return _mutate("set_saved_view", value, action="Cambió vista guardada")
def set_filter(name, value): return _mutate("set_filter", name, value, action=f"Actualizó filtro {name}")
def set_theme(value): return _mutate("set_theme", value, action="Cambió tema")
def set_sidebar(value): return _mutate("set_sidebar", value, action="Cambió barra lateral")
def set_zoom(value): return _mutate("set_zoom", value, action="Cambió zoom")
def set_window_layout(value): return _mutate("set_window_layout", value, action="Cambió distribución")


def current_context():
    return _load().to_dict()


def replace_current_context(context):
    """Adopt a validated serialized context without treating it as a user edit."""
    st.session_state[_CONTEXT_KEY] = WorkspaceContext(context).to_dict()


def current_submodule(default=""):
    return str(_load().get("submodule", default) or default)


def current_scene_number():
    return str((_load().get("scene", {}) or {}).get("number", ""))


def current_character():
    return str(_load().get("character", "") or "")


def scene_option_index(options):
    """Choose a selector default from CinePlan scene identity, not widget state."""
    number = current_scene_number()
    for index, option in enumerate(options):
        text = str(option)
        candidate = text.split(" | ", 1)[0].replace("Escena ", "").strip()
        if number and candidate == number:
            return index
    return 0


def notify_scene_record(scene, submodule=""):
    if scene is None:
        return
    if submodule and current_submodule() != submodule:
        return
    getter = scene.get if hasattr(scene, "get") else lambda key, default="": default
    number = getter("Escena", "")
    values = {
        "scene": {
            "id": getter("ID", number),
            "number": number,
            "heading": getter("Encabezado de escena", ""),
        },
        "location": getter("Locación", getter("Locacion", "")),
    }
    _merge_provider_values(values, f"Abrió escena {number}")
    register_workspace_provider(f"scene:{submodule or 'current'}", lambda: values)


def notify_tab_change(widget_key):
    """Translate a tab event immediately; the widget key is never persisted."""
    selected = st.session_state.get(widget_key)
    if selected:
        begin_submodule(selected)


def build_current_workspace(last_saved_timestamp=None, project_name=""):
    return build_workspace_context(current_context(), last_saved_timestamp, project_name)


def register_workspace_provider(name, provider):
    """Register and immediately evaluate one module-owned context provider."""
    if not name or not callable(provider):
        return
    registry = _PROVIDER_CALLBACKS.setdefault(_runtime_id(), {})
    registry[str(name)] = provider
    values = provider()
    if not isinstance(values, Mapping):
        return
    providers = st.session_state.get(_PROVIDERS_KEY, {})
    providers = dict(providers) if isinstance(providers, Mapping) else {}
    active = current_context()
    providers[str(name)] = {
        "module": active.get("module", ""),
        "submodule": active.get("submodule", ""),
        "values": dict(values),
    }
    st.session_state[_PROVIDERS_KEY] = providers
    _merge_provider_values(values, f"Sincronizó {name}")


def _merge_provider_values(values, action):
    context = _load()
    before = context.to_dict()
    context.merge_provider_values(values)
    if context.to_dict() != before:
        context.record_event(action)
        _save(context)
        st.session_state.project_dirty = True


def refresh():
    """Merge only explicit provider output; never inspect widget state."""
    providers = st.session_state.get(_PROVIDERS_KEY, {})
    if not isinstance(providers, Mapping):
        return current_context()
    callbacks = _PROVIDER_CALLBACKS.get(_runtime_id(), {})
    active = current_context()
    for name, provider in providers.items():
        if not isinstance(provider, Mapping):
            continue
        if provider.get("module") != active.get("module"):
            continue
        if provider.get("submodule") != active.get("submodule"):
            continue
        callback = callbacks.get(name)
        values = callback() if callable(callback) else provider.get("values")
        if isinstance(values, Mapping):
            provider["values"] = dict(values)
            _merge_provider_values(values, f"Sincronizó {name}")
    return current_context()


def _available_scene_numbers():
    scenes = st.session_state.get("scenes_df")
    if hasattr(scenes, "columns") and "Escena" in scenes.columns:
        return scenes["Escena"].astype(str).tolist()
    return []


def _available_characters():
    characters = st.session_state.get("characters_df")
    if hasattr(characters, "columns"):
        for column in ("Personaje", "Nombre"):
            if column in characters.columns:
                return characters[column].astype(str).tolist()
    return []


def apply_workspace_context(context):
    scene_numbers = _available_scene_numbers()
    plan = restore_workspace_context(
        context, MODULE_KEYS, scene_numbers, _available_characters(), scene_numbers,
    )
    st.session_state[_CONTEXT_KEY] = plan["context"]
    st.session_state.current_view = plan["view"]
    if plan["module_key"] and plan["module_key"] != "dashboard":
        st.session_state.main_menu = plan["module_key"]
    st.session_state.workspace_restore_pending = False
    return plan["view"] == "modules"


def stage_workspace_after_open(context):
    context = migrate_workspace_context(context) if isinstance(context, Mapping) and context else {}
    st.session_state.workspace_pending_context = dict(context)
    st.session_state.current_view = "dashboard"
    if context and context.get("automatic_restore"):
        apply_workspace_context(context)
        return "restored"
    st.session_state.workspace_restore_pending = bool(context)
    return "pending" if context else "dashboard"


def go_to_dashboard():
    begin_module("Proyecto")
    begin_submodule("Dashboard")
    st.session_state.current_view = "dashboard"
    st.session_state.workspace_restore_pending = False


def set_automatic_restore(enabled):
    _mutate("set_automatic_restore", enabled, action="Actualizó restauración automática")


def mark_project_dirty():
    st.session_state.project_dirty = True
