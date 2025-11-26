import streamlit as st
import pandas as pd
from datetime import date
import io

st.set_page_config(
    page_title="F10-02 / F10-03 · Diseño y Validación de Producto",
    layout="wide",
)

# ===============================
# Utils
# ===============================

BBDD_COLUMNS = [
    "Responsable",
    "Nº Solicitud",
    "Tipo",
    "Producto base",
    "Descripción diseño",
    "ID ensayo",
    "Nombre formulación",
    "Fecha ensayo",
    "Resultado",
    "Materia prima",
    "% peso",
    "Motivo / comentario",
    "Producto final",
    "Fórmula OK",
    "Riquezas",
]


def init_bbdd():
    if "bbdd" not in st.session_state:
        st.session_state["bbdd"] = pd.DataFrame(columns=BBDD_COLUMNS)


def parse_receta_text(text: str):
    """
    Pega aquí bloque tipo:

    M01 F3\t86,46
    ALANTOINA\t0,50
    ...
    o con ; o con coma/espacio.

    Devuelve lista de dicts {materia, pct}.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []
    for line in lines:
        sep = None
        if "\t" in line:
            sep = "\t"
        elif ";" in line:
            sep = ";"
        elif "," in line:
            # ojo: coma puede ser separador o decimal
            # intentamos primero como separador ; si no hay, usamos coma como separador
            parts_tmp = line.split(",")
            if len(parts_tmp) > 2:
                sep = ","
        if sep is None:
            parts = line.split()
            if len(parts) < 2:
                continue
            pct = parts[-1]
            materia = " ".join(parts[:-1])
        else:
            parts = [p.strip() for p in line.split(sep) if p.strip()]
            if len(parts) < 2:
                continue
            materia, pct = parts[0], parts[1]
        rows.append({"materia": materia, "pct": pct})
    return rows


def df_to_csv_download(df: pd.DataFrame, filename: str) -> None:
    csv_bytes = df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        "📥 Descargar " + filename,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


def build_informe_iso(meta: dict, ensayos: dict) -> bytes:
    """
    Genera un CSV "maquetado" tipo informe ISO:
    - 1. Datos de partida
    - 2. Ensayos verticales con fórmulas
    - 3. Verificación (producto final, fórmula OK, riquezas)
    """
    rows = []

    rows.append(["Responsable de proyecto:", meta.get("Responsable", "")])
    rows.append(
        [
            "Nº Solicitud:",
            meta.get("Nº Solicitud", ""),
            "Tipo:",
            meta.get("Tipo", ""),
        ]
    )
    rows.append(["Producto base / línea:", meta.get("Producto base", "")])
    rows.append([])
    rows.append(["1. DATOS DE PARTIDA DEL DISEÑO"])
    rows.append([meta.get("Descripción diseño", "")])
    rows.append([])
    rows.append(["2. ENSAYOS / FORMULACIONES"])
    rows.append([])

    for i, (ensayo_key, e) in enumerate(ensayos.items(), start=1):
        rows.append([f"Ensayo {i}", e["id"], e["nombre"]])
        rows.append(["Fecha ensayo:", e["fecha"], "Resultado:", e["resultado"]])
        rows.append([])
        rows.append(["Materia prima", "% peso"])
        for m in e["materias"]:
            rows.append([m["Materia prima"], m["% peso"]])
        rows.append([])
        rows.append(["Motivo / comentario:", e["motivo"]])
        rows.append([])
        rows.append([])

    rows.append(["3. VERIFICACIÓN"])
    rows.append(["Producto final:", meta.get("Producto final", "")])
    rows.append(["Fórmula OK:", meta.get("Fórmula OK", "")])
    rows.append(["Riquezas:", meta.get("Riquezas", "")])
    rows.append([])

    # Convertir a CSV (texto) con ; y BOM
    out_lines = []
    for cols in rows:
        line_cells = []
        for c in cols:
            t = str(c) if c is not None else ""
            t = t.replace("\r", " ").replace("\n", " ").strip()
            if '"' in t:
                t = t.replace('"', '""')
            if any(ch in t for ch in [';', '"']):
                t = f'"{t}"'
            line_cells.append(t)
        out_lines.append(";".join(line_cells))
    csv_content = "\r\n".join(out_lines)
    # BOM
    return ("\ufeff" + csv_content).encode("utf-8")


# ===============================
# UI
# ===============================

st.title("F10-02 / F10-03 · Diseño y Validación de Producto")

mode = st.sidebar.radio(
    "Modo",
    ("Registrar diseños y ensayos (F10-02/F10-03)", "Visor BBDD e informes ISO"),
)

init_bbdd()

# =====================================================
# MODO 1: REGISTRAR ENSAYOS / F10-02 / F10-03
# =====================================================
if mode == "Registrar diseños y ensayos (F10-02/F10-03)":
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

    motivoModificacion = st.text_area("Motivo / comentario (NOK, observaciones)", value="", height=120)

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

    if st.button("➕ Añadir ensayo al registro F10-02", type="primary", use_container_width=True):
        if not receta_text.strip():
            st.error("Primero pega la receta del ensayo.")
        elif not idEnsayo.strip():
            st.error("Rellena el ID de ensayo.")
        else:
            rows = parse_receta_text(receta_text)
            if not rows:
                st.error("No se han encontrado líneas válidas (materia prima + %). Revisa el texto pegado.")
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
        if st.button("🗑️ Borrar TODA la BBDD de esta sesión", use_container_width=True):
            st.session_state["bbdd"] = pd.DataFrame(columns=BBDD_COLUMNS)
            st.warning("BBDD vaciada en esta sesión.")
    with colB2:
        if len(st.session_state["bbdd"]) > 0:
            df_to_csv_download(st.session_state["bbdd"], "F10_02_BD_ensayos.csv")


# =====================================================
# MODO 2: VISOR BBDD + INFORME ISO
# =====================================================
else:
    st.subheader("📥 Cargar BBDD F10-02 (CSV)")

    uploaded_view = st.file_uploader(
        "Sube la BBDD (CSV) exportada desde el modo anterior o desde otro sistema",
        type=["csv"],
        key="uploader_view",
    )

    if uploaded_view is not None:
        df_bbdd = pd.read_csv(uploaded_view, sep=None, engine="python")
    else:
        # Si no sube nada y hay BBDD en sesión, la usamos como atajo
        df_bbdd = st.session_state.get("bbdd", pd.DataFrame(columns=BBDD_COLUMNS))

    if df_bbdd.empty:
        st.info("No hay datos en la BBDD. Sube un CSV o registra ensayos en el otro modo.")
        st.stop()

    # Asegurar columnas
    for c in BBDD_COLUMNS:
        if c not in df_bbdd.columns:
            df_bbdd[c] = ""

    df_bbdd = df_bbdd[BBDD_COLUMNS]

    st.markdown("### Vista rápida BBDD (F10-02 plano)")
    st.dataframe(df_bbdd.head(200), use_container_width=True, height=250)

    # Selector de Nº Solicitud
    st.markdown("### Seleccionar Nº de Solicitud")
    solicitudes = df_bbdd["Nº Solicitud"].fillna("(sin Nº)").unique().tolist()
    solicitudes = sorted(solicitudes, key=lambda x: str(x))
    solicitud_sel = st.selectbox("Nº Solicitud", solicitudes)

    df_sel = df_bbdd[df_bbdd["Nº Solicitud"].fillna("(sin Nº)") == solicitud_sel].copy()

    if df_sel.empty:
        st.warning("No hay filas para ese Nº de solicitud.")
        st.stop()

    # Meta (cojo primera fila)
    meta_row = df_sel.iloc[0].to_dict()

    st.markdown("### 1. Datos de partida del diseño (F10-02 · 1)")
    with st.container(border=True):
        st.write(f"**Responsable de proyecto:** {meta_row.get('Responsable', '')}")
        st.write(
            f"**Nº Solicitud:** {meta_row.get('Nº Solicitud', '')} &nbsp;&nbsp; "
            f"**Tipo:** {meta_row.get('Tipo', '')}"
        )
        st.write(f"**Producto base / línea:** {meta_row.get('Producto base', '')}")
        st.write("**Descripción de los datos de partida del diseño:**")
        st.write(meta_row.get("Descripción diseño", ""))

    # Agrupar ensayos para mostrar vertical + plegable
    st.markdown("### 2. Ensayos / formulaciones (F10-02 · 2)")
    grupos = (
        df_sel.groupby(
            [
                "ID ensayo",
                "Nombre formulación",
                "Fecha ensayo",
                "Resultado",
                "Motivo / comentario",
            ],
            dropna=False,
        )
        .agg({"Materia prima": list, "% peso": list})
        .reset_index()
    )

    ensayos_dict = {}

    for idx, row in grupos.iterrows():
        id_e = str(row["ID ensayo"])
        nombre_e = str(row["Nombre formulación"])
        fecha_e = str(row["Fecha ensayo"])
        resultado_e = str(row["Resultado"])
        motivo_e = str(row["Motivo / comentario"])
        materias = row["Materia prima"]
        pct = row["% peso"]
        mp_rows = []
        for m, p in zip(materias, pct):
            mp_rows.append({"Materia prima": m, "% peso": p})
        key = f"{id_e}||{nombre_e}"
        ensayos_dict[key] = {
            "id": id_e,
            "nombre": nombre_e,
            "fecha": fecha_e,
            "resultado": resultado_e,
            "motivo": motivo_e,
            "materias": mp_rows,
        }

    if not ensayos_dict:
        st.info("No se han encontrado ensayos para esta solicitud.")
    else:
        for i, (k, e) in enumerate(ensayos_dict.items(), start=1):
            etiqueta = f"Ensayo {i}: {e['id']} · {e['nombre']} ({e['resultado']})"
            expander = st.expander(etiqueta, expanded=False)
            with expander:
                st.write(
                    f"**Fecha ensayo:** {e['fecha']}  |  **Resultado:** {e['resultado']}"
                )
                st.write(f"**Motivo / comentario:** {e['motivo']}")
                st.write("**Fórmula (materias primas):**")
                df_formula = pd.DataFrame(e["materias"])
                st.dataframe(df_formula, use_container_width=True, height=200)

    # Verificación
    st.markdown("### 3. Verificación (F10-02 · 3)")
    with st.container(border=True):
        st.write(f"**Producto final:** {meta_row.get('Producto final', '')}")
        st.write(f"**Fórmula OK:** {meta_row.get('Fórmula OK', '')}")
        st.write(f"**Riquezas:** {meta_row.get('Riquezas', '')}")

    # Botón para informe ISO tipo CSV
    st.markdown("### 4. Exportar informe ISO (CSV) para este Nº de Solicitud")

    informe_bytes = build_informe_iso(meta_row, ensayos_dict)
    st.download_button(
        "📥 Descargar informe ISO (CSV)",
        data=informe_bytes,
        file_name=f"Informe_{solicitud_sel}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.info(
        "Abre el CSV en Excel (separador ;). Desde ahí puedes guardar como XLSX, "
        "ajustar bordes, fusionar celdas o añadir tu cabecera corporativa si el auditor lo pide."
    )
