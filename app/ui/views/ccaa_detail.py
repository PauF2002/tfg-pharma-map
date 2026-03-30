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
        hospital_points: list[dict[str, object]],
    ) -> str:
        selected_name_norm = cls._norm_text(selected_ccaa)

        snapshot_script = f"""
<script>
(function() {{
    const selectedCode = {json.dumps(selected_code.zfill(2) if selected_code else "")};
    const selectedNameNorm = {json.dumps(selected_name_norm)};
    const hospitalPoints = {json.dumps(hospital_points)};
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

    const notifyParentLayersState = (isOpen) => {{
        try {{
            window.parent.postMessage({{ type: "ccaa-layer-control-state", open: Boolean(isOpen) }}, "*");
        }} catch (error) {{
            // Ignore cross-frame messaging issues.
        }}
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
                    color: "#7EC8FF",
                    weight: 2.2,
                    fillColor: "#A9DCFF",
                    fillOpacity: 0.42,
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

    const addHospitalMarkers = (map) => {{
        if (map._ccaaHospitalLayer) {{
            map.removeLayer(map._ccaaHospitalLayer);
        }}

        const layerGroup = L.layerGroup();
        hospitalPoints.forEach((hospital) => {{
            const lat = Number(hospital.lat);
            const lon = Number(hospital.lon);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

            const dependency = String(hospital.dependency || "");
            const isPrivate = dependency.toLowerCase().includes("privad");
            const markerColor = isPrivate ? "#ef4444" : "#22c55e";

            const marker = L.circleMarker([lat, lon], {{
                radius: 4,
                color: markerColor,
                fillColor: markerColor,
                fillOpacity: 0.9,
                weight: 1.2,
            }});

            const hospitalName = String(hospital.name || "Hospital");
            const typeLabel = isPrivate ? "Privado" : "Publico";
            marker.bindPopup(`${{hospitalName}}<br>${{typeLabel}}`);
            layerGroup.addLayer(marker);
        }});

        layerGroup.addTo(map);
        map._ccaaHospitalLayer = layerGroup;
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
        map.options.maxZoom = 13.0;
        map.options.zoomDelta = 0.5;
        map.options.zoomSnap = 0.5;

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
            map.setMaxZoom(13.0);
            return;
        }}

        map.fitBounds(spainBounds, {{
            paddingTopLeft: [12, 12],
            paddingBottomRight: [420, 12]
        }});
        map.setZoom(Math.min(map.getZoom(), 6.1));
        map.setMinZoom(5.8);
        map.setMaxZoom(13.0);
    }};

    const bridgeLayerControlState = (map) => {{
        if (!map || typeof map.getContainer !== "function") return;
        const mapContainer = map.getContainer();
        if (!mapContainer) return;

        let boundControl = null;
        let controlObserver = null;

        const bindControl = (controlEl) => {{
            if (!controlEl || controlEl === boundControl) return;
            boundControl = controlEl;

            const emitState = () => {{
                const isExpanded = boundControl.classList.contains("leaflet-control-layers-expanded");
                notifyParentLayersState(isExpanded);
            }};

            ["click", "mouseenter", "mouseleave", "focusin", "focusout", "keyup"].forEach((eventName) => {{
                boundControl.addEventListener(eventName, () => setTimeout(emitState, 0));
            }});

            if (controlObserver) controlObserver.disconnect();
            controlObserver = new MutationObserver(() => emitState());
            controlObserver.observe(boundControl, {{ attributes: true, attributeFilter: ["class", "style"] }});

            emitState();
        }};

        const refreshControlBinding = () => {{
            const controlEl = mapContainer.querySelector(".leaflet-control-layers");
            if (!controlEl) {{
                notifyParentLayersState(false);
                return;
            }}
            bindControl(controlEl);
        }};

        const mapObserver = new MutationObserver(() => refreshControlBinding());
        mapObserver.observe(mapContainer, {{ childList: true, subtree: true }});

        refreshControlBinding();
    }};

    const init = () => {{
        const map = getMapInstance();
        if (!map) return;

        const result = styleLayers(map);
        configureStaticMap(map, result.bounds, result.ccaaName);
        addHospitalMarkers(map);
        bridgeLayerControlState(map);
        map.on("layeradd", (event) => {{
            const layer = event && event.layer;
            // Ignore transient non-CCAA layers (tooltips/popups/controls) to avoid zoom resets.
            if (!layer || !layer.feature || !layer.feature.properties) return;

            setTimeout(() => {{
                styleLayers(map);
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
        hospitals_path = project_root / "data" / "raw" / "CNH_2024_geocoded.csv"
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

        selected_kpi = pd.to_numeric(pd.Series([selected_row.get("opportunity_score")]), errors="coerce").iloc[0]
        spain_kpi_avg = pd.to_numeric(score_df["opportunity_score"], errors="coerce").mean()
        kpi_delta = selected_kpi - spain_kpi_avg if pd.notna(selected_kpi) and pd.notna(spain_kpi_avg) else float("nan")
        kpi_delta_sign = "+" if pd.notna(kpi_delta) and kpi_delta >= 0 else ""
        kpi_delta_class = "good" if pd.notna(kpi_delta) and kpi_delta >= 0 else "bad"

        score_name_to_code = self._build_score_name_to_code_map(score_df, boundaries_path)
        selected_code = score_name_to_code.get(selected_ccaa, "")

        hospital_points: list[dict[str, object]] = []
        if hospitals_path.exists():
            try:
                hospitals_df = pd.read_csv(hospitals_path, low_memory=False)
            except pd.errors.ParserError:
                hospitals_df = pd.read_csv(
                    hospitals_path,
                    engine="python",
                    on_bad_lines="skip",
                )
            if {"CCAA", "lat", "lon"}.issubset(hospitals_df.columns):
                hospitals_df["lat"] = pd.to_numeric(hospitals_df["lat"], errors="coerce")
                hospitals_df["lon"] = pd.to_numeric(hospitals_df["lon"], errors="coerce")
                hospitals_df = hospitals_df.dropna(subset=["CCAA", "lat", "lon"])

                selected_norm = self._norm_text(selected_ccaa)
                hospitals_df = hospitals_df[
                    hospitals_df["CCAA"].astype(str).map(self._norm_text) == selected_norm
                ]

                for _, row in hospitals_df.iterrows():
                    hospital_points.append(
                        {
                            "lat": float(row["lat"]),
                            "lon": float(row["lon"]),
                            "name": str(row.get("Nombre Centro", "Hospital")),
                            "dependency": str(row.get("Dependencia Funcional", "")),
                        }
                    )

        background_map_markup = '<div class="ccaa-map-fallback">Mapa no disponible</div>'
        if map_html_path.exists():
            base_map_html = map_html_path.read_text(encoding="utf-8")
            snapshot_map_html = self._build_snapshot_map_html(
                base_map_html=base_map_html,
                selected_ccaa=selected_ccaa,
                selected_code=selected_code,
                palette=palette,
                hospital_points=hospital_points,
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
        selected_flag_url = ccaa_flag_by_norm.get(self._norm_text(selected_ccaa), fallback_flag_url)

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
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 0.73rem;
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
    top: 77px;
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
    gap: 8px;
    padding: 7px;
}}
.ccaa-select-wrap {{
    display: flex;
    align-items: center;
    gap: 7px;
    min-width: 238px;
}}
.ccaa-select-wrap label {{
    color: {palette['label_color']};
    font-size: 0.64rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 700;
}}
.ccaa-flag {{
    width: 24px;
    height: 16px;
    object-fit: cover;
    border-radius: 3px;
    border: 1px solid {palette['surface_border']};
    flex: 0 0 auto;
    transition: transform 160ms ease;
    transform-origin: center;
}}
.ccaa-flag-btn {{
    border: 0;
    padding: 0;
    margin: 0;
    background: transparent;
    cursor: pointer;
    line-height: 0;
}}
.ccaa-flag-btn:hover .ccaa-flag,
.ccaa-flag-btn:focus-visible .ccaa-flag {{
    transform: scale(2);
}}
.ccaa-select-wrap select {{
    border: 1px solid {palette['surface_border']};
    background: {palette['surface_bg']};
    color: {palette['surface_text']};
    border-radius: 7px;
    font-size: 0.71rem;
    font-weight: 600;
    padding: 5px 7px;
    min-width: 178px;
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
    top: 12px;
    left: 12px;
    display: grid;
    grid-template-columns: 98px 112px;
    gap: 5px;
}}
.ccaa-chip {{
    border-radius: 9px;
    padding: 5px 7px;
    min-height: 46px;
}}
.ccaa-chip .label {{
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {palette['label_color']};
}}
.ccaa-chip .value {{
    margin-top: 3px;
    font-size: 1.08rem;
    line-height: 1;
    font-weight: 800;
    color: {palette['title_color']};
}}
.ccaa-kpi-compare-strip {{
    position: absolute;
    top: 42px;
    right: 65px;
    min-width: 360px;
    padding: 8px 12px;
    z-index: 15;
    transition: transform 180ms ease;
}}
.ccaa-kpi-compare-strip.layers-open {{
    transform: translateX(-85px);
}}
.ccaa-kpi-compare-title {{
    display: inline-flex;
    align-items: center;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: {palette['accent']};
    font-weight: 800;
    margin-bottom: 7px;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid {palette['accent_soft']};
    background: {palette['surface_bg']};
}}
.ccaa-kpi-compare-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr auto;
    gap: 8px;
    align-items: end;
}}
.ccaa-kpi-compare-item .label {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.63rem;
    color: {palette['label_color']};
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
.ccaa-kpi-flag-mini {{
    width: 14px;
    height: 10px;
    object-fit: cover;
    border-radius: 2px;
    border: 1px solid {palette['surface_border']};
    flex: 0 0 auto;
}}
.ccaa-kpi-compare-item .value {{
    margin-top: 2px;
    font-size: 1rem;
    font-weight: 800;
    color: {palette['title_color']};
    line-height: 1;
}}
.ccaa-kpi-delta {{
    font-size: 0.9rem;
    font-weight: 800;
    padding: 3px 7px;
    border-radius: 999px;
    border: 1px solid {palette['card_border']};
    background: {palette['surface_bg']};
}}
.ccaa-kpi-delta.good {{
    color: #16a34a;
}}
.ccaa-kpi-delta.bad {{
    color: #dc2626;
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
    .ccaa-kpi-compare-strip {{
        position: static;
        transform: none;
        min-width: 0;
        margin: 12px 12px 0 12px;
    }}
    .ccaa-kpi-compare-strip.layers-open {{
        transform: none;
    }}
    .ccaa-kpi-compare-grid {{
        grid-template-columns: 1fr 1fr;
    }}
    .ccaa-kpi-delta {{
        grid-column: 1 / -1;
        justify-self: start;
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
                <a
                    href="{html_lib.escape(overview_href, quote=True)}"
                    target="_top"
                    class="ccaa-detail-top-btn"
                    id="ccaa_overview_btn"
                    data-overview-href="{html_lib.escape(overview_href, quote=True)}"
                >Volver</a>
                <div class="ccaa-select-wrap">
                    <label for="ccaa_detail_select">CCAA</label>
                    <button
                        type="button"
                        class="ccaa-flag-btn"
                        aria-label="Bandera CCAA"
                    >
                        <img
                            id="ccaa_flag_img"
                            class="ccaa-flag"
                            src="{html_lib.escape(selected_flag_url, quote=True)}"
                            alt="Bandera CCAA"
                            data-fallback-src="{html_lib.escape(fallback_flag_url, quote=True)}"
                        />
                    </button>
                    <select id="ccaa_detail_select" data-base-href="{html_lib.escape(detail_base_href, quote=True)}">
                        {ccaa_options_html}
                    </select>
                </div>
            </div>
        </div>

        <div class="ccaa-kpi-compare-strip ccaa-floating">
            <div class="ccaa-kpi-compare-title">Comparacion KPI oportunidad</div>
            <div class="ccaa-kpi-compare-grid">
                <div class="ccaa-kpi-compare-item">
                    <div class="label">
                        <img
                            class="ccaa-kpi-flag-mini"
                            src="{html_lib.escape(selected_flag_url, quote=True)}"
                            alt="Bandera {html_lib.escape(selected_ccaa)}"
                            loading="lazy"
                            onerror="this.onerror=null;this.src='{html_lib.escape(fallback_flag_url, quote=True)}';"
                        />
                        {html_lib.escape(selected_ccaa)}
                    </div>
                    <div class="value">{self._fmt(selected_kpi)}</div>
                </div>
                <div class="ccaa-kpi-compare-item">
                    <div class="label">
                        <img
                            class="ccaa-kpi-flag-mini"
                            src="{html_lib.escape(fallback_flag_url, quote=True)}"
                            alt="Bandera Espana"
                            loading="lazy"
                        />
                        Media Espana
                    </div>
                    <div class="value">{self._fmt(spain_kpi_avg)}</div>
                </div>
                <div class="ccaa-kpi-delta {kpi_delta_class}">{kpi_delta_sign}{self._fmt(kpi_delta)}</div>
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
    const overviewBtn = document.getElementById("ccaa_overview_btn");
    const flagImg = document.getElementById("ccaa_flag_img");
    const compareStrip = document.querySelector(".ccaa-kpi-compare-strip");
    const ccaaFlagByNorm = {json.dumps(ccaa_flag_by_norm)};
    const fallbackFlagSrc = {json.dumps(fallback_flag_url)};
    if (!selector) return;

    const setCompareCompact = (isCompact) => {{
        if (!compareStrip) return;
        compareStrip.classList.toggle("layers-open", Boolean(isCompact));
    }};

    const onLayerControlMessage = (event) => {{
        const data = event && event.data;
        if (!data || data.type !== "ccaa-layer-control-state") return;
        setCompareCompact(Boolean(data.open));
    }};

    window.addEventListener("message", onLayerControlMessage);

    const normalizeCcaa = (value) => String(value || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/-/g, " ")
        .replace(/\s+/g, " ")
        .trim();

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
        if (flagImg) {{
            flagImg.src = ccaaFlagByNorm[normalizeCcaa(selector.value)] || fallbackFlagSrc;
        }}
        const baseHref = selector.dataset.baseHref || "?view=ccaa_detail";
        const url = buildDetailUrl(baseHref, selector.value);
        navigateTop(url);
    }});

    if (flagImg) {{
        flagImg.addEventListener("error", () => {{
            if (flagImg.src !== fallbackFlagSrc) flagImg.src = fallbackFlagSrc;
        }});
    }}


    if (overviewBtn) {{
        overviewBtn.addEventListener("click", (event) => {{
            event.preventDefault();
            const overviewHref = overviewBtn.dataset.overviewHref || "?view=overview_map";
            navigateTop(overviewHref);
        }});
    }}

    setCompareCompact(false);
}})();
</script>
"""

        components.html(detail_html, height=760, scrolling=False)
