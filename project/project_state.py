import streamlit as st


def get_dashboard_data():
    """
    Devuelve toda la información necesaria para el Dashboard.
    """

    scenes_df = st.session_state.get("scenes_df")
    characters_df = st.session_state.get("characters_df")
    project_info = st.session_state.get("project_info", {})

    scenes_count = len(scenes_df) if scenes_df is not None else 0
    characters_count = len(characters_df) if characters_df is not None else 0

    locations_count = 0

    if (
        scenes_df is not None
        and not scenes_df.empty
        and "Locación" in scenes_df.columns
    ):
        locations_count = scenes_df["Locación"].nunique()

    # ---------------------------------------
    # PROGRESO GENERAL
    # ---------------------------------------

    progress = 0

    if scenes_count > 0:
        progress = 20

    # ---------------------------------------
    # FLUJO DE TRABAJO
    # ---------------------------------------

    workflow = {
        "importar": "en_progreso",
        "revision": "bloqueado",
        "breakdown": "bloqueado",
        "stripboard": "bloqueado",
        "plan_rodaje": "bloqueado",
        "hojas_llamado": "bloqueado",
    }

    if scenes_count > 0:
        workflow["importar"] = "completado"
        workflow["revision"] = "en_progreso"

    # ---------------------------------------
    # DATOS PARA EL DASHBOARD
    # ---------------------------------------

    return {

    # ---------------------------------------
    # PROYECTO
    # ---------------------------------------

        "project": {
            "name": project_info.get("nombre", "Proyecto sin título"),
            "director": project_info.get("director", ""),
            "producer": project_info.get("productor", "")
        },

    # ---------------------------------------
    # GUION
    # ---------------------------------------

        "script": {
            "name": st.session_state.get("nombre_archivo_guion", ""),
            "type": st.session_state.get("tipo_archivo_guion", ""),
            "date": st.session_state.get("fecha_importacion_guion", "")
        },

    # ---------------------------------------
    # ESTADÍSTICAS
    # ---------------------------------------

        "stats": {

            "scenes": scenes_count,

            "characters": characters_count,

            "locations": locations_count,

            # Se calcularán automáticamente más adelante
            "total_eighths": 0,

            "estimated_duration": "-",

            "shoot_days": 0,

            "call_sheets": 0,

            "completed_breakdown": 0
        },

    # ---------------------------------------
    # PROGRESO GENERAL
    # ---------------------------------------

        "progress": progress,

    # ---------------------------------------
    # FLUJO DE TRABAJO
    # ---------------------------------------

        "workflow": workflow,

    # ---------------------------------------
    # ACTIVIDAD RECIENTE
    # ---------------------------------------

        "recent_activity": [

            {
                "icon": "description",
                "title": "Proyecto creado",
                "time": "-"
            }

        ],

    # ---------------------------------------
    # ACCIONES RÁPIDAS
    # ---------------------------------------

        "quick_actions": [

            {
                "id": "importar",
                "title": "Importar Guion"
            },

            {
                "id": "revision",
                "title": "Revisar y Modificar"
            },

            {
                "id": "breakdown",
                "title": "Breakdown"
            },

            {
                "id": "stripboard",
                "title": "Stripboard"
            },

            {
                "id": "plan_rodaje",
                "title": "Plan de Rodaje"
            },

            {
                "id": "hojas_llamado",
                "title": "Hojas de Llamado"
            }

        ]

    }