"""Shared visual language for CinePlan previews and printable PDF documents."""

from dataclasses import dataclass
from datetime import datetime
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle


@dataclass(frozen=True)
class DocumentTheme:
    page_size: tuple = landscape(letter)
    margin: float = 16
    header_height: float = 58
    footer_height: float = 24
    black: str = "#09090b"
    ink: str = "#111827"
    muted: str = "#71717a"
    border: str = "#d1d5db"
    paper: str = "#ffffff"
    accent: str = "#f8b400"
    font: str = "Helvetica"
    font_bold: str = "Helvetica-Bold"

    @property
    def usable_width(self):
        return self.page_size[0] - self.margin * 2


THEME = DocumentTheme()


@dataclass(frozen=True)
class EditorialGrid:
    """Single alignment and rhythm system used by HTML preview and PDF."""
    page_padding: float = 22
    content_gap: float = 8
    section_gap: float = 8
    column_gap: float = 8
    box_padding: float = 6
    box_radius: float = 6
    border_width: float = 0.35
    table_header_height: float = 22
    table_padding_x: float = 5
    table_padding_y: float = 4
    title_size: float = 9
    title_leading: float = 11

    @property
    def pdf_content_top(self):
        return THEME.header_height + THEME.margin + 14

    @property
    def pdf_content_bottom(self):
        return THEME.footer_height + THEME.margin


GRID = EditorialGrid()


def html_page_style():
    return (
        f"background:{THEME.paper};color:{THEME.ink};width:100%;aspect-ratio:11/8.5;"
        f"box-sizing:border-box;border:1px solid #cbd5e1;border-radius:{GRID.box_radius}px;"
        f"padding:{GRID.page_padding}px;box-shadow:0 12px 28px rgba(0,0,0,.22);"
        "font-family:Arial,sans-serif;font-size:9px;line-height:1.2;overflow:hidden;"
        "display:flex;flex-direction:column"
    )


def html_box_style():
    return (
        f"border:1px solid {THEME.border};border-radius:{GRID.box_radius}px;"
        f"padding:{GRID.box_padding}px;background:{THEME.paper};min-height:0;overflow:hidden"
    )


def html_section_title(title, count=None):
    suffix = f" ({count})" if count is not None else ""
    return (
        f'<div style="font-size:{GRID.title_size}px;line-height:{GRID.title_leading}px;'
        f'font-weight:900;color:{THEME.ink};border-bottom:1px solid #e5e7eb;'
        f'padding-bottom:{GRID.content_gap / 2}px;margin-bottom:{GRID.content_gap / 2}px">'
        f'{escape(str(title).upper())}{suffix}</div>'
    )


def html_scene_accent(color, label="Neutral"):
    return (
        f'<div aria-label="Color stripboard: {escape(str(label))}" '
        f'style="height:5px;flex:none;background:{escape(str(color))};'
        f'border:1px solid {THEME.border};margin-bottom:{GRID.section_gap}px;'
        'box-sizing:border-box"></div>'
    )


def pdf_scene_accent_commands(color):
    """ReportLab commands for the same restrained scene accent used in preview."""
    try:
        accent = colors.HexColor(color)
    except (TypeError, ValueError):
        accent = colors.HexColor(THEME.border)
    return (
        ('LINEABOVE', (0, 0), (-1, 0), 5, accent),
        ('BOX', (0, 0), (-1, -1), GRID.border_width, colors.HexColor(THEME.border)),
    )


def html_header(title, metadata):
    items = "".join(
        '<div style="min-width:0"><div style="font-size:6px;letter-spacing:.08em;'
        f'color:#a1a1aa;text-transform:uppercase">{escape(str(label))}</div>'
        '<div style="font-size:8px;font-weight:700;white-space:nowrap;overflow:hidden;'
        f'text-overflow:ellipsis">{escape(str(value or "—"))}</div></div>'
        for label, value in metadata
    )
    return (
        f'<header style="background:{THEME.black};color:#fff;margin:-{GRID.page_padding}px '
        f'-{GRID.page_padding}px {GRID.section_gap + 6}px;'
        'padding:14px 18px 12px;display:grid;grid-template-columns:1.45fr 2.6fr .7fr;'
        'gap:14px;align-items:center;flex:none">'
        '<div><div style="font-size:7px;letter-spacing:.12em;color:#a1a1aa">'
        'CINEPLAN SCHEDULER</div>'
        f'<div style="font-size:16px;font-weight:900;letter-spacing:-.03em;line-height:1.02">{escape(title)}</div></div>'
        f'<div style="display:grid;grid-template-columns:repeat({max(1, len(metadata))},minmax(0,1fr));gap:9px">{items}</div>'
        '<div style="height:36px;border:1px solid #52525b;display:flex;align-items:center;'
        'justify-content:center;font-size:7px;letter-spacing:.12em;color:#a1a1aa">LOGO</div>'
        '</header>'
    )


def html_footer(generation_date, page="1 de 1"):
    return (
        f'<footer style="border-top:1px solid #d4d4d8;margin-top:{GRID.section_gap}px;'
        f'padding-top:{GRID.content_gap / 2}px;flex:none;'
        'display:grid;grid-template-columns:1fr 1fr 1fr;align-items:center;color:#71717a;'
        'font-size:6.5px;letter-spacing:.04em">'
        '<span><b style="color:#27272a">CinePlan Scheduler</b></span>'
        f'<span style="text-align:center">Documento generado automáticamente · {escape(generation_date)}</span>'
        f'<span style="text-align:right">Página {escape(page)}</span></footer>'
    )


def _fit_text(pdf, text, font, max_size, max_width):
    size = max_size
    while size > 12 and stringWidth(str(text), font, size) > max_width:
        size -= 1
    return size


def draw_pdf_header(pdf, title, project="Proyecto", version="—", generated_at=None):
    generated_at = generated_at or datetime.now()
    width, height = THEME.page_size
    top = height - THEME.margin
    pdf.setFillColor(colors.HexColor(THEME.black))
    pdf.rect(THEME.margin, top - THEME.header_height, THEME.usable_width,
             THEME.header_height, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont(THEME.font, 6)
    pdf.drawString(THEME.margin + 14, top - 13, "CINEPLAN SCHEDULER")
    pdf.setFont(THEME.font_bold, _fit_text(pdf, title, THEME.font_bold, 15, 210))
    pdf.drawString(THEME.margin + 14, top - 34, str(title))
    metadata = (
        ("PROYECTO", project), ("VERSIÓN", version or "—"),
        ("FECHA", generated_at.strftime("%d/%m/%Y")), ("HORA", generated_at.strftime("%H:%M")),
    )
    x = THEME.margin + 250
    for label, value in metadata:
        pdf.setFillColor(colors.HexColor("#a1a1aa"))
        pdf.setFont(THEME.font, 5.5)
        pdf.drawString(x, top - 16, label)
        pdf.setFillColor(colors.white)
        pdf.setFont(THEME.font_bold, 7)
        pdf.drawString(x, top - 29, str(value)[:26])
        x += 105
    pdf.setStrokeColor(colors.HexColor("#52525b"))
    pdf.rect(width - THEME.margin - 64, top - 44, 50, 30, fill=0, stroke=1)
    pdf.setFillColor(colors.HexColor("#a1a1aa"))
    pdf.setFont(THEME.font, 6)
    pdf.drawCentredString(width - THEME.margin - 39, top - 31, "LOGO")


def draw_pdf_footer(pdf, page_number, generated_at=None):
    generated_at = generated_at or datetime.now()
    width, _ = THEME.page_size
    y = THEME.margin
    pdf.setStrokeColor(colors.HexColor(THEME.border))
    pdf.line(THEME.margin, y + 12, width - THEME.margin, y + 12)
    pdf.setFillColor(colors.HexColor(THEME.muted))
    pdf.setFont(THEME.font, 6.5)
    pdf.drawString(THEME.margin, y, "CinePlan Scheduler")
    pdf.drawCentredString(width / 2, y, f"Documento generado automáticamente · {generated_at:%d/%m/%Y}")
    pdf.drawRightString(width - THEME.margin, y, f"Página {page_number}")


def pdf_page_callback(title, project="Proyecto", version="—", generated_at=None):
    generated_at = generated_at or datetime.now()
    def render(pdf, _doc):
        pdf.saveState()
        draw_pdf_header(pdf, title, project, version, generated_at)
        draw_pdf_footer(pdf, pdf.getPageNumber(), generated_at)
        pdf.restoreState()
    return render


def table_styles():
    cell = ParagraphStyle("cineplan_cell", fontName=THEME.font, fontSize=6.5,
                          leading=8, textColor=colors.HexColor(THEME.ink))
    header = ParagraphStyle("cineplan_header_cell", parent=cell,
                            fontName=THEME.font_bold, textColor=colors.white)
    return cell, header


def dataframe_pdf(dataframe, title, column_widths, project="Proyecto", version="—"):
    output = BytesIO()
    generated_at = datetime.now()
    doc = SimpleDocTemplate(
        output, pagesize=THEME.page_size, leftMargin=THEME.margin,
        rightMargin=THEME.margin, topMargin=GRID.pdf_content_top,
        bottomMargin=GRID.pdf_content_bottom,
    )
    cell_style, header_style = table_styles()
    columns = list(dataframe.columns)
    data = [[Paragraph(escape(str(column)), header_style) for column in columns]]
    data.extend([
        [Paragraph(escape(str(value)), cell_style) for value in row]
        for row in dataframe.fillna("").values.tolist()
    ])
    table = Table(data, repeatRows=1, colWidths=column_widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(THEME.black)),
        ("GRID", (0, 0), (-1, -1), GRID.border_width, colors.HexColor(THEME.border)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), GRID.table_padding_x),
        ("RIGHTPADDING", (0, 0), (-1, -1), GRID.table_padding_x),
        ("TOPPADDING", (0, 0), (-1, -1), GRID.table_padding_y),
        ("BOTTOMPADDING", (0, 0), (-1, -1), GRID.table_padding_y),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
    ]))
    callback = pdf_page_callback(title, project, version, generated_at)
    doc.build([table], onFirstPage=callback, onLaterPages=callback)
    output.seek(0)
    return output


def editorial_pdf(title, subtitle="", description="", metadata=(), color="", project="Proyecto",
                  version="—", full_color_bar=False):
    """Premium binder-style page shared by covers, summaries and separators."""
    output = BytesIO()
    generated_at = datetime.now()
    width, height = THEME.page_size
    pdf = canvas.Canvas(output, pagesize=THEME.page_size)
    draw_pdf_header(pdf, title, project, version, generated_at)
    draw_pdf_footer(pdf, 1, generated_at)
    content_top = height - GRID.pdf_content_top - 28
    accent = color or THEME.accent
    try:
        pdf.setFillColor(colors.HexColor(accent))
    except ValueError:
        pdf.setFillColor(colors.HexColor(THEME.accent))
    bar_width = THEME.usable_width if full_color_bar else 58
    pdf.rect(THEME.margin, content_top - 8, bar_width, 8, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor(THEME.ink))
    title_size = _fit_text(pdf, title, THEME.font_bold, 34, THEME.usable_width * .72)
    pdf.setFont(THEME.font_bold, title_size)
    pdf.drawString(THEME.margin, content_top - 68, str(title))
    if subtitle:
        pdf.setFillColor(colors.HexColor("#4b5563"))
        pdf.setFont(THEME.font, 16)
        pdf.drawString(THEME.margin, content_top - 98, str(subtitle))
    if description:
        style = ParagraphStyle("editorial_description", fontName=THEME.font, fontSize=10,
                               leading=14, textColor=colors.HexColor(THEME.muted))
        paragraph = Paragraph(escape(str(description)), style)
        _, paragraph_height = paragraph.wrap(THEME.usable_width * .58, 100)
        paragraph.drawOn(pdf, THEME.margin, content_top - 132 - paragraph_height)
    cards = list(metadata)
    card_width = (THEME.usable_width - GRID.column_gap * 3) / 4
    card_y = 100
    for index, item in enumerate(cards[:8]):
        label, value = item if isinstance(item, tuple) and len(item) == 2 else ("", item)
        row, column = divmod(index, 4)
        x, y = THEME.margin + column * (card_width + GRID.column_gap), card_y + (1 - row) * 70
        pdf.setFillColor(colors.HexColor("#f8fafc"))
        pdf.setStrokeColor(colors.HexColor(THEME.border))
        pdf.setLineWidth(GRID.border_width)
        pdf.roundRect(x, y, card_width, 56, GRID.box_radius, fill=1, stroke=1)
        pdf.setFillColor(colors.HexColor(THEME.muted))
        pdf.setFont(THEME.font, 6.5)
        pdf.drawString(x + 10, y + 37, str(label).upper())
        pdf.setFillColor(colors.HexColor(THEME.ink))
        pdf.setFont(THEME.font_bold, 11)
        pdf.drawString(x + 10, y + 18, str(value)[:48])
    pdf.save()
    output.seek(0)
    return output.getvalue()
