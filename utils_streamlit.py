import streamlit as st
import pandas as pd


def df_to_csv_download(df: pd.DataFrame, filename: str, label: str):
    """
    Descarga un DataFrame como CSV con separador ; y BOM UTF-8,
    con un botón de Streamlit.
    Excel detecta bien la codificación y muestra tildes (Fórmula, etc.).
    """
    # 1) Generamos el CSV como texto (pandas ignora 'encoding' si no hay fichero)
    csv_str = df.to_csv(index=False, sep=";")

    # 2) Lo convertimos explícitamente a bytes UTF-8 con BOM
    csv_bytes = csv_str.encode("utf-8-sig")

    # 3) Streamlit recibe los bytes ya codificados
    st.download_button(
        label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )

