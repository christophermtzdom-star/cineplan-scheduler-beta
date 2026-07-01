import streamlit as st


@st.dialog("Importar guion")
def import_dialog():

    st.markdown(
        """
Selecciona un archivo **PDF** o **Final Draft (.FDX)**.

También puedes arrastrarlo directamente aquí.
"""
    )

    uploaded_file = st.file_uploader(
        "Guion",
        type=["pdf", "fdx"],
        label_visibility="collapsed"
    )

    if uploaded_file is None:
        return

    uploaded_file_id = f"{uploaded_file.name}_{uploaded_file.size}"

    if st.session_state.get("pending_uploaded_file_id") != uploaded_file_id:
        st.session_state["uploaded_script"] = uploaded_file
        st.session_state["pending_uploaded_file_id"] = uploaded_file_id
        st.rerun()