import streamlit as st
from contextlib import contextmanager


@contextmanager
def cine_panel(title=None, subtitle=None, icon=None, panel_class=""):

    if panel_class:
        st.markdown(
            f'<div class="{panel_class}">',
            unsafe_allow_html=True
        )

    with st.container(border=True):

        if title:
            st.markdown(f"### {title}")

            if subtitle:
                st.caption(subtitle)

        yield

    if panel_class:
        st.markdown("</div>", unsafe_allow_html=True)