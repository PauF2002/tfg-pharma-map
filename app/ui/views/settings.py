import streamlit as st

from ..config import UI_ACCENT_OPTIONS, UI_FONT_OPTIONS


class SettingsView:
    def render(self) -> None:
        settings_panel = st.container(key="settings_panel")
        with settings_panel:
            st.markdown(
                '<div class="main-kicker">PharmaTFG Platform</div>'
                '<div class="main-title">Settings</div>'
                '<div class="main-text" style="margin-bottom:16px;">Personaliza el aspecto de la app: modo oscuro/claro, tipografia y acento.</div>',
                unsafe_allow_html=True,
            )

            settings_col_1, settings_col_2 = st.columns(2, gap="large")

            with settings_col_1:
                st.subheader("Apariencia")
                st.radio(
                    "Modo",
                    options=["Dark", "Light"],
                    key="ui_theme_mode",
                    horizontal=True,
                )
                st.selectbox("Tipografia", options=list(UI_FONT_OPTIONS.keys()), key="ui_font_name")

            with settings_col_2:
                st.subheader("Detalles")
                st.selectbox("Color de acento", options=list(UI_ACCENT_OPTIONS.keys()), key="ui_accent_name")
                st.slider(
                    "Tamano base de texto",
                    min_value=14,
                    max_value=20,
                    key="ui_base_font_size",
                )
                st.caption("Estos ajustes afectan al estilo visual global de PharmaTFG.")

            reset_col, _ = st.columns([1.2, 4.8])
            with reset_col:
                if st.button("Restablecer ajustes", type="secondary"):
                    st.session_state.ui_theme_mode = "Dark"
                    st.session_state.ui_font_name = "Moderna"
                    st.session_state.ui_accent_name = "Cyan"
                    st.session_state.ui_base_font_size = 16
                    st.rerun()

            st.markdown(
                f'<div class="settings-preview">'
                f'<div class="settings-preview-title">Vista previa</div>'
                f'<div class="settings-preview-text">PharmaTFG · Tipografia: {st.session_state.ui_font_name} · Acento: {st.session_state.ui_accent_name}</div>'
                f'<div class="settings-preview-sub">Este texto cambia en tiempo real con tus ajustes.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
