"""Reusable, browser-independent CinePlan screenplay viewer.

PDF pages are rendered by the PDF.js engine bundled with
``streamlit-pdf-viewer``. No native browser PDF embed, PDF iframe, or PDF data
URL is used here.
"""

from __future__ import annotations

import hashlib
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import pdfplumber
import streamlit as st
from modules.screenplay_layout import (
    FINAL_DRAFT_LETTER,
    compose_screenplay_pdf,
    elements_from_fdx,
    elements_from_text,
)

try:
    from streamlit_pdf_viewer import pdf_viewer
except ImportError:  # requirements.txt installs it on the next normal startup.
    pdf_viewer = None


@dataclass(frozen=True)
class ScreenplayViewerState:
    """Navigation contract for future page, scene, and text synchronization."""

    page: int = 1
    search_text: str = ""
    scene: str | None = None

    def go_to_page(self, page_number: int) -> "ScreenplayViewerState":
        return ScreenplayViewerState(max(1, int(page_number)), self.search_text, self.scene)


@st.cache_data(show_spinner=False)
def _fdx_preview_pdf(content_hash: str, script_text: str, fdx_bytes: bytes | None) -> bytes:
    """Compose an industry-style preview once per unchanged FDX screenplay."""
    del content_hash
    try:
        elements = elements_from_fdx(fdx_bytes) if fdx_bytes else elements_from_text(script_text)
    except (ET.ParseError, ValueError):
        elements = elements_from_text(script_text)
    return compose_screenplay_pdf(elements, FINAL_DRAFT_LETTER)


def _page_count(pdf_bytes: bytes) -> int:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return max(1, len(pdf.pages))


def _set_zoom(state_key: str, value: float | str) -> None:
    st.session_state[state_key] = value


@st.dialog("Visor de guion", width="large")
def _open_reader_window(pdf_bytes: bytes, page: int, zoom: float | str, key: str) -> None:
    """Open a second PDF.js reader surface without invoking a browser PDF plug-in."""
    pdf_viewer(
        input=pdf_bytes, width="100%", height=780, render_text=False,
        resolution_boost=2,
        zoom_level=zoom, viewer_align="center", show_page_separator=True,
        scroll_to_page=page, scroll_behavior="instant", key=f"{key}_window_renderer",
    )


def _render_toolbar(
    pdf_bytes: bytes, filename: str, page: int, key: str
) -> float | str:
    zoom_key = f"{key}_zoom"
    st.session_state.setdefault(zoom_key, "auto")

    fit_width, fit_page, open_window, download = st.columns([1, 1, 1.25, 1], gap="small")
    fit_width.button("Ajustar ancho", key=f"{key}_fit_width", use_container_width=True, on_click=_set_zoom, args=(zoom_key, "auto"))
    fit_page.button("Ajustar página", key=f"{key}_fit_page", use_container_width=True, on_click=_set_zoom, args=(zoom_key, "auto-height"))
    open_clicked = open_window.button(
        "Abrir en nueva ventana", key=f"{key}_open", use_container_width=True,
    )
    download.download_button(
        "Descargar PDF", data=pdf_bytes, file_name=filename,
        mime="application/pdf", key=f"{key}_download", use_container_width=True,
    )
    if open_clicked:
        _open_reader_window(pdf_bytes, page, st.session_state[zoom_key], key)
    return st.session_state[zoom_key]


def render_screenplay_viewer(
    *, source_type: str, original_file_bytes: bytes | None, script_text: str = "",
    filename: str = "guion.pdf", initial_page: int = 1,
    navigation: ScreenplayViewerState | None = None, key: str = "cineplan_screenplay",
) -> bool:
    """Render an original PDF or cached FDX preview with the official engine."""
    source = (source_type or "").strip().upper()
    try:
        if source == "PDF":
            if not original_file_bytes:
                raise ValueError("El PDF original no está disponible en esta sesión.")
            pdf_bytes = original_file_bytes
        elif source == "FDX":
            fingerprint = hashlib.sha256(original_file_bytes or script_text.encode("utf-8")).hexdigest()
            pdf_bytes = _fdx_preview_pdf(fingerprint, script_text, original_file_bytes)
            st.info(
                "Vista previa generada desde un archivo FDX. Este PDF fue generado "
                "automáticamente únicamente para facilitar la lectura del guion dentro de "
                "CinePlan. Debido a las diferencias entre motores de renderizado, el formato "
                "puede variar ligeramente respecto al documento mostrado por Final Draft. "
                "Esta vista previa es una representación visual aproximada del guion original."
            )
        else:
            raise ValueError("No hay un archivo PDF o FDX disponible para previsualizar.")

        if pdf_viewer is None:
            raise RuntimeError("streamlit-pdf-viewer no está instalado.")

        total = _page_count(pdf_bytes)
        requested = navigation.page if navigation else initial_page
        page = max(1, min(total, requested))
        output_name = filename.rsplit(".", 1)[0] + ("_vista_previa.pdf" if source == "FDX" else ".pdf")
        zoom = _render_toolbar(pdf_bytes, output_name, page, key)
        pdf_viewer(
            input=pdf_bytes, width="100%", height=790, render_text=False,
            resolution_boost=2,
            zoom_level=zoom, viewer_align="center", show_page_separator=True,
            scroll_to_page=page, scroll_behavior="instant", key=f"{key}_renderer",
        )
        return True
    except Exception as error:
        st.warning(f"No fue posible iniciar el visor PDF. Se muestra el texto extraído. ({error})")
        st.text_area("Texto del guion", script_text or "No hay texto disponible.", height=690, disabled=True, label_visibility="collapsed")
        return False
