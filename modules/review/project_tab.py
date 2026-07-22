import streamlit as st
import plotly.graph_objects as go

from components.header import render_section_header
from components.icons import ANALYTICS, DESCRIPTION, INFO, PROJECT, SCENE, STATUS, UPLOAD_FILE
from components.panel import cine_panel
from modules.screenplay_viewer import ScreenplayViewerState, render_screenplay_viewer


LINES_PER_PAGE = 55


def split_script_into_pages(script_text):
    if not script_text:
        return [""]

    lines = script_text.splitlines()

    return [
        "\n".join(lines[i:i + LINES_PER_PAGE])
        for i in range(0, len(lines), LINES_PER_PAGE)
    ] or [""]


def make_donut(labels, values, colors):
    total = sum(values)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=colors),
                textinfo="percent",
                textposition="outside",
                hoverinfo="label+value+percent",
                sort=False,
                pull=[0.015] * len(values),
                textfont=dict(size=14, color="#f8fafc")
            )
        ]
    )

    fig.update_layout(
        annotations=[
            dict(
                text=(
                    f"<b>{total}</b><br>"
                    "<span style='font-size:12px'>ESCENAS</span>"
                ),
                x=0.5,
                y=0.5,
                font=dict(size=24, color="#f8fafc"),
                showarrow=False
            )
        ],
        showlegend=False,
        height=320,
        margin=dict(l=35, r=35, t=20, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1")
    )

    return fig


def get_project_stats():
    stats = {
        "locations_count": 0,

        "type_labels": [
            "INT.",
            "EXT.",
            "I/E",
            "Sin clasificar"
        ],
        "type_values": [0, 0, 0, 0],
        "type_colors": [
            "#ef4444",
            "#f97316",
            "#94a3b8",
            "#334155"
        ],

        "time_labels": [
            "Día",
            "Noche",
            "Amanecer / Atardecer",
            "Sin clasificar"
        ],
        "time_values": [0, 0, 0, 0],
        "time_colors": [
            "#facc15",
            "#3b82f6",
            "#8b5cf6",
            "#334155"
        ],

        "status_labels": [
            "Revisado",
            "Pendiente / Otros"
        ],
        "status_values": [0, 0],
        "status_colors": [
            "#22c55e",
            "#94a3b8"
        ],
    }

    if (
        "scenes_df" not in st.session_state
        or st.session_state.scenes_df.empty
    ):
        return stats

    scenes_df = st.session_state.scenes_df.copy()
    total_scenes = len(scenes_df)

    if "Locación" in scenes_df.columns:
        stats["locations_count"] = (
            scenes_df["Locación"]
            .fillna("")
            .astype(str)
            .str.strip()
            .replace("", "SIN LOCACIÓN")
            .nunique()
        )

    if "INT/EXT" in scenes_df.columns:
        int_ext = (
            scenes_df["INT/EXT"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )

        ie_mask = int_ext.str.contains("I/E", na=False)

        int_mask = (
            int_ext.str.contains("INT", na=False)
            & ~ie_mask
        )

        ext_mask = (
            int_ext.str.contains("EXT", na=False)
            & ~ie_mask
        )

        ie_count = int(ie_mask.sum())
        int_count = int(int_mask.sum())
        ext_count = int(ext_mask.sum())

        classified = int_count + ext_count + ie_count
        unclassified = total_scenes - classified

        stats["type_values"] = [
            int_count,
            ext_count,
            ie_count,
            max(0, unclassified)
        ]

    if "Tiempo" in scenes_df.columns:
        tiempo = (
            scenes_df["Tiempo"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )

        especial_mask = tiempo.str.contains(
            "AMANECER|ATARDECER|TARDE|MADRUGADA",
            na=False
        )

        dia_mask = (
            tiempo.str.contains("DÍA|DIA", na=False)
            & ~especial_mask
        )

        noche_mask = (
            tiempo.str.contains("NOCHE", na=False)
            & ~especial_mask
        )

        dia_count = int(dia_mask.sum())
        noche_count = int(noche_mask.sum())
        especial_count = int(especial_mask.sum())

        classified = dia_count + noche_count + especial_count
        unclassified = total_scenes - classified

        stats["time_values"] = [
            dia_count,
            noche_count,
            especial_count,
            max(0, unclassified)
        ]

    if "Estado" in scenes_df.columns:
        estado = (
            scenes_df["Estado"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )

        revisado_count = int(estado.eq("REVISADO").sum())
        otros_count = total_scenes - revisado_count

        stats["status_values"] = [
            revisado_count,
            otros_count
        ]
    else:
        stats["status_values"] = [
            0,
            total_scenes
        ]

    return stats


def render_stat_list(labels, values, colors):
    total = max(1, sum(values))

    for label, value, color in zip(labels, values, colors):
        percent = int((value / total) * 100)

        st.markdown(
            f"""
            <div style="
                display:flex;
                align-items:center;
                justify-content:space-between;
                padding:10px 0;
                border-bottom:1px solid rgba(148,163,184,.16);
            ">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="
                        width:12px;
                        height:12px;
                        border-radius:999px;
                        background:{color};
                        display:inline-block;
                    "></span>
                    <span style="color:#f8fafc;font-size:16px;">{label}</span>
                </div>
                <div style="text-align:right;">
                    <strong style="color:#f8fafc;font-size:22px;">{value}</strong>
                    <span style="color:#94a3b8;font-size:14px;margin-left:10px;">{percent}%</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_project_tab():

    if "project_info" not in st.session_state:
        st.session_state.project_info = {}

    project_name = st.session_state.project_info.get(
        "nombre",
        "Proyecto sin título"
    )

    script_text = st.session_state.get("script_text", "")
    total_pages = len(split_script_into_pages(script_text))

    scenes_count = len(st.session_state.get("scenes_df", []))
    characters_count = len(st.session_state.get("characters_df", []))
    stats = get_project_stats()

    render_section_header(
        icon=PROJECT,
        title="Proyecto",
        description=(
            "Confirma los datos principales del proyecto y verifica el guion importado."
        )
    )

    col_left, col_right = st.columns([1, 2.45], gap="large")

    with col_left:
        st.markdown('<span class="cp-project-upper-left-marker"></span>', unsafe_allow_html=True)

        with cine_panel(
            title=f":material/{INFO}: Información del proyecto",
            subtitle="Datos generales"
        ):

            st.session_state.project_info["nombre"] = st.text_input(
                "Nombre del proyecto",
                project_name
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

        with cine_panel(
            title=f":material/{UPLOAD_FILE}: Archivo importado",
            subtitle="Guion base"
        ):

            st.write(
                f"**Archivo:** "
                f"{st.session_state.get('nombre_archivo_guion', 'Sin archivo')}"
            )

            st.write(
                f"**Formato:** "
                f"{st.session_state.get('source_type', '-')}"
            )

            st.write(
                f"**Fecha:** "
                f"{st.session_state.get('fecha_importacion_guion', '-')}"
            )

        with cine_panel(
            title=f":material/{ANALYTICS}: Resumen del guion",
            subtitle="Datos detectados"
        ):

            c1, c2 = st.columns(2)
            c1.metric("Escenas", scenes_count)
            c2.metric("Páginas", total_pages)

            c3, c4 = st.columns(2)
            c3.metric("Personajes", characters_count)
            c4.metric("Locaciones", stats["locations_count"])

    with col_right:
        st.markdown('<span class="cp-project-upper-right-marker"></span>', unsafe_allow_html=True)

        with cine_panel(
            title=f":material/{DESCRIPTION}: Vista previa del guion",
            subtitle="Documento de trabajo"
        ):
            render_screenplay_viewer(
                source_type=st.session_state.get("source_type", ""),
                original_file_bytes=st.session_state.get("screenplay_source_bytes"),
                script_text=script_text,
                filename=st.session_state.get("nombre_archivo_guion", "guion.pdf"),
                navigation=ScreenplayViewerState(page=1),
            )

    with cine_panel(
        title=f":material/{ANALYTICS}: Estadísticas rápidas",
        subtitle="Resumen visual actualizado del guion importado"
    ):

        chart_col1, chart_col2, chart_col3 = st.columns(3, gap="large")

        with chart_col1:
            inner_chart, inner_list = st.columns([1.15, 1])

            with inner_chart:
                st.plotly_chart(
                    make_donut(
                        stats["type_labels"],
                        stats["type_values"],
                        stats["type_colors"]
                    ),
                    use_container_width=True
                )

            with inner_list:
                st.markdown(f"#### :material/{SCENE}: Tipo de escena")
                render_stat_list(
                    stats["type_labels"],
                    stats["type_values"],
                    stats["type_colors"]
                )

        with chart_col2:
            inner_chart, inner_list = st.columns([1.15, 1])

            with inner_chart:
                st.plotly_chart(
                    make_donut(
                        stats["time_labels"],
                        stats["time_values"],
                        stats["time_colors"]
                    ),
                    use_container_width=True
                )

            with inner_list:
                st.markdown(f"#### :material/{INFO}: Tiempo")
                render_stat_list(
                    stats["time_labels"],
                    stats["time_values"],
                    stats["time_colors"]
                )

        with chart_col3:
            inner_chart, inner_list = st.columns([1.15, 1])

            with inner_chart:
                st.plotly_chart(
                    make_donut(
                        stats["status_labels"],
                        stats["status_values"],
                        stats["status_colors"]
                    ),
                    use_container_width=True
                )

            with inner_list:
                st.markdown(f"#### :material/{STATUS}: Estado")
                render_stat_list(
                    stats["status_labels"],
                    stats["status_values"],
                    stats["status_colors"]
                )
