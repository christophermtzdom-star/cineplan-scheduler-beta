"""Public project-management operations used by CinePlan controls."""

import json
from io import StringIO
from pathlib import Path

import streamlit as st

from project.project_io import ProjectIOError, read_json, read_project, write_project
from project.project_metadata import build_metadata
from project.project_paths import (
    NativeDialogError,
    choose_open_path,
    choose_save_path,
    clear_current_path,
    remember_current_path,
)
from project.project_validator import ProjectValidationError
from project.workspace_runtime import (
    build_current_workspace, refresh, replace_current_context, stage_workspace_after_open,
)


def build_current_project_payload(payload_builder):
    """Reuse the application's canonical serializer and return its object payload."""
    payload = payload_builder()
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise TypeError("El proyecto actual no pudo prepararse para guardarse.")
    return payload


def _session_metadata():
    return {
        "project_id": st.session_state.get("project_id"),
        "created_at": st.session_state.get("project_created_at"),
    }


def _store_metadata(metadata):
    st.session_state.project_id = metadata["project_id"]
    st.session_state.project_created_at = metadata["created_at"]
    st.session_state.project_last_saved = metadata["last_saved"]


def _save_to(path, payload_builder):
    metadata = build_metadata(_session_metadata())
    refresh()
    project_name = st.session_state.get("project_info", {}).get("nombre", "")
    workspace = build_current_workspace(metadata["last_saved"], project_name)
    container = {
        **metadata,
        "workspace_context": workspace,
        "project": build_current_project_payload(payload_builder),
    }
    write_project(path, container)
    replace_current_context(workspace)
    remember_current_path(path)
    _store_metadata(metadata)
    st.session_state.project_dirty = False
    st.toast("Proyecto guardado correctamente.", icon=":material/check_circle:")
    return True


def save_project_as(payload_builder):
    try:
        name = st.session_state.get("project_info", {}).get("nombre")
        path = choose_save_path(name)
        if path is None:
            return False
        return _save_to(path, payload_builder)
    except (NativeDialogError, ProjectIOError) as error:
        st.error(str(error) or "No se pudo guardar el proyecto.")
        return False
    except (TypeError, ValueError):
        st.error("No se pudo guardar el proyecto.")
        return False


def save_current_project(payload_builder):
    current_path = st.session_state.get("current_project_path", "")
    already_saved = st.session_state.get("project_has_been_saved", False)
    if not current_path or not already_saved or Path(current_path).suffix.casefold() != ".cps":
        return save_project_as(payload_builder)
    try:
        return _save_to(Path(current_path), payload_builder)
    except ProjectIOError as error:
        st.error(str(error) or "No se pudo guardar el proyecto.")
        return False
    except (TypeError, ValueError):
        st.error("No se pudo guardar el proyecto.")
        return False


def _restore_payload(payload, payload_loader):
    payload_loader(StringIO(json.dumps(payload, ensure_ascii=False)))


def open_project(payload_loader):
    try:
        path = choose_open_path()
        if path is None:
            return False
        if path.suffix.casefold() == ".json":
            _restore_payload(read_json(path), payload_loader)
            clear_current_path()
            stage_workspace_after_open({})
            st.session_state.project_dirty = False
            st.warning(
                "Este proyecto utiliza el formato anterior. Guárdalo como "
                "Proyecto CinePlan (.cps) para actualizarlo."
            )
            return True

        container = read_project(path)
        _restore_payload(container["project"], payload_loader)
        remember_current_path(path)
        _store_metadata(container)
        workspace = container.get("workspace_context", container.get("workspace", {}))
        stage_workspace_after_open(workspace)
        st.session_state.project_dirty = False
        st.toast("Proyecto abierto correctamente.", icon=":material/folder_open:")
        return True
    except ProjectValidationError as error:
        st.error(str(error))
    except (NativeDialogError, ProjectIOError) as error:
        st.error(str(error) or "No se pudo abrir el proyecto seleccionado.")
    except (TypeError, ValueError):
        st.error("No se pudo abrir el proyecto seleccionado.")
    return False
