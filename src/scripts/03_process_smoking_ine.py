import pandas as pd
from pathlib import Path
import unicodedata

BASE = Path(__file__).resolve().parents[2]
INP = BASE / "data" / "raw" / "ine_smoking_ccaa.csv"
OUT = BASE / "data" / "processed" / "ccaa_smoking.csv"


def norm_txt(x: str) -> str:
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return " ".join(x.split())


raw = pd.read_csv(INP, sep=";", encoding="utf-8-sig")
df = raw.copy()

ccaa_col = next(c for c in df.columns if "comunidad" in c.lower())
status_col = next(c for c in df.columns if "consumo" in c.lower())
total_col = next(c for c in df.columns if c.lower().strip() == "total" or "total" in c.lower())

# Solo fumadores diarios, que es el indicador más estable para usar como proxy de prevalencia activa.
df = df[df[status_col].astype(str).str.contains("Fuma diariamente", case=False, na=False)].copy()

# Quitamos el total nacional y homogeneizamos nombres de CCAA para casar con el pipeline.
df["CCAA_raw"] = df[ccaa_col].astype(str).str.strip()
df = df[~df["CCAA_raw"].str.lower().str.contains("total nacional", na=False)]

df["smoking_pct"] = pd.to_numeric(
    df[total_col].astype(str).str.replace(",", ".", regex=False),
    errors="coerce",
)

def map_ccaa(value: str) -> str:
    fix = {
        norm_txt("Asturias (Principado De)"): "Ppdo. de Asturias",
        norm_txt("Balears (Illes)"): "Illes Balears",
        norm_txt("Madrid (Comunidad De)"): "Comunidad de Madrid",
        norm_txt("Murcia (Región De)"): "Región de Murcia",
        norm_txt("Navarra (Comunidad Foral De)"): "C. Foral de Navarra",
        norm_txt("Rioja (La)"): "La Rioja",
        norm_txt("Comunidad Valenciana"): "Comunidad Valenciana",
        norm_txt("Castilla-La Mancha"): "Castilla-La Mancha",
    }
    return fix.get(norm_txt(value), value)


df["CCAA"] = df["CCAA_raw"].apply(map_ccaa)
out = df[["CCAA", "smoking_pct"]].copy()
out.insert(1, "period", "latest")

OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False, encoding="utf-8-sig")

print(f"✅ Generado: {OUT}")
print(out.head(10).to_string(index=False))
print("✅ CCAA count:", out["CCAA"].nunique())