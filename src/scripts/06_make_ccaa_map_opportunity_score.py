import pandas as pd
from pathlib import Path
import unicodedata

BASE = Path(__file__).resolve().parents[2]

HOSP = BASE / "data" / "processed" / "ccaa_hospital_summary.csv"
MARKET = BASE / "data" / "processed" / "ccaa_market_monthly.csv"
OBES = BASE / "data" / "processed" / "ccaa_obesity.csv"

OUT_PROFILE = BASE / "data" / "processed" / "ccaa_profile_latest.csv"
OUT_SCORE = BASE / "data" / "processed" / "ccaa_opportunity_score.csv"

def norm_txt(x: str) -> str:
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return " ".join(x.split())

def minmax(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    mn, mx = s.min(), s.max()
    if mx == mn:
        return s * 0
    return (s - mn) / (mx - mn)

# --- Load ---
h = pd.read_csv(HOSP)
m = pd.read_csv(MARKET)
o = pd.read_csv(OBES)

# keys
h["ccaa_key"] = h["CCAA"].map(norm_txt)
m["ccaa_key"] = m["CCAA"].map(norm_txt)
o["ccaa_key"] = o["CCAA"].map(norm_txt)

# --- MARKET: media últimos 12 meses per cápita ---
m = m.dropna(subset=["market_monthly_eur_per_capita"]).copy()
m = m.sort_values(["ccaa_key", "year_month"])

market12 = (
    m.groupby("ccaa_key", as_index=False)
     .tail(12)
     .groupby("ccaa_key", as_index=False)
     .agg(
         market_12m_avg_eur_per_capita=("market_monthly_eur_per_capita", "mean"),
         market_12m_sum_eur=("market_monthly_eur", "sum"),
         market_last_month=("year_month", "max")
     )
)

# --- OBESITY: cogemos el último valor por CCAA (ya viene así normalmente) ---
# Si hay duplicados, nos quedamos el último por 'period'
if "period" in o.columns:
    o["_p"] = pd.to_numeric(o["period"].astype(str).str.extract(r"(\d{4})")[0], errors="coerce")
    o = o.sort_values(["ccaa_key", "_p"]).groupby("ccaa_key", as_index=False).tail(1).drop(columns=["_p"])

ob = o[["ccaa_key", "obesity_pct"]].copy()

# --- Merge base profile ---
profile = (
    h.merge(market12, on="ccaa_key", how="left")
     .merge(ob, on="ccaa_key", how="left")
)

# --- Opportunity score (0-100) ---
# Pesos recomendados: mercado 45% + obesidad 35% + capacidad (camas/100k) 20%
profile["beds_per_100k"] = pd.to_numeric(profile["beds_per_100k"], errors="coerce").fillna(0)
profile["market_12m_avg_eur_per_capita"] = pd.to_numeric(profile["market_12m_avg_eur_per_capita"], errors="coerce").fillna(0)
profile["obesity_pct"] = pd.to_numeric(profile["obesity_pct"], errors="coerce").fillna(0)

profile["beds_n"] = minmax(profile["beds_per_100k"])
profile["market_n"] = minmax(profile["market_12m_avg_eur_per_capita"])
profile["obesity_n"] = minmax(profile["obesity_pct"])

profile["opportunity_score"] = (100 * (
    0.45*profile["market_n"] +
    0.35*profile["obesity_n"] +
    0.20*profile["beds_n"]
)).round(2)

# ranking
score = profile[[
    "CCAA",
    "hospitals_total", "beds_total", "beds_per_100k",
    "market_12m_avg_eur_per_capita", "market_12m_sum_eur", "market_last_month",
    "obesity_pct",
    "opportunity_score"
]].sort_values("opportunity_score", ascending=False)

# --- Save ---
OUT_PROFILE.parent.mkdir(parents=True, exist_ok=True)
profile.to_csv(OUT_PROFILE, index=False, encoding="utf-8")
score.to_csv(OUT_SCORE, index=False, encoding="utf-8")

print(f"✅ Generado: {OUT_PROFILE}")
print(f"✅ Generado: {OUT_SCORE}")
print("\nTop 10 oportunidades:")
print(score.head(10).to_string(index=False))