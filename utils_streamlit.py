import streamlit as st
import pandas as pd


def df_to_csv_download(df: pd.DataFrame, filename: str, label: str):
    """
    Descarga un DataFrame como CSV con separador ; y BOM UTF-8,
    con un botón de Streamlit.
    """
    csv_bytes = df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )
