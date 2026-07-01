import streamlit as st


def cine_project_status(
    script_imported=False,
    review_complete=False,
    breakdown_complete=False,
    stripboard_complete=False,
    shooting_plan_complete=False,
    callsheet_complete=False,
):
    st.markdown("### 📋 Estado del proyecto")

    estados = [
        ("Guion importado", script_imported),
        ("Revisión del guion", review_complete),
        ("Breakdown", breakdown_complete),
        ("Stripboard", stripboard_complete),
        ("Plan de rodaje", shooting_plan_complete),
        ("Hojas de llamado", callsheet_complete),
    ]

    for nombre, estado in estados:
        if estado:
            st.success(f"✓ {nombre}")
        else:
            st.info(f"○ {nombre}")