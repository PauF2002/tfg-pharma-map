import pandas as pd
from pathlib import Path
import unicodedata
import re

# AJUSTE PARA PROCESAR ALZHEIMER INE
BASE = Path(__file__).resolve().parents[2]
INP = BASE / "data" / "raw" / "ine_alzheimer_ccaa.csv"
OUT = BASE / "data" / "processed" / "ccaa_alzheimer.csv"

def norm_txt(x: str) -> str:
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return " ".join(x.split())

# Intentar leer CSV con pandas; si el fichero está malformado (commas sin
# comillas en nombres de CCAA) hacemos un fallback que localiza el campo
# `Sexo` (Total/Hombre/Mujer) y reconstruye las filas correctamente.
try:
    df = pd.read_csv(INP, encoding="utf-8-sig")
    # comprobar mínima sanidad
    if not {"Comunidades y Ciudades Autónomas", "Sexo", "Total"}.issubset(set(df.columns)):
        raise ValueError("Columnas esperadas no encontradas")
    print(f"INE columns: {df.columns.tolist()} | rows: {len(df)}")
except Exception:
    print("WARN: CSV malformado, aplicando fallback de parsing por patrón de 'Sexo'...")
    text = Path(INP).read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    hdr = lines[0] if lines else ""
    rows = []
    for ln in lines[1:]:
        # buscar la ocurrencia que marca el inicio de la columna Sexo
        m = re.search(r",\s*(Total|Hombre|Mujer),", ln)
        if not m:
            # si no encontramos patrón, saltar línea
            continue
        start = m.start()
        comunidades = ln[:start].strip()
        rest = ln[start+1:]
        parts = rest.split(",")
        # parts[0]=Sexo, parts[1]=Enfermedades, resto -> Total (puede incluir comas)
        sexo = parts[0].strip()
        enfermedades = parts[1].strip() if len(parts) > 1 else ""
        total = ",".join(parts[2:]).strip() if len(parts) > 2 else ""
        rows.append([comunidades, sexo, enfermedades, total])
    df = pd.DataFrame(rows, columns=["Comunidades y Ciudades Autónomas", "Sexo", "Enfermedades", "Total"]) 
    print(f"Fallback rows: {len(df)}")

# 1) Identificar columnas
col_ccaa = "Comunidades y Ciudades Autónomas"
col_sexo = "Sexo"
col_total = "Total"

# 2) Filtrar solo el Total (ambos sexos)
mask = (df[col_sexo].str.strip() == "Total")
df = df[mask].copy()

# 3) Parsear valores (Total)
df["alzheimer_val"] = (
    df[col_total].astype(str)
      .str.replace('"', '', regex=False)
      .str.replace(",", ".", regex=False)
)
df["alzheimer_val"] = pd.to_numeric(df["alzheimer_val"], errors="coerce")

# 4) Limpiar CCAA
df["CCAA_raw"] = df[col_ccaa].astype(str).str.replace(r"^\s*\d+\s*", "", regex=True).str.strip()
df = df[~df["CCAA_raw"].str.lower().str.contains("total nacional", na=False)]

# 5) Homogeneizar nombres
fix = {
    norm_txt("Asturias, Principado de"): "Ppdo. de Asturias",
    norm_txt("Balears, Illes"): "Illes Balears",
    norm_txt("Murcia, Región de"): "Región de Murcia",
    norm_txt("Navarra, Comunidad Foral de"): "C. Foral de Navarra",
    norm_txt("Rioja, La"): "La Rioja",
    norm_txt("Comunitat Valenciana"): "Comunidad Valenciana",
    norm_txt("Castilla - La Mancha"): "Castilla-La Mancha",
}
df["CCAA"] = df["CCAA_raw"].apply(lambda x: fix.get(norm_txt(x), str(x)))

out = df[["CCAA", "alzheimer_val"]].copy()
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False, encoding="utf-8-sig")

print(f"Generado: {OUT}")
print(out.head(10).to_string(index=False))
print(f"CCAA count: {out['CCAA'].nunique()}")
