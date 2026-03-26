from pathlib import Path
import html as html_lib
import json
import unicodedata

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ..state import build_view_href
from ..styles import get_embedded_theme_palette


class CcaaDetailView:
    @staticmethod
    def _fmt(value: object, decimals: int = 2, suffix: str = "") -> str:
        numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.isna(numeric):
            return "--"
        return f"{float(numeric):,.{decimals}f}{suffix}".replace(",", "_").replace(".", ",").replace("_", ".")

    @staticmethod
    def _norm_text(value: object) -> str:
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return " ".join(text.replace("-", " ").split())

    @classmethod
    def _build_score_name_to_code_map(cls, score_df: pd.DataFrame, boundaries_path: Path) -> dict[str, str]:
        if not boundaries_path.exists():
            return {}

        try:
            boundaries_geojson = json.loads(boundaries_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        score_names = score_df["CCAA"].dropna().astype(str).tolist()
        score_by_norm = {cls._norm_text(name): name for name in score_names}

        score_by_norm.setdefault(cls._norm_text("Castilla-Leon"), "Castilla y León")
        score_by_norm.setdefault(cls._norm_text("Region de Murcia"), "Región de Murcia")
        score_by_norm.setdefault(cls._norm_text("Baleares"), "Illes Balears")
        score_by_norm.setdefault(cls._norm_text("Pais Vasco"), "País Vasco")
        score_by_norm.setdefault(cls._norm_text("Navarra"), "C. Foral de Navarra")
        score_by_norm.setdefault(cls._norm_text("Principado de Asturias"), "Ppdo. de Asturias")
        score_by_norm.setdefault(cls._norm_text("Aragon"), "Aragón")
        score_by_norm.setdefault(cls._norm_text("Comunidad Autonoma de Aragon"), "Aragón")

        score_name_to_code: dict[str, str] = {}
        for feature in boundaries_geojson.get("features", []):
            props = feature.get("properties", {})
            code = str(props.get("cod_ccaa", "")).strip().zfill(2)
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
                score_name_to_code[matched_name] = code

        # Ensure Aragón is explicitly mapped to code 02
        score_name_to_code["Aragón"] = "02"
        score_name_to_code["Aragon"] = "02"

        return score_name_to_code

    @classmethod
    def _build_snapshot_map_html(
        cls,
        base_map_html: str,
        selected_ccaa: str,
        selected_code: str,
        palette: dict[str, str],
    ) -> str:
        selected_name_norm = cls._norm_text(selected_ccaa)

        snapshot_script = f"""
<script>
(function() {{
    const selectedCode = {json.dumps(selected_code.zfill(2) if selected_code else "")};
    const selectedNameNorm = {json.dumps(selected_name_norm)};
    const accentColor = {json.dumps(palette['accent'])};
    const mutedBorder = {json.dumps(palette['card_border'])};
    const mutedFill = {json.dumps(palette['surface_bg'])};

    const normalize = (value) => String(value || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/-/g, " ")
        .replace(/\s+/g, " ")
        .trim();

    const getMapInstance = () => {{
        const key = Object.keys(window).find((k) => k.startsWith("map_") && window[k] && typeof window[k].eachLayer === "function");
        return key ? window[key] : null;
    }};

    const styleLayers = (map) => {{
        let selectedBounds = null;
        let selectedCCAAName = null;

        map.eachLayer((layer) => {{
            if (!layer || !layer.feature || !layer.feature.properties || typeof layer.setStyle !== "function") return;

            const props = layer.feature.properties;
            const code = String(props.cod_ccaa || "").trim().padStart(2, "0");
            const nameNorm = normalize(props.CCAA || props.ccaa || props.name || props.noml_ccaa || props.nombre || "");
            const isSelected = (selectedCode && code === selectedCode) || (selectedNameNorm && nameNorm === selectedNameNorm);

            if (isSelected) {{
                selectedCCAAName = props.CCAA || props.ccaa || props.name || props.noml_ccaa || props.nombre || null;
                layer.setStyle({{
                    color: accentColor,
                    weight: 2.2,
                    fillColor: accentColor,
                    fillOpacity: 0.82,
                    opacity: 1,
                }});
                if (typeof layer.bringToFront === "function") layer.bringToFront();

                if (typeof layer.getBounds === "function") {{
                    const layerBounds = layer.getBounds();
                    selectedBounds = selectedBounds ? selectedBounds.extend(layerBounds) : layerBounds;
                }}
            }} else {{
                layer.setStyle({{
                    color: mutedBorder,
                    weight: 1,
                    fillColor: mutedFill,
                    fillOpacity: 0.28,
                    opacity: 0.7,
                }});
            }}
        }});

        return {{ bounds: selectedBounds, ccaaName: selectedCCAAName }};
    }};

    const configureStaticMap = (map, selectedBounds, ccaaName) => {{
        if (map.dragging) map.dragging.enable();
        if (map.touchZoom) map.touchZoom.disable();
        if (map.doubleClickZoom) map.doubleClickZoom.disable();
        if (map.scrollWheelZoom) map.scrollWheelZoom.disable();
        if (map.boxZoom) map.boxZoom.disable();
        if (map.keyboard) map.keyboard.disable();
        if (map.tap) map.tap.enable();
        
        const container = map.getContainer();
        container.style.cursor = "grab";
        container.style.pointerEvents = "auto";
        container.style.userSelect = "none";

        if (map.zoomControl && map.zoomControl.remove) map.zoomControl.remove();
        document.querySelectorAll(".leaflet-control-zoom").forEach((node) => node.remove());
        L.control.zoom({{ position: "topright" }}).addTo(map);

        // Prevent accidental zoom changes while hovering interactive CCAA layers.
        const stopWheel = (event) => {{
            if (event && typeof event.preventDefault === "function") event.preventDefault();
            if (event && typeof event.stopPropagation === "function") event.stopPropagation();
            return false;
        }};

        map.getContainer().addEventListener("wheel", stopWheel, {{ passive: false }});
        map.eachLayer((layer) => {{
            if (layer && typeof layer.on === "function") {{
                layer.on("mouseover", () => {{
                    if (map.scrollWheelZoom) map.scrollWheelZoom.disable();
                }});
            }}
        }});

        const zoomControls = document.querySelectorAll(".leaflet-control-zoom");
        zoomControls.forEach((node) => {{
            node.style.display = "";
            node.style.pointerEvents = "auto";
        }});

        // Single framing for all CCAA: centered Iberian Peninsula with fixed zoom.
        const spainBounds = L.latLngBounds(
            L.latLng(27.4, -18.5),
            L.latLng(44.5, 4.5)
        );

        const hasSelectedBounds = selectedBounds && selectedBounds.isValid && selectedBounds.isValid();
        if (hasSelectedBounds) {{
            map.fitBounds(spainBounds, {{
                paddingTopLeft: [12, 12],
                paddingBottomRight: [420, 12]
            }});
            map.setZoom(Math.min(map.getZoom(), 6.1));
            map.setMinZoom(5.8);
            map.setMaxZoom(7.0);
            return;
        }}

        map.fitBounds(spainBounds, {{
            paddingTopLeft: [12, 12],
            paddingBottomRight: [420, 12]
        }});
        map.setZoom(Math.min(map.getZoom(), 6.1));
        map.setMinZoom(5.8);
        map.setMaxZoom(7.0);
    }};

    const init = () => {{
        const map = getMapInstance();
        if (!map) return;

        const result = styleLayers(map);
        configureStaticMap(map, result.bounds, result.ccaaName);
        map.on("layeradd", () => {{
            setTimeout(() => {{
                const updatedResult = styleLayers(map);
                configureStaticMap(map, updatedResult.bounds, updatedResult.ccaaName);
            }}, 0);
        }});
    }};

    if (document.readyState === "loading") {{
        document.addEventListener("DOMContentLoaded", init, {{ once: true }});
    }} else {{
        init();
    }}
}})();
</script>
"""

        if "</html>" in base_map_html:
            return base_map_html.replace("</html>", f"{snapshot_script}</html>")
        return f"{base_map_html}{snapshot_script}"

    def render(self) -> None:
        palette = get_embedded_theme_palette()

        project_root = Path(__file__).resolve().parents[3]
        map_html_path = project_root / "outputs" / "maps" / "ccaa_map_opportunity_score.html"
        boundaries_path = project_root / "data" / "raw" / "ccaa_boundaries.geojson"
        score_path = project_root / "data" / "processed" / "ccaa_opportunity_score.csv"
        market_path = project_root / "data" / "processed" / "ccaa_market_monthly.csv"

        if not score_path.exists() or not market_path.exists():
            st.error("Faltan archivos para construir el detalle CCAA. Revisa data/processed.")
            return

        score_df = pd.read_csv(score_path)
        market_df = pd.read_csv(market_path)

        ccaa_options = sorted(score_df["CCAA"].dropna().astype(str).unique().tolist())
        if not ccaa_options:
            st.warning("No hay CCAA disponibles para mostrar el detalle.")
            return

        qp_ccaa = st.query_params.get("ccaa")
        if isinstance(qp_ccaa, list):
            qp_ccaa = qp_ccaa[0]

        preferred_default = "Comunidad Valenciana"
        fallback_ccaa = preferred_default if preferred_default in ccaa_options else ccaa_options[0]
        selected_qp = qp_ccaa if qp_ccaa in ccaa_options else fallback_ccaa
        selected_ccaa = selected_qp

        overview_href = build_view_href("overview_map")
        market_href = build_view_href("market_state")
        detail_base_href = build_view_href("ccaa_detail")

        selected_row = score_df[score_df["CCAA"] == selected_ccaa]
        if selected_row.empty:
            st.warning(f"No hay datos para {selected_ccaa}.")
            return
        selected_row = selected_row.iloc[0]

        cv_row = score_df[score_df["CCAA"] == preferred_default]
        cv_row = cv_row.iloc[0] if not cv_row.empty else selected_row

        month_series = market_df[(market_df["CCAA"] == selected_ccaa)].copy()
        month_series["market_monthly_eur_per_capita"] = pd.to_numeric(
            month_series["market_monthly_eur_per_capita"], errors="coerce"
        )
        month_series = month_series.dropna(subset=["market_monthly_eur_per_capita", "year_month"])
        month_series = month_series.sort_values("year_month").tail(6)

        bars_html = ""
        if month_series.empty:
            bars_html = '<div class="ccaa-chart-empty">Sin serie mensual disponible</div>'
        else:
            max_value = float(month_series["market_monthly_eur_per_capita"].max())
            bars = []
            for _, row in month_series.iterrows():
                value = float(row["market_monthly_eur_per_capita"])
                bar_height = max(8.0, (value / max_value) * 100.0) if max_value > 0 else 8.0
                ym = str(row["year_month"])
                ym_label = ym[2:7] if len(ym) >= 7 else ym
                bars.append(
                    '<div class="ccaa-bar-wrap">'
                    f'<div class="ccaa-bar" style="height:{bar_height:.1f}%" title="{value:.2f} EUR/cap"></div>'
                    f'<div class="ccaa-bar-label">{html_lib.escape(ym_label)}</div>'
                    "</div>"
                )
            bars_html = "".join(bars)

        metric_rows = []

        def add_metric_row(label: str, col: str, lower_is_better: bool = False, suffix: str = "") -> None:
            selected_value = pd.to_numeric(pd.Series([selected_row.get(col)]), errors="coerce").iloc[0]
            cv_value = pd.to_numeric(pd.Series([cv_row.get(col)]), errors="coerce").iloc[0]

            if pd.isna(selected_value) or pd.isna(cv_value):
                symbol = "-"
                status_class = "neutral"
            else:
                if lower_is_better:
                    better = selected_value <= cv_value
                else:
                    better = selected_value >= cv_value
                symbol = "+" if better else "-"
                status_class = "good" if better else "bad"

            metric_rows.append(
                "<tr>"
                f"<td>{html_lib.escape(label)}</td>"
                f"<td>{self._fmt(selected_value, suffix=suffix)}</td>"
                f"<td>{self._fmt(cv_value, suffix=suffix)}</td>"
                f"<td class='status {status_class}'>{symbol}</td>"
                "</tr>"
            )

        add_metric_row("Opportunity score", "opportunity_score")
        add_metric_row("Beds / 100k", "beds_per_100k")
        add_metric_row("Market 12m EUR/cap", "market_12m_avg_eur_per_capita")
        add_metric_row("Obesity %", "obesity_pct", lower_is_better=True, suffix="%")

        score_name_to_code = self._build_score_name_to_code_map(score_df, boundaries_path)
        selected_code = score_name_to_code.get(selected_ccaa, "")

        background_map_markup = '<div class="ccaa-map-fallback">Mapa no disponible</div>'
        if map_html_path.exists():
            base_map_html = map_html_path.read_text(encoding="utf-8")
            snapshot_map_html = self._build_snapshot_map_html(
                base_map_html=base_map_html,
                selected_ccaa=selected_ccaa,
                selected_code=selected_code,
                palette=palette,
            )
            snapshot_map_srcdoc = html_lib.escape(snapshot_map_html, quote=True)
            background_map_markup = (
                f'<iframe srcdoc="{snapshot_map_srcdoc}" '
                'title="Mapa CCAA" loading="lazy" aria-label="Mapa de Espana con CCAA seleccionada"></iframe>'
            )

        ccaa_options_html = "".join(
            (
                f'<option value="{html_lib.escape(name, quote=True)}"'
                + (" selected" if name == selected_ccaa else "")
                + f'>{html_lib.escape(name)}</option>'
            )
            for name in ccaa_options
        )

        detail_html = f"""
<style>
html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
}}
.ccaa-detail-top-btn {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-decoration: none !important;
    color: {palette['surface_text']} !important;
    background: {palette['surface_bg']};
    border: 1px solid {palette['surface_border']};
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 0.86rem;
    font-weight: 700;
}}
.ccaa-detail-stage {{
    position: relative;
    width: 100%;
    height: 100%;
    border: 1px solid {palette['card_border']};
    border-radius: 18px;
    overflow: hidden;
    color: {palette['text_color']};
    font-family: {palette['font_stack']};
    background: {palette['app_bg']};
}}
.ccaa-map-layer {{
    position: absolute;
    inset: 0;
    pointer-events: auto;
}}
.ccaa-map-layer iframe {{
    width: 100%;
    height: 100%;
    border: 0;
    pointer-events: auto;
}}
.ccaa-overlay {{
    position: absolute;
    inset: 0;
    z-index: 10;
    pointer-events: none;
}}
.ccaa-floating {{
    background: {palette['panel_bg']};
    border: 1px solid {palette['card_border']};
    border-radius: 12px;
    backdrop-filter: blur(5px);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
    pointer-events: auto;
}}
.ccaa-overlay-top {{
    position: absolute;
    top: 12px;
    left: 12px;
    right: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}}
.ccaa-controls {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px;
}}
.ccaa-select-wrap {{
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 280px;
}}
.ccaa-select-wrap label {{
    color: {palette['label_color']};
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 700;
}}
.ccaa-select-wrap select {{
    border: 1px solid {palette['surface_border']};
    background: {palette['surface_bg']};
    color: {palette['surface_text']};
    border-radius: 8px;
    font-size: 0.84rem;
    font-weight: 600;
    padding: 6px 8px;
    min-width: 210px;
}}
.ccaa-title-box {{
    padding: 8px 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}}
.ccaa-title-main {{
    font-size: 1.2rem;
    font-weight: 700;
    color: {palette['title_color']};
}}
.ccaa-badge {{
    border-radius: 999px;
    border: 1px solid {palette['accent_soft']};
    background: {palette['surface_bg']};
    padding: 5px 9px;
    color: {palette['accent']};
    font-size: 0.74rem;
    font-weight: 700;
}}
.ccaa-overlay-kpis {{
    position: absolute;
    top: 74px;
    left: 12px;
    display: grid;
    grid-template-columns: 130px 150px;
    gap: 8px;
}}
.ccaa-chip {{
    border-radius: 10px;
    padding: 8px 10px;
    min-height: 66px;
}}
.ccaa-chip .label {{
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {palette['label_color']};
}}
.ccaa-chip .value {{
    margin-top: 5px;
    font-size: 1.6rem;
    line-height: 1;
    font-weight: 800;
    color: {palette['title_color']};
}}
.ccaa-detail-grid {{
    position: absolute;
    left: 12px;
    right: 12px;
    bottom: 12px;
    display: grid;
    grid-template-columns: 1.02fr 0.9fr 1.18fr;
    gap: 10px;
}}
.ccaa-grid-spacer {{
    pointer-events: none;
}}
.ccaa-card {{
    border: 1px solid {palette['card_border']};
    border-radius: 12px;
    padding: 10px;
    min-height: 270px;
    box-sizing: border-box;
    backdrop-filter: blur(6px);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
    pointer-events: auto;
    background: {palette['panel_soft_bg']};
}}
.ccaa-card-title {{
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {palette['label_color']};
    font-weight: 700;
    margin-bottom: 8px;
}}
.ccaa-outline {{
    height: 130px;
    border: 1px solid {palette['card_border']};
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 10px;
    background: {palette['panel_bg']};
}}
.ccaa-outline iframe {{
    width: 100%;
    height: 100%;
    border: 0;
}}
.ccaa-map-fallback {{
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: {palette['muted_text']};
    font-size: 0.9rem;
}}
.ccaa-score-box {{
    border: 1px solid {palette['accent_soft']};
    background: {palette['surface_bg']};
    color: {palette['surface_text']};
    border-radius: 10px;
    padding: 10px;
    font-weight: 700;
}}
.ccaa-kpi-list {{
    margin-top: 10px;
    display: grid;
    grid-template-columns: 1fr;
    gap: 6px;
}}
.ccaa-kpi-item {{
    display: flex;
    justify-content: space-between;
    font-size: 0.86rem;
    border-bottom: 1px dashed {palette['card_border']};
    padding-bottom: 4px;
}}
.ccaa-chart-wrap {{
    height: 190px;
    display: flex;
    align-items: flex-end;
    gap: 8px;
    border: 1px solid {palette['card_border']};
    border-radius: 10px;
    padding: 10px 8px;
    background: linear-gradient(180deg, {palette['panel_bg']} 0%, {palette['panel_soft_bg']} 100%);
}}
.ccaa-bar-wrap {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    gap: 6px;
    height: 100%;
}}
.ccaa-bar {{
    width: 100%;
    max-width: 36px;
    border-radius: 6px 6px 3px 3px;
    border: 1px solid {palette['accent_soft']};
    background: linear-gradient(180deg, {palette['accent']}66 0%, {palette['accent']} 100%);
    min-height: 8px;
}}
.ccaa-bar-label {{
    font-size: 0.72rem;
    color: {palette['label_color']};
    font-weight: 700;
}}
.ccaa-chart-empty {{
    width: 100%;
    text-align: center;
    color: {palette['muted_text']};
    font-size: 0.9rem;
}}
.ccaa-actions {{
    margin-top: 12px;
}}
.ccaa-target-btn {{
    width: 100%;
    display: inline-flex;
    justify-content: center;
    text-decoration: none !important;
    color: {palette['surface_text']} !important;
    background: {palette['surface_bg']};
    border: 1px solid {palette['surface_border']};
    border-radius: 10px;
    padding: 9px 10px;
    font-size: 0.86rem;
    font-weight: 700;
}}
.ccaa-compare-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
}}
.ccaa-compare-table th,
.ccaa-compare-table td {{
    border: 1px solid {palette['card_border']};
    padding: 7px 8px;
    text-align: left;
    color: {palette['text_color']};
}}
.ccaa-compare-table th {{
    background: {palette['surface_bg']};
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: {palette['label_color']};
}}
.status {{
    text-align: center !important;
    font-weight: 800;
}}
.status.good {{
    color: #16a34a;
}}
.status.bad {{
    color: #dc2626;
}}
.status.neutral {{
    color: {palette['muted_text']};
}}
@media (max-width: 1200px) {{
    .ccaa-overlay-top {{
        flex-direction: column;
        align-items: stretch;
    }}
    .ccaa-controls {{
        justify-content: space-between;
    }}
    .ccaa-select-wrap {{
        min-width: 0;
        flex: 1;
    }}
    .ccaa-select-wrap select {{
        min-width: 0;
        width: 100%;
    }}
    .ccaa-overlay-kpis {{
        position: static;
        grid-template-columns: 1fr 1fr;
        margin: 128px 12px 0 12px;
    }}
    .ccaa-detail-grid {{
        position: static;
        margin: 10px 12px 12px 12px;
        grid-template-columns: 1fr;
    }}
}}
</style>

<div class="ccaa-detail-stage">
    <div class="ccaa-map-layer">
        {background_map_markup}
    </div>

    <div class="ccaa-overlay">
        <div class="ccaa-overlay-top">
            <div class="ccaa-controls ccaa-floating">
                <a href="{html_lib.escape(overview_href, quote=True)}" target="_top" class="ccaa-detail-top-btn">Volver al mapa</a>
                <div class="ccaa-select-wrap">
                    <label for="ccaa_detail_select">CCAA</label>
                    <select id="ccaa_detail_select" data-base-href="{html_lib.escape(detail_base_href, quote=True)}">
                        {ccaa_options_html}
                    </select>
                </div>
            </div>
            <div class="ccaa-title-box ccaa-floating">
                <div class="ccaa-title-main">Comunidad {html_lib.escape(selected_ccaa)}</div>
                <div class="ccaa-badge">KPI ES vs KPI CV</div>
            </div>
        </div>

        <div class="ccaa-overlay-kpis">
            <div class="ccaa-chip ccaa-floating">
                <div class="label">CCAA</div>
                <div class="value">19</div>
            </div>
            <div class="ccaa-chip ccaa-floating">
                <div class="label">Hosp CV</div>
                <div class="value">{self._fmt(selected_row.get('hospitals_total'), decimals=0)}</div>
            </div>
        </div>

        <div class="ccaa-detail-grid">
            <div class="ccaa-grid-spacer"></div>
            <div class="ccaa-card">
                <div class="ccaa-card-title">Consumo de medicacion (EUR/cap)</div>
                <div class="ccaa-chart-wrap">
                    {bars_html}
                </div>
                <div class="ccaa-actions">
                    <a href="{html_lib.escape(market_href, quote=True)}" target="_top" class="ccaa-target-btn">Go To Targetlist</a>
                </div>
            </div>

            <div class="ccaa-card">
                <div class="ccaa-card-title">Variables: {html_lib.escape(selected_ccaa)} vs Comunidad Valenciana</div>
                <table class="ccaa-compare-table">
                    <thead>
                        <tr>
                            <th>Variable</th>
                            <th>{html_lib.escape(selected_ccaa)}</th>
                            <th>C. Valenciana</th>
                            <th>Target</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(metric_rows)}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
(function() {{
    const selector = document.getElementById("ccaa_detail_select");
    if (!selector) return;

    const buildDetailUrl = (baseHref, ccaaName) => {{
        const cleanBase = String(baseHref || "?view=ccaa_detail").replace(/&amp;/g, "&");
        const query = cleanBase.startsWith("?") ? cleanBase.slice(1) : cleanBase;
        const params = new URLSearchParams(query);
        params.set("ccaa", ccaaName);
        return `?${{params.toString()}}`;
    }};

    const navigateTop = (url) => {{
        try {{
            if (window.top) {{
                window.top.location.href = url;
                return;
            }}
        }} catch (error) {{
            // Ignore and try opening a new tab as a safe fallback.
        }}

        try {{
            window.open(url, "_blank", "noopener,noreferrer");
            return;
        }} catch (error) {{
            // Ignore and stop; do not navigate inside the embedded iframe.
        }}
    }};

    selector.addEventListener("change", () => {{
        const baseHref = selector.dataset.baseHref || "?view=ccaa_detail";
        const url = buildDetailUrl(baseHref, selector.value);
        navigateTop(url);
    }});
}})();
</script>
"""

        components.html(detail_html, height=760, scrolling=False)
