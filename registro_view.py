import streamlit as st
import pandas as pd
from datetime import date

from models import BBDD_COLUMNS, parse_receta_text
from utils_streamlit import df_to_csv_download


def render_registro_page():
    st.subheader("📥 Opcional: cargar BBDD existente (CSV)")

    uploaded_bbdd = st.file_uploader(
        "Sube un CSV previo (estructura F10-02) para continuar añadiendo ensayos",
        type=["csv"],
        key="uploader_registro",
    )

    col_load, col_info = st.columns([1, 2])
    with col_load:
        if uploaded_bbdd is not None:
            if st.button("Cargar CSV en BBDD actual", use_container_width=True):
                df_in = pd.read_csv(uploaded_bbdd, sep=None, engine="python")
                # Asegurar columnas
                missing = [c for c in BBDD_COLUMNS if c not in df_in.columns]
                for c in missing:
                    df_in[c] = ""
                st.session_state["bbdd"] = df_in[BBDD_COLUMNS]
                st.success(
                    f"BBDD cargada con {len(st.session_state['bbdd'])} filas."
                )
    with col_info:
        st.markdown(
            "_Si no subes nada, se empieza con una BBDD vacía (en esta sesión)._"
        )

    st.markdown("---")
    st.subheader("1. Datos de partida del diseño (F10-02 · 1)")

    col1, col2 = st.columns(2)
    with col1:
        respProyecto = st.text_input("Responsable de proyecto", value="")
        numSolicitud = st.text_input("Nº Solicitud", value="")
        tipoSolicitud = st.selectbox("Tipo", ["Interno", "Cliente"])
    with col2:
        productoBase = st.text_input("Producto / línea", value="")
        descripcionDiseno = st.text_area(
            "Descripción de los datos de partida del diseño",
            value="",
            height=120,
        )

    st.markdown("### 2. Ensayo / formulación (F10-02 · 2)")
    colE1, colE2, colE3, colE4 = st.columns(4)
    with colE1:
        idEnsayo = st.text_input("ID ensayo", value="")
    with colE2:
        nombreEnsayo = st.text_input("Nombre formulación", value="")
    with colE3:
        fechaEnsayo = st.date_input("Fecha ensayo", value=date.today())
    with colE4:
        resultadoEnsayo = st.selectbox("Resultado", ["NOK", "OK"])

    motivoModificacion = st.text_area(
        "Motivo / comentario (NOK, observaciones)",
        value="",
        height=120,
    )

    st.markdown("#### Receta del ensayo (pegar desde Excel)")
    receta_text = st.text_area(
        "Cada línea: materia prima + % peso (tabulado, punto y coma o espacio)",
        value="",
        height=120,
        key="receta_textarea",
    )

    st.markdown("### 3. Verificación (F10-02 · 3)")
    colV1, colV2, colV3 = st.columns(3)
    with colV1:
        productoVerificacion = st.text_input("Producto final", value="")
    with colV2:
        formulaOk = st.text_input("Fórmula OK (ref. ensayo / versión)", value="")
    with colV3:
        riquezas = st.text_input("Riquezas (garantías, NPK, micro...)", value="")

    if st.button(
        "➕ Añadir ensayo al registro F10-02",
        type="primary",
        use_container_width=True,
    ):
        if not receta_text.strip():
            st.error("Primero pega la receta del ensayo.")
        elif not idEnsayo.strip():
            st.error("Rellena el ID de ensayo.")
        else:
            rows = parse_receta_text(receta_text)
            if not rows:
                st.error(
                    "No se han encontrado líneas válidas (materia prima + %). Revisa el texto pegado."
                )
            else:
                new_records = []
                for r in rows:
                    new_records.append(
                        {
                            "Responsable": respProyecto.strip(),
                            "Nº Solicitud": numSolicitud.strip(),
                            "Tipo": tipoSolicitud,
                            "Producto base": productoBase.strip(),
                            "Descripción diseño": descripcionDiseno.strip(),
                            "ID ensayo": idEnsayo.strip(),
                            "Nombre formulación": nombreEnsayo.strip(),
                            "Fecha ensayo": fechaEnsayo.strftime("%Y-%m-%d"),
                            "Resultado": resultadoEnsayo,
                            "Materia prima": r["materia"],
                            "% peso": r["pct"],
                            "Motivo / comentario": motivoModificacion.strip(),
                            "Producto final": productoVerificacion.strip(),
                            "Fórmula OK": formulaOk.strip(),
                            "Riquezas": riquezas.strip(),
                        }
                    )

                df_new = pd.DataFrame(new_records, columns=BBDD_COLUMNS)
                st.session_state["bbdd"] = pd.concat(
                    [st.session_state["bbdd"], df_new], ignore_index=True
                )
                st.success(
                    f"Añadidas {len(new_records)} líneas para el ensayo {idEnsayo.strip()}."
                )

    st.markdown("### Tabla BBDD F10-02 (toda la sesión)")
    st.dataframe(st.session_state["bbdd"], use_container_width=True, height=300)

    colB1, colB2 = st.columns(2)
    with colB1:
        if st.button(
            "🗑️ Borrar TODA la BBDD de esta sesión", use_container_width=True
        ):
            st.session_state["bbdd"] = pd.DataFrame(columns=BBDD_COLUMNS)
            st.warning("BBDD vaciada en esta sesión.")
    with colB2:
        if len(st.session_state["bbdd"]) > 0:
            df_to_csv_download(
                st.session_state["bbdd"],
                "F10_02_BD_ensayos.csv",
                "📥 Descargar BBDD F10-02 (CSV)",
            )
