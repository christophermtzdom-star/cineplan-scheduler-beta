import streamlit as st
import pandas as pd

from components.header import render_section_header
from components.icons import ANALYTICS, OCTAVOS, SCENE, SYNC
from components.panel import cine_panel

from project.importer import (
    normalize_octavos_value,
    normalize_scene_octavos_fields,
    number_to_octavos
)


OCTAVOS_COLUMNS = [
    "Escena",
    "Locación",
    "INT/EXT",
    "Tiempo",
    "octavos_auto",
    "octavos_manual",
    "octavos_final"
]


def octavos_to_number(value):
    value = str(value).strip()

    if not value:
        return 0

    try:
        if " " in value:
            pages, fraction = value.split(" ")
            num, den = fraction.split("/")
            return int(pages) * 8 + int(num)

        if "/" in value:
            num, den = value.split("/")
            return int(num)

        return int(value) * 8
    except Exception:
        return 0


def obtener_octavos_finales(escena):
    if escena is None:
        return ""

    manual = normalize_octavos_value(escena.get("octavos_manual", ""))
    final = normalize_octavos_value(escena.get("octavos_final", ""))
    auto = normalize_octavos_value(escena.get("octavos_auto", ""))
    direct = normalize_octavos_value(escena.get("Octavos", ""))
    legacy = normalize_octavos_value(escena.get("octavos", ""))

    if manual:
        return manual
    if final:
        return final
    if auto:
        return auto
    if direct:
        return direct
    if legacy:
        return legacy

    return ""


def ensure_octavos_columns():
    if "scenes_df" not in st.session_state:
        st.session_state.scenes_df = pd.DataFrame()

    for column in OCTAVOS_COLUMNS:
        if column not in st.session_state.scenes_df.columns:
            st.session_state.scenes_df[column] = ""

    if "Octavos" not in st.session_state.scenes_df.columns:
        st.session_state.scenes_df["Octavos"] = ""


def build_octavos_display_df():
    display_df = st.session_state.scenes_df.copy()

    for column in ["octavos_auto", "octavos_manual", "octavos_final", "Octavos"]:
        if column not in display_df.columns:
            display_df[column] = ""

        display_df[column] = (
            display_df[column]
            .fillna("")
            .astype(str)
            .map(normalize_octavos_value)
        )

    available_columns = [
        column for column in OCTAVOS_COLUMNS
        if column in display_df.columns
    ]

    return display_df[available_columns].copy()


def get_octavos_total():
    return sum(
        octavos_to_number(
            obtener_octavos_finales(row.to_dict())
        )
        for _, row in st.session_state.scenes_df.iterrows()
    )


def get_octavos_stats():
    scenes_df = st.session_state.scenes_df.copy()

    total_scenes = len(scenes_df)

    auto_count = 0
    manual_count = 0
    final_count = 0

    if "octavos_auto" in scenes_df.columns:
        auto_count = (
            scenes_df["octavos_auto"]
            .fillna("")
            .astype(str)
            .map(normalize_octavos_value)
            .str.strip()
            .ne("")
            .sum()
        )

    if "octavos_manual" in scenes_df.columns:
        manual_count = (
            scenes_df["octavos_manual"]
            .fillna("")
            .astype(str)
            .map(normalize_octavos_value)
            .str.strip()
            .ne("")
            .sum()
        )

    final_count = sum(
        1
        for _, row in scenes_df.iterrows()
        if obtener_octavos_finales(row.to_dict())
    )

    total_octavos = get_octavos_total()

    return {
        "total_scenes": total_scenes,
        "auto_count": int(auto_count),
        "manual_count": int(manual_count),
        "final_count": int(final_count),
        "total_octavos": total_octavos,
        "total_octavos_label": number_to_octavos(total_octavos)
    }


def get_scene_options(display_df):
    options = []
    label_to_index = {}

    for i, row in display_df.iterrows():
        escena_val = str(row.get("Escena", "")).strip()
        locacion_val = str(row.get("Locación", "")).strip()
        int_ext_val = str(row.get("INT/EXT", "")).strip()
        tiempo_val = str(row.get("Tiempo", "")).strip()

        label = (
            f"Escena {escena_val} — "
            f"{locacion_val or '-'} — "
            f"{int_ext_val or '-'} — "
            f"{tiempo_val or '-'}"
        )

        options.append(label)
        label_to_index[label] = i

    return options, label_to_index


def render_octavos_table_card(display_df):
    with cine_panel(
        title=f":material/{OCTAVOS}: Tabla de octavos detectados",
        subtitle=(
            "Consulta los octavos automáticos, manuales y finales por escena."
        )
    ):

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )


def render_octavos_editor_card(display_df):
    with cine_panel(
        title=f":material/{OCTAVOS}: Editar octavos de escena",
        subtitle=(
            "Selecciona una escena y escribe un valor manual cuando sea necesario."
        )
    ):

        options, label_to_index = get_scene_options(display_df)

        if not options:
            st.info("No hay escenas disponibles para editar.")
            return

        if "octavos_manual_inputs" not in st.session_state:
            st.session_state["octavos_manual_inputs"] = {}

        col_scene, col_manual, col_button = st.columns(
            [1, 1, 1],
            gap="medium"
        )

        with col_scene:
            selected_label = st.selectbox(
                "Seleccionar escena",
                options,
                key="octavos_selected_label"
            )

        row_index = label_to_index.get(selected_label)

        if row_index is None:
            st.error("No se encontró la escena seleccionada.")
            return

        scene_row = st.session_state.scenes_df.iloc[row_index]

        auto_value = normalize_octavos_value(
            scene_row.get("octavos_auto", "")
        )

        current_manual = normalize_octavos_value(
            scene_row.get("octavos_manual", "")
        )

        current_final = normalize_octavos_value(
            scene_row.get("octavos_final", "")
        )

        if selected_label not in st.session_state["octavos_manual_inputs"]:
            st.session_state["octavos_manual_inputs"][selected_label] = current_manual

        prev_label = st.session_state.get("octavos_selected_label_prev")

        if prev_label != selected_label:
            st.session_state["octavos_manual_input"] = (
                st.session_state["octavos_manual_inputs"]
                .get(selected_label, current_manual)
            )
            st.session_state["octavos_selected_label_prev"] = selected_label

        with col_manual:
            manual_input = st.text_input(
                "Nuevo valor manual",
                value=st.session_state.get("octavos_manual_input", ""),
                key="octavos_manual_input"
            )

        manual_input_normalized = normalize_octavos_value(manual_input)

        st.session_state["octavos_manual_inputs"][
            selected_label
        ] = manual_input_normalized

        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)

            update_octavos = st.button(
                "Actualizar",
                icon=f":material/{SYNC}:",
                use_container_width=True,
                key="update_octavos_scene_button"
            )

        st.markdown(f"#### :material/{SCENE}: Escena seleccionada")
        st.write(selected_label)

        info_col1, info_col2, info_col3 = st.columns(3)

        info_col1.metric(
            "Automáticos",
            auto_value or "-"
        )

        info_col2.metric(
            "Manuales",
            current_manual or "-"
        )

        info_col3.metric(
            "Finales",
            current_final or "-"
        )

        if update_octavos:
            final_value = (
                manual_input_normalized
                if manual_input_normalized
                else auto_value
            )

            row_dict = scene_row.to_dict()
            row_dict["octavos_auto"] = auto_value
            row_dict["octavos_manual"] = manual_input_normalized
            row_dict["octavos_final"] = final_value
            row_dict["Octavos"] = final_value

            values = normalize_scene_octavos_fields(row_dict)

            idx_label = st.session_state.scenes_df.index[row_index]

            st.session_state.scenes_df.loc[
                idx_label,
                "octavos_auto"
            ] = values["octavos_auto"]

            st.session_state.scenes_df.loc[
                idx_label,
                "octavos_manual"
            ] = values["octavos_manual"]

            st.session_state.scenes_df.loc[
                idx_label,
                "octavos_final"
            ] = values["octavos_final"]

            st.session_state.scenes_df.loc[
                idx_label,
                "Octavos"
            ] = values["Octavos"]

            st.success("Octavos actualizados correctamente.")
            st.rerun()


def render_octavos_summary_card():
    stats = get_octavos_stats()

    with cine_panel(
        title=f":material/{ANALYTICS}: Resumen de octavos",
        subtitle="Indicadores generales basados en las escenas actuales."
    ):

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Escenas", stats["total_scenes"])
        col2.metric("Auto", stats["auto_count"])
        col3.metric("Manual", stats["manual_count"])
        col4.metric("Final", stats["final_count"])
        col5.metric("Total guion", stats["total_octavos_label"])


def render_octavos_tab():

    ensure_octavos_columns()

    render_section_header(
        icon=OCTAVOS,
        title="Octavos",
        description=(
            "Revisa los octavos detectados automáticamente, corrige manualmente "
            "cuando sea necesario y confirma el total estimado del guion."
        )
    )

    if st.session_state.scenes_df.empty:
        st.info("No hay escenas disponibles.")
        return

    display_df = build_octavos_display_df()

    render_octavos_table_card(display_df)
    render_octavos_editor_card(display_df)
    render_octavos_summary_card()
