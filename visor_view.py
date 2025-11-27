import streamlit as st
import pandas as pd

from models import BBDD_COLUMNS, build_informe_iso


def render_visor_page():
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
        st.info(
            "No hay datos en la BBDD. Sube un CSV o registra ensayos en el otro modo."
        )
        return

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
        return

    # Meta (primera fila)
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
