import streamlit as st
import pdfplumber
import pandas as pd
import re
import json
import xml.etree.ElementTree as ET

from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter


st.set_page_config(
    page_title="CinePlan Scheduler",
    layout="wide"
)

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


# ---------------------------------------------------------
# FUNCIONES
# ---------------------------------------------------------
def dataframe_to_excel(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Tabla")

    output.seek(0)
    return output


def dataframe_to_pdf(df, title="Reporte CinePlan"):
    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    data = [list(df.columns)] + df.astype(str).values.tolist()

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    doc.build([table])
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

    return pd.DataFrame(scenes), characters_df


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

    return pd.DataFrame(scenes), characters_df


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

    project_data = {
        "project_info": st.session_state.project_info,
        "script_text": st.session_state.script_text,
        "source_type": st.session_state.source_type,
        "scenes": scenes_records,
        "characters": characters_records
    }

    return json.dumps(
        project_data,
        ensure_ascii=False,
        indent=4
    ).encode("utf-8")

def load_project_from_json(json_file):
    data = json.load(json_file)

    st.session_state.project_info = data.get("project_info", {
        "nombre": "Proyecto sin título",
        "director": "",
        "productor": "",
        "version_guion": ""
    })

    st.session_state.script_text = data.get("script_text", "")
    st.session_state.source_type = data.get("source_type", "Proyecto JSON")
    st.session_state.scenes_df = pd.DataFrame(data.get("scenes", []))
    st.session_state.characters_df = pd.DataFrame(data.get("characters", []))


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

st.sidebar.header("Proyecto")

st.sidebar.markdown("### 1. Cargar guion")

uploaded_file = st.sidebar.file_uploader(
    "Importar guion PDF o FDX",
    type=["pdf", "fdx"],
    key="sidebar_script_uploader"
)

if uploaded_file is not None:

    uploaded_file_id = f"{uploaded_file.name}_{uploaded_file.size}"

    if st.session_state.get("last_uploaded_file_id") != uploaded_file_id:

        file_extension = uploaded_file.name.split(".")[-1].lower()

        if file_extension == "pdf":
            script_text = extract_text_from_pdf(uploaded_file)
            scenes_df, characters_df = detect_scenes_from_pdf_text(script_text)
            source_type = "PDF"

        elif file_extension == "fdx":
            script_text, fdx_scenes, fdx_characters = extract_fdx_data(uploaded_file)
            scenes_df, characters_df = detect_scenes_from_fdx(fdx_scenes, fdx_characters)
            source_type = "FDX"

        else:
            script_text = ""
            scenes_df = pd.DataFrame()
            characters_df = pd.DataFrame()
            source_type = "Desconocido"

        st.session_state.script_text = script_text
        st.session_state.scenes_df = scenes_df
        st.session_state.characters_df = characters_df
        st.session_state.source_type = source_type
        st.session_state.last_uploaded_file_id = uploaded_file_id

        if not scenes_df.empty:
            st.sidebar.success("Guion analizado correctamente.")
        else:
            st.sidebar.warning("No se detectaron escenas.")

st.sidebar.markdown("### 2. Abrir proyecto guardado")

project_json = st.sidebar.file_uploader(
    "Abrir proyecto guardado (.json)",
    type=["json"],
    key="sidebar_project_uploader"
)

if project_json is not None:
    load_project_from_json(project_json)
    st.sidebar.success("Proyecto cargado correctamente.")

st.sidebar.markdown("### 3. Guardar avances")

if not st.session_state.scenes_df.empty:
    st.sidebar.download_button(
        label="Guardar proyecto actual",
        data=project_to_json(),
        file_name="proyecto_cineplan.json",
        mime="application/json"
    )

    st.sidebar.caption(
        "Guarda constantemente los cambios de tu proyecto para continuar trabajando después."
    )
else:
    st.sidebar.info("Carga un guion o abre un proyecto para poder guardar.")


# ---------------------------------------------------------
# PÁGINA DE INICIO
# ---------------------------------------------------------

st.title("CinePlan Scheduler by ChrisMaDoX")

st.markdown("""
### Desglose automático de guion y planificación de producción audiovisual

CinePlan Scheduler es una herramienta diseñada para organizar guiones cinematográficos y audiovisuales a partir de archivos PDF o FDX. Su objetivo es facilitar el proceso de preproducción mediante la detección de escenas, personajes, locaciones, octavos y datos básicos del guion.

A partir de esta información, la plataforma permite revisar, corregir y validar el análisis inicial del guion antes de pasar a breakdown, plan de rodaje, horarios de grabación y hojas de llamado.
""")

st.divider()


# ---------------------------------------------------------
# IMPORTAR GUIÓN
# ---------------------------------------------------------

if st.session_state.scenes_df.empty:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Formatos compatibles", "PDF / FDX")
        st.write("Importa guiones en PDF o Final Draft.")

    with col2:
        st.metric("Primera etapa", "Importar guion")
        st.write("Detecta escenas, personajes, locaciones y octavos.")

    with col3:
        st.metric("Guardado", "JSON")
        st.write("Guarda tu avance y continúa editando después.")

    st.info("Utiliza el menú lateral para importar un guion PDF/FDX o abrir un proyecto guardado.")

else:
    tab_import = st.tabs(["1. Importar y analizar guion"])[0]

    with tab_import:
        st.subheader("Importar guion / Revisión inicial")

        subtab1, subtab2, subtab3, subtab4, subtab5, subtab6, subtab7, subtab8 = st.tabs([
            "Proyecto",
            "Escenas detectadas",
            "Locaciones",
            "Personajes",
            "Octavos",
            "Validación",
            "Resumen general",
            "Guardar / Abrir"
        ])

        with subtab1:
            st.markdown("### Datos del proyecto")

            st.session_state.project_info["nombre"] = st.text_input(
                "Nombre del proyecto",
                st.session_state.project_info.get("nombre", "Proyecto sin título")
            )

            st.session_state.project_info["director"] = st.text_input(
                "Director/a",
                st.session_state.project_info.get("director", "")
            )

            st.session_state.project_info["productor"] = st.text_input(
                "Productor/a",
                st.session_state.project_info.get("productor", "")
            )

            st.session_state.project_info["version_guion"] = st.text_input(
                "Versión del guion",
                st.session_state.project_info.get("version_guion", "")
            )

            st.markdown("### Archivo")
            st.write(f"Formato detectado: {st.session_state.source_type}")

            with st.expander("Ver texto extraído del guion"):
                st.text_area(
                    "Texto del guion",
                    st.session_state.script_text,
                    height=400
                )

        with subtab2:
            st.markdown("### Escenas detectadas y editables")

            required_scene_columns = [
                "Orden",
                "Escena",
                "Encabezado de escena",
                "INT/EXT",
                "Tiempo",
                "Locación",
                "Octavos",
                "Página",
                "Estado",
                "Notas"
            ]

            for column in required_scene_columns:
                if column not in st.session_state.scenes_df.columns:
                    st.session_state.scenes_df[column] = ""

            if st.button("Agregar escena"):
                nuevo_numero = len(st.session_state.scenes_df) + 1

                nueva_escena = pd.DataFrame([{
                    "Orden": nuevo_numero,
                    "Escena": nuevo_numero,
                    "Encabezado de escena": "NUEVA ESCENA",
                    "INT/EXT": "",
                    "Tiempo": "",
                    "Locación": "",
                    "Octavos": "1/8",
                    "Página": "",
                    "Estado": "Pendiente de revisión",
                    "Notas": ""
                }])

                st.session_state.scenes_df = pd.concat(
                    [st.session_state.scenes_df, nueva_escena],
                    ignore_index=True
                )

                st.rerun()

            st.caption(
                "También puedes agregar escenas directamente desde la última fila vacía de la tabla."
            )

            st.markdown("### Eliminar escena")

            escenas_disponibles = []
            for _, row in st.session_state.scenes_df.iterrows():
                numero = str(row.get("Escena", ""))
                encabezado = str(row.get("Encabezado de escena", ""))
                texto = f"{numero} - {encabezado}"
                escenas_disponibles.append(texto)

            if escenas_disponibles:
                escena_a_eliminar = st.selectbox(
                    "Selecciona una escena para eliminar",
                    escenas_disponibles,
                    key="escena_a_eliminar"
                )

                if st.button("Eliminar escena seleccionada"):
                    st.session_state.scenes_df = (
                        st.session_state.scenes_df[
                            st.session_state.scenes_df["Escena"].astype(str) != escena_a_eliminar.split(" - ")[0]
                        ]
                        .reset_index(drop=True)
                    )

                    st.rerun()
            else:
                st.info("No hay escenas para eliminar.")

            with st.form("form_escenas"):
                edited_scenes = st.data_editor(
                    st.session_state.scenes_df[required_scene_columns],
                    use_container_width=True,
                    num_rows="dynamic"
                )

                col_guardar, col_ordenar = st.columns([1, 1])

                with col_guardar:
                    guardar_escenas = st.form_submit_button("Guardar cambios")

                with col_ordenar:
                    ordenar_escenas = st.form_submit_button("Ordenar escenas por ID")

                if guardar_escenas:
                    st.session_state.scenes_df = edited_scenes.fillna("").copy()
                    st.success("Escenas actualizadas correctamente.")

                if ordenar_escenas:
                    edited_scenes = edited_scenes.fillna("").copy()

                    edited_scenes["Orden"] = pd.to_numeric(
                        edited_scenes["Orden"],
                        errors="coerce"
                    )

                    edited_scenes = (
                        edited_scenes
                        .sort_values("Orden")
                        .reset_index(drop=True)
                    )

                    st.session_state.scenes_df = edited_scenes.copy()

                    st.success("Escenas ordenadas correctamente.")
                    st.rerun()

            col_left, col_excel, col_pdf = st.columns([6, 1, 1])

            with col_excel:
                st.download_button(
                    label="Excel",
                    data=dataframe_to_excel(st.session_state.scenes_df),
                    file_name="escenas_detectadas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with col_pdf:
                st.download_button(
                    label="PDF",
                    data=dataframe_to_pdf(
                        st.session_state.scenes_df,
                        "Reporte de Escenas"
                    ),
                    file_name="escenas_detectadas.pdf",
                    mime="application/pdf"
                )

            st.markdown("### Resumen de escenas detectadas")

            st.metric(
                label="Total de escenas detectadas",
                value=len(st.session_state.scenes_df)
            )

        with subtab3:
            st.markdown("### Locaciones detectadas y editables")

            # ---------------------------------------------------------
            # CREAR RESUMEN DE LOCACIONES DESDE ESCENAS
            # ---------------------------------------------------------

            locations_df = st.session_state.scenes_df[[
                "Locación",
                "INT/EXT",
                "Tiempo",
                "Escena",
                "Encabezado de escena"
            ]].copy()

            def classify_location_type(types):
                types = str(types).upper()

                if "I/E" in types:
                    return "Interior / Exterior"
                elif "INT" in types and "EXT" in types:
                    return "Interior / Exterior"
                elif "INT" in types:
                    return "Interior"
                elif "EXT" in types:
                    return "Exterior"
                else:
                    return "Especial / Narrativa"

            location_summary = (
                locations_df
                .groupby("Locación")
                .agg({
                    "Escena": lambda x: ", ".join(map(str, sorted(set(x)))),
                    "INT/EXT": lambda x: ", ".join(sorted(set(x))),
                    "Tiempo": lambda x: ", ".join(sorted(set(x))),
                    "Encabezado de escena": lambda x: " | ".join(sorted(set(map(str, x))))
                })
                .reset_index()
            )

            location_summary["Clasificación"] = location_summary["INT/EXT"].apply(classify_location_type)

            if "manual_locations_df" not in st.session_state:
                st.session_state.manual_locations_df = pd.DataFrame(columns=[
                    "Locación",
                    "Escena",
                    "INT/EXT",
                    "Tiempo",
                    "Encabezado de escena",
                    "Clasificación"
                ])

            full_locations_df = pd.concat(
                [location_summary, st.session_state.manual_locations_df],
                ignore_index=True
            )

            # ---------------------------------------------------------
            # AGREGAR LOCACIÓN
            # ---------------------------------------------------------

            if st.button("Agregar locación"):
                nueva_locacion = pd.DataFrame([{
                    "Locación": "NUEVA LOCACIÓN",
                    "Escena": "",
                    "INT/EXT": "",
                    "Tiempo": "",
                    "Encabezado de escena": "",
                    "Clasificación": "Sin clasificar"
                }])

                st.session_state.manual_locations_df = pd.concat(
                    [st.session_state.manual_locations_df, nueva_locacion],
                    ignore_index=True
                )

                st.rerun()

            st.caption(
                "Las locaciones detectadas vienen de las escenas. Las locaciones agregadas manualmente se usan como apoyo de organización."
            )

            # ---------------------------------------------------------
            # ELIMINAR LOCACIÓN
            # ---------------------------------------------------------

            st.markdown("### Eliminar locación")

            locaciones_disponibles = full_locations_df["Locación"].dropna().astype(str).tolist()

            if locaciones_disponibles:
                locacion_a_eliminar = st.selectbox(
                    "Selecciona una locación para eliminar",
                    options=locaciones_disponibles,
                    key="locacion_a_eliminar"
                )

                if st.button("Eliminar locación seleccionada"):
                    st.session_state.manual_locations_df = (
                        st.session_state.manual_locations_df[
                            st.session_state.manual_locations_df["Locación"] != locacion_a_eliminar
                        ]
                        .reset_index(drop=True)
                    )

                    st.success(f"Locación eliminada: {locacion_a_eliminar}")
                    st.rerun()
            else:
                st.info("No hay locaciones para eliminar.")

            # ---------------------------------------------------------
            # TABLA EDITABLE
            # ---------------------------------------------------------

            with st.form("form_locaciones"):
                edited_locations = st.data_editor(
                    full_locations_df,
                    use_container_width=True,
                    num_rows="dynamic"
                )

                guardar_locaciones = st.form_submit_button("Guardar cambios")

                if guardar_locaciones:
                    manual_rows = edited_locations[
                        edited_locations["Escena"].astype(str).str.strip() == ""
                    ].copy()

                    st.session_state.manual_locations_df = manual_rows.reset_index(drop=True)

                    st.success("Locaciones actualizadas correctamente.")

            # ---------------------------------------------------------
            # TABLAS DE CLASIFICACIÓN
            # ---------------------------------------------------------

            st.markdown("### Resumen por tipo de locación")

            interiores_df = st.session_state.scenes_df[
                st.session_state.scenes_df["INT/EXT"].astype(str).str.upper().str.contains("INT", na=False)
                & ~st.session_state.scenes_df["INT/EXT"].astype(str).str.upper().str.contains("I/E", na=False)
            ][[
                "Escena",
                "Encabezado de escena",
                "Locación",
                "Tiempo",
                "Octavos"
            ]].copy()

            exteriores_df = st.session_state.scenes_df[
                st.session_state.scenes_df["INT/EXT"].astype(str).str.upper().str.contains("EXT", na=False)
                & ~st.session_state.scenes_df["INT/EXT"].astype(str).str.upper().str.contains("I/E", na=False)
            ][[
                "Escena",
                "Encabezado de escena",
                "Locación",
                "Tiempo",
                "Octavos"
            ]].copy()

            interiores_exteriores_df = st.session_state.scenes_df[
                st.session_state.scenes_df["INT/EXT"].astype(str).str.upper().str.contains("I/E", na=False)
            ][[
                "Escena",
                "Encabezado de escena",
                "Locación",
                "Tiempo",
                "Octavos"
            ]].copy()

            keywords_especiales = [
                "FLASH",
                "FLASHBACK",
                "SUEÑO",
                "VISION",
                "VISIÓN",
                "RITUAL",
                "PESADILLA",
                "RECUERDO",
                "MONTAJE",
                "SECUENCIA"
            ]

            patron_especiales = "|".join(keywords_especiales)

            especiales_df = st.session_state.scenes_df[
                st.session_state.scenes_df["Encabezado de escena"]
                .astype(str)
                .str.upper()
                .str.contains(patron_especiales, na=False)
            ][[
                "Escena",
                "Encabezado de escena",
                "Locación",
                "Tiempo",
                "Octavos"
            ]].copy()

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Interiores", len(interiores_df))
            col2.metric("Exteriores", len(exteriores_df))
            col3.metric("I/E", len(interiores_exteriores_df))
            col4.metric("Especiales", len(especiales_df))

            with st.expander("Ver escenas interiores"):
                st.dataframe(interiores_df, use_container_width=True)

            with st.expander("Ver escenas exteriores"):
                st.dataframe(exteriores_df, use_container_width=True)

            with st.expander("Ver escenas I/E"):
                st.dataframe(interiores_exteriores_df, use_container_width=True)

            with st.expander("Ver escenas especiales / narrativas"):
                st.dataframe(especiales_df, use_container_width=True)

            # ---------------------------------------------------------
            # EXPORTAR EXCEL / PDF
            # ---------------------------------------------------------

            export_locations_df = pd.concat([
                interiores_df.assign(Clasificación="Interior"),
                exteriores_df.assign(Clasificación="Exterior"),
                interiores_exteriores_df.assign(Clasificación="Interior / Exterior"),
                especiales_df.assign(Clasificación="Especial / Narrativa")
            ], ignore_index=True)

            col_left, col_excel, col_pdf = st.columns([6, 1, 1])

            with col_excel:
                st.download_button(
                    label="Excel",
                    data=dataframe_to_excel(export_locations_df),
                    file_name="locaciones_y_clasificacion.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with col_pdf:
                st.download_button(
                    label="PDF",
                    data=dataframe_to_pdf(
                        export_locations_df,
                        title="Reporte de Locaciones y Clasificación"
                    ),
                    file_name="locaciones_y_clasificacion.pdf",
                    mime="application/pdf"
                )

            
        with subtab4:
            st.markdown("### Personajes detectados y editables")

            required_character_columns = [
                "ID",
                "Personaje",
                "Actor/Actriz",
                "Contacto",
                "Notas"
            ]

            for column in required_character_columns:
                if column not in st.session_state.characters_df.columns:
                    st.session_state.characters_df[column] = ""

            if st.button("Agregar personaje"):
                nuevo_id = len(st.session_state.characters_df) + 1

                nueva_fila = pd.DataFrame([{
                    "ID": nuevo_id,
                    "Personaje": "NUEVO PERSONAJE",
                    "Actor/Actriz": "",
                    "Contacto": "",
                    "Notas": ""
                }])

                st.session_state.characters_df = pd.concat(
                    [st.session_state.characters_df, nueva_fila],
                    ignore_index=True
                )

                st.rerun()

            st.caption(
                "También puedes agregar personajes directamente desde la última fila vacía de la tabla."
            )

            st.markdown("### Eliminar personaje")

            personajes_disponibles = (
                st.session_state.characters_df["Personaje"]
                .dropna()
                .astype(str)
                .tolist()
            )

            if personajes_disponibles:
                personaje_a_eliminar = st.selectbox(
                    "Selecciona un personaje para eliminar",
                    personajes_disponibles
                )

                if st.button("Eliminar personaje seleccionado"):
                    st.session_state.characters_df = (
                        st.session_state.characters_df[
                            st.session_state.characters_df["Personaje"] != personaje_a_eliminar
                        ]
                        .reset_index(drop=True)
                    )

                    st.rerun()

            else:
                st.info("No hay personajes para eliminar.")

            with st.form("form_personajes"):
                edited_characters = st.data_editor(
                    st.session_state.characters_df[required_character_columns],
                    use_container_width=True,
                    num_rows="dynamic"
                )

                col_guardar, col_ordenar = st.columns([1, 1])

                with col_guardar:
                    guardar_personajes = st.form_submit_button("Guardar cambios")

                with col_ordenar:
                    ordenar_personajes = st.form_submit_button("Ordenar personajes por ID")

                if guardar_personajes:
                    st.session_state.characters_df = edited_characters.fillna("").copy()
                    st.success("Personajes actualizados correctamente.")

                if ordenar_personajes:
                    edited_characters = edited_characters.fillna("").copy()

                    edited_characters["ID"] = pd.to_numeric(
                        edited_characters["ID"],
                        errors="coerce"
                    )

                    edited_characters = (
                        edited_characters
                        .sort_values("ID")
                        .reset_index(drop=True)
                    )

                    edited_characters["ID"] = range(
                        1,
                        len(edited_characters) + 1
                    )

                    st.session_state.characters_df = edited_characters.copy()

                    st.success("Personajes ordenados correctamente.")
                    st.rerun()

            col_left, col_excel, col_pdf = st.columns([6, 1, 1])

            with col_excel:
                st.download_button(
                    label="Excel",
                    data=dataframe_to_excel(st.session_state.characters_df),
                    file_name="personajes.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with col_pdf:
                st.download_button(
                    label="PDF",
                    data=dataframe_to_pdf(
                        st.session_state.characters_df,
                        "Reporte de Personajes"
                    ),
                    file_name="personajes.pdf",
                    mime="application/pdf"
                )
        
        with subtab5:
            st.markdown("### Octavos")

            octavos_df = st.session_state.scenes_df[[
                "Escena",
                "Locación",
                "INT/EXT",
                "Tiempo",
                "Octavos"
            ]].copy()

            edited_octavos = st.data_editor(
                octavos_df,
                use_container_width=True,
                num_rows="dynamic",
                key="octavos_review_editor"
            )

            for _, row in edited_octavos.iterrows():
                escena = row["Escena"]

                st.session_state.scenes_df.loc[
                    st.session_state.scenes_df["Escena"] == escena,
                    "Octavos"
                ] = row["Octavos"]

            total_octavos = sum(
                octavos_to_number(x)
                for x in st.session_state.scenes_df["Octavos"]
            )

            st.info(f"Total del guion: {number_to_octavos(total_octavos)}")

        with subtab6:
            st.markdown("### Validación del análisis")

            validation_rows = []

            for _, row in st.session_state.scenes_df.iterrows():
                issues = []

                if not str(row.get("Encabezado de escena", "")).strip():
                    issues.append("Falta encabezado")

                if not str(row.get("INT/EXT", "")).strip():
                    issues.append("Falta INT/EXT")

                if not str(row.get("Locación", "")).strip():
                    issues.append("Falta locación")

                if not str(row.get("Tiempo", "")).strip():
                    issues.append("Falta tiempo")

                if not str(row.get("Octavos", "")).strip():
                    issues.append("Faltan octavos")

                validation_rows.append({
                    "Escena": row.get("Escena", ""),
                    "Estado": "Revisar" if issues else "Validada",
                    "Observaciones": ", ".join(issues) if issues else "Sin observaciones"
                })

            validation_df = pd.DataFrame(validation_rows)

            st.dataframe(
                validation_df,
                use_container_width=True
            )

            total_validated = len(validation_df[validation_df["Estado"] == "Validada"])
            total_scenes = len(validation_df)

            st.success(f"Escenas validadas: {total_validated}/{total_scenes}")

        with subtab7:
            st.markdown("### Resumen general")

            total_octavos = sum(
                octavos_to_number(x)
                for x in st.session_state.scenes_df["Octavos"]
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Escenas", len(st.session_state.scenes_df))
            col2.metric("Personajes", len(st.session_state.characters_df))
            col3.metric("Locaciones", st.session_state.scenes_df["Locación"].nunique())
            col4.metric("Octavos totales", number_to_octavos(total_octavos))

            st.dataframe(
                st.session_state.scenes_df,
                use_container_width=True
            )

        with subtab8:
            st.markdown("### Guardar / Abrir proyecto")

            st.download_button(
                label="Guardar proyecto actual en JSON",
                data=project_to_json(),
                file_name="proyecto_cineplan.json",
                mime="application/json"
            )

            st.info(
                "Para abrir un proyecto guardado, utiliza el menú lateral en la sección Abrir proyecto guardado."
            )