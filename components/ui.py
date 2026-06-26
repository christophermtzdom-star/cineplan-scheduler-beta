import streamlit as st
def cine_icon(name, size=32, color="currentColor"):
    return f"""
    <span class="material-symbols-rounded" style="font-size:{size}px; color:{color};">
        {name}
    </span>
    """


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
        unsafe_allow_html=True
    )
def cine_card(title, subtitle="", icon="", accent="primary"):
    st.markdown(
        f"""
        <div class="cine-card cine-card-{accent}">
            <div class="cine-card-icon">{icon}</div>
            <div class="cine-card-title">{title}</div>
            <div class="cine-card-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
def cine_action_card(title, subtitle="", icon="description", action_text="Abrir"):
    icon_html = cine_icon(icon, size=38)

    st.markdown(
        f"""
        <div class="cine-action-card">
            <div class="cine-action-icon">{icon_html}</div>
            <div class="cine-action-title">{title}</div>
            <div class="cine-action-subtitle">{subtitle}</div>
            <div class="cine-action-footer">{action_text} →</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        f"""
        <div class="cine-action-card">
            <div class="cine-action-icon">{icon}</div>
            <div class="cine-action-title">{title}</div>
            <div class="cine-action-subtitle">{subtitle}</div>
            <div class="cine-action-footer">{action_text} →</div>
        </div>
        """,
        unsafe_allow_html=True
    )