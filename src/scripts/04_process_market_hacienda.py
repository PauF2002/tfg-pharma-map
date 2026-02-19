import pandas as pd
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
XLSX_FILE = BASE / "data" / "raw" / "hacienda_gasto_farma_sanitario.xlsx"
SUMMARY_FILE = BASE / "data" / "processed" / "ccaa_hospital_summary.csv"
OUT_FILE = BASE / "data" / "processed" / "ccaa_market_monthly.csv"

SHEET = "Tabla 4v"   # Total gasto en productos farmacéuticos y sanitarios
HEADER_ROW = 5       # fila donde aparecen "2015 - Enero", etc.
LABEL_COL = 0        # columna donde aparecen ANDALUCÍA, ARAGÓN, ...

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

def norm_txt(x: str) -> str:
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = x.replace("*", "")
    x = " ".join(x.split())
    return x

# Alias para casar nombres con tu summary
ALIASES = {
    "asturias": "ppdo. de asturias",
    "islas baleares": "illes balears",
    "c. valenciana": "comunidad valenciana",
    "c.f. de navarra": "c. foral de navarra",
}

if not XLSX_FILE.exists():
    raise FileNotFoundError(f"No encuentro el XLSX: {XLSX_FILE}")

raw = pd.read_excel(XLSX_FILE, sheet_name=SHEET, header=None)

# 1) Detectar columnas mensuales (YYYY - Mes)
month_meta = []  # (col_idx, year, month_num, ym)
for col_idx in range(1, raw.shape[1]):
    h = raw.iloc[HEADER_ROW, col_idx]
    if isinstance(h, str) and re.match(r"^\d{4}\s*-\s*", h):
        year_str, month_str = [p.strip() for p in h.split("-", 1)]
        year = int(year_str)
        mkey = norm_txt(month_str)
        if mkey in MONTHS:
            mnum = MONTHS[mkey]
            ym = f"{year}-{mnum:02d}"
            month_meta.append((col_idx, year, mnum, ym))

if not month_meta:
    raise ValueError("No detecto columnas mensuales. ¿Ha cambiado el formato del Excel?")

# 2) Localizar bloque CCAA (debajo de 'TOTAL COMUNIDADES AUTÓNOMAS')
labels = raw.iloc[:, LABEL_COL].astype(str)

idx_total_ccaa = raw.index[labels.str.contains("TOTAL COMUNIDADES", na=False)]
if len(idx_total_ccaa) == 0:
    raise ValueError("No encuentro la fila 'TOTAL COMUNIDADES AUTÓNOMAS'.")

start = int(idx_total_ccaa[0]) + 1

# Fin: antes de la nota aclaratoria "*Ver Notas..."
idx_end_note = raw.index[labels.str.contains("Ver Notas", na=False)]
end = int(idx_end_note[0]) - 1 if len(idx_end_note) else raw.shape[0] - 1

ccaa_block = raw.iloc[start:end+1].copy()
ccaa_block = ccaa_block[ccaa_block[LABEL_COL].notna()]

# 3) Cargar summary para coger población y nombres canónicos
summary = pd.read_csv(SUMMARY_FILE)
summary["ccaa_key"] = summary["CCAA"].map(norm_txt)
key_to_ccaa = dict(zip(summary["ccaa_key"], summary["CCAA"]))
key_to_pop = dict(zip(summary["ccaa_key"], summary["population"]))

rows = []
for _, r in ccaa_block.iterrows():
    label = str(r[LABEL_COL]).strip()
    if not label or label.lower().startswith("total"):
        continue

    ccaa_key = norm_txt(label)
    ccaa_key = ALIASES.get(ccaa_key, ccaa_key)

    ccaa_name = key_to_ccaa.get(ccaa_key, label.title())
    population = key_to_pop.get(ccaa_key, None)

    for col_idx, year, mnum, ym in month_meta:
        val = r[col_idx]
        rows.append({
            "CCAA": ccaa_name,
            "ccaa_key": ccaa_key,
            "year": year,
            "month": mnum,
            "year_month": ym,
            "market_ytd_kEUR": pd.to_numeric(val, errors="coerce"),  # miles de euros (acumulado anual)
            "population": population
        })

df = pd.DataFrame(rows).dropna(subset=["market_ytd_kEUR"])
df = df.sort_values(["CCAA", "year", "month"])

# 4) Convertir acumulado anual -> mensual (diferencias dentro del año)
df["market_monthly_kEUR"] = df.groupby(["CCAA", "year"])["market_ytd_kEUR"].diff()

# Si es Enero, el mensual = acumulado (porque empieza el año)
is_jan = df["month"] == 1
df.loc[is_jan, "market_monthly_kEUR"] = df.loc[is_jan, "market_ytd_kEUR"]

# Si no es Enero y no hay mes anterior (ej: Junio-2014), lo dejamos NaN
df.loc[(~is_jan) & (df["market_monthly_kEUR"].isna()), "market_monthly_kEUR"] = pd.NA

# Euros
df["market_monthly_eur"] = (df["market_monthly_kEUR"] * 1000).astype("float")
df["market_ytd_eur"] = (df["market_ytd_kEUR"] * 1000).astype("float")

# Per cápita (si hay población)
df["market_monthly_eur_per_capita"] = df["market_monthly_eur"] / df["population"]

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_FILE, index=False, encoding="utf-8")

print(f"✅ Generado: {OUT_FILE}")
print("Filas:", len(df), "| CCAA:", df["CCAA"].nunique(), "| rango:", df["year_month"].min(), "→", df["year_month"].max())
print(df[["CCAA","year_month","market_monthly_eur","market_monthly_eur_per_capita"]].dropna().head(10).to_string(index=False))