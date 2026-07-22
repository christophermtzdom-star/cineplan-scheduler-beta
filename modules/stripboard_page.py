"""Controller for the new CinePlan Stripboard module."""

import streamlit as st
from project.workspace_runtime import begin_module, begin_submodule

from modules.stripboard.design_page import render_design_page


def render_stripboard_page(scenes_df=None):
    """Render the single Stripboard production-planning workspace."""
    begin_module("Stripboard")
    begin_submodule("Diseñar Stripboard")
    if scenes_df is None:
        scenes_df = st.session_state.get("scenes_df")

    st.markdown(
        '<div class="review-page"><div class="review-header">'
        '<div class="review-header-icon">'
        '<span class="material-symbols-rounded">view_timeline</span></div>'
        '<div><div class="review-kicker">4. Stripboard</div>'
        '<h1>Diseño de Stripboard</h1>'
        '<p>Analiza visualmente las escenas y prepara las decisiones del equipo de dirección.</p>'
        '</div></div></div>',
        unsafe_allow_html=True,
    )

    # Passed through for display only: Stripboard does not store an enriched copy.
    scene_details = st.session_state.get("breakdown_scene_data", {})
    render_design_page(scenes_df, scene_details)
