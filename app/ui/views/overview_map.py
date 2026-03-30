from pathlib import Path
import html as html_lib
import json
import unicodedata

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ..state import build_view_href
from ..styles import get_embedded_theme_palette


class OverviewMapView:
    @staticmethod
    def _norm_text(value: object) -> str:
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return " ".join(text.replace("-", " ").split())

    @classmethod
    def _build_code_to_ccaa_map(cls, score_df: pd.DataFrame, boundaries_path: Path) -> dict[str, str]:
        if not boundaries_path.exists():
            return {}

        try:
            boundaries_geojson = json.loads(boundaries_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        score_names = score_df["CCAA"].dropna().astype(str).tolist()
        score_by_norm = {cls._norm_text(name): name for name in score_names}

        # Alias keys from geojson names to dataset naming conventions.
        score_by_norm.setdefault(cls._norm_text("Castilla-Leon"), "Castilla y León")
        score_by_norm.setdefault(cls._norm_text("Region de Murcia"), "Región de Murcia")
        score_by_norm.setdefault(cls._norm_text("Baleares"), "Illes Balears")
        score_by_norm.setdefault(cls._norm_text("Pais Vasco"), "País Vasco")
        score_by_norm.setdefault(cls._norm_text("Navarra"), "C. Foral de Navarra")
        score_by_norm.setdefault(cls._norm_text("Principado de Asturias"), "Ppdo. de Asturias")

        code_to_ccaa: dict[str, str] = {}
        for feature in boundaries_geojson.get("features", []):
            props = feature.get("properties", {})
            code = str(props.get("cod_ccaa", "")).strip()
            if not code:
                continue

            candidates = [
                props.get("CCAA"),
                props.get("ccaa"),
                props.get("name"),
                props.get("noml_ccaa"),
                props.get("nombre"),
            ]

            matched_name = None
            for candidate in candidates:
                norm_candidate = cls._norm_text(candidate)
                if norm_candidate in score_by_norm:
                    matched_name = score_by_norm[norm_candidate]
                    break

            if matched_name:
                code_to_ccaa[code] = matched_name

        return code_to_ccaa

    def render(self) -> None:
        palette = get_embedded_theme_palette()

        project_root = Path(__file__).resolve().parents[3]
        map_html_path = project_root / "outputs" / "maps" / "ccaa_map_opportunity_score.html"
        boundaries_path = project_root / "data" / "raw" / "ccaa_boundaries.geojson"
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
            ranking_df = ranking_df.sort_values("KPI", ascending=False)
            ranking_df["KPI"] = ranking_df["KPI"].round(2)
            ranking_df["Beds"] = ranking_df["Beds"].round(2)
            ranking_df["Market"] = ranking_df["Market"].round(2)

            fallback_flag_url = "https://upload.wikimedia.org/wikipedia/commons/9/9a/Flag_of_Spain.svg"
            ccaa_flag_by_name = {
                "Andalucía": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/Flag_of_Andaluc%C3%ADa.svg/640px-Flag_of_Andaluc%C3%ADa.svg.png",
                "Aragón": "https://upload.wikimedia.org/wikipedia/commons/1/18/Flag_of_Aragon.svg",
                "Ppdo. de Asturias": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Flag_of_Asturias.svg",
                "Principado de Asturias": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Flag_of_Asturias.svg",
                "Illes Balears": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_the_Balearic_Islands.svg/640px-Flag_of_the_Balearic_Islands.svg.png",
                "Canarias": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Flag_of_Canary_Islands%2C_version.svg/640px-Flag_of_Canary_Islands%2C_version.svg.png",
                "Cantabria": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Flag_of_Cantabria.svg/640px-Flag_of_Cantabria.svg.png",
                "Castilla y León": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/Flag_of_Castile_and_Le%C3%B3n.svg/640px-Flag_of_Castile_and_Le%C3%B3n.svg.png",
                "Castilla-La Mancha": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Flag_of_Castile-La_Mancha.svg/640px-Flag_of_Castile-La_Mancha.svg.png",
                "Cataluña": "https://upload.wikimedia.org/wikipedia/commons/c/ce/Flag_of_Catalonia.svg",
                "Comunidad Valenciana": "https://upload.wikimedia.org/wikipedia/commons/1/16/Flag_of_the_Valencian_Community_%282x3%29.svg",
                "Extremadura": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/Flag_Extremadura.svg/640px-Flag_Extremadura.svg.png",
                "Galicia": "https://upload.wikimedia.org/wikipedia/commons/6/64/Flag_of_Galicia.svg",
                "Madrid": "https://upload.wikimedia.org/wikipedia/commons/9/9c/Flag_of_the_Community_of_Madrid.svg",
                "Comunidad de Madrid": "https://upload.wikimedia.org/wikipedia/commons/9/9c/Flag_of_the_Community_of_Madrid.svg",
                "Región de Murcia": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Flag_of_the_Region_of_Murcia.svg/640px-Flag_of_the_Region_of_Murcia.svg.png",
                "C. Foral de Navarra": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Bandera_de_Navarra.svg/640px-Bandera_de_Navarra.svg.png",
                "Comunidad Foral de Navarra": "https://upload.wikimedia.org/wikipedia/commons/b/b7/Flag_of_Navarre.svg",
                "País Vasco": "https://upload.wikimedia.org/wikipedia/commons/2/2d/Flag_of_the_Basque_Country.svg",
                "La Rioja": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Bandera_Republicana_de_La_Rioja.png/640px-Bandera_Republicana_de_La_Rioja.png",
                "Ceuta": "https://upload.wikimedia.org/wikipedia/commons/d/d3/Flag_of_Ceuta.svg",
                "Melilla": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Flag_Melilla.svg/640px-Flag_Melilla.svg.png",
            }
            ccaa_flag_by_norm = {self._norm_text(name): url for name, url in ccaa_flag_by_name.items()}

            code_to_ccaa = self._build_code_to_ccaa_map(score_df, boundaries_path)
            detail_base_href = build_view_href("ccaa_detail")

            rows_html = []
            for _, row in ranking_df.iterrows():
                ccaa_name = str(row["CCAA"])
                ccaa_flag_url = ccaa_flag_by_norm.get(self._norm_text(ccaa_name), fallback_flag_url)
                detail_href = build_view_href("ccaa_detail", {"ccaa": ccaa_name})
                rows_html.append(
                    "<tr>"
                    "<td class='ccaa-cell'>"
                    "<span class='ccaa-name-wrap'>"
                    f"<img class='ccaa-flag-mini' src='{html_lib.escape(ccaa_flag_url, quote=True)}' alt='Bandera {html_lib.escape(ccaa_name)}' loading='lazy' onerror='this.onerror=null;this.src=\"{html_lib.escape(fallback_flag_url, quote=True)}\";' />"
                    f"<span class='ccaa-name'>{html_lib.escape(ccaa_name)}</span>"
                    "</span>"
                    f"<a class='ccaa-hover-btn' href='{html_lib.escape(detail_href, quote=True)}' target='_blank' rel='noopener noreferrer'>Ir</a>"
                    "</td>"
                    f"<td>{float(row['KPI']):.2f}</td>"
                    f"<td>{float(row['Beds']):.2f}</td>"
                    f"<td>{float(row['Market']):.2f}</td>"
                    "</tr>"
                )
            table_rows = "".join(rows_html)

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
            map_click_script = f"""
<script>
(function() {{
    const detailBaseHref = {json.dumps(detail_base_href)};
    const codeToCcaa = {json.dumps(code_to_ccaa, ensure_ascii=False)};

    const getMapInstance = () => {{
        const mapKey = Object.keys(window).find((key) => key.startsWith("map_") && window[key] && typeof window[key].eachLayer === "function");
        return mapKey ? window[mapKey] : null;
    }};

    const goToDetail = (ccaaName) => {{
        if (!ccaaName) return;
        const targetUrl = `${{detailBaseHref}}&ccaa=${{encodeURIComponent(ccaaName)}}`;
        const newTab = window.open(targetUrl, "_blank", "noopener,noreferrer");
        if (!newTab) {{
            window.top.location.href = targetUrl;
        }}
    }};

    const resolveCcaaName = (props) => {{
        if (!props) return "";
        const code = String(props.cod_ccaa || props.cod || "").trim();
        if (code && codeToCcaa[code]) return codeToCcaa[code];
        const paddedCode = code ? code.padStart(2, "0") : "";
        if (paddedCode && codeToCcaa[paddedCode]) return codeToCcaa[paddedCode];

        const candidates = [props.CCAA, props.ccaa, props.name, props.noml_ccaa, props.nombre];
        for (const candidate of candidates) {{
            if (typeof candidate === "string" && candidate.trim()) return candidate.trim();
        }}
        return "";
    }};

    const attachClickToLayer = (layer) => {{
        if (!layer || !layer.feature || !layer.feature.properties || typeof layer.on !== "function") return;
        if (layer.__ccaaClickBound) return;

        layer.__ccaaClickBound = true;
        layer.on("click", () => {{
            const ccaaName = resolveCcaaName(layer.feature.properties);
            goToDetail(ccaaName);
        }});

        if (typeof layer.getElement === "function") {{
            const element = layer.getElement();
            if (element && element.style) {{
                element.style.cursor = "pointer";
            }}
        }}
    }};

    const wireMapClicks = () => {{
        const map = getMapInstance();
        if (!map) return;

        map.eachLayer((layer) => attachClickToLayer(layer));
        map.on("layeradd", (event) => attachClickToLayer(event.layer));
    }};

    if (document.readyState === "loading") {{
        document.addEventListener("DOMContentLoaded", wireMapClicks, {{ once: true }});
    }} else {{
        wireMapClicks();
    }}
}})();
</script>
"""

            if "</html>" in map_html:
                map_html = map_html.replace("</html>", f"{map_click_script}</html>")
            else:
                map_html = f"{map_html}{map_click_script}"

            map_srcdoc = html_lib.escape(map_html, quote=True)

            composed = f"""
<style>
html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    font-family: {palette['font_stack']};
    background: {palette['app_bg']};
}}
.overview-stage {{
    position: relative;
    width: 100%;
    height: 100%;
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid {palette['card_border']};
    background: {palette['app_bg']};
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
    background: {palette['panel_bg']};
    border: 1px solid {palette['card_border']};
    border-radius: 12px;
    padding: 8px 12px;
    box-shadow: 0 6px 18px rgba(15,23,42,0.12);
}}
.kpi-chip .label {{
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {palette['label_color']};
    font-weight: 700;
}}
.kpi-chip .value {{
    margin-top: 2px;
    font-size: 2rem;
    line-height: 1;
    font-weight: 700;
    color: {palette['title_color']};
}}
.disease-panel {{
    position: absolute;
    top: 112px;
    left: 50px;
    z-index: 25;
    min-width: 164px;
    background: {palette['panel_bg']};
    border: 1px solid {palette['card_border']};
    border-radius: 10px;
    padding: 6px 8px;
    box-shadow: 0 6px 18px rgba(15,23,42,0.12);
    backdrop-filter: blur(4px);
}}
.disease-panel-label {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {palette['label_color']};
    font-weight: 700;
    margin-bottom: 4px;
}}
.disease-panel select {{
    width: 100%;
    border: 1px solid {palette['surface_border']};
    border-radius: 8px;
    background: {palette['surface_bg']};
    color: {palette['surface_text']};
    font-size: 0.86rem;
    font-weight: 600;
    padding: 4px 6px;
    outline: none;
}}
.disease-panel-note {{
    margin-top: 4px;
    font-size: 0.7rem;
    color: {palette['muted_text']};
}}
.ranking-panel {{
    position: absolute;
    top: calc(12% + 55px);
    right: 14px;
    bottom: calc(20% + 10px);
    width: 28.5%;
    min-width: 240px;
    max-width: 380px;
    background: {palette['panel_bg']};
    border: 1px solid {palette['card_border']};
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
    color: {palette['title_color']};
    border-bottom: 1px solid {palette['card_border']};
}}
.ranking-scroll {{
    overflow-y: auto;
    overflow-x: hidden;
    padding: 0 10px 10px 10px;
}}
.ranking-table {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 0.8rem;
}}
.ranking-table col:nth-child(1) {{
    width: 52.8%;
}}
.ranking-table col:nth-child(2) {{
    width: 14.8%;
}}
.ranking-table col:nth-child(3) {{
    width: 14.8%;
}}
.ranking-table col:nth-child(4) {{
    width: 17.6%;
}}
.ranking-table th,
.ranking-table td {{
    border: 1px solid {palette['card_border']};
    padding: 5px 6px;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: {palette['text_color']};
}}
.ranking-table th {{
    position: sticky;
    top: 0;
    background: {palette['surface_bg']};
    z-index: 1;
    font-weight: 700;
    color: {palette['label_color']};
}}
.ccaa-cell {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    min-width: 0;
}}
.ccaa-name-wrap {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
}}
.ccaa-flag-mini {{
    width: 16px;
    height: 11px;
    object-fit: cover;
    border-radius: 2px;
    border: 1px solid {palette['surface_border']};
    flex: 0 0 auto;
}}
.ccaa-name {{
    color: {palette['title_color']};
    font-weight: 700;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.ccaa-hover-btn {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-decoration: none !important;
    color: {palette['accent']} !important;
    background: {palette['surface_bg']};
    border: 1px solid {palette['accent_soft']};
    border-radius: 7px;
    padding: 2px 6px;
    font-size: 0.7rem;
    font-weight: 700;
    line-height: 1;
    flex-shrink: 0;
    opacity: 0;
    pointer-events: none;
    transform: translateX(4px);
    transition: opacity 0.16s ease, transform 0.16s ease;
}}
.ranking-table tbody tr:hover .ccaa-hover-btn {{
    opacity: 1;
    pointer-events: auto;
    transform: translateX(0);
}}
@media (hover: none) {{
    .ccaa-hover-btn {{
        opacity: 1;
        pointer-events: auto;
        transform: none;
    }}
}}

@media (max-width: 1100px) {{
    .ranking-panel {{
        width: 35%;
        min-width: 200px;
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
                <colgroup>
                    <col>
                    <col>
                    <col>
                    <col>
                </colgroup>
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
