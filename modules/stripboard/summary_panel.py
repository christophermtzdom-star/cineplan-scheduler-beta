"""Reusable summary panels for design and planning views."""

import streamlit as st

from modules.stripboard.colors import STRIP_COLORS
from modules.stripboard.planner_utils import build_visible_summary


def _summary_item(label, value):
    st.markdown(
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'padding:8px 0;border-bottom:1px solid rgba(148,163,184,.12);">'
        f'<span style="font-size:12px;color:#cbd5e1;">{label}</span>'
        f'<strong style="font-size:13px;color:#f8fafc;">{value}</strong></div>',
        unsafe_allow_html=True,
    )


def render_stripboard_summary(visible_scenes=None):
    summary = build_visible_summary(visible_scenes)
    for label in (
        "Escenas", "Páginas", "Octavos", "Personajes", "Locaciones", "Looks",
        "Props", "Extras", "Vehículos", "Animales", "VFX", "Efectos Prácticos",
        "Sonido", "Notas",
    ):
        _summary_item(label, summary[label])

    st.markdown("#### Distribución")
    for label, value in summary["Distribución"].items():
        st.markdown(
            '<div style="display:flex;align-items:center;gap:9px;padding:7px 0;">'
            f'<span style="width:9px;height:9px;border-radius:3px;background:{STRIP_COLORS[label]};"></span>'
            f'<span style="flex:1;font-size:12px;color:#cbd5e1;">{label.title()}</span>'
            f'<strong style="font-size:13px;color:#f8fafc;">{value}</strong></div>',
            unsafe_allow_html=True,
        )


def render_planning_summary():
    st.markdown(
        '<div style="padding:18px;border:1px dashed rgba(248,180,0,.35);border-radius:12px;'
        'background:rgba(248,180,0,.05);text-align:center;">'
        '<span class="material-symbols-rounded" style="font-size:28px;color:#f8b400;">'
        'event_note</span><div style="font-size:13px;font-weight:700;color:#f8fafc;'
        'margin-top:8px;">Resumen de planificación</div>'
        '<div style="font-size:11px;color:#94a3b8;margin-top:5px;">'
        'Se activará al construir jornadas de rodaje.</div></div>',
        unsafe_allow_html=True,
    )
