import streamlit as st

from ui import SidebarNavigation, initialize_ui_state, render_base_styles, render_theme_styles
from ui.views import LogoutView, MainPageView, MarketStateView, NewsView, OverviewMapView, ProfileView, SettingsView

st.set_page_config(
    page_title="PharmaTFG",
    layout="wide",
    initial_sidebar_state="collapsed",
)

app_state = initialize_ui_state()
render_base_styles()
render_theme_styles()

views = {
    "main_page": MainPageView(),
    "overview_map": OverviewMapView(),
    "market_state": MarketStateView(),
    "news": NewsView(),
    "settings": SettingsView(),
    "profile": ProfileView(),
    "logout": LogoutView(),
}

sidebar_navigation = SidebarNavigation(app_state.current_view)

if app_state.sidebar_open:
    left, right = st.columns([1.18, 4.82], gap="small")
else:
    left, right = st.columns([0.28, 5.72], gap="small")

with left:
    sidebar_navigation.render(app_state.sidebar_open)

with right:
    views[app_state.current_view].render()
