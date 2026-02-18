import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Overview Map", layout="wide")

BASE = Path(__file__).resolve().parents[2]
MAP_HTML = BASE / "outputs" / "maps" / "ccaa_map_beds_per_100k.html"

st.title("Overview Map (CCAA)")
st.caption("Beds per 100k inhabitants — interactive choropleth map.")

if not MAP_HTML.exists():
    st.error("Map not found. Generate it first: python -u src/scripts/02_make_ccaa_map.py")
else:
    html = MAP_HTML.read_text(encoding="utf-8")
    st.components.v1.html(html, height=750, scrolling=True)
