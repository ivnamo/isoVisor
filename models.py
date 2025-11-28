from datetime import date
import pandas as pd
import io
import json

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
    # --- NUEVOS CAMPOS F10-03 ---
    "Spec_Descripcion",
    "Spec_Aspecto",
    "Spec_Color",
    "Spec_Densidad",
    "Spec_pH",
    "Spec_Quimica",
    "Validacion_JSON",
    "Fecha_Validacion",
]

# Tabla estándar para mostrar en el editor
VALIDACION_STD = [
    {"Área": "I+D+i", "Aspecto": "Fórmula - Funcionalidad", "Validar": True, "Comentarios": ""},
    {"Área": "Técnico", "Aspecto": "Validación agronómica", "Validar": True, "Comentarios": ""},
    {"Área": "Registros", "Aspecto": "Cumplimiento legislativo", "Validar": True, "Comentarios": ""},
    {"Área": "Producción", "Aspecto": "Viabilidad productiva", "Validar": True, "Comentarios": ""},
    {"Área": "Calidad", "Aspecto": "Cumplimiento legislativo", "Validar": True, "Comentarios": ""},
    {"Área": "Calidad", "Aspecto": "Composición declarada", "Validar": True, "Comentarios": ""},
    {"Área": "Calidad", "Aspecto": "Estabilidad química", "Validar": True, "Comentarios": ""},
    {"Área": "Marketing/Dir", "Aspecto": "Precio Tarifa", "Validar": True, "Comentarios": ""},
    {"Área": "Marketing/Dir", "Aspecto": "Lanzamiento", "Validar": True, "Comentarios": ""},
]

# ==============================================================================
# FUNCIONES BBDD Y PARSING
# ==============================================================================

def init_bbdd(session_state):
    if "bbdd" not in session_state:
        session_state["bbdd"] = pd.DataFrame(columns=BBDD_COLUMNS)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
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
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []
    for line in lines:
        sep = None
        if "\t" in line: sep = "\t"
        elif ";" in line: sep = ";"
        elif "," in line:
            parts_tmp = line.split(",")
            if len(parts_tmp) > 2: sep = ","
        
        if sep is None:
            parts = line.split()
            if len(parts) < 2: continue
            pct = parts[-1]
            materia = " ".join(parts[:-1])
        else:
            parts = [p.strip() for p in line.split(sep) if p.strip()]
            if len(parts) < 2: continue
            materia, pct = parts[0], parts[1]
        rows.append({"materia": materia, "pct": pct})
    return rows

def build_ensayos_dict_from_df(df_sel: pd.DataFrame) -> dict:
    df_work = df_sel.copy()
    df_work["__fecha_orden"] = pd.to_datetime(df_work["Fecha ensayo"], errors="coerce", dayfirst=True)
    df_work["__fecha_orden"] = df_work["__fecha_orden"].fillna(pd.Timestamp("1970-01-01"))
    
    df_work = df_work.sort_values(["__fecha_orden", "ID ensayo", "Nombre formulación"], ascending=[True, True, True])

    grupos = df_work.groupby(
        ["ID ensayo", "Nombre formulación", "Fecha ensayo", "Resultado", "Motivo / comentario"],
        dropna=False, sort=False
    ).agg({"Materia prima": list, "% peso": list}).reset_index()

    ensayos_dict = {}
    for _, row in grupos.iterrows():
        id_e = str(row["ID ensayo"])
        key = f"{id_e}||{row['Nombre formulación']}"
        ensayos_dict[key] = {
            "id": id_e,
            "nombre": str(row["Nombre formulación"]),
            "fecha": str(row["Fecha ensayo"]),
            "resultado": str(row["Resultado"]),
            "motivo": str(row["Motivo / comentario"]),
            "materias": [{"Materia prima": m, "% peso": p} for m, p in zip(row["Materia prima"], row["% peso"])]
        }
    return ensayos_dict

# ==============================================================================
# GENERACIÓN DE INFORME (F10-02 + F10-03)
# ==============================================================================

def _build_informe_iso_rows(meta: dict, ensayos: dict):
    rows = []

    # --- CABECERA F10-02 ---
    rows.append(["Responsable:", meta.get("Responsable", "")])
    rows.append(["Nº Solicitud:", meta.get("Nº Solicitud", ""), "Tipo:", meta.get("Tipo", "")])
    rows.append(["Producto base / línea:", meta.get("Producto base", "")])
    rows.append([])
    
    # --- 1. DATOS PARTIDA ---
    rows.append(["1. DATOS DE PARTIDA DEL DISEÑO"])
    rows.append([meta.get("Descripción diseño", "")])
    rows.append([])
    
    # --- 2. ENSAYOS ---
    rows.append(["2. ENSAYOS / FORMULACIONES"])
    rows.append([])
    for i, (k, e) in enumerate(ensayos.items(), start=1):
        rows.append([f"Ensayo {i}", e["id"], e["nombre"]])
        rows.append(["Fecha ensayo:", e["fecha"], "Resultado:", e["resultado"]])
        rows.append([])
        rows.append(["Materia prima", "% peso"])
        for m in e["materias"]:
            rows.append([m["Materia prima"], m["% peso"]])
        rows.append([])
        rows.append(["Motivo / comentario:", e["motivo"]])
        rows.append([])
    
    # --- 3. VERIFICACIÓN BASICA ---
    rows.append(["3. VERIFICACIÓN (Diseño)"])
    rows.append(["Producto final:", meta.get("Producto final", "")])
    rows.append(["Fórmula OK:", meta.get("Fórmula OK", "")])
    rows.append(["Riquezas:", meta.get("Riquezas", "")])
    rows.append([])
    rows.append([])

    # =========================================================
    # NUEVO: SECCIÓN F10-03 (ESPECIFICACIÓN Y VALIDACIÓN)
    # =========================================================
    
    # Recuperamos los datos nuevos del meta
    desc = meta.get("Spec_Descripcion", "")
    aspecto = meta.get("Spec_Aspecto", "")
    color = meta.get("Spec_Color", "")
    densidad = meta.get("Spec_Densidad", "")
    ph = meta.get("Spec_pH", "")
    quimica = meta.get("Spec_Quimica", "")
    
    rows.append(["--- ANEXO F10-03: VALIDACIÓN DE PRODUCTO ---"])
    rows.append([])
    rows.append(["1. ESPECIFICACIÓN FINAL"])
    rows.append(["DESCRIPCIÓN:", desc])
    rows.append([])
    rows.append(["CARACTERÍSTICAS FÍSICAS"])
    rows.append(["Aspecto:", aspecto, "Color:", color])
    rows.append(["Densidad:", densidad, "pH:", ph])
    rows.append([])
    rows.append(["CARACTERÍSTICAS QUÍMICAS"])
    # Dividimos la química por líneas para que quede bien en Excel
    if quimica:
        for linea in str(quimica).splitlines():
            rows.append([linea])
    rows.append([])
    rows.append([])

    rows.append(["2. VALIDACIÓN (El producto satisface los requisitos)"])
    fecha_val = meta.get("Fecha_Validacion", "")
    rows.append(["Fecha de validación:", fecha_val])
    rows.append([])
    
    # Cabecera tabla validación
    rows.append(["ÁREA", "ASPECTO A VALIDAR", "VALIDAR (OK/NOK)", "COMENTARIOS"])

    # Decodificar el JSON de validación
    val_json_str = meta.get("Validacion_JSON", "")
    if val_json_str and isinstance(val_json_str, str) and len(val_json_str) > 2:
        try:
            val_data = json.loads(val_json_str)
            for item in val_data:
                estado = "OK" if item.get("Validar") else "NOK/Pendiente"
                rows.append([
                    item.get("Área", ""),
                    item.get("Aspecto", ""),
                    estado,
                    item.get("Comentarios", "")
                ])
        except:
            rows.append(["Error al leer datos de validación"])
    else:
        # Si no hay datos, ponemos la estructura vacía
        rows.append(["(Sin datos de validación registrados)"])

    return rows

def build_informe_iso(meta: dict, ensayos: dict) -> bytes:
    rows = _build_informe_iso_rows(meta, ensayos)
    out_lines = []
    for cols in rows:
        line_cells = []
        for c in cols:
            t = str(c) if c is not None else ""
            t = t.replace("\r", " ").replace("\n", " ").strip()
            if '"' in t: t = t.replace('"', '""')
            if any(ch in t for ch in [';', '"']): t = f'"{t}"'
            line_cells.append(t)
        out_lines.append(";".join(line_cells))
    csv_content = "\r\n".join(out_lines)
    return ("\ufeff" + csv_content).encode("utf-8")

def _sanitize_sheet_name(name: str, used: set) -> str:
    invalid = '[]:*?/\\'
    cleaned = "".join("_" if c in invalid else c for c in str(name))
    if not cleaned: cleaned = "Solicitud"
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
    for c in BBDD_COLUMNS:
        if c not in df_bbdd.columns: df_bbdd[c] = ""
    df_bbdd = df_bbdd[BBDD_COLUMNS]

    solicitudes = df_bbdd["Nº Solicitud"].fillna("(sin Nº)").unique().tolist()
    
    def natural_sort_key(x):
        try: return (0, float(x))
        except: return (1, str(x))
    solicitudes = sorted(solicitudes, key=natural_sort_key)

    output = io.BytesIO()
    used_sheet_names = set()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for solicitud in solicitudes:
            df_sel = df_bbdd[df_bbdd["Nº Solicitud"].fillna("(sin Nº)") == solicitud].copy()
            if df_sel.empty: continue

            meta_row = df_sel.iloc[0].to_dict()
            ensayos_dict = build_ensayos_dict_from_df(df_sel)
            
            # AQUÍ SE LLAMA A LA NUEVA ESTRUCTURA DE FILAS
            rows = _build_informe_iso_rows(meta_row, ensayos_dict)

            max_cols = max(len(r) for r in rows) if rows else 1
            normalized_rows = []
            for r in rows:
                r_extended = list(r) + [""] * (max_cols - len(r))
                normalized_rows.append(r_extended)
            df_sheet = pd.DataFrame(normalized_rows)

            sheet_name = _sanitize_sheet_name(solicitud, used_sheet_names)
            df_sheet.to_excel(writer, sheet_name=sheet_name, index=False, header=False)

    output.seek(0)
    return output.getvalue()
