import re
import pandas as pd
import streamlit as st

from project.importer import normalize_octavos_value


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


def ensure_cast_structure(numero_escena, personajes_detectados=""):

    cast_columns = [
        "ID",
        "Personaje",
        "Actor/Actriz",
        "Tipo",
        "Notas"
    ]

    stunts_columns = [
        "ID",
        "Personaje sustituido",
        "Doble / Stunt",
        "Acción",
        "Nivel de riesgo",
        "Notas"
    ]

    extras_atmosfera_columns = [
        "ID",
        "Tipo de extra",
        "Cantidad",
        "Vestuario especial",
        "Notas"
    ]

    extras_dialogo_columns = [
        "ID",
        "Personaje / Extra",
        "Diálogo breve",
        "Cantidad",
        "Notas"
    ]

    if "breakdown_cast_data" not in st.session_state:
        st.session_state.breakdown_cast_data = {}

    if numero_escena not in st.session_state.breakdown_cast_data:

        cast_rows = []

        if personajes_detectados.strip():

            personajes_lista = [
                p.strip()
                for p in personajes_detectados.split(",")
                if p.strip()
            ]

            for personaje in personajes_lista:

                personaje_limpio = re.sub(
                    r"^#\d+\s*",
                    "",
                    personaje
                ).strip()

                cast_rows.append({
                    "ID": len(cast_rows) + 1,
                    "Personaje": personaje_limpio,
                    "Actor/Actriz": "",
                    "Tipo": "Principal",
                    "Notas": ""
                })

        st.session_state.breakdown_cast_data[numero_escena] = {

            "cast": pd.DataFrame(
                cast_rows,
                columns=cast_columns
            ),

            "stunts": pd.DataFrame(
                columns=stunts_columns
            ),

            "extras_atmosfera": pd.DataFrame(
                columns=extras_atmosfera_columns
            ),

            "extras_dialogo": pd.DataFrame(
                columns=extras_dialogo_columns
            )
        }

    estructura = st.session_state.breakdown_cast_data[numero_escena]

    required_tables = {

        "cast": cast_columns,

        "stunts": stunts_columns,

        "extras_atmosfera": extras_atmosfera_columns,

        "extras_dialogo": extras_dialogo_columns
    }

    for key, columns in required_tables.items():

        if key not in estructura:
            estructura[key] = pd.DataFrame(columns=columns)

        if not isinstance(estructura[key], pd.DataFrame):
            estructura[key] = pd.DataFrame(estructura[key])

        for column in columns:
            if column not in estructura[key].columns:
                estructura[key][column] = ""

        estructura[key] = estructura[key][columns].fillna("").copy()

    st.session_state.breakdown_cast_data[numero_escena] = estructura