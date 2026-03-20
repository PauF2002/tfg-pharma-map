from pathlib import Path
import html as html_lib

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


class OverviewMapView:
    def render(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        map_html_path = project_root / "outputs" / "maps" / "ccaa_map_opportunity_score.html"
        score_path = project_root / "data" / "processed" / "ccaa_opportunity_score.csv"
        hospital_path = project_root / "data" / "processed" / "ccaa_hospital_summary.csv"

        overview_panel = st.container(key="overview_map_panel")
        with overview_panel:
            if not map_html_path.exists() or not score_path.exists() or not hospital_path.exists():
                st.error("Faltan archivos para construir el Overview. Revisa outputs/maps y data/processed.")
                return

            score_df = pd.read_csv(score_path)
            hospital_df = pd.read_csv(hospital_path)

            ccaa_count = int(score_df["CCAA"].nunique())
            hospitals_total = int(pd.to_numeric(hospital_df["hospitals_total"], errors="coerce").fillna(0).sum())

            ranking_df = score_df[
                ["CCAA", "opportunity_score", "beds_per_100k", "market_12m_avg_eur_per_capita"]
            ].copy()
            ranking_df = ranking_df.rename(
                columns={
                    "opportunity_score": "KPI",
                    "beds_per_100k": "Beds",
                    "market_12m_avg_eur_per_capita": "Market",
                }
            )
            ranking_df = ranking_df.sort_values("KPI", ascending=False).head(12)
            ranking_df["KPI"] = ranking_df["KPI"].round(2)
            ranking_df["Beds"] = ranking_df["Beds"].round(2)
            ranking_df["Market"] = ranking_df["Market"].round(2)

            table_rows = "".join(
                "<tr>"
                f"<td>{html_lib.escape(str(row['CCAA']))}</td>"
                f"<td>{float(row['KPI']):.2f}</td>"
                f"<td>{float(row['Beds']):.2f}</td>"
                f"<td>{float(row['Market']):.2f}</td>"
                "</tr>"
                for _, row in ranking_df.iterrows()
            )

            disease_options = [
                "Obesity",
                "Diabetes",
                "Cardiovascular",
                "Respiratory",
                "Oncology",
            ]
            disease_options_html = "".join(
                f'<option value="{html_lib.escape(option)}"'
                + (" selected" if option == "Obesity" else "")
                + f'>{html_lib.escape(option)}</option>'
                for option in disease_options
            )

            map_html = map_html_path.read_text(encoding="utf-8")
            map_srcdoc = html_lib.escape(map_html, quote=True)

            composed = f"""
<style>
html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
    background: #f8fafc;
}}
.overview-stage {{
    position: relative;
    width: 100%;
    height: 100%;
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid #dbe3ee;
    background: #f8fafc;
}}
.overview-map-layer {{
    position: absolute;
    inset: 0;
}}
.overview-map-layer iframe {{
    width: 100%;
    height: 100%;
    border: 0;
}}
.overlay-top {{
    position: absolute;
    top: 14px;
    left: 50px;
    display: flex;
    gap: 10px;
    z-index: 25;
}}
.kpi-chip {{
    min-width: 132px;
    background: rgba(255,255,255,0.56);
    border: 1px solid #dbe3ee;
    border-radius: 12px;
    padding: 8px 12px;
    box-shadow: 0 6px 18px rgba(15,23,42,0.12);
}}
.kpi-chip .label {{
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #334155;
    font-weight: 700;
}}
.kpi-chip .value {{
    margin-top: 2px;
    font-size: 2rem;
    line-height: 1;
    font-weight: 700;
    color: #0f172a;
}}
.disease-panel {{
    position: absolute;
    top: 112px;
    left: 50px;
    z-index: 25;
    min-width: 164px;
    background: rgba(255,255,255,0.56);
    border: 1px solid #dbe3ee;
    border-radius: 10px;
    padding: 6px 8px;
    box-shadow: 0 6px 18px rgba(15,23,42,0.12);
    backdrop-filter: blur(4px);
}}
.disease-panel-label {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #334155;
    font-weight: 700;
    margin-bottom: 4px;
}}
.disease-panel select {{
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: rgba(255,255,255,0.85);
    color: #0f172a;
    font-size: 0.86rem;
    font-weight: 600;
    padding: 4px 6px;
    outline: none;
}}
.disease-panel-note {{
    margin-top: 4px;
    font-size: 0.7rem;
    color: #475569;
}}
.ranking-panel {{
    position: absolute;
    top: calc(12% + 55px);
    right: 14px;
    bottom: calc(20% + 10px);
    width: 28.5%;
    min-width: 240px;
    max-width: 380px;
    background: rgba(255,255,255,0.56);
    border: 1px solid #dbe3ee;
    border-radius: 14px;
    box-shadow: 0 8px 24px rgba(15,23,42,0.15);
    backdrop-filter: blur(4px);
    display: flex;
    flex-direction: column;
    z-index: 26;
}}
.ranking-title {{
    padding: 12px 14px 8px 14px;
    font-size: 1.28rem;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 1px solid #e5e7eb;
}}
.ranking-scroll {{
    overflow: auto;
    padding: 0 10px 10px 10px;
}}
.ranking-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.86rem;
}}
.ranking-table th,
.ranking-table td {{
    border: 1px solid #e2e8f0;
    padding: 6px 8px;
    text-align: left;
    white-space: nowrap;
}}
.ranking-table th {{
    position: sticky;
    top: 0;
    background: #f8fafc;
    z-index: 1;
    font-weight: 700;
}}

@media (max-width: 1100px) {{
    .ranking-panel {{
        width: 35%;
        min-width: 220px;
    }}
    .kpi-chip {{
        min-width: 108px;
    }}
}}
</style>

<div class="overview-stage">
    <div class="overview-map-layer">
        <iframe srcdoc="{map_srcdoc}"></iframe>
    </div>

    <div class="overlay-top">
        <div class="kpi-chip">
            <div class="label">CCAA</div>
            <div class="value">{ccaa_count}</div>
        </div>
        <div class="kpi-chip">
            <div class="label">Hospitals</div>
            <div class="value">{hospitals_total}</div>
        </div>
    </div>

    <div class="disease-panel">
        <div class="disease-panel-label">Disease</div>
        <select aria-label="Disease selector">
            {disease_options_html}
        </select>
        <div class="disease-panel-note">Ready to connect disease-specific layers.</div>
    </div>

    <aside class="ranking-panel">
        <div class="ranking-title">Ranking Top Opportunities</div>
        <div class="ranking-scroll">
            <table class="ranking-table">
                <thead>
                    <tr>
                        <th>CCAA</th>
                        <th>KPI</th>
                        <th>Beds</th>
                        <th>Market</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </aside>
</div>
"""

            components.html(composed, height=780, scrolling=False)
