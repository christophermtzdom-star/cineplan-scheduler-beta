import streamlit as st
import pandas as pd

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


def render_summary_tab():

    st.markdown("### Resumen general")

    scenes_df = st.session_state.get("scenes_df", pd.DataFrame())
    characters_df = st.session_state.get("characters_df", pd.DataFrame())

    if scenes_df.empty:
        st.info("No hay información disponible.")
        return

    if "Estado" not in st.session_state.scenes_df.columns:
        st.session_state.scenes_df["Estado"] = "Pendiente"

    st.session_state.scenes_df["Estado"] = (
        st.session_state.scenes_df["Estado"]
        .fillna("Pendiente")
        .replace("", "Pendiente")
    )

    total_octavos = sum(
        octavos_to_number(
            obtener_octavos_finales(row.to_dict())
        )
        for _, row in st.session_state.scenes_df.iterrows()
    )

    total_escenas = len(st.session_state.scenes_df)

    revisadas = (
        st.session_state.scenes_df["Estado"]
        .astype(str)
        .eq("Revisado")
        .sum()
    )

    pendientes = total_escenas - revisadas

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Escenas", total_escenas)
    col2.metric("Revisadas", revisadas)
    col3.metric("Pendientes", pendientes)
    col4.metric("Octavos totales", number_to_octavos(total_octavos))

    st.divider()

    summary_df = st.session_state.scenes_df.copy()

    if "octavos_final" in summary_df.columns:
        summary_df["Octavos finales"] = summary_df["octavos_final"]
    elif "Octavos" in summary_df.columns:
        summary_df["Octavos finales"] = summary_df["Octavos"]
    else:
        summary_df["Octavos finales"] = ""

    columns_to_remove = [
        "octavos_auto",
        "octavos_manual",
        "octavos_final",
        "Octavos",
        "octavos"
    ]

    summary_df = summary_df.drop(
        columns=[c for c in columns_to_remove if c in summary_df.columns],
        errors="ignore"
    )

    st.markdown("### Validación final de escenas")

    with st.form("form_resumen_revision"):
        edited_summary = st.data_editor(
            summary_df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "Estado": st.column_config.SelectboxColumn(
                    "Estado",
                    options=ESTADO_OPTIONS,
                    required=True
                )
            }
        )

        guardar_resumen = st.form_submit_button(
            "Guardar revisión final"
        )

        if guardar_resumen:
            st.session_state.scenes_df["Estado"] = edited_summary["Estado"].values
            st.success("Estados de revisión actualizados correctamente.")
            st.rerun()

    st.divider()

    revisadas_actualizadas = (
        st.session_state.scenes_df["Estado"]
        .astype(str)
        .eq("Revisado")
        .sum()
    )

    pendientes_actualizadas = total_escenas - revisadas_actualizadas

    if total_escenas > 0 and revisadas_actualizadas == total_escenas:

        st.success(
            "Revisión final completada. Todas las escenas han sido revisadas."
        )

        if st.button(
            "Continuar al Breakdown",
            icon=":material/arrow_forward:",
            use_container_width=True
        ):
            st.session_state.main_menu = "2. Breakdown"
            st.session_state.current_view = "modules"
            st.rerun()

    else:

        st.warning(
            f"Aún faltan {pendientes_actualizadas} escena(s) por revisar antes de continuar con el Breakdown."
        )