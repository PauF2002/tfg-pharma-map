from __future__ import annotations

import base64
from datetime import date
import html as html_lib
import mimetypes
from pathlib import Path
import unicodedata

import streamlit as st

from ..opportunity_pack import build_opportunity_pack_excel, prepare_opportunity_pack_data


class OpportunityPackView:
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

    @staticmethod
    def _parse_values(raw_value: object, separator: str = ",") -> list[str]:
        if raw_value is None:
            return []
        if isinstance(raw_value, list):
            chunks = [str(item) for item in raw_value]
        else:
            chunks = [str(raw_value)]

        values: list[str] = []
        for chunk in chunks:
            values.extend([part.strip() for part in chunk.split(separator) if part.strip()])

        # Preserve order and remove duplicates.
        return list(dict.fromkeys(values))

    def render(self) -> None:
        project_root = Path(__file__).resolve().parents[3]

        qp_ccaa = st.query_params.get("ccaa")
        qp_disease = st.query_params.get("disease")
        qp_snapshot = st.query_params.get("snapshot_date")
        qp_ids = st.query_params.get("hospital_ids")
        qp_names = st.query_params.get("hospital_names")

        if isinstance(qp_ccaa, list):
            qp_ccaa = qp_ccaa[0]
        if isinstance(qp_disease, list):
            qp_disease = qp_disease[0]
        if isinstance(qp_snapshot, list):
            qp_snapshot = qp_snapshot[0]

        selected_ccaa = str(qp_ccaa or "Comunidad Valenciana")
        selected_disease = str(qp_disease or "Obesity")
        snapshot_date = str(qp_snapshot or date.today().isoformat())
        hospital_ids = self._parse_values(qp_ids, separator=",")
        hospital_names = self._parse_values(qp_names, separator="||")

        flags_dir = project_root / "app" / "assets" / "fotos"
        fallback_flag_url = "https://upload.wikimedia.org/wikipedia/commons/9/9a/Flag_of_Spain.svg"
        ccaa_flag_by_norm = self._build_local_flag_map(flags_dir)
        selected_flag_url = ccaa_flag_by_norm.get(self._norm_text(selected_ccaa), fallback_flag_url)

        payload = prepare_opportunity_pack_data(
            project_root=project_root,
            ccaa=selected_ccaa,
            disease=selected_disease,
            hospital_ids=hospital_ids,
            hospital_names=hospital_names,
            snapshot_date=snapshot_date,
        )

        excel_bytes = build_opportunity_pack_excel(payload)

        st.markdown(
            """
<style>
.st-key-tl_header_card,
.st-key-tl_kpi_card,
.st-key-tl_therapeutic_card,
.st-key-tl_hospital_card,
.st-key-tl_charts_card,
.st-key-tl_export_card {
    background: var(--ui-card-bg, #ffffff) !important;
    border: 1px solid var(--ui-card-border, #e5e7eb) !important;
    border-radius: 18px !important;
    padding: 14px 16px !important;
    margin-bottom: -7px !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.06) !important;
}
.st-key-tl_header_card {
    margin-top: -7px !important;
}
.st-key-tl_header_card h3,
.st-key-tl_kpi_card h4,
.st-key-tl_therapeutic_card h4,
.st-key-tl_hospital_card h4,
.st-key-tl_charts_card h4 {
    margin-top: 0 !important;
}
.st-key-tl_kpi_card {
    padding-bottom: 24px !important;
}
.st-key-tl_therapeutic_card {
    margin-top: -7px !important;
    padding-top: 10px !important;
    padding-bottom: 24px !important;
}
.st-key-tl_hospital_card {
    margin-top: -102px !important;
    padding-top: 10px !important;
}
.tl-context-line {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    color: var(--ui-text, #4b5563);
    font-size: 0.9rem;
    margin-top: -25px !important;
}
.tl-ccaa-flag {
    width: 24px;
    height: 16px;
    border-radiu: 3px;
    border: 1px solid var(--ui-card-border, #d1d5db);
    object-fit: cover;
    vertical-align: middle;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    transform-origin: center center;
}
.tl-ccaa-flag:hover {
    transform: scale(2);
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.18);
    position: relative;
    z-index: 10;
}
.st-key-tl_top_row [data-testid="stHorizontalBlock"] {
    gap: 0.3rem !important;
}
.st-key-tl_top_row {
    margin-top: -7px !important;
}
.formula-container {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
    font-size: 0.78rem;
    margin-top: -13px;
    padding: 6px 10px;
    background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
    border-radius: 8px;
    border-left: 3px solid #3b82f6;
}
.formula-component {
    display: inline-flex;
    align-items: center;
    padding: 3px 6px;
    background: white;
    border-radius: 6px;
    border: 1px solid #e5e7eb;
    font-weight: 500;
    cursor: help;
    position: relative;
    transition: all 0.2s;
}
.formula-component:hover {
    background: #f0f4ff;
    border-color: #3b82f6;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
}
.formula-operator {
    font-weight: 700;
    color: #3b82f6;
    padding: 0 4px;
}
.formula-result {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    background: #3b82f6;
    border-radius: 6px;
    border: 2px solid #3b82f6;
    font-weight: 600;
    color: white;
    margin-left: 28px;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}
.formula-tooltip {
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: #1f2937;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.75rem;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s;
    z-index: 1000;
    margin-bottom: 5px;
    font-weight: normal;
}
.formula-component:hover .formula-tooltip {
    opacity: 1;
    pointer-events: auto;
}
.formula-tooltip::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 4px solid transparent;
    border-top-color: #1f2937;
}
.st-key-tl_kpi_card [data-testid="stMetricContainer"] {
    transform: scale(0.5s5);
    transform-origin: left center;
}
.tl-pie-wrap {
    display: grid;
    grid-template-columns: 180px 1fr;
    gap: 16px;
    align-items: center;
    margin-top: 12px;
    padding: 14px 10px 18px;
    border-top: 1px solid var(--ui-card-border, #e5e7eb);
    min-height: 280px;
}
.tl-pie-chart {
    position: relative;
    width: 180px;
    height: 180px;
    border-radius: 50%;
    border: 1px solid rgba(15, 23, 42, 0.08);
    box-shadow:
        0 14px 30px rgba(15, 23, 42, 0.12),
        inset 0 0 0 10px rgba(255, 255, 255, 0.55);
}
.tl-pie-chart::after {
    content: '';
    position: absolute;
    inset: 26px;
    border-radius: 50%;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.18);
}
.tl-pie-center {
    position: absolute;
    inset: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    z-index: 1;
    pointer-events: none;
}
.tl-pie-center span {
    display: block;
    font-size: 0.72rem;
    color: #475569;
    line-height: 1.15;
    font-weight: 600;
}
.tl-pie-legend {
    display: flex;
    flex-direction: column;
    gap: 10px;
    font-size: 0.9rem;
    color: var(--ui-text, #334155);
}
.tl-pie-legend-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border-radius: 12px;
    background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(248,250,252,0.96) 100%);
    border: 1px solid rgba(148, 163, 184, 0.18);
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
}
.tl-pie-swatch {
    width: 14px;
    height: 14px;
    border-radius: 999px;
    flex: 0 0 auto;
    box-shadow: 0 0 0 3px rgba(255,255,255,0.9);
}
.tl-pie-title {
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 4px;
}
.tl-pie-subtitle {
    font-size: 0.8rem;
    color: #64748b;
    margin-bottom: 2px;
}
.tl-pie-legend-item strong {
    color: #0f172a;
}
</style>
            """,
            unsafe_allow_html=True,
        )

        header_left, _ = st.columns([1.15, 1.13], gap="small")
        with header_left:
            header_card = st.container(key="tl_header_card")
            with header_card:
                st.markdown("### Target List")
                st.markdown(
                    f'<div class="tl-context-line">'
                    f'<span>CCAA:</span><img class="tl-ccaa-flag" src="{html_lib.escape(selected_flag_url, quote=True)}" alt="Bandera CCAA" />'
                    f'<span>| Disease: {html_lib.escape(selected_disease)} | Fecha: {html_lib.escape(snapshot_date)}</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )

        top_row = st.container(key="tl_top_row")
        with top_row:
            top_left, top_right = st.columns([1, 1], gap="small")

            with top_left:
                kpi_card = st.container(key="tl_kpi_card")
                with kpi_card:
                    st.markdown("#### KPIs")
                    kpi_1, kpi_2, kpi_3, kpi_4, kpi_5 = st.columns(5)
                    kpi_1.metric("Target hospitals", int(payload.kpis["target_hospitals"]))
                    kpi_2.metric("Total beds", f"{int(payload.kpis['total_beds']):,}".replace(",", "."))
                    kpi_3.metric("Avg score", f"{float(payload.kpis['avg_score']):.2f}")
                    kpi_4.metric("Max score", f"{float(payload.kpis['max_score']):.2f}")
                    kpi_5.metric("Market potential", f"{float(payload.kpis['market_potential']):,.0f} EUR".replace(",", "."))

                    st.markdown(
                        '''
                        <div class="formula-container">
                            <span class="formula-component">
                                Opp Score CCAA
                                <div class="formula-tooltip">0-100 base del mercado</div>
                            </span>
                            <span class="formula-operator">×</span>
                            <span class="formula-component">
                                Factor Tamaño
                                <div class="formula-tooltip">≥900=1.25 | ≥600=1.15 | ≥300=1.05 | ≥100=0.95 | <100=0.85</div>
                            </span>
                            <span class="formula-operator">×</span>
                            <span class="formula-component">
                                Factor Tipo Centro
                                <div class="formula-tooltip">Público general ≈1.15 | Privado ≈0.92 | Especializado ≈1.02</div>
                            </span>
                            <span class="formula-operator">=</span>
                            <span class="formula-result">Score Final</span>
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

                therapeutic_card = st.container(key="tl_therapeutic_card")
                with therapeutic_card:
                    st.markdown("#### Therapeutic Opportunity")
                    st.markdown(payload.therapeutic_description)
                    st.dataframe(payload.therapeutic_table, use_container_width=True, hide_index=True, height=270)

            with top_right:
                hospital_card = st.container(key="tl_hospital_card")
                with hospital_card:
                    header_col, export_col = st.columns([3, 1], gap="small")
                    with header_col:
                        st.markdown("#### Hospital Target List")
                    with export_col:
                        st.download_button(
                            "📥 Excel",
                            data=excel_bytes,
                            file_name=f"target_list_{selected_ccaa.lower().replace(' ', '_')}_{snapshot_date}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary",
                            use_container_width=True,
                        )
                    if payload.target_hospitals.empty:
                        st.warning("No hay hospitales seleccionados. Se mantiene la estructura con placeholders.")
                    else:
                        display_df = payload.target_hospitals.copy()
                        display_df = display_df.rename(
                            columns={
                                "ranking": "Ranking",
                                "hospital_id": "Hospital ID",
                                "hospital": "Hospital",
                                "ccaa": "CCAA",
                                "municipio": "Municipio",
                                "provincia": "Provincia",
                                "beds": "Beds",
                                "score": "Score",
                                "tier": "Tier",
                                "inclusion_reason": "Inclusion Reason",
                                "recommended_action": "Recommended Action",
                                "dependency": "Dependency",
                                "center_class": "Center Class",
                                "size_factor": "Size Factor",
                                "center_type_factor": "Center Type Factor",
                                "market_potential_eur": "Market Potential (EUR)",
                            }
                        )
                        st.dataframe(display_df, use_container_width=True, hide_index=True, height=388)

                        def _bucket_hospital_type(value: object) -> str:
                            text = str(value or "").strip().lower()
                            if "privad" in text:
                                return "Privado"
                            if "public" in text or "públic" in text or "otros centros o establecimientos publicos" in text:
                                return "Público"
                            return "Otros"

                        type_counts = (
                            payload.target_hospitals["dependency"]
                            .fillna("")
                            .map(_bucket_hospital_type)
                            .value_counts()
                            .reindex(["Público", "Privado", "Otros"], fill_value=0)
                        )
                        total_types = int(type_counts.sum())
                        if total_types > 0:
                            type_colors = {
                                "Público": "#22c55e",
                                "Privado": "#ef4444",
                                "Otros": "#64748b",
                            }
                            pie_parts = []
                            cursor = 0.0
                            for label, count in type_counts.items():
                                if count <= 0:
                                    continue
                                next_cursor = cursor + (count / total_types) * 100
                                pie_parts.append(f"{type_colors[label]} {cursor:.2f}% {next_cursor:.2f}%")
                                cursor = next_cursor
                            pie_css = ", ".join(pie_parts) if pie_parts else "#cbd5e1 0% 100%"

                            legend_html = "".join(
                                f'<div class="tl-pie-legend-item">'
                                f'<span class="tl-pie-swatch" style="background:{type_colors[label]};"></span>'
                                f'<span>{label}: {int(count)} ({(count / total_types * 100):.0f}%)</span>'
                                f'</div>'
                                for label, count in type_counts.items()
                                if count > 0
                            )

                            st.markdown(
                                f'''
                                <div class="tl-pie-wrap">
                                    <div class="tl-pie-chart" style="background: conic-gradient({pie_css});">
                                        <div class="tl-pie-center"><span>{total_types}<br/>Hospitals</span></div>
                                    </div>
                                    <div class="tl-pie-legend">
                                        <div class="tl-pie-title">Hospital type split</div>
                                        <div class="tl-pie-subtitle">Distribución por dependencia funcional</div>
                                        {legend_html}
                                    </div>
                                </div>
                                ''',
                                unsafe_allow_html=True,
                            )
