import streamlit as st
from datetime import datetime
import pdfplumber
import xml.etree.ElementTree as ET
import pandas as pd
import re

def import_script(uploaded_file):
    """
    Punto único de entrada para importar un guion PDF o FDX.
    """

    if uploaded_file is None:
        return False

    uploaded_file_id = f"{uploaded_file.name}_{uploaded_file.size}"

    if st.session_state.get("last_uploaded_file_id") == uploaded_file_id:
        return True

    file_extension = uploaded_file.name.split(".")[-1].lower()

    if file_extension == "pdf":
        script_text = extract_text_from_pdf(uploaded_file)
        scenes_df, characters_df = detect_scenes_from_pdf_text(script_text)
        source_type = "PDF"

    elif file_extension == "fdx":
        script_text, fdx_scenes, fdx_characters = extract_fdx_data(uploaded_file)
        scenes_df, characters_df = detect_scenes_from_fdx(
            fdx_scenes,
            fdx_characters
        )
        source_type = "FDX"

    else:
        script_text = ""
        scenes_df = pd.DataFrame()
        characters_df = pd.DataFrame()
        source_type = "Desconocido"

    st.session_state.script_text = script_text
    st.session_state.scenes_df = normalize_scenes_df_octavos(scenes_df)
    st.session_state.characters_df = characters_df
    st.session_state.source_type = source_type
    st.session_state.nombre_archivo_guion = uploaded_file.name
    st.session_state.tipo_archivo_guion = source_type
    st.session_state.fecha_importacion_guion = datetime.now().isoformat()
    st.session_state.last_uploaded_file_id = uploaded_file_id

    return not scenes_df.empty

def extract_text_from_pdf(pdf_file):
    text = ""

    with pdfplumber.open(pdf_file) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()

            if page_text:
                text += f"\n--- PÁGINA {page_number} ---\n"
                text += page_text + "\n"

    return text

def get_xml_text(element):
    texts = []

    for text_node in element.iter():
        if text_node.text:
            texts.append(text_node.text)

    return " ".join(texts).strip()


def extract_fdx_data(fdx_file):
    raw = fdx_file.read()
    root = ET.fromstring(raw)

    paragraphs = []

    for paragraph in root.iter():
        tag_name = paragraph.tag.split("}")[-1]

        if tag_name == "Paragraph":
            paragraph_type = paragraph.attrib.get("Type", "")
            paragraph_number = paragraph.attrib.get("Number", "")
            paragraph_length = paragraph.attrib.get("Length", "")
            paragraph_text = get_xml_text(paragraph)

            if paragraph_text:
                paragraphs.append({
                    "type": paragraph_type,
                    "number": paragraph_number,
                    "length": paragraph_length,
                    "text": paragraph_text
                })

    script_lines = []
    scenes = []
    current_scene = None
    characters = set()

    for p in paragraphs:
        script_lines.append(p["text"])

        if p["type"] == "Scene Heading":
            if current_scene:
                scenes.append(current_scene)

            current_scene = {
                "header": p["text"],
                "number": p["number"],
                "length": p["length"],
                "text": p["text"] + "\n",
                "characters": set()
            }

        elif current_scene:
            current_scene["text"] += p["text"] + "\n"

            if p["type"] == "Character":
                character = p["text"].strip().upper()
                characters.add(character)
                current_scene["characters"].add(character)

    if current_scene:
        scenes.append(current_scene)

    return "\n".join(script_lines), scenes, sorted(characters)

def split_script_into_scenes(script_text):
    headers = re.findall(
        r'((INT\.|EXT\.|INT\/EXT\.|INT\.\/EXT\.|I\/E\.|FLASH|FLASHBACK|SUEÑO|VISIÓN|MONTAJE|SECUENCIA|PESADILLA|RECUERDO)\s*[-–]?\s*.+)',
        script_text
    )

    scenes = []

    for i, header_match in enumerate(headers):
        header = header_match[0].strip()
        start = script_text.find(header)

        if i + 1 < len(headers):
            end = script_text.find(headers[i + 1][0], start + len(header))
        else:
            end = len(script_text)

        scene_text = script_text[start:end].strip()

        page_match = re.findall(r'--- PÁGINA (\d+) ---', script_text[:start])
        page_number = page_match[-1] if page_match else ""

        scenes.append({
            "header": header,
            "text": scene_text,
            "page": page_number
        })

    return scenes

def detect_characters_from_text(script_text):
    candidates = re.findall(
        r'^\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{1,35})\s*$',
        script_text,
        re.MULTILINE
    )

    ignored = {
        "INT", "EXT", "I/E", "DIA", "DÍA", "NOCHE", "CONTINUO",
        "CORTE A", "FADE IN", "FADE OUT", "DISOLVENCIA",
        "FLASHBACK", "PRESENTE", "FIN", "THE END", "INSERT", "CUT TO"
    }

    clean = []

    for name in candidates:
        name = name.strip()

        if name not in ignored and len(name.split()) <= 4:
            clean.append(name)

    unique_characters = sorted(set(clean))

    return {
        name: index + 1
        for index, name in enumerate(unique_characters)
    }

def detect_scene_characters(scene_text, character_map):
    detected = []

    for name, number in character_map.items():
        if re.search(rf'\b{name}\b', scene_text):
            detected.append(f"#{number} {name}")

    return ", ".join(detected)

def parse_scene_heading(header):
    tipo = ""
    header_upper = header.upper()

    if (
        header_upper.startswith("INT./EXT.")
        or header_upper.startswith("INT/EXT.")
        or header_upper.startswith("I/E.")
    ):
        tipo = "I/E."
    elif header_upper.startswith("INT."):
        tipo = "INT."
    elif header_upper.startswith("EXT."):
        tipo = "EXT."

    parts = re.split(r'\s-\s|\s–\s', header)

    location = parts[0]
    location = (
        location
        .replace("INT./EXT.", "")
        .replace("INT/EXT.", "")
        .replace("I/E.", "")
        .replace("INT.", "")
        .replace("EXT.", "")
        .strip()
    )

    time = parts[1].strip() if len(parts) > 1 else ""

    header = header.upper()
    location = location.upper()
    time = time.upper()
    tipo = tipo.upper()

    return tipo, location, time

def number_to_octavos(total):
    pages = total // 8
    eighths = total % 8

    if pages == 0:
        return f"{eighths}/8"
    elif eighths == 0:
        return f"{pages}"
    else:
        return f"{pages} {eighths}/8"


def normalize_length_to_octavos(length_value):
    value = str(length_value).strip()

    if not value:
        return "1/8"

    if "/" in value:
        return value

    try:
        number = float(value)
        return number_to_octavos(round(number * 8))
    except:
        return "1/8"
    
def estimate_octavos_from_text(scene_text):
    lines = [
        line for line in scene_text.split("\n")
        if line.strip()
    ]

    line_count = len(lines)
    estimated_eighths = max(1, round(line_count / 7))
    return number_to_octavos(estimated_eighths)

def normalize_octavos_value(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    normalized = str(value).strip()
    if not normalized:
        return ""

    if normalized.lower() in {"nan", "none"}:
        return ""

    return normalized

def normalize_scene_octavos_fields(scene):
    scene = dict(scene)

    auto = normalize_octavos_value(scene.get("octavos_auto", ""))
    manual = normalize_octavos_value(scene.get("octavos_manual", ""))
    final = normalize_octavos_value(scene.get("octavos_final", ""))
    direct = normalize_octavos_value(scene.get("Octavos", ""))
    legacy = normalize_octavos_value(scene.get("octavos", ""))

    if not auto:
        auto = direct or legacy or final

    if manual:
        final = manual
    elif not final:
        final = auto

    final = final or ""

    return pd.Series({
        "octavos_auto": auto,
        "octavos_manual": manual,
        "octavos_final": final,
        "Octavos": final
    })

def normalize_scenes_df_octavos(scenes_df):
    df = scenes_df.copy()

    for col in [
        "octavos_auto",
        "octavos_manual",
        "octavos_final",
        "Octavos",
        "octavos"
    ]:
        if col not in df.columns:
            df[col] = ""

    normalized = df.apply(normalize_scene_octavos_fields, axis=1)
    df[[
        "octavos_auto",
        "octavos_manual",
        "octavos_final",
        "Octavos"
    ]] = normalized[[
        "octavos_auto",
        "octavos_manual",
        "octavos_final",
        "Octavos"
    ]]

    return df


def detect_scenes_from_pdf_text(script_text):
    scene_blocks = split_script_into_scenes(script_text)
    character_map = detect_characters_from_text(script_text)

    scenes = []

    for index, scene in enumerate(scene_blocks, start=1):
        header = scene["header"]
        tipo, location, time = parse_scene_heading(header)

        scenes.append({
            "Orden": index,
            "Escena": index,
            "Encabezado de escena": header.upper(),
            "INT/EXT": tipo.upper(),
            "Tiempo": time.upper(),
            "Locación": location.upper(),
            "Octavos": estimate_octavos_from_text(scene["text"]),
            "Página": scene.get("page", ""),
            "Personajes": detect_scene_characters(scene["text"], character_map),
            "Estado": "Pendiente de revisión",
            "Notas": ""
        })

    characters_df = pd.DataFrame([
        {"ID": number, "Personaje": name}
        for name, number in character_map.items()
    ])

    scenes_df = normalize_scenes_df_octavos(pd.DataFrame(scenes))
    return scenes_df, characters_df

def detect_scenes_from_fdx(fdx_scenes, fdx_characters):
    character_map = {
        name: index + 1
        for index, name in enumerate(sorted(fdx_characters))
    }

    scenes = []

    for index, scene in enumerate(fdx_scenes, start=1):
        header = scene["header"]
        tipo, location, time = parse_scene_heading(header)

        scene_characters = []

        for character in sorted(scene["characters"]):
            if character in character_map:
                scene_characters.append(f"#{character_map[character]} {character}")

        scenes.append({
            "Orden": index,
            "Escena": index,
            "Encabezado de escena": header.upper(),
            "INT/EXT": tipo.upper(),
            "Tiempo": time.upper(),
            "Locación": location.upper(),
            "Octavos": normalize_length_to_octavos(scene.get("length", "")) if scene.get("length", "") else estimate_octavos_from_text(scene["text"]),
            "Página": "",
            "Personajes": ", ".join(scene_characters),
            "Estado": "Pendiente de revisión",
            "Notas": ""
        })

    characters_df = pd.DataFrame([
        {"ID": number, "Personaje": name}
        for name, number in character_map.items()
    ])

    scenes_df = normalize_scenes_df_octavos(pd.DataFrame(scenes))
    return scenes_df, characters_df



