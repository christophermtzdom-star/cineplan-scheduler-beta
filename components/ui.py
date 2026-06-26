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
        unsafe_allow_html=True
    )