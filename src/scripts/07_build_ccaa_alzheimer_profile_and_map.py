import json
import unicodedata
from pathlib import Path

import pandas as pd
import plotly.express as px

BASE = Path(__file__).resolve().parents[2]
HOSP = BASE / "data" / "processed" / "ccaa_hospital_summary.csv"
MARKET = BASE / "data" / "processed" / "ccaa_market_monthly.csv"
SMOKE = BASE / "data" / "processed" / "ccaa_alzheimer.csv"

OUT_PROFILE = BASE / "data" / "processed" / "ccaa_alzheimer_profile_latest.csv"
OUT_SCORE = BASE / "data" / "processed" / "ccaa_alzheimer_opportunity_score.csv"
OUT_MAP = BASE / "outputs" / "maps" / "ccaa_map_alzheimer.html"
OUT_MAP.parent.mkdir(parents=True, exist_ok=True)


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


h = pd.read_csv(HOSP)
m = pd.read_csv(MARKET)
s = pd.read_csv(SMOKE)

h["ccaa_key"] = h["CCAA"].map(norm_txt)
m["ccaa_key"] = m["CCAA"].map(norm_txt)
s["ccaa_key"] = s["CCAA"].map(norm_txt)

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

if "period" in s.columns:
    s["_p"] = s["period"].astype(str)
else:
    s["_p"] = "latest"

smoke = s[["ccaa_key", "alzheimer_val"]].copy()

profile = (
    h.merge(market12, on="ccaa_key", how="left")
     .merge(smoke, on="ccaa_key", how="left")
)

profile["beds_per_100k"] = pd.to_numeric(profile["beds_per_100k"], errors="coerce").fillna(0)
profile["market_12m_avg_eur_per_capita"] = pd.to_numeric(profile["market_12m_avg_eur_per_capita"], errors="coerce").fillna(0)
profile["alzheimer_val"] = pd.to_numeric(profile["alzheimer_val"], errors="coerce").fillna(0)

profile["beds_n"] = minmax(profile["beds_per_100k"])
profile["market_n"] = minmax(profile["market_12m_avg_eur_per_capita"])
profile["alzheimer_n"] = minmax(profile["alzheimer_val"])

profile["opportunity_score"] = (100 * (
    0.45 * profile["market_n"] +
    0.35 * profile["alzheimer_n"] +
    0.20 * profile["beds_n"]
)).round(2)

score = profile[[
    "CCAA",
    "hospitals_total", "beds_total", "beds_per_100k",
    "market_12m_avg_eur_per_capita", "market_12m_sum_eur", "market_last_month",
    "alzheimer_val",
    "opportunity_score"
]].sort_values("opportunity_score", ascending=False)

OUT_PROFILE.parent.mkdir(parents=True, exist_ok=True)
profile.to_csv(OUT_PROFILE, index=False, encoding="utf-8")
score.to_csv(OUT_SCORE, index=False, encoding="utf-8")

with open(BASE / "data" / "raw" / "ccaa_boundaries.geojson", "r", encoding="utf-8") as f:
    gj = json.load(f)

props0 = gj["features"][0]["properties"]
name_field = "name" if "name" in props0 else ("NAME" if "NAME" in props0 else list(props0.keys())[0])

for feat in gj["features"]:
    feat["properties"]["ccaa_key"] = norm_txt(feat["properties"].get(name_field, ""))

geo_keys = sorted({feat["properties"]["ccaa_key"] for feat in gj["features"] if feat["properties"]["ccaa_key"]})
aliases = {
    "ppdo. de asturias": "asturias",
    "c. foral de navarra": "navarra",
    "p. de madrid": "madrid",
    "illes balears": "baleares",
    "comunidad valenciana": "valencia",
    "comunitat valenciana": "valencia",
    "c. valenciana": "valencia",
    "region de murcia": "murcia",
}


def map_key(k: str) -> str:
    if k in geo_keys:
        return k
    if k in aliases and aliases[k] in geo_keys:
        return aliases[k]
    return k


score["ccaa_key_mapped"] = score["CCAA"].map(norm_txt).apply(map_key)

fig = px.choropleth(
    score,
    geojson=gj,
    locations="ccaa_key_mapped",
    featureidkey="properties.ccaa_key",
    color="opportunity_score",
    hover_name="CCAA",
    hover_data={
        "opportunity_score": True,
        "beds_per_100k": True,
        "market_12m_avg_eur_per_capita": True,
        "alzheimer_val": True,
        "ccaa_key_mapped": False,
    },
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    title="Opportunity score for alzheimer by CCAA",
    margin={"r": 0, "t": 50, "l": 0, "b": 0},
)

fig.write_html(str(OUT_MAP))
print(f"✅ Generado: {OUT_PROFILE}")
print(f"✅ Generado: {OUT_SCORE}")
print(f"✅ Mapa generado: {OUT_MAP}")
print(score.head(10).to_string(index=False))
