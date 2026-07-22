"""Future shooting-planning workspace shell."""

import streamlit as st

from modules.stripboard.config import PLANNING_PANEL_WIDTHS
from modules.stripboard.filters import render_planning_filters
from modules.stripboard.summary_panel import render_planning_summary


def _heading(icon, title, subtitle=""):
    st.markdown(
        '<div style="margin-bottom:16px;">'
        f'<span class="material-symbols-rounded" style="font-size:22px;color:#f8b400;'
        f'vertical-align:middle;margin-right:8px;">{icon}</span>'
        f'<strong style="font-size:18px;color:#f8fafc;">{title}</strong>'
        f'<div style="font-size:12px;color:#94a3b8;margin-top:5px;">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


def render_planning_page():
    left, center, right = st.columns(PLANNING_PANEL_WIDTHS, gap="medium")

    with left:
        with st.container(border=True):
            _heading("tune", "Planificación", "Filtros futuros")
            render_planning_filters()

    with center:
        with st.container(border=True):
            _heading(
                "calendar_month",
                "Planificar Rodaje",
                "Construye jornadas a partir de las escenas preparadas.",
            )
            st.markdown(
                '<div style="min-height:500px;display:flex;align-items:center;justify-content:center;'
                'border:1px dashed rgba(148,163,184,.32);border-radius:18px;'
                'background:repeating-linear-gradient(135deg,rgba(30,41,59,.35),'
                'rgba(30,41,59,.35) 12px,rgba(15,23,42,.35) 12px,rgba(15,23,42,.35) 24px);">'
                '<div style="max-width:430px;text-align:center;padding:40px;">'
                '<span class="material-symbols-rounded" style="font-size:48px;color:#f8b400;">'
                'dashboard_customize</span>'
                '<div style="font-size:20px;font-weight:750;color:#f8fafc;margin-top:14px;">'
                'El Plan de Rodaje se construirá aquí a partir del Stripboard.</div>'
                '<div style="font-size:12px;color:#94a3b8;margin-top:9px;">'
                'Área preparada para jornadas, unidades y organización visual de tiras.</div>'
                '</div></div>',
                unsafe_allow_html=True,
            )

    with right:
        with st.container(border=True):
            _heading("summarize", "Resumen", "Planificación del rodaje")
            render_planning_summary()
