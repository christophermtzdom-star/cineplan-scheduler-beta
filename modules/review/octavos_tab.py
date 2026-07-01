import streamlit as st
import pandas as pd

from project.importer import (
    normalize_octavos_value,
    normalize_scene_octavos_fields,
    number_to_octavos
)


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
    except:
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


def render_octavos_tab():

    st.markdown("### Octavos")

    if "scenes_df" not in st.session_state or st.session_state.scenes_df.empty:
        st.info("No hay escenas disponibles.")
        return

    octavos_columns = [
        "Escena",
        "Locación",
        "INT/EXT",
        "Tiempo",
        "octavos_auto",
        "octavos_manual",
        "octavos_final"
    ]

    display_df = st.session_state.scenes_df.copy()

    for c in ["octavos_auto", "octavos_manual", "octavos_final"]:
        if c not in display_df.columns:
            display_df[c] = ""

        display_df[c] = (
            display_df[c]
            .fillna("")
            .astype(str)
            .map(normalize_octavos_value)
        )

    available_columns = [
        c for c in octavos_columns
        if c in display_df.columns
    ]

    st.dataframe(
        display_df[available_columns],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Editar octavos de escena")

    options = []
    label_to_index = {}

    for i, row in display_df.iterrows():
        escena_val = str(row.get("Escena", "")).strip()
        locacion_val = str(row.get("Locación", "")).strip()
        int_ext_val = str(row.get("INT/EXT", "")).strip()
        tiempo_val = str(row.get("Tiempo", "")).strip()

        label = f"Escena {escena_val} — {locacion_val or '-'} — {int_ext_val or '-'} — {tiempo_val or '-'}"
        options.append(label)
        label_to_index[label] = i

    if not options:
        st.info("No hay escenas disponibles para editar.")
        return

    if "octavos_manual_inputs" not in st.session_state:
        st.session_state["octavos_manual_inputs"] = {}

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

    auto_value = normalize_octavos_value(scene_row.get("octavos_auto", ""))
    current_manual = normalize_octavos_value(scene_row.get("octavos_manual", ""))
    current_final = normalize_octavos_value(scene_row.get("octavos_final", ""))

    if selected_label not in st.session_state["octavos_manual_inputs"]:
        st.session_state["octavos_manual_inputs"][selected_label] = current_manual

    prev_label = st.session_state.get("octavos_selected_label_prev")

    if prev_label != selected_label:
        st.session_state["octavos_manual_input"] = (
            st.session_state["octavos_manual_inputs"]
            .get(selected_label, current_manual)
        )
        st.session_state["octavos_selected_label_prev"] = selected_label

    manual_input = st.text_input(
        "Nuevo valor manual",
        value=st.session_state.get("octavos_manual_input", ""),
        key="octavos_manual_input"
    )

    manual_input_normalized = normalize_octavos_value(manual_input)
    st.session_state["octavos_manual_inputs"][selected_label] = manual_input_normalized

    st.markdown(f"**Escena seleccionada:** {selected_label}")
    st.markdown(f"**Octavos automáticos:** {auto_value or '-'}")
    st.markdown(f"**Octavos manuales actuales:** {current_manual or '-'}")
    st.markdown(f"**Octavos finales actuales:** {current_final or '-'}")

    if st.button("Actualizar octavos de escena", icon=":material/sync:"):
        final_value = manual_input_normalized if manual_input_normalized else auto_value

        row_dict = scene_row.to_dict()
        row_dict["octavos_auto"] = auto_value
        row_dict["octavos_manual"] = manual_input_normalized
        row_dict["octavos_final"] = final_value
        row_dict["Octavos"] = final_value

        values = normalize_scene_octavos_fields(row_dict)

        idx_label = st.session_state.scenes_df.index[row_index]

        st.session_state.scenes_df.loc[idx_label, "octavos_auto"] = values["octavos_auto"]
        st.session_state.scenes_df.loc[idx_label, "octavos_manual"] = values["octavos_manual"]
        st.session_state.scenes_df.loc[idx_label, "octavos_final"] = values["octavos_final"]
        st.session_state.scenes_df.loc[idx_label, "Octavos"] = values["Octavos"]

        st.success("Octavos actualizados correctamente.")

    total_octavos = sum(
        octavos_to_number(
            obtener_octavos_finales(row.to_dict())
        )
        for _, row in st.session_state.scenes_df.iterrows()
    )

    st.info(f"Total del guion: {number_to_octavos(total_octavos)}")