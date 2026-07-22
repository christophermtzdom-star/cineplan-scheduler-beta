import pandas as pd
import streamlit as st
from project.workspace_runtime import current_character, current_submodule, register_workspace_provider, set_character

from components.icons import (
    ANALYTICS,
    CAST,
    CHARACTER,
    PENDING,
    SAVE,
    STATUS,
    TASK,
)
from components.icons import CAST as ICON_CAST
from components.header import render_section_header
from components.panel import cine_panel


_MASTER_STATE_KEY = "cast_master_df"

_MASTER_COLUMNS = [
    "ID",
    "Personaje",
    "Actor/Actriz",
    "Estado casting",
    "Tipo",
    "Teléfono",
    "Email",
    "Representante",
    "Doble requerido",
    "Observaciones",
]

_CASTING_STATUSES = [
    "Pendiente",
    "Confirmado",
    "Reemplazo",
]

_CHARACTER_TYPES = [
    "Principal",
    "Secundario",
    "Cameo",
]

_YES_NO_OPTIONS = ["No", "Sí"]


def _icon_label(icon, label):
    return f":material/{icon}: {label}"


def _clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _new_master_record(source_row):
    return {
        "ID": source_row.get("ID", ""),
        "Personaje": _clean_text(source_row.get("Personaje", "")),
        "Actor/Actriz": _clean_text(source_row.get("Actor/Actriz", "")),
        "Estado casting": "Pendiente",
        "Tipo": "Principal",
        "Teléfono": _clean_text(source_row.get("Contacto", "")),
        "Email": "",
        "Representante": "",
        "Doble requerido": "No",
        "Observaciones": _clean_text(source_row.get("Notas", "")),
    }


def _find_existing_record(master_df, source_row):
    source_id = _clean_text(source_row.get("ID", ""))
    source_name = _clean_text(source_row.get("Personaje", "")).casefold()

    if source_id:
        id_matches = master_df[
            master_df["ID"].map(_clean_text) == source_id
        ]
        if not id_matches.empty:
            return id_matches.iloc[0].to_dict()

    if source_name:
        name_matches = master_df[
            master_df["Personaje"].map(_clean_text).str.casefold()
            == source_name
        ]
        if not name_matches.empty:
            return name_matches.iloc[0].to_dict()

    return None


def _synchronize_master_catalog():
    characters_df = st.session_state.get("characters_df", pd.DataFrame())

    if characters_df is None or characters_df.empty:
        return pd.DataFrame(columns=_MASTER_COLUMNS)

    current_master = st.session_state.get(
        _MASTER_STATE_KEY,
        pd.DataFrame(columns=_MASTER_COLUMNS)
    )

    if not isinstance(current_master, pd.DataFrame):
        current_master = pd.DataFrame(current_master)

    for column in _MASTER_COLUMNS:
        if column not in current_master.columns:
            current_master[column] = ""

    current_master = current_master[_MASTER_COLUMNS].fillna("").copy()
    synchronized_records = []
    seen_characters = set()

    for _, source_row in characters_df.iterrows():
        character_name = _clean_text(source_row.get("Personaje", ""))
        identity = character_name.casefold()

        if not character_name or identity in seen_characters:
            continue

        seen_characters.add(identity)
        existing_record = _find_existing_record(current_master, source_row)

        if existing_record is None:
            record = _new_master_record(source_row)
        else:
            record = {
                column: existing_record.get(column, "")
                for column in _MASTER_COLUMNS
            }
            record["ID"] = source_row.get("ID", record["ID"])
            record["Personaje"] = character_name

        record["Estado casting"] = (
            _clean_text(record["Estado casting"]) or "Pendiente"
        )
        record["Tipo"] = _clean_text(record["Tipo"]) or "Principal"
        record["Doble requerido"] = (
            _clean_text(record["Doble requerido"]) or "No"
        )

        synchronized_records.append(record)

    synchronized_df = pd.DataFrame(
        synchronized_records,
        columns=_MASTER_COLUMNS
    ).fillna("")

    st.session_state[_MASTER_STATE_KEY] = synchronized_df.copy()
    return synchronized_df


def _select_index(options, value, fallback=0):
    return options.index(value) if value in options else fallback


def _render_character_selector(master_df):
    options = master_df.index.tolist()
    restored_character = current_character()
    default_index = next(
        (position for position, index in enumerate(options)
         if str(master_df.at[index, "Personaje"]) == restored_character),
        0,
    )
    with cine_panel(
        title=_icon_label(CHARACTER, "Personaje actual"),
        subtitle="Selecciona el personaje cuya ficha de talento deseas editar.",
    ):
        selected_index = st.selectbox(
            "Seleccionar personaje",
            options=options,
            index=default_index,
            format_func=lambda index: master_df.at[index, "Personaje"],
            key="cast_master_character_selector"
        )

        selected_row = master_df.loc[selected_index]
        if current_submodule() == "Cast / Talento":
            character = selected_row.get("Personaje", "")
            set_character(character)
            register_workspace_provider("cast:character", lambda: {"character": character})
        id_column, character_column, status_column = st.columns([0.7, 2.2, 1])
        id_column.metric("ID", selected_row.get("ID", "-"))
        character_column.metric(
            "Personaje",
            selected_row.get("Personaje", "-") or "-"
        )
        status_column.metric(
            "Estado",
            selected_row.get("Estado casting", "Pendiente") or "Pendiente"
        )

    return selected_index


def _render_character_sheet(selected_index, character_record):
    widget_prefix = f"cast_master_{selected_index}"

    with st.form(f"form_cast_master_{selected_index}"):
        with cine_panel(
            title=_icon_label(CAST, "Ficha maestra de talento"),
            subtitle="Información general de casting para todo el proyecto.",
        ):
            identity_column, character_column = st.columns([0.7, 2.3])

            with identity_column:
                st.text_input(
                    "ID",
                    value=_clean_text(character_record.get("ID", "")),
                    disabled=True,
                    key=f"{widget_prefix}_id"
                )

            with character_column:
                st.text_input(
                    "Personaje",
                    value=_clean_text(character_record.get("Personaje", "")),
                    disabled=True,
                    key=f"{widget_prefix}_character"
                )

            actor = st.text_input(
                "Actor / Actriz",
                value=_clean_text(character_record.get("Actor/Actriz", "")),
                key=f"{widget_prefix}_actor"
            )

            status_column, type_column = st.columns(2)

            with status_column:
                casting_status = st.selectbox(
                    "Estado de casting",
                    _CASTING_STATUSES,
                    index=_select_index(
                        _CASTING_STATUSES,
                        _clean_text(character_record.get("Estado casting", ""))
                    ),
                    key=f"{widget_prefix}_status"
                )

            with type_column:
                character_type = st.selectbox(
                    "Tipo de personaje",
                    _CHARACTER_TYPES,
                    index=_select_index(
                        _CHARACTER_TYPES,
                        _clean_text(character_record.get("Tipo", ""))
                    ),
                    key=f"{widget_prefix}_type"
                )

            phone_column, email_column = st.columns(2)

            with phone_column:
                phone = st.text_input(
                    "Teléfono",
                    value=_clean_text(character_record.get("Teléfono", "")),
                    key=f"{widget_prefix}_phone"
                )

            with email_column:
                email = st.text_input(
                    "Email",
                    value=_clean_text(character_record.get("Email", "")),
                    key=f"{widget_prefix}_email"
                )

            representative_column, double_column = st.columns([2, 1])

            with representative_column:
                representative = st.text_input(
                    "Representante (opcional)",
                    value=_clean_text(character_record.get("Representante", "")),
                    key=f"{widget_prefix}_representative"
                )

            with double_column:
                double_required = st.selectbox(
                    "Doble requerido",
                    _YES_NO_OPTIONS,
                    index=_select_index(
                        _YES_NO_OPTIONS,
                        _clean_text(character_record.get("Doble requerido", ""))
                    ),
                    key=f"{widget_prefix}_double"
                )

            observations = st.text_area(
                "Observaciones generales",
                value=_clean_text(character_record.get("Observaciones", "")),
                height=160,
                key=f"{widget_prefix}_observations"
            )

        st.write("")
        _, save_column, _ = st.columns([1, 2, 1])

        with save_column:
            save_character = st.form_submit_button(
                "Guardar ficha de talento",
                icon=f":material/{SAVE}:",
                type="primary",
                use_container_width=True
            )

        if save_character:
            master_df = st.session_state[_MASTER_STATE_KEY].copy()
            master_df.at[selected_index, "Actor/Actriz"] = actor
            master_df.at[selected_index, "Estado casting"] = casting_status
            master_df.at[selected_index, "Tipo"] = character_type
            master_df.at[selected_index, "Teléfono"] = phone
            master_df.at[selected_index, "Email"] = email
            master_df.at[selected_index, "Representante"] = representative
            master_df.at[selected_index, "Doble requerido"] = double_required
            master_df.at[selected_index, "Observaciones"] = observations
            st.session_state[_MASTER_STATE_KEY] = master_df
            st.success("Ficha de talento guardada correctamente.")


def _get_dashboard_metrics(master_df):
    actors = master_df["Actor/Actriz"].astype(str).str.strip()
    statuses = master_df["Estado casting"].astype(str).str.casefold()
    types = master_df["Tipo"].astype(str).str.casefold()
    observations = master_df["Observaciones"].astype(str).str.strip()

    return {
        "total": len(master_df),
        "confirmed": int(statuses.eq("confirmado").sum()),
        "pending": int(statuses.eq("pendiente").sum()),
        "principal": int(types.eq("principal").sum()),
        "secondary": int(types.eq("secundario").sum()),
        "cameos": int(types.eq("cameo").sum()),
        "without_actor": int(actors.eq("").sum()),
        "observations": int(observations.ne("").sum()),
    }


def _render_cast_dashboard(master_df):
    metrics = _get_dashboard_metrics(master_df)

    st.markdown(f"## {_icon_label(ANALYTICS, 'Resumen de Cast')}")
    st.caption("Estado general del catálogo de talento del proyecto.")

    with cine_panel(
        title=_icon_label(CAST, "Casting del proyecto"),
        subtitle="Asignación de talento y estado de casting.",
    ):
        first_row = st.columns(2)
        first_row[0].metric(
            _icon_label(CHARACTER, "Personajes"),
            metrics["total"]
        )
        first_row[1].metric(
            _icon_label(TASK, "Confirmados"),
            metrics["confirmed"]
        )

        second_row = st.columns(2)
        second_row[0].metric(
            _icon_label(PENDING, "Casting pendiente"),
            metrics["pending"]
        )
        second_row[1].metric(
            _icon_label(PENDING, "Sin actor"),
            metrics["without_actor"]
        )

    with cine_panel(
        title=_icon_label(STATUS, "Clasificación"),
        subtitle="Tipos de personaje y fichas documentadas.",
    ):
        type_columns = st.columns(3)
        type_columns[0].metric("Principales", metrics["principal"])
        type_columns[1].metric("Secundarios", metrics["secondary"])
        type_columns[2].metric("Cameos", metrics["cameos"])
        st.metric("Con observaciones", metrics["observations"])


def _render_summary_table(master_df):
    summary_df = master_df[
        [
            "ID",
            "Personaje",
            "Actor/Actriz",
            "Estado casting",
            "Tipo",
            "Teléfono",
            "Email",
            "Representante",
        ]
    ].rename(columns={
        "Personaje": "Personaje",
        "Actor/Actriz": "Actor",
        "Estado casting": "Estado",
        "Tipo": "Tipo",
        "Teléfono": "Teléfono",
        "Email": "Email",
        "Representante": "Representante",
    })

    with cine_panel(
        title=_icon_label(TASK, "Resumen del talento"),
        subtitle="Vista general de consulta. La edición se realiza en la ficha.",
    ):
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True
        )


def render_cast_page():
    render_section_header(
        icon=ICON_CAST,
        title="Cast / Talento",
        description=(
            "Administra el catálogo maestro del elenco del proyecto. La información "
            "registrada aquí será utilizada por Vestuario, Producción, Stripboard, "
            "Hojas de llamado y Exportación."
        )
    )

    master_df = _synchronize_master_catalog()

    if master_df.empty:
        st.info(
            "No hay personajes detectados. Revisa primero la sección Personajes "
            "en Importar y revisar."
        )
        return

    selected_index = _render_character_selector(master_df)
    work_column, dashboard_column = st.columns([1.85, 1], gap="large")

    with work_column:
        _render_character_sheet(selected_index, master_df.loc[selected_index])

    with dashboard_column:
        current_master = st.session_state[_MASTER_STATE_KEY]
        _render_cast_dashboard(current_master)

    st.write("")
    _render_summary_table(st.session_state[_MASTER_STATE_KEY])
