import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="CCAA KPIs", layout="wide")

BASE = Path(__file__).resolve().parents[2]
SUMMARY = BASE / "data" / "processed" / "ccaa_hospital_summary.csv"

st.title("CCAA KPIs (Hospital Capacity)")
st.caption("Base KPIs derived from CNH + population.")

if not SUMMARY.exists():
    st.error("Missing processed data. Run: python -u src/scripts/01_build_ccaa_summary.py")
else:
    df = pd.read_csv(SUMMARY)
    df = df.sort_values("beds_per_100k", ascending=False)

    st.dataframe(df, use_container_width=True)

    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="ccaa_hospital_summary.csv",
        mime="text/csv"
    )
