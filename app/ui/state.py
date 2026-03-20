from dataclasses import dataclass

import streamlit as st

from .config import (
    DEFAULT_SELECTED_COMPANY,
    DEFAULT_TV_CHART_HEIGHT_PERCENT,
    DEFAULT_TV_EMBED_HEIGHT_PX,
    DEFAULT_PROFILE_NAME,
    DEFAULT_TV_TOP_LINE_TRIM_PX,
    DEFAULT_VIEW,
    UI_ACCENT_OPTIONS,
    UI_FONT_OPTIONS,
    VALID_VIEWS,
)
from .user_data import get_or_create_default_user, load_user_preferences


@dataclass
class AppState:
    current_view: str
    sidebar_open: bool


def initialize_ui_state() -> AppState:
    view_param = st.query_params.get("view", DEFAULT_VIEW)
    if isinstance(view_param, list):
        view_param = view_param[0]

    if view_param == "dashboard":
        view_param = DEFAULT_VIEW

    current_view = view_param if view_param in VALID_VIEWS else DEFAULT_VIEW

    if "sidebar_open" not in st.session_state:
        st.session_state.sidebar_open = True

    if "tv_top_line_trim_px" not in st.session_state:
        st.session_state.tv_top_line_trim_px = DEFAULT_TV_TOP_LINE_TRIM_PX

    if "tv_chart_height_percent" not in st.session_state:
        st.session_state.tv_chart_height_percent = DEFAULT_TV_CHART_HEIGHT_PERCENT

    if "tv_embed_height_px" not in st.session_state:
        st.session_state.tv_embed_height_px = DEFAULT_TV_EMBED_HEIGHT_PX

    if "selected_market_symbol" not in st.session_state:
        st.session_state.selected_market_symbol = DEFAULT_SELECTED_COMPANY

    if "current_user_id" not in st.session_state:
        user = get_or_create_default_user(DEFAULT_PROFILE_NAME)
        st.session_state.current_user_id = user["id"]
        st.session_state.current_user_name = user["full_name"]
        st.session_state.current_user_email = user["email"]
        st.session_state.current_user_role = user["role"]
        st.session_state.current_user_company = user["company"]

    user_preferences = load_user_preferences(st.session_state.current_user_id)

    qp_theme = st.query_params.get("theme")
    qp_font = st.query_params.get("font")
    qp_accent = st.query_params.get("accent")
    qp_size = st.query_params.get("size")

    if isinstance(qp_theme, list):
        qp_theme = qp_theme[0]
    if isinstance(qp_font, list):
        qp_font = qp_font[0]
    if isinstance(qp_accent, list):
        qp_accent = qp_accent[0]
    if isinstance(qp_size, list):
        qp_size = qp_size[0]

    if "ui_theme_mode" not in st.session_state:
        initial_theme = qp_theme if qp_theme in {"Dark", "Light"} else user_preferences["theme"]
        st.session_state.ui_theme_mode = initial_theme if initial_theme in {"Dark", "Light"} else "Dark"

    if "ui_font_name" not in st.session_state:
        initial_font = qp_font if qp_font in UI_FONT_OPTIONS else user_preferences["font"]
        st.session_state.ui_font_name = initial_font if initial_font in UI_FONT_OPTIONS else "Moderna"

    if "ui_accent_name" not in st.session_state:
        initial_accent = qp_accent if qp_accent in UI_ACCENT_OPTIONS else user_preferences["accent"]
        st.session_state.ui_accent_name = initial_accent if initial_accent in UI_ACCENT_OPTIONS else "Cyan"

    if "ui_base_font_size" not in st.session_state:
        parsed_size = int(qp_size) if str(qp_size).isdigit() else int(user_preferences["base_font_size"])
        st.session_state.ui_base_font_size = min(20, max(14, parsed_size))

    if "ui_email_notifications" not in st.session_state:
        st.session_state.ui_email_notifications = bool(user_preferences["notifications"])

    persist_theme_query_params()

    return AppState(current_view=current_view, sidebar_open=st.session_state.sidebar_open)


def persist_theme_query_params() -> None:
    st.query_params["theme"] = st.session_state.ui_theme_mode
    st.query_params["font"] = st.session_state.ui_font_name
    st.query_params["accent"] = st.session_state.ui_accent_name
    st.query_params["size"] = str(st.session_state.ui_base_font_size)


def build_view_href(view_key: str) -> str:
    return (
        f"?view={view_key}"
        f"&theme={st.session_state.ui_theme_mode}"
        f"&font={st.session_state.ui_font_name}"
        f"&accent={st.session_state.ui_accent_name}"
        f"&size={st.session_state.ui_base_font_size}"
    )


def toggle_sidebar() -> None:
    st.session_state.sidebar_open = not st.session_state.sidebar_open
    st.rerun()
