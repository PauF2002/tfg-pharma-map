import streamlit as st

from .config import DEFAULT_PROFILE_NAME
from .state import build_view_href, toggle_sidebar


class SidebarNavigation:
    def __init__(self, current_view: str):
        self.current_view = current_view

    def nav_item(self, label: str, icon: str, view_key: str) -> str:
        active_class = "active" if view_key == self.current_view else ""
        href = build_view_href(view_key)
        if view_key == "market_state":
            return (
                f'<a href="{href}" target="_self" class="nav-item dashboard-item {active_class}">'
                '<div class="dashboard-nav-head">'
                f'<span class="nav-icon">{icon}</span>'
                f'<span class="nav-label">{label}</span>'
                '</div>'
                '<div class="dashboard-reactive-graph">'
                '<span class="dashboard-reactive-edge top"></span>'
                '<span class="dashboard-reactive-edge right"></span>'
                '<span class="dashboard-reactive-edge bottom"></span>'
                '<span class="dashboard-reactive-edge left"></span>'
                '<svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">'
                '<polyline class="dashboard-reactive-line" points="4,27 15,19 28,24 40,14 54,21 68,10 82,16 96,8"></polyline>'
                '<circle class="dashboard-reactive-dot green" cx="8" cy="24" r="1.15" style="animation-delay:0.0s"></circle>'
                '<circle class="dashboard-reactive-dot red" cx="20" cy="21" r="1.05" style="animation-delay:0.22s"></circle>'
                '<circle class="dashboard-reactive-dot green" cx="31" cy="22" r="1.2" style="animation-delay:0.45s"></circle>'
                '<circle class="dashboard-reactive-dot red" cx="43" cy="16" r="1.1" style="animation-delay:0.7s"></circle>'
                '<circle class="dashboard-reactive-dot green" cx="57" cy="19" r="1.25" style="animation-delay:0.95s"></circle>'
                '<circle class="dashboard-reactive-dot red" cx="72" cy="12" r="1.15" style="animation-delay:1.2s"></circle>'
                '<circle class="dashboard-reactive-dot green" cx="86" cy="14" r="1.2" style="animation-delay:1.45s"></circle>'
                '<circle class="dashboard-reactive-dot red" cx="94" cy="9" r="1.05" style="animation-delay:1.7s"></circle>'
                '</svg>'
                '</div>'
                '</a>'
            )
        return (
            f'<a href="{href}" target="_self" class="nav-item {active_class}">'
            f'<span class="nav-icon">{icon}</span>'
            f'<span class="nav-label">{label}</span>'
            '</a>'
        )

    def rail_item(self, icon: str, view_key: str) -> str:
        active_class = "active" if view_key == self.current_view else ""
        href = build_view_href(view_key)
        return (
            f'<a href="{href}" target="_self" class="rail-item {active_class}">'
            f'<span>{icon}</span>'
            '</a>'
        )

    def _open_sidebar_html(self) -> str:
        profile_href = build_view_href("profile")
        return (
            '<div class="sidebar-shell">'
            '<div class="sidebar-top">'
            f'<a href="{profile_href}" target="_self" class="profile-card-link">'
            '<div class="profile-card">'
            '<div class="avatar-circle">👤</div>'
            f'<div class="profile-name">{DEFAULT_PROFILE_NAME} <span class="profile-check">✓</span></div>'
            '</div>'
            '</a>'
            '<div class="nav-group">'
            f'{self.nav_item("Main Page", "⌂", "main_page")}'
            f'{self.nav_item("Market State", "▦", "market_state")}'
            f'{self.nav_item("News", "📰", "news")}'
            f'{self.nav_item("Settings", "⚙", "settings")}'
            '</div>'
            '</div>'
            '<div class="bottom-group">'
            f'{self.nav_item("Log Out", "⇠", "logout")}'
            '</div>'
            '</div>'
        )

    def _closed_rail_html(self) -> str:
        return (
            '<div class="rail-shell">'
            '<div class="rail-top">'
            '<div class="rail-logo">P</div>'
            '<div class="rail-avatar">👤</div>'
            '<div class="rail-nav">'
            f'{self.rail_item("⌂", "main_page")}'
            f'{self.rail_item("▦", "market_state")}'
            f'{self.rail_item("📰", "news")}'
            f'{self.rail_item("⚙", "settings")}'
            '</div>'
            '</div>'
            '<div class="rail-bottom">'
            f'{self.rail_item("⇠", "logout")}'
            '</div>'
            '</div>'
        )

    def render(self, sidebar_open: bool) -> None:
        if sidebar_open:
            header_card = st.container(key="sidebar_header_card")
            with header_card:
                head_l, head_c, head_r = st.columns([1, 6, 1], gap="small")
                with head_l:
                    st.markdown("", unsafe_allow_html=True)
                with head_c:
                    st.markdown('<div class="sidebar-title">PharmaTFG</div>', unsafe_allow_html=True)
                with head_r:
                    st.markdown('<div class="toggle-inline">', unsafe_allow_html=True)
                    if st.button("◧", key="toggle_sidebar_open_btn", type="tertiary"):
                        toggle_sidebar()
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(self._open_sidebar_html(), unsafe_allow_html=True)
        else:
            rail_header = st.container(key="rail_header_card")
            with rail_header:
                if st.button("◨", key="toggle_sidebar_closed_btn", type="tertiary"):
                    toggle_sidebar()
            st.markdown(self._closed_rail_html(), unsafe_allow_html=True)
