import pandas as pd
from pathlib import Path
import unicodedata
import re

BASE = Path(__file__).resolve().parents[2]
INP = BASE / "data" / "raw" / "ine_diabetes_ccaa.csv"
OUT = BASE / "data" / "processed" / "ccaa_diabetes.csv"


def norm_txt(x: str) -> str:
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return " ".join(x.split())


try:
    df = pd.read_csv(INP, encoding="utf-8-sig")
    if not {"Comunidades y Ciudades Autónomas", "Sexo", "Total"}.issubset(set(df.columns)):
        raise ValueError("Columnas esperadas no encontradas")
    print(f"INE columns: {df.columns.tolist()} | rows: {len(df)}")
except Exception:
    print("WARN: CSV malformado, aplicando fallback de parsing por patrón de 'Sexo'...")
    text = Path(INP).read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    rows = []
    for ln in lines[1:]:
        m = re.search(r",\s*(Total|Hombre|Mujer),", ln)
        if not m:
            continue
        start = m.start()
        comunidades = ln[:start].strip()
        rest = ln[start + 1 :]
        parts = rest.split(",")
        sexo = parts[0].strip()
        enfermedades = parts[1].strip() if len(parts) > 1 else ""
        total = ",".join(parts[2:]).strip() if len(parts) > 2 else ""
        rows.append([comunidades, sexo, enfermedades, total])
    df = pd.DataFrame(rows, columns=["Comunidades y Ciudades Autónomas", "Sexo", "Enfermedades", "Total"])
    print(f"Fallback rows: {len(df)}")

col_ccaa = "Comunidades y Ciudades Autónomas"
col_sexo = "Sexo"
col_total = "Total"

mask = df[col_sexo].astype(str).str.strip() == "Total"
df = df[mask].copy()

df["diabetes_val"] = (
    df[col_total].astype(str).str.replace('"', "", regex=False).str.replace(",", ".", regex=False)
)
df["diabetes_val"] = pd.to_numeric(df["diabetes_val"], errors="coerce")

df["CCAA_raw"] = df[col_ccaa].astype(str).str.replace(r"^\s*\d+\s*", "", regex=True).str.strip()
df = df[~df["CCAA_raw"].str.lower().str.contains("total nacional", na=False)]

fix = {
    norm_txt("Asturias, Principado de"): "Ppdo. de Asturias",
    norm_txt("Balears, Illes"): "Illes Balears",
    norm_txt("Murcia, Región de"): "Región de Murcia",
    norm_txt("Navarra, Comunidad Foral de"): "C. Foral de Navarra",
    norm_txt("Rioja, La"): "La Rioja",
    norm_txt("Comunitat Valenciana"): "Comunidad Valenciana",
    norm_txt("Castilla - La Mancha"): "Castilla-La Mancha",
    norm_txt("Madrid, Comunidad de"): "Madrid",
}

df["CCAA"] = df["CCAA_raw"].apply(lambda x: fix.get(norm_txt(x), str(x)))

out = df[["CCAA", "diabetes_val"]].copy()
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False, encoding="utf-8-sig")

print(f"Generado: {OUT}")
print(out.head(10).to_string(index=False))
print(f"CCAA count: {out['CCAA'].nunique()}")
