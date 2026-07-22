import streamlit as st

from project.project_paths import safe_default_filename


def _browser_filename(project_name):
    return safe_default_filename(project_name).rsplit(".", 1)[0] + ".cineplan"


def cine_topbar(
    project_name="Sin proyecto", on_save=None, on_open=None, web_mode=False,
    download_data=None, on_upload=None,
):

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
            if web_mode:
                st.download_button(
                    "Descargar proyecto", data=download_data or b"",
                    file_name=_browser_filename(project_name),
                    mime="application/json", icon=":material/download:",
                    use_container_width=True,
                )
            else:
                save_pressed = st.button(
                    "Guardar", icon=":material/save:", use_container_width=True
                )
                if save_pressed and on_save:
                    on_save()

        with col_open:
            if web_mode:
                uploaded = st.file_uploader(
                    "Cargar proyecto", type=["cineplan", "cps", "json"],
                    key="browser_project_upload",
                )
                if uploaded is not None and on_upload:
                    upload_id = (
                        uploaded.name, uploaded.size, getattr(uploaded, "file_id", None)
                    )
                    if st.session_state.get("browser_project_upload_id") != upload_id:
                        if on_upload(uploaded):
                            st.session_state.browser_project_upload_id = upload_id
                            st.rerun()
            else:
                open_pressed = st.button(
                    "Abrir", icon=":material/folder_open:", use_container_width=True
                )
                if open_pressed and on_open:
                    on_open()

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
