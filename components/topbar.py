"""CinePlan's grouped, extensible command bar."""

import streamlit as st

from project.project_paths import safe_default_filename


def _browser_filename(project_name):
    return safe_default_filename(project_name).rsplit(".", 1)[0] + ".cineplan"


def _handle_browser_upload(uploaded, on_upload):
    if uploaded is None or on_upload is None:
        return
    upload_id = (uploaded.name, uploaded.size, getattr(uploaded, "file_id", None))
    if st.session_state.get("browser_project_upload_id") == upload_id:
        return
    if on_upload(uploaded):
        st.session_state.browser_project_upload_id = upload_id
        st.rerun()


def _render_file_commands(
    project_name, on_save, on_open, web_mode, download_data, on_upload,
):
    """Render the Archivo group; storage transport only changes its controls."""
    import_col, open_col, save_col = st.columns(
        [1.05, 1.55 if web_mode else 1.0, 1.9 if web_mode else 1.0], gap="small"
    )

    with import_col:
        if st.button(
            "Importar", icon=":material/upload_file:", width="stretch"
        ):
            st.session_state.show_import_dialog = True

    with open_col:
        if web_mode:
            with st.popover(
                "Cargar proyecto", icon=":material/upload:", width="stretch"
            ):
                uploaded = st.file_uploader(
                    "Seleccionar proyecto",
                    type=["cineplan", "cps", "json"],
                    key="browser_project_upload",
                )
                _handle_browser_upload(uploaded, on_upload)
        elif st.button(
            "Abrir", icon=":material/folder_open:", width="stretch"
        ) and on_open:
            on_open()

    with save_col:
        if web_mode:
            st.download_button(
                "Descargar proyecto",
                data=download_data or b"",
                file_name=_browser_filename(project_name),
                mime="application/json",
                icon=":material/download:",
                width="stretch",
            )
        elif st.button(
            "Guardar", icon=":material/save:", width="stretch"
        ) and on_save:
            on_save()


def _render_tool_commands():
    """Render the Herramientas group."""
    st.button("Config.", icon=":material/settings:", width="stretch")


def _render_account_commands():
    """Render the Usuario group."""
    st.button("Cuenta", icon=":material/account_circle:", width="stretch")


def cine_topbar(
    project_name="Sin proyecto",
    on_save=None,
    on_open=None,
    web_mode=False,
    download_data=None,
    on_upload=None,
):
    """Render stable command groups with reserved capacity for Proyecto actions."""
    with st.container(key="cineplan_command_bar_shell"):
        with st.container(key="cineplan_command_bar"):
            logo_col, commands_col = st.columns([4.1, 6.9], gap="medium")

            with logo_col:
                st.markdown("### 🎬 CinePlan")
                st.caption(
                    "Bienvenido de vuelta, Christopher. Aquí tienes el estado "
                    "general de tu proyecto."
                )

            with commands_col:
                # Stable group slots: Archivo | Proyecto (reserved) |
                # Herramientas | Usuario. New commands can fill the reserved
                # group without changing the command bar's outer structure.
                file_group, project_group, tools_group, account_group = st.columns(
                    [5.1, 0.8, 1.25, 1.0], gap="medium"
                )
                with file_group:
                    _render_file_commands(
                        project_name,
                        on_save,
                        on_open,
                        web_mode,
                        download_data,
                        on_upload,
                    )
                with project_group:
                    st.empty()
                with tools_group:
                    _render_tool_commands()
                with account_group:
                    _render_account_commands()

        st.divider()
