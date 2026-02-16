import json
import pandas as pd
import plotly.express as px
from pathlib import Path
import unicodedata
import difflib

BASE = Path(__file__).resolve().parents[2]
SUMMARY = BASE / "data" / "processed" / "ccaa_hospital_summary.csv"
GEOJSON = BASE / "data" / "raw" / "ccaa_boundaries.geojson"
OUTDIR  = BASE / "outputs" / "maps"
OUTDIR.mkdir(parents=True, exist_ok=True)
HTML_OUT = OUTDIR / "ccaa_map_beds_per_100k.html"

def norm_txt(x: str) -> str:
    if pd.isna(x):
        return ""
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = " ".join(x.split())
    return x

df = pd.read_csv(SUMMARY)

with open(GEOJSON, "r", encoding="utf-8") as f:
    gj = json.load(f)

# Detecta el campo "name" del geojson
props0 = gj["features"][0]["properties"]
name_field = "name" if "name" in props0 else ("NAME" if "NAME" in props0 else list(props0.keys())[0])

# Keys normalizadas en geojson
for feat in gj["features"]:
    feat["properties"]["ccaa_key"] = norm_txt(feat["properties"].get(name_field, ""))

geo_keys = sorted({feat["properties"]["ccaa_key"] for feat in gj["features"] if feat["properties"]["ccaa_key"]})

# Keys normalizadas en df
df["ccaa_key"] = df["CCAA"].map(norm_txt)

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
    cand = difflib.get_close_matches(k, geo_keys, n=1, cutoff=0.75)
    return cand[0] if cand else k


df["ccaa_key_mapped"] = df["ccaa_key"].apply(map_key)

unmatched = df.loc[~df["ccaa_key_mapped"].isin(geo_keys), "CCAA"].tolist()
if unmatched:
    print("⚠️ CCAA sin match en geojson (no se pintarán):")
    for x in unmatched:
        print("  -", x)

fig = px.choropleth(
    df,
    geojson=gj,
    locations="ccaa_key_mapped",
    featureidkey="properties.ccaa_key",
    color="beds_per_100k",
    hover_name="CCAA",
    hover_data={
        "beds_per_100k": True,
        "hospitals_total": True,
        "beds_total": True,
        "hospitals_per_1M": True,
        "population": True,
        "ccaa_key": False,
        "ccaa_key_mapped": False,
    },
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    title="Camas hospitalarias por 100.000 habitantes (por CCAA)",
    margin={"r":0, "t":50, "l":0, "b":0},
)

fig.write_html(str(HTML_OUT))
print(f"✅ Mapa generado: {HTML_OUT}")
