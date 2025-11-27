import streamlit as st
from models import init_bbdd
from registro_view import render_registro_page
from visor_view import render_visor_page

st.set_page_config(
    page_title="F10-02 / F10-03 · Diseño y Validación de Producto",
    layout="wide",
)

# Inicializar BBDD en sesión
init_bbdd(st.session_state)

st.title("F10-02 / F10-03 · Diseño y Validación de Producto")

mode = st.sidebar.radio(
    "Modo",
    (
        "Registrar diseños y ensayos (F10-02/F10-03)",
        "Visor BBDD e informes ISO",
    ),
)

if mode == "Registrar diseños y ensayos (F10-02/F10-03)":
    render_registro_page()
else:
    render_visor_page()
