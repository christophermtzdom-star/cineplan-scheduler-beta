import streamlit as st
import pandas as pd


def classify_location_type(types):
    types = str(types).upper()

    if "I/E" in types:
        return "Interior / Exterior"
    elif "INT" in types and "EXT" in types:
        return "Interior / Exterior"
    elif "INT" in types:
        return "Interior"
    elif "EXT" in types:
        return "Exterior"
    else:
        return "Especial / Narrativa"


def render_locations_tab():

    st.markdown("### Locaciones")

    scenes_df = st.session_state.get("scenes_df", pd.DataFrame())

    if scenes_df.empty:
        st.info("No hay escenas detectadas.")
        return

    required_columns = [
        "Escena",
        "Encabezado de escena",
        "Locación",
        "INT/EXT",
        "Tiempo",
        "Octavos"
    ]

    for column in required_columns:
        if column not in scenes_df.columns:
            scenes_df[column] = ""

    locations_df = scenes_df[required_columns].copy()

    st.markdown("### Resumen general de locaciones")

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

    st.dataframe(
        location_summary,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.markdown("### Resumen por tipo de locación")

    interiores_df = locations_df[
        locations_df["INT/EXT"]
        .astype(str)
        .str.upper()
        .str.contains("INT", na=False)
        & ~locations_df["INT/EXT"]
        .astype(str)
        .str.upper()
        .str.contains("I/E", na=False)
    ].copy()

    exteriores_df = locations_df[
        locations_df["INT/EXT"]
        .astype(str)
        .str.upper()
        .str.contains("EXT", na=False)
        & ~locations_df["INT/EXT"]
        .astype(str)
        .str.upper()
        .str.contains("I/E", na=False)
    ].copy()

    interiores_exteriores_df = locations_df[
        locations_df["INT/EXT"]
        .astype(str)
        .str.upper()
        .str.contains("I/E", na=False)
    ].copy()

    keywords_especiales = [
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

    patron_especiales = "|".join(keywords_especiales)

    especiales_df = locations_df[
        locations_df["Encabezado de escena"]
        .astype(str)
        .str.upper()
        .str.contains(patron_especiales, na=False)
    ].copy()

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

    st.divider()

    st.markdown("### Resumen numérico")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.metric(
            "Locaciones únicas",
            locations_df["Locación"].nunique()
        )

    with col_b:
        st.metric(
            "Escenas totales",
            len(locations_df)
        )

    with col_c:
        st.metric(
            "Tiempos distintos",
            locations_df["Tiempo"].nunique()
        )