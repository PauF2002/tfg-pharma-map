import streamlit as st

from .config import UI_ACCENT_OPTIONS, UI_FONT_OPTIONS


def get_theme_tokens() -> dict[str, str]:
    selected_font_stack = UI_FONT_OPTIONS[st.session_state.ui_font_name]
    selected_accent_color = UI_ACCENT_OPTIONS[st.session_state.ui_accent_name]
    selected_base_font_size = int(st.session_state.ui_base_font_size)

    if st.session_state.ui_theme_mode == "Dark":
        return {
            "app_bg": "#0b1220",
            "card_bg": "#111827",
            "card_border": "#1f2937",
            "title_color": "#f8fafc",
            "text_color": "#cbd5e1",
            "muted_text": "#94a3b8",
            "news_bg": "linear-gradient(180deg, #111827 0%, #0f172a 100%)",
            "news_border": "#334155",
            "market_card_bg": "#000000",
            "market_card_border": "#1f2937",
            "control_bg": "#0f172a",
            "control_border": "#334155",
            "control_text": "#e2e8f0",
            "label_color": "#cbd5e1",
            "font_stack": selected_font_stack,
            "accent_color": selected_accent_color,
            "base_font_size": str(selected_base_font_size),
        }

    return {
        "app_bg": "#f3f4f6",
        "card_bg": "#ffffff",
        "card_border": "#e5e7eb",
        "title_color": "#111827",
        "text_color": "#4b5563",
        "muted_text": "#6b7280",
        "news_bg": "linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)",
        "news_border": "#dbe3ee",
        "market_card_bg": "#ffffff",
        "market_card_border": "#d1d5db",
        "control_bg": "#ffffff",
        "control_border": "#cbd5e1",
        "control_text": "#0f172a",
        "label_color": "#334155",
        "font_stack": selected_font_stack,
        "accent_color": selected_accent_color,
        "base_font_size": str(selected_base_font_size),
    }


def get_embedded_theme_palette() -> dict[str, str]:
    tokens = get_theme_tokens()
    is_dark = st.session_state.ui_theme_mode == "Dark"

    return {
        "font_stack": tokens["font_stack"],
        "app_bg": tokens["app_bg"],
        "panel_bg": "rgba(15,23,42,0.56)" if is_dark else "rgba(255,255,255,0.56)",
        "panel_soft_bg": "rgba(15,23,42,0.82)" if is_dark else "rgba(255,255,255,0.82)",
        "card_border": tokens["card_border"],
        "title_color": tokens["title_color"],
        "text_color": tokens["text_color"],
        "muted_text": tokens["muted_text"],
        "label_color": tokens["label_color"],
        "surface_bg": tokens["control_bg"],
        "surface_border": tokens["control_border"],
        "surface_text": tokens["control_text"],
        "accent": tokens["accent_color"],
        "accent_soft": f"{tokens['accent_color']}33",
    }


def render_base_styles() -> None:
    st.markdown(
        """
<style>
:root {
    --sidebar-bg: linear-gradient(180deg, #171717 0%, #0f0f0f 100%);
}

[data-testid="stHeader"] {
    display: none;
}

.block-container {
    padding-top: 0rem;
    padding-bottom: 0rem;
    padding-left: 0.25rem;
    padding-right: 0.25rem;
    max-width: 100%;
}

html, body, [data-testid="stAppViewContainer"] {
    background: #f3f4f6;
    overflow: hidden;
}

section[data-testid="stSidebar"] {
    display: none;
}

.sidebar-title {
    color: #f8fafc;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.05;
    letter-spacing: 0.2px;
    margin: 0;
    margin-top: 12px;
    padding: 0 0 0 6px;
    text-align: center;
    width: 100%;
}

.dashboard-reactive-graph {
    margin: 10px auto 0 auto;
    width: 86%;
    height: 42px;
    border-radius: 10px;
    border: 1px solid rgba(34,197,94,0.28);
    background: linear-gradient(180deg, rgba(20,44,26,0.6) 0%, rgba(7,18,10,0.72) 100%);
    position: relative;
    overflow: hidden;
}

.dashboard-reactive-graph svg {
    width: 100%;
    height: 100%;
    display: block;
}

.dashboard-reactive-line {
    fill: none;
    stroke: #22c55e;
    stroke-width: 2.1;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 4 3;
    filter: drop-shadow(0 0 3px rgba(34,197,94,0.55));
    animation: graphPulse 2.5s ease-in-out infinite, graphFlow 2.5s linear infinite;
}

.dashboard-reactive-dot {
    opacity: 0.25;
    transform-origin: center;
}

.dashboard-reactive-dot.green {
    fill: #4ade80;
    filter: drop-shadow(0 0 3px rgba(74,222,128,0.55));
    animation: dotPulseGreen 2.5s ease-in-out infinite;
}

.dashboard-reactive-dot.red {
    fill: #ef4444;
    filter: drop-shadow(0 0 3px rgba(239,68,68,0.5));
    animation: dotPulseRed 2.5s ease-in-out infinite;
}

.dashboard-reactive-edge {
    position: absolute;
    background: rgba(34,197,94,0.18);
    box-shadow: 0 0 0 rgba(34,197,94,0);
}

.dashboard-reactive-edge.top,
.dashboard-reactive-edge.bottom {
    left: 7px;
    right: 7px;
    height: 2px;
}

.dashboard-reactive-edge.left,
.dashboard-reactive-edge.right {
    top: 7px;
    bottom: 7px;
    width: 2px;
}

.dashboard-reactive-edge.top { top: 2px; animation: edgePulse 2.5s ease-in-out infinite 0s; }
.dashboard-reactive-edge.right { right: 2px; animation: edgePulse 2.5s ease-in-out infinite 0.625s; }
.dashboard-reactive-edge.bottom { bottom: 2px; animation: edgePulse 2.5s ease-in-out infinite 1.25s; }
.dashboard-reactive-edge.left { left: 2px; animation: edgePulse 2.5s ease-in-out infinite 1.875s; }

@keyframes edgePulse {
    0%, 100% {
        background: rgba(34,197,94,0.2);
        box-shadow: 0 0 0 rgba(34,197,94,0);
    }
    50% {
        background: rgba(74,222,128,0.95);
        box-shadow: 0 0 12px rgba(74,222,128,0.9);
    }
}

@keyframes graphPulse {
    0%, 100% {
        stroke: #22c55e;
        filter: drop-shadow(0 0 3px rgba(34,197,94,0.45));
    }
    50% {
        stroke: #4ade80;
        filter: drop-shadow(0 0 8px rgba(74,222,128,0.95));
    }
}

@keyframes graphFlow {
    from {
        stroke-dashoffset: 0;
    }
    to {
        stroke-dashoffset: -42;
    }
}

@keyframes dotPulseGreen {
    0%, 100% {
        opacity: 0.2;
        transform: scale(1);
        filter: drop-shadow(0 0 2px rgba(74,222,128,0.35));
    }
    50% {
        opacity: 1;
        transform: scale(1.18);
        filter: drop-shadow(0 0 7px rgba(74,222,128,0.98));
    }
}

@keyframes dotPulseRed {
    0%, 100% {
        opacity: 0.18;
        transform: scale(1);
        filter: drop-shadow(0 0 2px rgba(239,68,68,0.25));
    }
    50% {
        opacity: 0.95;
        transform: scale(1.2);
        filter: drop-shadow(0 0 7px rgba(248,113,113,0.95));
    }
}

.st-key-sidebar_header_card {
    background: var(--sidebar-bg);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 22px;
    padding: 12px 12px 10px 12px;
    margin-top: -17px;
    margin-bottom: -16px;
    box-shadow: 0 10px 26px rgba(0,0,0,0.20);
    position: relative;
    z-index: 0;
}

.st-key-rail_header_card {
    background: var(--sidebar-bg);
    border: none;
    border-radius: 22px;
    padding: 12px 8px 10px 8px;
    margin-top: -17px;
    margin-bottom: -16px;
    position: relative;
    z-index: 10;
    min-height: 66px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.st-key-rail_header_card button[data-testid="stBaseButton-tertiary"],
.st-key-rail_header_card button[data-testid="stBaseButton-tertiary"] p,
.st-key-rail_header_card button[data-testid="stBaseButton-tertiary"] span,
.st-key-sidebar_header_card button[data-testid="stBaseButton-tertiary"],
.st-key-sidebar_header_card button[data-testid="stBaseButton-tertiary"] p,
.st-key-sidebar_header_card button[data-testid="stBaseButton-tertiary"] span {
    color: #ffffff !important;
}

.st-key-rail_header_card button[data-testid="stBaseButton-tertiary"],
.st-key-sidebar_header_card button[data-testid="stBaseButton-tertiary"] {
    background: rgba(255,255,255,0.10) !important;
    border: none !important;
    box-shadow: none !important;
    color: #ffffff !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    padding: 0 !important;
    margin: 0 !important;
    width: 22px !important;
    min-width: 22px !important;
    height: 22px !important;
    min-height: 22px !important;
    line-height: 1 !important;
    border-radius: 7px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}

.st-key-rail_header_card button[data-testid="stBaseButton-tertiary"]:hover,
.st-key-sidebar_header_card button[data-testid="stBaseButton-tertiary"]:hover {
    background: rgba(255,255,255,0.18) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: none !important;
}

.st-key-sidebar_header_card button[data-testid="stBaseButton-tertiary"]:focus {
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}

.sidebar-shell {
    height: calc(100dvh - 58px - 50px);
    background: var(--sidebar-bg);
    border-radius: 26px;
    padding: 40px 14px 14px 14px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 10px 26px rgba(0,0,0,0.20);
    overflow: auto;
    position: relative;
    z-index: 2;
    resize: vertical;
    min-height: 100px;
}

.sidebar-top {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.profile-card-link {
    text-decoration: none !important;
}

.profile-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 16px 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
}

.profile-card-link:hover .profile-card {
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.18);
}

.avatar-circle {
    width: 88px;
    height: 88px;
    border-radius: 50%;
    border: 1.5px solid rgba(255,255,255,0.22);
    background: rgba(255,255,255,0.03);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.7rem;
}

.profile-name {
    color: #f1f5f9;
    font-size: 1rem;
    font-weight: 500;
    text-align: center;
}

.profile-check {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    margin-left: 6px;
    border-radius: 4px;
    background: #84cc16;
    color: #0f172a;
    font-size: 0.78rem;
    font-weight: 800;
}

.nav-group,
.bottom-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 14px;
    text-decoration: none !important;
    color: #e5e7eb !important;
    font-size: 1.02rem;
    font-weight: 500;
    padding: 14px 14px;
    border-radius: 18px;
    transition: 0.18s ease;
    background: transparent;
    border: 1px solid transparent;
}

.nav-item.dashboard-item {
    display: block;
    padding: 12px 12px 10px 12px;
}

.dashboard-nav-head {
    display: flex;
    align-items: center;
    gap: 14px;
}

.nav-item.dashboard-item .dashboard-reactive-graph {
    width: calc(100% - 6px);
    margin: 10px 3px 0 3px;
    height: 68px;
}

.nav-item:hover {
    background: rgba(255,255,255,0.05);
    color: #ffffff !important;
}

.nav-item.active {
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.08);
    color: #ffffff !important;
}

.nav-icon {
    width: 24px;
    text-align: center;
    font-size: 1.15rem;
    opacity: 0.95;
}

.nav-label {
    flex: 1;
}

.rail-shell {
    height: calc(100dvh - 66px - 50px);
    background: linear-gradient(180deg, #171717 0%, #0f0f0f 100%);
    border-radius: 22px;
    padding: 28px 8px 14px 8px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 26px rgba(0,0,0,0.20);
    overflow: hidden;
    position: relative;
    z-index: 1;
}

.rail-top {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    width: 100%;
}

.rail-logo {
    color: #f8fafc;
    font-size: 1.2rem;
    font-weight: 700;
    padding-top: 6px;
    padding-bottom: 6px;
}

.rail-avatar-link {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.22);
    color: #f1f5f9;
    background: rgba(255,255,255,0.03);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.15rem;
    text-decoration: none !important;
    transition: 0.18s ease;
}

.rail-avatar-link,
.rail-avatar-link:link,
.rail-avatar-link:visited,
.rail-avatar-link span {
    color: #f1f5f9 !important;
}

.rail-avatar-link:hover {
    background: rgba(255,255,255,0.09);
    border: 1px solid rgba(255,255,255,0.32);
}

.rail-avatar-link.active {
    background: rgba(255,255,255,0.16);
    border: 1px solid rgba(255,255,255,0.28);
}

.rail-nav,
.rail-bottom {
    display: flex;
    flex-direction: column;
    gap: 10px;
    align-items: center;
    width: 100%;
}

.rail-item {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    color: #e5e7eb;
    font-size: 1rem;
    transition: 0.18s ease;
    background: transparent;
    border: 1px solid transparent;
}

.rail-item,
.rail-item:link,
.rail-item:visited,
.rail-item span {
    color: #e5e7eb !important;
}

.rail-item:hover {
    background: rgba(255,255,255,0.05);
    color: #ffffff;
}

.rail-item.active {
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.08);
    color: #ffffff;
}

.main-wrap {
    height: calc(100dvh - 8px);
    padding: 18px 10px;
    overflow: hidden;
}

.main-card {
    height: 100%;
    background: #ffffff;
    border-radius: 28px;
    border: 1px solid #e5e7eb;
    padding: 28px 32px;
    box-shadow: 0 8px 24px rgba(15,23,42,0.06);
}

.st-key-market_state_wrap,
.st-key-market_state_wrap > div,
.st-key-market_state_wrap [data-testid="stVerticalBlock"] {
    height: calc(100dvh - 24px) !important;
    max-height: calc(100dvh - 24px) !important;
    padding: 8px 6px !important;
    overflow: hidden !important;
}

.st-key-market_state_card {
    background: #000000 !important;
    border-radius: 28px !important;
    border: none !important;
    padding: 22px 24px !important;
    box-shadow: none !important;
    height: 100% !important;
    max-height: calc(100dvh - 40px) !important;
    overflow: hidden !important;
}

.st-key-market_state_card > div,
.st-key-market_state_card [data-testid="stVerticalBlock"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}

.st-key-market_state_card [data-testid="stIFrame"],
.st-key-market_state_card iframe {
    background: #000000 !important;
    border: none !important;
}

.st-key-market_state_card [data-testid="stIFrame"] {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 0 !important;
}

.st-key-market_state_card [data-testid="stIFrame"] > div {
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
}

.st-key-profile_panel {
    background: #ffffff !important;
    border-radius: 28px !important;
    border: 1px solid #e5e7eb !important;
    padding: 28px 32px !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.06) !important;
    max-height: calc(100dvh - 24px) !important;
    overflow: auto !important;
}

.st-key-profile_panel > div,
.st-key-profile_panel [data-testid="stVerticalBlock"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

.st-key-overview_map_panel {
    background: #ffffff !important;
    border-radius: 28px !important;
    border: 1px solid #e5e7eb !important;
    padding: 10px !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.06) !important;
    height: calc(100dvh - 24px) !important;
    max-height: calc(100dvh - 24px) !important;
    overflow: hidden !important;
}

.st-key-overview_map_panel > div,
.st-key-overview_map_panel [data-testid="stVerticalBlock"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

.overview-kpi-card {
    border: 1px solid #dbe3ee;
    border-radius: 14px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    min-height: 86px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.overview-kpi-label {
    color: #334155;
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    line-height: 1;
}

.overview-kpi-value {
    color: #0f172a;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.1;
    margin-top: 4px;
}

.overview-ranking-title {
    color: #0f172a;
    font-size: 1.55rem;
    font-weight: 700;
    line-height: 1.1;
    margin-top: 2px;
    margin-bottom: 12px;
}

.st-key-overview_map_frame [data-testid="stIFrame"],
.st-key-overview_map_frame iframe {
    border: 1px solid #dbe3ee !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    background: #f8fafc !important;
}

.st-key-logout_panel {
    background: #ffffff !important;
    border-radius: 28px !important;
    border: 1px solid #e5e7eb !important;
    padding: 28px 32px !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.06) !important;
    max-height: calc(100dvh - 24px) !important;
    overflow: auto !important;
}

.st-key-logout_panel > div,
.st-key-logout_panel [data-testid="stVerticalBlock"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

.main-kicker {
    color: #6b7280;
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.market-kicker {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 6px;
    color: #ef4444;
    animation: kickerPulse 1.8s ease-in-out infinite;
}

@keyframes kickerPulse {
    0%, 100% { opacity: 1; color: #ef4444; }
    50% { opacity: 0.55; color: #f87171; }
}

.market-title {
    color: #f9fafb;
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 4px;
}

.market-subtitle {
    color: #9ca3af;
    font-size: 0.97rem;
    margin-bottom: 0;
}

.market-copy-center {
    min-height: 112px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-start;
    text-align: left;
    width: fit-content;
    margin: 0 auto;
    transform: translate(-200px, 30px);
}

.st-key-market_symbol_selector [data-testid="stWidgetLabel"] {
    color: #cbd5e1;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.st-key-market_symbol_selector [data-baseweb="select"] > div {
    background: #0b0b0b;
    border: 1px solid #334155;
    border-radius: 10px;
    min-height: 38px;
}

.st-key-market_symbol_selector [data-baseweb="select"] * {
    color: #f1f5f9 !important;
}

.st-key-market_symbol_selector,
.st-key-market_symbol_selector > div {
    background: transparent !important;
}

.main-title {
    color: #111827;
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 12px;
}

.main-text {
    color: #4b5563;
    font-size: 1rem;
    max-width: 820px;
    line-height: 1.6;
}

.placeholder-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(220px, 1fr));
    gap: 18px;
    margin-top: 28px;
}

.placeholder-box {
    border: 1px solid #e5e7eb;
    border-radius: 20px;
    background: #f9fafb;
    min-height: 165px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    font-size: 1.1rem;
    font-weight: 600;
}

.news-grid,
.mainpage-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(240px, 1fr));
    gap: 18px;
    margin-top: 26px;
}

.mainpage-card-anchor {
    text-decoration: none !important;
    color: inherit !important;
}

.news-card,
.mainpage-card {
    border: 1px solid #dbe3ee;
    border-radius: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    min-height: 170px;
    padding: 18px;
    text-decoration: none;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.mainpage-card {
    border-radius: 22px;
    padding: 22px;
    min-height: 220px;
}

.mainpage-card-kpi {
    min-height: 200px;
}

.mainpage-card-compact {
    min-height: 140px;
}

.news-card:hover {
    transform: translateY(-2px);
    border-color: #93c5fd;
    box-shadow: 0 12px 26px rgba(15, 23, 42, 0.12);
}

.news-card-kicker,
.mainpage-card-kicker {
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #0f766e;
}

.news-card-title,
.mainpage-card-title {
    color: #0f172a;
    font-size: 1.18rem;
    font-weight: 700;
    margin-top: 10px;
    margin-bottom: 10px;
}

.mainpage-card-title {
    font-size: 1.4rem;
    line-height: 1.15;
}

.news-card-text,
.mainpage-card-text {
    color: #475569;
    font-size: 0.95rem;
    line-height: 1.45;
}

.mainpage-card-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}

.mainpage-card-icon {
    width: 62px;
    height: 62px;
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.9rem;
    background: rgba(59, 130, 246, 0.08);
    border: 1px solid rgba(59, 130, 246, 0.14);
}

.mainpage-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-top: 18px;
}

.mainpage-card-tag {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 6px 10px;
    background: rgba(15, 23, 42, 0.05);
    color: #334155;
    font-size: 0.82rem;
    font-weight: 600;
}

.mainpage-video-wrap {
    margin-top: 12px;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(148,163,184,0.24);
    position: relative;
    height: 124px;
    background: #0b1220;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.mainpage-card-kpi .mainpage-video-wrap {
    margin-top: 14px;
    height: 142px;
}

.mainpage-video-wrap.empty {
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #0f172a, #1e293b);
}

.mainpage-video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transform: scale(1.0);
    transition: transform 0.35s ease, filter 0.35s ease;
    display: block;
}

.mainpage-video.object-top {
    object-position: 50% 22%;
    transform-origin: 50% 0%;
}

.mainpage-video-overlay {
    position: absolute;
    left: 10px;
    bottom: 8px;
    background: rgba(2,6,23,0.68);
    color: #e2e8f0;
    font-size: 0.74rem;
    padding: 4px 8px;
    border-radius: 999px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.mainpage-card:hover .mainpage-video-wrap {
    transform: translateY(-1px);
    box-shadow: 0 12px 28px rgba(15,23,42,0.2);
    border-color: rgba(56,189,248,0.55);
}

.mainpage-card:hover .mainpage-video {
    transform: scale(1.06);
    filter: saturate(1.08) contrast(1.04);
}

.news-card-link,
.mainpage-card-link {
    color: #2563eb;
    font-size: 0.84rem;
    font-weight: 700;
    margin-top: 12px;
}

.mainpage-card-link {
    font-size: 0.9rem;
}

.st-key-settings_panel {
    background: var(--sidebar-bg);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 24px;
    padding: 18px 20px 18px 20px;
    min-height: calc(100dvh - 120px);
}

.st-key-settings_panel [data-testid="stHeading"] {
    color: #e2e8f0;
}

.st-key-settings_panel [data-testid="stCaptionContainer"],
.st-key-settings_panel label,
.st-key-settings_panel p {
    color: #94a3b8 !important;
}

.settings-preview {
    margin-top: 16px;
    border-radius: 14px;
    padding: 14px 16px;
}

.settings-preview-title {
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.settings-preview-text {
    font-size: 1.02rem;
    line-height: 1.5;
}

.settings-preview-sub {
    font-size: 0.9rem;
    margin-top: 6px;
}

@media (max-width: 920px) {
    .news-grid,
    .mainpage-grid {
        grid-template-columns: 1fr;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_theme_styles() -> None:
    tokens = get_theme_tokens()

    st.markdown(
        f"""
<style>
:root {{
    --ui-app-bg: {tokens['app_bg']};
    --ui-card-bg: {tokens['card_bg']};
    --ui-card-border: {tokens['card_border']};
    --ui-title: {tokens['title_color']};
    --ui-text: {tokens['text_color']};
    --ui-muted: {tokens['muted_text']};
    --ui-surface: {tokens['control_bg']};
    --ui-surface-border: {tokens['control_border']};
    --ui-surface-text: {tokens['control_text']};
    --ui-label: {tokens['label_color']};
    --ui-accent: {tokens['accent_color']};
}}

html, body, [data-testid="stAppViewContainer"], .stApp {{
    background: {tokens['app_bg']} !important;
    font-family: {tokens['font_stack']} !important;
    font-size: {tokens['base_font_size']}px !important;
}}

[data-testid="stAppViewContainer"] *,
[data-testid="stAppViewContainer"] *::before,
[data-testid="stAppViewContainer"] *::after {{
    font-family: {tokens['font_stack']} !important;
}}

.main-card {{
    background: {tokens['card_bg']} !important;
    border-color: {tokens['card_border']} !important;
}}

.st-key-market_state_card {{
    background: {tokens['market_card_bg']} !important;
    border-color: {tokens['market_card_border']} !important;
}}

.market-title,
.main-title,
.news-card-title,
.mainpage-card-title {{
    color: {tokens['title_color']} !important;
}}

.main-text,
.market-subtitle,
.news-card-text,
.mainpage-card-text,
.settings-preview-text {{
    color: {tokens['text_color']} !important;
}}

.main-kicker,
.news-card-kicker,
.mainpage-card-kicker,
.mainpage-card-tag,
.settings-preview-sub {{
    color: {tokens['muted_text']} !important;
}}

.news-card-link,
.mainpage-card-link,
.st-key-settings_panel h2,
.st-key-settings_panel h3,
.settings-preview-title {{
    color: {tokens['accent_color']} !important;
}}

.nav-item.active,
.rail-item.active {{
    border-color: {tokens['accent_color']}66 !important;
    box-shadow: inset 0 0 0 1px {tokens['accent_color']}44 !important;
}}

.mainpage-card,
.news-card {{
    background: {tokens['news_bg']} !important;
    border-color: {tokens['news_border']} !important;
}}

.mainpage-card-icon {{
    border-color: {tokens['accent_color']}33 !important;
    background: {tokens['accent_color']}14 !important;
}}

.market-kicker {{
    color: #ef4444 !important;
}}

.st-key-settings_panel {{
    background: {tokens['card_bg']} !important;
    border-color: {tokens['card_border']} !important;
}}

.st-key-settings_panel [data-testid="stHeading"],
.st-key-settings_panel [data-testid="stCaptionContainer"],
.st-key-settings_panel label,
.st-key-settings_panel p,
.st-key-settings_panel span,
.st-key-settings_panel div {{
    color: {tokens['label_color']} !important;
}}

.st-key-settings_panel [data-baseweb="select"] > div,
.st-key-settings_panel [data-baseweb="slider"] > div,
.st-key-settings_panel [data-baseweb="radio"] > div {{
    background: {tokens['control_bg']} !important;
    border-color: {tokens['control_border']} !important;
}}

.st-key-settings_panel [data-baseweb="select"] *,
.st-key-settings_panel [data-baseweb="radio"] *,
.st-key-settings_panel [data-baseweb="slider"] *,
.st-key-settings_panel [data-testid="stSliderTickBarMin"],
.st-key-settings_panel [data-testid="stSliderThumbValue"] {{
    color: {tokens['control_text']} !important;
}}

.st-key-settings_panel button {{
    color: {tokens['control_text']} !important;
    border-color: {tokens['control_border']} !important;
    background: {tokens['control_bg']} !important;
}}

.settings-preview {{
    border: 1px solid {tokens['card_border']};
    background: {tokens['control_bg']};
}}
</style>
        """,
        unsafe_allow_html=True,
    )
