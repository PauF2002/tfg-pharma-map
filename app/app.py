import streamlit as st

from ui import SidebarNavigation, initialize_ui_state, render_base_styles, render_theme_styles
from ui.views import MainPageView, MarketStateView, NewsView, PlaceholderView, ProfileView, SettingsView

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
    "market_state": MarketStateView(),
    "news": NewsView(),
    "settings": SettingsView(),
    "profile": ProfileView(),
    "logout": PlaceholderView(
        title="Log Out",
        text="Here you can later add the real logout flow, session reset, or a return-to-login screen.",
    ),
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
