from collections.abc import Mapping
from datetime import datetime
from html import escape
from io import BytesIO
import sys

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader, PdfWriter
from project.workspace_runtime import register_workspace_provider, set_document

from components.header import render_section_header
from components.icons import (
    ANALYTICS,
    CALLSHEET,
    CAST,
    EXCEL,
    EXPORT,
    EXTRAS,
    PDF,
    PRODUCTION,
    PROPS,
    SCENE,
    VFX,
    WARDROBE,
)
from components.panel import cine_panel
from modules.breakdown.document_framework import (
    DOCUMENT_DEFINITIONS,
    DOCUMENTS_BY_LABEL,
    column_weights,
    editorial_pdf,
    export_filename,
    format_excel_worksheet,
)
from modules.breakdown.document_layout import (
    GRID,
    html_box_style,
    html_footer,
    html_header,
    html_page_style,
    html_scene_accent,
    html_section_title,
)


_MODE_OPTIONS = ["Escena actual", "Escenas seleccionadas", "Proyecto completo"]
_SELECTED_SCENE_KEY = "export_selected_scene"

_DOCUMENT_OPTIONS = tuple(definition.label for definition in DOCUMENT_DEFINITIONS)


def _icon_label(icon, label):
    return f":material/{icon}: {label}"


def _clean_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _scene_sort_key(scene_number):
    try:
        return 0, float(str(scene_number).strip())
    except ValueError:
        return 1, str(scene_number).casefold()


def _scene_records():
    scenes_df = st.session_state.get("scenes_df", pd.DataFrame())
    if not isinstance(scenes_df, pd.DataFrame) or scenes_df.empty:
        return []
    records = scenes_df.fillna("").to_dict(orient="records")
    return sorted(records, key=lambda row: _scene_sort_key(row.get("Escena", "")))


def _scene_number(row):
    return _clean_text(row.get("Escena"))


def _scene_heading(row):
    return _clean_text(row.get("Encabezado de escena")) or "Sin encabezado"


def _first_value(mapping, *keys, fallback=""):
    if not isinstance(mapping, Mapping):
        return fallback
    for key in keys:
        value = _clean_text(mapping.get(key))
        if value:
            return value
    return fallback


def _scene_details(scene):
    number = _scene_number(scene)
    saved = st.session_state.get("breakdown_scene_data", {})
    saved = saved.get(number, {}) if isinstance(saved, Mapping) else {}
    return {**scene, **(dict(saved) if isinstance(saved, Mapping) else {})}


def _as_dataframe(value):
    if isinstance(value, pd.DataFrame):
        return value.fillna("").copy()
    if isinstance(value, (list, tuple)):
        try:
            return pd.DataFrame(value).fillna("")
        except (TypeError, ValueError):
            return pd.DataFrame()
    return pd.DataFrame()


def _scene_department_data(state_key, scene_number):
    state = st.session_state.get(state_key, {})
    if not isinstance(state, Mapping):
        return {}
    value = state.get(str(scene_number), state.get(scene_number, {}))
    return value if isinstance(value, Mapping) else {}


def _row_label(row, preferred_columns):
    for column in preferred_columns:
        value = _clean_text(row.get(column))
        if value and value not in {"Ninguno", "No"}:
            return value
    values = [
        _clean_text(value)
        for key, value in row.items()
        if key != "ID" and _clean_text(value)
    ]
    return " · ".join(values[:2])


def _mapping_labels(mapping, preferred_columns):
    labels = []
    if not isinstance(mapping, Mapping):
        return labels
    for value in mapping.values():
        dataframe = _as_dataframe(value)
        if dataframe.empty:
            continue
        for row in dataframe.to_dict(orient="records"):
            label = _row_label(row, preferred_columns)
            if label:
                labels.append(label)
    return labels


def _cast_labels(scene, scene_number):
    cast_data = _scene_department_data("breakdown_cast_data", scene_number)
    labels = _mapping_labels(
        cast_data, ("Personaje", "Personaje / Extra", "Personaje / Tipo")
    )
    if labels:
        return labels
    detected = _first_value(scene, "Personajes", "Personajes detectados")
    return [item.strip() for item in detected.split(",") if item.strip()]


def _wardrobe_labels(scene_number):
    state = st.session_state.get("breakdown_wardrobe_makeup_data", {})
    if not isinstance(state, Mapping):
        return []
    catalog = state.get("__character_looks__", {})
    if not isinstance(catalog, Mapping):
        return []
    labels = []
    for record in catalog.values():
        if not isinstance(record, Mapping):
            continue
        character = _clean_text(record.get("character"))
        looks = record.get("looks", {})
        if not isinstance(looks, Mapping):
            continue
        for look in looks.values():
            if not isinstance(look, Mapping):
                continue
            scenes = {_clean_text(item) for item in look.get("scenes", [])}
            if str(scene_number) in scenes:
                look_name = _clean_text(look.get("name")) or "Look"
                labels.append(f"{character} — {look_name}" if character else look_name)
    return labels


def _production_labels(scene_number):
    data = _scene_department_data("breakdown_production_notes_data", scene_number)
    notes = _as_dataframe(data.get("notas_produccion"))
    labels = []
    if not notes.empty:
        for row in notes.to_dict(orient="records"):
            department = _clean_text(row.get("Departamento")) or "Producción"
            instruction = _clean_text(row.get("Instrucción"))
            observation = _clean_text(row.get("Observaciones"))
            detail = instruction or observation
            labels.append(f"{department}: {detail}" if detail else department)
    legacy = _clean_text(data.get("notas_generales"))
    if legacy and not any(legacy in label for label in labels):
        labels.append(legacy)
    return labels


def _preview_sections(scene):
    number = _scene_number(scene)
    props = _mapping_labels(
        _scene_department_data("breakdown_props_data", number),
        ("Prop", "Elemento", "Prop especial"),
    )
    vfx = _mapping_labels(
        _scene_department_data("breakdown_vfx_sound_data", number),
        ("VFX requerido", "SFX práctico", "Elemento sonoro", "Requerimiento"),
    )
    extras = _mapping_labels(
        _scene_department_data("breakdown_extras_data", number),
        ("Tipo extra", "Personaje / Tipo", "Vehículo", "Animal"),
    )
    return (
        ("Cast", CAST, _cast_labels(scene, number)),
        ("Props / Utilería", PROPS, props),
        ("Vestuario / Maquillaje", WARDROBE, _wardrobe_labels(number)),
        ("VFX / Efectos Prácticos / Sonido", VFX, vfx),
        ("Extras / Vehículos / Animales", EXTRAS, extras),
        ("Notas de Producción", PRODUCTION, _production_labels(number)),
    )


def _project_information():
    value = st.session_state.get("project_info", {})
    return value if isinstance(value, Mapping) else {}


def _count_dataframes(value):
    if isinstance(value, pd.DataFrame):
        return len(value)
    if isinstance(value, Mapping):
        return sum(_count_dataframes(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return len(value)
    return 0


def _summary_metrics(scenes):
    characters_df = st.session_state.get("characters_df", pd.DataFrame())
    character_count = len(characters_df) if isinstance(characters_df, pd.DataFrame) else 0
    wardrobe = st.session_state.get("breakdown_wardrobe_makeup_data", {})
    catalog = wardrobe.get("__character_looks__", {}) if isinstance(wardrobe, Mapping) else {}
    looks = 0
    if isinstance(catalog, Mapping):
        looks = sum(
            len(record.get("looks", {}))
            for record in catalog.values()
            if isinstance(record, Mapping) and isinstance(record.get("looks", {}), Mapping)
        )
    return (
        ("Escenas", len(scenes), SCENE),
        ("Personajes", character_count, CAST),
        ("Props", _count_dataframes(st.session_state.get("breakdown_props_data", {})), PROPS),
        ("Looks", looks, WARDROBE),
        ("VFX", _count_dataframes(st.session_state.get("breakdown_vfx_sound_data", {})), VFX),
        ("Extras", _count_dataframes(st.session_state.get("breakdown_extras_data", {})), EXTRAS),
        ("Notas", _count_dataframes(st.session_state.get("breakdown_production_notes_data", {})), PRODUCTION),
    )


def _render_summary(scenes):
    with cine_panel(
        title=_icon_label(ANALYTICS, "Resumen del Breakdown"),
        subtitle="Información registrada actualmente en el proyecto.",
    ):
        for label, value, icon in _summary_metrics(scenes):
            st.metric(_icon_label(icon, label), value)


def _select_scene(scene_number):
    st.session_state[_SELECTED_SCENE_KEY] = scene_number
    st.rerun()


def _render_scene_navigation(scenes, selected_number):
    with cine_panel(
        title=_icon_label(SCENE, "Navegación de escenas"),
    ):
        query = st.text_input(
            "Buscar escena",
            placeholder="Número, encabezado o locación",
            key="export_scene_search",
        ).strip().casefold()
        filtered = [
            scene for scene in scenes
            if not query
            or query in _scene_number(scene).casefold()
            or query in _scene_heading(scene).casefold()
            or query in _first_value(
                _scene_details(scene), "Locación", "Locacion"
            ).casefold()
        ]

        st.caption("Escena actual")
        if not filtered:
            st.info("No se encontraron escenas.")
        else:
            filtered_numbers = [_scene_number(scene) for scene in filtered]
            selector_key = "export_compact_scene_selector"
            stored_selection = st.session_state.get(selector_key)
            if stored_selection not in filtered_numbers:
                st.session_state[selector_key] = (
                    selected_number if selected_number in filtered_numbers else None
                )
            selected_scene_number = st.selectbox(
                "Seleccionar escena",
                filtered_numbers,
                index=None,
                format_func=lambda number: (
                    f"{number} · {_scene_heading(filtered[filtered_numbers.index(number)])}"
                ),
                placeholder="Selecciona una escena",
                label_visibility="collapsed",
                key=selector_key,
            )
            if (
                selected_scene_number is not None
                and selected_scene_number != selected_number
            ):
                _select_scene(selected_scene_number)

        numbers = [_scene_number(scene) for scene in scenes]
        current_index = numbers.index(selected_number)
        previous, position, following = st.columns([1, 0.8, 1])
        with previous:
            if st.button(
                "◀ Escena anterior",
                key="export_compact_previous_scene",
                disabled=current_index == 0,
                use_container_width=True,
            ):
                _change_scene(scenes, selected_number, -1)
        position.markdown(
            f"<div style='text-align:center;padding-top:8px'>"
            f"<strong>{current_index + 1} de {len(scenes)}</strong></div>",
            unsafe_allow_html=True,
        )
        with following:
            if st.button(
                "Escena siguiente ▶",
                key="export_compact_next_scene",
                disabled=current_index == len(scenes) - 1,
                use_container_width=True,
            ):
                _change_scene(scenes, selected_number, 1)


def _prepare_mode_state():
    st.session_state.setdefault("export_options_mode", _MODE_OPTIONS[0])


def _change_scene(scenes, selected_number, offset):
    numbers = [_scene_number(scene) for scene in scenes]
    current_index = numbers.index(selected_number)
    new_index = max(0, min(len(numbers) - 1, current_index + offset))
    st.session_state[_SELECTED_SCENE_KEY] = numbers[new_index]
    st.rerun()


def _render_preview_navigation(scenes, selected_number):
    previous, current, following = st.columns([1, 2, 1])
    with previous:
        if st.button(
            "◀ Escena anterior",
            key="export_previous_scene",
            disabled=selected_number == _scene_number(scenes[0]),
            use_container_width=True,
        ):
            _change_scene(scenes, selected_number, -1)
    numbers = [_scene_number(scene) for scene in scenes]
    position = numbers.index(selected_number) + 1
    current.markdown(
        f"<div style='text-align:center;padding-top:8px'><strong>"
        f"Escena {position} de {len(scenes)}</strong></div>",
        unsafe_allow_html=True,
    )
    with following:
        if st.button(
            "Escena siguiente ▶",
            key="export_next_scene",
            disabled=selected_number == _scene_number(scenes[-1]),
            use_container_width=True,
        ):
            _change_scene(scenes, selected_number, 1)


def _cast_rows(scene, scene_number):
    scene_cast = _scene_department_data("breakdown_cast_data", scene_number)
    cast_table = _as_dataframe(scene_cast.get("cast"))
    master = st.session_state.get("cast_master_df", pd.DataFrame())
    master = master if isinstance(master, pd.DataFrame) else pd.DataFrame(master)
    master_by_name = {}
    if not master.empty and "Personaje" in master.columns:
        master_by_name = {
            _clean_text(row.get("Personaje")).casefold(): row
            for row in master.to_dict(orient="records")
            if _clean_text(row.get("Personaje"))
        }

    source_rows = cast_table.to_dict(orient="records")
    if not source_rows:
        source_rows = [
            {"Personaje": name}
            for name in _cast_labels(scene, scene_number)
        ]
    rows, seen = [], set()
    for row in source_rows:
        character = _first_value(
            row, "Personaje", "Personaje / Extra", "Personaje / Tipo"
        )
        identity = character.casefold()
        if not character or identity in seen:
            continue
        seen.add(identity)
        master_row = master_by_name.get(identity, {})
        double = _first_value(master_row, "Doble requerido")
        if double:
            double = "Sí" if double.casefold() in {"sí", "si", "yes", "true", "1"} else "No"
        rows.append({
            "Personaje": character,
            "Actor / Actriz": _first_value(master_row, "Actor/Actriz"),
            "Tipo": _first_value(master_row, "Tipo"),
            "Estado": _first_value(master_row, "Estado casting"),
            "Doble": double,
        })
    return rows


def _props_rows(scene_number):
    data = _scene_department_data("breakdown_props_data", scene_number)
    rows = []
    categories = (
        ("props_mano", "Mano", ("Prop",), ("Personaje que lo usa",), ("Continuidad",)),
        ("set_dressing", "Set", ("Elemento",), ("Área / Set",), ()),
        ("props_especiales", "Especial", ("Prop especial",), (), ("FX asociado",)),
        ("utileria_riesgo", "Riesgo", ("Elemento",), (), ("Tipo", "Seguridad requerida")),
    )
    for key, category, element_keys, area_keys, detail_keys in categories:
        for row in _as_dataframe(data.get(key)).to_dict(orient="records"):
            prop = _first_value(row, *element_keys)
            if prop:
                detail = " / ".join(filter(None, (_clean_text(row.get(k)) for k in detail_keys)))
                rows.append({
                    "Categoría": category,
                    "Elemento": prop,
                    "Cantidad": _first_value(row, "Cantidad"),
                    "Personaje / Área": _first_value(row, *area_keys),
                    "Continuidad / FX / Riesgo": detail,
                    "Responsable": _first_value(row, "Responsable"),
                })
    return rows


def _wardrobe_rows(scene_number):
    rows = []
    state = st.session_state.get("breakdown_wardrobe_makeup_data", {})
    catalog = state.get("__character_looks__", {}) if isinstance(state, Mapping) else {}
    seen = set()
    for record in catalog.values() if isinstance(catalog, Mapping) else ():
        if not isinstance(record, Mapping):
            continue
        character = _clean_text(record.get("character"))
        looks = record.get("looks", {})
        for look in looks.values() if isinstance(looks, Mapping) else ():
            if not isinstance(look, Mapping):
                continue
            scenes = {_clean_text(value) for value in look.get("scenes", [])}
            if str(scene_number) not in scenes:
                continue
            look_name = _clean_text(look.get("name")) or "Look"
            identity = (character.casefold(), look_name.casefold())
            if identity in seen:
                continue
            seen.add(identity)
            makeup_hair = " / ".join(filter(None, (
                _clean_text(look.get("makeup")), _clean_text(look.get("hair"))
            )))
            rows.append({
                "Personaje": character, "Look": look_name,
                "Vestuario": _clean_text(look.get("wardrobe")),
                "Maquillaje / Peinado": makeup_hair,
                "Estado": _clean_text(look.get("character_state")),
            })
    return rows


def _vfx_rows(scene_number):
    data = _scene_department_data("breakdown_vfx_sound_data", scene_number)
    categories = (
        ("vfx", "VFX", ("VFX requerido",), "Prioridad"),
        ("sfx_practicos", "Efecto práctico", ("SFX práctico",), "Seguridad"),
        ("sonido", "Sonido", ("Elemento sonoro",), ""),
    )
    rows = []
    for key, category, element_columns, priority_column in categories:
        for row in _as_dataframe(data.get(key)).to_dict(orient="records"):
            element = _first_value(row, *element_columns)
            if element:
                rows.append({
                    "Área": category, "Elemento": element,
                    "Tipo": _first_value(row, "Tipo"),
                    "Responsable": _first_value(row, "Responsable"),
                    "Prioridad / Seguridad": _first_value(row, priority_column),
                })
    return rows


def _extras_rows(scene_number):
    data = _scene_department_data("breakdown_extras_data", scene_number)
    categories = (
        ("extras_atmosfera", "Ambiente", ("Tipo extra",), ("Acción",)),
        ("extras_dialogo", "Diálogo", ("Personaje / Tipo",), ("Línea o función",)),
        ("vehiculos_pelicula", "Vehículo", ("Vehículo",), ("Acción escena",)),
        ("animales", "Animal", ("Animal",), ("Handler requerido", "Nombre del Handler")),
    )
    rows = []
    for key, category, columns, action_columns in categories:
        for row in _as_dataframe(data.get(key)).to_dict(orient="records"):
            element = _first_value(row, *columns)
            if element:
                rows.append({
                    "Categoría": category,
                    "Elemento": element,
                    "Cantidad": _first_value(row, "Cantidad", fallback="1" if key == "vehiculos_pelicula" else ""),
                    "Acción / Función": " / ".join(filter(None, (
                        _clean_text(row.get(column)) for column in action_columns
                    ))),
                    "Responsable": _first_value(row, "Responsable"),
                })
    return rows


def _production_rows(scene_number):
    data = _scene_department_data("breakdown_production_notes_data", scene_number)
    notes = _as_dataframe(data.get("notas_produccion"))
    rows = []
    for row in notes.to_dict(orient="records"):
        department = _first_value(row, "Departamento")
        instruction = _first_value(row, "Instrucción")
        if department or instruction:
            rows.append({
                "Departamento": department, "Instrucción": instruction,
                "Observaciones": _first_value(row, "Observaciones"),
            })
    return rows


def _general_observations(details, scene_number):
    observations = []
    scene_note = _first_value(details, "Notas de escena", "Notas", "Observaciones")
    if scene_note:
        observations.append(scene_note)
    data = _scene_department_data("breakdown_production_notes_data", scene_number)
    notes = _as_dataframe(data.get("notas_produccion"))
    if "Observaciones" in notes.columns:
        observations.extend(
            value for value in notes["Observaciones"].map(_clean_text) if value
        )
    legacy = _clean_text(data.get("notas_generales"))
    if legacy:
        observations.append(legacy)
    return " · ".join(dict.fromkeys(observations)) or "Sin observaciones."


def _allocate_row_limits(sections, budget=25):
    maximums = {
        "cast": 7,
        "props": 8,
        "wardrobe": 5,
        "extras": 6,
        "notes": 5,
        "vfx": 4,
    }
    priority = ("cast", "props", "wardrobe", "extras", "notes", "vfx")
    distribution_order = (
        "cast", "props", "cast", "props",
        "wardrobe", "extras", "wardrobe", "extras",
        "notes", "vfx",
    )
    limits = {key: min(1, len(sections[key]["rows"])) for key in priority}
    remaining = max(0, budget - sum(limits.values()))
    while remaining:
        distributed = False
        for key in distribution_order:
            available = min(len(sections[key]["rows"]), maximums[key])
            if limits[key] < available:
                limits[key] += 1
                remaining -= 1
                distributed = True
                if not remaining:
                    break
        if not distributed:
            break
    return limits


def _compact_text(value, limit=46):
    value = _clean_text(value)
    return value if len(value) <= limit else f"{value[:limit - 1].rstrip()}…"


def _html_table(columns, rows, limit, overflow_label, empty_message):
    if not rows:
        return (
            '<div style="color:#6b7280;font-style:italic;padding-top:4px">'
            f"{escape(empty_message)}</div>"
        )
    weights = column_weights(columns, rows)
    weight_total = sum(weights) or 1
    colgroup = "".join(
        f'<col style="width:{weight / weight_total * 100:.2f}%">' for weight in weights
    )
    headers = "".join(
        f'<th style="text-align:left;color:#fff;background:#09090b;font-size:7px;'
        f'height:{GRID.table_header_height}px;padding:{GRID.table_padding_y}px '
        f'{GRID.table_padding_x}px;border:1px solid #d1d5db;box-sizing:border-box">'
        f'{escape(column)}</th>'
        for column in columns
    )
    body = "".join(
        "<tr>" + "".join(
            f'<td style="padding:{GRID.table_padding_y}px {GRID.table_padding_x}px;'
            f'border:1px solid #e5e7eb;'
            f'vertical-align:top;white-space:normal;overflow-wrap:anywhere">'
            f'{escape(_clean_text(row.get(column)))}</td>'
            for column in columns
        ) + "</tr>"
        for row in rows[:limit]
    )
    hidden = len(rows) - limit
    remainder = (
        f'<div style="font-size:8px;font-weight:700;color:#4b5563;padding:2px 4px">'
        f'+{hidden} {escape(overflow_label)} más</div>'
        if hidden > 0 else ""
    )
    return (
        '<table style="width:100%;border-collapse:collapse;table-layout:fixed;'
        f'font-size:8.5px"><colgroup>{colgroup}</colgroup><thead><tr>{headers}</tr></thead><tbody>{body}</tbody>'
        f'</table>{remainder}'
    )


def _department_section(title, section, limit):
    rows = section["rows"]
    return (
        f'<section style="{html_box_style()}">'
        f'{html_section_title(title, len(rows))}'
        f'{_html_table(section["columns"], rows, limit, section["overflow"], section["empty"])}</section>'
    )


def _scene_items(state_key):
    state = st.session_state.get(state_key, {})
    if not isinstance(state, Mapping):
        return ()
    return tuple(
        (str(scene_number), value)
        for scene_number, value in state.items()
        if not str(scene_number).startswith("__") and isinstance(value, Mapping)
    )


def _joined_values(*values):
    return " / ".join(dict.fromkeys(
        value for value in (_clean_text(item) for item in values) if value
    ))


def _scene_list(values):
    return ", ".join(sorted(set(values), key=_scene_sort_key))


def _quantity_summary(values):
    cleaned = list(dict.fromkeys(_clean_text(value) for value in values if _clean_text(value)))
    if not cleaned:
        return ""
    numeric = []
    for value in values:
        try:
            numeric.append(float(_clean_text(value).replace(",", ".")))
        except ValueError:
            return _joined_values(*cleaned)
    total = sum(numeric)
    return str(int(total)) if total.is_integer() else f"{total:g}"


def _cast_document_rows(scenes):
    master = st.session_state.get("cast_master_df", pd.DataFrame())
    master = _as_dataframe(master)
    records = {}
    for row in master.to_dict(orient="records"):
        character = _first_value(row, "Personaje")
        if character:
            records[character.casefold()] = {
                "Personaje": character,
                "Actor / Actriz": _first_value(row, "Actor/Actriz"),
                "Tipo": _first_value(row, "Tipo"),
                "Estado": _first_value(row, "Estado casting"),
                "Doble": _first_value(row, "Doble requerido"),
                "Escenas": set(),
                "Contacto": _joined_values(row.get("Teléfono"), row.get("Email")),
                "Notas": _first_value(row, "Observaciones"),
            }
    for scene in scenes:
        scene_number = _scene_number(scene)
        for character in _cast_labels(scene, scene_number):
            identity = character.casefold()
            records.setdefault(identity, {
                "Personaje": character, "Actor / Actriz": "", "Tipo": "",
                "Estado": "", "Doble": "", "Escenas": set(),
                "Contacto": "", "Notas": "",
            })["Escenas"].add(scene_number)
    return [{**row, "Escenas": _scene_list(row["Escenas"])} for row in records.values()]


def _props_document_rows():
    configs = (
        ("props_mano", "Mano", ("Prop",), ("Personaje que lo usa",), ("Continuidad",)),
        ("set_dressing", "Set", ("Elemento",), ("Área / Set",), ()),
        ("props_especiales", "Especial", ("Prop especial",), ("Personaje asociado",), ("FX asociado",)),
        ("utileria_riesgo", "Riesgo", ("Elemento",), (), ("Tipo", "Seguridad requerida")),
    )
    grouped = {}
    for scene_number, data in _scene_items("breakdown_props_data"):
        for key, category, names, areas, continuity in configs:
            for row in _as_dataframe(data.get(key)).to_dict(orient="records"):
                element = _first_value(row, *names)
                if not element:
                    continue
                identity = (category.casefold(), element.casefold())
                entry = grouped.setdefault(identity, {
                    "Categoría": category, "Elemento": element, "Cantidad": [],
                    "Personaje / Área": [], "Continuidad / Riesgo": [],
                    "Responsable": [], "Escenas": set(),
                })
                for target, value in (
                    ("Cantidad", _first_value(row, "Cantidad")),
                    ("Personaje / Área", _first_value(row, *areas)),
                    ("Continuidad / Riesgo", _joined_values(*(row.get(k) for k in continuity))),
                    ("Responsable", _first_value(row, "Responsable")),
                ):
                    if value and (target == "Cantidad" or value not in entry[target]):
                        entry[target].append(value)
                entry["Escenas"].add(scene_number)
    return [{
        **entry,
        "Cantidad": _quantity_summary(entry["Cantidad"]),
        "Personaje / Área": _joined_values(*entry["Personaje / Área"]),
        "Continuidad / Riesgo": _joined_values(*entry["Continuidad / Riesgo"]),
        "Responsable": _joined_values(*entry["Responsable"]),
        "Escenas": _scene_list(entry["Escenas"]),
    } for entry in grouped.values()]


def _wardrobe_document_rows():
    state = st.session_state.get("breakdown_wardrobe_makeup_data", {})
    catalog = state.get("__character_looks__", {}) if isinstance(state, Mapping) else {}
    rows = []
    for record in catalog.values() if isinstance(catalog, Mapping) else ():
        if not isinstance(record, Mapping):
            continue
        character = _clean_text(record.get("character"))
        looks = record.get("looks", {})
        for look in looks.values() if isinstance(looks, Mapping) else ():
            if isinstance(look, Mapping):
                rows.append({
                    "Personaje": character,
                    "Look": _clean_text(look.get("name")),
                    "Escenas": _scene_list(_clean_text(scene) for scene in look.get("scenes", []) if _clean_text(scene)),
                    "Vestuario": _clean_text(look.get("wardrobe")),
                    "Maquillaje": _clean_text(look.get("makeup")),
                    "Peinado": _clean_text(look.get("hair")),
                    "Accesorios / Calzado": _joined_values(look.get("accessories"), look.get("footwear")),
                    "Continuidad": _clean_text(look.get("character_state")),
                    "Notas": _clean_text(look.get("notes")),
                })
    return rows


def _vfx_document_rows():
    configs = (
        ("vfx", "VFX", "VFX requerido", "Prioridad", ""),
        ("sfx_practicos", "Efecto práctico", "SFX práctico", "", "Seguridad"),
        ("sonido", "Sonido", "Elemento sonoro", "", ""),
    )
    rows = []
    for scene_number, data in _scene_items("breakdown_vfx_sound_data"):
        for key, area, element_key, priority_key, safety_key in configs:
            for row in _as_dataframe(data.get(key)).to_dict(orient="records"):
                element = _first_value(row, element_key)
                if element:
                    rows.append({
                        "Área": area, "Elemento": element,
                        "Tipo": _first_value(row, "Tipo"),
                        "Responsable": _first_value(row, "Responsable"),
                        "Prioridad": _first_value(row, priority_key),
                        "Seguridad": _first_value(row, safety_key),
                        "Escenas": scene_number,
                        "Notas": _joined_values(row.get("Descripción"), row.get("Notas")),
                    })
    return rows


def _extras_document_rows():
    configs = (
        ("extras_atmosfera", "Ambiente", "Tipo extra", "Acción", ""),
        ("extras_dialogo", "Diálogo", "Personaje / Tipo", "Línea o función", ""),
        ("vehiculos_pelicula", "Vehículo", "Vehículo", "Acción escena", ""),
        ("animales", "Animal", "Animal", "", "Nombre del Handler"),
    )
    rows = []
    for scene_number, data in _scene_items("breakdown_extras_data"):
        for key, category, element_key, action_key, handler_key in configs:
            for row in _as_dataframe(data.get(key)).to_dict(orient="records"):
                element = _first_value(row, element_key)
                if element:
                    rows.append({
                        "Categoría": category, "Elemento": element,
                        "Cantidad": _first_value(row, "Cantidad", fallback="1" if key == "vehiculos_pelicula" else ""),
                        "Escenas": scene_number,
                        "Responsable": _first_value(row, "Responsable"),
                        "Acción": _first_value(row, action_key),
                        "Handler": _joined_values(row.get("Handler requerido"), row.get(handler_key)),
                        "Notas": _first_value(row, "Notas"),
                    })
    return rows


def _production_document_rows():
    rows = []
    for scene_number, data in _scene_items("breakdown_production_notes_data"):
        for row in _as_dataframe(data.get("notas_produccion")).to_dict(orient="records"):
            if _first_value(row, "Departamento", "Instrucción", "Instruccion", "Instrucciones", "Observaciones"):
                rows.append({
                    "Departamento": _first_value(row, "Departamento"),
                    "Responsable": _first_value(row, "Responsable"),
                    "Instrucción": _first_value(
                        row, "Instrucción", "Instruccion", "Instrucciones", "instruction"
                    ),
                    "Observaciones": _first_value(row, "Observaciones", "Observación", "Observacion"),
                    "Permisos": _first_value(row, "Permisos", "Permiso"),
                    "Riesgos": _first_value(row, "Riesgos", "Riesgo"),
                    "Escenas": scene_number,
                    "Estado": _first_value(row, "Estado"),
                })
    return sorted(rows, key=lambda row: (row["Departamento"].casefold(), _scene_sort_key(row["Escenas"])))


def _render_document_selector():
    st.markdown("**DOCUMENTO**")
    selected = st.selectbox(
        "Documento",
        _DOCUMENT_OPTIONS,
        label_visibility="collapsed",
    )
    st.session_state.export_selected_document = selected
    set_document(selected)
    register_workspace_provider("export:document", lambda: {"document": selected})
    return selected


def _render_letter_preview(scene):
    details = _scene_details(scene)
    scene_color = DOCUMENTS_BY_LABEL["Hoja de Breakdown"].scene_color(details)
    scene_number = _scene_number(details)
    project = _project_information()
    project_name = _first_value(project, "nombre", fallback="Proyecto sin nombre")
    script_version = _first_value(project, "version_guion", "versión_guion", "version")
    generated_at = datetime.now()
    generation_date = generated_at.strftime("%d/%m/%Y")
    generation_time = generated_at.strftime("%H:%M")
    description = _first_value(
        details, "Descripción", "Descripcion", "Sinopsis", fallback="Sin descripción registrada."
    )
    info = [
        ("Proyecto", project_name),
        ("Escena", scene_number or "—"),
        ("INT / EXT", _first_value(details, "INT/EXT", fallback="—")),
        ("Tiempo", _first_value(details, "Tiempo", fallback="—")),
        ("Locación", _first_value(details, "Locación", "Locacion", fallback="—")),
        ("Set", _first_value(details, "Set", "Área / Set", "Area / Set", fallback="—")),
        ("Página", _first_value(details, "Página", "Pagina", fallback="—")),
        ("Octavos", _first_value(details, "Octavos", "Octavos finales", fallback="—")),
        ("Orden", _first_value(details, "Orden", "Orden de rodaje", fallback="—")),
        ("Estado", _first_value(details, "Estado breakdown", fallback="Pendiente")),
    ]
    if script_version:
        info.append(("Versión", script_version))
    info_html = "".join(
        f'<div style="min-width:0"><b style="color:#6b7280;font-size:7px">'
        f'{escape(label.upper())}</b><br><span style="font-size:8px;white-space:nowrap;'
        f'overflow:hidden;text-overflow:ellipsis;display:block">{escape(value)}</span></div>'
        for label, value in info
    )

    sections = {
        "cast": {
            "title": "Cast", "columns": ["Personaje", "Actor / Actriz", "Tipo", "Estado", "Doble"],
            "rows": _cast_rows(details, scene_number), "overflow": "personajes",
            "empty": "Sin personajes registrados.",
        },
        "props": {
            "title": "Props", "columns": ["Categoría", "Elemento", "Cantidad", "Personaje / Área", "Continuidad / FX / Riesgo", "Responsable"],
            "rows": _props_rows(scene_number), "overflow": "props",
            "empty": "Sin utilería registrada.",
        },
        "wardrobe": {
            "title": "Vestuario", "columns": ["Personaje", "Look", "Vestuario", "Maquillaje / Peinado", "Estado"],
            "rows": _wardrobe_rows(scene_number), "overflow": "Looks",
            "empty": "Sin Looks asignados.",
        },
        "vfx": {
            "title": "VFX / Efectos Prácticos / Sonido", "columns": ["Área", "Elemento", "Tipo", "Responsable", "Prioridad / Seguridad"],
            "rows": _vfx_rows(scene_number), "overflow": "elementos",
            "empty": "Sin efectos o requerimientos registrados.",
        },
        "extras": {
            "title": "Extras / Vehículos / Animales",
            "columns": ["Categoría", "Elemento", "Cantidad", "Acción / Función", "Responsable"],
            "rows": _extras_rows(scene_number), "overflow": "extras",
            "empty": "Sin extras, vehículos o animales registrados.",
        },
        "notes": {
            "title": "Notas de Producción", "columns": ["Departamento", "Instrucción", "Observaciones"],
            "rows": _production_rows(scene_number), "overflow": "notas",
            "empty": "Sin notas de producción.",
        },
    }
    limits = _allocate_row_limits(sections)
    visual_order = ("cast", "props", "wardrobe", "vfx", "extras", "notes")
    sections_html = "".join(
        _department_section(
            sections[key]["title"], sections[key], limits[key]
        )
        for key in visual_order
    )
    observations = _general_observations(details, scene_number)
    header_fields = (
        ("Proyecto", project_name),
        ("Versión de guion", script_version or "—"),
        ("Escena", scene_number or "—"),
        ("Fecha", generation_date),
        ("Hora", generation_time),
        ("Página", _first_value(details, "Página", "Pagina", fallback="—")),
    )
    shared_header = html_header("HOJA DE BREAKDOWN", header_fields[:5])
    scene_accent = html_scene_accent(scene_color.hex, scene_color.label)
    shared_footer = html_footer(generation_date)
    st.markdown(
        f"""
        <div style="background:#e5e7eb;padding:18px;border-radius:12px;overflow:auto;zoom:{_preview_scale():.2f}">
          <article style="{html_page_style()}">
            {shared_header}
            {scene_accent}
            <div style="display:grid;grid-template-columns:repeat(10,minmax(0,1fr));gap:4px;
              border-bottom:1px solid #d1d5db;padding-bottom:4px;margin-bottom:4px;flex:none">{info_html}</div>
            <section style="margin-bottom:5px;flex:none;max-height:34px;overflow:hidden">
              <b style="font-size:8px">DESCRIPCIÓN</b>
              <div style="margin-top:2px;font-size:8px">{escape(description)}</div></section>
            <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
              gap:{GRID.column_gap}px;align-content:start;min-height:0;overflow:hidden;flex:0 1 auto">
              {sections_html}
            </div>
            <section style="border-top:1px solid #9ca3af;margin-top:5px;padding-top:4px;
              flex:1 1 auto;min-height:22px;overflow:hidden">
              <b style="font-size:8px">OBSERVACIONES GENERALES</b>
              <div style="font-size:8px;margin-top:2px">{escape(observations)}</div>
            </section>
            {shared_footer}
          </article>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _department_document_config(document, scenes):
    configs = {
        "Documento de Cast": (
            "DOCUMENTO DE CAST", "Catálogo maestro de personajes y talento",
            ["Personaje", "Actor / Actriz", "Tipo", "Estado", "Doble", "Escenas", "Contacto", "Notas"],
            _cast_document_rows(scenes), "Sin personajes registrados.", "personajes",
        ),
        "Documento de Props y Utilería": (
            "DOCUMENTO DE PROPS Y UTILERÍA", "Necesidades consolidadas de utilería por escena",
            ["Categoría", "Elemento", "Cantidad", "Personaje / Área", "Continuidad / Riesgo", "Responsable", "Escenas"],
            _props_document_rows(), "Sin utilería registrada.", "elementos",
        ),
        "Documento de Vestuario y Maquillaje": (
            "DOCUMENTO DE VESTUARIO Y MAQUILLAJE", "Looks organizados por personaje",
            ["Personaje", "Look", "Escenas", "Vestuario", "Maquillaje", "Peinado", "Accesorios / Calzado", "Continuidad", "Notas"],
            _wardrobe_document_rows(), "Sin Looks registrados.", "Looks",
        ),
        "Documento de VFX / Efectos Prácticos / Sonido": (
            "DOCUMENTO DE VFX / EFECTOS PRÁCTICOS / SONIDO", "Requerimientos visuales, prácticos y sonoros",
            ["Área", "Elemento", "Tipo", "Responsable", "Prioridad", "Seguridad", "Escenas", "Notas"],
            _vfx_document_rows(), "Sin efectos o requerimientos registrados.", "elementos",
        ),
        "Documento de Extras, Vehículos y Animales": (
            "DOCUMENTO DE EXTRAS, VEHÍCULOS Y ANIMALES", "Necesidades consolidadas frente a cámara",
            ["Categoría", "Elemento", "Cantidad", "Escenas", "Responsable", "Acción", "Handler", "Notas"],
            _extras_document_rows(), "Sin extras, vehículos o animales registrados.", "elementos",
        ),
        "Documento de Producción": (
            "DOCUMENTO DE PRODUCCIÓN", "Instrucciones agrupadas por departamento",
            ["Departamento", "Responsable", "Instrucción", "Observaciones", "Permisos", "Riesgos", "Escenas", "Estado"],
            _production_document_rows(), "Sin notas de producción.", "notas",
        ),
    }
    title, subtitle, columns, rows, empty_message, overflow_label = configs[document]
    scene_numbers = {_scene_number(scene) for scene in scenes}
    rows = [row for row in rows if _row_belongs_to_scenes(row, scene_numbers)]
    return title, subtitle, columns, rows, empty_message, overflow_label


def _render_department_document(document, scenes):
    title, subtitle, columns, rows, empty_message, overflow_label = (
        _department_document_config(document, scenes)
    )
    definition = DOCUMENTS_BY_LABEL[document]
    document_key = _document_key(definition)
    selected_columns = [
        field for field in definition.fields
        if st.session_state.get(f"export_{document_key}_field_{field}", True)
    ]
    visible_columns = [column for column in selected_columns if column in columns]
    if visible_columns:
        columns = visible_columns
    project = _project_information()
    project_name = _first_value(project, "nombre", fallback="Proyecto sin nombre")
    script_version = _first_value(project, "version_guion", "versión_guion", "version")
    generated_at = datetime.now()
    generation_date = generated_at.strftime("%d/%m/%Y")
    generation_time = generated_at.strftime("%H:%M")
    header_fields = (
        ("Proyecto", project_name),
        ("Versión de guion", script_version or "—"),
        ("Fecha", generation_date),
        ("Hora", generation_time),
        ("Registros", str(len(rows))),
    )
    shared_header = html_header(title, header_fields[:4])
    shared_footer = html_footer(generation_date)
    table = _html_table(columns, rows, 14, overflow_label, empty_message)
    st.markdown(
        f"""
        <div style="background:#e5e7eb;padding:18px;border-radius:12px;overflow:auto;zoom:{_preview_scale():.2f}">
          <article style="{html_page_style()}">
            {shared_header}
            <section style="flex:none;margin-bottom:12px">
              <div style="font-size:13px;font-weight:900">{escape(title.title())}</div>
              <div style="font-size:8px;color:#71717a;margin-top:2px">{escape(subtitle)} · {len(rows)} registros</div>
            </section>
            <section style="flex:1 1 auto;min-height:0;overflow:hidden">{table}</section>
            {shared_footer}
          </article>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _preview_scale():
    return float(st.session_state.get("export_preview_scale", 1.0))


def _set_preview_scale(value):
    st.session_state.export_preview_scale = max(0.5, min(1.6, round(value, 2)))


def _render_zoom_controls():
    left, value, right, fit = st.columns([1, 1, 1, 2])
    if left.button("Zoom −", key="export_zoom_out", use_container_width=True):
        _set_preview_scale(_preview_scale() - 0.1)
        st.rerun()
    value.markdown(f"**{round(_preview_scale() * 100)} %**")
    if right.button("Zoom +", key="export_zoom_in", use_container_width=True):
        _set_preview_scale(_preview_scale() + 0.1)
        st.rerun()
    if fit.button("Ajustar a pantalla", key="export_fit", use_container_width=True):
        # Preview pages are width:100%; scale 1 is therefore the computed fit.
        _set_preview_scale(1.0)
        st.rerun()


def _render_preview(scenes, selected_scene):
    with cine_panel(
        title=_icon_label(EXPORT, "Centro de Documentos"),
        subtitle="Previsualiza, revisa y prepara los documentos oficiales de producción.",
    ):
        number = _scene_number(selected_scene)
        selected_document = _render_document_selector()
        st.divider()
        _render_preview_navigation(scenes, number)
        if selected_document == "Hoja de Breakdown":
            _render_letter_preview(selected_scene)
        else:
            _render_department_document(selected_document, [selected_scene])
        _render_zoom_controls()


def _application_generator(name):
    """Resolve CinePlan's existing generators without duplicating their logic."""
    generator = getattr(sys.modules.get("__main__"), name, None)
    if not callable(generator):
        raise RuntimeError("El generador de documentos no está disponible.")
    return generator


def _scene_export_row(scene):
    number = _scene_number(scene)
    details = _scene_details(scene)
    return {
        "Escena": number,
        "Encabezado": _scene_heading(scene),
        "INT / EXT": _first_value(details, "INT/EXT"),
        "Tiempo": _first_value(details, "Tiempo"),
        "Locación": _first_value(details, "Locación", "Locacion"),
        "Octavos": _first_value(details, "Octavos", "Octavos finales"),
        "Reparto": len(_cast_rows(scene, number)),
        "Utilería": len(_props_rows(number)),
        "Vestuario": len(_wardrobe_rows(number)),
        "VFX / SFX / Sonido": len(_vfx_rows(number)),
        "Extras / Vehículos": len(_extras_rows(number)),
        "Notas de producción": len(_production_rows(number)),
    }


def _breakdown_document_rows(scene):
    number = _scene_number(scene)
    details = _scene_details(scene)
    rows = [{
        "Escena": number, "Sección": "Datos de escena",
        "Elemento": _scene_heading(scene),
        "Detalle": _first_value(details, "Descripción", "Descripcion", "Sinopsis"),
        "Cantidad": "", "Responsable": "",
    }]
    sections = (
        ("Reparto / Talento", _cast_rows(scene, number)),
        ("Utilería", _props_rows(number)),
        ("Vestuario / Maquillaje", _wardrobe_rows(number)),
        ("VFX / SFX / Sonido", _vfx_rows(number)),
        ("Extras / Vehículos", _extras_rows(number)),
        ("Notas de producción", _production_rows(number)),
    )
    name_keys = ("Elemento", "Personaje", "Look", "Departamento", "Instrucción", "Área")
    for section, values in sections:
        for value in values:
            element = _first_value(value, *name_keys)
            detail = " · ".join(
                f"{key}: {_clean_text(item)}" for key, item in value.items()
                if key not in name_keys and key not in {"Cantidad", "Responsable"} and _clean_text(item)
            )
            rows.append({
                "Escena": number, "Sección": section, "Elemento": element,
                "Detalle": detail, "Cantidad": _first_value(value, "Cantidad"),
                "Responsable": _first_value(value, "Responsable"),
            })
    return rows


def _document_rows_for_export(document, scenes):
    if document == "Hoja de Breakdown":
        return [row for scene in scenes for row in _breakdown_document_rows(scene)]
    return _department_document_config(document, scenes)[3]


def _row_belongs_to_scenes(row, scene_numbers):
    value = _first_value(row, "Escenas", "Escena")
    if not value:
        return True
    referenced = {part.strip() for part in value.split(",") if part.strip()}
    return bool(referenced.intersection(scene_numbers))


def _export_dataframe(document, scenes, options=None):
    dataframe = pd.DataFrame(_document_rows_for_export(document, scenes)).fillna("")
    # Presentation aliases belong to the document definition layer. They expose
    # familiar production labels without changing the stored resource schema.
    if document == "Documento de Extras, Vehículos y Animales":
        aliases = {
            "Tipo": "Categoría", "Conductor": "Handler", "Vehículo": "Elemento",
        }
        for visible, source in aliases.items():
            if source in dataframe.columns and visible not in dataframe.columns:
                dataframe[visible] = dataframe[source]
    options = options or {}
    selected_fields = options.get("fields", ())
    if selected_fields:
        columns = [column for column in selected_fields if column in dataframe.columns]
        if columns:
            dataframe = dataframe[columns]
    sort_by = options.get("sort_by")
    if sort_by in dataframe.columns:
        dataframe = dataframe.sort_values(sort_by, kind="stable")
    group_by = options.get("group_by")
    if group_by in dataframe.columns and group_by != sort_by:
        dataframe = dataframe.sort_values(group_by, kind="stable")
    return dataframe.reset_index(drop=True)


def _scene_pdf(scene):
    number = _scene_number(scene)
    details = _scene_details(scene)
    sections = {
        "REPARTO / TALENTO": pd.DataFrame(_cast_rows(scene, number)),
        "UTILERÍA": pd.DataFrame(_props_rows(number)),
        "VESTUARIO / MAQUILLAJE": pd.DataFrame(_wardrobe_rows(number)),
        "VFX / SFX / SONIDO": pd.DataFrame(_vfx_rows(number)),
        "EXTRAS / VEHÍCULOS": pd.DataFrame(_extras_rows(number)),
        "NOTAS DE PRODUCCIÓN": pd.DataFrame(_production_rows(number)),
    }
    return _application_generator("generate_breakdown_pdf")(
        number, details, st.session_state.get("project_info", {}), sections=sections
    ).getvalue()


def _printable_dataframe(dataframe, empty_message="Sin registros para esta escena."):
    return dataframe if not dataframe.empty else pd.DataFrame([{"Estado": empty_message}])


def _generated_pdf(document, scene, options=None):
    if document == "Hoja de Breakdown":
        return _scene_pdf(scene)
    dataframe = _printable_dataframe(_export_dataframe(document, [scene], options))
    return _application_generator("dataframe_to_pdf")(
        dataframe, title=document, project_info=_project_information()
    ).getvalue()


def _merge_pdfs(documents):
    writer = PdfWriter()
    for document in documents:
        reader = PdfReader(BytesIO(document))
        for page in reader.pages:
            writer.add_page(page)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _metadata_dataframes(document, scenes, include, options=None):
    frames = []
    project = _project_information()
    if include.get("cover"):
        frames.append(("Portada", pd.DataFrame([{
            "Proyecto": _first_value(project, "nombre", fallback="Proyecto CinePlan"),
            "Documento": document,
            "Fecha": datetime.now().strftime("%d/%m/%Y"),
        }])))
    if include.get("summary"):
        frames.append(("Resumen", pd.DataFrame([_scene_export_row(scene) for scene in scenes])))
    if include.get("catalogs"):
        frames.append(("Catálogos", _printable_dataframe(
            _export_dataframe(document, _scene_records(), options), "Sin registros en el catálogo."
        )))
    return frames


def _editorial_front_matter(document, scenes, include):
    project = _project_information()
    project_name = _first_value(project, "nombre", fallback="Proyecto CinePlan")
    pages = []
    if include.get("cover"):
        pages.append(editorial_pdf(
            "HOJA DE BREAKDOWN" if document == "Hoja de Breakdown" else document.upper(),
            project_name,
            "Documento maestro para coordinación y desglose de producción.",
            (
                ("Director", _first_value(project, "director", fallback="—")),
                ("Productora", _first_value(project, "productora", "productor", fallback="Producción")),
                ("Versión", _first_value(project, "version_guion", "versión_guion", fallback="—")),
                ("Fecha", datetime.now().strftime("%d/%m/%Y")),
                ("Hora", datetime.now().strftime("%H:%M")),
            ),
            project=project_name,
            version=_first_value(project, "version_guion", "versión_guion", fallback="—"),
        ))
    if include.get("summary"):
        scene_rows = [_scene_export_row(scene) for scene in scenes]
        metrics = {
            "Escenas": len(scenes),
            "Reparto": sum(row["Reparto"] for row in scene_rows),
            "Utilería": sum(row["Utilería"] for row in scene_rows),
            "Vestuario": sum(row["Vestuario"] for row in scene_rows),
            "VFX / SFX / Sonido": sum(row["VFX / SFX / Sonido"] for row in scene_rows),
            "Extras / Vehículos": sum(row["Extras / Vehículos"] for row in scene_rows),
            "Notas de producción": sum(row["Notas de producción"] for row in scene_rows),
        }
        pages.append(editorial_pdf(
            "RESUMEN DEL PROYECTO", project_name,
            "Panorama ejecutivo de los recursos registrados para las escenas incluidas.",
            tuple(metrics.items()),
            project=project_name,
            version=_first_value(project, "version_guion", "versión_guion", fallback="—"),
        ))
    return pages


def _catalog_pdf_pages(generator):
    project = _project_information()
    project_name = _first_value(project, "nombre", fallback="Proyecto CinePlan")
    version = _first_value(project, "version_guion", "versión_guion", fallback="—")
    pages = [editorial_pdf(
        "CATÁLOGOS GENERALES", project_name,
        "Índice editorial de recursos generales de producción.",
        (("Catálogos", len(DOCUMENTS_BY_LABEL) - 1), ("Fecha", datetime.now().strftime("%d/%m/%Y"))),
        project=project_name, version=version,
    )]
    for definition in DOCUMENTS_BY_LABEL.values():
        if definition.label == "Hoja de Breakdown":
            continue
        pages.append(editorial_pdf(
            definition.filename_title.upper(), project_name, definition.description,
            (("Documento", definition.filename_title), ("Tipo", "Catálogo general")),
            color=definition.color, project=project_name, version=version,
        ))
        dataframe = _printable_dataframe(
            _export_dataframe(definition.label, _scene_records()),
            "Sin registros en este catálogo.",
        )
        pages.append(generator(
            dataframe, title=definition.filename_title, project_info=project
        ).getvalue())
    return pages


def _scene_separator_pdf(scene):
    details = _scene_details(scene)
    number = _scene_number(scene)
    heading = _scene_heading(scene)
    scene_type = _first_value(details, "INT/EXT", fallback="—")
    time = _first_value(details, "Tiempo", fallback="—")
    eighths = _first_value(details, "Octavos", "Octavos finales", fallback="—")
    strip_color = DOCUMENTS_BY_LABEL["Hoja de Breakdown"].scene_color(details)
    return editorial_pdf(
        f"ESCENA {number}", heading,
        "Separador de escena para carpeta de producción.",
        (("INT / EXT", scene_type), ("Tiempo", time), ("Octavos", eighths)),
        color=strip_color.hex, project=_first_value(_project_information(), "nombre", fallback="Proyecto CinePlan"),
        version=_first_value(_project_information(), "version_guion", "versión_guion", fallback="—"),
        full_color_bar=True,
    )


def _export_pdf(document, scenes, include, options=None):
    generator = _application_generator("dataframe_to_pdf")
    pages = _editorial_front_matter(document, scenes, include)
    if include.get("catalogs"):
        pages.extend(_catalog_pdf_pages(generator))
    for scene in scenes:
        if include.get("separators"):
            pages.append(_scene_separator_pdf(scene))
        pages.append(_generated_pdf(document, scene, options))
    return _merge_pdfs(pages)


def _safe_sheet_name(label, used):
    base = "".join(character for character in label if character not in "[]:*?/\\")[:31] or "Hoja"
    candidate, suffix = base, 2
    while candidate in used:
        ending = f" {suffix}"
        candidate = f"{base[:31 - len(ending)]}{ending}"
        suffix += 1
    used.add(candidate)
    return candidate


def _export_excel(document, scenes, include, options=None):
    if len(scenes) == 1 and not any(include.values()):
        dataframe = _printable_dataframe(_export_dataframe(document, scenes, options))
        return _application_generator("dataframe_to_excel")(dataframe).getvalue()
    output = BytesIO()
    used = set()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for title, frame in _metadata_dataframes(document, scenes, include, options):
            sheet_name = _safe_sheet_name(title, used)
            frame.to_excel(writer, index=False, sheet_name=sheet_name)
            format_excel_worksheet(writer.sheets[sheet_name])
        for scene in scenes:
            frame = _printable_dataframe(_export_dataframe(document, [scene], options))
            sheet_name = _safe_sheet_name(f"Escena {_scene_number(scene)}", used)
            frame.to_excel(
                writer, index=False,
                sheet_name=sheet_name,
            )
            format_excel_worksheet(writer.sheets[sheet_name])
    return output.getvalue()


def _export_bytes(document, scenes, output_format, include=None, options=None):
    include = include or {}
    return (_export_pdf(document, scenes, include, options) if output_format == "PDF"
            else _export_excel(document, scenes, include, options))


def _cached_export_bytes(document, scenes, output_format, include, options=None):
    options = options or {}
    signature_rows = [
        _export_dataframe(document, [scene], options).to_json(orient="records", force_ascii=False)
        for scene in scenes
    ]
    catalog_signature = (
        _export_dataframe(document, _scene_records(), options).to_json(orient="records", force_ascii=False)
        if include.get("catalogs") else ""
    )
    signature = repr((document, output_format, tuple(_scene_number(scene) for scene in scenes),
                      tuple(sorted(include.items())), tuple(signature_rows),
                      _project_information(), catalog_signature, repr(options)))
    cache = st.session_state.get("document_export_cache", {})
    if cache.get("signature") != signature:
        cache = {"signature": signature,
                 "data": _export_bytes(document, scenes, output_format, include, options)}
        st.session_state.document_export_cache = cache
    return cache["data"]


def _document_key(definition):
    return definition.filename_title.casefold().replace(" ", "_").replace(",", "")


def _render_export_options(scenes, selected_number):
    with cine_panel(
        title=_icon_label(EXPORT, "Opciones de exportación"),
        subtitle="Configura el contenido del documento antes de exportar.",
    ):
        document = st.session_state.get("export_selected_document", _DOCUMENT_OPTIONS[0])
        definition = DOCUMENTS_BY_LABEL[document]
        document_key = _document_key(definition)
        export_mode = "Proyecto completo"
        selected_numbers = []
        if definition.supports_scope:
            st.markdown("**EXPORTAR**")
            export_mode = st.radio(
                "Alcance", _MODE_OPTIONS, key="export_options_mode",
                label_visibility="collapsed",
            )
            if export_mode == "Escenas seleccionadas":
                selected_numbers = st.multiselect(
                    "Escenas incluidas",
                    [_scene_number(scene) for scene in scenes],
                    key="export_selected_scenes",
                    format_func=lambda number: f"Escena {number}",
                )
        st.markdown("**FORMATO**")
        output_format = st.radio(
            "Formato", ["PDF", "Excel"], key="export_format",
            label_visibility="collapsed",
        )
        include = {}
        export_options = {}
        if definition.supports_front_matter:
            st.markdown("**ORDEN**")
            st.selectbox("Orden", ["Número de escena"], key="export_order",
                         label_visibility="collapsed")
            st.markdown("**INCLUIR**")
            include = {
                "cover": st.checkbox("Portada", value=True, key="export_cover"),
                "summary": st.checkbox("Resumen del proyecto", value=True, key="export_project_summary"),
                "catalogs": st.checkbox("Catálogos generales", value=True, key="export_catalogs"),
                "separators": st.checkbox("Separador entre escenas", value=True, key="export_separators"),
            }
        else:
            if definition.fields:
                st.markdown("**INCLUIR**")
                selected_fields = [
                    field for field in definition.fields
                    if st.checkbox(field, value=True, key=f"export_{document_key}_field_{field}")
                ]
                export_options["fields"] = tuple(selected_fields)
            if definition.sort_options:
                st.markdown("**ORDENAR POR**")
                export_options["sort_by"] = st.radio(
                    "Ordenar por", definition.sort_options,
                    key=f"export_{document_key}_sort", label_visibility="collapsed",
                )
            if definition.group_options:
                st.markdown("**AGRUPAR POR**")
                export_options["group_by"] = st.radio(
                    "Agrupar por", definition.group_options,
                    key=f"export_{document_key}_group", label_visibility="collapsed",
                )

        if export_mode == "Escena actual":
            export_scenes = [scene for scene in scenes if _scene_number(scene) == selected_number]
            scope_label = "escena"
        elif export_mode == "Escenas seleccionadas":
            export_scenes = [scene for scene in scenes if _scene_number(scene) in selected_numbers]
            scope_label = "escenas seleccionadas"
        else:
            export_scenes = scenes
            scope_label = "proyecto completo"

        st.divider()
        disabled = not export_scenes
        export_data = None
        export_error = ""
        if not disabled:
            try:
                export_data = _cached_export_bytes(
                    document, export_scenes, output_format, include, export_options
                )
            except (RuntimeError, ValueError, TypeError, OSError) as error:
                export_error = str(error)
        extension = "pdf" if output_format == "PDF" else "xlsx"
        mime = "application/pdf" if output_format == "PDF" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        project_name = _first_value(_project_information(), "nombre", fallback="Proyecto CinePlan")
        scene_numbers = [_scene_number(scene) for scene in export_scenes]
        filename = export_filename(
            project_name, definition, export_mode, scene_numbers, extension
        )
        button_target = scope_label if definition.supports_scope else definition.filename_title
        st.download_button(
            f"Exportar {button_target} ({output_format})",
            data=export_data or b"",
            file_name=filename,
            mime=mime,
            disabled=disabled or export_data is None,
            key="export_document_download",
            icon=f":material/{PDF if output_format == 'PDF' else EXCEL}:",
            use_container_width=True,
        )
        if export_error:
            st.error(export_error)
        if st.button("Imprimir", key="print_breakdown_scene", icon=f":material/{CALLSHEET}:",
                     use_container_width=True):
            components.html("<script>window.parent.print();</script>", height=0, width=0)


def render_export_page():
    render_section_header(
        icon=EXPORT,
        title="Centro de Documentos CinePlan",
        description=(
            "Previsualiza, revisa y configura la exportación de los documentos "
            "oficiales de producción."
        ),
    )

    scenes = _scene_records()
    if not scenes:
        st.warning("No hay escenas disponibles para generar la vista previa.")
        return

    _prepare_mode_state()
    scene_numbers = [_scene_number(scene) for scene in scenes]
    selected_number = st.session_state.get(_SELECTED_SCENE_KEY)
    if selected_number not in scene_numbers:
        selected_number = scene_numbers[0]
        st.session_state[_SELECTED_SCENE_KEY] = selected_number
    selected_scene = scenes[scene_numbers.index(selected_number)]

    left_column, center_column, right_column = st.columns([1, 3, 1], gap="medium")
    with left_column:
        _render_summary(scenes)
        _render_scene_navigation(scenes, selected_number)
    with center_column:
        _render_preview(scenes, selected_scene)
    with right_column:
        _render_export_options(scenes, selected_number)
