import streamlit as st
import pandas as pd

from components.header import render_section_header
from components.icons import (
    ADD_LOCATION,
    ANALYTICS,
    LOCATION,
    REMOVE_LOCATION,
)
from components.panel import cine_panel


REQUIRED_LOCATION_COLUMNS = [
    "Escena",
    "Encabezado de escena",
    "Locación",
    "INT/EXT",
    "Tiempo",
    "Octavos"
]


SPECIAL_KEYWORDS = [
    "FLASH",
    "FLASHBACK",
    "SUEÑO",
    "SUENO",
    "VISIÓN",
    "VISION",
    "RITUAL",
    "PESADILLA",
    "RECUERDO",
    "MONTAJE",
    "SECUENCIA",
    "ALUCINACIÓN",
    "ALUCINACION",
    "SOBRENATURAL"
]


def classify_location_type(types):
    types = str(types).upper()

    if "I/E" in types:
        return "Interior / Exterior"
    if "INT" in types and "EXT" in types:
        return "Interior / Exterior"
    if "INT" in types:
        return "Interior"
    if "EXT" in types:
        return "Exterior"

    return "Especial / Narrativa"


def ensure_location_columns():
    if "scenes_df" not in st.session_state:
        st.session_state.scenes_df = pd.DataFrame()

    for column in REQUIRED_LOCATION_COLUMNS:
        if column not in st.session_state.scenes_df.columns:
            st.session_state.scenes_df[column] = ""


def get_locations_df():
    ensure_location_columns()

    locations_df = st.session_state.scenes_df[
        REQUIRED_LOCATION_COLUMNS
    ].copy()

    locations_df["Locación"] = (
        locations_df["Locación"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    locations_df.loc[
        locations_df["Locación"] == "",
        "Locación"
    ] = "SIN LOCACIÓN"

    return locations_df


def get_location_summary(locations_df):
    if locations_df.empty:
        return pd.DataFrame()

    location_summary = (
        locations_df
        .groupby("Locación")
        .agg({
            "Escena": lambda x: ", ".join(map(str, sorted(set(x)))),
            "INT/EXT": lambda x: ", ".join(sorted(set(map(str, x)))),
            "Tiempo": lambda x: ", ".join(sorted(set(map(str, x)))),
            "Encabezado de escena": lambda x: " | ".join(sorted(set(map(str, x))))
        })
        .reset_index()
    )

    location_summary["Clasificación"] = location_summary["INT/EXT"].apply(
        classify_location_type
    )

    return location_summary


def get_scene_options():
    scene_options = []

    for _, row in st.session_state.scenes_df.iterrows():
        numero = str(row.get("Escena", ""))
        encabezado = str(row.get("Encabezado de escena", ""))
        locacion = str(row.get("Locación", "")).strip() or "SIN LOCACIÓN"

        scene_options.append(
            f"{numero} - {encabezado} — {locacion}"
        )

    return scene_options


def get_location_options():
    locations_df = get_locations_df()

    locations = (
        locations_df["Locación"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", "SIN LOCACIÓN")
        .unique()
        .tolist()
    )

    locations = sorted(locations)

    if "SIN LOCACIÓN" not in locations:
        locations.insert(0, "SIN LOCACIÓN")

    return locations


def render_assign_scene_card():

    with cine_panel(
        title=f":material/{ADD_LOCATION}: Agregar locación a escena",
        subtitle=(
            "Selecciona una escena y asígnale una locación existente o crea una nueva."
        )
    ):

        scene_options = get_scene_options()
        location_options = get_location_options()

        if not scene_options:
            st.info("No hay escenas disponibles.")
            return

        col_scene, col_location, col_button = st.columns(
            [2.3, 1.4, 1],
            gap="medium"
        )

        with col_scene:
            selected_scene = st.selectbox(
                "Escena",
                scene_options,
                key="location_assign_scene"
            )

        with col_location:
            selected_location = st.selectbox(
                "Locación",
                location_options,
                key="location_assign_existing"
            )

            new_location = st.text_input(
                "O escribir nueva locación",
                key="location_assign_new"
            )

        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)

            assign_scene = st.button(
                "Asignar",
                icon=f":material/{ADD_LOCATION}:",
                use_container_width=True
            )

        if assign_scene:
            scene_number = selected_scene.split(" - ")[0]

            final_location = (
                new_location.strip()
                if new_location.strip()
                else selected_location
            )

            idx_list = st.session_state.scenes_df[
                st.session_state.scenes_df["Escena"].astype(str)
                == scene_number
            ].index.tolist()

            if not idx_list:
                st.error("No se encontró la escena seleccionada.")
                return

            idx = idx_list[0]

            st.session_state.scenes_df.at[
                idx,
                "Locación"
            ] = final_location.upper()

            st.success("Escena asignada a locación correctamente.")
            st.rerun()


def render_remove_scene_location_card():

    with cine_panel(
        title=f":material/{REMOVE_LOCATION}: Quitar locación a escena",
        subtitle=(
            "Elimina la locación asignada a una escena. La escena quedará como SIN LOCACIÓN"
        )
    ):

        scene_options = get_scene_options()

        if not scene_options:
            st.info("No hay escenas disponibles.")
            return

        col_scene, col_button = st.columns(
            [3, 1],
            gap="medium"
        )

        with col_scene:
            selected_scene = st.selectbox(
                "Escena",
                scene_options,
                key="location_remove_scene"
            )

        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)

            remove_location = st.button(
                "Quitar",
                icon=f":material/{REMOVE_LOCATION}:",
                use_container_width=True
            )

        if remove_location:
            scene_number = selected_scene.split(" - ")[0]

            idx_list = st.session_state.scenes_df[
                st.session_state.scenes_df["Escena"].astype(str)
                == scene_number
            ].index.tolist()

            if not idx_list:
                st.error("No se encontró la escena seleccionada.")
                return

            idx = idx_list[0]

            st.session_state.scenes_df.at[
                idx,
                "Locación"
            ] = ""

            st.success("Locación retirada de la escena.")
            st.rerun()


def render_location_summary_card(location_summary):

    with cine_panel(
        title=f":material/{ANALYTICS}: Resumen general de locaciones",
        subtitle=(
            "Agrupación actualizada a partir de las escenas detectadas y editadas."
        )
    ):

        st.dataframe(
            location_summary,
            use_container_width=True,
            hide_index=True
        )


def render_location_type_summary(locations_df):

    int_ext = locations_df["INT/EXT"].astype(str).str.upper()

    interiores_df = locations_df[
        int_ext.str.contains("INT", na=False)
        & ~int_ext.str.contains("I/E", na=False)
    ].copy()

    exteriores_df = locations_df[
        int_ext.str.contains("EXT", na=False)
        & ~int_ext.str.contains("I/E", na=False)
    ].copy()

    interiores_exteriores_df = locations_df[
        int_ext.str.contains("I/E", na=False)
    ].copy()

    patron_especiales = "|".join(SPECIAL_KEYWORDS)

    especiales_df = locations_df[
        locations_df["Encabezado de escena"]
        .astype(str)
        .str.upper()
        .str.contains(patron_especiales, na=False)
    ].copy()

    with cine_panel(
        title=f":material/{LOCATION}: Resumen por tipo de locación",
        subtitle=(
            "Clasificación rápida para detectar interiores, exteriores, I/E y escenas especiales."
        )
    ):

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Interiores", len(interiores_df))
        col2.metric("Exteriores", len(exteriores_df))
        col3.metric("I/E", len(interiores_exteriores_df))
        col4.metric("Especiales", len(especiales_df))

        with st.expander("Ver escenas interiores"):
            st.dataframe(
                interiores_df,
                use_container_width=True,
                hide_index=True
            )

        with st.expander("Ver escenas exteriores"):
            st.dataframe(
                exteriores_df,
                use_container_width=True,
                hide_index=True
            )

        with st.expander("Ver escenas I/E"):
            st.dataframe(
                interiores_exteriores_df,
                use_container_width=True,
                hide_index=True
            )

        with st.expander("Ver escenas especiales / narrativas"):
            st.dataframe(
                especiales_df,
                use_container_width=True,
                hide_index=True
            )


def render_location_numeric_summary(locations_df):

    with cine_panel(
        title=f":material/{ANALYTICS}: Resumen numérico",
        subtitle="Indicadores generales de locaciones y escenas."
    ):

        col_a, col_b, col_c = st.columns(3)

        col_a.metric(
            "Locaciones únicas",
            locations_df["Locación"].nunique()
        )

        col_b.metric(
            "Escenas totales",
            len(locations_df)
        )

        col_c.metric(
            "Tiempos distintos",
            locations_df["Tiempo"].nunique()
        )


def render_locations_tab():

    ensure_location_columns()

    render_section_header(
        icon=LOCATION,
        title="Locaciones",
        description=(
            "Revisa las locaciones detectadas, reasigna escenas y verifica la "
            "clasificación por interiores, exteriores, I/E y escenas especiales."
        )
    )

    if st.session_state.scenes_df.empty:
        st.info("No hay escenas detectadas.")
        return

    action_col_left, action_col_right = st.columns(
        [1, 1],
        gap="large"
    )

    with action_col_left:
        render_assign_scene_card()

    with action_col_right:
        render_remove_scene_location_card()

    locations_df = get_locations_df()
    location_summary = get_location_summary(locations_df)

    render_location_summary_card(location_summary)
    render_location_type_summary(locations_df)
    render_location_numeric_summary(locations_df)
