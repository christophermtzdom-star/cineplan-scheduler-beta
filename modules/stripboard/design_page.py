"""Design workspace for the read-only Stripboard V1."""

import streamlit as st

from modules.stripboard.config import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_PANEL_WIDTHS,
    PAGE_SIZE_OPTIONS,
    STRIP_LIST_HEIGHT,
    WORKSPACE_PANEL_HEIGHT,
)
from modules.stripboard.filters import render_design_filters
from modules.stripboard.planner_utils import paginate_records, scenes_to_records
from modules.stripboard.strip_card import render_strip_row
from modules.stripboard.summary_panel import render_stripboard_summary


_PAGE_KEY = "stripboard_current_page"
_PAGE_SIZE_KEY = "stripboard_page_size"


def _reset_page():
    st.session_state[_PAGE_KEY] = 1


def _change_page(delta, total_pages):
    current_page = st.session_state.get(_PAGE_KEY, 1)
    st.session_state[_PAGE_KEY] = max(1, min(current_page + delta, total_pages))


def _panel_title(icon, title, subtitle=""):
    subtitle_html = (
        f'<div style="font-size:12px;color:#94a3b8;margin-top:4px;">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(
        '<div style="margin-bottom:16px;">'
        '<div style="display:flex;align-items:center;gap:9px;">'
        f'<span class="material-symbols-rounded" style="color:#f8b400;font-size:22px;">{icon}</span>'
        f'<div style="font-size:18px;font-weight:750;color:#f8fafc;">{title}</div></div>'
        f'{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


def _empty_state():
    st.markdown(
        '<div style="min-height:420px;display:flex;align-items:center;justify-content:center;'
        'border:1px dashed rgba(148,163,184,.3);border-radius:18px;'
        'background:radial-gradient(circle at center,rgba(248,180,0,.07),transparent 55%);">'
        '<div style="max-width:390px;text-align:center;padding:36px;">'
        '<span class="material-symbols-rounded" style="font-size:46px;color:#f8b400;">movie_edit</span>'
        '<div style="font-size:20px;font-weight:750;color:#f8fafc;margin-top:13px;">'
        'Tu Stripboard comienza con el guion</div>'
        '<div style="font-size:13px;line-height:1.6;color:#94a3b8;margin-top:8px;">'
        'Importa un guion para visualizar sus escenas como tiras de producción y preparar el rodaje.'
        '</div></div></div>',
        unsafe_allow_html=True,
    )


def render_design_page(scenes=None, scene_details=None):
    records = scenes_to_records(scenes)
    if _PAGE_KEY not in st.session_state:
        st.session_state[_PAGE_KEY] = 1

    left, center, right = st.columns(DEFAULT_PANEL_WIDTHS, gap="medium")

    with left:
        with st.container(height=WORKSPACE_PANEL_HEIGHT, border=True):
            _panel_title("filter_alt", "Filtros")
            render_design_filters()

    with center:
        with st.container(height=WORKSPACE_PANEL_HEIGHT, border=True):
            _panel_title(
                "view_timeline",
                "Diseñar Stripboard",
                "Organiza y analiza las escenas antes de construir el Plan de Rodaje.",
            )
            st.caption("ESPACIO DE DISEÑO · LECTURA")

            control_col, range_col = st.columns((1, 2.2), vertical_alignment="bottom")
            with control_col:
                page_size = st.selectbox(
                    "Mostrar",
                    PAGE_SIZE_OPTIONS,
                    index=PAGE_SIZE_OPTIONS.index(DEFAULT_PAGE_SIZE),
                    key=_PAGE_SIZE_KEY,
                    on_change=_reset_page,
                )

            page_data = paginate_records(records, st.session_state[_PAGE_KEY], page_size)
            if st.session_state[_PAGE_KEY] != page_data["page"]:
                st.session_state[_PAGE_KEY] = page_data["page"]

            with range_col:
                st.markdown(
                    '<div style="padding:0 0 9px;color:#94a3b8;font-size:13px;">'
                    f'Mostrando <strong style="color:#f8fafc;">'
                    f'{page_data["start"]}–{page_data["end"]}</strong> '
                    f'de {page_data["total_records"]} escenas</div>',
                    unsafe_allow_html=True,
                )

            if records:
                with st.container(height=STRIP_LIST_HEIGHT, border=False):
                    for scene in page_data["records"]:
                        scene_number = str(scene.get("Escena", scene.get("Orden", "")))
                        details = (scene_details or {}).get(scene_number, {})
                        render_strip_row(scene, details)

                previous_col, page_col, next_col = st.columns(
                    (1, 1.4, 1),
                    vertical_alignment="center",
                )
                with previous_col:
                    st.button(
                        "Anterior",
                        icon=":material/chevron_left:",
                        disabled=page_data["page"] <= 1,
                        use_container_width=True,
                        key="stripboard_previous_page",
                        on_click=_change_page,
                        args=(-1, page_data["total_pages"]),
                    )
                with page_col:
                    st.markdown(
                        '<div style="text-align:center;color:#cbd5e1;font-size:13px;">'
                        f'Página <strong>{page_data["page"]}</strong> de '
                        f'<strong>{page_data["total_pages"]}</strong></div>',
                        unsafe_allow_html=True,
                    )
                with next_col:
                    st.button(
                        "Siguiente",
                        icon=":material/chevron_right:",
                        disabled=page_data["page"] >= page_data["total_pages"],
                        use_container_width=True,
                        key="stripboard_next_page",
                        on_click=_change_page,
                        args=(1, page_data["total_pages"]),
                    )
            else:
                _empty_state()

    with right:
        with st.container(height=WORKSPACE_PANEL_HEIGHT, border=True):
            _panel_title("analytics", "Resumen del Stripboard")
            st.caption("ESCENAS VISIBLES")
            render_stripboard_summary(page_data["records"])
