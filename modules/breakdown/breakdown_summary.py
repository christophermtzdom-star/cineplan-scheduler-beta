from collections.abc import Mapping

import streamlit as st

from components.icons import (
    ANALYTICS,
    CAST,
    EXTRAS,
    PENDING,
    PRODUCTION,
    PROPS,
    SCENE,
    TASK,
    VFX,
    WARDROBE,
)
from components.panel import cine_panel


_REVIEWED_STATUSES = {
    "REVISADO",
    "LISTO PARA EXPORTAR",
}

_DEPARTMENTS = (
    ("Cast", CAST, "breakdown_cast_data"),
    ("Props", PROPS, "breakdown_props_data"),
    ("Vestuario / Maquillaje", WARDROBE, "breakdown_wardrobe_makeup_data"),
    ("VFX / Sonido", VFX, "breakdown_vfx_sound_data"),
    ("Extras", EXTRAS, "breakdown_extras_data"),
    ("Producción", PRODUCTION, "breakdown_production_notes_data"),
)


def _icon_label(icon, label):
    return f":material/{icon}: {label}"


def _normalize_scene_id(value):
    if value is None:
        return ""

    scene_id = str(value).strip()

    if scene_id.lower() in {"", "nan", "none"}:
        return ""

    if scene_id.endswith(".0"):
        integer_part = scene_id[:-2]
        if integer_part.lstrip("-").isdigit():
            return integer_part

    return scene_id


def _get_scene_ids(scenes_df):
    if scenes_df is None or "Escena" not in getattr(scenes_df, "columns", []):
        return set()

    return {
        scene_id
        for scene_id in (
            _normalize_scene_id(value)
            for value in scenes_df["Escena"].tolist()
        )
        if scene_id
    }


def _get_mapping(state_key):
    value = st.session_state.get(state_key, {})
    return value if isinstance(value, Mapping) else {}


def _get_general_stats(scenes_df, scene_ids):
    total = len(scenes_df) if scenes_df is not None else 0
    scene_data = _get_mapping("breakdown_scene_data")

    reviewed_ids = {
        _normalize_scene_id(scene_id)
        for scene_id, data in scene_data.items()
        if isinstance(data, Mapping)
        and str(data.get("Estado breakdown", "")).strip().upper()
        in _REVIEWED_STATUSES
    }

    if scene_ids:
        reviewed = len(reviewed_ids.intersection(scene_ids))
    else:
        reviewed = min(total, len(reviewed_ids))

    pending = max(0, total - reviewed)
    progress = reviewed / total if total else 0.0

    return {
        "total": total,
        "reviewed": reviewed,
        "pending": pending,
        "progress": progress,
    }


def _get_department_stats(state_key, scene_ids, total_scenes):
    department_data = _get_mapping(state_key)
    completed_ids = {
        scene_id
        for scene_id in (
            _normalize_scene_id(value)
            for value in department_data.keys()
        )
        if scene_id
    }

    if scene_ids:
        completed = len(completed_ids.intersection(scene_ids))
    else:
        completed = min(total_scenes, len(completed_ids))

    progress = completed / total_scenes if total_scenes else 0.0
    return completed, progress


def _render_general_summary(stats):
    with cine_panel(
        title="Resumen general",
        subtitle="Estado global de la revisión de escenas del breakdown.",
    ):
        columns = st.columns(4)
        columns[0].metric(
            _icon_label(SCENE, "Total de escenas"),
            stats["total"]
        )
        columns[1].metric(
            _icon_label(TASK, "Escenas revisadas"),
            stats["reviewed"]
        )
        columns[2].metric(
            _icon_label(PENDING, "Escenas pendientes"),
            stats["pending"]
        )
        columns[3].metric(
            _icon_label(ANALYTICS, "Progreso general"),
            f'{stats["progress"]:.0%}'
        )
        st.progress(stats["progress"])


def _render_department_card(label, icon, state_key, scene_ids, total_scenes):
    completed, progress = _get_department_stats(
        state_key,
        scene_ids,
        total_scenes,
    )

    with cine_panel(
        title=_icon_label(icon, label),
        subtitle=f"{completed} de {total_scenes} escenas",
    ):
        st.metric("Progreso", f"{progress:.0%}")
        st.progress(progress)


def _render_department_progress(scene_ids, total_scenes):
    st.markdown("### Progreso por departamento")
    st.caption("Cobertura registrada por escena en cada área del breakdown.")

    for start in range(0, len(_DEPARTMENTS), 3):
        columns = st.columns(3, gap="large")

        for column, (label, icon, state_key) in zip(
            columns,
            _DEPARTMENTS[start:start + 3],
        ):
            with column:
                _render_department_card(
                    label,
                    icon,
                    state_key,
                    scene_ids,
                    total_scenes,
                )


def render_breakdown_summary():
    scenes_df = st.session_state.get("scenes_df")
    total_scenes = len(scenes_df) if scenes_df is not None else 0
    scene_ids = _get_scene_ids(scenes_df)

    st.markdown("## Resumen del proceso del Breakdown")
    st.caption(
        "Consulta el avance general y la cobertura de trabajo por departamento."
    )

    if total_scenes == 0:
        st.info("No hay escenas disponibles para calcular el progreso del breakdown.")
        return

    general_stats = _get_general_stats(scenes_df, scene_ids)
    _render_general_summary(general_stats)
    _render_department_progress(scene_ids, total_scenes)
