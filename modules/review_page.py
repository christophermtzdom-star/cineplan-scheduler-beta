import streamlit as st
from project.workspace_runtime import begin_module, begin_submodule, current_submodule, notify_tab_change

from modules.review.project_tab import render_project_tab
from modules.review.scenes_tab import render_scenes_tab
from modules.review.locations_tab import render_locations_tab
from modules.review.characters_tab import render_characters_tab
from modules.review.octavos_tab import render_octavos_tab
from modules.review.summary_tab import render_summary_tab


def render_review_page():
    begin_module("Importar y revisar")

    st.markdown(
        """
        <div class="review-page">
            <div class="review-header">
                <div class="review-header-icon">
                    <span class="material-symbols-rounded">fact_check</span>
                </div>
                <div>
                    <div class="review-kicker">1. Importar y analizar guion</div>
                    <h1>Revisión inicial</h1>
                    <p>
                        Revisa y ajusta la información detectada antes de continuar al Breakdown.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    labels = [
        "Proyecto",
        "Escenas detectadas",
        "Locaciones",
        "Personajes",
        "Octavos",
        "Resumen general"
    ]
    selected = current_submodule("Proyecto")
    if selected not in labels:
        selected = "Proyecto"
    tabs = st.tabs(
        labels, default=selected, key="review_workspace_tab",
        on_change=notify_tab_change, args=("review_workspace_tab",),
    )
    begin_submodule(selected)

    with tabs[0]:
        render_project_tab()

    with tabs[1]:
        render_scenes_tab()

    with tabs[2]:
        render_locations_tab()

    with tabs[3]:
        render_characters_tab()

    with tabs[4]:
        render_octavos_tab()

    with tabs[5]:
        render_summary_tab()
