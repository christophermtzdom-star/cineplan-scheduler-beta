import streamlit as st
import pandas as pd

from components.header import render_section_header
from components.icons import ADD, ANALYTICS, DELETE, GRID, SCENE
from components.panel import cine_panel


EDITABLE_SCENE_COLUMNS = [
    "Orden",
    "Escena",
    "Encabezado de escena",
    "INT/EXT",
    "Tiempo",
    "Locación",
    "Estado"
]


def ensure_scene_columns():
    if "scenes_df" not in st.session_state:
        st.session_state.scenes_df = pd.DataFrame()

    for column in EDITABLE_SCENE_COLUMNS:
        if column not in st.session_state.scenes_df.columns:
            st.session_state.scenes_df[column] = ""


def renumber_scenes():
    st.session_state.scenes_df = (
        st.session_state.scenes_df
        .reset_index(drop=True)
        .copy()
    )

    st.session_state.scenes_df["Orden"] = range(
        1,
        len(st.session_state.scenes_df) + 1
    )

    st.session_state.scenes_df["Escena"] = range(
        1,
        len(st.session_state.scenes_df) + 1
    )


def create_empty_scene(scene_number):
    return {
        "Orden": scene_number,
        "Escena": scene_number,
        "Encabezado de escena": "NUEVA ESCENA",
        "INT/EXT": "",
        "Tiempo": "",
        "Locación": "",
        "Estado": "Pendiente"
    }


def get_scene_options():
    scene_options = []

    for _, row in st.session_state.scenes_df.iterrows():
        numero = str(row.get("Escena", ""))
        encabezado = str(row.get("Encabezado de escena", ""))
        scene_options.append(f"{numero} - {encabezado}")

    return scene_options


def get_scene_stats():
    scenes_df = st.session_state.scenes_df

    total_scenes = len(scenes_df)
    locations_count = 0
    int_count = 0
    ext_count = 0
    ie_count = 0

    if "Locación" in scenes_df.columns:
        locations_count = (
            scenes_df["Locación"]
            .fillna("")
            .astype(str)
            .str.strip()
            .replace("", "SIN LOCACIÓN")
            .nunique()
        )

    if "INT/EXT" in scenes_df.columns:
        int_ext = (
            scenes_df["INT/EXT"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )

        ie_mask = int_ext.str.contains("I/E", na=False)

        int_count = int(
            (
                int_ext.str.contains("INT", na=False)
                & ~ie_mask
            ).sum()
        )

        ext_count = int(
            (
                int_ext.str.contains("EXT", na=False)
                & ~ie_mask
            ).sum()
        )

        ie_count = int(ie_mask.sum())

    return {
        "total_scenes": total_scenes,
        "locations_count": locations_count,
        "int_count": int_count,
        "ext_count": ext_count,
        "ie_count": ie_count
    }


def render_insert_scene_card(scene_options):

    with cine_panel(
        title=f":material/{ADD}: Insertar nueva escena",
        subtitle=(
            "Agrega una escena antes o después de una escena existente. "
            "CinePlan renumera automáticamente el orden."
        )
    ):

        col_position, col_scene, col_button = st.columns(
            [1, 2, 1],
            gap="medium"
        )

        with col_position:
            insert_position = st.selectbox(
                "Posición",
                ["Después de", "Antes de"],
                key="insert_scene_position"
            )

        with col_scene:
            selected_scene = st.selectbox(
                "Escena de referencia",
                scene_options,
                key="insert_scene_reference"
            )

        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)

            insert_scene = st.button(
                "Insertar escena",
                icon=f":material/{ADD}:",
                use_container_width=True,
                key="insert_scene_button_review"
            )

        if insert_scene:
            selected_scene_number = selected_scene.split(" - ")[0]

            reference_indexes = st.session_state.scenes_df[
                st.session_state.scenes_df["Escena"].astype(str)
                == selected_scene_number
            ].index.tolist()

            if not reference_indexes:
                st.error("No se encontró la escena de referencia.")
                return

            reference_index = reference_indexes[0]

            insert_index = (
                reference_index + 1
                if insert_position == "Después de"
                else reference_index
            )

            current_df = st.session_state.scenes_df.copy()

            before_df = current_df.iloc[:insert_index].copy()
            after_df = current_df.iloc[insert_index:].copy()

            new_scene_df = pd.DataFrame([
                create_empty_scene(insert_index + 1)
            ])

            st.session_state.scenes_df = pd.concat(
                [before_df, new_scene_df, after_df],
                ignore_index=True
            )

            renumber_scenes()

            st.success("Escena insertada correctamente.")
            st.rerun()


def render_delete_scene_card(scene_options):

    with cine_panel(
        title=f":material/{DELETE}: Eliminar escena",
        subtitle=(
            "Elimina una escena detectada o agregada manualmente. "
            "Después de eliminar, CinePlan renumera automáticamente."
        )
    ):

        if not scene_options:
            st.info("No hay escenas para eliminar.")
            return

        col_scene, col_button = st.columns(
            [3, 1],
            gap="medium"
        )

        with col_scene:
            escena_a_eliminar = st.selectbox(
                "Selecciona una escena para eliminar",
                scene_options,
                key="escena_a_eliminar_review"
            )

        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)

            delete_scene = st.button(
                "Eliminar",
                icon=f":material/{DELETE}:",
                use_container_width=True,
                key="delete_scene_button_review"
            )

        if delete_scene:
            escena_numero = escena_a_eliminar.split(" - ")[0]

            st.session_state.scenes_df = (
                st.session_state.scenes_df[
                    st.session_state.scenes_df["Escena"].astype(str)
                    != escena_numero
                ]
                .reset_index(drop=True)
            )

            renumber_scenes()

            st.success("Escena eliminada correctamente.")
            st.rerun()


def render_edit_table_card():

    with cine_panel(
        title=f":material/{GRID}: Tabla editable",
        subtitle=(
            "Corrige únicamente orden, escena, encabezado, INT/EXT, tiempo, locación y estado. "
        )
    ):

        editable_df = st.session_state.scenes_df.copy()

        for column in EDITABLE_SCENE_COLUMNS:
            if column not in editable_df.columns:
                editable_df[column] = ""

        editable_df = editable_df[EDITABLE_SCENE_COLUMNS].fillna("").copy()

        with st.form("form_escenas_review"):
            edited_scenes = st.data_editor(
                editable_df,
                use_container_width=True,
                num_rows="fixed",
                hide_index=True
            )

            col_ordenar, col_guardar = st.columns(
                [1, 1],
                gap="medium"
            )

            with col_ordenar:
                ordenar_escenas = st.form_submit_button(
                    "Ordenar y renumerar escenas",
                    use_container_width=True
                )

            with col_guardar:
                guardar_escenas = st.form_submit_button(
                    "Guardar cambios",
                    use_container_width=True
                )

            if ordenar_escenas:
                full_df = st.session_state.scenes_df.copy().reset_index(drop=True)
                edited_scenes = edited_scenes.fillna("").copy().reset_index(drop=True)

                for column in EDITABLE_SCENE_COLUMNS:
                    full_df[column] = edited_scenes[column]

                full_df["Escena"] = pd.to_numeric(
                    full_df["Escena"],
                    errors="coerce"
                )

                full_df = (
                    full_df
                    .sort_values("Escena")
                    .reset_index(drop=True)
                )

                st.session_state.scenes_df = full_df.copy()

                renumber_scenes()

                st.success("Escenas ordenadas y renumeradas correctamente.")
                st.rerun()

            if guardar_escenas:
                full_df = st.session_state.scenes_df.copy().reset_index(drop=True)
                edited_scenes = edited_scenes.fillna("").copy().reset_index(drop=True)

                for column in EDITABLE_SCENE_COLUMNS:
                    full_df[column] = edited_scenes[column]

                st.session_state.scenes_df = full_df.copy()

                st.success("Escenas actualizadas correctamente.")
                st.rerun()


def render_scene_summary_card():

    stats = get_scene_stats()

    with cine_panel(
        title=f":material/{ANALYTICS}: Resumen de escenas",
        subtitle="Indicadores rápidos basados en la tabla actual."
    ):

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Total", stats["total_scenes"])
        col2.metric("Locaciones", stats["locations_count"])
        col3.metric("INT.", stats["int_count"])
        col4.metric("EXT.", stats["ext_count"])
        col5.metric("I/E", stats["ie_count"])


def render_scenes_tab():

    ensure_scene_columns()

    render_section_header(
        icon=SCENE,
        title="Escenas detectadas",
        description=(
            "Revisa, corrige, inserta o elimina escenas antes de continuar con "
            "locaciones, personajes, octavos y resumen final."
        )
    )

    if st.session_state.scenes_df.empty:
        st.info("No hay escenas detectadas.")
        return

    scene_options = get_scene_options()

    action_col_left, action_col_right = st.columns(
        [1, 1],
        gap="large"
    )

    with action_col_left:
        render_insert_scene_card(scene_options)

    with action_col_right:
        render_delete_scene_card(scene_options)

    render_edit_table_card()

    render_scene_summary_card()
