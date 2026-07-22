from collections.abc import Mapping

import pandas as pd
import streamlit as st
from project.workspace_runtime import notify_scene_record, scene_option_index

from components.header import render_section_header
from components.icons import (
    ADD,
    ANALYTICS,
    DELETE,
    NOTE,
    PRODUCTION,
    SAVE,
    SCENE,
    TASK,
)
from components.panel import cine_panel


_NOTES_KEY = "notas_produccion"
_NOTE_COLUMNS = ["ID", "Departamento", "Instrucción", "Observaciones"]

_LEGACY_TABLES = {
    "riesgos_seguridad": [
        "ID", "Riesgo", "Departamento", "Nivel riesgo",
        "Medida preventiva", "Notas",
    ],
    "permisos_logistica": [
        "ID", "Requerimiento", "Tipo", "Responsable", "Estado", "Notas",
    ],
    "continuidad_critica": [
        "ID", "Elemento continuidad", "Importancia", "Departamento", "Notas",
    ],
}

_DEPARTMENTS = [
    "Producción",
    "Dirección",
    "Fotografía",
    "Cámara",
    "Iluminación",
    "Grip",
    "Arte",
    "Utilería",
    "Vestuario",
    "Maquillaje",
    "Sonido",
    "Efectos Prácticos",
    "VFX / Postproducción",
    "Casting",
    "Continuidad",
    "Transporte",
    "Otro...",
]


def _icon_label(icon, label):
    return f":material/{icon}: {label}"


def _clean_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _normalize_dataframe(value, columns):
    if isinstance(value, pd.DataFrame):
        dataframe = value.copy()
    elif value is None:
        dataframe = pd.DataFrame(columns=columns)
    else:
        dataframe = pd.DataFrame(value)
    for column in columns:
        if column not in dataframe.columns:
            dataframe[column] = ""
    return dataframe[columns].fillna("").copy()


def _build_scene_options():
    scenes_df = st.session_state.get("scenes_df", pd.DataFrame())
    if not isinstance(scenes_df, pd.DataFrame) or scenes_df.empty:
        return []
    return [
        f'{row.get("Escena", "")} | {row.get("Encabezado de escena", "")}'
        for _, row in scenes_df.iterrows()
    ]


def _get_scene(scene_number):
    scenes_df = st.session_state.get("scenes_df", pd.DataFrame())
    if not isinstance(scenes_df, pd.DataFrame) or "Escena" not in scenes_df.columns:
        return None
    matches = scenes_df[scenes_df["Escena"].astype(str) == str(scene_number)]
    return None if matches.empty else matches.iloc[0]


def _render_scene_selector(scene_options):
    with cine_panel(
        title=_icon_label(SCENE, "Escena actual"),
        subtitle="Selecciona la escena cuyas instrucciones de producción deseas administrar.",
    ):
        selected = st.selectbox(
            "Seleccionar escena", scene_options,
            index=scene_option_index(scene_options), key="production_notes_selector"
        )
        scene_number = selected.split(" | ")[0]
        scene = _get_scene(scene_number)
        notify_scene_record(scene, "Notas de producción")
        if scene is not None:
            columns = st.columns([0.7, 2.4, 1, 1])
            columns[0].metric("Escena", scene.get("Escena", "-") or "-")
            columns[1].metric(
                "Encabezado", scene.get("Encabezado de escena", "-") or "-"
            )
            columns[2].metric("INT / EXT", scene.get("INT/EXT", "-") or "-")
            columns[3].metric("Tiempo", scene.get("Tiempo", "-") or "-")
    return scene_number, scene


def _ensure_scene_structure(scene_number):
    state = st.session_state.get("breakdown_production_notes_data", {})
    if not isinstance(state, Mapping):
        state = {}
    state = dict(state)
    stored_value = state.get(scene_number, {})
    scene_data = dict(stored_value) if isinstance(stored_value, Mapping) else {}

    for key, columns in _LEGACY_TABLES.items():
        scene_data[key] = _normalize_dataframe(scene_data.get(key), columns)
    scene_data["notas_generales"] = _clean_text(scene_data.get("notas_generales"))

    if _NOTES_KEY not in scene_data:
        legacy_note = scene_data["notas_generales"]
        migrated_rows = []
        if legacy_note:
            migrated_rows.append({
                "ID": 1,
                "Departamento": "Producción",
                "Instrucción": "",
                "Observaciones": legacy_note,
            })
        scene_data[_NOTES_KEY] = pd.DataFrame(
            migrated_rows, columns=_NOTE_COLUMNS
        )
    else:
        scene_data[_NOTES_KEY] = _normalize_dataframe(
            scene_data.get(_NOTES_KEY), _NOTE_COLUMNS
        )

    state[scene_number] = scene_data
    st.session_state.breakdown_production_notes_data = state
    return scene_data


def _next_id(dataframe):
    values = pd.to_numeric(dataframe.get("ID", pd.Series(dtype=float)), errors="coerce")
    return 1 if values.dropna().empty else int(values.max()) + 1


def _save_notes(scene_number, dataframe):
    state = st.session_state.breakdown_production_notes_data
    scene_data = state[scene_number]
    st.session_state.breakdown_production_notes_data = {
        **state,
        scene_number: {
            **scene_data,
            _NOTES_KEY: dataframe[_NOTE_COLUMNS].fillna("").copy(),
        },
    }


def _add_note(scene_number, dataframe):
    new_row = pd.DataFrame([{
        "ID": _next_id(dataframe),
        "Departamento": "Producción",
        "Instrucción": "",
        "Observaciones": "",
    }])
    _save_notes(scene_number, pd.concat([dataframe, new_row], ignore_index=True))


def _render_department_select(current, key):
    current_value = _clean_text(current)
    standard = [item for item in _DEPARTMENTS if item != "Otro..."]
    selected = current_value if current_value in standard else "Otro..."
    choice = st.selectbox(
        "Departamento",
        _DEPARTMENTS,
        index=_DEPARTMENTS.index(selected),
        key=f"{key}_department",
    )
    if choice != "Otro...":
        return choice
    custom_value = current_value if current_value not in standard else ""
    return st.text_input(
        "Especificar departamento",
        value=custom_value,
        key=f"{key}_custom_department",
    ).strip()


def _scene_sort_key(scene_number):
    try:
        return 0, float(str(scene_number).strip())
    except ValueError:
        return 1, str(scene_number).casefold()


def _build_project_catalog():
    entries = {}
    state = st.session_state.get("breakdown_production_notes_data", {})
    if not isinstance(state, Mapping):
        state = {}
    for scene_number, value in state.items():
        if not isinstance(value, Mapping):
            continue
        dataframe = _normalize_dataframe(value.get(_NOTES_KEY), _NOTE_COLUMNS)
        for department in dataframe["Departamento"]:
            clean_department = _clean_text(department)
            if not clean_department:
                continue
            entry = entries.setdefault(
                clean_department.casefold(),
                {"Departamento": clean_department, "Apariciones": 0, "Escenas": set()},
            )
            entry["Apariciones"] += 1
            entry["Escenas"].add(str(scene_number).strip())
    rows = [{
        "Departamento": entry["Departamento"],
        "Apariciones": entry["Apariciones"],
        "Escenas": ", ".join(sorted(entry["Escenas"], key=_scene_sort_key)),
    } for entry in entries.values()]
    rows.sort(key=lambda row: row["Departamento"].casefold())
    return pd.DataFrame(rows, columns=["Departamento", "Apariciones", "Escenas"])


def _other_department_scenes(scene_number, department):
    normalized = _clean_text(department).casefold()
    scenes = []
    state = st.session_state.get("breakdown_production_notes_data", {})
    if not normalized or not isinstance(state, Mapping):
        return scenes
    for other_scene, value in state.items():
        if str(other_scene) == str(scene_number) or not isinstance(value, Mapping):
            continue
        dataframe = _normalize_dataframe(value.get(_NOTES_KEY), _NOTE_COLUMNS)
        if dataframe["Departamento"].map(_clean_text).str.casefold().eq(normalized).any():
            scenes.append(str(other_scene).strip())
    return sorted(set(scenes), key=_scene_sort_key)


@st.dialog("Eliminar nota de producción")
def _confirm_delete_note(scene_number, row_index):
    dataframe = _normalize_dataframe(
        st.session_state.breakdown_production_notes_data[scene_number][_NOTES_KEY],
        _NOTE_COLUMNS,
    )
    if row_index not in dataframe.index:
        st.error("No se encontró la nota seleccionada.")
        return
    department = _clean_text(dataframe.at[row_index, "Departamento"])
    other_scenes = _other_department_scenes(scene_number, department)
    st.markdown("### ¿Eliminar esta nota?")
    st.write(f"**Departamento:** {department or 'Sin departamento'}")
    st.write(f"**Escena:** {scene_number}")
    if other_scenes:
        st.warning("Este departamento también tiene notas en las siguientes escenas:")
        for scene in other_scenes:
            st.write(scene)
        st.write("Solo se eliminará la nota de la escena actual.")
        st.caption("El catálogo general se actualizará automáticamente.")
    else:
        st.info("Esta nota solo será eliminada de la escena actual.")
    cancel_column, delete_column = st.columns(2)
    with cancel_column:
        cancel = st.button(
            "Cancelar",
            key=f"cancel_production_note_{scene_number}_{row_index}",
            use_container_width=True,
        )
    with delete_column:
        confirm = st.button(
            "Eliminar",
            icon=f":material/{DELETE}:",
            type="primary",
            key=f"confirm_production_note_{scene_number}_{row_index}",
            use_container_width=True,
        )
    if cancel:
        st.rerun()
    if confirm:
        _save_notes(scene_number, dataframe.drop(index=row_index).reset_index(drop=True))
        st.session_state["production_note_message"] = "Nota eliminada correctamente."
        st.rerun()


def _render_note_card(scene_number, dataframe, row_index, row):
    record_id = row.get("ID", row_index)
    prefix = f"production_note_{scene_number}_{record_id}"
    title = _clean_text(row.get("Departamento")) or "Nueva nota de producción"
    with cine_panel(title=_icon_label(PRODUCTION, title)):
        with st.form(f"{prefix}_form"):
            department = _render_department_select(row.get("Departamento"), prefix)
            instruction = st.text_area(
                "Instrucción para el departamento",
                value=_clean_text(row.get("Instrucción")),
                height=180,
                key=f"{prefix}_instruction",
            )
            observations = st.text_area(
                "Observaciones generales",
                value=_clean_text(row.get("Observaciones")),
                height=160,
                key=f"{prefix}_observations",
            )
            update_column, delete_column = st.columns(2)
            with update_column:
                update = st.form_submit_button(
                    "Actualizar", icon=f":material/{SAVE}:", use_container_width=True
                )
            with delete_column:
                delete = st.form_submit_button(
                    "Eliminar", icon=f":material/{DELETE}:", use_container_width=True
                )
        if update:
            updated = dataframe.copy()
            updated.at[row_index, "Departamento"] = department
            updated.at[row_index, "Instrucción"] = instruction
            updated.at[row_index, "Observaciones"] = observations
            _save_notes(scene_number, updated)
            st.success("Nota de producción actualizada correctamente.")
        if delete:
            _confirm_delete_note(scene_number, row_index)


def _render_dashboard(dataframe):
    departments = dataframe["Departamento"].map(_clean_text)
    instructions = dataframe["Instrucción"].map(_clean_text)
    completed = int((departments.ne("") & instructions.ne("")).sum())
    total = len(dataframe)
    pending = total - completed
    involved = departments[departments.ne("")].str.casefold().nunique()
    with cine_panel(
        title=_icon_label(ANALYTICS, "Dashboard del Departamento"),
        subtitle="Estado de las instrucciones de producción de la escena actual.",
    ):
        columns = st.columns(4)
        columns[0].metric("Total de notas", total)
        columns[1].metric("Departamentos involucrados", involved)
        columns[2].metric("Pendientes", pending)
        columns[3].metric("Completadas", completed)
        st.progress(completed / total if total else 0.0)


def _render_notes_section(scene_number, dataframe):
    with cine_panel(
        title=_icon_label(NOTE, "Notas de Producción"),
        subtitle=(
            "Registra instrucciones y observaciones importantes para cada departamento "
            "involucrado en esta escena. Estas notas podrán reutilizarse posteriormente "
            "en la Hoja de Llamado y otros reportes."
        ),
    ):
        if st.button(
            "Agregar Nota de Producción",
            icon=f":material/{ADD}:",
            key=f"add_production_note_{scene_number}",
            use_container_width=True,
        ):
            _add_note(scene_number, dataframe)
            st.rerun()
    if dataframe.empty:
        st.info("No hay notas de producción registradas para esta escena.")
        return
    for row_index, row in dataframe.iterrows():
        st.write("")
        _render_note_card(scene_number, dataframe, row_index, row)


def _render_scene_summary(dataframe):
    with cine_panel(
        title=_icon_label(SCENE, "Resumen de la Escena"),
        subtitle="Vista de solo lectura de las notas guardadas en la escena actual.",
    ):
        summary = dataframe[["Departamento", "Instrucción", "Observaciones"]].copy()
        st.dataframe(summary, use_container_width=True, hide_index=True)


def _render_project_catalog():
    with cine_panel(
        title=_icon_label(TASK, "Catálogo General"),
        subtitle=(
            "Índice automático de los departamentos con notas registradas en el proyecto."
        ),
    ):
        st.dataframe(
            _build_project_catalog(), use_container_width=True, hide_index=True
        )


def render_production_page():
    render_section_header(
        icon=PRODUCTION,
        title="Notas de Producción",
        description=(
            "Registra instrucciones departamentales y observaciones generales de cada "
            "escena para su uso en rodaje, reportes y hojas de llamado."
        ),
    )

    pending_message = st.session_state.pop("production_note_message", None)
    if pending_message:
        st.success(pending_message)

    scene_options = _build_scene_options()
    if not scene_options:
        st.warning("No hay escenas disponibles.")
        return

    scene_number, scene = _render_scene_selector(scene_options)
    if scene is None:
        st.warning("No se encontró la escena seleccionada.")
        return

    scene_data = _ensure_scene_structure(scene_number)
    dataframe = scene_data[_NOTES_KEY]

    _render_dashboard(dataframe)
    st.write("")
    _render_notes_section(scene_number, dataframe)
    current = st.session_state.breakdown_production_notes_data[scene_number][_NOTES_KEY]
    st.write("")
    _render_scene_summary(current)
    st.write("")
    _render_project_catalog()
