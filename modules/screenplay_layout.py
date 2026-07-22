"""Configurable screenplay composition engine used by CinePlan PDF previews."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from html import escape
from typing import Iterable

import pdfplumber
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer


@dataclass(frozen=True)
class ScreenplayLayoutConfig:
    """All measurements for a screenplay format, centralized in one profile."""

    name: str = "Final Draft style — Letter"
    page_size: tuple[float, float] = letter
    top_margin: float = 0.75 * inch
    bottom_margin: float = 0.75 * inch
    left_margin: float = 1.5 * inch
    right_margin: float = 1.0 * inch
    font_name: str = "Courier"
    font_name_bold: str = "Courier-Bold"
    font_size: float = 12
    leading: float = 12
    action_width: float = 5.75 * inch
    right_safety_inset: float = 0.125 * inch
    dialogue_left_indent: float = 1.0 * inch
    dialogue_right_indent: float = 1.5 * inch
    character_left_indent: float = 2.0 * inch
    character_width: float = 2.2 * inch
    parenthetical_left_indent: float = 1.5 * inch
    parenthetical_right_indent: float = 2.0 * inch
    transition_left_indent: float = 4.0 * inch
    scene_space_before: float = 12
    action_space_before: float = 8
    dialogue_space_before: float = 0
    element_space_after: float = 0
    page_number_top: float = 0.42 * inch
    page_number_right: float = 0.75 * inch
    show_first_page_number: bool = False
    header: str = ""
    footer: str = ""

    @classmethod
    def a4(cls) -> "ScreenplayLayoutConfig":
        return cls(name="Screenplay — A4", page_size=A4)


FINAL_DRAFT_LETTER = ScreenplayLayoutConfig()


@dataclass(frozen=True)
class ScreenplayElement:
    kind: str
    text: str


_SCENE_PREFIX = re.compile(
    r"^(INT\.?|EXT\.?|INT\.?/EXT\.?|I/E\.?|EST\.?|INT\.\s*/\s*EXT\.)(?:\s|$)", re.I
)
_TRANSITION = re.compile(r"(?:TO:|CORTE A:|DISUELVE A:|FADE OUT\.?|FIN\.?|CONTINUARÁ\.?)$", re.I)


def _xml_text(node: ET.Element) -> str:
    return "".join(node.itertext()).strip()


def elements_from_fdx(fdx_bytes: bytes) -> list[ScreenplayElement]:
    """Read Final Draft paragraph semantics without altering the import pipeline."""
    root = ET.fromstring(fdx_bytes)
    elements = []
    for node in root.iter():
        if node.tag.split("}")[-1] != "Paragraph":
            continue
        text = _xml_text(node)
        if text:
            elements.append(ScreenplayElement(node.attrib.get("Type", "Action"), text))
    return elements


def elements_from_text(script_text: str) -> list[ScreenplayElement]:
    """Best-effort semantics for compatible projects that only contain plain text."""
    elements: list[ScreenplayElement] = []
    previous_kind = ""
    for raw in (script_text or "").splitlines():
        text = raw.strip()
        if not text:
            continue
        if _SCENE_PREFIX.match(text):
            kind = "Scene Heading"
        elif _TRANSITION.search(text):
            kind = "Transition"
        elif text.startswith("(") and text.endswith(")") and previous_kind in {"Character", "Parenthetical"}:
            kind = "Parenthetical"
        elif text == text.upper() and len(text) <= 42 and not text.endswith((".", "!", "?")):
            kind = "Character"
        elif previous_kind in {"Character", "Parenthetical", "Dialogue"}:
            kind = "Dialogue"
        else:
            kind = "Action"
        elements.append(ScreenplayElement(kind, text))
        previous_kind = kind
    return elements


def _styles(config: ScreenplayLayoutConfig) -> dict[str, ParagraphStyle]:
    printable_width = (
        config.page_size[0] - config.left_margin - config.right_margin
        - config.right_safety_inset
    )
    base = dict(
        fontName=config.font_name, fontSize=config.font_size, leading=config.leading,
        textColor="#000000", allowWidows=0, allowOrphans=0,
        splitLongWords=1, spaceAfter=config.element_space_after,
    )
    bold = {**base, "fontName": config.font_name_bold}
    return {
        "Action": ParagraphStyle(
            "ScreenplayAction", **base, alignment=TA_LEFT,
            rightIndent=max(0, printable_width - config.action_width),
            spaceBefore=config.action_space_before,
        ),
        "Scene Heading": ParagraphStyle(
            "ScreenplayScene", **bold,
            alignment=TA_LEFT, spaceBefore=config.scene_space_before, keepWithNext=True,
        ),
        "Character": ParagraphStyle(
            "ScreenplayCharacter", **base, leftIndent=config.character_left_indent,
            rightIndent=max(0, printable_width - config.character_left_indent - config.character_width),
            alignment=TA_LEFT, spaceBefore=config.leading, keepWithNext=True,
        ),
        "Dialogue": ParagraphStyle(
            "ScreenplayDialogue", **base, leftIndent=config.dialogue_left_indent,
            rightIndent=config.dialogue_right_indent, alignment=TA_LEFT,
            spaceBefore=config.dialogue_space_before,
        ),
        "Parenthetical": ParagraphStyle(
            "ScreenplayParenthetical", **base, leftIndent=config.parenthetical_left_indent,
            rightIndent=config.parenthetical_right_indent, alignment=TA_LEFT, keepWithNext=True,
        ),
        "Transition": ParagraphStyle(
            "ScreenplayTransition", **base, leftIndent=config.transition_left_indent,
            alignment=TA_RIGHT, spaceBefore=config.leading,
        ),
        "Shot": ParagraphStyle(
            "ScreenplayShot", **bold,
            alignment=TA_LEFT, spaceBefore=config.leading, keepWithNext=True,
        ),
        "General": ParagraphStyle("ScreenplayGeneral", **base, alignment=TA_LEFT),
    }


def _page_decorations(canvas: Canvas, document: BaseDocTemplate, config: ScreenplayLayoutConfig) -> None:
    canvas.saveState()
    canvas.setFont(config.font_name, 10)
    width, height = config.page_size
    page = canvas.getPageNumber()
    if page > 1 or config.show_first_page_number:
        canvas.drawRightString(width - config.page_number_right, height - config.page_number_top, f"{page}.")
    if config.header:
        canvas.drawString(config.left_margin, height - config.page_number_top, config.header)
    if config.footer:
        canvas.drawCentredString(width / 2, config.bottom_margin * 0.45, config.footer)
    canvas.restoreState()


def _element_text_width(kind: str, config: ScreenplayLayoutConfig) -> float:
    printable = (
        config.page_size[0] - config.left_margin - config.right_margin
        - config.right_safety_inset
    )
    widths = {
        "Action": min(config.action_width, printable),
        "Character": min(config.character_width, printable - config.character_left_indent),
        "Dialogue": printable - config.dialogue_left_indent - config.dialogue_right_indent,
        "Parenthetical": printable - config.parenthetical_left_indent - config.parenthetical_right_indent,
        "Transition": printable - config.transition_left_indent,
    }
    return max(inch, widths.get(kind, printable) - 1.0)


def _split_token_by_metrics(token: str, font: str, size: float, width: float) -> list[str]:
    """Split an unbroken token without ever exceeding the measured line width."""
    chunks: list[str] = []
    current = ""
    for character in token:
        candidate = current + character
        if current and pdfmetrics.stringWidth(candidate, font, size) > width:
            chunks.append(current)
            current = character
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _wrap_by_font_metrics(text: str, font: str, size: float, width: float) -> str:
    """Greedily compose explicit lines using ReportLab's actual font metrics."""
    rendered_lines: list[str] = []
    for source_line in text.splitlines() or [text]:
        words = source_line.split()
        if not words:
            rendered_lines.append("")
            continue
        current = ""
        for word in words:
            chunks = (
                _split_token_by_metrics(word, font, size, width)
                if pdfmetrics.stringWidth(word, font, size) > width else [word]
            )
            for index, chunk in enumerate(chunks):
                candidate = f"{current} {chunk}".strip()
                if current and pdfmetrics.stringWidth(candidate, font, size) > width:
                    rendered_lines.append(current)
                    current = chunk
                else:
                    current = candidate
                if index < len(chunks) - 1:
                    rendered_lines.append(current)
                    current = ""
        if current:
            rendered_lines.append(current)
    return "\n".join(rendered_lines)


def _compose_once(
    elements: Iterable[ScreenplayElement],
    config: ScreenplayLayoutConfig,
) -> bytes:
    output = io.BytesIO()
    document = BaseDocTemplate(
        output, pagesize=config.page_size, leftMargin=config.left_margin,
        rightMargin=config.right_margin, topMargin=config.top_margin,
        bottomMargin=config.bottom_margin, title="Vista previa de guion CinePlan",
        author="CinePlan",
    )
    frame = Frame(
        config.left_margin, config.bottom_margin,
        config.page_size[0] - config.left_margin - config.right_margin
        - config.right_safety_inset,
        config.page_size[1] - config.top_margin - config.bottom_margin,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    document.addPageTemplates([
        PageTemplate(
            id=config.name, frames=[frame],
            onPage=lambda canvas, doc: _page_decorations(canvas, doc, config),
        )
    ])
    styles = _styles(config)
    story = []
    for element in elements:
        kind = element.kind if element.kind in styles else "General"
        text = element.text.upper() if kind in {"Scene Heading", "Character", "Transition", "Shot"} else element.text
        font = config.font_name_bold if kind in {"Scene Heading", "Shot"} else config.font_name
        text = _wrap_by_font_metrics(
            text, font, config.font_size, _element_text_width(kind, config)
        )
        story.append(Paragraph(escape(text).replace("\n", "<br/>"), styles[kind]))
    if not story:
        raise ValueError("El guion no contiene elementos disponibles para composición.")
    document.build(story)
    return output.getvalue()


def _rendered_overflow(pdf_bytes: bytes, config: ScreenplayLayoutConfig) -> float:
    """Measure laid-out glyph bounds inside the text frame using the rendered PDF."""
    left = config.left_margin
    right = config.page_size[0] - config.right_margin
    top = config.top_margin
    bottom = config.page_size[1] - config.bottom_margin
    overflow = 0.0
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for word in page.extract_words():
                # Exclude configurable header/footer/page-number decorations.
                if word["top"] < top - 1 or word["bottom"] > bottom + 1:
                    continue
                overflow = max(
                    overflow,
                    left - float(word["x0"]),
                    float(word["x1"]) - right,
                )
    return max(0.0, overflow)


def compose_screenplay_pdf(
    elements: Iterable[ScreenplayElement],
    config: ScreenplayLayoutConfig = FINAL_DRAFT_LETTER,
) -> bytes:
    """Compose and metric-check screenplay pages before returning the PDF."""
    materialized = list(elements)
    calibrated = config
    for _ in range(3):
        pdf_bytes = _compose_once(materialized, calibrated)
        overflow = _rendered_overflow(pdf_bytes, calibrated)
        if overflow <= 0.25:  # Sub-point tolerance for PDF coordinate rounding.
            return pdf_bytes
        calibrated = replace(
            calibrated,
            action_width=max(2.5 * inch, calibrated.action_width - overflow - 2),
            right_safety_inset=calibrated.right_safety_inset + overflow + 2,
        )
    raise ValueError("No fue posible componer el guion dentro del área imprimible.")
