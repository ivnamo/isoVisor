import streamlit as st
import pandas as pd
import json
from datetime import date

from models import BBDD_COLUMNS, parse_receta_text, normalize_columns, VALIDACION_STD
from utils_streamlit import df_to_csv_download

def render_registro_page():
    st.subheader("📥 Opcional: cargar BBDD existente (CSV)")

    uploaded_bbdd = st.file_uploader(
        "Sube un CSV previo para continuar añadiendo ensayos",
        type=["csv"],
        key="uploader_registro",
    )

    col_load, col_info = st.columns([1, 2])
    with col_load:
        if uploaded_bbdd is not None:
            if st.button("Cargar CSV en BBDD actual", width="stretch"):
                df_in = pd.read_csv(uploaded_bbdd, sep=None, engine="python")
                df_in = normalize_columns(df_in)
                missing = [c for c in BBDD_COLUMNS if c not in df_in.columns]
                for c in missing: df_in[c] = ""
                st.session_state["bbdd"] = df_in[BBDD_COLUMNS]
                st.success(f"BBDD cargada correctamente ({len(df_in)} filas).")

    st.markdown("---")
    st.subheader("1. Datos de partida del diseño (F10-02 · 1)")

    col1, col2 = st.columns(2)
    with col1:
        respProyecto = st.text_input("Responsable", value="")
        numSolicitud = st.text_input("Nº Solicitud", value="")
        tipoSolicitud = st.selectbox("Tipo", ["Interno", "Cliente"])
    with col2:
        productoBase = st.text_input("Producto / línea", value="")
        descripcionDiseno = st.text_area("Descripción datos partida", value="", height=100)

    st.markdown("### 2. Ensayo / formulación (F10-02 · 2)")
    colE1, colE2, colE3, colE4 = st.columns(4)
    with colE1: idEnsayo = st.text_input("ID ensayo", value="")
    with colE2: nombreEnsayo = st.text_input("Nombre formulación", value="")
    with colE3: fechaEnsayo = st.date_input("Fecha ensayo", value=date.today())
    with colE4: resultadoEnsayo = st.selectbox("Resultado", ["NOK", "OK"])

    motivoModificacion = st.text_area("Motivo / comentario", value="", height=100)

    st.markdown("#### Receta del ensayo (pegar desde Excel)")
    receta_text = st.text_area("Materia prima + % peso", height=100, key="receta_textarea")

    st.markdown("### 3. Verificación Básica")
    colV1, colV2, colV3 = st.columns(3)
    with colV1: productoVerificacion = st.text_input("Producto final", value="")
    with colV2: formulaOk = st.text_input("Fórmula OK", value="")
    with colV3: riquezas = st.text_input("Riquezas (Resumen)", value="")

    # --- AQUÍ ESTÁ LO NUEVO QUE NO VEÍAS ANTES ---
    st.markdown("---")
    st.subheader("4. Especificación Final y Validación (F10-03)")

    with st.expander("📝 1. Especificaciones (F10-03)", expanded=True):
        st.markdown("**Descripción y Físico**")
        spec_desc = st.text_area("Descripción Larga (Marketing)", height=80)
        
        c_f1, c_f2, c_f3, c_f4 = st.columns(4)
        with c_f1: spec_aspecto = st.selectbox("Aspecto", ["Líquido", "Sólido", "Gel", "Suspensión"])
        with c_f2: spec_color = st.text_input("Color", "Blanquecino")
        with c_f3: spec_densidad = st.text_input("Densidad (g/cc)", "1,7")
        with c_f4: spec_ph = st.text_input("pH", "8 - 9")

        st.markdown("**Características Químicas (Lista detallada)**")
        spec_quimica = st.text_area("Pegar lista de riquezas", height=80)

    st.markdown("**2. Tabla de Validación**")
    if "df_val_temp" not in st.session_state:
        st.session_state["df_val_temp"] = pd.DataFrame(VALIDACION_STD)

    edited_val_df = st.data_editor(
        st.session_state["df_val_temp"],
        column_config={
            "Validar": st.column_config.CheckboxColumn("¿OK?", default=False),
            "Comentarios": st.column_config.TextColumn("Observaciones", width="large")
        },
        disabled=["Área", "Aspecto"],
        hide_index=True,
        width="stretch"
    )
    
    fecha_val = st.date_input("Fecha Validación", value=date.today())

    st.markdown("---")

    if st.button("➕ Añadir ensayo (Guardar todo)", type="primary", width="stretch"):
        if not receta_text.strip():
            st.error("Falta la receta.")
        elif not idEnsayo.strip():
            st.error("Falta ID ensayo.")
        else:
            rows = parse_receta_text(receta_text)
            if not rows:
                st.error("Error en formato receta.")
            else:
                new_records = []
                # Convertir tabla validación a texto para guardar
                val_json = edited_val_df.to_json(orient="records", force_ascii=False)
                fecha_val_str = fecha_val.strftime("%Y-%m-%d")

                for r in rows:
                    new_records.append({
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
                        # CAMPOS NUEVOS
                        "Spec_Descripcion": spec_desc,
                        "Spec_Aspecto": spec_aspecto,
                        "Spec_Color": spec_color,
                        "Spec_Densidad": spec_densidad,
                        "Spec_pH": spec_ph,
                        "Spec_Quimica": spec_quimica,
                        "Validacion_JSON": val_json,
                        "Fecha_Validacion": fecha_val_str
                    })

                df_new = pd.DataFrame(new_records, columns=BBDD_COLUMNS)
                st.session_state["bbdd"] = pd.concat([st.session_state["bbdd"], df_new], ignore_index=True)
                st.success(f"Guardado ensayo {idEnsayo} con datos F10-03.")

    st.markdown("### Tabla BBDD (Sesión)")
    st.dataframe(st.session_state["bbdd"], width="stretch", height=200)

    if len(st.session_state["bbdd"]) > 0:
        df_to_csv_download(st.session_state["bbdd"], "BBDD_Sesion.csv", "📥 Descargar BBDD Completa (CSV)")
