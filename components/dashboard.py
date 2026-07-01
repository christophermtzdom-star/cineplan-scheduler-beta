def calcular_progreso():
    """
    Calcula el porcentaje general del proyecto.
    """

    import streamlit as st

    progreso = 0

    # 1. Guion importado
    if not st.session_state.scenes_df.empty:
        progreso += 20

    return progreso
def siguiente_paso():
    import streamlit as st

    if st.session_state.scenes_df.empty:
        return "📄 Importa un guion PDF o FDX para comenzar."

    return "📝 Revisa y corrige la información detectada antes de continuar."