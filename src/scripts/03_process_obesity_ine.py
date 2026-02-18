import pandas as pd
from pathlib import Path
import unicodedata

BASE = Path(__file__).resolve().parents[2]
INP = BASE / "data" / "raw" / "ine_obesity_ccaa.csv"
OUT = BASE / "data" / "processed" / "ccaa_obesity.csv"

def norm_txt(x: str) -> str:
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return " ".join(x.split())

df = pd.read_csv(INP, sep=";", engine="python")

# Detecta columna CCAA
ccaa_col = next((c for c in df.columns if "comun" in c.lower() and "aut" in c.lower()), None)
# Detecta periodo/año
period_col = next((c for c in df.columns if "period" in c.lower() or "año" in c.lower() or "anio" in c.lower()), None)
# Detecta valor
value_col = next((c for c in df.columns if c.lower() in ["total", "valor"] or "total" in c.lower()), None)

if ccaa_col is None or value_col is None:
    raise ValueError(f"No detecto columnas INE. Columnas: {df.columns.tolist()}")

out = pd.DataFrame()
out["CCAA_raw"] = df[ccaa_col].astype(str).str.strip()
out["ccaa_key"] = out["CCAA_raw"].map(norm_txt)

if period_col:
    out["period"] = df[period_col].astype(str).str.strip()
else:
    out["period"] = ""

val = df[value_col].astype(str).str.replace(",", ".", regex=False)
out["obesity_pct"] = pd.to_numeric(val, errors="coerce")

# limpia
out = out.dropna(subset=["obesity_pct"])
out = out[~out["CCAA_raw"].str.lower().str.contains("total", na=False)]

# quedarnos con el último periodo disponible por CCAA
# (si period es año numérico o tipo "2022", funcionará)
out["_p"] = pd.to_numeric(out["period"].str.extract(r"(\d{4})")[0], errors="coerce")
out = out.sort_values(["ccaa_key", "_p"])
out_latest = out.groupby("ccaa_key", as_index=False).tail(1).drop(columns=["_p"])

out_latest.rename(columns={"CCAA_raw": "CCAA"}, inplace=True)

OUT.parent.mkdir(parents=True, exist_ok=True)
out_latest.to_csv(OUT, index=False, encoding="utf-8")

print(f"✅ Generado: {OUT}")
print(out_latest.head(10).to_string(index=False))
print("CCAA:", out_latest["CCAA"].nunique(), "| Periodo único:", out_latest["period"].unique()[:5])
