"""Reusable read-only scene strip."""

from html import escape

import streamlit as st

from modules.stripboard.colors import STRIP_SURFACES, get_strip_color
from modules.stripboard.planner_utils import display_value


_SAVED_STRIP_COLORS = {
    "blanco": "#F8FAFC",
    "amarillo": "#FACC15",
    "azul": "#60A5FA",
    "verde": "#4ADE80",
    "rosa": "#F472B6",
    "morado": "#C084FC",
}


def _safe(value):
    return escape(str(value if value is not None else "—"), quote=True)


def _field(label, value, wide=False):
    width = "min-width:190px;flex:2.3;" if wide else "min-width:72px;flex:1;"
    return (
        f'<div style="{width}">'
        f'<div style="font-size:9px;letter-spacing:.08em;text-transform:uppercase;'
        f'color:{STRIP_SURFACES["muted"]};margin-bottom:3px;">{_safe(label)}</div>'
        f'<div style="font-size:12px;color:{STRIP_SURFACES["text"]};font-weight:600;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_safe(value)}</div>'
        '</div>'
    )


def _scene_value(scene, scene_details, *keys, default="—"):
    """Read live scene details first, without persisting a Stripboard copy."""
    value = display_value(scene_details or {}, *keys, default="")
    if str(value).strip():
        return value
    return display_value(scene, *keys, default=default)


def _strip_color(scene, scene_details, scene_type):
    saved_color = _scene_value(
        scene,
        scene_details,
        "Color del Stripboard",
        "Color stripboard",
        "color_stripboard",
        default="",
    )
    color_text = str(saved_color).strip()
    if color_text:
        return _SAVED_STRIP_COLORS.get(color_text.casefold(), color_text)
    return get_strip_color(scene_type)


def render_strip_row(scene, scene_details=None):
    """Render one scene using its live Datos de escena values."""
    scene_type = _scene_value(scene, scene_details, "INT/EXT", default="Especial")
    scene_number = _scene_value(scene, scene_details, "Escena", "Orden")
    heading = _scene_value(
        scene, scene_details, "Encabezado de escena", "Encabezado"
    )
    description = _scene_value(
        scene,
        scene_details,
        "Descripción breve",
        "Descripción",
        "descripcion_escena",
        "descripcion",
        "Descripcion",
        default="",
    )
    fields = (
        _field("Locación", display_value(scene, "Locación", "Locacion"), wide=True),
        _field("Día/Noche", display_value(scene, "Tiempo", "Día/Noche")),
        _field("Página", display_value(scene, "Página", "Pagina")),
        _field("Octavos", display_value(scene, "Octavos")),
        _field("Personajes", display_value(scene, "Personajes"), wide=True),
        _field("Extras", display_value(scene, "Extras")),
        _field("Props", display_value(scene, "Props")),
        _field("VFX", display_value(scene, "VFX")),
        _field("Estado", display_value(scene, "Estado")),
        _field("Notas", display_value(scene, "Notas"), wide=True),
    )
    color = _strip_color(scene, scene_details, scene_type)
    description_html = _safe(description) if str(description).strip() else ""
    html = (
        f'<div class="cine-strip-row" style="display:flex;height:104px;'
        f'background:{STRIP_SURFACES["card"]};border:1px solid {STRIP_SURFACES["border"]};'
        'border-radius:12px;margin:0 0 9px;overflow:hidden;'
        'box-shadow:0 8px 24px rgba(2,6,23,.16);">'
        f'<div aria-label="Color del Stripboard" style="width:7px;flex:0 0 7px;background:{color};"></div>'
        '<div style="display:flex;align-items:center;gap:16px;padding:12px 14px;'
        'min-width:0;overflow-x:hidden;">'
        '<div style="width:270px;min-width:270px;align-self:stretch;display:flex;flex-direction:column;'
        'justify-content:center;overflow:hidden;">'
        f'<div style="font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:{STRIP_SURFACES["accent"]};'
        f'font-weight:750;margin-bottom:3px;">Escena {_safe(scene_number)}</div>'
        f'<div style="font-size:14px;line-height:1.25;color:{STRIP_SURFACES["text"]};font-weight:750;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_safe(scene_type)} · {_safe(heading)}</div>'
        f'<div title="{_safe(description)}" style="height:31px;margin-top:4px;font-size:11px;line-height:15px;'
        f'color:{STRIP_SURFACES["muted"]};font-weight:450;overflow:hidden;overflow-wrap:anywhere;'
        f'display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;">{description_html}</div>'
        '</div>'
        + "".join(fields)
        + '</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)
