from datetime import date
import pandas as pd
import io

# ==============================================================================
# CONFIGURACIÓN DE LA BBDD
# ==============================================================================

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
    # --- NUEVOS CAMPOS F10-03 (Especificación y Validación) ---
    "Spec_Descripcion",
    "Spec_Aspecto",
    "Spec_Color",
    "Spec_Densidad",
    "Spec_pH",
    "Spec_Quimica",
    "Validacion_JSON",  # Aquí guardaremos la tabla de validación completa
    "Fecha_Validacion",
]

# Estructura estándar para la tabla de validación (F10-03)
VALIDACION_STD = [
    {"Área": "I+D+i", "Aspecto": "Fórmula - Funcionalidad", "Validar": False, "Comentarios": ""},
    {"Área": "Técnico", "Aspecto": "Validación agronómica", "Validar": False, "Comentarios": ""},
    {"Área": "Registros", "Aspecto": "Cumplimiento legislativo", "Validar": False, "Comentarios": ""},
    {"Área": "Producción", "Aspecto": "Viabilidad productiva", "Validar": False, "Comentarios": ""},
    {"Área": "Calidad", "Aspecto": "Cumplimiento legislativo", "Validar": False, "Comentarios": ""},
    {"Área": "Calidad", "Aspecto": "Composición declarada", "Validar": False, "Comentarios": ""},
    {"Área": "Calidad", "Aspecto": "Estabilidad química", "Validar": False, "Comentarios": ""},
    {"Área": "Marketing/Dir", "Aspecto": "Precio Tarifa", "Validar": False, "Comentarios": ""},
    {"Área": "Marketing/Dir", "Aspecto": "Lanzamiento", "Validar": False, "Comentarios": ""},
]

# ==============================================================================
# FUNCIONES BBDD Y PARSING
# ==============================================================================

def init_bbdd(session_state):
    """Inicializa la BBDD en sesión si no existe."""
    if "bbdd" not in session_state:
        session_state["bbdd"] = pd.DataFrame(columns=BBDD_COLUMNS)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas:
    - Elimina BOM (\ufeff) y espacios.
    - Mapea cualquier columna que empiece por 'responsable' a 'Responsable'.
    """
    new_cols = []
    for c in df.columns:
        if isinstance(c, str):
            col = c.replace("\ufeff", "").strip()
            low = col.lower()
            if low.startswith("responsable"):
                col = "Responsable"
        else:
            col = c
        new_cols.append(col)
    df.columns = new_cols
    return df


def parse_receta_text(text: str):
    """
    Pega aquí bloque tipo:

    M01 F3\t86,46
    ALANTOINA\t0,50
    ...

    Soporta tabulador, ; o espacio. Devuelve lista de dicts {materia, pct}.
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
            # la coma puede ser decimal; solo la usamos como separador si hay muchas partes
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


def build_ensayos_dict_from_df(df_sel: pd.DataFrame) -> dict:
    """
    A partir de un df filtrado por Nº de solicitud, agrupa ensayos:
    - clave = ID ensayo + Nombre formulación
    - materias / % en lista
    Ordena por fecha de ensayo y por ID de ensayo.
    """
    df_work = df_sel.copy()

    # Columna auxiliar para ordenar por fecha (admite formatos tipo 11/03/2025 ó 2025-03-11)
    df_work["__fecha_orden"] = pd.to_datetime(
        df_work["Fecha ensayo"], errors="coerce", dayfirst=True
    )
    df_work["__fecha_orden"] = df_work["__fecha_orden"].fillna(pd.Timestamp("1970-01-01"))

    # Ordenar por fecha + ID + nombre formulación
    df_work = df_work.sort_values(
        ["__fecha_orden", "ID ensayo", "Nombre formulación"], ascending=[True, True, True]
    )

    grupos = (
        df_work.groupby(
            [
                "ID ensayo",
                "Nombre formulación",
                "Fecha ensayo",
                "Resultado",
                "Motivo / comentario",
            ],
            dropna=False,
            sort=False,  # respetar el orden ya aplicado en df_work
        )
        .agg({"Materia prima": list, "% peso": list})
        .reset_index()
    )

    ensayos_dict = {}

    for _, row in grupos.iterrows():
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

    return ensayos_dict


def _build_informe_iso_rows(meta: dict, ensayos: dict):
    """
    Devuelve la estructura del informe como lista de listas (filas / columnas),
    sin convertir todavía a CSV o Excel.
    """
    rows = []

    rows.append(["Responsable:", meta.get("Responsable", "")])
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

    return rows


def build_informe_iso(meta: dict, ensayos: dict) -> bytes:
    """
    Genera un CSV "maquetado" tipo informe ISO:
    - 1. Datos de partida
    - 2. Ensayos verticales con fórmulas
    - 3. Verificación (producto final, fórmula OK, riquezas)
    Devuelve bytes UTF-8 con BOM, listo para descargar como CSV.
    """
    rows = _build_informe_iso_rows(meta, ensayos)

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


def _sanitize_sheet_name(name: str, used: set) -> str:
    """
    Limpia el nombre de hoja para Excel (31 chars máx, sin caracteres raros) y
    evita duplicados añadiendo sufijos.
    """
    invalid = '[]:*?/\\'
    cleaned = "".join("_" if c in invalid else c for c in str(name))
    if not cleaned:
        cleaned = "Solicitud"
    cleaned = cleaned[:31]
    base = cleaned
    i = 1
    while cleaned in used:
        suffix = f"_{i}"
        cleaned = (base[: 31 - len(suffix)]) + suffix
        i += 1
    used.add(cleaned)
    return cleaned


def build_informe_iso_excel_all(df_bbdd: pd.DataFrame) -> bytes:
    """
    Genera un XLSX con una hoja por Nº de Solicitud.
    Cada hoja lleva el informe ISO (mismas secciones que el CSV por solicitud).
    Devuelve bytes del XLSX.
    """
    # Asegurar columnas
    for c in BBDD_COLUMNS:
        if c not in df_bbdd.columns:
            df_bbdd[c] = ""

    df_bbdd = df_bbdd[BBDD_COLUMNS]

    # Lista de solicitudes (pueden ser números o texto)
    solicitudes = df_bbdd["Nº Solicitud"].fillna("(sin Nº)").unique().tolist()

    # Orden "natural": primero numéricos por valor, luego textos
    def natural_sort_key(x):
        try:
            return (0, float(x))
        except Exception:
            return (1, str(x))

    solicitudes = sorted(solicitudes, key=natural_sort_key)

    output = io.BytesIO()
    used_sheet_names = set()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for solicitud in solicitudes:
            df_sel = df_bbdd[
                df_bbdd["Nº Solicitud"].fillna("(sin Nº)") == solicitud
            ].copy()
            if df_sel.empty:
                continue

            meta_row = df_sel.iloc[0].to_dict()
            ensayos_dict = build_ensayos_dict_from_df(df_sel)
            rows = _build_informe_iso_rows(meta_row, ensayos_dict)

            # convertir filas a DataFrame (rellenando hasta el nº máximo de columnas)
            max_cols = max(len(r) for r in rows) if rows else 1
            normalized_rows = []
            for r in rows:
                r_extended = list(r) + [""] * (max_cols - len(r))
                normalized_rows.append(r_extended)
            df_sheet = pd.DataFrame(normalized_rows)

            sheet_name = _sanitize_sheet_name(solicitud, used_sheet_names)
            df_sheet.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
                header=False,
            )

    output.seek(0)
    return output.getvalue()
