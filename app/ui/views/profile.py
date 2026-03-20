import streamlit as st
import pandas as pd

from ..user_data import get_recent_activity, log_user_activity, save_user_preferences, save_user_profile


class ProfileView:
    def render(self) -> None:
        user_id = st.session_state.current_user_id
        current_name = st.session_state.get("current_user_name", "")
        current_email = st.session_state.get("current_user_email", "")
        current_role = st.session_state.get("current_user_role", "Analista")
        current_company = st.session_state.get("current_user_company", "TFG Pharma")
        current_notifications = st.session_state.get("ui_email_notifications", True)

        profile_panel = st.container(key="profile_panel")
        with profile_panel:
            st.markdown(
                '<div class="main-kicker">PharmaTFG Platform</div>'
                '<div class="main-title">Profile</div>'
                '<div class="main-text">Gestiona tus datos de cuenta y preferencias de notificaciones.</div>',
                unsafe_allow_html=True,
            )

            with st.form("profile_form"):
                info_col, pref_col = st.columns(2, gap="large")

                with info_col:
                    st.subheader("Informacion de cuenta")
                    full_name = st.text_input("Nombre completo", value=current_name)
                    email = st.text_input("Email", value=current_email)
                    role = st.selectbox(
                        "Rol",
                        ["Administrador", "Analista", "Viewer"],
                        index=["Administrador", "Analista", "Viewer"].index(current_role)
                        if current_role in {"Administrador", "Analista", "Viewer"}
                        else 1,
                    )
                    company = st.text_input("Empresa", value=current_company)

                with pref_col:
                    st.subheader("Preferencias")
                    notifications = st.checkbox("Recibir notificaciones por email", value=current_notifications)
                    st.caption(
                        f"Tema: {st.session_state.ui_theme_mode} | Acento: {st.session_state.ui_accent_name} | "
                        f"Tipografia: {st.session_state.ui_font_name}"
                    )

                save_col, cancel_col = st.columns(2)
                with save_col:
                    save_clicked = st.form_submit_button("Guardar cambios", use_container_width=True)
                with cancel_col:
                    cancel_clicked = st.form_submit_button("Cancelar", use_container_width=True)

        if save_clicked:
            if not full_name.strip() or not company.strip() or "@" not in email:
                st.error("Revisa el formulario: nombre, empresa y email valido son obligatorios.")
            else:
                save_user_profile(user_id, full_name, email, role, company)
                save_user_preferences(
                    user_id=user_id,
                    theme=st.session_state.ui_theme_mode,
                    accent=st.session_state.ui_accent_name,
                    font=st.session_state.ui_font_name,
                    base_font_size=int(st.session_state.ui_base_font_size),
                    notifications=bool(notifications),
                )

                st.session_state.current_user_name = full_name.strip()
                st.session_state.current_user_email = email.strip()
                st.session_state.current_user_role = role
                st.session_state.current_user_company = company.strip()
                st.session_state.ui_email_notifications = bool(notifications)

                log_user_activity(user_id, "Profile updated", f"Perfil actualizado por {full_name.strip()}")
                st.success("Cambios guardados correctamente.")

        if cancel_clicked:
            st.info("Cambios descartados.")
            st.rerun()

            st.markdown("---")
            st.subheader("Actividad reciente")
            recent_activity = get_recent_activity(user_id=user_id, limit=8)
            if recent_activity:
                activity_df = pd.DataFrame(recent_activity)
                activity_df = activity_df.rename(
                    columns={"action": "Accion", "details": "Detalles", "created_at": "Fecha"}
                )
                st.dataframe(activity_df, use_container_width=True, hide_index=True)
            else:
                st.caption("Aun no hay actividad registrada para este usuario.")
