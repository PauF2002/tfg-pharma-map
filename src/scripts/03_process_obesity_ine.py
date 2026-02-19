import pandas as pd
from pathlib import Path
import unicodedata
import re

BASE = Path(__file__).resolve().parents[2]
INP = BASE / "data" / "raw" / "ine_obesity_ccaa.csv"
OUT = BASE / "data" / "processed" / "ccaa_obesity.csv"

def norm_txt(x: str) -> str:
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return " ".join(x.split())

# 1) Leer TSV del INE (tabulador)
df = pd.read_csv(
    INP,
    sep="\t",
    engine="python",
    encoding="utf-8-sig",
    quotechar='"'
)

print("✅ INE columns:", df.columns.tolist(), "| rows:", len(df))

# 2) Renombrar columnas esperadas (por si vienen con mayúsculas/acentos)
# Esperado: Comunidad autónoma, Masa corporal, Periodo, Total
col_ccaa = next(c for c in df.columns if "comunidad" in c.lower())
col_masa = next(c for c in df.columns if "masa" in c.lower())
col_periodo = next(c for c in df.columns if "period" in c.lower())
col_total = next(c for c in df.columns if c.lower().strip() == "total" or "total" in c.lower())

# 3) Filtrar SOLO obesidad (IMC >= 30)
mask_ob = df[col_masa].astype(str).str.contains("Obesidad", case=False, na=False)
df = df[mask_ob].copy()

# 4) Parsear valores
df["period"] = pd.to_numeric(df[col_periodo], errors="coerce")
df["obesity_pct"] = (
    df[col_total].astype(str)
      .str.replace(",", ".", regex=False)   # coma decimal -> punto
)
df["obesity_pct"] = pd.to_numeric(df["obesity_pct"], errors="coerce")

# 5) Limpiar CCAA (quitar prefijo "01 ", "02 ", etc.)
df["CCAA_raw"] = df[col_ccaa].astype(str).str.replace(r"^\s*\d+\s*", "", regex=True).str.strip()

# quitar Total Nacional
df = df[~df["CCAA_raw"].str.lower().str.contains("total nacional", na=False)]

df = df.dropna(subset=["period", "obesity_pct"])

# 6) Quedarnos con el último año por CCAA
df = df.sort_values(["CCAA_raw", "period"]).groupby("CCAA_raw", as_index=False).tail(1)

# 7) Homogeneizar nombres para casar con tu pipeline (hospital/geojson)
fix = {
    norm_txt("Asturias, Principado de"): "Ppdo. de Asturias",
    norm_txt("Balears, Illes"): "Illes Balears",
    norm_txt("Murcia, Región de"): "Región de Murcia",
    norm_txt("Navarra, Comunidad Foral de"): "C. Foral de Navarra",
    norm_txt("Rioja, La"): "La Rioja",
    norm_txt("Comunitat Valenciana"): "Comunidad Valenciana",
    norm_txt("Castilla - La Mancha"): "Castilla-La Mancha",
}
df["CCAA"] = df["CCAA_raw"].apply(lambda x: fix.get(norm_txt(x), x))

out = df[["CCAA", "period", "obesity_pct"]].copy()
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False, encoding="utf-8-sig")


print(f"✅ Generado: {OUT}")
print(out.head(10).to_string(index=False))
print("✅ CCAA count:", out["CCAA"].nunique(), "| latest years:", sorted(out["period"].unique())[-5:])