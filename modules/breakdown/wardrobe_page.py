from collections.abc import Mapping
from uuid import uuid4

import pandas as pd
import streamlit as st
from project.workspace_runtime import current_character, current_submodule, register_workspace_provider, set_character

from components.header import render_section_header
from components.icons import (
    ADD,
    ANALYTICS,
    CHARACTER,
    DELETE,
    DESCRIPTION,
    NOTE,
    SAVE,
    SCENE,
    STATUS,
    WARDROBE,
)
from components.panel import cine_panel


_MASTER_CATALOG_KEY = "__character_looks__"

_LOOK_FIELDS = (
    {
        "key": "wardrobe",
        "title": "Vestuario",
        "icon": WARDROBE,
        "description": (
            "Describe toda la ropa utilizada por el personaje en este Look. "
            "Ejemplos: chaqueta, camisa, jeans, cinturón o bufanda."
        ),
    },
    {
        "key": "makeup",
        "title": "Maquillaje",
        "icon": DESCRIPTION,
        "description": (
            "Detalla el maquillaje requerido y su acabado visual. "
            "Ejemplos: maquillaje natural, envejecimiento, heridas o sangre."
        ),
    },
    {
        "key": "hair",
        "title": "Cabello",
        "icon": DESCRIPTION,
        "description": (
            "Describe el peinado y las condiciones del cabello. "
            "Ejemplos: recogido, mojado, despeinado, peluca o extensiones."
        ),
    },
    {
        "key": "accessories",
        "title": "Accesorios",
        "icon": WARDROBE,
        "description": (
            "Registra los complementos visibles que forman parte del Look. "
            "Ejemplos: joyería, sombrero, mochila, lentes o reloj."
        ),
    },
    {
        "key": "footwear",
        "title": "Calzado",
        "icon": WARDROBE,
        "description": (
            "Describe el calzado utilizado y cualquier requisito especial. "
            "Ejemplos: zapatos, botas, tenis, tacones o calzado de seguridad."
        ),
    },
    {
        "key": "character_state",
        "title": "Estado del personaje / Continuidad",
        "icon": STATUS,
        "description": (
            "Define el estado físico que debe mantenerse para continuidad. "
            "Ejemplos: limpio, mojado, con lodo, sangre, heridas o vendajes."
        ),
    },
    {
        "key": "notes",
        "title": "Notas generales",
        "icon": NOTE,
        "description": (
            "Agrega referencias, instrucciones o consideraciones generales "
            "necesarias para reproducir correctamente este Look."
        ),
    },
)


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


def _character_identity(character_id, character_name):
    clean_id = _clean_text(character_id)

    if clean_id:
        return f"id:{clean_id}"

    return f"name:{_clean_text(character_name).casefold()}"


def _new_look(look_number):
    look_id = uuid4().hex
    return look_id, {
        "look_id": look_id,
        "name": f"Look {look_number}",
        "wardrobe": "",
        "makeup": "",
        "hair": "",
        "accessories": "",
        "footwear": "",
        "character_state": "",
        "notes": "",
        "scenes": [],
    }


def _normalize_look(look_id, value, fallback_number):
    look = dict(value) if isinstance(value, Mapping) else {}
    normalized = {
        "look_id": _clean_text(look.get("look_id", look_id)) or look_id,
        "name": _clean_text(look.get("name", "")) or f"Look {fallback_number}",
        "wardrobe": _clean_text(look.get("wardrobe", "")),
        "makeup": _clean_text(look.get("makeup", "")),
        "hair": _clean_text(look.get("hair", "")),
        "accessories": _clean_text(look.get("accessories", "")),
        "footwear": _clean_text(look.get("footwear", "")),
        "character_state": _clean_text(look.get("character_state", "")),
        "notes": _clean_text(look.get("notes", "")),
        "scenes": [],
    }

    scenes = look.get("scenes", [])

    if isinstance(scenes, (list, tuple, set)):
        normalized["scenes"] = list(dict.fromkeys(
            _clean_text(scene)
            for scene in scenes
            if _clean_text(scene)
        ))

    return normalized


def _get_wardrobe_state():
    state = st.session_state.get("breakdown_wardrobe_makeup_data", {})

    if not isinstance(state, Mapping):
        state = {}

    return dict(state)


def _find_character_record(catalog, character_id, character_name):
    identity = _character_identity(character_id, character_name)

    if identity in catalog and isinstance(catalog[identity], Mapping):
        return identity, dict(catalog[identity])

    normalized_name = _clean_text(character_name).casefold()

    for stored_identity, record in catalog.items():
        if (
            isinstance(record, Mapping)
            and _clean_text(record.get("character", "")).casefold()
            == normalized_name
        ):
            return stored_identity, dict(record)

    return identity, None


def _synchronize_character_catalog():
    characters_df = st.session_state.get("characters_df", pd.DataFrame())
    wardrobe_state = _get_wardrobe_state()
    stored_catalog = wardrobe_state.get(_MASTER_CATALOG_KEY, {})

    if not isinstance(stored_catalog, Mapping):
        stored_catalog = {}

    synchronized_catalog = {}
    seen_names = set()

    if characters_df is not None and not characters_df.empty:
        for _, row in characters_df.iterrows():
            character_name = _clean_text(row.get("Personaje", ""))
            normalized_name = character_name.casefold()

            if not character_name or normalized_name in seen_names:
                continue

            seen_names.add(normalized_name)
            character_id = row.get("ID", "")
            identity = _character_identity(character_id, character_name)
            _, existing_record = _find_character_record(
                stored_catalog,
                character_id,
                character_name
            )

            record = dict(existing_record) if existing_record else {}
            looks_value = record.get("looks", {})

            if not isinstance(looks_value, Mapping):
                looks_value = {}

            looks = {
                str(look_id): _normalize_look(
                    str(look_id),
                    look,
                    position
                )
                for position, (look_id, look) in enumerate(
                    looks_value.items(),
                    start=1
                )
            }

            if not looks:
                look_id, look = _new_look(1)
                looks[look_id] = look

            synchronized_catalog[identity] = {
                "character_id": character_id,
                "character": character_name,
                "looks": looks,
            }

    wardrobe_state[_MASTER_CATALOG_KEY] = synchronized_catalog
    st.session_state.breakdown_wardrobe_makeup_data = wardrobe_state
    return synchronized_catalog


def _render_character_selector(catalog):
    character_keys = list(catalog.keys())
    restored_character = current_character()
    default_index = next(
        (index for index, key in enumerate(character_keys)
         if str(catalog[key].get("character", "")) == restored_character),
        0,
    )

    with cine_panel(
        title=_icon_label(CHARACTER, "Personaje actual"),
        subtitle="Selecciona el personaje cuyo catálogo visual deseas administrar.",
    ):
        selected = st.selectbox(
            "Seleccionar personaje",
            character_keys,
            index=default_index,
            format_func=lambda key: catalog[key]["character"],
            key="wardrobe_character_selector"
        )
        if current_submodule() == "Vestuario / Maquillaje":
            character = catalog[selected]["character"]
            set_character(character)
            register_workspace_provider("wardrobe:character", lambda: {"character": character})
        return selected


def _delete_look(character_key, look_id):
    wardrobe_state = _get_wardrobe_state()
    looks = wardrobe_state[_MASTER_CATALOG_KEY][character_key]["looks"]
    look_ids = list(looks.keys())
    deleted_index = look_ids.index(look_id)
    del looks[look_id]

    if looks:
        remaining_ids = list(looks.keys())
        next_look_id = (
            remaining_ids[deleted_index - 1]
            if deleted_index > 0
            else remaining_ids[0]
        )
    else:
        next_look_id, default_look = _new_look(1)
        looks[next_look_id] = default_look

    st.session_state.breakdown_wardrobe_makeup_data = wardrobe_state
    st.session_state[f"wardrobe_pending_look_{character_key}"] = next_look_id


@st.dialog("Eliminar Look")
def _confirm_delete_look(character_key, look_id):
    wardrobe_state = _get_wardrobe_state()
    look = wardrobe_state[_MASTER_CATALOG_KEY][character_key]["looks"][look_id]
    scenes = sorted(look.get("scenes", []), key=_scene_sort_key)

    if scenes:
        st.warning(
            "Este Look está asignado actualmente a las siguientes escenas:"
        )

        for scene in scenes:
            st.write(scene)

        st.write(
            "Eliminar este Look también eliminará sus asignaciones. "
            "¿Deseas continuar?"
        )
    else:
        st.info("Este Look no tiene escenas asignadas.")
        st.write("¿Deseas eliminarlo?")

    cancel_column, delete_column = st.columns(2)

    with cancel_column:
        cancel = st.button(
            "Cancelar",
            key=f"cancel_delete_look_{look_id}",
            use_container_width=True
        )

    with delete_column:
        confirm = st.button(
            "Eliminar Look",
            icon=f":material/{DELETE}:",
            key=f"confirm_delete_look_{look_id}",
            type="primary",
            use_container_width=True
        )

    if cancel:
        st.rerun()

    if confirm:
        _delete_look(character_key, look_id)
        st.rerun()


def _render_look_manager(character_key, character_record):
    looks = character_record["looks"]
    look_ids = list(looks.keys())
    selector_key = f"wardrobe_look_selector_{character_key}"
    pending_key = f"wardrobe_pending_look_{character_key}"
    pending_look_id = st.session_state.pop(pending_key, None)

    if pending_look_id in looks:
        st.session_state[selector_key] = pending_look_id

    with cine_panel(
        title=_icon_label(WARDROBE, "Looks del personaje"),
        subtitle="Cada Look conserva un ID estable aunque cambies su nombre visible.",
    ):
        selected_look_id = st.selectbox(
            "Seleccionar Look",
            look_ids,
            format_func=lambda look_id: looks[look_id]["name"],
            key=selector_key
        )

        add_column, delete_column = st.columns(2)

        with add_column:
            add_look = st.button(
                "Nuevo Look",
                icon=f":material/{ADD}:",
                key=f"wardrobe_add_look_{character_key}",
                use_container_width=True
            )

        with delete_column:
            delete_look = st.button(
                "Eliminar Look",
                icon=f":material/{DELETE}:",
                key=f"wardrobe_delete_look_{character_key}",
                use_container_width=True
            )

        if add_look:
            look_id, look = _new_look(len(looks) + 1)
            wardrobe_state = _get_wardrobe_state()
            wardrobe_state[_MASTER_CATALOG_KEY][character_key]["looks"][
                look_id
            ] = look
            st.session_state.breakdown_wardrobe_makeup_data = wardrobe_state
            st.rerun()

        if delete_look:
            _confirm_delete_look(character_key, selected_look_id)

    return selected_look_id


def _build_scene_options():
    scenes_df = st.session_state.get("scenes_df", pd.DataFrame())
    scene_labels = {}

    if scenes_df is None or scenes_df.empty:
        return [], scene_labels

    for _, row in scenes_df.iterrows():
        scene_number = _clean_text(row.get("Escena", ""))

        if not scene_number or scene_number in scene_labels:
            continue

        heading = _clean_text(row.get("Encabezado de escena", ""))
        scene_labels[scene_number] = (
            f"Escena {scene_number} | {heading}"
            if heading
            else f"Escena {scene_number}"
        )

    return list(scene_labels.keys()), scene_labels


def _render_look_form(character_key, look_id, look):
    scene_options, scene_labels = _build_scene_options()
    selected_scenes = [
        scene
        for scene in look.get("scenes", [])
        if scene in scene_labels
    ]

    with st.form(f"wardrobe_look_form_{character_key}_{look_id}"):
        with cine_panel(
            title=_icon_label(WARDROBE, "Ficha completa del Look"),
            subtitle="Define el estado visual integral del personaje.",
        ):
            look_name = st.text_input(
                "Nombre del Look",
                value=look["name"],
                key=f"wardrobe_look_name_{look_id}"
            )

        edited_values = {}

        for field in _LOOK_FIELDS:
            st.write("")

            with cine_panel(
                title=_icon_label(field["icon"], field["title"]),
                subtitle=field["description"],
            ):
                edited_values[field["key"]] = st.text_area(
                    field["title"],
                    value=look[field["key"]],
                    height=130,
                    label_visibility="collapsed",
                    key=f'wardrobe_{field["key"]}_{look_id}'
                )

        st.write("")

        with cine_panel(
            title=_icon_label(SCENE, "Escenas que utilizan este Look"),
            subtitle=(
                "Selecciona todas las escenas donde el personaje conserva este "
                "estado visual. Las escenas no se modifican."
            ),
        ):
            scenes = st.multiselect(
                "Escenas",
                scene_options,
                default=selected_scenes,
                format_func=lambda scene: scene_labels[scene],
                key=f"wardrobe_scenes_{look_id}"
            )

        st.write("")
        _, save_column, _ = st.columns([1, 2, 1])

        with save_column:
            save_look = st.form_submit_button(
                "Guardar Look",
                icon=f":material/{SAVE}:",
                type="primary",
                use_container_width=True
            )

        if save_look:
            wardrobe_state = _get_wardrobe_state()
            saved_look = wardrobe_state[_MASTER_CATALOG_KEY][character_key][
                "looks"
            ][look_id]
            saved_look["look_id"] = look_id
            saved_look["name"] = _clean_text(look_name) or look["name"]

            for field_key, value in edited_values.items():
                saved_look[field_key] = value

            saved_look["scenes"] = list(scenes)
            st.session_state.breakdown_wardrobe_makeup_data = wardrobe_state
            st.success("Look guardado correctamente.")


def _scene_sort_key(scene_number):
    try:
        return 0, float(scene_number)
    except ValueError:
        return 1, str(scene_number).casefold()


def _render_character_look_summary(catalog):
    st.markdown(f"### {_icon_label(ANALYTICS, 'Resumen de Looks por personaje')}")
    st.caption(
        "Consulta los Looks maestros, sus apariciones y las escenas donde se "
        "utiliza cada uno."
    )

    for character_record in catalog.values():
        rows = []
        processed_looks = set()

        for look_id, look in character_record["looks"].items():
            stable_look_id = look.get("look_id", look_id)

            if stable_look_id in processed_looks:
                continue

            processed_looks.add(stable_look_id)
            scenes = sorted(look.get("scenes", []), key=_scene_sort_key)
            rows.append({
                "Character": character_record["character"],
                "Look": look["name"],
                "Apariciones": len(scenes),
                "Escenas": ", ".join(scenes),
            })

        summary_df = pd.DataFrame(
            rows,
            columns=["Character", "Look", "Apariciones", "Escenas"]
        )

        with cine_panel(
            title=_icon_label(CHARACTER, character_record["character"]),
            subtitle=f'{len(rows)} Look(s) registrado(s)',
        ):
            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True
            )


def render_wardrobe_page():
    render_section_header(
        icon=WARDROBE,
        title="Vestuario / Maquillaje",
        description=(
            "Administra los Looks maestros y la continuidad visual de cada "
            "personaje del proyecto."
        )
    )

    catalog = _synchronize_character_catalog()

    if not catalog:
        st.info(
            "No hay personajes detectados. Revisa primero la sección Personajes "
            "en Importar y revisar."
        )
        return

    character_key = _render_character_selector(catalog)
    character_record = catalog[character_key]
    work_column, summary_column = st.columns([1.85, 1], gap="large")

    with work_column:
        look_id = _render_look_manager(character_key, character_record)
        _render_look_form(
            character_key,
            look_id,
            character_record["looks"][look_id]
        )

    with summary_column:
        current_state = _get_wardrobe_state()
        current_catalog = current_state[_MASTER_CATALOG_KEY]
        _render_character_look_summary(current_catalog)
