import re
import unicodedata
from pathlib import Path

import pandas as pd
import folium


BASE = Path(__file__).resolve().parents[2]
GEOJSON = BASE / "data" / "raw" / "ccaa_boundaries.geojson"
SCORES  = BASE / "data" / "processed" / "ccaa_opportunity_score.csv"
OUT     = BASE / "outputs" / "maps" / "ccaa_map_opportunity_score.html"


def key(s: str) -> str:
    """Normaliza texto: minúsculas, sin acentos, sin signos, espacios limpios."""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^\w\s-]", " ", s)          # quita puntos/comas/etc (mantiene guiones)
    s = s.replace("-", " ")                  # guiones como espacio
    s = " ".join(s.split())
    return s


# Alias: NOMBRE_EN_TUS_CSV -> NOMBRE_EN_GEOJSON(name)
ALIAS = {
    "c foral de navarra": "navarra",
    "ppdo de asturias": "asturias",
    "principado de asturias": "asturias",
    "castilla y leon": "castilla leon",
    "comunidad valenciana": "valencia",
    "illes balears": "baleares",
    "islas baleares": "baleares",
    "region de murcia": "murcia",
    "pais vasco": "pais vasco",   # ya coincide
}


def apply_alias(k: str) -> str:
    return ALIAS.get(k, k)


# 1) Cargar score
df = pd.read_csv(SCORES)
df["ccaa_key"] = df["CCAA"].map(key).map(apply_alias)

# Dejamos strings “bonitos” para tooltip (evita formatos raros)
df["opportunity_score_s"] = df["opportunity_score"].round(2).astype(str)
df["beds_per_100k_s"] = df["beds_per_100k"].round(2).astype(str)
df["market_pc_s"] = df["market_12m_avg_eur_per_capita"].round(2).astype(str)
df["obesity_pct_s"] = df["obesity_pct"].round(1).astype(str)

# 2) Cargar geojson y crear key desde properties['name']
import json
gj = json.loads(GEOJSON.read_text(encoding="utf-8"))

for feat in gj["features"]:
    nm = feat["properties"].get("name", "")
    feat["properties"]["geo_key"] = key(nm)

geo_keys = {f["properties"]["geo_key"] for f in gj["features"]}
df_keys = set(df["ccaa_key"].unique())

missing = sorted(list(df_keys - geo_keys))
if missing:
    print("⚠️ CCAA sin match en geojson (no se pintarán):")
    for m in missing:
        print("  -", m)

# 3) Inyectar en el geojson las métricas (para tooltip/popup)
row_by_key = {r["ccaa_key"]: r for _, r in df.iterrows()}

for feat in gj["features"]:
    k = feat["properties"]["geo_key"]
    r = row_by_key.get(k)
    if r is None:
        # sin datos (p.ej. Ceuta/Melilla) -> dejamos vacío
        feat["properties"]["CCAA"] = feat["properties"].get("name", "")
        feat["properties"]["opportunity_score"] = None
        feat["properties"]["beds_per_100k"] = None
        feat["properties"]["market_12m_avg_eur_per_capita"] = None
        feat["properties"]["obesity_pct"] = None
        feat["properties"]["opportunity_score_s"] = ""
        feat["properties"]["beds_per_100k_s"] = ""
        feat["properties"]["market_pc_s"] = ""
        feat["properties"]["obesity_pct_s"] = ""
    else:
        feat["properties"]["CCAA"] = r["CCAA"]
        feat["properties"]["opportunity_score"] = float(r["opportunity_score"])
        feat["properties"]["beds_per_100k"] = float(r["beds_per_100k"])
        feat["properties"]["market_12m_avg_eur_per_capita"] = float(r["market_12m_avg_eur_per_capita"])
        feat["properties"]["obesity_pct"] = float(r["obesity_pct"])
        feat["properties"]["opportunity_score_s"] = r["opportunity_score_s"]
        feat["properties"]["beds_per_100k_s"] = r["beds_per_100k_s"]
        feat["properties"]["market_pc_s"] = r["market_pc_s"]
        feat["properties"]["obesity_pct_s"] = r["obesity_pct_s"]


# 4) Mapa
OUT.parent.mkdir(parents=True, exist_ok=True)

m = folium.Map(location=[40.2, -3.7], zoom_start=6, tiles="cartodbpositron")

folium.Choropleth(
    geo_data=gj,
    data=df,
    columns=["ccaa_key", "opportunity_score"],
    key_on="feature.properties.geo_key",
    fill_opacity=0.75,
    line_opacity=0.35,
    name="Opportunity Score",
).add_to(m)

folium.GeoJson(
    gj,
    name="Info",
    tooltip=folium.GeoJsonTooltip(
        fields=["CCAA", "opportunity_score_s", "beds_per_100k_s", "market_pc_s", "obesity_pct_s"],
        aliases=["CCAA", "Opportunity score", "Beds / 100k", "Market € / cap (12m avg)", "Obesity % (latest)"],
        localize=True,
        sticky=False,
        labels=True,
    ),
).add_to(m)

folium.LayerControl().add_to(m)

m.save(str(OUT))
print(f"✅ Mapa generado: {OUT}")
