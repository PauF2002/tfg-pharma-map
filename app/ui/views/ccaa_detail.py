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
        metrics_by_ccaa: dict[str, dict[str, float | None]],
        hospital_points: list[dict[str, object]],
    ) -> str:
        selected_name_norm = cls._norm_text(selected_ccaa)

        snapshot_script = f"""
<script>
(function() {{
    const selectedCode = {json.dumps(selected_code.zfill(2) if selected_code else "")};
    const selectedNameNorm = {json.dumps(selected_name_norm)};
    const metricsByCcaaRaw = {json.dumps(metrics_by_ccaa, ensure_ascii=False)};
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

    const metricsByCcaa = Object.fromEntries(
        Object.entries(metricsByCcaaRaw).map(([k, v]) => [normalize(k), v])
    );

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

        const styleId = "ccaa-detail-hover-blockers";
        if (!document.getElementById(styleId)) {{
            const styleTag = document.createElement("style");
            styleTag.id = styleId;
            styleTag.textContent = `
                .leaflet-tooltip {{ display: none !important; }}
                .leaflet-tooltip.disease-tooltip {{ display: block !important; }}
            `;
            document.head.appendChild(styleTag);
        }}

        map.on("popupopen", (event) => {{
            const source = event && event.popup ? event.popup._source : null;
            if (source && source.feature && source.feature.properties) {{
                map.closePopup(event.popup);
            }}
        }});
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

            // Remove legacy hover handlers/tooltips coming from the base HTML map.
            if (typeof layer.off === "function") {{
                layer.off("mouseover");
                layer.off("mouseout");
                layer.off("mousemove");
            }}
            if (typeof layer.unbindTooltip === "function") layer.unbindTooltip();
            if (typeof layer.unbindPopup === "function") layer.unbindPopup();

            const ccaaLabel = props.CCAA || props.ccaa || props.name || props.noml_ccaa || props.nombre || "CCAA";
            bindDiseaseTooltip(layer, ccaaLabel);

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

        installLegacyHoverBlockers(map);

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
        boundaries_path = project_root / "data" / "raw" / "ccaa_boundaries.geojson"
        hospitals_path = project_root / "data" / "raw" / "CNH_2024_geocoded.csv"
        market_path = project_root / "data" / "processed" / "ccaa_market_monthly.csv"
        flags_dir = project_root / "app" / "assets" / "fotos"

        qp_ccaa = st.query_params.get("ccaa")
        qp_disease = st.query_params.get("disease")
        if isinstance(qp_ccaa, list):
            qp_ccaa = qp_ccaa[0]
        if isinstance(qp_disease, list):
            qp_disease = qp_disease[0]

        preferred_default = "Comunidad Valenciana"
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
        # Keep a single interactive base map for all diseases; swap only the data file
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

        if not score_path.exists() or not market_path.exists() or not map_html_path.exists():
            st.error("Faltan archivos para construir el detalle CCAA de la enfermedad seleccionada. Revisa outputs/maps y data/processed.")
            return

        score_df = pd.read_csv(score_path)
        market_df = pd.read_csv(market_path)

        ccaa_options = sorted(score_df["CCAA"].dropna().astype(str).unique().tolist())
        if not ccaa_options:
            st.warning("No hay CCAA disponibles para mostrar el detalle.")
            return
        fallback_ccaa = preferred_default if preferred_default in ccaa_options else ccaa_options[0]
        selected_qp = qp_ccaa if qp_ccaa in ccaa_options else fallback_ccaa
        selected_ccaa = selected_qp

        overview_href = build_view_href("overview_map")
        target_href = build_view_href("opportunity_pack", {"ccaa": selected_ccaa, "disease": selected_disease})
        detail_base_href = build_view_href("ccaa_detail")

        disease_selector_html = "".join(
            (
                f'<a class="ccaa-disease-pill{" active" if option == selected_disease else ""}" '
                f'href="{html_lib.escape(build_view_href("ccaa_detail", {"ccaa": selected_ccaa, "disease": option}), quote=True)}">'
                f'{html_lib.escape(option)}</a>'
            )
            for option in disease_options
        )

        st.markdown(
            f"""
            <div class="ccaa-disease-switcher">
                <div class="ccaa-disease-switcher-label">Disease</div>
                <div class="ccaa-disease-switcher-row">
                    {disease_selector_html}
                </div>
                <div class="ccaa-disease-switcher-note">Selecciona una enfermedad para recargar el detalle y el pack de oportunidad.</div>
            </div>
            <style>
            .ccaa-disease-switcher {{
                margin: 0.15rem 0 0.35rem 0;
                padding: 4px 8px;
                height: 36px;
                display: flex;
                align-items: center;
                gap: 10px;
                border: 1px solid {palette['card_border']};
                border-radius: 14px;
                background: color-mix(in srgb, {palette['panel_bg']} 82%, transparent);
                backdrop-filter: blur(4px);
                box-shadow: 0 6px 18px rgba(15,23,42,0.10);
            }}
            .ccaa-disease-switcher-label {{
                font-size: 0.62rem;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: {palette['label_color']};
                font-weight: 700;
                margin: 0;
                padding-right: 8px;
                white-space: nowrap;
            }}
            .ccaa-disease-switcher-row {{
                display: flex;
                flex-wrap: nowrap;
                gap: 8px;
                align-items: center;
            }}
            .ccaa-disease-pill {{
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
            .ccaa-disease-pill:hover {{
                transform: translateY(-1px);
                border-color: {palette['accent']};
            }}
            .ccaa-disease-pill.active {{
                background: linear-gradient(135deg, {palette['accent']} 0%, {palette['accent']}cc 100%);
                border-color: {palette['accent']};
                color: #ffffff;
            }}
            .ccaa-disease-switcher-note {{
                display: none; /* hide note to keep the switcher compact */
            }}
            a.ccaa-disease-pill, .ccaa-disease-pill {{
                text-decoration: none !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

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

        spain_monthly_reference = market_df[["year_month", "market_monthly_eur_per_capita"]].copy()
        spain_monthly_reference["market_monthly_eur_per_capita"] = pd.to_numeric(
            spain_monthly_reference["market_monthly_eur_per_capita"], errors="coerce"
        )
        spain_monthly_reference = (
            spain_monthly_reference.dropna(subset=["year_month", "market_monthly_eur_per_capita"])
            .groupby("year_month", as_index=True)["market_monthly_eur_per_capita"]
            .mean()
        )

        bars_html = ""
        chart_legend_html = ""
        chart_summary_html = ""
        if month_series.empty:
            bars_html = '<div class="ccaa-chart-empty">Sin serie mensual disponible</div>'
            chart_summary_html = (
                '<div class="ccaa-chart-summary">'
                '<div class="ccaa-summary-note">No hay datos suficientes para comparar esta CCAA con la media nacional.</div>'
                "</div>"
            )
        else:
            month_series["spain_ref"] = month_series["year_month"].map(spain_monthly_reference)
            month_values = pd.to_numeric(month_series["market_monthly_eur_per_capita"], errors="coerce")
            max_value = float(month_values.max())
            min_value = float(month_values.min())
            value_range = max_value - min_value
            peak_idx = month_series["market_monthly_eur_per_capita"].idxmax()
            peak_month = month_series.loc[peak_idx]
            selected_avg_6m = pd.to_numeric(month_series["market_monthly_eur_per_capita"], errors="coerce").mean()
            spain_avg_6m = pd.to_numeric(month_series["spain_ref"], errors="coerce").mean()
            first_value = pd.to_numeric(month_series["market_monthly_eur_per_capita"], errors="coerce").iloc[0]
            last_value = pd.to_numeric(month_series["market_monthly_eur_per_capita"], errors="coerce").iloc[-1]
            trend_pct = ((last_value - first_value) / first_value * 100.0) if pd.notna(first_value) and first_value > 0 else float("nan")
            last_mom_pct = float("nan")
            if len(month_series) >= 2:
                prev_value = pd.to_numeric(
                    pd.Series([month_series["market_monthly_eur_per_capita"].iloc[-2]]), errors="coerce"
                ).iloc[0]
                if pd.notna(prev_value) and prev_value > 0:
                    last_mom_pct = ((last_value - prev_value) / prev_value) * 100.0
            bars = []
            for _, row in month_series.iterrows():
                value = float(row["market_monthly_eur_per_capita"])
                # Spread bars across available height based on local 6-month range
                # so month-to-month differences remain visible even with close values.
                if value_range > 0:
                    normalized = (value - min_value) / value_range
                    bar_height = 22.0 + (normalized * 78.0)
                else:
                    bar_height = 60.0
                ym = str(row["year_month"])
                ym_label = ym[2:7] if len(ym) >= 7 else ym

                ref_value = pd.to_numeric(pd.Series([row.get("spain_ref")]), errors="coerce").iloc[0]
                if pd.notna(ref_value) and float(ref_value) > 0:
                    ratio = value / float(ref_value)
                    if ratio >= 1.10:
                        status_class = "high"
                        status_label = "Sobre ref"
                    elif ratio <= 0.90:
                        status_class = "low"
                        status_label = "Bajo ref"
                    else:
                        status_class = "neutral"
                        status_label = "En ref"
                    delta_text = f" ({value - float(ref_value):+.2f})"
                    tooltip_ref = f" | Ref Espana: {float(ref_value):.2f}"
                    ref_label = f"Ref {float(ref_value):.1f}"
                else:
                    status_class = "neutral"
                    status_label = "Sin ref"
                    delta_text = ""
                    tooltip_ref = ""
                    ref_label = "Ref --"

                is_peak = int(row.name) == int(peak_idx)
                peak_class = " ccaa-bar-peak" if is_peak else ""
                label_class = f"{status_class} peak" if is_peak else status_class
                bars.append(
                    '<div class="ccaa-bar-wrap">'
                    f'<div class="ccaa-bar-status {status_class}{peak_class}">{status_label}</div>'
                    f'<div class="ccaa-bar-value {label_class}">{value:.1f}</div>'
                    f'<div class="ccaa-bar {status_class}{peak_class}" style="height:{bar_height:.1f}%" title="{value:.2f} EUR/cap{tooltip_ref}{delta_text}"></div>'
                    f'<div class="ccaa-bar-ref {status_class}">{ref_label}</div>'
                    f'<div class="ccaa-bar-label {label_class}">{html_lib.escape(ym_label)}</div>'
                    "</div>"
                )
            bars_html = "".join(bars)

            chart_legend_html = (
                '<div class="ccaa-chart-legend">'
                '<span class="ccaa-legend-item"><span class="ccaa-legend-dot high"></span>Sobre ref (+10%)</span>'
                '<span class="ccaa-legend-item"><span class="ccaa-legend-dot neutral"></span>En rango (+/-10%)</span>'
                '<span class="ccaa-legend-item"><span class="ccaa-legend-dot low"></span>Bajo ref (-10%)</span>'
                '<span class="ccaa-legend-item"><span class="ccaa-legend-dot peak"></span>Mes pico (6m)</span>'
                "</div>"
            )

            if pd.notna(selected_avg_6m) and pd.notna(spain_avg_6m):
                avg_gap = float(selected_avg_6m - spain_avg_6m)
                avg_gap_text = f"{avg_gap:+.2f} EUR/cap"
                gap_class = "up" if avg_gap >= 0 else "down"
            else:
                avg_gap_text = "sin ref"
                gap_class = "flat"

            if pd.notna(trend_pct):
                trend_text = f"{trend_pct:+.1f}%"
                trend_class = "up" if trend_pct >= 0 else "down"
            else:
                trend_text = "sin base"
                trend_class = "flat"

            if pd.notna(last_mom_pct):
                mom_text = f"{last_mom_pct:+.1f}%"
                mom_class = "up" if last_mom_pct >= 0 else "down"
            else:
                mom_text = "sin base"
                mom_class = "flat"

            chart_summary_html = (
                '<div class="ccaa-chart-summary">'
                '<div class="ccaa-summary-grid">'
                f'<div class="ccaa-summary-item"><span>Media 6m {html_lib.escape(selected_ccaa)}</span><strong>{self._fmt(selected_avg_6m)} EUR/cap</strong></div>'
                f'<div class="ccaa-summary-item"><span>Media 6m Espana</span><strong>{self._fmt(spain_avg_6m)} EUR/cap</strong></div>'
                "</div>"
                '<div class="ccaa-inline-kpis">'
                f'<span class="ccaa-kpi-pill {gap_class}">Gap 6m: {avg_gap_text}</span>'
                f'<span class="ccaa-kpi-pill {trend_class}">Tendencia 6m: {trend_text}</span>'
                f'<span class="ccaa-kpi-pill {mom_class}">Ultimo mes: {mom_text}</span>'
                "</div>"
                "</div>"
            )

        selected_kpi = pd.to_numeric(pd.Series([selected_row.get("opportunity_score")]), errors="coerce").iloc[0]
        spain_kpi_avg = pd.to_numeric(score_df["opportunity_score"], errors="coerce").mean()
        kpi_delta = selected_kpi - spain_kpi_avg if pd.notna(selected_kpi) and pd.notna(spain_kpi_avg) else float("nan")
        kpi_delta_sign = "+" if pd.notna(kpi_delta) and kpi_delta >= 0 else ""
        kpi_delta_class = "good" if pd.notna(kpi_delta) and kpi_delta >= 0 else "bad"
        kpi_label_class = "good" if pd.notna(kpi_delta) and kpi_delta >= 0 else "bad"

        score_name_to_code = self._build_score_name_to_code_map(score_df, boundaries_path)
        selected_code = score_name_to_code.get(selected_ccaa, "")

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

        metrics_by_ccaa = {}
        if all(
            col in score_df.columns
            for col in ["CCAA", "opportunity_score", "beds_per_100k", "market_12m_avg_eur_per_capita"]
        ):
            metric_df = score_df[
                ["CCAA", "opportunity_score", "beds_per_100k", "market_12m_avg_eur_per_capita"]
            ].copy()
            metric_df["opportunity_score"] = pd.to_numeric(metric_df["opportunity_score"], errors="coerce")
            metric_df["beds_per_100k"] = pd.to_numeric(metric_df["beds_per_100k"], errors="coerce")
            metric_df["market_12m_avg_eur_per_capita"] = pd.to_numeric(
                metric_df["market_12m_avg_eur_per_capita"], errors="coerce"
            )
            metrics_by_ccaa = {
                str(row["CCAA"]): {
                    "kpi": float(row["opportunity_score"]) if pd.notna(row["opportunity_score"]) else None,
                    "beds": float(row["beds_per_100k"]) if pd.notna(row["beds_per_100k"]) else None,
                    "market": float(row["market_12m_avg_eur_per_capita"]) if pd.notna(row["market_12m_avg_eur_per_capita"]) else None,
                    "obesity_pct": obesity_pct_by_ccaa.get(str(row["CCAA"])),
                }
                for _, row in metric_df.iterrows()
            }

        hospital_points: list[dict[str, object]] = []
        hospital_table_rows: list[dict[str, object]] = []
        if hospitals_path.exists():
            try:
                hospitals_df = pd.read_csv(hospitals_path, low_memory=False)
            except pd.errors.ParserError:
                hospitals_df = pd.read_csv(
                    hospitals_path,
                    engine="python",
                    on_bad_lines="skip",
                )
            if "CCAA" in hospitals_df.columns:
                selected_norm = self._norm_text(selected_ccaa)
                ccaa_hospitals_df = hospitals_df[
                    hospitals_df["CCAA"].astype(str).map(self._norm_text) == selected_norm
                ].copy()

                # Build hospital list for the target list module.
                for _, row in ccaa_hospitals_df.iterrows():
                    beds_value = pd.to_numeric(pd.Series([row.get("CAMAS")]), errors="coerce").iloc[0]
                    beds = int(beds_value) if pd.notna(beds_value) else 0
                    hospital_table_rows.append(
                        {
                            "id": str(row.get("CCN") or row.get("CODCNH") or row.name),
                            "name": str(row.get("Nombre Centro", "Hospital")),
                            "beds": beds,
                            "dependency": str(row.get("Dependencia Funcional", "")),
                            "center_class": str(row.get("Clase de Centro", "")),
                            "municipio": str(row.get("Municipio", "")),
                            "provincia": str(row.get("Provincia", "")),
                            "active": str(row.get("ALTA", "")),
                        }
                    )

                hospital_table_rows = sorted(hospital_table_rows, key=lambda item: int(item.get("beds", 0)), reverse=True)

                if {"lat", "lon"}.issubset(ccaa_hospitals_df.columns):
                    ccaa_hospitals_df["lat"] = pd.to_numeric(ccaa_hospitals_df["lat"], errors="coerce")
                    ccaa_hospitals_df["lon"] = pd.to_numeric(ccaa_hospitals_df["lon"], errors="coerce")
                    map_hospitals_df = ccaa_hospitals_df.dropna(subset=["lat", "lon"])
                    for _, row in map_hospitals_df.iterrows():
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
                metrics_by_ccaa=metrics_by_ccaa,
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

        disease_options_html = "".join(
            f'<option value="{html_lib.escape(option)}"'
            + (" selected" if option == selected_disease else "")
            + f'>{html_lib.escape(option)}</option>'
            for option in disease_options
        )

        fallback_flag_url = "https://upload.wikimedia.org/wikipedia/commons/9/9a/Flag_of_Spain.svg"
        ccaa_flag_by_norm = self._build_local_flag_map(flags_dir)
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
.disease-panel {{
    position: absolute;
    top: 130px; /* moved 10px up */
    left: 12px;
    z-index: 25;
    min-width: 120px;
    max-width: 240px;
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
.disease-panel-value {{
    font-size: 0.9rem;
    font-weight: 800; /* bold disease name */
    margin: 0;
    color: {palette['title_color']};
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
    gap: 4px;
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
.ccaa-kpi-word.good {{
    color: #16a34a;
}}
.ccaa-kpi-word.bad {{
    color: #dc2626;
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
    align-items: start;
}}
.ccaa-grid-spacer {{
    pointer-events: auto;
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
}}
.ccaa-side-info {{
    width: min(100%, 360px);
    border: 1px solid {palette['card_border']};
    border-radius: 12px;
    padding: 8px 8px 5px 8px;
    box-sizing: border-box;
    backdrop-filter: blur(6px);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
    background: color-mix(in srgb, {palette['panel_soft_bg']} 88%, transparent);
    align-self: flex-start;
    height: fit-content;
}}
.ccaa-side-info-title {{
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {palette['label_color']};
    font-weight: 700;
    margin-bottom: 8px;
}}
.ccaa-side-info,
.ccaa-card-consumo {{
    margin-top: 128px;
}}
.ccaa-card {{
    border: 1px solid {palette['card_border']};
    border-radius: 12px;
    padding: 10px;
    min-height: 228px;
    height: fit-content;
    align-self: start;
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
    height: 220px;
    display: flex;
    align-items: flex-end;
    gap: 8px;
    border: 1px solid {palette['card_border']};
    border-radius: 10px;
    padding: 8px 8px 6px 8px;
    background:
        repeating-linear-gradient(
            to top,
            rgba(100, 116, 139, 0.16) 0,
            rgba(100, 116, 139, 0.16) 1px,
            transparent 1px,
            transparent 34px
        ),
        linear-gradient(
            180deg,
            color-mix(in srgb, {palette['panel_bg']} 84%, transparent) 0%,
            color-mix(in srgb, {palette['panel_soft_bg']} 84%, transparent) 100%
        );
}}
.ccaa-bar-wrap {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    gap: 4px;
    height: 100%;
}}
.ccaa-bar {{
    width: 100%;
    max-width: 28px;
    border-radius: 6px 6px 3px 3px;
    border: 1px solid {palette['accent_soft']};
    background: linear-gradient(180deg, {palette['accent']}66 0%, {palette['accent']} 100%);
    min-height: 8px;
}}
.ccaa-bar.high {{
    border-color: #d97706;
    background: linear-gradient(180deg, rgba(255, 226, 164, 0.78) 0%, rgba(217, 119, 6, 0.9) 100%);
}}
.ccaa-bar.low {{
    border-color: #0369a1;
    background: linear-gradient(180deg, rgba(186, 230, 253, 0.78) 0%, rgba(3, 105, 161, 0.9) 100%);
}}
.ccaa-bar.neutral {{
    border-color: #64748b;
    background: linear-gradient(180deg, rgba(203, 213, 225, 0.75) 0%, rgba(100, 116, 139, 0.9) 100%);
}}
.ccaa-bar.ccaa-bar-peak {{
    box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.38), 0 0 12px rgba(22, 163, 74, 0.28);
}}
.ccaa-bar-status {{
    min-height: 14px;
    font-size: 0.6rem;
    line-height: 1;
    padding: 2px 5px;
    border-radius: 999px;
    border: 1px solid {palette['card_border']};
    background: {palette['surface_bg']};
    color: {palette['label_color']};
    white-space: nowrap;
}}
.ccaa-bar-value {{
    font-size: 0.63rem;
    font-weight: 700;
    line-height: 1;
}}
.ccaa-bar-value.high {{
    color: #9a3412;
}}
.ccaa-bar-value.low {{
    color: #075985;
}}
.ccaa-bar-value.neutral {{
    color: #475569;
}}
.ccaa-bar-value.peak {{
    color: #166534;
}}
.ccaa-bar-status.high {{
    color: #7c2d12;
    border-color: #d97706;
    background: rgba(255, 247, 237, 0.92);
}}
.ccaa-bar-status.low {{
    color: #0c4a6e;
    border-color: #0369a1;
    background: rgba(239, 246, 255, 0.92);
}}
.ccaa-bar-status.neutral {{
    color: #334155;
    border-color: #64748b;
    background: rgba(241, 245, 249, 0.92);
}}
.ccaa-bar-status.ccaa-bar-peak {{
    border-color: #16a34a;
    background: rgba(240, 253, 244, 0.92);
    color: #166534;
    font-weight: 700;
}}
.ccaa-bar-label {{
    font-size: 0.72rem;
    color: {palette['label_color']};
    font-weight: 700;
}}
.ccaa-bar-ref {{
    font-size: 0.58rem;
    font-weight: 700;
    line-height: 1;
    opacity: 0.85;
}}
.ccaa-bar-ref.high {{
    color: #b45309;
}}
.ccaa-bar-ref.low {{
    color: #0369a1;
}}
.ccaa-bar-ref.neutral {{
    color: #64748b;
}}
.ccaa-bar-label.high {{
    color: #9a3412;
}}
.ccaa-bar-label.low {{
    color: #075985;
}}
.ccaa-bar-label.neutral {{
    color: #475569;
}}
.ccaa-bar-label.peak {{
    text-decoration: underline;
    text-underline-offset: 2px;
    font-weight: 800;
}}
.ccaa-chart-empty {{
    width: 100%;
    text-align: center;
    color: {palette['muted_text']};
    font-size: 0.9rem;
}}
.ccaa-chart-legend {{
    margin-top: 2px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 5px 8px;
}}
.ccaa-legend-item {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.63rem;
    color: {palette['label_color']};
    font-weight: 600;
    white-space: nowrap;
}}
.ccaa-legend-dot {{
    width: 9px;
    height: 9px;
    border-radius: 999px;
    border: 1px solid {palette['surface_border']};
    flex: 0 0 auto;
}}
.ccaa-legend-dot.high {{
    background: #d97706;
    border-color: #d97706;
}}
.ccaa-legend-dot.neutral {{
    background: #64748b;
    border-color: #64748b;
}}
.ccaa-legend-dot.low {{
    background: #0369a1;
    border-color: #0369a1;
}}
.ccaa-legend-dot.peak {{
    background: #16a34a;
    border-color: #16a34a;
}}
.ccaa-chart-summary {{
    margin-top: 4px;
    border: 1px solid {palette['card_border']};
    border-radius: 8px;
    padding: 5px 6px;
    background: color-mix(in srgb, {palette['panel_bg']} 86%, transparent);
}}
.ccaa-summary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}}
.ccaa-summary-item span {{
    display: block;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: {palette['label_color']};
    font-weight: 700;
}}
.ccaa-summary-item strong {{
    display: block;
    margin-top: 2px;
    font-size: 0.8rem;
    color: {palette['title_color']};
}}
.ccaa-summary-note {{
    margin-top: 5px;
    font-size: 0.68rem;
    color: {palette['text_color']};
    line-height: 1.35;
}}
.ccaa-inline-kpis {{
    margin-top: 4px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}}
.ccaa-kpi-pill {{
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    border: 1px solid {palette['card_border']};
    padding: 2px 7px;
    font-size: 0.62rem;
    font-weight: 700;
    line-height: 1.2;
    background: rgba(248, 250, 252, 0.8);
    color: #334155;
}}
.ccaa-kpi-pill.up {{
    border-color: #15803d;
    color: #166534;
    background: rgba(240, 253, 244, 0.9);
}}
.ccaa-kpi-pill.down {{
    border-color: #b91c1c;
    color: #991b1b;
    background: rgba(254, 242, 242, 0.9);
}}
.ccaa-kpi-pill.flat {{
    border-color: #64748b;
    color: #475569;
    background: rgba(241, 245, 249, 0.9);
}}
.ccaa-hospital-toolbar {{
    display: grid;
    grid-template-columns: 1.25fr 1fr 1fr;
    gap: 6px;
    margin-bottom: 8px;
}}
.ccaa-hospital-toolbar input,
.ccaa-hospital-toolbar select {{
    width: 100%;
    border: 1px solid {palette['surface_border']};
    border-radius: 7px;
    background: color-mix(in srgb, {palette['surface_bg']} 86%, transparent);
    color: {palette['surface_text']};
    font-size: 0.72rem;
    font-weight: 600;
    padding: 5px 6px;
}}
.ccaa-hospital-table-wrap {{
    border: 1px solid {palette['card_border']};
    border-radius: 10px;
    overflow: hidden;
}}
.ccaa-hospital-table-scroll {{
    max-height: 313px;
    overflow: auto;
}}
.ccaa-hospital-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.73rem;
}}
.ccaa-hospital-table th,
.ccaa-hospital-table td {{
    border: 1px solid {palette['card_border']};
    padding: 6px 6px;
    text-align: left;
    color: {palette['text_color']};
    vertical-align: top;
}}
.ccaa-hospital-table th {{
    position: sticky;
    top: 0;
    background: {palette['surface_bg']};
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: {palette['label_color']};
}}
.ccaa-hospital-name {{
    font-weight: 700;
    color: {palette['title_color']};
}}
.ccaa-hospital-sub {{
    margin-top: 2px;
    font-size: 0.66rem;
    color: {palette['muted_text']};
}}
.ccaa-add-btn {{
    border: 1px solid {palette['accent_soft']};
    background: color-mix(in srgb, {palette['surface_bg']} 88%, transparent);
    color: {palette['accent']};
    border-radius: 6px;
    padding: 3px 7px;
    font-size: 0.67rem;
    font-weight: 700;
    cursor: pointer;
}}
.ccaa-add-btn:hover {{
    filter: brightness(1.05);
}}
.ccaa-hospital-row.selected {{
    background: rgba(22, 163, 74, 0.07);
}}
.ccaa-hospital-row {{
    cursor: pointer;
}}
.ccaa-hospital-row.active {{
    background: rgba(59, 130, 246, 0.08);
    outline: 1px solid rgba(59, 130, 246, 0.35);
    outline-offset: -1px;
}}
.ccaa-add-btn.remove {{
    border-color: #dc2626;
    color: #dc2626;
}}
.ccaa-cart-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 5px 8px;
    border-radius: 999px;
    border: 1px solid {palette['accent_soft']};
    background: {palette['surface_bg']};
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
    margin-left: auto;
}}
.ccaa-card-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
}}
.ccaa-cart-icon-btn,
.ccaa-cart-action-btn {{
    appearance: none;
    border: 0;
    background: transparent;
    color: {palette['surface_text']};
    cursor: pointer;
    padding: 0;
    margin: 0;
}}
.ccaa-cart-icon-btn {{
    font-size: 1.05rem;
    line-height: 1;
}}
.ccaa-cart-count {{
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #16a34a;
    color: #ffffff;
    font-size: 0.72rem;
    font-weight: 800;
}}
.ccaa-cart-actions {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
}}
.ccaa-cart-action-btn {{
    width: 20px;
    height: 20px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.12);
    color: {palette['label_color']};
    font-size: 0.82rem;
    font-weight: 800;
    line-height: 1;
}}
.ccaa-cart-link-btn {{
    text-decoration: none !important;
    color: {palette['surface_text']} !important;
    background: rgba(148, 163, 184, 0.12);
    border: 1px solid {palette['surface_border']};
    border-radius: 999px;
    padding: 3px 8px;
    font-size: 0.68rem;
    font-weight: 700;
    line-height: 1.2;
}}
.ccaa-cart-action-btn:hover,
.ccaa-cart-icon-btn:hover {{
    filter: brightness(1.06);
}}
.ccaa-cart-link-btn:hover {{
    filter: brightness(1.06);
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

        <div class="disease-panel ccaa-floating">
            <div class="disease-panel-label">Disease</div>
            <div class="disease-panel-value">{html_lib.escape(selected_disease)}</div>
            <div class="disease-panel-note">Dataset activo para el detalle actual.</div>
        </div>

        <div class="ccaa-kpi-compare-strip ccaa-floating">
            <div class="ccaa-kpi-compare-title">
                <span>Comparación</span>
                <span class="ccaa-kpi-word {kpi_label_class}">KPI</span>
                <span>Oportunidad</span>
            </div>
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
                <div class="label">HOSP TOTALES</div>
                <div class="value">{self._fmt(selected_row.get('hospitals_total'), decimals=0)}</div>
            </div>
        </div>

        <div class="ccaa-detail-grid">
            <div class="ccaa-grid-spacer">
                <div class="ccaa-side-info">
                    <div class="ccaa-side-info-title">Lectura rapida consumo</div>
                    {chart_legend_html}
                    {chart_summary_html}
                </div>
            </div>
            <div class="ccaa-card ccaa-card-consumo">
                <div class="ccaa-card-title">Consumo de medicacion (EUR/cap)</div>
                <div class="ccaa-chart-wrap">
                    {bars_html}
                </div>
            </div>

            <div class="ccaa-card" id="target_list_section">
                <div class="ccaa-card-header">
                    <div class="ccaa-card-title">Target List Hospitales: {html_lib.escape(selected_ccaa)}</div>
                    <div class="ccaa-cart-badge" title="Abrir target list">
                        <a href="{html_lib.escape(target_href, quote=True)}" target="_top" class="ccaa-cart-link-btn" id="target_list_open" data-base-href="{html_lib.escape(target_href, quote=True)}">Target List</a>
                        <button class="ccaa-cart-icon-btn" id="target_cart_open" type="button" aria-label="Abrir target list">🏥</button>
                        <span class="ccaa-cart-count" id="target_cart_count">0</span>
                        <div class="ccaa-cart-actions">
                            <button class="ccaa-cart-action-btn" id="target_cart_collapse" type="button" aria-label="Quitar hospital seleccionado">-</button>
                        </div>
                    </div>
                </div>
                <div class="ccaa-hospital-toolbar">
                    <input id="hospital_search" type="text" placeholder="Buscar hospital o municipio" />
                    <select id="hospital_dependency_filter">
                        <option value="all">Dependencia: todas</option>
                    </select>
                    <select id="hospital_sort">
                        <option value="beds_desc">Camas: mayor a menor</option>
                        <option value="beds_asc">Camas: menor a mayor</option>
                        <option value="name_asc">Nombre A-Z</option>
                        <option value="dependency_asc">Dependencia</option>
                    </select>
                </div>

                <div class="ccaa-hospital-table-wrap">
                    <div class="ccaa-hospital-table-scroll">
                        <table class="ccaa-hospital-table">
                            <thead>
                                <tr>
                                    <th>Hospital</th>
                                    <th>Camas</th>
                                    <th>Dependencia</th>
                                    <th>Clase</th>
                                    <th>Accion</th>
                                </tr>
                            </thead>
                            <tbody id="hospital_table_body"></tbody>
                        </table>
                    </div>
                </div>
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
    const targetCartOpen = document.getElementById("target_cart_open");
    const targetCartCollapse = document.getElementById("target_cart_collapse");
    const targetCartCount = document.getElementById("target_cart_count");
    const targetListOpenLink = document.getElementById("target_list_open");
    const targetListSection = document.getElementById("target_list_section");
    const selectedDisease = {json.dumps(selected_disease)};
    const ccaaFlagByNorm = {json.dumps(ccaa_flag_by_norm)};
    const fallbackFlagSrc = {json.dumps(fallback_flag_url)};
    const hospitalRows = {json.dumps(hospital_table_rows, ensure_ascii=False)};
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

    const buildOpportunityPackUrl = () => {{
        const baseHref = targetListOpenLink ? targetListOpenLink.dataset.baseHref : "?view=opportunity_pack";
        const cleanBase = String(baseHref || "?view=opportunity_pack").replace(/&amp;/g, "&");
        const query = cleanBase.startsWith("?") ? cleanBase.slice(1) : cleanBase;
        const params = new URLSearchParams(query);
        params.set("ccaa", selector ? selector.value : "");
        params.set("disease", selectedDisease || "Obesity");
        params.set("snapshot_date", new Date().toISOString().slice(0, 10));

        const selectedIds = targetList
            .map((item) => String(item.id || "").trim())
            .filter((value) => value.length > 0);
        if (selectedIds.length) params.set("hospital_ids", selectedIds.join(","));
        else params.delete("hospital_ids");

        const selectedNames = targetList
            .map((item) => String(item.name || "").trim())
            .filter((value) => value.length > 0);
        if (selectedNames.length) params.set("hospital_names", selectedNames.join("||"));
        else params.delete("hospital_names");

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

    const hospitalSearch = document.getElementById("hospital_search");
    const dependencyFilter = document.getElementById("hospital_dependency_filter");
    const hospitalSort = document.getElementById("hospital_sort");
    const hospitalTableBody = document.getElementById("hospital_table_body");
    const targetList = [];
    let selectedHospitalId = "";
    let showOnlyTarget = false;

    const escapeHtml = (value) => String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");

    const toNumber = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;

    const updateDependencyOptions = () => {{
        if (!dependencyFilter) return;
        const values = Array.from(new Set(hospitalRows
            .map((item) => String(item.dependency || "").trim())
            .filter((item) => item.length > 0)))
            .sort((a, b) => a.localeCompare(b, "es", {{ sensitivity: "base" }}));

        dependencyFilter.innerHTML = '<option value="all">Dependencia: todas</option>'
            + values.map((value) => `<option value="${{escapeHtml(value)}}">${{escapeHtml(value)}}</option>`).join("");
    }};

    const syncCartCount = () => {{
        if (targetCartCount) targetCartCount.textContent = String(targetList.length);
    }};

    const isInTargetList = (hospitalId) => targetList.some((item) => String(item.id) === String(hospitalId || ""));

    const setSelectedHospital = (hospitalId) => {{
        selectedHospitalId = String(hospitalId || "");
        renderHospitalTable();
    }};

    const getSelectedTargetHospital = () => {{
        if (!selectedHospitalId) return "";
        return isInTargetList(selectedHospitalId) ? selectedHospitalId : "";
    }};

    const addToTargetList = (hospitalId) => {{
        const id = String(hospitalId || "");
        const match = hospitalRows.find((row) => String(row.id) === id);
        if (!match) return;
        const exists = targetList.some((item) => String(item.id) === id);
        if (exists) return;
        targetList.push(match);
        selectedHospitalId = id;
        syncCartCount();
        renderHospitalTable();
    }};

    const removeFromTargetList = (hospitalId) => {{
        const id = String(hospitalId || "");
        const next = targetList.filter((item) => String(item.id) !== id);
        targetList.length = 0;
        targetList.push(...next);
        if (selectedHospitalId === id) selectedHospitalId = "";
        syncCartCount();
        renderHospitalTable();
    }};

    const removeSelectedHospital = () => {{
        const id = getSelectedTargetHospital();
        if (!id) return;
        removeFromTargetList(id);
    }};

    const buildHospitalRows = () => {{
        const searchValue = normalizeCcaa(hospitalSearch ? hospitalSearch.value : "");
        const dependencyValue = dependencyFilter ? dependencyFilter.value : "all";
        const sortMode = hospitalSort ? hospitalSort.value : "beds_desc";

        let rows = hospitalRows.filter((item) => {{
            if (dependencyValue && dependencyValue !== "all" && String(item.dependency || "") !== dependencyValue) return false;
            if (!searchValue) return true;
            const haystack = normalizeCcaa(`${{item.name || ""}} ${{item.municipio || ""}} ${{item.provincia || ""}}`);
            return haystack.includes(searchValue);
        }});

        if (showOnlyTarget) {{
            rows = rows.filter((item) => isInTargetList(item.id));
        }}

        rows = rows.sort((a, b) => {{
            const aSelected = isInTargetList(a.id) ? 1 : 0;
            const bSelected = isInTargetList(b.id) ? 1 : 0;
            if (aSelected !== bSelected) return bSelected - aSelected;
            if (sortMode === "beds_asc") return toNumber(a.beds) - toNumber(b.beds);
            if (sortMode === "name_asc") return String(a.name || "").localeCompare(String(b.name || ""), "es", {{ sensitivity: "base" }});
            if (sortMode === "dependency_asc") return String(a.dependency || "").localeCompare(String(b.dependency || ""), "es", {{ sensitivity: "base" }});
            return toNumber(b.beds) - toNumber(a.beds);
        }});

        return rows.slice(0, 150);
    }};

    const renderHospitalTable = () => {{
        if (!hospitalTableBody) return;
        const rows = buildHospitalRows();
        if (!rows.length) {{
            hospitalTableBody.innerHTML = '<tr><td colspan="5">No hay hospitales para los filtros seleccionados.</td></tr>';
            return;
        }}

        hospitalTableBody.innerHTML = rows.map((item) => {{
            const selected = isInTargetList(item.id);
            const isActive = String(item.id) === String(selectedHospitalId || "");
            const rowClass = ["ccaa-hospital-row", selected ? "selected" : "", isActive ? "active" : ""].filter(Boolean).join(" ");
            const btnClass = selected ? "ccaa-add-btn remove" : "ccaa-add-btn";
            const btnLabel = selected ? "Quitar" : "Anadir";
            return `<tr class="${{rowClass}}" data-hospital-id="${{escapeHtml(item.id)}}">
                <td>
                    <div class="ccaa-hospital-name">${{escapeHtml(item.name)}}</div>
                    <div class="ccaa-hospital-sub">${{escapeHtml(item.municipio)}} · ${{escapeHtml(item.provincia)}}</div>
                </td>
                <td>${{toNumber(item.beds)}}</td>
                <td>${{escapeHtml(item.dependency)}}</td>
                <td>${{escapeHtml(item.center_class)}}</td>
                <td><button class="${{btnClass}}" data-hospital-id="${{escapeHtml(item.id)}}">${{btnLabel}}</button></td>
            </tr>`;
        }}).join("");

        hospitalTableBody.querySelectorAll("tr[data-hospital-id]").forEach((row) => {{
            row.addEventListener("click", (event) => {{
                const target = event.target;
                if (target && target.closest && target.closest("button")) return;
                setSelectedHospital(row.dataset.hospitalId || "");
            }});
        }});

        hospitalTableBody.querySelectorAll(".ccaa-add-btn").forEach((button) => {{
            button.addEventListener("click", () => {{
                const id = button.dataset.hospitalId;
                if (button.classList.contains("remove")) removeFromTargetList(id);
                else addToTargetList(id);
            }});
        }});
    }};

    updateDependencyOptions();
    renderHospitalTable();
    syncCartCount();

    if (targetCartOpen) targetCartOpen.addEventListener("click", () => {{
        if (targetListSection && typeof targetListSection.scrollIntoView === "function") {{
            targetListSection.scrollIntoView({{ behavior: "smooth", block: "start" }});
        }}
    }});
    if (targetListOpenLink) {{
        targetListOpenLink.addEventListener("click", (event) => {{
            event.preventDefault();
            navigateTop(buildOpportunityPackUrl());
        }});
    }}
    if (targetCartCollapse) {{
        targetCartCollapse.addEventListener("click", () => {{
            removeSelectedHospital();
        }});
    }}

    [hospitalSearch, dependencyFilter, hospitalSort].forEach((node) => {{
        if (!node) return;
        node.addEventListener("input", renderHospitalTable);
        node.addEventListener("change", renderHospitalTable);
    }});

    setCompareCompact(false);
}})();
</script>
"""

        components.html(detail_html, height=760, scrolling=False)
