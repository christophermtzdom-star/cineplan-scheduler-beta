import streamlit as st
import pandas as pd


REQUIRED_CHARACTER_COLUMNS = [
    "ID",
    "Personaje",
    "Actor/Actriz",
    "Contacto",
    "Notas"
]


def ensure_character_columns():
    if "characters_df" not in st.session_state:
        st.session_state.characters_df = pd.DataFrame()

    for column in REQUIRED_CHARACTER_COLUMNS:
        if column not in st.session_state.characters_df.columns:
            st.session_state.characters_df[column] = ""


def renumber_characters():
    st.session_state.characters_df = (
        st.session_state.characters_df
        .reset_index(drop=True)
        .copy()
    )

    st.session_state.characters_df["ID"] = range(
        1,
        len(st.session_state.characters_df) + 1
    )


def create_empty_character(character_id):
    return {
        "ID": character_id,
        "Personaje": "NUEVO PERSONAJE",
        "Actor/Actriz": "",
        "Contacto": "",
        "Notas": ""
    }


def render_characters_tab():

    st.markdown("### Personajes detectados y editables")

    ensure_character_columns()

    if st.session_state.characters_df.empty:
        st.info("No hay personajes detectados.")
        return

    st.markdown("### Insertar nuevo personaje")

    character_options = []

    for _, row in st.session_state.characters_df.iterrows():
        character_id = str(row.get("ID", ""))
        character_name = str(row.get("Personaje", ""))
        character_options.append(f"{character_id} - {character_name}")

    col_position, col_character, col_button = st.columns([1, 2, 1])

    with col_position:
        insert_position = st.selectbox(
            "Posición",
            ["Después de", "Antes de"],
            key="insert_character_position"
        )

    with col_character:
        selected_character = st.selectbox(
            "Personaje de referencia",
            character_options,
            key="insert_character_reference"
        )

    with col_button:
        st.markdown("<br>", unsafe_allow_html=True)

        insert_character = st.button(
            "Insertar personaje",
            icon=":material/person_add:",
            use_container_width=True
        )

    if insert_character:
        selected_character_id = selected_character.split(" - ")[0]

        reference_indexes = st.session_state.characters_df[
            st.session_state.characters_df["ID"].astype(str)
            == selected_character_id
        ].index.tolist()

        if not reference_indexes:
            st.error("No se encontró el personaje de referencia.")
            return

        reference_index = reference_indexes[0]

        if insert_position == "Después de":
            insert_index = reference_index + 1
        else:
            insert_index = reference_index

        current_df = st.session_state.characters_df.copy()

        before_df = current_df.iloc[:insert_index].copy()
        after_df = current_df.iloc[insert_index:].copy()

        new_character_df = pd.DataFrame([
            create_empty_character(insert_index + 1)
        ])

        st.session_state.characters_df = pd.concat(
            [before_df, new_character_df, after_df],
            ignore_index=True
        )

        renumber_characters()

        st.success("Personaje insertado correctamente.")
        st.rerun()

    st.caption(
        "Puedes insertar un personaje antes o después de cualquier personaje existente. "
        "CinePlan renumera automáticamente los IDs."
    )

    st.divider()

    st.markdown("### Eliminar personaje")

    personajes_disponibles = []

    for _, row in st.session_state.characters_df.iterrows():
        character_id = str(row.get("ID", ""))
        character_name = str(row.get("Personaje", ""))
        personajes_disponibles.append(f"{character_id} - {character_name}")

    if personajes_disponibles:
        personaje_a_eliminar = st.selectbox(
            "Selecciona un personaje para eliminar",
            personajes_disponibles,
            key="personaje_a_eliminar_review"
        )

        if st.button(
            "Eliminar personaje seleccionado",
            icon=":material/delete:",
            use_container_width=True
        ):
            character_id = personaje_a_eliminar.split(" - ")[0]

            st.session_state.characters_df = (
                st.session_state.characters_df[
                    st.session_state.characters_df["ID"].astype(str)
                    != character_id
                ]
                .reset_index(drop=True)
            )

            renumber_characters()

            st.success("Personaje eliminado correctamente.")
            st.rerun()
    else:
        st.info("No hay personajes para eliminar.")

    st.divider()

    st.markdown("### Tabla editable")

    with st.form("form_personajes_review"):
        edited_characters = st.data_editor(
            st.session_state.characters_df[REQUIRED_CHARACTER_COLUMNS],
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True
        )

        col_guardar, col_ordenar = st.columns([1, 1])

        with col_guardar:
            guardar_personajes = st.form_submit_button(
                "Guardar cambios"
            )

        with col_ordenar:
            ordenar_personajes = st.form_submit_button(
                "Ordenar y renumerar personajes"
            )

        if guardar_personajes:
            st.session_state.characters_df = edited_characters.fillna("").copy()
            st.success("Personajes actualizados correctamente.")

        if ordenar_personajes:
            edited_characters = edited_characters.fillna("").copy()

            edited_characters["ID"] = pd.to_numeric(
                edited_characters["ID"],
                errors="coerce"
            )

            edited_characters = (
                edited_characters
                .sort_values("ID")
                .reset_index(drop=True)
            )

            st.session_state.characters_df = edited_characters.copy()

            renumber_characters()

            st.success("Personajes ordenados y renumerados correctamente.")
            st.rerun()

    st.divider()

    st.markdown("### Resumen de personajes")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Personajes detectados",
            len(st.session_state.characters_df)
        )

    with col2:
        if "Actor/Actriz" in st.session_state.characters_df.columns:
            asignados = (
                st.session_state.characters_df["Actor/Actriz"]
                .astype(str)
                .str.strip()
                .ne("")
                .sum()
            )
        else:
            asignados = 0

        st.metric(
            "Actores asignados",
            asignados
        )