import streamlit as st


def cine_topbar(project_name="Sin proyecto"):

    with st.container():

        col_logo, col_import, col_save, col_open, col_settings, col_account = st.columns(
            [4.5, 1.2, 1, 1, 1.3, 1]
        )

        with col_logo:
            st.markdown("### 🎬 CinePlan")
            st.caption(
                "Bienvenido de vuelta, Christopher. Aquí tienes el estado general de tu proyecto."
            )

        with col_import:
            if st.button(
                "Importar",
                icon=":material/upload_file:",
                use_container_width=True
            ):
                st.session_state.show_import_dialog = True

        with col_save:
            st.button(
                "Guardar",
                icon=":material/save:",
                use_container_width=True
            )

        with col_open:
            st.button(
                "Abrir",
                icon=":material/folder_open:",
                use_container_width=True
            )

        with col_settings:
            st.button(
                "Config.",
                icon=":material/settings:",
                use_container_width=True
            )

        with col_account:
            st.button(
                "Cuenta",
                icon=":material/account_circle:",
                use_container_width=True
            )

        st.divider()