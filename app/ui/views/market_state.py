from pathlib import Path
import unicodedata

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ..config import SPANISH_PHARMA_COMPANIES


class MarketStateView:
    @staticmethod
    def _norm_text(value: object) -> str:
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return " ".join(text.replace("-", " ").replace("_", " ").split())

    @classmethod
    def _pick_column(cls, columns: list[str], required_tokens: list[str], excluded_tokens: list[str] | None = None) -> str | None:
        excluded_tokens = excluded_tokens or []
        for column in columns:
            norm_col = cls._norm_text(column)
            if all(token in norm_col for token in required_tokens) and not any(token in norm_col for token in excluded_tokens):
                return column
        return None

    @classmethod
    def _load_hospital_df(cls) -> pd.DataFrame:
        project_root = Path(__file__).resolve().parents[3]
        hospitals_path = project_root / "data" / "raw" / "CNH_2024_geocoded.csv"
        if not hospitals_path.exists():
            return pd.DataFrame()

        hospitals_df = pd.DataFrame()
        for encoding in ("utf-8", "latin-1"):
            try:
                hospitals_df = pd.read_csv(hospitals_path, encoding=encoding, low_memory=False)
                if not hospitals_df.empty:
                    break
            except Exception:
                continue

        if hospitals_df.empty:
            return hospitals_df

        columns = hospitals_df.columns.astype(str).tolist()
        ccaa_col = cls._pick_column(columns, ["ccaa"], ["cod"])
        name_col = cls._pick_column(columns, ["nombre", "centro"])
        camas_col = cls._pick_column(columns, ["camas"])
        dep_col = cls._pick_column(columns, ["dependencia", "funcional"])
        clase_col = cls._pick_column(columns, ["clase", "centro"])
        municipio_col = cls._pick_column(columns, ["municipio"], ["cod"])
        provincia_col = cls._pick_column(columns, ["provincia"], ["cod"])
        alta_col = cls._pick_column(columns, ["alta"])
        complejo_col = cls._pick_column(columns, ["forma", "parte", "complejo"])
        email_col = cls._pick_column(columns, ["email"])
        telefono_col = cls._pick_column(columns, ["telefono"])
        ccn_col = cls._pick_column(columns, ["ccn"])

        selected_cols = [
            ccn_col,
            name_col,
            ccaa_col,
            camas_col,
            dep_col,
            clase_col,
            municipio_col,
            provincia_col,
            alta_col,
            complejo_col,
            email_col,
            telefono_col,
        ]
        selected_cols = [col for col in selected_cols if col and col in hospitals_df.columns]
        hospitals_df = hospitals_df[selected_cols].copy()

        rename_map = {
            ccn_col: "hospital_id",
            name_col: "hospital",
            ccaa_col: "ccaa",
            camas_col: "beds",
            dep_col: "dependency",
            clase_col: "center_class",
            municipio_col: "municipio",
            provincia_col: "provincia",
            alta_col: "active",
            complejo_col: "complex_member",
            email_col: "email",
            telefono_col: "phone",
        }
        rename_map = {k: v for k, v in rename_map.items() if k is not None}
        hospitals_df = hospitals_df.rename(columns=rename_map)

        for col in ["hospital", "ccaa", "dependency", "center_class", "municipio", "provincia", "email", "phone"]:
            if col in hospitals_df.columns:
                hospitals_df[col] = hospitals_df[col].fillna("").astype(str).str.strip()

        if "beds" in hospitals_df.columns:
            hospitals_df["beds"] = pd.to_numeric(hospitals_df["beds"], errors="coerce").fillna(0)
        else:
            hospitals_df["beds"] = 0

        if "hospital_id" not in hospitals_df.columns:
            hospitals_df["hospital_id"] = hospitals_df.index.astype(str)
        else:
            hospitals_df["hospital_id"] = hospitals_df["hospital_id"].fillna("").astype(str)

        hospitals_df = hospitals_df[hospitals_df["hospital"].astype(str).str.len() > 0]
        hospitals_df = hospitals_df[hospitals_df["ccaa"].astype(str).str.len() > 0]
        return hospitals_df

    @staticmethod
    def _init_target_list_state() -> None:
        if "target_hospitals" not in st.session_state:
            st.session_state.target_hospitals = []

    @staticmethod
    def _add_hospitals_to_target(rows: list[dict[str, object]]) -> int:
        if not rows:
            return 0
        existing = {str(item.get("hospital_id", "")) for item in st.session_state.target_hospitals}
        added = 0
        for row in rows:
            row_id = str(row.get("hospital_id", ""))
            if row_id in existing:
                continue
            st.session_state.target_hospitals.append(row)
            existing.add(row_id)
            added += 1
        return added

    def render(self) -> None:
        self._init_target_list_state()

        market_wrap = st.container(key="market_state_wrap")
        with market_wrap:
            market_card = st.container(key="market_state_card")
            with market_card:
                tv_top_line_trim_px = int(st.session_state.tv_top_line_trim_px)
                tv_chart_height_percent = int(st.session_state.tv_chart_height_percent)
                tv_embed_height_px = int(st.session_state.tv_embed_height_px)
                tv_theme = "dark" if st.session_state.ui_theme_mode == "Dark" else "light"
                tv_bg_color = "#000000" if st.session_state.ui_theme_mode == "Dark" else "#ffffff"

                header_left, header_right = st.columns([3.6, 2.4], gap="medium")

                with header_right:
                    symbol_selector = st.container(key="market_symbol_selector")
                    with symbol_selector:
                        st.markdown(
                            '<div style="color:#cbd5e1;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:4px;text-align:right;">Empresa</div>',
                            unsafe_allow_html=True,
                        )
                        selected_company = st.selectbox(
                            "Empresa",
                            options=list(SPANISH_PHARMA_COMPANIES.keys()),
                            key="selected_market_symbol",
                            label_visibility="collapsed",
                        )

                selected_info = SPANISH_PHARMA_COMPANIES[selected_company]
                selected_symbol = selected_info["symbol"]
                selected_subtitle = selected_info["subtitle"]

                with header_left:
                    st.markdown(
                        '<div class="market-copy-center">'
                        '<div class="market-kicker">&#9679; Live Market Data</div>'
                        '<div class="market-title">Market State</div>'
                        f'<div class="market-subtitle">{selected_subtitle} &mdash; Bolsa de Madrid</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

            tradingview_widget = f"""
<style>
    * {{
        box-sizing: border-box;
    }}
    html, body {{
        margin: 0;
        padding: 0;
        height: 100%;
        background: {tv_bg_color} !important;
        overflow: hidden;
    }}
    .tradingview-widget-container,
    .tradingview-widget-container__widget {{
        width: 100%;
        height: {tv_chart_height_percent}%;
        background: {tv_bg_color};
        border: 0 !important;
    }}
    .tradingview-widget-container {{
        transform: translateY(-{tv_top_line_trim_px}px);
    }}
    .tradingview-widget-container iframe {{
        border: 0 !important;
        background: {tv_bg_color} !important;
        display: block;
    }}
</style>
<div class="tradingview-widget-container" style="height:{tv_chart_height_percent}%;width:100%;margin-top:0;">
    <div class="tradingview-widget-container__widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
    {{
        "autosize": true,
        "symbol": "{selected_symbol}",
        "interval": "D",
        "timezone": "Europe/Madrid",
        "theme": "{tv_theme}",
        "style": "16",
        "locale": "es",
        "allow_symbol_change": true,
        "calendar": false,
        "support_host": "https://www.tradingview.com"
    }}
    </script>
</div>
"""
            components.html(tradingview_widget, height=tv_embed_height_px, scrolling=False)

            st.markdown("### Target List Hospitales")
            hospitals_df = self._load_hospital_df()

            if hospitals_df.empty:
                st.warning("No se pudo cargar el listado de hospitales.")
                return

            qp_ccaa = st.query_params.get("ccaa")
            if isinstance(qp_ccaa, list):
                qp_ccaa = qp_ccaa[0]

            ccaa_options = sorted(hospitals_df["ccaa"].dropna().astype(str).unique().tolist())
            default_ccaa = qp_ccaa if qp_ccaa in ccaa_options else ccaa_options[0]

            filters_left, filters_mid, filters_right = st.columns([2.3, 1.3, 1.3], gap="small")
            with filters_left:
                selected_ccaa = st.selectbox("CCAA", options=ccaa_options, index=ccaa_options.index(default_ccaa))

            ccaa_df = hospitals_df[hospitals_df["ccaa"] == selected_ccaa].copy()

            dependency_options = sorted([v for v in ccaa_df["dependency"].dropna().unique().tolist() if str(v).strip()])
            class_options = sorted([v for v in ccaa_df["center_class"].dropna().unique().tolist() if str(v).strip()])

            with filters_mid:
                selected_dependencies = st.multiselect(
                    "Dependencia",
                    options=dependency_options,
                    default=[],
                    placeholder="Todas",
                )

            with filters_right:
                selected_classes = st.multiselect(
                    "Clase centro",
                    options=class_options,
                    default=[],
                    placeholder="Todas",
                )

            sort_col_left, sort_col_right = st.columns([1.6, 1.4], gap="small")
            with sort_col_left:
                sort_choice = st.selectbox(
                    "Ordenar por",
                    options=[
                        "Camas (mayor a menor)",
                        "Camas (menor a mayor)",
                        "Nombre A-Z",
                        "Dependencia",
                        "Clase centro",
                    ],
                )
            with sort_col_right:
                top_n = st.selectbox("Mostrar", options=[25, 50, 100, 200], index=1)

            if selected_dependencies:
                ccaa_df = ccaa_df[ccaa_df["dependency"].isin(selected_dependencies)]
            if selected_classes:
                ccaa_df = ccaa_df[ccaa_df["center_class"].isin(selected_classes)]

            sort_map = {
                "Camas (mayor a menor)": ("beds", False),
                "Camas (menor a mayor)": ("beds", True),
                "Nombre A-Z": ("hospital", True),
                "Dependencia": ("dependency", True),
                "Clase centro": ("center_class", True),
            }
            sort_field, ascending = sort_map[sort_choice]
            ccaa_df = ccaa_df.sort_values(sort_field, ascending=ascending).head(int(top_n)).copy()

            dependency_norm = ccaa_df["dependency"].astype(str).str.lower()
            private_count = int(dependency_norm.str.contains("privad").sum())
            public_count = int(len(ccaa_df) - private_count)

            kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
            kpi_1.metric("Hospitales", f"{len(ccaa_df):,}".replace(",", "."))
            kpi_2.metric("Camas totales", f"{int(ccaa_df['beds'].sum()):,}".replace(",", "."))
            kpi_3.metric("Promedio camas", f"{ccaa_df['beds'].mean():.1f}" if len(ccaa_df) else "0")
            kpi_4.metric("Publicos / Privados", f"{public_count} / {private_count}")

            table_df = ccaa_df[
                ["hospital_id", "hospital", "beds", "dependency", "center_class", "municipio", "provincia", "active"]
            ].copy()
            table_df = table_df.rename(
                columns={
                    "hospital_id": "ID",
                    "hospital": "Hospital",
                    "beds": "Camas",
                    "dependency": "Dependencia",
                    "center_class": "Clase",
                    "municipio": "Municipio",
                    "provincia": "Provincia",
                    "active": "Alta",
                }
            )
            table_df["Anadir"] = False

            edited_df = st.data_editor(
                table_df,
                hide_index=True,
                use_container_width=True,
                height=520,
                key=f"target_editor_{self._norm_text(selected_ccaa)}",
                column_config={
                    "Anadir": st.column_config.CheckboxColumn("Anadir", help="Marcar para agregar al target list"),
                    "Camas": st.column_config.NumberColumn("Camas", format="%d"),
                },
            )

            selected_rows = edited_df[edited_df["Anadir"] == True].copy()  # noqa: E712
            btn_left, btn_mid, btn_right = st.columns([1.2, 1.2, 3.6])
            with btn_left:
                add_clicked = st.button("Anadir seleccionados", type="primary", use_container_width=True)
            with btn_mid:
                clear_clicked = st.button("Limpiar target", use_container_width=True)

            if add_clicked:
                payload = selected_rows.to_dict("records")
                normalized_payload = [
                    {
                        "hospital_id": str(row.get("ID", "")),
                        "hospital": str(row.get("Hospital", "")),
                        "ccaa": selected_ccaa,
                        "beds": float(row.get("Camas", 0) or 0),
                        "dependency": str(row.get("Dependencia", "")),
                        "center_class": str(row.get("Clase", "")),
                        "municipio": str(row.get("Municipio", "")),
                        "provincia": str(row.get("Provincia", "")),
                        "active": str(row.get("Alta", "")),
                    }
                    for row in payload
                ]
                added = self._add_hospitals_to_target(normalized_payload)
                if added:
                    st.success(f"Se anadieron {added} hospitales al target list.")
                else:
                    st.info("No se anadio ningun hospital nuevo.")

            if clear_clicked:
                st.session_state.target_hospitals = []
                st.success("Target list limpiado.")

            st.markdown("#### Mi Target List")
            target_df = pd.DataFrame(st.session_state.target_hospitals)
            if target_df.empty:
                st.caption("Aun no hay hospitales anadidos.")
            else:
                display_cols = [
                    "hospital",
                    "ccaa",
                    "beds",
                    "dependency",
                    "center_class",
                    "municipio",
                    "provincia",
                    "active",
                ]
                target_df = target_df[display_cols].rename(
                    columns={
                        "hospital": "Hospital",
                        "ccaa": "CCAA",
                        "beds": "Camas",
                        "dependency": "Dependencia",
                        "center_class": "Clase",
                        "municipio": "Municipio",
                        "provincia": "Provincia",
                        "active": "Alta",
                    }
                )
                st.dataframe(target_df, use_container_width=True, hide_index=True, height=552)
