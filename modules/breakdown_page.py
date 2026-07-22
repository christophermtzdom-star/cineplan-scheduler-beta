import streamlit as st
from project.workspace_runtime import begin_module, begin_submodule, current_submodule, notify_tab_change

from modules.breakdown.scene_page import render_scene_page
from modules.breakdown.cast_page import render_cast_page
from modules.breakdown.props_page import render_props_page
from modules.breakdown.wardrobe_page import render_wardrobe_page
from modules.breakdown.vfx_page import render_vfx_page
from modules.breakdown.extras_page import render_extras_page
from modules.breakdown.production_page import render_production_page
from modules.breakdown.export_page import render_export_page


def render_breakdown_page():
    begin_module("Breakdown")

    st.markdown(
        """
        <div class="review-page">
            <div class="review-header">
                <div class="review-header-icon">
                    <span class="material-symbols-rounded">calendar_month</span>
                </div>
                <div>
                    <div class="review-kicker">2. Breakdown</div>
                    <h1>Desglose de producción</h1>
                    <p>
                        Completa y organiza los elementos necesarios de cada escena por departamento.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    labels = [
        "Datos de escena",
        "Reparto / Talento",
        "Utilería",
        "Vestuario / Maquillaje",
        "VFX / SFX / Sonido",
        "Extras / Vehículos",
        "Notas de producción",
        "Exportar Desglose"
    ]
    selected = current_submodule("Datos de escena")
    if selected not in labels:
        selected = "Datos de escena"
    tabs = st.tabs(
        labels, default=selected, key="breakdown_workspace_tab",
        on_change=notify_tab_change, args=("breakdown_workspace_tab",),
    )
    begin_submodule(selected)

    with tabs[0]:
        render_scene_page()

    with tabs[1]:
        render_cast_page()

    with tabs[2]:
        render_props_page()

    with tabs[3]:
        render_wardrobe_page()

    with tabs[4]:
        render_vfx_page()

    with tabs[5]:
        render_extras_page()

    with tabs[6]:
        render_production_page()

    with tabs[7]:
        render_export_page()
