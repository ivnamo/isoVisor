from datetime import date
import pandas as pd

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


def init_bbdd(session_state):
    """Inicializa la BBDD en sesión si no existe."""
    if "bbdd" not in session_state:
        session_state["bbdd"] = pd.DataFrame(columns=BBDD_COLUMNS)


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


def build_informe_iso(meta: dict, ensayos: dict) -> bytes:
    """
    Genera un CSV "maquetado" tipo informe ISO:
    - 1. Datos de partida
    - 2. Ensayos verticales con fórmulas
    - 3. Verificación (producto final, fórmula OK, riquezas)
    Devuelve bytes UTF-8 con BOM, listo para descargar.
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
