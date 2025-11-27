import streamlit as st
import pandas as pd

from models import (
    BBDD_COLUMNS,
    build_informe_iso,
    build_informe_iso_excel_all,
    build_ensayos_dict_from_df,
    normalize_columns,
)


def render_visor_page():
    st.subheader("📥 Cargar BBDD F10-02 (CSV)")

    uploaded_view = st.file_uploader(
        "Sube la BBDD (CSV) exportada desde el modo anterior o desde otro sistema",
        type=["csv"],
        key="uploader_view",
    )

    # 1) Cargar BBDD: CSV subido o BBDD en sesión
    if uploaded_view is not None:
        df_bbdd = pd.read_csv(uploaded_view, sep=None, engine="python")
    else:
        df_bbdd = st.session_state.get("bbdd", pd.DataFrame(columns=BBDD_COLUMNS))

    # 2) Normalizar nombres de columnas (Responsable, BOM, espacios, etc.)
    df_bbdd = normalize_columns(df_bbdd)

    if df_bbdd.empty:
        st.info(
            "No hay datos en la BBDD. Sube un CSV o registra ensayos en el otro modo."
        )
        return

    # 3) Asegurar columnas esperadas
    for c in BBDD_COLUMNS:
        if c not in df_bbdd.columns:
            df_bbdd[c] = ""

    df_bbdd = df_bbdd[BBDD_COLUMNS]

    # Vista rápida
    st.markdown("### Vista rápida BBDD (F10-02 plano)")
    st.dataframe(df_bbdd.head(200), height=250)

    # 4) Selector de Nº Solicitud
    st.markdown("### Seleccionar Nº de Solicitud")
    solicitudes = df_bbdd["Nº Solicitud"].fillna("(sin Nº)").unique().tolist()
    def natural_sort_key(x):
        try:
            return (0, float(x))
        except:
            return (1, str(x))
    solicitudes = sorted(solicitudes, key=natural_sort_key)
    solicitud_sel = st.selectbox("Nº Solicitud", solicitudes)

    df_sel = df_bbdd[df_bbdd["Nº Solicitud"].fillna("(sin Nº)") == solicitud_sel].copy()

    if df_sel.empty:
        st.warning("No hay filas para ese Nº de solicitud.")
        return

    # 5) Datos de partida del diseño
    meta_row = df_sel.iloc[0].to_dict()

    st.markdown("### 1. Datos de partida del diseño (F10-02 · 1)")
    with st.container():
        responsable = (
            meta_row.get("Responsable")
            or meta_row.get("Responsable de proyecto")
            or ""
        )
        st.write(f"**Responsable:** {responsable}")
        st.write(
            f"**Nº Solicitud:** {meta_row.get('Nº Solicitud', '')} &nbsp;&nbsp; "
            f"**Tipo:** {meta_row.get('Tipo', '')}"
        )
        st.write(f"**Producto base / línea:** {meta_row.get('Producto base', '')}")
        st.write("**Descripción de los datos de partida del diseño:**")
        st.write(meta_row.get("Descripción diseño", ""))

    # 6) Ensayos / formulaciones agrupados
    st.markdown("### 2. Ensayos / formulaciones (F10-02 · 2)")

    ensayos_dict = build_ensayos_dict_from_df(df_sel)

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
                st.dataframe(df_formula, height=200)

    # 7) Verificación
    st.markdown("### 3. Verificación (F10-02 · 3)")
    with st.container():
        st.write(f"**Producto final:** {meta_row.get('Producto final', '')}")
        st.write(f"**Fórmula OK:** {meta_row.get('Fórmula OK', '')}")
        st.write(f"**Riquezas:** {meta_row.get('Riquezas', '')}")

    # 8) Botón para informe ISO tipo CSV (solo esta solicitud)
    st.markdown("### 4. Exportar informe ISO (CSV) para este Nº de Solicitud")

    informe_bytes = build_informe_iso(meta_row, ensayos_dict)
    st.download_button(
        label="📥 Descargar informe ISO (CSV)",
        data=informe_bytes,
        file_name=f"Informe_{solicitud_sel}.csv",
        mime="text/csv",
    )

    # 9) Botón para informe ISO XLSX con TODAS las solicitudes (una hoja por cada Nº)
    st.markdown("### 5. Exportar informe ISO (XLSX) para TODAS las solicitudes")

    xlsx_bytes = build_informe_iso_excel_all(df_bbdd)
    st.download_button(
        label="📥 Descargar informe ISO (XLSX) · todas las solicitudes",
        data=xlsx_bytes,
        file_name="Informe_ISO_todas_solicitudes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
