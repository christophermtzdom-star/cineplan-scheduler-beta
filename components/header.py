from html import escape

import streamlit as st

from components.icons import ICONS, cine_icon


def render_section_header(icon, title, description):
    """Render the standard Review-style section header."""
    if icon not in ICONS.values():
        raise ValueError("icon must be a centralized CinePlan Material Symbol")

    icon_html = cine_icon(icon, size=24)

    st.markdown(
        f"""
        <div class="review-section-title review-project-intro">
            <h2>{icon_html} {escape(str(title))}</h2>
            <p>{escape(str(description))}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def cine_header(title, subtitle="", icon=""):
    st.markdown(
        f"""
<div class="cine-header">
    <div class="cine-header-icon">{icon}</div>

    <div>
        <h1 class="cine-header-title">{title}</h1>
        <p class="cine-header-subtitle">{subtitle}</p>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def cine_dashboard_header(
    project_name="Proyecto sin título",
    director_name="",
    project_type="Preproducción audiovisual",
    script_name="Sin guion importado",
    script_type="-",
    imported_date="-",
    scenes_count=0,
    characters_count=0,
    locations_count=0,
    progress=0,
    next_step=""
):
    progress = max(0, min(progress, 100))
    welcome = "Bienvenido"
    if str(director_name).strip():
        welcome = f"Bienvenido, {str(director_name).strip()}"

    st.html(
        f"""
<div class="cine-dashboard-hero">

    <div class="cine-dashboard-main">

        <div class="cine-dashboard-badge">
            En preproducción
        </div>

        <h1>{escape(str(project_name))}</h1>

        <p>{escape(welcome)} · {escape(str(project_type))}</p>

        <div class="cine-dashboard-meta">
            <span>Guion: <strong>{escape(str(script_name))}</strong></span>
            <span>Tipo: <strong>{escape(str(script_type))}</strong></span>
            <span>Importado: <strong>{escape(str(imported_date))}</strong></span>
        </div>

        <div class="cine-dashboard-stats-line">
            {scenes_count} escenas ·
            {characters_count} personajes ·
            {locations_count} locaciones
        </div>

    </div>

    <div class="cine-dashboard-progress-box">

        <div class="cine-dashboard-progress-label">
            <span>Avance general</span>
            <strong>{progress}%</strong>
        </div>

        <div class="cine-dashboard-progress-track">
            <div class="cine-dashboard-progress-fill"
                 style="width:{progress}%;"></div>
        </div>

        <div class="cine-dashboard-next-step">
            <strong>Siguiente paso</strong><br>
            {escape(str(next_step))}
        </div>

    </div>

</div>
"""
    )
