import streamlit as st
import pdfplumber
import pandas as pd
import re
import random
import json
import xml.etree.ElementTree as ET

from html import escape
from io import BytesIO
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from datetime import datetime
from pathlib import Path
from components.ui import (
    cine_header,
    cine_dashboard_header,
    cine_topbar,
    cine_card,
    cine_action_card,
    cine_panel
)
from components.import_dialog import import_dialog
from modules.review_page import render_review_page
from modules.screenplay_viewer import render_screenplay_viewer
from modules.breakdown_page import render_breakdown_page
from modules.breakdown.scene_page import render_scene_page
from modules.breakdown.props_resources import legacy_props_projection, migrate_legacy_props
from modules.breakdown.document_framework import (
    format_excel_worksheet,
    pdf_column_widths,
    scene_color_identity,
)
from modules.breakdown.document_layout import (
    GRID,
    THEME,
    dataframe_pdf as shared_dataframe_pdf,
    pdf_page_callback,
    pdf_scene_accent_commands,
    table_styles as shared_table_styles,
)
try:
    from modules.stripboard_page import render_stripboard_page
except Exception as stripboard_import_error:
    render_stripboard_page = None

from project.project_state import get_dashboard_data, register_recent_activity
from project.project_manager import open_project, save_current_project
from project.workspace_dialog import render_workspace_restore_dialog
from project.workspace_runtime import begin_module, begin_submodule, go_to_dashboard
from project.breakdown_utils import (
    obtener_octavos_finales,
    ensure_cast_structure
)

from project.importer import (
    import_script,
    normalize_octavos_value,
    normalize_scene_octavos_fields,
    normalize_scenes_df_octavos,
    number_to_octavos
)

def load_theme():
    css_folder = Path("assets")

    css_order = [
        "theme.css",
        "sidebar.css",
        "dashboard.css",
        "cards.css",
        "buttons.css",
        "tables.css",
        "panel.css",
        "review.css",
        "stripboard.css"

    ]

    css = ""

    for file in css_order:
        path = css_folder / file

        if path.exists():
            css += path.read_text(encoding="utf-8")
            css += "\n"

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True
    )


st.set_page_config(
    page_title="CinePlan Scheduler",
    layout="wide"
)
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded"
      rel="stylesheet">
""", unsafe_allow_html=True)
load_theme()

if "uploaded_script" not in st.session_state:
    st.session_state.uploaded_script = None

# ---------------------------------------------------------
# ESTADO
# ---------------------------------------------------------

if "scenes_df" not in st.session_state:
    st.session_state.scenes_df = pd.DataFrame()

if "characters_df" not in st.session_state:
    st.session_state.characters_df = pd.DataFrame()

if "script_text" not in st.session_state:
    st.session_state.script_text = ""

if "source_type" not in st.session_state:
    st.session_state.source_type = ""

if "project_info" not in st.session_state:
    st.session_state.project_info = {
        "nombre": "Proyecto sin título",
        "director": "",
        "productor": "",
        "version_guion": ""
    }

for project_session_key, default_value in {
    "current_project_path": "",
    "current_project_filename": "",
    "project_has_been_saved": False,
    "project_id": "",
    "project_created_at": "",
    "project_last_saved": "",
    "project_dirty": False,
    "workspace_restore_pending": False,
    "workspace_pending_context": {},
    "cineplan_workspace_context": {},
    "cineplan_workspace_providers": {},
    "cineplan_workspace_runtime_id": "",
}.items():
    if project_session_key not in st.session_state:
        st.session_state[project_session_key] = default_value

if "nombre_archivo_guion" not in st.session_state:
    st.session_state.nombre_archivo_guion = ""

if "tipo_archivo_guion" not in st.session_state:
    st.session_state.tipo_archivo_guion = ""

if "fecha_importacion_guion" not in st.session_state:
    st.session_state.fecha_importacion_guion = ""

if "version_proyecto_json" not in st.session_state:
    st.session_state.version_proyecto_json = "1.1"

if "recent_activity" not in st.session_state:
    st.session_state.recent_activity = []

if "current_view" not in st.session_state:
    st.session_state.current_view = "dashboard"


# ---------------------------------------------------------
# FUNCIONES
# ---------------------------------------------------------

# ---------------------------------------------------------
# UI / DASHBOARD
# ---------------------------------------------------------

_DASHBOARD_TIPS = (
    ("importar", "Importa versiones de guion con nombres claros para identificar rápidamente cada revisión."),
    ("importar", "Comprueba que el PDF tenga texto seleccionable antes de iniciar la detección de escenas."),
    ("importar", "Conserva una copia del guion original antes de realizar ajustes durante la revisión."),
    ("revision", "Revisa los encabezados de escena antes de corregir personajes y locaciones."),
    ("revision", "Registrar correctamente los octavos mejora la planeación del rodaje."),
    ("revision", "Marca una escena como revisada solamente después de confirmar su encabezado y contenido."),
    ("revision", "Unifica los nombres de personajes para evitar duplicados en Cast y Breakdown."),
    ("revision", "Verifica las locaciones detectadas antes de comenzar el desglose por departamentos."),
    ("breakdown", "Completa primero los datos de escena antes de registrar utilería."),
    ("breakdown", "El Breakdown es la base del Stripboard y del Plan de Rodaje."),
    ("breakdown", "Registra solo los departamentos que realmente intervienen en cada escena."),
    ("cast", "Mantén actualizada la información del reparto antes de generar Hojas de Llamado."),
    ("cast", "Confirma el estado de casting para identificar rápidamente personajes pendientes."),
    ("cast", "Asocia cada personaje con sus escenas para facilitar la coordinación del reparto."),
    ("props", "Distingue entre utilería de mano y decoración para asignar responsabilidades correctamente."),
    ("props", "Documenta la continuidad de los props que cambian, se consumen o se rompen."),
    ("props", "Identifica con anticipación la utilería que requiere medidas especiales de seguridad."),
    ("wardrobe", "Los Looks de vestuario pueden reutilizarse en múltiples escenas."),
    ("wardrobe", "Agrupa vestuario, maquillaje y peinado dentro del mismo Look de continuidad."),
    ("wardrobe", "Describe el estado del personaje cuando afecte vestuario, maquillaje o cabello."),
    ("vfx", "Separa claramente los VFX de los efectos prácticos que deben resolverse durante el rodaje."),
    ("vfx", "Registra la prioridad y seguridad de cada efecto antes de cerrar el Breakdown."),
    ("sonido", "Anota Playback, Room Tone, ADR y Foley cuando sean necesarios para la escena."),
    ("extras", "Define cantidad, acción y responsable para cada grupo de extras de ambiente."),
    ("extras", "Registra al Handler y las necesidades de seguridad cuando participen animales."),
    ("produccion", "Utiliza las Notas de Producción para dejar instrucciones específicas a cada departamento."),
    ("produccion", "Convierte las observaciones generales en instrucciones claras y accionables."),
    ("stripboard", "Revisa continuidad, locación y tiempo dramático antes de ordenar el Stripboard."),
    ("stripboard", "Agrupar escenas por locación puede reducir movimientos de equipo y tiempos de montaje."),
    ("plan", "Considera disponibilidad de reparto, locaciones y luz natural al construir el Plan de Rodaje."),
    ("plan", "Evita jornadas sobrecargadas distribuyendo páginas, octavos y complejidad técnica."),
    ("llamados", "Confirma horarios, contactos y necesidades departamentales antes de emitir Hojas de Llamado."),
    ("exportar", "Revisa la vista previa de cada documento antes de imprimirlo o compartirlo."),
    ("continuidad", "Usa nombres consistentes para que la continuidad pueda seguir elementos entre escenas."),
    ("preproduccion", "Guarda versiones frecuentes del proyecto durante la preproducción."),
    ("preproduccion", "Una información breve y precisa ayuda más al equipo que una observación extensa y ambigua."),
)


def _select_dashboard_tip(dashboard_data):
    """Selecciona un consejo y permite priorizar el contexto del flujo actual."""
    workflow = dashboard_data.get("workflow", {})
    if (
        not dashboard_data.get("script", {}).get("name")
        and not dashboard_data.get("stats", {}).get("scenes")
    ):
        preferred = {"importar"}
    elif workflow.get("revision") == "en_progreso":
        preferred = {"revision"}
    elif workflow.get("breakdown") == "en_progreso":
        preferred = {
            "breakdown", "cast", "props", "wardrobe", "vfx",
            "sonido", "extras", "produccion", "continuidad",
        }
    else:
        preferred = {category for category, _ in _DASHBOARD_TIPS}
    candidates = [tip for category, tip in _DASHBOARD_TIPS if category in preferred]
    return random.choice(candidates)

def render_project_progress(workflow):

    st.markdown("### Flujo de trabajo del proyecto")

    steps = [
        ("importar", "upload", "1", "Importar guion", "PDF / FDX"),
        ("revision", "fact_check", "2", "Revisar", "Escenas, personajes y locaciones"),
        ("breakdown", "calendar_month", "3", "Breakdown", "Desglose por departamentos"),
        ("stripboard", "grid_view", "4", "Stripboard", "Orden de filmación"),
        ("plan_rodaje", "event", "5", "Plan de rodaje", "Calendario"),
        ("hojas_llamado", "description", "6", "Hojas de llamado", "Call Sheets"),
    ]

    cols = st.columns(len(steps))

    for col, (key, icon_name, number, title, subtitle) in zip(cols, steps):

        status = workflow.get(key, "bloqueado")

        if status == "completado":
            status_label = "Completado"
            status_color = "#22c55e"
        elif status == "en_progreso":
            status_label = "En progreso"
            status_color = "#f8b400"
        else:
            status_label = "Bloqueado"
            status_color = "#94a3b8"

        with col:
            card_html = f"""<div style="border:1px solid rgba(148,163,184,.20); border-radius:16px; padding:18px; min-height:165px; background:rgba(15,23,42,.75);">
<div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
<span class="material-symbols-rounded" style="font-size:30px; color:{status_color};">{icon_name}</span>
<span style="font-size:22px; font-weight:700; color:white;">{number}</span>
</div>
<div style="font-size:18px; font-weight:700; color:white; margin-bottom:6px;">{title}</div>
<div style="font-size:12px; color:#94a3b8; min-height:34px;">{subtitle}</div>
<div style="margin-top:18px; font-size:13px; font-weight:600; color:{status_color};">{status_label}</div>
</div>"""

            st.markdown(card_html, unsafe_allow_html=True)

            
def dataframe_to_excel(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Tabla")
        format_excel_worksheet(writer.sheets["Tabla"])

    output.seek(0)
    return output


def dataframe_to_pdf(df, title="Reporte CinePlan", project_info=None):
    project_info = project_info or st.session_state.get("project_info", {})
    columns = list(df.columns)
    return shared_dataframe_pdf(
        df, title, pdf_column_widths(columns, THEME.usable_width, df.to_dict(orient="records")),
        project=project_info.get("nombre", "Proyecto"),
        version=project_info.get("version_guion", project_info.get("versión_guion", "—")),
    )

def generate_breakdown_pdf(numero_escena, escena_info, project_info, sections=None):
    """Genera PDF estilo hoja de breakdown con bloques dinámicos de ancho completo o mitad de página.

    sections: dict (titulo -> DataFrame|dict|str). Solo se incluyen secciones no vacías.
    """
    from reportlab.platypus import Paragraph, Spacer, Table as RLTable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    left_margin = THEME.margin
    right_margin = THEME.margin
    top_margin = GRID.pdf_content_top
    bottom_margin = GRID.pdf_content_bottom
    page_width = landscape(letter)[0] - left_margin - right_margin
    half_block_width = page_width / 2
    half_table_inner_width = half_block_width - GRID.box_padding * 2

    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        rightMargin=right_margin,
        leftMargin=left_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Heading1'], fontSize=14)
    meta_style = ParagraphStyle('meta', parent=styles['Normal'], fontSize=8)
    block_title = ParagraphStyle(
        'block_title', parent=styles['Heading3'], fontName=THEME.font_bold,
        fontSize=GRID.title_size, leading=GRID.title_leading,
        spaceBefore=GRID.section_gap, spaceAfter=GRID.content_gap / 2,
    )
    normal_small = ParagraphStyle('normal_small', parent=styles['Normal'], fontSize=8)

    story = []

    # Scene header block (full width)
    scene_header = [
        [Paragraph(f"<b>ESCENA {numero_escena} - {escena_info.get('Encabezado de escena','-')}</b>", block_title)],
        [Paragraph(f"Locación: {escena_info.get('Locación','-')}  |  INT/EXT: {escena_info.get('INT/EXT','-')}  |  Tiempo: {escena_info.get('Tiempo','-')}  |  Octavos: {escena_info.get('Octavos','-')}", normal_small)],
        [Paragraph(f"Color stripboard: {escena_info.get('Color stripboard','-')}", normal_small)]
    ]
    scene_accent = scene_color_identity(escena_info)
    sh = RLTable(scene_header, colWidths=[page_width])
    sh.setStyle(TableStyle([
        *pdf_scene_accent_commands(scene_accent.hex),
        ('BACKGROUND',(0,0),(0,0),colors.HexColor('#f7f7f7')),
        ('LEFTPADDING',(0,0),(-1,-1),GRID.box_padding),
        ('RIGHTPADDING',(0,0),(-1,-1),GRID.box_padding),
        ('TOPPADDING',(0,0),(-1,-1),GRID.box_padding),
        ('BOTTOMPADDING',(0,0),(-1,-1),GRID.box_padding),
    ]))
    story.append(sh)
    story.append(Spacer(1, GRID.section_gap))

    # Descripción y Notas (full width)
    descripcion = escena_info.get('Descripción') or escena_info.get('descripcion_escena') or escena_info.get('descripcion') or escena_info.get('Descripcion') or ''
    notas = escena_info.get('Notas de escena') or escena_info.get('notas_escena') or escena_info.get('notas') or ''

    if descripcion:
        story.append(Paragraph('<b>DESCRIPCIÓN</b>', block_title))
        story.append(Paragraph(descripcion, normal_small))
        story.append(Spacer(1, GRID.section_gap))

    if notas:
        story.append(Paragraph('<b>NOTAS</b>', block_title))
        story.append(Paragraph(notas, normal_small))
        story.append(Spacer(1, GRID.section_gap))

    def has_value(value):
        if value is None:
            return False
        if isinstance(value, pd.DataFrame):
            return not value.empty
        return bool(value)

    def make_paragraph_table(df, max_width):
        if df.empty:
            return None

        columns = list(df.columns)
        col_widths = pdf_column_widths(columns, max_width, df.to_dict(orient="records"))
        cell_style, header_cell_style = shared_table_styles()
        data = [[Paragraph(escape(str(col)), header_cell_style) for col in columns]]

        for row in df.fillna("").astype(str).values.tolist():
            data.append([Paragraph(escape(str(cell)), cell_style) for cell in row])

        tbl = RLTable(data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(THEME.black)),
            ('GRID', (0, 0), (-1, -1), GRID.border_width, colors.HexColor(THEME.border)),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), GRID.table_padding_x),
            ('RIGHTPADDING', (0, 0), (-1, -1), GRID.table_padding_x),
            ('TOPPADDING', (0, 0), (-1, -1), GRID.table_padding_y),
            ('BOTTOMPADDING', (0, 0), (-1, -1), GRID.table_padding_y),
        ]))
        return tbl

    # Prepare non-empty section blocks
    blocks = []
    if isinstance(sections, dict):
        for title, content in sections.items():
            if not has_value(content):
                continue

            block_story = []
            block_story.append([Paragraph(f'<b>{title}</b>', block_title)])

            max_columns = 1
            show_full_width = False

            if isinstance(content, dict):
                for sub, subcontent in content.items():
                    if isinstance(subcontent, pd.DataFrame) and not subcontent.empty:
                        columns = subcontent.shape[1]
                        max_columns = max(max_columns, columns)
                        if columns >= 4:
                            show_full_width = True
                        sub_max_width = half_table_inner_width if columns <= 3 else page_width - 8
                        tbl = make_paragraph_table(subcontent, sub_max_width)
                        if tbl:
                            block_story.append([Paragraph(f'<b>{sub}</b>', normal_small)])
                            block_story.append([tbl])
                    else:
                        if has_value(subcontent):
                            block_story.append([Paragraph(f'<b>{sub}:</b> {str(subcontent)}', normal_small)])
            elif isinstance(content, pd.DataFrame):
                columns = content.shape[1]
                max_columns = columns
                if columns >= 4:
                    show_full_width = True
                tbl_max_width = half_table_inner_width if columns <= 3 else page_width - 8
                tbl = make_paragraph_table(content, tbl_max_width)
                if tbl:
                    block_story.append([tbl])
            else:
                block_story.append([Paragraph(str(content), normal_small)])

            nested_width = page_width if show_full_width else half_block_width
            nested = RLTable(block_story, colWidths=[nested_width])
            nested.setStyle(TableStyle([
                ('BOX',(0,0),(-1,-1),GRID.border_width,colors.HexColor(THEME.border)),
                ('LEFTPADDING',(0,0),(-1,-1),GRID.box_padding),
                ('RIGHTPADDING',(0,0),(-1,-1),GRID.box_padding),
                ('TOPPADDING',(0,0),(-1,-1),GRID.box_padding),
                ('BOTTOMPADDING',(0,0),(-1,-1),GRID.box_padding),
            ]))
            blocks.append((nested, nested_width, max_columns))

    if blocks:
        table_data = []
        span_rows = []
        row_index = 0
        i = 0

        while i < len(blocks):
            left, left_width, left_columns = blocks[i]
            if i + 1 < len(blocks):
                right, right_width, right_columns = blocks[i+1]
                if left_columns <= 3 and right_columns <= 3:
                    table_data.append([left, right])
                    row_index += 1
                    i += 2
                    continue

            table_data.append([left, ''])
            span_rows.append(row_index)
            row_index += 1
            i += 1

        main_table = RLTable(table_data, colWidths=[half_block_width, half_block_width])
        main_style = [('VALIGN',(0,0),(-1,-1),'TOP')]
        for row in span_rows:
            main_style.append(('SPAN',(0,row),(1,row)))
        main_table.setStyle(TableStyle(main_style))
        story.append(main_table)

    callback = pdf_page_callback(
        "HOJA DE BREAKDOWN", project_info.get("nombre", "Proyecto"),
        project_info.get("version_guion", project_info.get("versión_guion", "—")),
    )
    doc.build(story, onFirstPage=callback, onLaterPages=callback)
    output.seek(0)
    return output

def octavos_to_number(value):
    value = str(value).strip()

    if not value:
        return 0

    try:
        if " " in value:
            pages, fraction = value.split(" ")
            num, den = fraction.split("/")
            return int(pages) * 8 + int(num)

        if "/" in value:
            num, den = value.split("/")
            return int(num)

        return int(value) * 8
    except:
        return 0


def obtener_octavos_finales(escena):
    
    if escena is None:
        return ""

    manual = normalize_octavos_value(escena.get("octavos_manual", ""))
    final = normalize_octavos_value(escena.get("octavos_final", ""))
    auto = normalize_octavos_value(escena.get("octavos_auto", ""))
    direct = normalize_octavos_value(escena.get("Octavos", ""))
    legacy = normalize_octavos_value(escena.get("octavos", ""))

    if manual:
        return manual
    if final:
        return final
    if auto:
        return auto
    if direct:
        return direct
    if legacy:
        return legacy
    return ""


def serialize_nested_value(value):
    if isinstance(value, pd.DataFrame):
        return value.fillna("").to_dict(orient="records")
    if isinstance(value, pd.Series):
        return value.fillna("").to_dict()
    if isinstance(value, dict):
        return {
            key: serialize_nested_value(val)
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [serialize_nested_value(item) for item in value]
    if isinstance(value, tuple):
        return [serialize_nested_value(item) for item in value]
    if isinstance(value, set):
        return [serialize_nested_value(item) for item in value]
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        return str(value)


def find_unserializable_values(value, path="root"):
    non_serializable = []

    if isinstance(value, dict):
        for key, val in value.items():
            non_serializable.extend(
                find_unserializable_values(val, f"{path}.{key}")
            )
        return non_serializable

    if isinstance(value, list):
        for index, item in enumerate(value):
            non_serializable.extend(
                find_unserializable_values(item, f"{path}[{index}]")
            )
        return non_serializable

    if isinstance(value, pd.DataFrame) or isinstance(value, pd.Series):
        non_serializable.append((path, type(value).__name__))
        return non_serializable

    try:
        json.dumps(value, ensure_ascii=False)
    except TypeError:
        non_serializable.append((path, type(value).__name__))

    return non_serializable


def serialize_project_data(data):
    serialized = serialize_nested_value(data)
    invalid = find_unserializable_values(serialized)

    if invalid:
        for path, type_name in invalid:
            serialized = serialize_nested_value(serialized)
        invalid = find_unserializable_values(serialized)
        if invalid:
            raise TypeError(
                "JSON serialization failed for project_data. "
                f"Invalid entries: {invalid}"
            )

    return serialized


def deserialize_dataframe_structure(value):
    if isinstance(value, dict):
        return {
            key: deserialize_dataframe_structure(val)
            for key, val in value.items()
        }
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            return pd.DataFrame(value)
        return value
    return value


def get_default_validation_checklist():
    return pd.DataFrame([
        {"Área": "Guion", "Elemento a revisar": "Guion importado correctamente", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Guion", "Elemento a revisar": "Texto extraído revisado", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Guion", "Elemento a revisar": "Formato general revisado", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Escenas", "Elemento a revisar": "Escenas detectadas revisadas", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Escenas", "Elemento a revisar": "Orden de escenas revisado", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Escenas", "Elemento a revisar": "Encabezados revisados", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Locaciones", "Elemento a revisar": "Locaciones detectadas revisadas", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Locaciones", "Elemento a revisar": "Locaciones manuales corregidas", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Locaciones", "Elemento a revisar": "Escenas sin locación revisadas", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Personajes", "Elemento a revisar": "Personajes detectados revisados", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Personajes", "Elemento a revisar": "Nombres corregidos", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Personajes", "Elemento a revisar": "Personajes por escena revisados", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Octavos", "Elemento a revisar": "Octavos automáticos revisados", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Octavos", "Elemento a revisar": "Octavos manuales corregidos cuando aplica", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Octavos", "Elemento a revisar": "Octavos finales actualizados", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Preparación para Breakdown", "Elemento a revisar": "Escenas listas para breakdown", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Preparación para Breakdown", "Elemento a revisar": "Información mínima completa", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""},
        {"Área": "Preparación para Breakdown", "Elemento a revisar": "Observaciones de revisión cerradas", "Estado": "Pendiente", "Comentarios": "", "Última actualización": ""}
    ])


def ensure_cast_structure(numero_escena, personajes_detectados=""):

    cast_columns = [
        "ID",
        "Personaje",
        "Actor/Actriz",
        "Tipo",
        "Notas"
    ]

    stunts_columns = [
        "ID",
        "Personaje sustituido",
        "Doble / Stunt",
        "Acción",
        "Nivel de riesgo",
        "Notas"
    ]

    extras_atmosfera_columns = [
        "ID",
        "Tipo de extra",
        "Cantidad",
        "Vestuario especial",
        "Notas"
    ]

    extras_dialogo_columns = [
        "ID",
        "Personaje / Extra",
        "Diálogo breve",
        "Cantidad",
        "Notas"
    ]

    if "breakdown_cast_data" not in st.session_state:
        st.session_state.breakdown_cast_data = {}

    if numero_escena not in st.session_state.breakdown_cast_data:
        cast_rows = []

        if personajes_detectados.strip():
            personajes_lista = [
                p.strip()
                for p in personajes_detectados.split(",")
                if p.strip()
            ]

            for personaje in personajes_lista:
                personaje_limpio = re.sub(
                    r"^#\d+\s*",
                    "",
                    personaje
                ).strip()

                cast_rows.append({
                    "ID": len(cast_rows) + 1,
                    "Personaje": personaje_limpio,
                    "Actor/Actriz": "",
                    "Tipo": "Principal",
                    "Notas": ""
                })

        st.session_state.breakdown_cast_data[numero_escena] = {
            "cast": pd.DataFrame(cast_rows, columns=cast_columns),
            "stunts": pd.DataFrame(columns=stunts_columns),
            "extras_atmosfera": pd.DataFrame(columns=extras_atmosfera_columns),
            "extras_dialogo": pd.DataFrame(columns=extras_dialogo_columns)
        }

    estructura = st.session_state.breakdown_cast_data[numero_escena]

    required_tables = {
        "cast": cast_columns,
        "stunts": stunts_columns,
        "extras_atmosfera": extras_atmosfera_columns,
        "extras_dialogo": extras_dialogo_columns
    }

    for key, columns in required_tables.items():

        if key not in estructura:
            estructura[key] = pd.DataFrame(columns=columns)

        if not isinstance(estructura[key], pd.DataFrame):
            estructura[key] = pd.DataFrame(estructura[key])

        for column in columns:
            if column not in estructura[key].columns:
                estructura[key][column] = ""

        estructura[key] = estructura[key][columns].fillna("").copy()

    st.session_state.breakdown_cast_data[numero_escena] = estructura
def ensure_props_structure(numero_escena):

    props_mano_columns = [
        "ID",
        "Prop",
        "Personaje que lo usa",
        "Cantidad",
        "Continuidad",
        "Notas"
    ]

    set_dressing_columns = [
        "ID",
        "Elemento",
        "Área / Set",
        "Cantidad",
        "Notas"
    ]

    props_especiales_columns = [
        "ID",
        "Prop especial",
        "FX asociado",
        "Responsable",
        "Notas"
    ]

    utileria_riesgo_columns = [
        "ID",
        "Elemento",
        "Tipo",
        "Seguridad requerida",
        "Responsable",
        "Notas"
    ]

    if "breakdown_props_data" not in st.session_state:
        st.session_state.breakdown_props_data = {}

    if numero_escena not in st.session_state.breakdown_props_data:
        st.session_state.breakdown_props_data[numero_escena] = {}

    estructura = st.session_state.breakdown_props_data[numero_escena]

    required_tables = {
        "props_mano": props_mano_columns,
        "set_dressing": set_dressing_columns,
        "props_especiales": props_especiales_columns,
        "utileria_riesgo": utileria_riesgo_columns
    }

    for key, columns in required_tables.items():

        if key not in estructura:
            estructura[key] = pd.DataFrame(columns=columns)

        if not isinstance(estructura[key], pd.DataFrame):
            estructura[key] = pd.DataFrame(estructura[key])

        for column in columns:
            if column not in estructura[key].columns:
                estructura[key][column] = ""

        estructura[key] = estructura[key][columns].fillna("").copy()

    st.session_state.breakdown_props_data[numero_escena] = estructura

def project_to_json():

    scenes_records = []

    if (
        "scenes_df" in st.session_state
        and not st.session_state.scenes_df.empty
    ):
        scenes_records = (
            st.session_state.scenes_df
            .fillna("")
            .to_dict(orient="records")
        )
        normalized_records = []
        for record in scenes_records:
            normalized_octavos = normalize_scene_octavos_fields(record).to_dict()
            normalized_records.append({
                **record,
                **normalized_octavos,
                "octavos": normalized_octavos["Octavos"]
            })
        scenes_records = normalized_records

    characters_records = []

    if (
        "characters_df" in st.session_state
        and not st.session_state.characters_df.empty
    ):
        characters_records = (
            st.session_state.characters_df
            .fillna("")
            .to_dict(orient="records")
        )

    manual_locations_records = []

    if (
        "manual_locations_df" in st.session_state
        and not st.session_state.manual_locations_df.empty
    ):
        manual_locations_records = (
            st.session_state.manual_locations_df
            .fillna("")
            .to_dict(orient="records")
        )

    explicit_state_keys = {
        "project_info",
        "script_text",
        "source_type",
        "scenes_df",
        "characters_df",
        "breakdown_scene_data",
        "breakdown_cast_data",
        "breakdown_props_data",
        "breakdown_resource_store",
        "manual_locations_df",
        "breakdown_wardrobe_makeup_data",
        "breakdown_vfx_sound_data",
        "breakdown_extras_data",
        "breakdown_production_notes_data",
        "validation_checklist",
        "recent_activity",
        "nombre_archivo_guion",
        "tipo_archivo_guion",
        "fecha_importacion_guion",
        "version_proyecto_json",
        "last_uploaded_file_id",
        "_dashboard_project_signature",
        "_dashboard_workflow_snapshot",
        "screenplay_source_bytes",
        "current_project_path",
        "current_project_filename",
        "project_has_been_saved",
        "project_id",
        "project_created_at",
        "project_last_saved",
        "project_dirty",
        "workspace_restore_pending",
        "workspace_pending_context",
        "cineplan_workspace_context",
        "cineplan_workspace_providers",
        "cineplan_workspace_runtime_id",
        "review_workspace_tab",
        "breakdown_workspace_tab",
    }

    extra_state = {
        key: serialize_nested_value(value)
        for key, value in st.session_state.items()
        if key not in explicit_state_keys
    }

    project_data = {
        "version_proyecto_json": st.session_state.get("version_proyecto_json", "1.1"),
        "nombre_archivo_guion": st.session_state.get("nombre_archivo_guion", ""),
        "tipo_archivo_guion": st.session_state.get("tipo_archivo_guion", ""),
        "fecha_importacion_guion": st.session_state.get("fecha_importacion_guion", ""),
        "project_info": st.session_state.project_info,
        "script_text": st.session_state.script_text,
        "source_type": st.session_state.source_type,
        "scenes": scenes_records,
        "characters": characters_records,
        "manual_locations_df": manual_locations_records,
        "breakdown_scene_data": serialize_nested_value(st.session_state.get("breakdown_scene_data", {})),
        "breakdown_cast_data": {
            escena: {
                categoria: tabla.fillna("").to_dict(orient="records")
                for categoria, tabla in datos.items()
            }
            for escena, datos in st.session_state.get("breakdown_cast_data", {}).items()
        },
        "breakdown_props_data": {
            escena: {
                categoria: tabla.fillna("").to_dict(orient="records")
                for categoria, tabla in datos.items()
            }
            for escena, datos in st.session_state.get("breakdown_props_data", {}).items()
        },
        "breakdown_resource_store": serialize_nested_value(
            st.session_state.get("breakdown_resource_store", {})
        ),
        "breakdown_wardrobe_makeup_data": serialize_nested_value(
            st.session_state.get("breakdown_wardrobe_makeup_data", {})
        ),
        "breakdown_vfx_sound_data": serialize_nested_value(
            st.session_state.get("breakdown_vfx_sound_data", {})
        ),
        "breakdown_extras_data": serialize_nested_value(
            st.session_state.get("breakdown_extras_data", {})
        ),
        "breakdown_production_notes_data": serialize_nested_value(
            st.session_state.get("breakdown_production_notes_data", {})
        ),
        "validation_checklist": serialize_nested_value(
            st.session_state.get("validation_checklist", get_default_validation_checklist())
        ),
        "recent_activity": serialize_nested_value(
            st.session_state.get("recent_activity", [])[:10]
        ),
        "extra_state": extra_state
    }

    project_data = serialize_project_data(project_data)

    return json.dumps(
        project_data,
        ensure_ascii=False,
        indent=4
    ).encode("utf-8")


def load_project_from_json(json_file):

    data = json.load(json_file)

    st.session_state.project_info = data.get(
        "project_info",
        {
            "nombre": "Proyecto sin título",
            "director": "",
            "productor": "",
            "version_guion": ""
        }
    )

    st.session_state.script_text = data.get("script_text", "")
    # Saved projects keep their historical JSON schema; never reuse a PDF from
    # a previously open project when the source document is not embedded.
    st.session_state.pop("screenplay_source_bytes", None)
    st.session_state.source_type = data.get("source_type", "Proyecto JSON")
    st.session_state.nombre_archivo_guion = data.get("nombre_archivo_guion", "")
    st.session_state.tipo_archivo_guion = data.get("tipo_archivo_guion", "")
    st.session_state.fecha_importacion_guion = data.get("fecha_importacion_guion", "")
    st.session_state.version_proyecto_json = data.get("version_proyecto_json", "1.1")
    loaded_activity = data.get("recent_activity", [])
    st.session_state.recent_activity = (
        loaded_activity[:10] if isinstance(loaded_activity, list) else []
    )

    st.session_state.scenes_df = normalize_scenes_df_octavos(
        pd.DataFrame(data.get("scenes", []))
    )
    st.session_state.characters_df = pd.DataFrame(data.get("characters", []))

    st.session_state.manual_locations_df = pd.DataFrame(
        data.get("manual_locations_df", [])
    )

    st.session_state.breakdown_scene_data = deserialize_dataframe_structure(
        data.get("breakdown_scene_data", {})
    )

    breakdown_cast_loaded = data.get(
        "breakdown_cast_data",
        {}
    )

    st.session_state.breakdown_cast_data = {
        escena: {
            categoria: pd.DataFrame(tabla)
            for categoria, tabla in datos.items()
        }
        for escena, datos in breakdown_cast_loaded.items()
    }

    breakdown_props_loaded = data.get(
        "breakdown_props_data",
        {}
    )

    st.session_state.breakdown_props_data = {
        escena: {
            categoria: pd.DataFrame(tabla)
            for categoria, tabla in datos.items()
        }
        for escena, datos in breakdown_props_loaded.items()
    }

    loaded_resource_store = data.get("breakdown_resource_store")
    scene_locations = {
        str(row.get("Escena", "")): row.get("Locación", row.get("LocaciÃ³n", ""))
        for row in data.get("scenes", []) if isinstance(row, dict)
    }
    st.session_state.breakdown_resource_store = migrate_legacy_props(
        breakdown_props_loaded,
        store=loaded_resource_store if isinstance(loaded_resource_store, dict) else None,
        scene_locations=scene_locations,
    )
    st.session_state.breakdown_props_data = legacy_props_projection(
        st.session_state.breakdown_resource_store
    )

    st.session_state.breakdown_wardrobe_makeup_data = deserialize_dataframe_structure(
        data.get("breakdown_wardrobe_makeup_data", {})
    )

    st.session_state.breakdown_vfx_sound_data = deserialize_dataframe_structure(
        data.get("breakdown_vfx_sound_data", {})
    )

    st.session_state.breakdown_extras_data = deserialize_dataframe_structure(
        data.get("breakdown_extras_data", {})
    )

    st.session_state.breakdown_production_notes_data = deserialize_dataframe_structure(
        data.get("breakdown_production_notes_data", {})
    )

    if data.get("validation_checklist") is not None:
        st.session_state.validation_checklist = pd.DataFrame(
            data.get("validation_checklist", [])
        ).fillna("").copy()

    for key, value in data.get("extra_state", {}).items():
        if key not in {
            "project_info",
            "script_text",
            "source_type",
            "scenes_df",
            "characters_df",
            "breakdown_scene_data",
            "breakdown_cast_data",
            "breakdown_props_data",
            "breakdown_resource_store",
            "manual_locations_df",
            "breakdown_wardrobe_makeup_data",
            "breakdown_vfx_sound_data",
            "breakdown_extras_data",
            "breakdown_production_notes_data",
            "validation_checklist",
            "recent_activity",
            "nombre_archivo_guion",
            "tipo_archivo_guion",
            "fecha_importacion_guion",
            "version_proyecto_json",
            "last_uploaded_file_id",
            "_dashboard_project_signature",
            "_dashboard_workflow_snapshot",
            "current_project_path",
            "current_project_filename",
            "project_has_been_saved",
            "project_id",
            "project_created_at",
            "project_last_saved",
            "project_dirty",
            "workspace_restore_pending",
            "workspace_pending_context",
            "cineplan_workspace_context",
            "cineplan_workspace_providers",
            "cineplan_workspace_runtime_id",
            "review_workspace_tab",
            "breakdown_workspace_tab",
        }:
            st.session_state[key] = value

    if "validation_checklist" in st.session_state and not isinstance(
        st.session_state.validation_checklist, pd.DataFrame
    ):
        st.session_state.validation_checklist = pd.DataFrame(
            st.session_state.validation_checklist
        ).fillna("").copy()

    st.session_state._dashboard_project_signature = tuple(
        str(st.session_state.project_info.get(key, "")).strip()
        for key in ("nombre", "director", "productor", "version_guion")
    )
    st.session_state.pop("_dashboard_workflow_snapshot", None)
    register_recent_activity(
        "Proyecto cargado",
        st.session_state.project_info.get("nombre", "Proyecto sin título"),
        "upload_file", "proyecto",
    )
# =========================================================
# TOP BAR
# =========================================================

cine_topbar(
    project_name=st.session_state.project_info.get(
        "nombre",
        "Sin proyecto"
    ),
    on_save=lambda: save_current_project(project_to_json),
    on_open=lambda: open_project(load_project_from_json),
)
render_workspace_restore_dialog()
# =========================================================
# IMPORT DIALOG
# =========================================================

if "show_import_dialog" not in st.session_state:
    st.session_state.show_import_dialog = False

if st.session_state.show_import_dialog:
    import_dialog()

# Procesar el archivo seleccionado
if st.session_state.uploaded_script is not None:
    # Keep the original upload in session memory for the reusable screenplay viewer.
    # It is deliberately excluded from project JSON to preserve the existing schema.
    st.session_state.screenplay_source_bytes = st.session_state.uploaded_script.getvalue()
    imported_ok = import_script(st.session_state.uploaded_script)

    if imported_ok:
        register_recent_activity(
            "Guion importado",
            st.session_state.get("nombre_archivo_guion", "Guion del proyecto"),
            "description", "guion",
        )
        st.session_state.uploaded_script = None
        st.session_state.show_import_dialog = False
        st.session_state.current_view = "modules"

        st.success("Guion importado correctamente.")
        st.rerun()

    else:
        st.session_state.uploaded_script = None
        st.session_state.show_import_dialog = False

        st.error("No se pudo importar el guion.")
# El Dashboard es la fuente única para el avance principal y lateral.
dashboard = get_dashboard_data()

# ---------------------------------------------------------
# SIDEBAR / NAVEGACIÓN
# ---------------------------------------------------------

with st.sidebar:

    st.markdown("# 🎬 CinePlan")
    st.caption("Scheduler")

    st.markdown("---")

    if st.button(
        "Inicio",
        icon=":material/home:",
        use_container_width=True
    ):
        go_to_dashboard()
        st.rerun()

    st.markdown("### Proyecto")

    nombre = st.session_state.project_info.get(
        "nombre",
        "Sin proyecto"
    )

    st.caption(nombre)

    st.markdown("---")

    st.markdown("### Flujo de trabajo")

    if st.button(
        "Importar y revisar",
        icon=":material/fact_check:",
        use_container_width=True
    ):
        begin_module("Importar y revisar")
        begin_submodule("Proyecto")
        st.session_state.current_view = "modules"
        st.session_state.main_menu = "1. Importar y analizar guion"
        st.rerun()

    if st.button(
        "Breakdown",
        icon=":material/calendar_month:",
        use_container_width=True
    ):
        begin_module("Breakdown")
        begin_submodule("Datos de escena")
        st.session_state.current_view = "modules"
        st.session_state.main_menu = "2. Breakdown"
        st.rerun()

    if st.button(
        "Stripboard",
        icon=":material/view_agenda:",
        use_container_width=True
    ):
        begin_module("Stripboard")
        begin_submodule("Diseñar Stripboard")
        st.session_state.current_view = "modules"
        st.session_state.main_menu = "3. Stripboard"
        st.rerun()

    st.button(
        "Rodaje",
        icon=":material/event:",
        use_container_width=True,
        disabled=True
    )

    st.button(
        "Llamados",
        icon=":material/description:",
        use_container_width=True,
        disabled=True
    )

    st.markdown("---")

    st.caption("Progreso")

    st.progress(dashboard["progress"] / 100)

    st.caption(dashboard["progress_caption"])

# ---------------------------------------------------------
# PÁGINA DE INICIO
# ---------------------------------------------------------
if st.session_state.current_view == "dashboard":
    if not st.session_state.get("workspace_restore_pending", False):
        begin_module("Proyecto")
        begin_submodule("Dashboard")
    cine_dashboard_header(
    project_name=dashboard["project"]["name"],
    director_name=dashboard["project"]["director"],
    project_type="Preproducción cinematográfica",
    script_name=dashboard["script"]["name"] or "Sin guion importado",
    script_type=dashboard["script"]["type"] or "-",
    imported_date=dashboard["script"]["date"][:10] if dashboard["script"]["date"] else "-",
    scenes_count=dashboard["stats"]["scenes"],
    characters_count=dashboard["stats"]["characters"],
    locations_count=dashboard["stats"]["locations"],
    progress=dashboard["progress"],
    next_step=dashboard["next_step"]
    
)
    
    render_project_progress(
    workflow=dashboard["workflow"]
)

    st.markdown(
        "Planifica toda la preproducción de tu proyecto cinematográfico desde un único lugar."
    )

    st.divider()

    col_stats, col_activity, col_actions = st.columns([1, 1, 1])

    with col_stats:
        with cine_panel(
            title="Estadísticas del proyecto",
            subtitle="Resumen general",
            panel_class="cine-dashboard-panel"
             
        ):
            st.markdown("""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
                <span class="material-symbols-rounded" style="font-size:22px;color:#f8b400;">analytics</span>
                <span style="font-size:18px;font-weight:700;">Estadísticas del proyecto</span>
            </div>
            """, unsafe_allow_html=True)

            with st.container(height=330, border=False):
                s1, s2, s3 = st.columns(3)

                with s1:
                    st.metric("Escenas", dashboard["stats"]["scenes"])

                with s2:
                    st.metric("Personajes", dashboard["stats"]["characters"])

                with s3:
                    st.metric("Locaciones", dashboard["stats"]["locations"])

                st.markdown("#### Resumen del breakdown")
                st.write(f'**Octavos:** {dashboard["stats"]["total_eighths"]}')
                st.write(f'**Duración estimada:** {dashboard["stats"]["estimated_duration"]}')
                st.write(f'**Avance:** {dashboard["progress"]}%')


    with col_activity:
        with cine_panel(
            title="Actividad reciente",
            subtitle="Últimos movimientos",
            panel_class="cine-dashboard-panel"
            
        ):
            st.markdown("""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
                <span class="material-symbols-rounded" style="font-size:22px;color:#f8b400;">history</span>
                <span style="font-size:18px;font-weight:700;">Actividad reciente</span>
            </div>
            """, unsafe_allow_html=True)

            activity_cards = []

            for item in dashboard["recent_activity"]:
                icon = item.get("icon", "history")
                title = item.get("title", "-")
                description = item.get("detail", item.get("description", ""))
                timestamp = item.get("time", "-")

                card_html = (
                    '<div class="activity-card" style="padding:8px 2px;'
                    'border-bottom:1px solid rgba(148,163,184,.15);'
                    'min-width:0;overflow-wrap:anywhere;">'
                    '<span class="material-symbols-rounded" style="font-size:18px;'
                    f'color:#f8b400;vertical-align:middle;">{icon}</span>'
                    f'<strong>{title}</strong><br>'
                    f'<span style="font-size:12px;color:#cbd5e1;">{description}</span><br>'
                    f'<span style="font-size:12px;color:#94a3b8;">{timestamp}</span>'
                    '</div>'
                )
                activity_cards.append(card_html)

            if not activity_cards:
                activity_cards.append(
                    '<div class="activity-card" style="padding:14px;border-radius:10px;'
                    'background:rgba(59,130,246,.10);color:#cbd5e1;">'
                    'Todavía no hay actividad registrada.'
                    '</div>'
                )

            final_html = (
                '<div style="height:330px;overflow-y:auto;overflow-x:hidden;'
                'scroll-behavior:smooth;overscroll-behavior:contain;'
                'border:1px solid rgba(148,163,184,.12);border-radius:12px;'
                'padding:0 10px;box-sizing:border-box;">'
                + "".join(activity_cards)
                + '</div>'
            )
            st.markdown(final_html, unsafe_allow_html=True)


    with col_actions:
        with cine_panel(
            title="Acciones rápidas",
            subtitle="Atajos del proyecto",
            panel_class="cine-dashboard-panel"
            
        ):
            st.markdown("""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
                <span class="material-symbols-rounded" style="font-size:22px;color:#f8b400;">bolt</span>
                <span style="font-size:18px;font-weight:700;">Acciones rápidas</span>
            </div>
            """, unsafe_allow_html=True)

            with st.container(height=330, border=False):
                a1, a2 = st.columns(2)

                with a1:
                    cine_action_card("Importar Guion", "PDF / FDX", "upload", "Iniciar")
                    cine_action_card("Breakdown", "Agregar elementos", "calendar_month", "Abrir")
                    cine_action_card("Plan de Rodaje", "Calendario y días", "event", "Planear")

                with a2:
                    cine_action_card("Revisar", "Escenas y locaciones", "fact_check", "Abrir")
                    cine_action_card("Stripboard", "Orden de rodaje", "grid_view", "Diseñar")
                    cine_action_card("Hojas de Llamado", "Generar llamadas", "description", "Generar")

            dashboard_tip = _select_dashboard_tip(dashboard)
            consejo_html = (
                '<div style="margin-top:24px;padding:18px 22px;border:1px solid rgba(148,163,184,.15);'
                'border-radius:16px;background:rgba(15,23,42,.65);display:flex;align-items:center;gap:16px;">'
                '<span class="material-symbols-rounded" style="font-size:34px;color:#f8b400;">lightbulb</span>'
                '<div><div style="font-size:17px;font-weight:700;color:white;margin-bottom:4px;">Consejo</div>'
                f'<div style="font-size:14px;color:#cbd5e1;line-height:1.6;">{escape(dashboard_tip)}</div>'
                '</div></div>'
            )

    st.markdown(consejo_html, unsafe_allow_html=True)


else:
    st.session_state.current_view = "modules"

    if "main_menu" not in st.session_state:
        st.session_state.main_menu = "1. Importar y analizar guion"

    main_menu = st.session_state.main_menu

    if main_menu == "2. Breakdown":
        render_breakdown_page()

    elif main_menu == "1. Importar y analizar guion":
        render_review_page()
        

    # LEGACY BREAKDOWN: retained temporarily for testing and later removal.
    # This branch is unreachable because Breakdown is handled above by
    # render_breakdown_page().
    elif main_menu == "2. Breakdown":
        st.markdown("# Breakdown")

        bd_menu = st.sidebar.radio(
    "Breakdown",
    [
        "Datos de escena",
        "Cast / Talento",
        "Props / Utilería",
        "Vestuario / Maquillaje",
        "VFX / SFX / Sonido",
        "Extras / Vehículos",
        "Notas de producción",
        "Exportar breakdown"
    ],
    horizontal=False,
    label_visibility="collapsed",
    key="breakdown_sub_menu"
)
        if bd_menu == "Datos de escena":
            render_scene_page()

        elif bd_menu == "Cast / Talento":

            st.markdown("## Cast / Talento")

            escenas_breakdown = []

            for _, row in st.session_state.scenes_df.iterrows():
                numero = str(row.get("Escena", ""))
                encabezado = str(row.get("Encabezado de escena", ""))
                escenas_breakdown.append(f"{numero} | {encabezado}")

            if escenas_breakdown:

                escena_seleccionada_cast = st.selectbox(
                    "Seleccionar escena",
                    escenas_breakdown,
                    key="cast_scene_selector"
                )

                numero_escena_cast = escena_seleccionada_cast.split(" | ")[0]

                escena_df_cast = st.session_state.scenes_df[
                    st.session_state.scenes_df["Escena"].astype(str) == numero_escena_cast
                ]

                personajes_detectados = ""

                if not escena_df_cast.empty:
                    personajes_detectados = str(
                        escena_df_cast.iloc[0].get("Personajes", "")
                    )

                ensure_cast_structure(
                    numero_escena_cast,
                    personajes_detectados
                )

                cast_data = st.session_state.breakdown_cast_data[numero_escena_cast]

                st.markdown("### Cast principal detectado / editable")

                st.caption(
                    "Aquí aparecen los personajes detectados en la escena. Puedes corregirlos, agregar nuevos personajes o completar actor/actriz."
                )

                with st.form(f"form_cast_talento_{numero_escena_cast}"):

                    edited_cast = st.data_editor(
                        cast_data["cast"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"cast_editor_{numero_escena_cast}"
                    )

                    st.markdown("### Dobles de riesgo / Stunts")

                    edited_stunts = st.data_editor(
                        cast_data["stunts"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"stunts_editor_{numero_escena_cast}"
                    )

                    st.markdown("### Extras de atmósfera")

                    edited_extras_atmosfera = st.data_editor(
                        cast_data["extras_atmosfera"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"extras_atmosfera_editor_{numero_escena_cast}"
                    )

                    st.markdown("### Extras con diálogo")

                    edited_extras_dialogo = st.data_editor(
                        cast_data["extras_dialogo"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"extras_dialogo_editor_{numero_escena_cast}"
                    )

                    guardar_cast_talento = st.form_submit_button(
                        "Guardar cast / talento"
                    )

                    if guardar_cast_talento:

                        st.session_state.breakdown_cast_data[numero_escena_cast] = {
                            "cast": edited_cast.fillna("").copy(),
                            "stunts": edited_stunts.fillna("").copy(),
                            "extras_atmosfera": edited_extras_atmosfera.fillna("").copy(),
                            "extras_dialogo": edited_extras_dialogo.fillna("").copy()
                        }

                        st.success("Cast / talento guardado correctamente.")

                st.markdown("### Previsualización acumulada")

                datos_escena_preview = st.session_state.get(
                    "breakdown_scene_data",
                    {}
                ).get(numero_escena_cast, {})

                escena_original_preview = st.session_state.scenes_df[
                    st.session_state.scenes_df["Escena"].astype(str) == numero_escena_cast
                ]

                escena_data_preview = {}
                if not escena_original_preview.empty:
                    escena_data_preview = escena_original_preview.iloc[0].to_dict()

                escena_preview_merged = {
                    **escena_data_preview,
                    **datos_escena_preview
                }

                st.info(
                    f"""
                    **Escena:** {datos_escena_preview.get("Escena", numero_escena_cast)}  
                    **Encabezado:** {datos_escena_preview.get("Encabezado de escena", escena_seleccionada_cast)}  
                    **Locación:** {datos_escena_preview.get("Locación", "")}  
                    **INT/EXT:** {datos_escena_preview.get("INT/EXT", "")}  
                    **Tiempo:** {datos_escena_preview.get("Tiempo", "")}  
                    **Octavos:** {obtener_octavos_finales(escena_preview_merged)}  
                    **Color stripboard:** {datos_escena_preview.get("Color stripboard", "")}  
                    **Descripción:** {datos_escena_preview.get("Descripción", "")}
                    """
                )

                st.markdown("#### Cast principal")
                st.dataframe(
                    st.session_state.breakdown_cast_data[numero_escena_cast]["cast"],
                    use_container_width=True
                )

                st.markdown("#### Dobles de riesgo / Stunts")
                st.dataframe(
                    st.session_state.breakdown_cast_data[numero_escena_cast]["stunts"],
                    use_container_width=True
                )

                st.markdown("#### Extras de atmósfera")
                st.dataframe(
                    st.session_state.breakdown_cast_data[numero_escena_cast]["extras_atmosfera"],
                    use_container_width=True
                )

                st.markdown("#### Extras con diálogo")
                st.dataframe(
                    st.session_state.breakdown_cast_data[numero_escena_cast]["extras_dialogo"],
                    use_container_width=True
                )

            else:
                st.warning("No hay escenas disponibles.")
        elif bd_menu == "Props / Utilería":

            st.markdown("## Props / Utilería")

            escenas_breakdown = []

            for _, row in st.session_state.scenes_df.iterrows():

                numero = str(row.get("Escena", ""))
                encabezado = str(row.get("Encabezado de escena", ""))

                escenas_breakdown.append(
                    f"{numero} | {encabezado}"
                )

            if escenas_breakdown:

                escena_seleccionada_props = st.selectbox(
                    "Seleccionar escena",
                    escenas_breakdown,
                    key="props_scene_selector"
                )

                numero_escena_props = escena_seleccionada_props.split(" | ")[0]

                # -------------------------------------------------
                # ASEGURAR ESTRUCTURA
                # -------------------------------------------------

                ensure_props_structure(numero_escena_props)

                props_data = st.session_state.breakdown_props_data[
                    numero_escena_props
                ]

                # -------------------------------------------------
                # FORMULARIO
                # -------------------------------------------------

                with st.form(f"form_props_{numero_escena_props}"):

                    st.markdown("### Props de mano")

                    edited_props_mano = st.data_editor(
                        props_data["props_mano"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"props_mano_{numero_escena_props}"
                    )

                    st.markdown("### Set dressing / Decoración")

                    edited_set_dressing = st.data_editor(
                        props_data["set_dressing"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"set_dressing_{numero_escena_props}"
                    )

                    st.markdown("### Props especiales")

                    edited_props_especiales = st.data_editor(
                        props_data["props_especiales"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"props_especiales_{numero_escena_props}"
                    )

                    st.markdown("### Utilería de riesgo")

                    edited_utileria_riesgo = st.data_editor(
                        props_data["utileria_riesgo"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"utileria_riesgo_{numero_escena_props}"
                    )

                    guardar_props = st.form_submit_button(
                        "Guardar props / utilería"
                    )

                    if guardar_props:

                        st.session_state.breakdown_props_data[
                            numero_escena_props
                        ] = {

                            "props_mano": edited_props_mano.fillna("").copy(),

                            "set_dressing": edited_set_dressing.fillna("").copy(),

                            "props_especiales": edited_props_especiales.fillna("").copy(),

                            "utileria_riesgo": edited_utileria_riesgo.fillna("").copy()
                        }

                        st.success(
                            "Props / utilería guardados correctamente."
                        )

                # -------------------------------------------------
                # PREVISUALIZACIÓN
                # -------------------------------------------------

                st.markdown("### Previsualización acumulada")

                st.markdown("#### Props de mano")

                st.dataframe(
                    st.session_state.breakdown_props_data[
                        numero_escena_props
                    ]["props_mano"],
                    use_container_width=True
                )

                st.markdown("#### Set dressing / Decoración")

                st.dataframe(
                    st.session_state.breakdown_props_data[
                        numero_escena_props
                    ]["set_dressing"],
                    use_container_width=True
                )

                st.markdown("#### Props especiales")

                st.dataframe(
                    st.session_state.breakdown_props_data[
                        numero_escena_props
                    ]["props_especiales"],
                    use_container_width=True
                )

                st.markdown("#### Utilería de riesgo")

                st.dataframe(
                    st.session_state.breakdown_props_data[
                        numero_escena_props
                    ]["utileria_riesgo"],
                    use_container_width=True
                )

            else:
                st.warning("No hay escenas disponibles.")
        
        elif bd_menu == "Vestuario / Maquillaje":

            st.markdown("## Vestuario / Maquillaje")

            escenas_breakdown = []

            for _, row in st.session_state.scenes_df.iterrows():

                numero = str(row.get("Escena", ""))
                encabezado = str(
                    row.get("Encabezado de escena", "")
                )

                escenas_breakdown.append(
                    f"{numero} | {encabezado}"
                )

            if escenas_breakdown:

                escena_seleccionada_wardrobe = st.selectbox(
                    "Seleccionar escena",
                    escenas_breakdown,
                    key="wardrobe_scene_selector"
                )

                numero_escena_wardrobe = (
                    escena_seleccionada_wardrobe
                    .split(" | ")[0]
                )

                # ==================================================
                # SESSION STATE
                # ==================================================

                if (
                    "breakdown_wardrobe_makeup_data"
                    not in st.session_state
                ):
                    st.session_state[
                        "breakdown_wardrobe_makeup_data"
                    ] = {}

                if (
                    numero_escena_wardrobe
                    not in st.session_state[
                        "breakdown_wardrobe_makeup_data"
                    ]
                ):
                    st.session_state[
                        "breakdown_wardrobe_makeup_data"
                    ][numero_escena_wardrobe] = {}

                wardrobe_scene_data = (
                    st.session_state
                    .breakdown_wardrobe_makeup_data[
                        numero_escena_wardrobe
                    ]
                )

                # ==================================================
                # OBTENER CAST DE LA ESCENA
                # ==================================================

                cast_scene_data = (
                    st.session_state
                    .get("breakdown_cast_data", {})
                    .get(numero_escena_wardrobe, {})
                )

                cast_df = cast_scene_data.get(
                    "cast",
                    pd.DataFrame()
                )

                # ==================================================
                # AUTOPOBLAR SI TABLAS ESTÁN VACÍAS
                # ==================================================

                if (
                    "vestuario" not in wardrobe_scene_data
                    or wardrobe_scene_data[
                        "vestuario"
                    ].empty
                ):

                    vestuario_rows = []

                    if not cast_df.empty:

                        for _, row in cast_df.iterrows():

                            personaje = str(
                                row.get("Personaje", "")
                            ).strip()

                            if personaje:

                                vestuario_rows.append({
                                    "ID":
                                        len(
                                            vestuario_rows
                                        ) + 1,

                                    "Personaje":
                                        personaje,

                                    "Vestuario": "",

                                    "Cambio vestuario":
                                        "",

                                    "Estado vestuario":
                                        "",

                                    "Continuidad":
                                        "",

                                    "Notas":
                                        ""
                                })

                    wardrobe_scene_data[
                        "vestuario"
                    ] = pd.DataFrame(
                        vestuario_rows,
                        columns=[
                            "ID",
                            "Personaje",
                            "Vestuario",
                            "Cambio vestuario",
                            "Estado vestuario",
                            "Continuidad",
                            "Notas"
                        ]
                    )

                if (
                    "maquillaje"
                    not in wardrobe_scene_data
                    or wardrobe_scene_data[
                        "maquillaje"
                    ].empty
                ):

                    maquillaje_rows = []

                    if not cast_df.empty:

                        for _, row in cast_df.iterrows():

                            personaje = str(
                                row.get("Personaje", "")
                            ).strip()

                            if personaje:

                                maquillaje_rows.append({
                                    "ID":
                                        len(
                                            maquillaje_rows
                                        ) + 1,

                                    "Personaje":
                                        personaje,

                                    "Maquillaje":
                                        "",

                                    "Peinado":
                                        "",

                                    "Continuidad":
                                        "",

                                    "Notas":
                                        ""
                                })

                    wardrobe_scene_data[
                        "maquillaje"
                    ] = pd.DataFrame(
                        maquillaje_rows,
                        columns=[
                            "ID",
                            "Personaje",
                            "Maquillaje",
                            "Peinado",
                            "Continuidad",
                            "Notas"
                        ]
                    )

                if (
                    "fx_makeup"
                    not in wardrobe_scene_data
                    or wardrobe_scene_data[
                        "fx_makeup"
                    ].empty
                ):

                    fx_rows = []

                    if not cast_df.empty:

                        for _, row in cast_df.iterrows():

                            personaje = str(
                                row.get("Personaje", "")
                            ).strip()

                            if personaje:

                                fx_rows.append({
                                    "ID":
                                        len(
                                            fx_rows
                                        ) + 1,

                                    "Personaje":
                                        personaje,

                                    "FX Makeup":
                                        "",

                                    "Complejidad":
                                        "",

                                    "Tiempo aplicación":
                                        "",

                                    "Notas":
                                        ""
                                })

                    wardrobe_scene_data[
                        "fx_makeup"
                    ] = pd.DataFrame(
                        fx_rows,
                        columns=[
                            "ID",
                            "Personaje",
                            "FX Makeup",
                            "Complejidad",
                            "Tiempo aplicación",
                            "Notas"
                        ]
                    )

                if (
                    "continuidad_visual"
                    not in wardrobe_scene_data
                ):

                    wardrobe_scene_data[
                        "continuidad_visual"
                    ] = pd.DataFrame(
                        columns=[
                            "ID",
                            "Elemento continuidad",
                            "Referencia visual",
                            "Notas script"
                        ]
                    )

                # ==================================================
                # FORMULARIO
                # ==================================================

                with st.form(
                    f"form_wardrobe_"
                    f"{numero_escena_wardrobe}"
                ):

                    st.markdown(
                        "### Vestuario principal"
                    )

                    edited_vestuario = (
                        st.data_editor(
                            wardrobe_scene_data[
                                "vestuario"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"vestuario_"
                                f"{numero_escena_wardrobe}"
                            )
                        )
                    )

                    st.markdown(
                        "### Maquillaje / Peinado"
                    )

                    edited_maquillaje = (
                        st.data_editor(
                            wardrobe_scene_data[
                                "maquillaje"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"maquillaje_"
                                f"{numero_escena_wardrobe}"
                            )
                        )
                    )

                    st.markdown(
                        "### FX Makeup / Prostéticos"
                    )

                    edited_fx_makeup = (
                        st.data_editor(
                            wardrobe_scene_data[
                                "fx_makeup"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"fx_makeup_"
                                f"{numero_escena_wardrobe}"
                            )
                        )
                    )

                    st.markdown(
                        "### Continuidad visual"
                    )

                    edited_continuidad = (
                        st.data_editor(
                            wardrobe_scene_data[
                                "continuidad_visual"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"continuidad_"
                                f"{numero_escena_wardrobe}"
                            )
                        )
                    )

                    guardar_wardrobe = (
                        st.form_submit_button(
                            "Guardar vestuario / maquillaje"
                        )
                    )

                    if guardar_wardrobe:

                        st.session_state[
                            "breakdown_wardrobe_makeup_data"
                        ][
                            numero_escena_wardrobe
                        ] = {

                            "vestuario":
                                edited_vestuario
                                .fillna("")
                                .copy(),

                            "maquillaje":
                                edited_maquillaje
                                .fillna("")
                                .copy(),

                            "fx_makeup":
                                edited_fx_makeup
                                .fillna("")
                                .copy(),

                            "continuidad_visual":
                                edited_continuidad
                                .fillna("")
                                .copy()
                        }

                        st.success(
                            "Vestuario / maquillaje "
                            "guardado correctamente."
                        )

                # ==================================================
                # PREVISUALIZACIÓN
                # ==================================================

                st.markdown(
                    "### Previsualización acumulada"
                )

                st.markdown("#### Vestuario")

                st.dataframe(
                    st.session_state[
                        "breakdown_wardrobe_makeup_data"
                    ][numero_escena_wardrobe][
                        "vestuario"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Maquillaje / Peinado"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_wardrobe_makeup_data"
                    ][numero_escena_wardrobe][
                        "maquillaje"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### FX Makeup / Prostéticos"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_wardrobe_makeup_data"
                    ][numero_escena_wardrobe][
                        "fx_makeup"
                    ],
                    use_container_width=True
                )

            else:
                st.warning(
                    "No hay escenas disponibles."
                )
        elif bd_menu == "VFX / SFX / Sonido":

            st.markdown("## VFX / SFX / Sonido")

            escenas_breakdown = []

            for _, row in st.session_state.scenes_df.iterrows():

                numero = str(row.get("Escena", ""))
                encabezado = str(
                    row.get("Encabezado de escena", "")
                )

                escenas_breakdown.append(
                    f"{numero} | {encabezado}"
                )

            if escenas_breakdown:

                escena_seleccionada_fx = st.selectbox(
                    "Seleccionar escena",
                    escenas_breakdown,
                    key="vfx_scene_selector"
                )

                numero_escena_fx = (
                    escena_seleccionada_fx
                    .split(" | ")[0]
                )

                # ==================================================
                # SESSION STATE
                # ==================================================

                if (
                    "breakdown_vfx_sound_data"
                    not in st.session_state
                ):
                    st.session_state[
                        "breakdown_vfx_sound_data"
                    ] = {}

                if (
                    numero_escena_fx
                    not in st.session_state[
                        "breakdown_vfx_sound_data"
                    ]
                ):

                    st.session_state[
                        "breakdown_vfx_sound_data"
                    ][numero_escena_fx] = {

                        "vfx": pd.DataFrame(
                            columns=[
                                "ID",
                                "VFX requerido",
                                "Descripción",
                                "Complejidad",
                                "Departamento",
                                "Notas"
                            ]
                        ),

                        "sfx_practicos": pd.DataFrame(
                            columns=[
                                "ID",
                                "SFX práctico",
                                "Material requerido",
                                "Seguridad",
                                "Responsable",
                                "Notas"
                            ]
                        ),

                        "sonido": pd.DataFrame(
                            columns=[
                                "ID",
                                "Elemento sonoro",
                                "Tipo",
                                "Narrativo",
                                "Grabación especial",
                                "Notas"
                            ]
                        ),

                        "requerimientos_tecnicos": pd.DataFrame(
                            columns=[
                                "ID",
                                "Requerimiento",
                                "Departamento",
                                "Prioridad",
                                "Notas"
                            ]
                        )
                    }

                fx_scene_data = (
                    st.session_state
                    .breakdown_vfx_sound_data[
                        numero_escena_fx
                    ]
                )

                # ==================================================
                # FORMULARIO
                # ==================================================

                with st.form(
                    f"form_vfx_{numero_escena_fx}"
                ):

                    st.markdown("### VFX")

                    edited_vfx = st.data_editor(
                        fx_scene_data["vfx"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"vfx_{numero_escena_fx}"
                    )

                    st.markdown(
                        "### SFX prácticos"
                    )

                    edited_sfx = st.data_editor(
                        fx_scene_data[
                            "sfx_practicos"
                        ],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"sfx_{numero_escena_fx}"
                    )

                    st.markdown(
                        "### Sonido especial / ambiente"
                    )

                    edited_sound = st.data_editor(
                        fx_scene_data[
                            "sonido"
                        ],
                        use_container_width=True,
                        num_rows="dynamic",
                        key=f"sound_{numero_escena_fx}"
                    )

                    st.markdown(
                        "### Requerimientos técnicos"
                    )

                    edited_requirements = (
                        st.data_editor(
                            fx_scene_data[
                                "requerimientos_tecnicos"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"requirements_"
                                f"{numero_escena_fx}"
                            )
                        )
                    )

                    guardar_fx = (
                        st.form_submit_button(
                            "Guardar VFX / "
                            "SFX / Sonido"
                        )
                    )

                    if guardar_fx:

                        st.session_state[
                            "breakdown_vfx_sound_data"
                        ][numero_escena_fx] = {

                            "vfx":
                                edited_vfx
                                .fillna("")
                                .copy(),

                            "sfx_practicos":
                                edited_sfx
                                .fillna("")
                                .copy(),

                            "sonido":
                                edited_sound
                                .fillna("")
                                .copy(),

                            "requerimientos_tecnicos":
                                edited_requirements
                                .fillna("")
                                .copy()
                        }

                        st.success(
                            "VFX / SFX / Sonido "
                            "guardado correctamente."
                        )

                # ==================================================
                # PREVISUALIZACIÓN
                # ==================================================

                st.markdown(
                    "### Previsualización acumulada"
                )

                st.markdown("#### VFX")

                st.dataframe(
                    st.session_state[
                        "breakdown_vfx_sound_data"
                    ][numero_escena_fx][
                        "vfx"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### SFX prácticos"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_vfx_sound_data"
                    ][numero_escena_fx][
                        "sfx_practicos"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Sonido especial / ambiente"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_vfx_sound_data"
                    ][numero_escena_fx][
                        "sonido"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Requerimientos técnicos"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_vfx_sound_data"
                    ][numero_escena_fx][
                        "requerimientos_tecnicos"
                    ],
                    use_container_width=True
                )

            else:
                st.warning(
                    "No hay escenas disponibles."
                )       
        
        elif bd_menu == "Extras / Vehículos":

            st.markdown(
                "## Extras / Vehículos / Animales"
            )

            escenas_breakdown = []

            for _, row in st.session_state.scenes_df.iterrows():

                numero = str(
                    row.get("Escena", "")
                )

                encabezado = str(
                    row.get(
                        "Encabezado de escena",
                        ""
                    )
                )

                escenas_breakdown.append(
                    f"{numero} | {encabezado}"
                )

            if escenas_breakdown:

                escena_seleccionada_extras = (
                    st.selectbox(
                        "Seleccionar escena",
                        escenas_breakdown,
                        key="extras_scene_selector"
                    )
                )

                numero_escena_extras = (
                    escena_seleccionada_extras
                    .split(" | ")[0]
                )

                # ==================================================
                # SESSION STATE
                # ==================================================

                if (
                    "breakdown_extras_data"
                    not in st.session_state
                ):
                    st.session_state[
                        "breakdown_extras_data"
                    ] = {}

                if (
                    numero_escena_extras
                    not in st.session_state[
                        "breakdown_extras_data"
                    ]
                ):

                    st.session_state[
                        "breakdown_extras_data"
                    ][
                        numero_escena_extras
                    ] = {

                        "extras_atmosfera":
                            pd.DataFrame(
                                columns=[
                                    "ID",
                                    "Tipo extra",
                                    "Cantidad",
                                    "Vestuario requerido",
                                    "Acción",
                                    "Notas"
                                ]
                            ),

                        "extras_dialogo":
                            pd.DataFrame(
                                columns=[
                                    "ID",
                                    "Personaje / Tipo",
                                    "Línea o función",
                                    "Cantidad",
                                    "Notas"
                                ]
                            ),

                        "vehiculos_pelicula":
                            pd.DataFrame(
                                columns=[
                                    "ID",
                                    "Vehículo",
                                    "Personaje asociado",
                                    "Acción escena",
                                    "Vehículo película",
                                    "Notas"
                                ]
                            ),

                        "vehiculos_produccion":
                            pd.DataFrame(
                                columns=[
                                    "ID",
                                    "Vehículo producción",
                                    "Departamento",
                                    "Cantidad",
                                    "Notas"
                                ]
                            ),

                        "animales":
                            pd.DataFrame(
                                columns=[
                                    "ID",
                                    "Animal",
                                    "Cantidad",
                                    "Handler requerido",
                                    "Notas"
                                ]
                            )
                    }

                extras_scene_data = (
                    st.session_state[
                        "breakdown_extras_data"
                    ][numero_escena_extras]
                )

                # ==================================================
                # FORMULARIO
                # ==================================================

                with st.form(
                    f"form_extras_"
                    f"{numero_escena_extras}"
                ):

                    st.markdown(
                        "### Extras de atmósfera"
                    )

                    edited_extras_atmosfera = (
                        st.data_editor(
                            extras_scene_data[
                                "extras_atmosfera"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"extras_atmosfera_"
                                f"{numero_escena_extras}"
                            )
                        )
                    )

                    st.markdown(
                        "### Extras con diálogo"
                    )

                    edited_extras_dialogo = (
                        st.data_editor(
                            extras_scene_data[
                                "extras_dialogo"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"extras_dialogo_"
                                f"{numero_escena_extras}"
                            )
                        )
                    )

                    st.markdown(
                        "### Vehículos película"
                    )

                    edited_vehiculos_pelicula = (
                        st.data_editor(
                            extras_scene_data[
                                "vehiculos_pelicula"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"vehiculos_pelicula_"
                                f"{numero_escena_extras}"
                            )
                        )
                    )

                    st.markdown(
                        "### Vehículos de producción"
                    )

                    edited_vehiculos_produccion = (
                        st.data_editor(
                            extras_scene_data[
                                "vehiculos_produccion"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"vehiculos_produccion_"
                                f"{numero_escena_extras}"
                            )
                        )
                    )

                    st.markdown(
                        "### Animales"
                    )

                    edited_animales = (
                        st.data_editor(
                            extras_scene_data[
                                "animales"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"animales_"
                                f"{numero_escena_extras}"
                            )
                        )
                    )

                    guardar_extras = (
                        st.form_submit_button(
                            "Guardar extras / "
                            "vehículos / animales"
                        )
                    )

                    if guardar_extras:

                        st.session_state[
                            "breakdown_extras_data"
                        ][
                            numero_escena_extras
                        ] = {

                            "extras_atmosfera":
                                edited_extras_atmosfera
                                .fillna("")
                                .copy(),

                            "extras_dialogo":
                                edited_extras_dialogo
                                .fillna("")
                                .copy(),

                            "vehiculos_pelicula":
                                edited_vehiculos_pelicula
                                .fillna("")
                                .copy(),

                            "vehiculos_produccion":
                                edited_vehiculos_produccion
                                .fillna("")
                                .copy(),

                            "animales":
                                edited_animales
                                .fillna("")
                                .copy()
                        }

                        st.success(
                            "Extras / vehículos / "
                            "animales guardados "
                            "correctamente."
                        )

                # ==================================================
                # PREVISUALIZACIÓN
                # ==================================================

                st.markdown(
                    "### Previsualización acumulada"
                )

                st.markdown(
                    "#### Extras de atmósfera"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_extras_data"
                    ][numero_escena_extras][
                        "extras_atmosfera"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Extras con diálogo"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_extras_data"
                    ][numero_escena_extras][
                        "extras_dialogo"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Vehículos película"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_extras_data"
                    ][numero_escena_extras][
                        "vehiculos_pelicula"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Vehículos de producción"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_extras_data"
                    ][numero_escena_extras][
                        "vehiculos_produccion"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Animales"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_extras_data"
                    ][numero_escena_extras][
                        "animales"
                    ],
                    use_container_width=True
                )

            else:
                st.warning(
                    "No hay escenas disponibles."
                )

        elif bd_menu == "Notas de producción":

            st.markdown(
                "## Notas de Producción"
            )

            escenas_breakdown = []

            for _, row in st.session_state.scenes_df.iterrows():

                numero = str(
                    row.get("Escena", "")
                )

                encabezado = str(
                    row.get(
                        "Encabezado de escena",
                        ""
                    )
                )

                escenas_breakdown.append(
                    f"{numero} | {encabezado}"
                )

            if escenas_breakdown:

                escena_seleccionada_notes = (
                    st.selectbox(
                        "Seleccionar escena",
                        escenas_breakdown,
                        key="production_notes_selector"
                    )
                )

                numero_escena_notes = (
                    escena_seleccionada_notes
                    .split(" | ")[0]
                )

                # ==================================================
                # SESSION STATE
                # ==================================================

                if (
                    "breakdown_production_notes_data"
                    not in st.session_state
                ):
                    st.session_state[
                        "breakdown_production_notes_data"
                    ] = {}

                if (
                    numero_escena_notes
                    not in st.session_state[
                        "breakdown_production_notes_data"
                    ]
                ):

                    st.session_state[
                        "breakdown_production_notes_data"
                    ][
                        numero_escena_notes
                    ] = {

                        "riesgos_seguridad":
                            pd.DataFrame(
                                columns=[
                                    "ID",
                                    "Riesgo",
                                    "Departamento",
                                    "Nivel riesgo",
                                    "Medida preventiva",
                                    "Notas"
                                ]
                            ),

                        "permisos_logistica":
                            pd.DataFrame(
                                columns=[
                                    "ID",
                                    "Requerimiento",
                                    "Tipo",
                                    "Responsable",
                                    "Estado",
                                    "Notas"
                                ]
                            ),

                        "continuidad_critica":
                            pd.DataFrame(
                                columns=[
                                    "ID",
                                    "Elemento continuidad",
                                    "Importancia",
                                    "Departamento",
                                    "Notas"
                                ]
                            ),

                        "notas_generales":
                            ""
                    }

                notes_scene_data = (
                    st.session_state[
                        "breakdown_production_notes_data"
                    ][numero_escena_notes]
                )

                # ==================================================
                # FORMULARIO
                # ==================================================

                with st.form(
                    f"form_notes_"
                    f"{numero_escena_notes}"
                ):

                    st.markdown(
                        "### Riesgos / Seguridad"
                    )

                    edited_riesgos = (
                        st.data_editor(
                            notes_scene_data[
                                "riesgos_seguridad"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"riesgos_"
                                f"{numero_escena_notes}"
                            )
                        )
                    )

                    st.markdown(
                        "### Permisos / Logística"
                    )

                    edited_permisos = (
                        st.data_editor(
                            notes_scene_data[
                                "permisos_logistica"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"permisos_"
                                f"{numero_escena_notes}"
                            )
                        )
                    )

                    st.markdown(
                        "### Continuidad crítica"
                    )

                    edited_continuidad = (
                        st.data_editor(
                            notes_scene_data[
                                "continuidad_critica"
                            ],
                            use_container_width=True,
                            num_rows="dynamic",
                            key=(
                                f"continuidad_notes_"
                                f"{numero_escena_notes}"
                            )
                        )
                    )

                    st.markdown(
                        "### Notas generales de producción"
                    )

                    edited_notes = (
                        st.text_area(
                            "Observaciones",
                            value=notes_scene_data.get(
                                "notas_generales",
                                ""
                            ),
                            height=180,
                            key=(
                                f"general_notes_"
                                f"{numero_escena_notes}"
                            )
                        )
                    )

                    guardar_notes = (
                        st.form_submit_button(
                            "Guardar notas "
                            "de producción"
                        )
                    )

                    if guardar_notes:

                        st.session_state[
                            "breakdown_production_notes_data"
                        ][
                            numero_escena_notes
                        ] = {

                            "riesgos_seguridad":
                                edited_riesgos
                                .fillna("")
                                .copy(),

                            "permisos_logistica":
                                edited_permisos
                                .fillna("")
                                .copy(),

                            "continuidad_critica":
                                edited_continuidad
                                .fillna("")
                                .copy(),

                            "notas_generales":
                                edited_notes
                        }

                        st.success(
                            "Notas de producción "
                            "guardadas correctamente."
                        )

                # ==================================================
                # PREVISUALIZACIÓN
                # ==================================================

                st.markdown(
                    "### Previsualización acumulada"
                )

                st.markdown(
                    "#### Riesgos / Seguridad"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_production_notes_data"
                    ][numero_escena_notes][
                        "riesgos_seguridad"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Permisos / Logística"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_production_notes_data"
                    ][numero_escena_notes][
                        "permisos_logistica"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Continuidad crítica"
                )

                st.dataframe(
                    st.session_state[
                        "breakdown_production_notes_data"
                    ][numero_escena_notes][
                        "continuidad_critica"
                    ],
                    use_container_width=True
                )

                st.markdown(
                    "#### Notas generales"
                )

                st.text_area(
                    "Resumen",
                    value=st.session_state[
                        "breakdown_production_notes_data"
                    ][numero_escena_notes].get(
                        "notas_generales",
                        ""
                    ),
                    height=180,
                    disabled=True,
                    key=(
                        f"preview_notes_"
                        f"{numero_escena_notes}"
                    )
                )

            else:
                st.warning(
                    "No hay escenas disponibles."
                )

        elif bd_menu == "Exportar breakdown":

            st.markdown("## Exportar Breakdown")

            # ==================================================
            # DATOS DEL PROYECTO
            # ==================================================

            project_info = st.session_state.get(
                "project_info",
                {}
            )

            nombre_proyecto = project_info.get(
                "nombre",
                "Proyecto sin título"
            )

            director = project_info.get(
                "director",
                "-"
            )

            productor = project_info.get(
                "productor",
                "-"
            )

            version_guion = project_info.get(
                "version_guion",
                "-"
            )

            total_escenas = len(
                st.session_state.scenes_df
            )

            # ==================================================
            # HEADER PROYECTO
            # ==================================================

            st.markdown("### Información del proyecto")

            col1, col2 = st.columns(2)

            with col1:

                st.markdown(
                    f"""
        **Proyecto:** {nombre_proyecto}

        **Director:** {director}

        **Productor:** {productor}
        """
                )

            with col2:

                st.markdown(
                    f"""
        **Versión de guion:** {version_guion}

        **Escenas analizadas:** {total_escenas}
        """
                )

            st.divider()

            # ==================================================
            # SELECTOR ESCENA
            # ==================================================

            escenas_breakdown = []

            if not st.session_state.scenes_df.empty:

                for _, row in (
                    st.session_state.scenes_df
                    .iterrows()
                ):

                    numero = str(
                        row.get("Escena", "")
                    )

                    encabezado = str(
                        row.get(
                            "Encabezado de escena",
                            ""
                        )
                    )

                    escenas_breakdown.append(
                        f"{numero} | {encabezado}"
                    )

            if escenas_breakdown:

                escena_exportar = st.selectbox(
                    "Seleccionar escena",
                    escenas_breakdown,
                    key="breakdown_preview_scene"
                )

                numero_escena = (
                    escena_exportar
                    .split(" | ")[0]
                )

                # ==================================================
                # DATOS ESCENA ORIGINAL
                # ==================================================

                escena_df = (
                    st.session_state.scenes_df[
                        st.session_state.scenes_df[
                            "Escena"
                        ].astype(str)
                        == numero_escena
                    ]
                )

                escena_data = {}

                if not escena_df.empty:

                    escena_data = (
                        escena_df.iloc[0]
                        .to_dict()
                    )

                # ==================================================
                # DATOS GUARDADOS TAB ESCENA
                # ==================================================

                breakdown_scene = (
                    st.session_state.get(
                        "breakdown_scene_data",
                        {}
                    )
                )

                datos_guardados = (
                    breakdown_scene.get(
                        numero_escena,
                        {}
                    )
                )

                encabezado = escena_data.get(
                    "Encabezado de escena",
                    "-"
                )

                locacion = datos_guardados.get(
                    "locacion",
                    escena_data.get(
                        "Locación",
                        "-"
                    )
                )

                int_ext = datos_guardados.get(
                    "INT/EXT",
                    datos_guardados.get(
                        "int_ext",
                        escena_data.get(
                            "INT/EXT",
                            "-"
                        )
                    )
                )

                tiempo = datos_guardados.get(
                    "Tiempo",
                    datos_guardados.get(
                        "tiempo",
                        escena_data.get(
                            "Tiempo",
                            "-"
                        )
                    )
                )

                escena_merged = {
                    **escena_data,
                    **datos_guardados
                }

                octavos = obtener_octavos_finales(escena_merged) or "-"

                color_stripboard = datos_guardados.get(
                    "Color stripboard",
                    datos_guardados.get(
                        "color_stripboard",
                        "-"
                    )
                )

                descripcion = datos_guardados.get(
                    "Descripción",
                    datos_guardados.get(
                        "descripcion_escena",
                        datos_guardados.get(
                            "descripcion",
                            datos_guardados.get(
                                "Descripcion",
                                escena_data.get(
                                    "Descripción",
                                    ""
                                )
                            )
                        )
                    )
                )

                notas_escena = datos_guardados.get(
                    "Notas de escena",
                    datos_guardados.get(
                        "notas_escena",
                        datos_guardados.get(
                            "notas",
                            escena_data.get(
                                "Notas de escena",
                                ""
                            )
                        )
                    )
                )

                hoja_actual = (
                    int(numero_escena)
                    if str(numero_escena).isdigit()
                    else 1
                )

                # ==================================================
                # PREVIEW BREAKDOWN
                # ==================================================

                st.success(
                    "Vista previa del breakdown lista."
                )

                st.markdown("---")

                # HEADER HÍBRIDO

                c1, c2, c3 = st.columns(
                    [2, 2, 1]
                )

                with c1:

                    st.markdown(
                        f"""
        ### {nombre_proyecto}

        **Director:** {director}

        **Productor:** {productor}
        """
                    )

                with c2:

                    st.markdown(
                        f"""
        ### Breakdown de escena

        **Versión guion:** {version_guion}

        **Fecha:** {datetime.now().strftime('%d/%m/%Y')}
        """
                    )

                with c3:

                    st.markdown(
                        f"""
        ### Hoja

        **{hoja_actual} de {total_escenas}**
        """
                    )

                st.markdown("---")

                st.markdown(
                    f"## ESCENA {numero_escena}"
                )

                st.markdown(
                    f"### {encabezado}"
                )

                colA, colB, colC = st.columns(3)

                with colA:

                    st.markdown(
                        f"""
        **Locación**  
        {locacion}

        **INT/EXT**  
        {int_ext}
        """
                    )

                with colB:

                    st.markdown(
                        f"""
        **Tiempo**  
        {tiempo}

        **Octavos**  
        {octavos}
        """
                    )

                with colC:

                    st.markdown(
                        f"""
        **Color stripboard**  
        {color_stripboard}
        """
                    )

                st.markdown(
                    "### Descripción escena"
                )

                st.info(descripcion)

                st.markdown(
                    "### Notas de escena"
                )

                st.info(notas_escena)

                st.markdown("---")

                left_col, right_col = st.columns(2)

                # ==================================================
                # CAST
                # ==================================================

                with left_col:

                    st.markdown(
                        "## 🎭 Cast / Talento"
                    )

                    cast_scene = (
                        st.session_state.get(
                            "breakdown_cast_data",
                            {}
                        ).get(
                            numero_escena,
                            {}
                        )
                    )

                    for titulo, key in {

                        "Cast principal":
                            "cast",

                        "Dobles / Stunts":
                            "stunts",

                        "Extras atmósfera":
                            "extras_atmosfera",

                        "Extras diálogo":
                            "extras_dialogo"

                    }.items():

                        df = cast_scene.get(
                            key,
                            pd.DataFrame()
                        )

                        if not df.empty:

                            st.markdown(
                                f"#### {titulo}"
                            )

                            st.dataframe(
                                df,
                                use_container_width=True,
                                hide_index=True
                            )

                # ==================================================
                # PROPS
                # ==================================================

                with right_col:

                    st.markdown(
                        "## 🧰 Props / Utilería"
                    )

                    props_scene = (
                        st.session_state.get(
                            "breakdown_props_data",
                            {}
                        ).get(
                            numero_escena,
                            {}
                        )
                    )

                    for titulo, key in {

                        "Props de mano":
                            "props_mano",

                        "Set dressing":
                            "set_dressing",

                        "Props especiales":
                            "props_especiales",

                        "Utilería riesgo":
                            "utileria_riesgo"

                    }.items():

                        df = props_scene.get(
                            key,
                            pd.DataFrame()
                        )

                        if not df.empty:

                            st.markdown(
                                f"#### {titulo}"
                            )

                            st.dataframe(
                                df,
                                use_container_width=True,
                                hide_index=True
                            )

                st.markdown("---")

                st.markdown("### Exportar breakdown")

                # Recolectar secciones disponibles para el PDF (mantener compatibilidad con sesiones previas)
                sections = {}

                # Cast / Talento
                if cast_scene:
                    sections['Cast / Talento'] = cast_scene

                # Props / Utilería
                if props_scene:
                    sections['Props / Utilería'] = props_scene

                # Vestuario / Maquillaje (si existe en session_state)
                wardrobe_scene = st.session_state.get('breakdown_wardrobe_makeup_data', {}).get(numero_escena, {})
                if wardrobe_scene:
                    sections['Vestuario / Maquillaje'] = wardrobe_scene

                # VFX / SFX / Sonido
                vfx_scene = st.session_state.get('breakdown_vfx_sound_data', {}).get(numero_escena, {})
                if vfx_scene:
                    sections['VFX / SFX / Sonido'] = vfx_scene

                # Extras / Vehículos / Animales
                extras_scene = st.session_state.get('breakdown_extras_data', {}).get(numero_escena, {})
                if extras_scene:
                    sections['Extras / Vehículos / Animales'] = extras_scene

                # Notas de producción
                production_notes = st.session_state.get('breakdown_production_notes_data', {}).get(numero_escena, {})
                if production_notes:
                    sections['Notas de Producción'] = production_notes

                col_download, col_space = st.columns([1, 2])

                with col_download:

                    escena_info_pdf = {
                        'Encabezado de escena': escena_data.get('Encabezado de escena', '-'),
                        'Locación': locacion,
                        'INT/EXT': int_ext,
                        'Tiempo': tiempo,
                        'Octavos': octavos,
                        'Color stripboard': color_stripboard,
                        'Descripción': descripcion,
                        'Notas de escena': notas_escena
                    }

                    # Generar PDF para descarga
                    pdf_buffer = generate_breakdown_pdf(
                        numero_escena,
                        escena_info_pdf,
                        project_info,
                        sections=sections
                    )

                    st.download_button(
                        label="⬇️ Descargar PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"breakdown_escena_{numero_escena}.pdf",
                        mime="application/pdf",
                        key=f"download_pdf_{numero_escena}"
                    )

                st.markdown("")

                with st.expander("📄 Vista previa PDF - Haz clic para expandir", expanded=False):

                    escena_info_pdf_preview = escena_info_pdf

                    # Generar otra instancia para preview (evita consumo del buffer)
                    pdf_buffer_preview = generate_breakdown_pdf(
                        numero_escena,
                        escena_info_pdf_preview,
                        project_info,
                        sections=sections
                    )

                    render_screenplay_viewer(
                        source_type="PDF",
                        original_file_bytes=pdf_buffer_preview.getvalue(),
                        filename=f"breakdown_escena_{numero_escena}.pdf",
                        key=f"breakdown_pdf_{numero_escena}",
                    )

            else:

                st.warning(
                    "No hay escenas disponibles."
                )

     # ---------------------------------------------------------
     # STRIPBOARD
     # ---------------------------------------------------------

    elif main_menu == "3. Stripboard":
        if render_stripboard_page is None:
            st.error(
                "No fue posible cargar el Stripboard. "
                "Intenta reiniciar CinePlan o verifica la instalación del módulo."
            )
        else:
            try:
                render_stripboard_page()
            except Exception:
                st.error(
                    "El Stripboard no pudo abrirse en este momento. "
                    "Tus datos del proyecto no fueron modificados."
                )
