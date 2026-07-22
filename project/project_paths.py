"""Native path selection and active-project path helpers."""

import re
from pathlib import Path

import streamlit as st

from project.project_metadata import PROJECT_EXTENSION


class NativeDialogError(RuntimeError):
    """The local desktop file dialog could not be displayed."""


def safe_default_filename(project_name):
    name = str(project_name or "Proyecto CinePlan").strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).rstrip(". ")
    return f"{name or 'Proyecto CinePlan'}{PROJECT_EXTENSION}"


def enforce_cps_extension(path):
    selected = Path(path)
    if selected.suffix.casefold() != PROJECT_EXTENSION:
        selected = selected.with_suffix(PROJECT_EXTENSION)
    return selected.resolve()


def _dialog(kind, **options):
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        try:
            result = getattr(filedialog, kind)(parent=root, **options)
        finally:
            root.destroy()
        return result or None
    except Exception as error:
        raise NativeDialogError(
            "No fue posible abrir el diálogo nativo de archivos. "
            "CinePlan debe ejecutarse localmente con acceso al escritorio."
        ) from error


def choose_save_path(project_name):
    selected = _dialog(
        "asksaveasfilename",
        title="Guardar Proyecto CinePlan",
        defaultextension=PROJECT_EXTENSION,
        initialfile=safe_default_filename(project_name),
        filetypes=(("Proyecto CinePlan", "*.cps"),),
    )
    return enforce_cps_extension(selected) if selected else None


def choose_open_path():
    selected = _dialog(
        "askopenfilename",
        title="Abrir Proyecto",
        filetypes=(
            ("Proyecto CinePlan", "*.cps"),
            ("Proyecto CinePlan anterior", "*.json"),
        ),
    )
    return Path(selected).resolve() if selected else None


def remember_current_path(path):
    path = Path(path).resolve()
    st.session_state.current_project_path = str(path)
    st.session_state.current_project_filename = path.name
    st.session_state.project_has_been_saved = path.suffix.casefold() == PROJECT_EXTENSION


def clear_current_path():
    st.session_state.current_project_path = ""
    st.session_state.current_project_filename = ""
    st.session_state.project_has_been_saved = False
