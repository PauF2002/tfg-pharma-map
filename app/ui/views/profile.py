import streamlit as st

from ..config import DEFAULT_PROFILE_NAME


class ProfileView:
    def render(self) -> None:
        profile_html = (
            '<div class="main-wrap">'
            '<div class="main-card">'
            '<div class="main-kicker">PharmaTFG Platform</div>'
            '<div class="main-title">Profile</div>'
            f'<div class="main-text">Panel personal de {DEFAULT_PROFILE_NAME}. Aqui puedes centralizar preferencias, accesos y resumen de actividad.</div>'
            '<div class="placeholder-grid">'
            '<div class="placeholder-box">User summary</div>'
            '<div class="placeholder-box">Preferences</div>'
            '<div class="placeholder-box">Access log</div>'
            '<div class="placeholder-box">Saved views</div>'
            '</div>'
            '</div>'
            '</div>'
        )
        st.markdown(profile_html, unsafe_allow_html=True)
