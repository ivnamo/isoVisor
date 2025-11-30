import streamlit as st
import pandas as pd


def df_to_csv_download(df: pd.DataFrame, filename: str, label: str):
    """
    Descarga un DataFrame como CSV con separador ; y codificación Windows-1252,
    más compatible con Excel en castellano (evita textos tipo 'FÃ³rmula OK').
    """
    # Codificación pensada para que Excel abra bien las tildes por defecto
    csv_bytes = df.to_csv(
        index=False,
        sep=";",
        encoding="cp1252",   # antes: "utf-8-sig"
        errors="replace",     # por si aparece algún carácter raro fuera de cp1252
    )
    st.download_button(
        label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )
