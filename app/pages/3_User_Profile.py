import streamlit as st

st.set_page_config(
    page_title="Perfil de Usuario - TFG Pharma",
    layout="wide",
)

st.title("👤 Perfil de Usuario")

# Información del usuario
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("""
    <div style='text-align: center; padding: 30px;'>
        <div style='width: 150px; height: 150px; margin: 0 auto; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; font-size: 80px;'>
            👤
        </div>
        <h2 style='margin-top: 20px;'>Usuario Demo</h2>
        <p style='color: #9CA3AF;'>demo@tfgpharma.com</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.subheader("Información de la cuenta")
    
    with st.form("user_profile_form"):
        nombre = st.text_input("Nombre completo", value="Usuario Demo")
        email = st.text_input("Email", value="demo@tfgpharma.com")
        rol = st.selectbox("Rol", ["Administrador", "Analista", "Viewer"], index=1)
        empresa = st.text_input("Empresa", value="TFG Pharma")
        
        st.markdown("---")
        st.subheader("Preferencias")
        
        notificaciones = st.checkbox("Recibir notificaciones por email", value=True)
        tema_oscuro = st.checkbox("Modo oscuro", value=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            guardar = st.form_submit_button("💾 Guardar cambios", use_container_width=True)
        with col_btn2:
            cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)
        
        if guardar:
            st.success("✅ Cambios guardados correctamente")
        if cancelar:
            st.info("❌ Cambios descartados")

st.markdown("---")

# Actividad reciente
st.subheader("📊 Actividad reciente")

actividades = [
    {"accion": "Consulta Overview", "fecha": "2026-02-26 12:30", "detalles": "Visualizó mapa de oportunidades"},
    {"accion": "Descarga CSV", "fecha": "2026-02-26 11:15", "detalles": "Top opportunities.csv"},
    {"accion": "Filtro CCAA", "fecha": "2026-02-25 16:45", "detalles": "Exploró hospitales en Madrid"},
    {"accion": "Simulación", "fecha": "2026-02-25 15:20", "detalles": "What-if análisis en Cataluña"},
    {"accion": "Login", "fecha": "2026-02-25 09:00", "detalles": "Inicio de sesión exitoso"},
]

import pandas as pd
df_actividades = pd.DataFrame(actividades)
st.dataframe(df_actividades, use_container_width=True, hide_index=True)

st.markdown("---")

# Estadísticas de uso
st.subheader("📈 Estadísticas de uso")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Sesiones totales", "47", "+3")
col2.metric("Reportes descargados", "12", "+2")
col3.metric("CCAA consultadas", "15", "+1")
col4.metric("Tiempo promedio", "45 min", "+5 min")
