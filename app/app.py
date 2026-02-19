from pathlib import Path
import re
import unicodedata
import json

import pandas as pd
import streamlit as st
import plotly.express as px

import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium


# -----------------------------
# Paths
# -----------------------------
BASE = Path(__file__).resolve().parents[1]
DATA_RAW = BASE / "data" / "raw"
DATA_PRO = BASE / "data" / "processed"
OUT_MAPS = BASE / "outputs" / "maps"

GEOJSON = DATA_RAW / "ccaa_boundaries.geojson"
HOSP_FILE = DATA_RAW / "CNH_2024_geocoded.csv"

PROFILE_FILE = DATA_PRO / "ccaa_profile_latest.csv"
SCORE_FILE   = DATA_PRO / "ccaa_opportunity_score.csv"
MARKET_FILE  = DATA_PRO / "ccaa_market_monthly.csv"
OBESITY_FILE = DATA_PRO / "ccaa_obesity.csv"


# -----------------------------
# Helpers
# -----------------------------
def key(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^\w\s-]", " ", s)
    s = s.replace("-", " ")
    s = " ".join(s.split())
    return s


ALIAS = {
    "c foral de navarra": "navarra",
    "ppdo de asturias": "asturias",
    "principado de asturias": "asturias",
    "castilla y leon": "castilla leon",
    "comunidad valenciana": "valencia",
    "illes balears": "baleares",
    "islas baleares": "baleares",
    "region de murcia": "murcia",
}

def apply_alias(k: str) -> str:
    return ALIAS.get(k, k)


@st.cache_data
def load_geojson():
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    for feat in gj["features"]:
        nm = feat["properties"].get("name", "")
        feat["properties"]["geo_key"] = key(nm)
    return gj


@st.cache_data
def load_scores():
    df = pd.read_csv(SCORE_FILE)
    df["ccaa_key"] = df["CCAA"].map(key).map(apply_alias)
    return df


@st.cache_data
def load_profile():
    return pd.read_csv(PROFILE_FILE)


@st.cache_data
def load_market():
    df = pd.read_csv(MARKET_FILE)
    # year_month viene como "YYYY-MM"
    df["date"] = pd.to_datetime(df["year_month"] + "-01")
    return df


@st.cache_data
def load_obesity():
    return pd.read_csv(OBESITY_FILE)


@st.cache_data
def load_hospitals():
    # Robust (como hiciste tú): si hay una línea mala, saltarla
    hosp = pd.read_csv(HOSP_FILE, sep=",", engine="python", encoding="utf-8", on_bad_lines="skip")
    for c in ["CCAA", "Provincia", "Municipio", "Nombre Centro", "Clase de Centro", "Dependencia Funcional"]:
        if c in hosp.columns:
            hosp[c] = hosp[c].astype(str).str.strip()

    # lat/lon
    hosp["lat"] = pd.to_numeric(hosp.get("lat"), errors="coerce")
    hosp["lon"] = pd.to_numeric(hosp.get("lon"), errors="coerce")
    hosp["CAMAS"] = pd.to_numeric(hosp.get("CAMAS"), errors="coerce").fillna(0).astype(int)

    hosp["is_private"] = hosp["Dependencia Funcional"].astype(str).str.contains("privad", case=False, na=False)
    hosp["is_public"] = ~hosp["is_private"]
    return hosp


def build_choropleth(gj, df_scores, value_col: str, title: str):
    # Inyectar datos en geojson para tooltip
    row_by_key = {r["ccaa_key"]: r for _, r in df_scores.iterrows()}

    for feat in gj["features"]:
        k = feat["properties"]["geo_key"]
        r = row_by_key.get(k)
        feat["properties"]["CCAA_csv"] = (r["CCAA"] if r is not None else feat["properties"].get("name", ""))
        if r is None:
            feat["properties"][value_col] = None
        else:
            feat["properties"][value_col] = float(r[value_col])

    m = folium.Map(location=[40.2, -3.7], zoom_start=6, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=gj,
        data=df_scores,
        columns=["ccaa_key", value_col],
        key_on="feature.properties.geo_key",
        fill_opacity=0.75,
        line_opacity=0.35,
        name=title,
    ).add_to(m)

    folium.GeoJson(
        gj,
        name="tooltip",
        tooltip=folium.GeoJsonTooltip(
            fields=["CCAA_csv", value_col],
            aliases=["CCAA", title],
            labels=True,
            sticky=False,
        ),
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


# -----------------------------
# UI
# -----------------------------
st.set_page_config(
    page_title="Pharma Decision Platform (TFG)",
    layout="wide",
)

st.title("📍 Pharma Decision Platform (TFG)")
st.caption("Plataforma de análisis para apoyar decisiones de marketing en el sector farmacéutico (obesidad/diabetes).")

# Load all
gj = load_geojson()
scores = load_scores()
profile = load_profile()
market = load_market()
obesity = load_obesity()
hosp = load_hospitals()

# Sidebar nav
section = st.sidebar.radio(
    "Navegación",
    ["Overview", "CCAA Drilldown", "Hospitals Explorer", "About / Methodology"],
)

# -----------------------------
# 1) OVERVIEW
# -----------------------------
if section == "Overview":
    st.subheader("Overview")
    col1, col2, col3, col4 = st.columns(4)

    # KPIs globales (simples, pero quedan muy bien)
    col1.metric("CCAA con score", int(scores["CCAA"].nunique()))
    col2.metric("Hospitals (CNH)", int(len(hosp)))
    col3.metric("Año obesidad (latest)", int(obesity["period"].max()) if len(obesity) else 0)
    col4.metric("Último mes mercado", str(market["date"].max().date()) if len(market) else "-")

    st.markdown("---")
    left, right = st.columns([1.2, 0.8])

    with left:
        st.markdown("### 🗺️ Mapa: Opportunity Score")
        m = build_choropleth(gj, scores, "opportunity_score", "Opportunity score")
        st_folium(m, width=None, height=560)

    with right:
        st.markdown("### 🏆 Ranking Top Oportunidades")
        top = scores.sort_values("opportunity_score", ascending=False).head(12)
        st.dataframe(
            top[["CCAA", "opportunity_score", "beds_per_100k", "market_12m_avg_eur_per_capita", "obesity_pct"]],
            use_container_width=True,
        )

        st.download_button(
            "⬇️ Descargar ranking (CSV)",
            data=top.to_csv(index=False).encode("utf-8"),
            file_name="top_opportunities.csv",
            mime="text/csv",
        )


# -----------------------------
# 2) CCAA DRILLDOWN
# -----------------------------
elif section == "CCAA Drilldown":
    st.subheader("CCAA Drilldown")

    ccaa = st.selectbox("Selecciona una CCAA", sorted(scores["CCAA"].unique().tolist()))
    row = scores[scores["CCAA"] == ccaa].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Opportunity score", f"{row['opportunity_score']:.2f}")
    c2.metric("Beds / 100k", f"{row['beds_per_100k']:.2f}")
    c3.metric("Market €/cap (12m avg)", f"{row['market_12m_avg_eur_per_capita']:.2f}")
    c4.metric("Obesity % (latest)", f"{row['obesity_pct']:.1f}")

    st.markdown("---")

    # Time series mercado
    dfm = market[market["CCAA"] == ccaa].sort_values("date")
    if len(dfm):
        st.markdown("### 📈 Evolución del mercado (mensual)")
        fig1 = px.line(dfm, x="date", y="market_monthly_eur_per_capita", title="Market monthly € per capita")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.line(dfm, x="date", y="market_monthly_eur", title="Market monthly € (total)")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No hay datos de mercado para esta CCAA.")

    # Tabla hospitales top por camas
    st.markdown("### 🏥 Hospitales (Top por CAMAS)")
    hccaa = hosp[hosp["CCAA"] == ccaa].copy()
    hccaa = hccaa.sort_values("CAMAS", ascending=False).head(20)
    st.dataframe(
        hccaa[["Nombre Centro", "Provincia", "Municipio", "CAMAS", "Dependencia Funcional", "Clase de Centro"]],
        use_container_width=True
    )

    # Mini simulador (queda MUY bien en TFG)
    st.markdown("### 🧪 Simulador rápido (What-if) – Producto obesidad/diabetes")
    a, b, c = st.columns(3)
    penetration = a.slider("Penetración estimada (%)", 0.0, 5.0, 1.0, 0.1)
    price_month = b.slider("Precio mensual tratamiento (€)", 20, 300, 120, 5)
    months = c.slider("Meses tratamiento/año", 1, 12, 6, 1)

    # Proxy muy simple: población (si existe) * obesidad% * penetración
    # Si no hay población aquí, asumimos “escala relativa” (igual vale para demo)
    pop = None
    if "population" in scores.columns:
        pop = float(row.get("population", 0) or 0)

    obesity_pct = float(row["obesity_pct"]) / 100.0
    pen = penetration / 100.0

    if pop and pop > 0:
        patients = pop * obesity_pct * pen
        revenue = patients * price_month * months
        st.info(f"Estimación (proxy): **{patients:,.0f}** pacientes -> **{revenue:,.0f} € / año**")
    else:
        st.info("Estimación (proxy): activa cuando tengamos población integrada en el score (opcional).")


# -----------------------------
# 3) HOSPITALS EXPLORER
# -----------------------------
elif section == "Hospitals Explorer":
    st.subheader("Hospitals Explorer")

    ccaa_filter = st.selectbox("Filtrar por CCAA", ["(Todas)"] + sorted(hosp["CCAA"].unique().tolist()))
    pub_filter = st.multiselect("Tipo", ["Público", "Privado"], default=["Público", "Privado"])
    camas_min, camas_max = st.slider("Rango de camas", 0, int(hosp["CAMAS"].max()), (0, int(hosp["CAMAS"].max())))

    dfh = hosp.copy()
    if ccaa_filter != "(Todas)":
        dfh = dfh[dfh["CCAA"] == ccaa_filter]

    if pub_filter != ["Público", "Privado"]:
        if pub_filter == ["Público"]:
            dfh = dfh[dfh["is_public"]]
        elif pub_filter == ["Privado"]:
            dfh = dfh[dfh["is_private"]]

    dfh = dfh[(dfh["CAMAS"] >= camas_min) & (dfh["CAMAS"] <= camas_max)]

    st.caption(f"Resultados: {len(dfh)} hospitales")
    st.dataframe(
        dfh[["Nombre Centro", "CCAA", "Provincia", "Municipio", "CAMAS", "Dependencia Funcional"]].head(200),
        use_container_width=True
    )

    st.markdown("### 🗺️ Mapa de hospitales (cluster)")
    dfh_map = dfh.dropna(subset=["lat", "lon"]).copy()
    if len(dfh_map) == 0:
        st.warning("No hay coordenadas disponibles para los filtros actuales.")
    else:
        m = folium.Map(location=[40.2, -3.7], zoom_start=6, tiles="cartodbpositron")
        cluster = MarkerCluster().add_to(m)

        for _, r in dfh_map.head(2000).iterrows():
            txt = f"{r['Nombre Centro']}<br>{r['CCAA']} - {r['Provincia']}<br>CAMAS: {r['CAMAS']}"
            folium.Marker([r["lat"], r["lon"]], popup=txt).add_to(cluster)

        st_folium(m, width=None, height=560)


# -----------------------------
# 4) ABOUT / METHODOLOGY
# -----------------------------
else:
    st.subheader("About / Methodology")

    st.markdown(
        """
**Objetivo del TFG**  
Diseñar una plataforma de análisis de datos para apoyar decisiones de marketing en el sector farmacéutico,
usando como caso de estudio el mercado **obesidad/diabetes**.

**Fuentes de datos (v1)**  
- CNH: Catálogo Nacional de Hospitales (hospitales, camas, geolocalización).  
- Hacienda: series de gasto (proxy de mercado sanitario/farmacéutico).  
- INE: indicadores de obesidad por CCAA (latest).

**Métricas base**  
- `beds_per_100k` (capacidad sanitaria)  
- `market_12m_avg_eur_per_capita` (tamaño mercado)  
- `obesity_pct` (necesidad/potencial)

**Opportunity Score**  
Score combinado normalizando métricas y ponderando:
capacidad + mercado + necesidad (obesidad).  
> Nota: el score es un “ranking proxy”, útil para exploración, no un modelo causal.

**Siguientes mejoras (para que el TFG parezca MUY completo)**  
- Añadir capa “producto”: segmentación por tipo (anti-obesidad, diabetes, etc.)  
- Añadir módulo “Sales simulation” (escenarios y elasticidad)  
- Añadir mapa drilldown por provincia / hospital  
- Validación con casos de uso y storytelling (ej.: lanzamiento en 3 CCAA top)
"""
    )