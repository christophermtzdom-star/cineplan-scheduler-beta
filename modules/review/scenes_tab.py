import streamlit as st
import pandas as pd


REQUIRED_SCENE_COLUMNS = [
    "Orden",
    "Escena",
    "Encabezado de escena",
    "INT/EXT",
    "Tiempo",
    "Locación",
    "Octavos",
    "Página",
    "Estado",
    "Notas"
]


def ensure_scene_columns():
    if "scenes_df" not in st.session_state:
        st.session_state.scenes_df = pd.DataFrame()

    for column in REQUIRED_SCENE_COLUMNS:
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
        "Octavos": "1/8",
        "Página": "",
        "Estado": "Pendiente de revisión",
        "Notas": ""
    }


def render_scenes_tab():

    st.markdown("### Escenas detectadas y editables")

    ensure_scene_columns()

    if st.session_state.scenes_df.empty:
        st.info("No hay escenas detectadas.")
        return

    st.markdown("### Insertar nueva escena")

    scene_options = []

    for _, row in st.session_state.scenes_df.iterrows():
        numero = str(row.get("Escena", ""))
        encabezado = str(row.get("Encabezado de escena", ""))
        scene_options.append(f"{numero} - {encabezado}")

    col_position, col_scene, col_button = st.columns([1, 2, 1])

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
            icon=":material/add:",
            use_container_width=True
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

        if insert_position == "Después de":
            insert_index = reference_index + 1
        else:
            insert_index = reference_index

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

    st.caption(
        "Puedes insertar una escena antes o después de cualquier escena existente. "
        "CinePlan renumera automáticamente el orden."
    )

    st.divider()

    st.markdown("### Eliminar escena")

    escenas_disponibles = []

    for _, row in st.session_state.scenes_df.iterrows():
        numero = str(row.get("Escena", ""))
        encabezado = str(row.get("Encabezado de escena", ""))
        escenas_disponibles.append(f"{numero} - {encabezado}")

    if escenas_disponibles:
        escena_a_eliminar = st.selectbox(
            "Selecciona una escena para eliminar",
            escenas_disponibles,
            key="escena_a_eliminar_review"
        )

        if st.button(
            "Eliminar escena seleccionada",
            icon=":material/delete:",
            use_container_width=True
        ):
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
    else:
        st.info("No hay escenas para eliminar.")

    st.divider()

    st.markdown("### Tabla editable")

    with st.form("form_escenas_review"):
        edited_scenes = st.data_editor(
            st.session_state.scenes_df[REQUIRED_SCENE_COLUMNS],
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True
        )

        col_guardar, col_ordenar = st.columns([1, 1])

        with col_guardar:
            guardar_escenas = st.form_submit_button(
                "Guardar cambios"
            )

        with col_ordenar:
            ordenar_escenas = st.form_submit_button(
                "Ordenar y renumerar escenas"
            )

        if guardar_escenas:
            st.session_state.scenes_df = edited_scenes.fillna("").copy()
            st.success("Escenas actualizadas correctamente.")

        if ordenar_escenas:
            edited_scenes = edited_scenes.fillna("").copy()

            edited_scenes["Escena"] = pd.to_numeric(
                edited_scenes["Escena"],
                errors="coerce"
            )

            edited_scenes = (
                edited_scenes
                .sort_values("Escena")
                .reset_index(drop=True)
            )

            st.session_state.scenes_df = edited_scenes.copy()

            renumber_scenes()

            st.success("Escenas ordenadas y renumeradas correctamente.")
            st.rerun()

    st.divider()

    st.markdown("### Resumen de escenas detectadas")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="Total de escenas",
            value=len(st.session_state.scenes_df)
        )

    with col2:
        if "Locación" in st.session_state.scenes_df.columns:
            st.metric(
                label="Locaciones",
                value=st.session_state.scenes_df["Locación"].nunique()
            )
        else:
            st.metric(
                label="Locaciones",
                value=0
            )