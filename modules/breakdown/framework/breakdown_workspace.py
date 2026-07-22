"""Compact, desktop-style three-panel Breakdown resource workspace."""

import pandas as pd
import streamlit as st

from .autocomplete_engine import autocomplete
from .resource_catalog import catalog_rows
from .resource_filters import filter_rows, sort_rows
from .resource_summary import resource_statistics


_SECTIONS = ("General", "Producción", "Continuidad", "Proyecto")


def _key(config, *parts):
    """Return a stable widget key scoped to one resource workspace."""
    suffix = "_".join(str(part).strip().replace(" ", "_").casefold() for part in parts if part != "")
    return f"{config.resource_type}_{suffix}" if suffix else str(config.resource_type)


def _rerun_changed(on_change):
    if on_change:
        on_change()


def _autosave(engine, resource_id, scene_id, config, on_change):
    prefix = _key(config, "inspector", resource_id)
    resource_changes = {
        "name": st.session_state.get(f"{prefix}_name", ""),
        "category": st.session_state.get(f"{prefix}_category", config.categories[0]),
        "status": st.session_state.get(f"{prefix}_status", config.statuses[0]),
        "favorite": st.session_state.get(f"{prefix}_favorite", False),
    }
    assignment_changes = {
        "quantity": st.session_state.get(f"{prefix}_quantity", 1),
    }
    custom_fields = dict(engine.get(resource_id).get("custom_fields", {}))
    for field in config.inspector_fields:
        if field.read_only:
            continue
        value = st.session_state.get(f"{prefix}_{field.key}", "")
        if field.scope == "resource":
            resource_changes[field.key] = value
        elif field.scope == "custom":
            custom_fields[field.key] = value
        else:
            assignment_changes[field.key] = value
    resource_changes["custom_fields"] = custom_fields
    engine.update(resource_id, **resource_changes)
    engine.assign(resource_id, scene_id, **assignment_changes)
    _rerun_changed(on_change)


def _render_metric_strip(stats):
    st.markdown(
        f"""
        <div class="bw-metrics">
          <div><b>{stats['current_scene']}</b><span>Escena</span></div>
          <div><b>{stats['project_total']}</b><span>Total</span></div>
          <div><b>{stats['favorites']}</b><span>Fav</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_new_resource(engine, config, scene_id, on_change, resource_configs=None):
    resource_configs = tuple(resource_configs or (config,))
    with st.popover("Nuevo", icon=":material/add:", use_container_width=True,
                    key=_key(config, "new")):
        create_config = config
        if len(resource_configs) > 1:
            labels = {item.label: item for item in resource_configs}
            selected_label = st.selectbox("Tipo de recurso", tuple(labels),
                                          key=_key(config, "new", "resource", "type"))
            create_config = labels[selected_label]
        typed_name = st.text_input("Nombre", key=_key(config, "new", "name"))
        suggestions = autocomplete(engine, typed_name, create_config.resource_type)
        if suggestions:
            st.caption("Coincidencias del proyecto")
            for match in suggestions[:4]:
                scenes = ", ".join(match["scenes"]) or "sin escenas"
                if st.button(f"Usar {match['name']} · {scenes}",
                             key=_key(config, "new", "reuse", match["id"]),
                             use_container_width=True):
                    engine.assign(match["id"], scene_id)
                    st.session_state[f"{config.resource_type}_selected_id"] = match["id"]
                    _rerun_changed(on_change)
                    st.rerun()
        category = st.selectbox("Categoría", create_config.categories,
                                key=_key(config, "new", "category"))
        exact = engine.exact_name(typed_name, create_config.resource_type)
        create_label = "Usar recurso existente" if exact and not create_config.allow_duplicate_creation else "Crear recurso"
        if st.button(create_label, type="primary", disabled=not typed_name.strip(),
                     key=_key(config, "new", "create"), use_container_width=True):
            resource = exact if exact and not create_config.allow_duplicate_creation else engine.create(
                create_config, typed_name, category,
                allow_duplicate=create_config.allow_duplicate_creation and bool(suggestions)
            )
            engine.assign(resource["id"], scene_id)
            st.session_state[f"{config.resource_type}_selected_id"] = resource["id"]
            _rerun_changed(on_change)
            st.rerun()


def _render_field(field, value, key, callback, disabled=False):
    args = callback
    if field.read_only:
        st.text_input(field.label, str(value or ""), key=key, disabled=True)
    elif field.kind == "textarea":
        st.text_area(field.label, str(value or ""), key=key, height=82,
                     on_change=_autosave, args=args, disabled=disabled)
    elif field.kind == "number":
        st.number_input(field.label, value=float(value or 0), key=key,
                        on_change=_autosave, args=args, disabled=disabled)
    elif field.kind == "select":
        options = field.options or ("",)
        st.selectbox(field.label, options,
                     index=options.index(value) if value in options else 0,
                     key=key, on_change=_autosave, args=args, disabled=disabled)
    else:
        st.text_input(field.label, str(value or ""), key=key,
                      on_change=_autosave, args=args, disabled=disabled)


def _field_value(field, resource, assignment, engine):
    if field.key == "scene":
        return assignment.get("scene_id", "")
    if field.key == "relationships":
        scenes = sorted({a["scene_id"] for a in engine.assignments_for_resource(resource["id"])})
        return f"Escenas: {', '.join(scenes) or '—'} · Personajes: {', '.join(resource.get('characters', [])) or '—'}"
    if field.scope == "resource":
        return resource.get(field.key, "")
    if field.scope == "custom":
        return resource.get("custom_fields", {}).get(field.key, "")
    return assignment.get(field.key, "")


def _search_ids(engine, query, resource_type):
    """Use engine search plus assignment fields configured by workspace modules."""
    identity = str(query or "").casefold().strip()
    matches = {resource["id"] for resource in engine.find(query, resource_type)}
    if not identity:
        return matches
    for resource in engine.resources(resource_type):
        custom = resource.get("custom_fields", {})
        tags = custom.get("tags", "") if isinstance(custom, dict) else ""
        assignments = engine.assignments_for_resource(resource["id"])
        searchable = " ".join([
            str(tags),
            *(str(assignment.get("responsible", "")) for assignment in assignments),
        ]).casefold()
        if identity in searchable:
            matches.add(resource["id"])
    return matches


def _render_inspector(engine, config, scene_id, selected_id, on_change):
    st.markdown("#### Inspector")
    if not selected_id or selected_id not in engine.store["resources"]:
        st.caption("Selecciona un recurso para editarlo.")
        return
    resource = engine.get(selected_id)
    assignment = next((a for a in engine.assignments_for_scene(scene_id)
                       if a["resource_id"] == selected_id), {})
    prefix = _key(config, "inspector", selected_id)
    callback = (engine, selected_id, scene_id, config, on_change)
    tabs = st.tabs(_SECTIONS, key=_key(config, "inspector", "sections"))
    with tabs[0]:
        st.caption(selected_id)
        st.text_input("Nombre", resource.get("name", ""), key=f"{prefix}_name",
                      on_change=_autosave, args=callback)
        c1, c2 = st.columns(2, gap="small")
        c1.selectbox("Categoría", config.categories,
                     index=config.categories.index(resource.get("category")) if resource.get("category") in config.categories else 0,
                     key=f"{prefix}_category", on_change=_autosave, args=callback)
        c2.selectbox("Estado", config.statuses,
                     index=config.statuses.index(resource.get("status")) if resource.get("status") in config.statuses else 0,
                     key=f"{prefix}_status", on_change=_autosave, args=callback)
        st.number_input("Cantidad", min_value=0, step=1, value=int(assignment.get("quantity", 1) or 0),
                        key=f"{prefix}_quantity", on_change=_autosave, args=callback)
        for field in (f for f in config.inspector_fields if f.section == "General"):
            _render_field(field, _field_value(field, resource, assignment, engine),
                          f"{prefix}_{field.key}", callback)
    for tab, section in zip(tabs[1:], _SECTIONS[1:]):
        with tab:
            if section == "Proyecto":
                st.checkbox("Favorito", resource.get("favorite", False), key=f"{prefix}_favorite",
                            on_change=_autosave, args=callback)
            fields = [f for f in config.inspector_fields if f.section == section]
            if not fields:
                st.caption("Sin campos configurados.")
            for field in fields:
                _render_field(field, _field_value(field, resource, assignment, engine),
                              f"{prefix}_{field.key}", callback)


def render_workspace(engine, config, scene_id, scene_record=None, on_change=None,
                     resource_configs=None):
    """Render the common workspace; department behavior comes from configuration."""
    scene_record = scene_record or {}
    resource_configs = tuple(resource_configs or (config,))
    configs_by_type = {item.resource_type: item for item in resource_configs}
    type_labels = {item.label: item.resource_type for item in resource_configs}
    st.markdown("""
    <style>
      .bw-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin:4px 0 8px}
      .bw-metrics div{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.09);border-radius:7px;padding:6px 3px;text-align:center}
      .bw-metrics b{display:block;font-size:1.05rem;line-height:1.1}.bw-metrics span{font-size:.68rem;opacity:.68}
      [data-testid="stVerticalBlock"]{gap:.45rem}
      [data-testid="stMetric"]{padding:0}
    </style>""", unsafe_allow_html=True)
    st.caption(f"ESCENA {scene_id}  ·  {scene_record.get('Encabezado de escena', '')}  ·  "
               f"{scene_record.get('INT/EXT', '')}  ·  {scene_record.get('Tiempo', '')}")
    left, center, right = st.columns([0.95, 2.7, 1.5], gap="small")
    with left:
        query = st.text_input("Buscar", key=_key(config, "search"),
                              placeholder="Nombre, escena, personaje…", label_visibility="collapsed",
                              icon=":material/search:")
        selected_type_label = "Todos"
        if len(resource_configs) > 1:
            selected_type_label = st.selectbox(
                "Tipo de recurso", ("Todos", *type_labels),
                key=_key(config, "resource", "type", "filter"),
            )
        selected_type = type_labels.get(selected_type_label, "")
        filtered_configs = (configs_by_type[selected_type],) if selected_type else resource_configs
        categories = tuple(dict.fromkeys(value for item in filtered_configs for value in item.categories))
        statuses = tuple(dict.fromkeys(value for item in filtered_configs for value in item.statuses))
        category = st.selectbox("Categoría", ("Todas", *categories),
                                key=_key(config, "category", "filter"))
        status = st.selectbox("Estado", ("Todos", *statuses),
                              key=_key(config, "status", "filter"))
        resources = [resource for item in filtered_configs for resource in engine.resources(item.resource_type)]
        assignments = [assignment for item in filtered_configs
                       for assignment in engine.assignments_for_scene(scene_id, item.resource_type)]
        _render_metric_strip({
            "current_scene": len(assignments),
            "project_total": len(resources),
            "favorites": sum(bool(resource.get("favorite")) for resource in resources),
        })

    view_key = _key(config, "workspace", "view")
    with center:
        view = st.segmented_control("Vista", ("Escena actual", "Catálogo", "Estadísticas"),
                                    default="Escena actual", key=view_key,
                                    label_visibility="collapsed")
        rows = []
        for item in filtered_configs:
            type_label = f"{item.material_symbol}  {item.label}" if item.material_symbol else item.label
            rows.extend({**row, "Tipo": type_label} for row in catalog_rows(engine, item.resource_type))
        if view == "Escena actual":
            assigned = {assignment["resource_id"]: assignment for item in filtered_configs
                        for assignment in engine.assignments_for_scene(scene_id, item.resource_type)}
            rows = [{**row, "Cantidad": assigned[row["ID"]].get("quantity", 1),
                     "Personaje": assigned[row["ID"]].get("character", "")}
                    for row in rows if row["ID"] in assigned]
        if query:
            allowed = set().union(*(
                _search_ids(engine, query, item.resource_type) for item in filtered_configs
            ))
            rows = [row for row in rows if row["ID"] in allowed]
        rows = filter_rows(rows, "" if category == "Todas" else category,
                           "" if status == "Todos" else status)
        if view == "Estadísticas":
            counts = []
            for item in filtered_configs:
                for category_name in item.categories:
                    total = sum(resource.get("category") == category_name
                                for resource in engine.resources(item.resource_type))
                    counts.append({"Tipo": item.label, "Categoría": category_name, "Recursos": total})
            st.dataframe(pd.DataFrame(counts),
                         hide_index=True, use_container_width=True, height=560,
                         key=_key(config, "statistics", "table"))
        else:
            rows = sort_rows(rows, "Nombre")
            display = pd.DataFrame(rows)
            visible = [c for c in ("Tipo", "ID", "Nombre", "Categoría", "Personaje", "Escenas", "Cantidad", "Estado") if c in display.columns]
            event = st.dataframe(display[visible] if visible else display, hide_index=True,
                                 use_container_width=True, height=560, selection_mode="single-row",
                                 on_select="rerun", key=_key(config, "resource", "table"))
            selection = event.selection.rows if event else []
            if selection and selection[0] < len(rows):
                selected_id = rows[selection[0]]["ID"]
                st.session_state[f"{config.resource_type}_selected_id"] = selected_id
        selected_id = st.session_state.get(f"{config.resource_type}_selected_id", "")
        actions = st.columns(3, gap="small")
        with actions[0]:
            _render_new_resource(engine, config, scene_id, on_change, filtered_configs)
        if actions[1].button("Duplicar", icon=":material/content_copy:", disabled=not selected_id,
                             use_container_width=True, key=_key(config, "duplicate")):
            source = engine.get(selected_id)
            source_config = configs_by_type[source["resource_type"]]
            duplicate = engine.create(source_config, f"{source['name']} copia", source["category"],
                                      status=source.get("status", source_config.statuses[0]))
            engine.assign(duplicate["id"], scene_id)
            st.session_state[f"{config.resource_type}_selected_id"] = duplicate["id"]
            _rerun_changed(on_change)
            st.rerun()
        remove_label = "Quitar" if st.session_state.get(view_key, "Escena actual") == "Escena actual" else "Eliminar"
        with actions[2].popover(remove_label, icon=":material/delete:",
                                disabled=not selected_id, use_container_width=True,
                                key=_key(config, "remove")):
            message = ("Quitar la referencia de esta escena. El recurso seguirá en el proyecto."
                       if remove_label == "Quitar" else
                       "Eliminar el recurso del proyecto y de todas sus escenas.")
            st.caption(message)
            if st.button(f"Confirmar {remove_label.lower()}", type="primary",
                         key=_key(config, "remove", "confirm", selected_id),
                         use_container_width=True):
                if remove_label == "Quitar":
                    engine.unassign(selected_id, scene_id)
                else:
                    engine.delete(selected_id)
                st.session_state.pop(f"{config.resource_type}_selected_id", None)
                _rerun_changed(on_change)
                st.rerun()
    with right:
        selected_id = st.session_state.get(f"{config.resource_type}_selected_id", "")
        inspector_config = config
        if selected_id in engine.store["resources"]:
            inspector_config = configs_by_type.get(
                engine.store["resources"][selected_id].get("resource_type"), config
            )
        _render_inspector(engine, inspector_config, scene_id, selected_id, on_change)
