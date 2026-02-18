import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Pharma Decision Platform", layout="wide")

BASE = Path(__file__).resolve().parents[1]
SUMMARY = BASE / "data" / "processed" / "ccaa_hospital_summary.csv"

st.title("Pharma Decision Platform (TFG)")
st.caption("Geospatial + KPI dashboard for marketing decision-making in the pharma sector (Spain).")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("""
### What you can do
- Explore an interactive CCAA map (beds per 100k, etc.)
- Click a region and drill down into details
- Build an opportunity ranking (next steps)
""")
with col2:
    if SUMMARY.exists():
        df = pd.read_csv(SUMMARY)
        st.metric("CCAA covered", df["CCAA"].nunique())
        st.metric("Total hospitals (CNH)", int(df["hospitals_total"].sum()))
    else:
        st.warning("Run scripts 01 and 02 to generate processed data.")
