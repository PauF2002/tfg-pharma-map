import streamlit as st

from ..user_data import log_user_activity


class LogoutView:
    def render(self) -> None:
        logout_panel = st.container(key="logout_panel")
        with logout_panel:
            st.markdown(
                '<div class="main-kicker">Plataforma PharmaTFG</div>'
                '<div class="main-title">Cerrar sesión</div>'
                '<div class="main-text">Cierra la sesión local de esta aplicación. Se reiniciarán las preferencias en memoria y volverás a la pantalla principal.</div>',
                unsafe_allow_html=True,
            )

            st.markdown("---")
            st.warning("Esta acción cierra la sesión local del navegador actual.")

            left_btn, right_btn = st.columns(2)
            with left_btn:
                confirm_logout = st.button("Cerrar sesión", type="primary", use_container_width=True)
            with right_btn:
                cancel_logout = st.button("Cancelar", type="secondary", use_container_width=True)

            if cancel_logout:
                st.query_params["view"] = "main_page"
                st.rerun()

            if confirm_logout:
                user_id = st.session_state.get("current_user_id")
                if user_id:
                    log_user_activity(user_id, "Logout", "Cierre de sesión local desde la vista de logout")

                st.session_state.clear()
                st.query_params.clear()
                st.query_params["view"] = "main_page"
                st.rerun()
