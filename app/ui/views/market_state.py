import streamlit as st
import streamlit.components.v1 as components

from ..config import SPANISH_PHARMA_COMPANIES


class MarketStateView:
    def render(self) -> None:
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
