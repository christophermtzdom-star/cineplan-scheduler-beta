import streamlit as st
from components.icons import cine_icon


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
    icon_html = cine_icon(icon, size=22)

    html = f"""<div class="cine-action-card">
<div class="cine-action-header">
<div class="cine-action-icon">{icon_html}</div>
<div class="cine-action-text">
<div class="cine-action-title">{title}</div>
<div class="cine-action-subtitle">{subtitle}</div>
</div>
</div>
<div class="cine-action-footer">
<span>{action_text}</span>
<span class="material-symbols-rounded">arrow_forward</span>
</div>
</div>"""

    st.markdown(html, unsafe_allow_html=True)