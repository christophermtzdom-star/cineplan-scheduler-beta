import streamlit as st
from project.workspace_runtime import notify_scene_record, scene_option_index

from components.icons import DESCRIPTION, INFO, NOTE, SAVE, SCENE, STATUS
from components.icons import SCENE as ICON_SCENE
from components.header import render_section_header
from components.panel import cine_panel
from project.importer import normalize_octavos_value
from modules.breakdown.breakdown_summary import render_breakdown_summary


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


def sugerir_color_stripboard(encabezado, int_ext, tiempo):
    encabezado = str(encabezado).upper()
    int_ext = str(int_ext).upper()
    tiempo = str(tiempo).upper()

    especiales = [
        "SUEÑO",
        "FLASH",
        "FLASHBACK",
        "RITUAL",
        "VISIÓN",
        "VISION",
        "MONTAJE",
        "SECUENCIA",
        "PESADILLA",
        "RECUERDO",
        "SOBRENATURAL"
    ]

    if any(palabra in encabezado for palabra in especiales):
        return "Morado"

    if "I/E" in int_ext:
        return "Rosa"

    if "INT" in int_ext and ("DÍA" in tiempo or "DIA" in tiempo):
        return "Blanco"

    if "EXT" in int_ext and ("DÍA" in tiempo or "DIA" in tiempo):
        return "Amarillo"

    if "INT" in int_ext and "NOCHE" in tiempo:
        return "Azul"

    if "EXT" in int_ext and "NOCHE" in tiempo:
        return "Verde"

    return "Blanco"


def _build_scene_options():
    escenas_breakdown = []

    for _, row in st.session_state.scenes_df.iterrows():
        numero = str(row.get("Escena", ""))
        encabezado = str(row.get("Encabezado de escena", ""))

        escenas_breakdown.append(
            f"{numero} | {encabezado}"
        )

    return escenas_breakdown


def _panel_title(icon, label):
    return f":material/{icon}: {label}"


def _render_scene_selector(escenas_breakdown):
    with cine_panel(
        title=_panel_title(SCENE, "Escena actual"),
        subtitle=(
            "Esta es la escena de trabajo activa. Selecciona otra para cambiar "
            "el contexto de edición."
        ),
    ):
        escena_seleccionada = st.selectbox(
            "Seleccionar escena",
            escenas_breakdown,
            index=scene_option_index(escenas_breakdown),
            key="breakdown_scene_selector"
        )

        numero_escena = escena_seleccionada.split(" | ")[0]
        escena_df = st.session_state.scenes_df[
            st.session_state.scenes_df["Escena"].astype(str) == numero_escena
        ]

        if not escena_df.empty:
            escena_data = escena_df.iloc[0]
            notify_scene_record(escena_data, "Datos de escena")
            datos_guardados = st.session_state.get(
                "breakdown_scene_data",
                {}
            ).get(str(numero_escena), {})

            scene_column, heading_column, type_column, time_column, status_column = (
                st.columns([0.75, 2.4, 1, 1, 1.25])
            )

            scene_column.metric("Escena", escena_data.get("Escena", "-"))
            heading_column.metric(
                "Encabezado",
                escena_data.get("Encabezado de escena", "-") or "-"
            )
            type_column.metric(
                "INT / EXT",
                escena_data.get("INT/EXT", "-") or "-"
            )
            time_column.metric(
                "Tiempo",
                escena_data.get("Tiempo", "-") or "-"
            )
            status_column.metric(
                "Estado",
                datos_guardados.get("Estado breakdown", "Pendiente")
            )

        return escena_seleccionada


def _render_legacy_breakdown_preview(
    numero_escena,
    escena_data,
    color_sugerido,
):
    """Legacy preview retained for migration to Export Breakdown."""
    datos_preview = st.session_state.breakdown_scene_data.get(
        str(numero_escena),
        {}
    )

    escena_merged = {
        **escena_data,
        **datos_preview
    }

    octavos_preview = obtener_octavos_finales(escena_merged) or ""

    st.markdown(
        "### Previsualización de hoja de breakdown"
    )

    st.info(
        f"""
            PRODUCCIÓN: {st.session_state.project_info.get("nombre", "")}

            DIRECTOR/A: {st.session_state.project_info.get("director", "")}

            PRODUCTOR/A: {st.session_state.project_info.get("productor", "")}

            VERSIÓN DE GUIÓN: {st.session_state.project_info.get("version_guion", "")}

            --------------------------------------------------

            ESCENA: {datos_preview.get("Escena", escena_data.get("Escena", ""))}

            ENCABEZADO:
            {datos_preview.get("Encabezado de escena", escena_data.get("Encabezado de escena", ""))}

            INT/EXT:
            {datos_preview.get("INT/EXT", escena_data.get("INT/EXT", ""))}

            TIEMPO:
            {datos_preview.get("Tiempo", escena_data.get("Tiempo", ""))}

            LOCACIÓN:
            {datos_preview.get("Locación", escena_data.get("Locación", ""))}

            PÁGINA:
            {datos_preview.get("Página", escena_data.get("Página", ""))}

            OCTAVOS:
            {octavos_preview}

            COLOR STRIPBOARD:
            {datos_preview.get("Color stripboard", color_sugerido)}

            ESTADO:
            {datos_preview.get("Estado breakdown", "Pendiente")}

            --------------------------------------------------

            DESCRIPCIÓN:
            {datos_preview.get("Descripción", "")}

            --------------------------------------------------

            NOTAS:
            {datos_preview.get("Notas de escena", "")}
            """
    )


def render_scene_page():
    render_section_header(
        icon=ICON_SCENE,
        title="Datos de escena",
        description=(
            "Revisa y completa la información general de cada escena antes de "
            "iniciar el desglose de producción."
        )
    )

    escenas_breakdown = _build_scene_options()

    if not escenas_breakdown:
        st.warning("No hay escenas disponibles.")
        return

    escena_seleccionada = _render_scene_selector(escenas_breakdown)

    numero_escena = escena_seleccionada.split(" | ")[0]

    escena_df = st.session_state.scenes_df[
        st.session_state.scenes_df["Escena"].astype(str) == numero_escena
    ]

    if escena_df.empty:
        st.warning("No se encontró la escena seleccionada.")
        return

    escena_data = escena_df.iloc[0]

    if "breakdown_scene_data" not in st.session_state:
        st.session_state.breakdown_scene_data = {}

    datos_guardados = st.session_state.breakdown_scene_data.get(
        str(numero_escena),
        {}
    )

    color_sugerido = sugerir_color_stripboard(
        escena_data.get("Encabezado de escena", ""),
        escena_data.get("INT/EXT", ""),
        escena_data.get("Tiempo", "")
    )

    content_column, summary_column = st.columns(
        [1.85, 1],
        gap="large"
    )

    with content_column:
        with st.form(f"form_datos_escena_{numero_escena}"):
            with cine_panel(
                title=_panel_title(INFO, "Información general"),
                subtitle="Datos principales para identificar y planificar la escena.",
            ):
                number_column, heading_column = st.columns([1, 2])

                with number_column:
                    escena_numero = st.text_input(
                        "Número de escena",
                        value=str(escena_data.get("Escena", "")),
                        key=f"escena_numero_{numero_escena}"
                    )

                with heading_column:
                    encabezado = st.text_input(
                        "Encabezado de escena",
                        value=str(
                            escena_data.get("Encabezado de escena", "")
                        ),
                        key=f"encabezado_{numero_escena}"
                    )

                int_ext_column, time_column = st.columns(2)

                opciones_int_ext = [
                    "INT.",
                    "EXT.",
                    "I/E.",
                    "ESPECIAL"
                ]

                valor_actual_int_ext = str(
                    escena_data.get("INT/EXT", "INT.")
                )

                if valor_actual_int_ext not in opciones_int_ext:
                    valor_actual_int_ext = "INT."

                with int_ext_column:
                    int_ext = st.selectbox(
                        "INT / EXT",
                        opciones_int_ext,
                        index=opciones_int_ext.index(valor_actual_int_ext),
                        key=f"int_ext_{numero_escena}"
                    )

                with time_column:
                    tiempo = st.text_input(
                        "Día / Noche / Tiempo",
                        value=str(escena_data.get("Tiempo", "")),
                        key=f"tiempo_{numero_escena}"
                    )

                page_column, eighths_column = st.columns(2)

                with page_column:
                    pagina = st.text_input(
                        "Página",
                        value=str(escena_data.get("Página", "")),
                        key=f"pagina_{numero_escena}"
                    )

                with eighths_column:
                    octavos = st.text_input(
                        "Octavos",
                        value=str(escena_data.get("Octavos", "")),
                        key=f"octavos_{numero_escena}"
                    )

                locacion = st.text_input(
                    "Locación",
                    value=str(escena_data.get("Locación", "")),
                    key=f"locacion_{numero_escena}"
                )

            st.write("")

            with cine_panel(
                title=_panel_title(STATUS, "Estado de la escena"),
                subtitle="Control visual y avance dentro del breakdown.",
            ):
                status_column, color_column = st.columns(2)

                estados_breakdown = [
                    "Pendiente",
                    "En proceso",
                    "Revisado",
                    "Listo para exportar"
                ]

                estado_actual = datos_guardados.get(
                    "Estado breakdown",
                    "Pendiente"
                )

                if estado_actual not in estados_breakdown:
                    estado_actual = "Pendiente"

                with status_column:
                    estado_breakdown = st.selectbox(
                        "Estado del breakdown",
                        estados_breakdown,
                        index=estados_breakdown.index(estado_actual),
                        key=f"estado_breakdown_{numero_escena}"
                    )

                colores_stripboard = [
                    "Blanco",
                    "Amarillo",
                    "Azul",
                    "Verde",
                    "Rosa",
                    "Morado"
                ]

                color_actual = datos_guardados.get(
                    "Color stripboard",
                    color_sugerido
                )

                if color_actual not in colores_stripboard:
                    color_actual = color_sugerido

                with color_column:
                    color_stripboard = st.selectbox(
                        "Color stripboard",
                        colores_stripboard,
                        index=colores_stripboard.index(color_actual),
                        key=f"color_stripboard_{numero_escena}"
                    )

            st.write("")

            with cine_panel(title=_panel_title(DESCRIPTION, "Descripción")):
                descripcion = st.text_area(
                    "Descripción breve de la escena",
                    value=datos_guardados.get("Descripción", ""),
                    key=f"descripcion_escena_{numero_escena}",
                    height=180
                )

            st.write("")

            with cine_panel(title=_panel_title(NOTE, "Notas")):
                notas_escena = st.text_area(
                    "Notas de escena",
                    value=datos_guardados.get(
                        "Notas de escena",
                        str(escena_data.get("Notas", ""))
                    ),
                    key=f"notas_escena_{numero_escena}",
                    height=180
                )

            st.write("")
            st.write("")

            _, save_column, _ = st.columns([1, 2, 1])

            with save_column:
                guardar_datos_escena = st.form_submit_button(
                    "Guardar cambios",
                    icon=f":material/{SAVE}:",
                    use_container_width=True
                )

            if guardar_datos_escena:
                idx = st.session_state.scenes_df[
                    st.session_state.scenes_df["Escena"].astype(str)
                    == numero_escena
                ].index[0]

                st.session_state.scenes_df.at[
                    idx,
                    "Escena"
                ] = int(escena_numero)

                st.session_state.scenes_df.at[
                    idx,
                    "Encabezado de escena"
                ] = encabezado.upper()

                st.session_state.scenes_df.at[
                    idx,
                    "INT/EXT"
                ] = int_ext

                st.session_state.scenes_df.at[
                    idx,
                    "Tiempo"
                ] = tiempo.upper()

                st.session_state.scenes_df.at[
                    idx,
                    "Locación"
                ] = locacion.upper()

                st.session_state.scenes_df.at[
                    idx,
                    "Página"
                ] = pagina

                st.session_state.scenes_df.at[
                    idx,
                    "Octavos"
                ] = octavos

                st.session_state.scenes_df.at[
                    idx,
                    "Notas"
                ] = notas_escena

                st.session_state.breakdown_scene_data[
                    str(escena_numero)
                ] = {
                    "Escena": escena_numero,
                    "Encabezado de escena": encabezado.upper(),
                    "INT/EXT": int_ext,
                    "Tiempo": tiempo.upper(),
                    "Locación": locacion.upper(),
                    "Página": pagina,
                    "Octavos": octavos,
                    "Color stripboard": color_stripboard,
                    "Estado breakdown": estado_breakdown,
                    "Descripción": descripcion,
                    "Notas de escena": notas_escena
                }

                st.success(
                    "Datos de escena guardados correctamente."
                )

    with summary_column:
        render_breakdown_summary()

    # LEGACY: _render_legacy_breakdown_preview() is intentionally not called.
    # The preview is retained above for future migration to Export Breakdown.
