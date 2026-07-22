import streamlit as st
import pandas as pd
import re

from components.header import render_section_header
from components.icons import ANALYTICS, ARROW_FORWARD, STATUS, TASK
from components.panel import cine_panel
from project.importer import number_to_octavos
from modules.review.octavos_tab import (
    octavos_to_number,
    obtener_octavos_finales
)


ESTADO_OPTIONS = [
    "Pendiente",
    "Revisado",
    "Incompleta",
    "Modificada"
]


SUMMARY_COLUMNS = [
    "Orden",
    "Escena",
    "Encabezado de escena",
    "INT/EXT",
    "Tiempo",
    "Locación",
    "Personajes",
    "Octavos finales",
    "Notas",
    "Estado"
]


def parse_scene_ranges(value):
    scenes = set()

    text = str(value).strip()

    if not text:
        return scenes

    parts = re.split(r",|;|\n", text)

    for part in parts:
        part = part.strip().replace("–", "-")

        if not part:
            continue

        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start = int(float(start.strip()))
                end = int(float(end.strip()))

                for number in range(start, end + 1):
                    scenes.add(number)

            except Exception:
                continue
        else:
            try:
                scenes.add(int(float(part)))
            except Exception:
                continue

    return scenes


def build_scene_character_map():
    scene_character_map = {}

    characters_df = st.session_state.get("characters_df", pd.DataFrame())

    if characters_df.empty:
        return scene_character_map

    if "Personaje" not in characters_df.columns or "Escenas" not in characters_df.columns:
        return scene_character_map

    for _, row in characters_df.iterrows():
        character_name = str(row.get("Personaje", "")).strip()

        if not character_name:
            continue

        scene_numbers = parse_scene_ranges(row.get("Escenas", ""))

        for scene_number in scene_numbers:
            if scene_number not in scene_character_map:
                scene_character_map[scene_number] = []

            scene_character_map[scene_number].append(character_name)

    for scene_number in scene_character_map:
        scene_character_map[scene_number] = ", ".join(
            sorted(set(scene_character_map[scene_number]))
        )

    return scene_character_map


def ensure_summary_columns():
    if "scenes_df" not in st.session_state:
        st.session_state.scenes_df = pd.DataFrame()

    for column in [
        "Orden",
        "Escena",
        "Encabezado de escena",
        "INT/EXT",
        "Tiempo",
        "Locación",
        "Notas",
        "Estado"
    ]:
        if column not in st.session_state.scenes_df.columns:
            st.session_state.scenes_df[column] = ""

    st.session_state.scenes_df["Estado"] = (
        st.session_state.scenes_df["Estado"]
        .fillna("Pendiente")
        .replace("", "Pendiente")
    )


def build_summary_df():
    scene_character_map = build_scene_character_map()

    summary_df = st.session_state.scenes_df.copy()

    for column in SUMMARY_COLUMNS:
        if column not in summary_df.columns:
            summary_df[column] = ""

    personajes_values = []

    for _, row in summary_df.iterrows():
        try:
            scene_number = int(float(row.get("Escena", "")))
        except Exception:
            scene_number = None

        personajes_values.append(
            scene_character_map.get(scene_number, "")
        )

    summary_df["Personajes"] = personajes_values

    summary_df["Octavos finales"] = summary_df.apply(
        lambda row: obtener_octavos_finales(row.to_dict()),
        axis=1
    )

    return summary_df[SUMMARY_COLUMNS].copy()


def get_summary_stats():
    total_escenas = len(st.session_state.scenes_df)

    revisadas = (
        st.session_state.scenes_df["Estado"]
        .astype(str)
        .eq("Revisado")
        .sum()
    )

    pendientes = total_escenas - revisadas

    total_octavos = sum(
        octavos_to_number(
            obtener_octavos_finales(row.to_dict())
        )
        for _, row in st.session_state.scenes_df.iterrows()
    )

    return {
        "total_escenas": total_escenas,
        "revisadas": int(revisadas),
        "pendientes": int(pendientes),
        "total_octavos": total_octavos,
        "total_octavos_label": number_to_octavos(total_octavos)
    }


def render_summary_tab():

    ensure_summary_columns()

    render_section_header(
        icon=ANALYTICS,
        title="Resumen general",
        description=(
            "Revisa la información final de escenas antes de continuar al Breakdown. "
            "La columna Personajes se actualiza desde la pestaña Personajes."
        )
    )

    if st.session_state.scenes_df.empty:
        st.info("No hay información disponible.")
        return

    stats = get_summary_stats()

    with cine_panel(title=f":material/{STATUS}: Estado de revisión"):

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Escenas", stats["total_escenas"])
        col2.metric("Revisadas", stats["revisadas"])
        col3.metric("Pendientes", stats["pendientes"])
        col4.metric("Octavos totales", stats["total_octavos_label"])

        if stats["total_escenas"] > 0:
            progress_value = stats["revisadas"] / stats["total_escenas"]
        else:
            progress_value = 0

        st.progress(progress_value)

    summary_df = build_summary_df()

    with cine_panel(
        title=f":material/{TASK}: Validación final de escenas",
        subtitle=(
            "Marca cada escena como Revisado cuando hayas confirmado toda su información."
        )
    ):

        with st.form("form_resumen_revision"):
            edited_summary = st.data_editor(
                summary_df,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                disabled=[
                    "Personajes",
                    "Octavos finales"
                ],
                column_config={
                    "Estado": st.column_config.SelectboxColumn(
                        "Estado",
                        options=ESTADO_OPTIONS,
                        required=True
                    )
                }
            )

            guardar_resumen = st.form_submit_button(
                "Guardar revisión final",
                use_container_width=True
            )

            if guardar_resumen:
                editable_columns = [
                    "Orden",
                    "Escena",
                    "Encabezado de escena",
                    "INT/EXT",
                    "Tiempo",
                    "Locación",
                    "Notas",
                    "Estado"
                ]

                for column in editable_columns:
                    if column in edited_summary.columns:
                        st.session_state.scenes_df[column] = (
                            edited_summary[column]
                            .fillna("")
                            .values
                        )

                st.success("Revisión final actualizada correctamente.")
                st.rerun()

    stats_actualizadas = get_summary_stats()

    with cine_panel(title=f":material/{TASK}: Cierre de revisión"):

        if (
            stats_actualizadas["total_escenas"] > 0
            and stats_actualizadas["revisadas"] == stats_actualizadas["total_escenas"]
        ):
            st.success(
                "Revisión final completada. Todas las escenas han sido revisadas."
            )

            if st.button(
                "Continuar al Breakdown",
                icon=f":material/{ARROW_FORWARD}:",
                use_container_width=True,
                key="continue_to_breakdown_from_summary"
            ):
                st.session_state.main_menu = "2. Breakdown"
                st.session_state.current_view = "modules"
                st.rerun()

        else:
            st.warning(
                f"Aún faltan {stats_actualizadas['pendientes']} escena(s) por revisar antes de continuar con el Breakdown."
            )
