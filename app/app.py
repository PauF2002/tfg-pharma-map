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

def inject_sidebar_styles():
    st.markdown("""
    <style>
    /* ===== Global dark theme ===== */
    :root {
        color-scheme: dark;
    }

    [data-testid="stAppViewContainer"] {
        background: radial-gradient(1200px 800px at 10% 0%, #111827 0%, #0b1220 45%, #0a0f1a 100%);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .stApp {
        color: #E5E7EB;
    }

    /* Texto base en el contenido principal */
    [data-testid="stMarkdownContainer"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"],
    [data-testid="stCaptionContainer"],
    [data-testid="stText"],
    [data-testid="stDataFrame"] {
        color: #E5E7EB;
    }

    /* ===== Sidebar contenedor ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    /* Texto del sidebar */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: #E5E7EB;
    }

    /* ===== RADIO GROUP (navegación) ===== */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    /* Cada opción = botón uniforme */
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        display: flex !important;
        align-items: center;
        width: 100%;
        min-height: 52px;      /* todos igual */
        height: 52px;          /* todos igual */
        box-sizing: border-box;
        padding: 0 14px;
        margin: 0;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
        transition: all 0.18s ease-in-out;
        cursor: pointer;
        overflow: hidden;
    }

    /* Hover reactivo */
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background: rgba(96,165,250,0.12);
        border-color: rgba(96,165,250,0.45);
        transform: translateX(3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.25);
    }

    /* 🔴 Quitar el “botón rojo” (círculo del radio) */
    [data-testid="stSidebar"] div[role="radiogroup"] > label input[type="radio"] {
        position: absolute !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        pointer-events: none !important;
    }

    /* Si Streamlit renderiza un círculo visual extra (según versión), lo ocultamos */
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    /* Texto de la opción */
    [data-testid="stSidebar"] div[role="radiogroup"] > label p {
        margin: 0 !important;
        width: 100%;
        color: #E5E7EB !important;
        font-weight: 600;
        white-space: nowrap;        /* evita que unos botones crezcan */
        overflow: hidden;
        text-overflow: ellipsis;    /* si el texto es largo, ... */
    }

    /* Seleccionado */
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(90deg, rgba(79,70,229,0.25), rgba(96,165,250,0.18));
        border-color: rgba(96,165,250,0.55);
        box-shadow: inset 0 0 0 1px rgba(96,165,250,0.25);
    }
                

    /* Contenido interno del sidebar (menos margen y mas arriba) */
    [data-testid="stSidebarUserContent"] {
        padding-top: 0.005rem !important;
        padding-left: 0.45rem !important;
        padding-right: 0.45rem !important;
    }

    /* Radio group ocupa todo */
    [data-testid="stSidebar"] div[role="radiogroup"] {
    width: 100% !important;
    }

    /* Cada botón ocupa todo el ancho */
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
    width: 100% !important;
    min-width: 100% !important;
    }

    /* Separadores del sidebar */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.08);
    }

    /* Ocultar navegacion multipage por defecto en sidebar */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* ===== Top nav (page links) ===== */
    .top-nav {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        margin: 6px 0 14px 0;
    }

    [data-testid="stPageLink"] {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 8px 14px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.18);
        background: rgba(255,255,255,0.05);
        box-shadow: 0 6px 14px rgba(0,0,0,0.22);
        color: #E5E7EB !important;
        text-decoration: none !important;
        font-weight: 600;
        transition: all 0.18s ease-in-out;
    }

    [data-testid="stPageLink"]:hover {
        background: rgba(96,165,250,0.14);
        border-color: rgba(96,165,250,0.45);
        transform: translateY(-1px);
    }

    /* Perfil clickeable */
    .user-profile-link {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: rgba(255,255,255,0.04);
        border-radius: 10px;
        margin-bottom: 12px;
        border: 1px solid rgba(255,255,255,0.08);
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none !important;
    }

  
    </style>
    """, unsafe_allow_html=True)

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

    #RECORRE EL DATFRAME Y DEVUELVE EL INDEX Y LA DILA COMO SERIE, LUEGO CREA UN DICCIONARIO CON LA KEY "ccaa_key" Y EL VALOR DE ESA COLUMNA, Y ASOCIA ESA KEY CON LA FILA COMPLETA (r) EN EL DICCIONARIO
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
        fill_color="RdYlGn",
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

inject_sidebar_styles()

# Perfil de usuario en el sidebar (clickeable)
st.sidebar.markdown("""
<a href="/User_Profile" target="_self" style="text-decoration: none;">
    <div class="user-profile-link">
        <div style='width: 42px; height: 42px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0;'>
            👤
        </div>
        <div style='flex: 1; min-width: 0;'>
            <div style='color: #E5E7EB; font-weight: 600; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>
                Usuario Demo
            </div>
            <div style='color: #9CA3AF; font-size: 12px; margin-top: 2px;'>
                ✓ Sesión activa
            </div>
        </div>
    </div>
</a>
""", unsafe_allow_html=True)

# Logo y nombre de la app en el sidebar
st.sidebar.markdown("""
<div style='text-align: center; padding: 15px 0; border-bottom: 1px solid rgba(255,255,255,0.1);'>
    <h2 style='margin: 0; color: #E5E7EB;'>💊 TFG PHARMA</h2>
</div>
""", unsafe_allow_html=True)

# Top nav (paginas)
top_cols = st.columns(4, gap="small")
with top_cols[0]:
    st.page_link("app.py", label="app")
with top_cols[1]:
    st.page_link("pages/1_Overview_Map.py", label="Overview Map")
with top_cols[2]:
    st.page_link("pages/2_CCAA_Table.py", label="CCAA Table")
with top_cols[3]:
    st.page_link("pages/4_Inventory.py", label="Inventory")

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
    label_visibility="collapsed"
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
        st_folium(m, width=None, height=580)

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
            folium.Marker(
                [r["lat"], r["lon"]],
                 popup=txt,
                 icon=folium.DivIcon(
                     html="""
                    <div style="font-size: 20px; line-height: 20px; text-align:center;">
                     🏥
                    </div>
                    """
                 )
             ).add_to(cluster)
        st_folium(m, width=None, height=580)


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