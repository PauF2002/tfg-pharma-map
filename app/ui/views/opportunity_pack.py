from __future__ import annotations

import base64
from datetime import date
import html as html_lib
import mimetypes
from pathlib import Path
from textwrap import dedent
import unicodedata
import streamlit as st
import streamlit.components.v1 as components

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

        def _fmt_int(value: float | int) -> str:
            return f"{int(value):,}".replace(",", ".")

        def _fmt_score(value: float | int) -> str:
            return f"{float(value):.2f}"

        def _fmt_market_short(value: float | int) -> str:
            return f"€{_fmt_int(value)}"

        def _bucket_hospital_type(value: object) -> str:
            text = str(value or "").strip().lower()
            if "privad" in text:
                return "Private"
            if (
                "public" in text
                or "públic" in text
                or "servicios e institutos de salud" in text
                or "seguridad social" in text
                or "autonomica" in text
                or "autonómica" in text
            ):
                return "Public"
            return "Other"

        target_df = payload.target_hospitals.copy()
        if target_df.empty:
            st.warning("No hay hospitales seleccionados para mostrar el Opportunity Pack.")
            return

        target_hospitals = int(payload.kpis["target_hospitals"])
        total_beds = int(payload.kpis["total_beds"])
        avg_score = float(payload.kpis["avg_score"])
        max_score = float(payload.kpis["max_score"])
        market_potential = float(payload.kpis["market_potential"])
        tier_1_hospitals = int(payload.kpis.get("tier_1_hospitals", 0) or 0)

        top_hospital_name = str(target_df.sort_values("score", ascending=False).iloc[0].get("hospital", "N/A"))
        avg_vs_max = ((avg_score / max_score) * 100.0) if max_score > 0 else 0.0

        therapeutic_rows = payload.therapeutic_table.to_dict("records")
        therapeutic_table_html = "".join(
            "<tr>"
            f"<td>{html_lib.escape(str(row.get('molecule', '')))}</td>"
            f"<td>{html_lib.escape(str(row.get('therapy_line', '')))}</td>"
            f"<td>{html_lib.escape(str(row.get('potential_medication', '')))}</td>"
            f"<td>{html_lib.escape(str(row.get('commercial_note', '')))}</td>"
            "</tr>"
            for row in therapeutic_rows
        )

        hospital_rows = target_df.to_dict("records")
        hospital_table_html = "".join(
            "<tr>"
            f"<td>{int(row.get('ranking', 0))}</td>"
            f"<td>{html_lib.escape(str(row.get('hospital', '')))}</td>"
            f"<td class='op-city-cell'>{html_lib.escape(str(row.get('municipio', '')))}</td>"
            f"<td>{_fmt_int(row.get('beds', 0))}</td>"
            f"<td><span class='op-tier-badge {html_lib.escape(str(row.get('tier', 'tier 4')).lower().replace(' ', '-'))}'>{html_lib.escape(str(row.get('tier', 'Tier 4')))}</span></td>"
            f"<td><strong>{float(row.get('score', 0.0)):.1f}</strong></td>"
            f"<td>{'Priority visit' if str(row.get('tier', '')).strip() == 'Tier 1' else 'Extend outreach'}</td>"
            "</tr>"
            for row in hospital_rows
        )

        top_scores = target_df.sort_values("score", ascending=False).head(3).to_dict("records")
        top_score_max = max((float(row.get("score", 0.0)) for row in top_scores), default=1.0)
        top_score_bars_html = "".join(
            "<div class='op-bar-row'>"
            f"<div class='op-bar-label'>{html_lib.escape(str(row.get('hospital', '')))}</div>"
            "<div class='op-bar-track'>"
            f"<div class='op-bar-fill' style='width:{(float(row.get('score', 0.0)) / top_score_max) * 100:.1f}%;'></div>"
            "</div>"
            f"<div class='op-bar-value'>{float(row.get('score', 0.0)):.1f}</div>"
            "</div>"
            for row in top_scores
        )

        type_counts = (
            target_df["dependency"]
            .fillna("")
            .map(_bucket_hospital_type)
            .value_counts()
            .reindex(["Public", "Private", "Other"], fill_value=0)
        )
        type_max = max(int(type_counts.max()), 1)
        type_bars_html = "".join(
            "<div class='op-mini-bar-row'>"
            f"<div class='op-mini-label op-mini-label-{html_lib.escape(label.lower())}'>{html_lib.escape(label)}</div>"
            "<div class='op-mini-track'>"
            f"<div class='op-mini-fill op-mini-fill-{html_lib.escape(label.lower())}' style='width:{(int(count) / type_max) * 100:.1f}%;'></div>"
            "</div>"
            f"<div class='op-mini-value'>{int(count)}</div>"
            "</div>"
            for label, count in type_counts.items()
            if int(count) > 0
        )

        province_counts = target_df["provincia"].fillna("").astype(str).str.strip()
        province_counts = province_counts[province_counts.str.len() > 0].value_counts().head(3)
        province_max = max(int(province_counts.max()) if not province_counts.empty else 1, 1)
        province_bars_html = "".join(
            "<div class='op-mini-bar-row'>"
            f"<div class='op-mini-label'>{html_lib.escape(str(province))}</div>"
            "<div class='op-mini-track'>"
            f"<div class='op-mini-fill province' style='width:{(int(count) / province_max) * 100:.1f}%;'></div>"
            "</div>"
            f"<div class='op-mini-value'>{int(count)}</div>"
            "</div>"
            for province, count in province_counts.items()
        )

        st.markdown(
            """
<style>
[data-testid="stAppViewContainer"] {
    overflow: hidden !important;
}
[data-testid="stAppViewContainer"] .main {
    overflow: hidden !important;
}
[data-testid="stAppViewContainer"] .block-container {
    padding-bottom: 0 !important;
}
.op-shell {
    background: linear-gradient(180deg, #f3f5f8 0%, #eef1f5 100%);
    border: 1px solid #dde2ea;
    border-radius: 20px;
    padding: 16px;
}
.op-card {
    background: #ffffff;
    border: 1px solid #e5e9f0;
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.07);
    padding: 14px 16px;
}
.st-key-op_header_card {
    background: #ffffff !important;
    border: 1px solid #e5e9f0 !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.07) !important;
    padding: 10px 14px !important;
    margin-top: -31px !important;
    margin-bottom: -22px !important;
}
.st-key-op_header_card [data-testid="stHorizontalBlock"] {
    align-items: center;
}
.op-header-title {
    font-size: 1.65rem;
    font-weight: 700;
    color: #1f2937;
    margin: 0;
    line-height: 1;
}
.op-header-meta {
    margin-top: 4px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    font-size: 0.95rem;
    color: #4b5563;
}
.op-flag {
    width: 21px;
    height: 14px;
    object-fit: cover;
    border-radius: 3px;
    border: 1px solid #d3d8e0;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    transform-origin: center center;
    display: inline-block;
}
.op-flag:hover {
    transform: scale(1.9);
    box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
}
.op-export-meta {
    margin-top: 4px;
    text-align: right;
    color: #6b7280;
    font-size: 0.82rem;
    font-weight: 600;
}
.stDownloadButton button {
    width: 100%;
    margin-top: 4px;
    border-radius: 10px !important;
    border: 0 !important;
    background: linear-gradient(90deg, #1f9d7a 0%, #2aa66f 100%) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}
.op-grid-kpi {
    margin-top: 12px;
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(5, minmax(0, 1fr));
}
.op-kpi-title {
    font-size: 1.1rem;
    color: #374151;
    font-weight: 700;
    display: inline-flex;
.op-table-scroll {
    overflow-y: auto;
    overflow-x: hidden;
    border: 1px solid #e6ebf2;
    border-radius: 10px;
}
.op-table-scroll.therapeutic {
    max-height: 210px;
}
.op-table-scroll.hospital {
    max-height: 300px;
}
    align-items: center;
    gap: 6px;
    border: 1px solid #e6ebf2;
.op-kpi-value {
    margin-top: 8px;
    font-size: 2.7rem;
    line-height: 1;
    font-weight: 700;
    color: #1f2937;
}
.op-kpi-sub {
    position: sticky;
    top: 0;
    z-index: 2;
    margin-top: 6px;
    font-size: 0.9rem;
    color: #6b7280;
}
.op-kpi-pill {
    margin-top: 6px;
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #ecf7f2;
    color: #257a60;
    font-size: 0.88rem;
    font-weight: 700;
}
.op-info {
    width: 18px;
    height: 18px;
    border-radius: 999px;
    border: 1px solid #c7d2de;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    font-weight: 700;
    color: #64748b;
    cursor: help;
    position: relative;
}
.op-info:hover::after {
    content: attr(data-tip);
    position: absolute;
    bottom: 130%;
    left: 50%;
    transform: translateX(-50%);
    width: 260px;
    max-width: 75vw;
    white-space: normal;
    background: #111827;
    color: #ffffff;
    border-radius: 10px;
    padding: 9px 10px;
    font-size: 0.78rem;
    line-height: 1.3;
    z-index: 20;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.35);
}
.op-insight {
    margin-top: 12px;
}
.op-insight-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 6px;
}
.op-insight-text {
    color: #374151;
    font-size: 1.2rem;
    line-height: 1.35;
}
.op-main-grid {
    margin-top: 12px;
    display: grid;
    gap: 10px;
    grid-template-columns: 1fr 1fr;
}
.op-card-title {
    font-size: 1.95rem;
    color: #1f2937;
    font-weight: 700;
    margin-bottom: 8px;
}
.op-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}
.op-table th,
.op-table td {
    border: 1px solid #e6ebf2;
    padding: 8px 9px;
    font-size: 0.9rem;
    color: #374151;
    text-align: left;
    vertical-align: top;
}
.op-table th {
    background: #f7f9fc;
    color: #6b7280;
    font-weight: 700;
}
.op-rationale {
    margin-bottom: 8px;
    color: #5b6472;
    font-size: 0.92rem;
}
.op-tier-badge {
    border-radius: 8px;
    padding: 3px 8px;
    font-size: 0.76rem;
    font-weight: 700;
    display: inline-block;
}
.op-tier-badge.tier-1 { background: #dcf5ea; color: #17654e; }
.op-tier-badge.tier-2 { background: #fdf1d5; color: #8a6322; }
.op-tier-badge.tier-3 { background: #eceff3; color: #5b6472; }
.op-tier-badge.tier-4 { background: #f3f4f6; color: #6b7280; }
.op-bottom-grid {
    margin-top: 10px;
    display: grid;
    gap: 10px;
    grid-template-columns: 2fr 1fr 1fr;
}
.op-bar-row {
    display: grid;
    grid-template-columns: 1.25fr 2fr 0.45fr;
    gap: 10px;
    align-items: center;
    margin-bottom: 10px;
}
.op-bar-label {
    color: #4b5563;
    font-size: 0.88rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.op-bar-track {
    background: #e9edf2;
    border-radius: 8px;
    height: 20px;
    overflow: hidden;
}
.op-bar-fill {
    height: 100%;
    border-radius: 8px;
    background: linear-gradient(90deg, #9bc7b1 0%, #5ea388 100%);
}
.op-bar-value {
    text-align: right;
    color: #1f2937;
    font-size: 1.0rem;
    font-weight: 700;
}
.op-mini-bar-row {
    display: grid;
    grid-template-columns: 0.85fr 1.2fr 0.35fr;
    gap: 8px;
    align-items: center;
    margin-bottom: 10px;
}
.op-mini-label {
    color: #4b5563;
    font-size: 0.92rem;
}
.op-mini-track {
    background: #e9edf2;
    border-radius: 7px;
    height: 16px;
    overflow: hidden;
}
.op-mini-fill {
    height: 100%;
    border-radius: 7px;
    background: linear-gradient(90deg, #8db9c2 0%, #4f8b9f 100%);
}
.op-mini-fill.province {
    background: linear-gradient(90deg, #b7d9c4 0%, #77b08e 100%);
}
.op-mini-value {
    text-align: right;
    font-size: 0.9rem;
    color: #1f2937;
    font-weight: 700;
}
@media (max-width: 1180px) {
    .op-grid-kpi { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .op-main-grid { grid-template-columns: 1fr; }
    .op-bottom-grid { grid-template-columns: 1fr; }
    .op-kpi-value { font-size: 2.2rem; }
}
</style>
            """,
            unsafe_allow_html=True,
        )

        header_card = st.container(key="op_header_card")
        with header_card:
            header_left, header_right = st.columns([4.9, 1.6], gap="small")
            with header_left:
                st.markdown(
                    f"""
                    <div class="op-header-title">Target Opportunity Pack</div>
                    <div class="op-header-meta">
                        <img class="op-flag" src="{html_lib.escape(selected_flag_url, quote=True)}" alt="CCAA flag" />
                        <span>{html_lib.escape(selected_ccaa)} | Disease: {html_lib.escape(selected_disease)} | {html_lib.escape(snapshot_date)}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with header_right:
                st.markdown(
                    f"<div class='op-export-meta'>{target_hospitals} selected hospitals</div>",
                    unsafe_allow_html=True,
                )
                st.download_button(
                    "Export Opportunity Pack",
                    data=excel_bytes,
                    file_name=f"target_list_{selected_ccaa.lower().replace(' ', '_')}_{snapshot_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                )

        avg_tip = (
            "Media de Score en hospitales seleccionados. "
            "Score = Opp Score CCAA x Factor Tamano x Factor Tipo Centro, con tope 0-100."
        )
        max_tip = (
            "Maximo Score observado en el target. "
            "Usa la misma formula por hospital con clipping 0-100."
        )
        market_tip = (
            "Suma de market_potential_eur. "
            "Por hospital: Beds x Market 12m EUR/capita CCAA x multiplicador por Tier "
            "(Tier 1=1.30, Tier 2=1.15, Tier 3=1.00, Tier 4=0.85)."
        )

        dashboard_html = dedent(
            f"""
<style>
body {{
    margin: 0;
    padding: 0;
    background: transparent;
    font-family: "Segoe UI", Tahoma, sans-serif;
}}
.op-shell {{
    background: linear-gradient(180deg, #f3f5f8 0%, #eef1f5 100%);
    border: 1px solid #dde2ea;
    border-radius: 20px;
    margin-top: 5px;
    padding: 16px;
}}
.op-card {{
    background: #ffffff;
    border: 1px solid #e5e9f0;
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.07);
    padding: 14px 16px;
}}
.op-grid-kpi {{
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(5, minmax(140px, 1fr));
}}
.op-grid-kpi .op-card {{
    padding: 6px 8px;
    min-height: 82px;
}}
.op-kpi-title {{
    font-size: 0.78rem;
    line-height: 1.05;
    color: #374151;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    min-height: 16px;
}}
.op-kpi-icon {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 13px;
    height: 13px;
    font-size: 0.8rem;
    line-height: 1;
}}
.op-kpi-icon.gold {{
    color: #eab308;
}}
.op-kpi-value {{
    margin-top: 3px;
    font-size: 1.45rem;
    line-height: 1;
    font-weight: 700;
    color: #1f2937;
}}
.op-kpi-sub {{
    margin-top: 1px;
    font-size: 0.64rem;
    color: #6b7280;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-height: 0.9rem;
}}
.op-kpi-sub.placeholder {{
    visibility: hidden;
}}
.op-kpi-pill {{
    margin-top: 1px;
    display: inline-block;
    padding: 2px 6px;
    border-radius: 999px;
    background: #ecf7f2;
    color: #257a60;
    font-size: 0.6rem;
    font-weight: 700;
}}
.op-info {{
    width: 15px;
    height: 15px;
    border-radius: 999px;
    border: 1px solid #c7d2de;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.62rem;
    font-weight: 700;
    color: #64748b;
    cursor: help;
    position: relative;
}}
.op-info:hover::after {{
    content: attr(data-tip);
    position: absolute;
    top: 130%;
    left: 50%;
    transform: translateX(-50%);
    width: 260px;
    max-width: 75vw;
    white-space: normal;
    background: #111827;
    color: #ffffff;
    border-radius: 10px;
    padding: 9px 10px;
    font-size: 0.78rem;
    line-height: 1.3;
    z-index: 20;
}}
.op-main-grid {{
    margin-top: 12px;
    display: grid;
    gap: 10px;
    grid-template-columns: 1fr 1fr;
}}
.op-card-title {{
    font-size: 1.6rem;
    color: #1f2937;
    font-weight: 700;
    margin-bottom: 8px;
}}
.op-table {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}}
.op-table-scroll {{
    overflow-y: auto;
    overflow-x: hidden;
    border: 1px solid #e6ebf2;
    border-radius: 10px;
}}
.op-table-scroll.therapeutic {{
    max-height: 215px;
}}
.op-table-scroll.hospital {{
    max-height: 263px;
}}
.op-table th,
.op-table td {{
    border: 1px solid #e6ebf2;
    padding: 7px 8px;
    font-size: 0.85rem;
    line-height: 1.2;
    color: #374151;
    text-align: left;
    vertical-align: top;
}}
.op-city-cell {{
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
    font-size: 0.8rem;
    line-height: 1.15;
}}
.op-table th {{
    position: sticky;
    top: 0;
    z-index: 2;
    background: #f7f9fc;
    color: #6b7280;
    font-weight: 700;
}}
.op-rationale {{
    margin-bottom: 8px;
    color: #5b6472;
    font-size: 0.92rem;
}}
.op-tier-badge {{
    border-radius: 8px;
    padding: 3px 8px;
    font-size: 0.76rem;
    font-weight: 700;
    display: inline-block;
}}
.op-tier-badge.tier-1 {{ background: #dcf5ea; color: #17654e; }}
.op-tier-badge.tier-2 {{ background: #fdf1d5; color: #8a6322; }}
.op-tier-badge.tier-3 {{ background: #eceff3; color: #5b6472; }}
.op-tier-badge.tier-4 {{ background: #f3f4f6; color: #6b7280; }}
.op-bottom-grid {{
    margin-top: 10px;
    display: grid;
    gap: 10px;
    grid-template-columns: 2fr 1fr 1fr;
}}
.op-bar-row {{
    display: grid;
    grid-template-columns: 1.25fr 2fr 0.45fr;
    gap: 10px;
    align-items: center;
    margin-bottom: 10px;
}}
.op-bar-label {{
    color: #4b5563;
    font-size: 0.88rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.op-bar-track {{
    background: #e9edf2;
    border-radius: 8px;
    height: 20px;
    overflow: hidden;
}}
.op-bar-fill {{
    height: 100%;
    border-radius: 8px;
    background: linear-gradient(90deg, #9bc7b1 0%, #5ea388 100%);
}}
.op-bar-value {{
    text-align: right;
    color: #1f2937;
    font-size: 1rem;
    font-weight: 700;
}}
.op-mini-bar-row {{
    display: grid;
    grid-template-columns: 0.85fr 1.2fr 0.35fr;
    gap: 8px;
    align-items: center;
    margin-bottom: 10px;
}}
.op-mini-label {{ color: #4b5563; font-size: 0.92rem; }}
.op-mini-label-public {{ color: #315f9e; font-weight: 600; }}
.op-mini-label-private {{ color: #9b3b4a; font-weight: 600; }}
.op-mini-track {{
    background: #e9edf2;
    border-radius: 7px;
    height: 16px;
    overflow: hidden;
}}
.op-mini-fill {{
    height: 100%;
    border-radius: 7px;
    background: linear-gradient(90deg, #8db9c2 0%, #4f8b9f 100%);
}}
.op-mini-fill-public {{
    background: linear-gradient(90deg, #b8d0ec 0%, #4f78ad 100%);
}}
.op-mini-fill-private {{
    background: linear-gradient(90deg, #efc1ca 0%, #b25666 100%);
}}
.op-mini-fill.province {{
    background: linear-gradient(90deg, #b7d9c4 0%, #77b08e 100%);
}}
.op-mini-value {{
    text-align: right;
    font-size: 0.9rem;
    color: #1f2937;
    font-weight: 700;
}}
</style>

<div class="op-shell">
    <div class="op-grid-kpi">
        <div class="op-card">
            <div class="op-kpi-title"><span class="op-kpi-icon">🏥</span>Target hospitals</div>
            <div class="op-kpi-value">{target_hospitals}</div>
            <div class="op-kpi-sub placeholder">alignment</div>
        </div>
        <div class="op-card">
            <div class="op-kpi-title"><span class="op-kpi-icon">🛏</span>Total beds</div>
            <div class="op-kpi-value">{_fmt_int(total_beds)}</div>
            <div class="op-kpi-sub placeholder">alignment</div>
        </div>
        <div class="op-card">
            <div class="op-kpi-title"><span class="op-kpi-icon">◎</span>Avg score <span class="op-info" data-tip="{html_lib.escape(avg_tip, quote=True)}">i</span></div>
            <div class="op-kpi-value">{_fmt_score(avg_score)}</div>
            <div class="op-kpi-sub">{avg_vs_max:.0f}% of max score</div>
        </div>
        <div class="op-card">
            <div class="op-kpi-title"><span class="op-kpi-icon gold">🏆</span>Max score <span class="op-info" data-tip="{html_lib.escape(max_tip, quote=True)}">i</span></div>
            <div class="op-kpi-value">{_fmt_score(max_score)}</div>
            <div class="op-kpi-sub">Top hospital {html_lib.escape(top_hospital_name)}</div>
        </div>
        <div class="op-card">
            <div class="op-kpi-title"><span class="op-kpi-icon">📈</span>Market potential <span class="op-info" data-tip="{html_lib.escape(market_tip, quote=True)}">i</span></div>
            <div class="op-kpi-value">{_fmt_market_short(market_potential)}</div>
            <div class="op-kpi-pill">Tier 1 ready</div>
        </div>
    </div>

    <div class="op-main-grid">
        <div class="op-card">
            <div class="op-card-title">Therapeutic Opportunity</div>
            <div class="op-rationale"><strong>Commercial rationale:</strong> {html_lib.escape(payload.therapeutic_description)}</div>
            <div class="op-table-scroll therapeutic">
                <table class="op-table">
                    <thead>
                        <tr>
                            <th>Molecule</th>
                            <th>Therapy line</th>
                            <th>Drug class</th>
                            <th>Strategic rationale</th>
                        </tr>
                    </thead>
                    <tbody>
                        {therapeutic_table_html}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="op-card">
            <div class="op-card-title">Hospital Target List</div>
            <div class="op-table-scroll hospital">
                <table class="op-table">
                    <thead>
                        <tr>
                            <th style="width:8%;">Rank</th>
                            <th style="width:29%;">Hospital</th>
                            <th style="width:16%;">City</th>
                            <th style="width:10%;">Beds</th>
                            <th style="width:12%;">Priority</th>
                            <th style="width:10%;">Opport.</th>
                            <th style="width:15%;">Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {hospital_table_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="op-bottom-grid">
        <div class="op-card">
            <div class="op-card-title">Top Hospitals by Opportunity Score</div>
            {top_score_bars_html}
        </div>
        <div class="op-card">
            <div class="op-card-title">Hospital Insights</div>
            {type_bars_html}
        </div>
        <div class="op-card">
            <div class="op-card-title">Province split</div>
            {province_bars_html}
        </div>
    </div>
</div>
            """
        )
        components.html(dashboard_html, height=930, scrolling=False)
