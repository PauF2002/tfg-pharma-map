from pathlib import Path
import html as html_lib
import json
import unicodedata
import base64
import mimetypes

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

    @staticmethod
    def _file_to_data_uri(file_path: Path) -> str | None:
        if not file_path.exists():
            return None

        try:
            binary = file_path.read_bytes()
        except OSError:
            return None

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "image/png"
        encoded = base64.b64encode(binary).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    @classmethod
    def _build_local_flag_map(cls, flags_dir: Path) -> dict[str, str]:
        local_flag_files = {
            "Andalucía": "Flag_of_Andalucía.svg.png",
            "Aragón": "Flag_of_Aragon.svg",
            "Ppdo. de Asturias": "Flag_of_Asturias.svg",
            "Principado de Asturias": "Flag_of_Asturias.svg",
            "Illes Balears": "Flag_of_the_Balearic_Islands.svg.png",
            "Canarias": "CANARIAS.jpg",
            "Cantabria": "Flag_of_Cantabria.svg.png",
            "Castilla y León": "Flag_of_Castile_and_León.svg.png",
            "Castilla-La Mancha": "Flag_of_Castile-La_Mancha.svg.png",
            "Cataluña": "Flag_of_Catalonia.svg",
            "Comunidad Valenciana": "Flag_of_the_Valencian_Community_(2x3).svg",
            "Extremadura": "Flag_of_Extremadura,_Spain_(with_coat_of_arms).svg.png",
            "Galicia": "Flag_of_Galicia.svg",
            "Madrid": "Flag_of_the_Community_of_Madrid.svg",
            "Comunidad de Madrid": "Flag_of_the_Community_of_Madrid.svg",
            "Región de Murcia": "Flag_of_the_Region_of_Murcia.svg.png",
            "C. Foral de Navarra": "Bandera_de_Navarra.svg.png",
            "Comunidad Foral de Navarra": "Bandera_de_Navarra.svg.png",
            "País Vasco": "Flag_of_the_Basque_Country.svg",
            "La Rioja": "Bandera_Republicana_de_La_Rioja.png",
            "Ceuta": "Flag_of_Ceuta.svg",
            "Melilla": "Flag_of_Melilla.svg.png",
        }

        local_flags: dict[str, str] = {}
        for ccaa_name, filename in local_flag_files.items():
            data_uri = cls._file_to_data_uri(flags_dir / filename)
            if data_uri:
                local_flags[cls._norm_text(ccaa_name)] = data_uri
        return local_flags

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
        boundaries_path = project_root / "data" / "raw" / "ccaa_boundaries.geojson"
        hospital_path = project_root / "data" / "processed" / "ccaa_hospital_summary.csv"
        flags_dir = project_root / "app" / "assets" / "fotos"

        qp_disease = st.query_params.get("disease")
        if isinstance(qp_disease, list):
            qp_disease = qp_disease[0]
        disease_options = [
            "Obesity",
            "Tabaquismo",
            "Alzheimer",
            "Epilepsia",
            "Diabetes",
            "Cardiovascular",
            "Respiratory",
            "Oncology",
        ]
        selected_disease = str(qp_disease or "Obesity") if str(qp_disease or "").strip() in disease_options else "Obesity"

        disease_norm = self._norm_text(selected_disease)
        # Use the same interactive base map for all diseases (visual layer),
        # while selecting disease-specific score CSVs for data-driven panels.
        map_html_path = project_root / "outputs" / "maps" / "ccaa_map_opportunity_score.html"
        if any(term in disease_norm for term in ("smoking", "smoke", "tabaquismo", "tabaco", "fumador", "fumadores")):
            score_path = project_root / "data" / "processed" / "ccaa_smoking_opportunity_score.csv"
        elif "alzheimer" in disease_norm:
            score_path = project_root / "data" / "processed" / "ccaa_alzheimer_opportunity_score.csv"
        elif "epilepsia" in disease_norm or "epilepsy" in disease_norm:
            score_path = project_root / "data" / "processed" / "ccaa_epilepsia_opportunity_score.csv"
        elif "diabetes" in disease_norm:
            diabetes_path = project_root / "data" / "processed" / "ccaa_diabetes_opportunity_score.csv"
            score_path = diabetes_path if diabetes_path.exists() else project_root / "data" / "processed" / "ccaa_opportunity_score.csv"
        else:
            score_path = project_root / "data" / "processed" / "ccaa_opportunity_score.csv"

        # Human-friendly disease label for the KPI formula (Spanish terms where appropriate)
        formula_disease_map = {
            "obesity": "obesidad",
            "smoking": "tabaquismo",
            "tabaquismo": "tabaquismo",
            "alzheimer": "alzheimer",
            "diabetes": "diabetes",
            "cardiovascular": "cardiovascular",
            "respiratory": "respiratorio",
            "oncology": "oncología",
        }
        formula_disease_key = None
        for key in formula_disease_map.keys():
            if key in disease_norm:
                formula_disease_key = key
                break
        formula_disease_label = formula_disease_map.get(formula_disease_key, selected_disease.lower())

        disease_selector_html = "".join(
            (
                f'<a class="disease-pill{" active" if option == selected_disease else ""}" '
                f'href="{html_lib.escape(build_view_href("overview_map", {"disease": option}), quote=True)}">'
                f'{html_lib.escape(option)}</a>'
            )
            for option in disease_options
        )

        st.markdown(
            f"""
            <div class="overview-disease-switcher">
                <div class="disease-switcher-label">Disease</div>
                <div class="disease-switcher-row">
                    {disease_selector_html}
                </div>
                <div class="disease-switcher-note">Selecciona una enfermedad para recargar el panel con su propio dataset.</div>
            </div>
            <style>
            .overview-disease-switcher {{
                margin: 0.25rem 0 0.35rem 0;
                padding: 6px 10px;
                height: 40px;
                display: flex;
                align-items: center;
                gap: 12px;
                border: 1px solid {palette['card_border']};
                border-radius: 14px;
                background: color-mix(in srgb, {palette['panel_bg']} 82%, transparent);
                backdrop-filter: blur(4px);
                box-shadow: 0 6px 18px rgba(15,23,42,0.10);
            }}
            .disease-switcher-label {{
                font-size: 0.64rem;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: {palette['label_color']};
                font-weight: 700;
                margin: 0;
                padding-right: 8px;
                white-space: nowrap;
            }}
            .disease-switcher-row {{
                display: flex;
                flex-wrap: nowrap;
                gap: 8px;
                align-items: center;
            }}
            .disease-pill {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 4px 8px; /* narrower */
                border-radius: 999px;
                border: 1px solid {palette['surface_border']};
                background: {palette['surface_bg']};
                color: {palette['surface_text']};
                text-decoration: none !important; /* force remove underline */
                font-size: 0.74rem; /* slightly smaller */
                font-weight: 700;
                line-height: 1;
                transition: transform 0.12s ease, border-color 0.12s ease, background 0.12s ease;
            }}
            .disease-pill:hover {{
                transform: translateY(-1px);
                border-color: {palette['accent']};
            }}
            .disease-pill.active {{
                background: linear-gradient(135deg, {palette['accent']} 0%, {palette['accent']}cc 100%);
                border-color: {palette['accent']};
                color: #ffffff;
            }}
            /* Ensure anchor tags never show underline from global styles */
            a.disease-pill, .disease-pill {{
                text-decoration: none !important;
            }}
            .disease-switcher-note {{
                display: none; /* hide explanatory note to keep switcher compact */
            }}
            /* Make the external disease pills text not underlined (defensive) */
            .disease-pill {{
                text-decoration: none;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        overview_panel = st.container(key="overview_map_panel")
        with overview_panel:
            if not map_html_path.exists() or not score_path.exists() or not hospital_path.exists():
                st.error("Faltan archivos para construir el Overview de la enfermedad seleccionada. Revisa outputs/maps y data/processed.")
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

            obesity_pct_by_ccaa: dict[str, float] = {}
            obesity_score_path = project_root / "data" / "processed" / "ccaa_opportunity_score.csv"
            if obesity_score_path.exists():
                obesity_df = pd.read_csv(obesity_score_path)
                if "CCAA" in obesity_df.columns and "obesity_pct" in obesity_df.columns:
                    obesity_clean = obesity_df[["CCAA", "obesity_pct"]].copy()
                    obesity_clean["obesity_pct"] = pd.to_numeric(obesity_clean["obesity_pct"], errors="coerce")
                    obesity_pct_by_ccaa = {
                        str(row["CCAA"]): float(row["obesity_pct"])
                        for _, row in obesity_clean.dropna(subset=["obesity_pct"]).iterrows()
                    }

            kpi_min = float(ranking_df["KPI"].min()) if not ranking_df.empty else 0.0
            kpi_max = float(ranking_df["KPI"].max()) if not ranking_df.empty else 0.0

            fallback_flag_url = "https://upload.wikimedia.org/wikipedia/commons/9/9a/Flag_of_Spain.svg"
            ccaa_flag_by_norm = self._build_local_flag_map(flags_dir)

            code_to_ccaa = self._build_code_to_ccaa_map(score_df, boundaries_path)
            detail_base_href = build_view_href("ccaa_detail", {"disease": selected_disease})

            rows_html = []
            for _, row in ranking_df.iterrows():
                ccaa_name = str(row["CCAA"])
                ccaa_flag_url = ccaa_flag_by_norm.get(self._norm_text(ccaa_name), fallback_flag_url)
                detail_href = build_view_href("ccaa_detail", {"ccaa": ccaa_name, "disease": selected_disease})
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
            score_by_ccaa = {str(row["CCAA"]): float(row["KPI"]) for _, row in ranking_df.iterrows()}
            metrics_by_ccaa = {
                str(row["CCAA"]): {
                    "kpi": float(row["KPI"]),
                    "beds": float(row["Beds"]),
                    "market": float(row["Market"]),
                    "obesity_pct": obesity_pct_by_ccaa.get(str(row["CCAA"])),
                }
                for _, row in ranking_df.iterrows()
            }

            disease_options_html = "".join(
                f'<option value="{html_lib.escape(option)}"'
                + (" selected" if option == selected_disease else "")
                + f'>{html_lib.escape(option)}</option>'
                for option in disease_options
            )

            map_html = map_html_path.read_text(encoding="utf-8")
            map_click_script = f"""
<script>
(function() {{
    const detailBaseHref = {json.dumps(detail_base_href)};
    const codeToCcaa = {json.dumps(code_to_ccaa, ensure_ascii=False)};
    const scoreByCcaaRaw = {json.dumps(score_by_ccaa, ensure_ascii=False)};
    const metricsByCcaaRaw = {json.dumps(metrics_by_ccaa, ensure_ascii=False)};

    const normalize = (value) => String(value || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/-/g, " ")
        .replace(/\s+/g, " ")
        .trim();

    const scoreByCcaa = Object.fromEntries(
        Object.entries(scoreByCcaaRaw).map(([k, v]) => [normalize(k), Number(v)])
    );
    const metricsByCcaa = Object.fromEntries(
        Object.entries(metricsByCcaaRaw).map(([k, v]) => [normalize(k), v])
    );
    const scoreValues = Object.values(scoreByCcaa).filter((v) => Number.isFinite(v));
    const minScore = scoreValues.length ? Math.min(...scoreValues) : 0;
    const maxScore = scoreValues.length ? Math.max(...scoreValues) : 100;

    const hexToRgb = (hex) => {{
        const c = String(hex || "").replace("#", "");
        const full = c.length === 3 ? c.split("").map((x) => x + x).join("") : c;
        return [
            parseInt(full.slice(0, 2), 16),
            parseInt(full.slice(2, 4), 16),
            parseInt(full.slice(4, 6), 16),
        ];
    }};

    const rgbToHex = (r, g, b) =>
        `#${{[r, g, b]
            .map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0"))
            .join("")}}`;

    const blend = (fromHex, toHex, t) => {{
        const a = hexToRgb(fromHex);
        const b = hexToRgb(toHex);
        const tt = Math.max(0, Math.min(1, Number.isFinite(t) ? t : 0));
        return rgbToHex(
            a[0] + (b[0] - a[0]) * tt,
            a[1] + (b[1] - a[1]) * tt,
            a[2] + (b[2] - a[2]) * tt,
        );
    }};

    const scoreToColor = (score) => {{
        if (!Number.isFinite(score)) return "#cbd5e1";
        const span = maxScore - minScore;
        const t = span > 0 ? (score - minScore) / span : 0.5;
        // Original blue gradient
        return blend("#dbeafe", "#1d4ed8", t);
    }};

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

    const applyChoroplethStyle = (layer) => {{
        if (!layer || !layer.feature || !layer.feature.properties || typeof layer.setStyle !== "function") return;
        const ccaaName = resolveCcaaName(layer.feature.properties);
        const score = scoreByCcaa[normalize(ccaaName)];
        const fillColor = scoreToColor(score);
        layer.setStyle({{
            color: "#3b82f6",
            weight: 2,
            opacity: 0.95,
            fillColor,
            fillOpacity: 0.68,
        }});
    }};

    const bindDiseaseTooltip = (layer, ccaaName) => {{
        if (!layer) return;
        const metric = metricsByCcaa[normalize(ccaaName)] || null;
        const kpiText = metric && Number.isFinite(Number(metric.kpi)) ? Number(metric.kpi).toFixed(2) : "N/A";
        const bedsText = metric && Number.isFinite(Number(metric.beds)) ? Number(metric.beds).toFixed(2) : "N/A";
        const marketText = metric && Number.isFinite(Number(metric.market)) ? Number(metric.market).toFixed(2) : "N/A";
        const obesityText = metric && Number.isFinite(Number(metric.obesity_pct)) ? Number(metric.obesity_pct).toFixed(1) : "N/A";
        const html = [
            "<div style='min-width:220px'>",
            `<div style='font-weight:700;margin-bottom:6px'>${{ccaaName || "CCAA"}}</div>`,
            `<div><strong>KPI</strong> ${{kpiText}}</div>`,
            `<div><strong>Beds / 100k</strong> ${{bedsText}}</div>`,
            `<div><strong>Market € / cap (12m avg)</strong> ${{marketText}}</div>`,
            `<div><strong>Obesity % (latest)</strong> ${{obesityText}}</div>`,
            "</div>",
        ].join("");

        if (typeof layer.off === "function") {{
            layer.off("mouseover");
            layer.off("mouseout");
            layer.off("mousemove");
        }}
        if (typeof layer.unbindTooltip === "function") layer.unbindTooltip();
        if (typeof layer.unbindPopup === "function") layer.unbindPopup();
        if (typeof layer.bindTooltip === "function") {{
            layer.bindTooltip(html, {{
                sticky: true,
                direction: "top",
                opacity: 0.95,
                className: "disease-tooltip",
            }});
        }}
    }};

    const installLegacyHoverBlockers = (map) => {{
        if (!map || map.__legacyHoverBlocked) return;
        map.__legacyHoverBlocked = true;

        const styleId = "overview-hover-blockers";
        if (!document.getElementById(styleId)) {{
            const styleTag = document.createElement("style");
            styleTag.id = styleId;
            styleTag.textContent = `
                .leaflet-tooltip {{ display: none !important; }}
                .leaflet-tooltip.disease-tooltip {{ display: block !important; }}
                .leaflet-popup {{ display: none !important; }}
            `;
            document.head.appendChild(styleTag);
        }}

        map.on("popupopen", (event) => {{
            if (event && event.popup) map.closePopup(event.popup);
        }});
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

        applyChoroplethStyle(layer);
        const ccaaName = resolveCcaaName(layer.feature.properties);
        bindDiseaseTooltip(layer, ccaaName);
    }};

    const visitFeatureLayers = (rootLayer, visitor) => {{
        if (!rootLayer) return;
        if (rootLayer.feature && rootLayer.feature.properties) {{
            visitor(rootLayer);
        }}
        if (typeof rootLayer.eachLayer === "function") {{
            rootLayer.eachLayer((child) => visitFeatureLayers(child, visitor));
        }}
    }};

    const wireMapClicks = () => {{
        const map = getMapInstance();
        if (!map) return;

        installLegacyHoverBlockers(map);

        map.eachLayer((layer) => visitFeatureLayers(layer, attachClickToLayer));
        map.on("layeradd", (event) => visitFeatureLayers(event.layer, attachClickToLayer));
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
    background: color-mix(in srgb, {palette['panel_bg']} 78%, transparent);
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
    top: 88px; /* moved slightly lower */
    left: 50px;
    z-index: 25;
    min-width: 140px; /* narrower */
    max-width: 240px;
    height: 44px; /* compact fixed height */
    background: color-mix(in srgb, {palette['panel_bg']} 76%, transparent);
    border: 1px solid {palette['card_border']};
    border-radius: 10px;
    padding: 2px 8px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    box-shadow: 0 6px 18px rgba(15,23,42,0.12);
    backdrop-filter: blur(4px);
}}
.disease-panel-label {{
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: {palette['label_color']};
    font-weight: 700;
    margin: 0;
    line-height: 1;
}}
.disease-panel-value {{
    font-size: 0.82rem;
    font-weight: 800; /* bold disease name */
    margin: 0;
    padding: 0;
    color: {palette['title_color']};
    text-decoration: none !important;
    line-height: 1;
}}
.disease-panel select {{
    width: 100%;
    border: 1px solid {palette['surface_border']};
    border-radius: 8px;
    background: {palette['surface_bg']};
    color: {palette['surface_text']};
    font-size: 0.78rem;
    font-weight: 600;
    padding: 2px 6px;
    outline: none;
}}
.disease-panel-note {{
    display: none; /* hidden to keep panel compact */
}}
.map-legend-panel {{
    position: absolute;
    top: 212px;
    left: 50px;
    z-index: 25;
    width: min(320px, calc(100% - 88px));
    background: color-mix(in srgb, {palette['panel_bg']} 84%, transparent);
    border: 1px solid {palette['card_border']};
    border-radius: 12px;
    padding: 10px 12px;
    box-shadow: 0 6px 18px rgba(15,23,42,0.12);
    backdrop-filter: blur(4px);
}}
.map-legend-title {{
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {palette['label_color']};
    font-weight: 700;
    margin-bottom: 8px;
}}
.map-legend-scale {{
    height: 12px;
    border-radius: 999px;
    border: 1px solid {palette['surface_border']};
    background: linear-gradient(90deg, #dbeafe 0%, #93c5fd 45%, #2563eb 100%);
}}
.map-legend-range {{
    margin-top: 4px;
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 0.72rem;
    color: {palette['muted_text']};
    font-weight: 600;
}}
.map-legend-note {{
    margin-top: 8px;
    font-size: 0.72rem;
    color: {palette['text_color']};
    line-height: 1.3;
}}
.map-legend-formula {{
    margin-top: 6px;
    font-size: 0.7rem;
    color: {palette['muted_text']};
    line-height: 1.35;
}}
.ranking-panel {{
    position: absolute;
    top: calc(12% + 55px);
    right: 14px;
    bottom: calc(20% + 10px);
    width: 28.5%;
    min-width: 240px;
    max-width: 380px;
    background: color-mix(in srgb, {palette['panel_bg']} 78%, transparent);
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
    .map-legend-panel {{
        width: min(290px, calc(100% - 88px));
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
        <div class="disease-panel-value">{html_lib.escape(selected_disease)}</div>
        <div class="disease-panel-note">Dataset activo para el panel actual.</div>
    </div>

    <div class="map-legend-panel" role="note" aria-label="KPI legend">
        <div class="map-legend-title">Legend: Opportunity KPI</div>
        <div class="map-legend-scale" aria-hidden="true"></div>
        <div class="map-legend-range">
            <span>Low ({kpi_min:.2f})</span>
            <span>High ({kpi_max:.2f})</span>
        </div>
        <div class="map-legend-note">
            Azul más oscuro = mayor oportunidad estimada para la CCAA.
        </div>
        <div class="map-legend-formula">
            KPI = 45% mercado per cápita (12m) + 35% <strong>{html_lib.escape(formula_disease_label)}</strong> + 20% camas/100k,
            tras normalizar cada variable entre 0 y 1 (min-max) y escalar a 0-100.
        </div>
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
