import streamlit as st
import pandas as pd

from components.header import render_section_header
from components.icons import ADD_CHARACTER, ANALYTICS, CHARACTER, DELETE, GRID
from components.panel import cine_panel


REQUIRED_CHARACTER_COLUMNS = [
    "ID",
    "Personaje",
    "Escenas",
    "Apariciones",
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

    st.session_state.characters_df = (
        st.session_state.characters_df[REQUIRED_CHARACTER_COLUMNS]
        .fillna("")
        .copy()
    )


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
        "Escenas": "",
        "Apariciones": "",
        "Actor/Actriz": "",
        "Contacto": "",
        "Notas": ""
    }


def get_character_options():
    character_options = []

    for _, row in st.session_state.characters_df.iterrows():
        character_id = str(row.get("ID", ""))
        character_name = str(row.get("Personaje", ""))
        character_options.append(f"{character_id} - {character_name}")

    return character_options


def render_insert_character_card(character_options):
    with cine_panel(
        title=f":material/{ADD_CHARACTER}: Insertar nuevo personaje",
        subtitle=(
            "Agrega un personaje antes o después de otro personaje existente. "
            "CinePlan renumera automáticamente los IDs."
        )
    ):

        col_position, col_character, col_button = st.columns(
            [1, 2, 1],
            gap="medium"
        )

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
                icon=f":material/{ADD_CHARACTER}:",
                use_container_width=True,
                key="insert_character_button_review"
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

            insert_index = (
                reference_index + 1
                if insert_position == "Después de"
                else reference_index
            )

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


def render_delete_character_card(character_options):
    with cine_panel(
        title=f":material/{DELETE}: Eliminar personaje",
        subtitle=(
            "Elimina un personaje de la lista general. "
            "Después de eliminar, CinePlan renumera automáticamente."
        )
    ):

        if not character_options:
            st.info("No hay personajes para eliminar.")
            return

        col_character, col_button = st.columns(
            [3, 1],
            gap="medium"
        )

        with col_character:
            personaje_a_eliminar = st.selectbox(
                "Selecciona un personaje para eliminar",
                character_options,
                key="personaje_a_eliminar_review"
            )

        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)

            delete_character = st.button(
                "Eliminar",
                icon=f":material/{DELETE}:",
                use_container_width=True,
                key="delete_character_button_review"
            )

        if delete_character:
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


def render_characters_table_card():
    with cine_panel(
        title=f":material/{GRID}: Tabla editable",
        subtitle=(
            "Edita personajes, escenas, apariciones, actor/actriz, contacto y notas. "
            "Puedes corregir manualmente las escenas y apariciones detectadas."
        )
    ):

        with st.form("form_personajes_review"):
            edited_characters = st.data_editor(
                st.session_state.characters_df[REQUIRED_CHARACTER_COLUMNS],
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True
            )

            col_ordenar, col_guardar = st.columns(
                [1, 1],
                gap="medium"
            )

            with col_ordenar:
                ordenar_personajes = st.form_submit_button(
                    "Ordenar y renumerar personajes",
                    use_container_width=True
                )

            with col_guardar:
                guardar_personajes = st.form_submit_button(
                    "Guardar cambios",
                    use_container_width=True
                )

            if ordenar_personajes:
                clean_df = edited_characters.fillna("").copy()

                clean_df["ID"] = pd.to_numeric(
                    clean_df["ID"],
                    errors="coerce"
                )

                clean_df = (
                    clean_df
                    .sort_values("ID")
                    .reset_index(drop=True)
                )

                st.session_state.characters_df = clean_df.copy()

                renumber_characters()

                st.success("Personajes ordenados y renumerados correctamente.")
                st.rerun()

            if guardar_personajes:
                st.session_state.characters_df = (
                    edited_characters
                    .fillna("")
                    .copy()
                )

                st.success("Personajes actualizados correctamente.")
                st.rerun()


def render_character_summary_card():
    characters_df = st.session_state.characters_df.copy()

    total_characters = len(characters_df)

    assigned_actors = (
        characters_df["Actor/Actriz"]
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )

    contacts_count = (
        characters_df["Contacto"]
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )

    pending_casting = total_characters - assigned_actors

    total_appearances = int(
        pd.to_numeric(
            characters_df["Apariciones"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )

    with cine_panel(
        title=f":material/{ANALYTICS}: Resumen de personajes",
        subtitle="Indicadores rápidos basados en la tabla actual."
    ):

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Personajes", total_characters)
        col2.metric("Actores asignados", assigned_actors)
        col3.metric("Pendientes", pending_casting)
        col4.metric("Apariciones", total_appearances)

        col5, col6 = st.columns(2)

        col5.metric("Contactos registrados", contacts_count)
        col6.metric("Sin contacto", total_characters - contacts_count)


def render_characters_tab():
    ensure_character_columns()

    render_section_header(
        icon=CHARACTER,
        title="Personajes",
        description=(
            "Revisa los personajes detectados, ordena sus IDs, asigna actor o actriz, "
            "registra contacto y corrige manualmente sus escenas y apariciones."
        )
    )

    if st.session_state.characters_df.empty:
        st.info("No hay personajes detectados.")
        return

    character_options = get_character_options()

    action_col_left, action_col_right = st.columns(
        [1, 1],
        gap="large"
    )

    with action_col_left:
        render_insert_character_card(character_options)

    with action_col_right:
        render_delete_character_card(character_options)

    render_characters_table_card()

    render_character_summary_card()
