import streamlit as st


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

    st.html(
        f"""
<div class="cine-dashboard-hero">

    <div class="cine-dashboard-main">

        <div class="cine-dashboard-badge">
            En preproducción
        </div>

        <h1>{project_name}</h1>

        <p>{project_type}</p>

        <div class="cine-dashboard-meta">
            <span>Guion: <strong>{script_name}</strong></span>
            <span>Tipo: <strong>{script_type}</strong></span>
            <span>Importado: <strong>{imported_date}</strong></span>
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
            {next_step}
        </div>

    </div>

</div>
"""
    )