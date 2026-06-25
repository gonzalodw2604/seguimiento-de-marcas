import streamlit as st
import pandas as pd
import datetime
import altair as alt
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# ==========================================
# CONFIGURACIÓN Y FUNCIONES
# ==========================================
st.set_page_config(page_title="BalasTeam - Gestión Atlética", page_icon="🏃‍♂️", layout="centered", initial_sidebar_state="expanded")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300) # El caché evita el error 429 de Google Sheets
def obtener_hoja(nombre_hoja):
    return conn.read(worksheet=nombre_hoja, ttl=0).astype(str)

def obtener_coeficiente(distancia, genero):
    coefs = {"60m": {"Hombre": 0.030, "Mujer": 0.025}, "100m": {"Hombre": 0.055, "Mujer": 0.050}, "200m": {"Hombre": 0.090, "Mujer": 0.080}}
    return coefs.get(distancia, {}).get(genero, 0.0)

def limpiar_comentarios(texto):
    texto = str(texto)
    if texto.startswith(("=", "+", "-", "@")): return "'" + texto
    return texto

# ==========================================
# AUTENTICACIÓN
# ==========================================
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🏃‍♂️ Acceso al Club")
    try:
        df_usuarios = obtener_hoja("Usuarios")
        df_usuarios["usuario"] = df_usuarios["usuario"].str.lower().str.strip()
        df_usuarios["contrasena"] = df_usuarios["contrasena"].str.strip()
        dict_usuarios = dict(zip(df_usuarios["usuario"], df_usuarios["contrasena"]))
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        dict_usuarios = {}

    tab_login, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Registro"])
    with tab_login:
        with st.form("login"):
            u = st.text_input("Usuario").lower().strip()
            p = st.text_input("Contraseña", type="password").strip()
            if st.form_submit_button("Entrar"):
                if u in dict_usuarios and dict_usuarios[u] == p:
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = u
                    st.rerun()
                else: st.error("Usuario o contraseña incorrectos.")
    with tab_registro:
        with st.form("reg"):
            u = st.text_input("Nuevo Usuario").lower().strip()
            p = st.text_input("Nueva Contraseña", type="password").strip()
            if st.form_submit_button("Crear"):
                if u in dict_usuarios: st.error("Usuario ya existe.")
                else:
                    conn.update(worksheet="Usuarios", data=pd.concat([df_usuarios, pd.DataFrame([{"usuario": u, "contrasena": p}])]))
                    st.success("Creado. Ya puedes entrar.")
else:
    # ==========================================
    # MENÚ Y APP PRINCIPAL
    # ==========================================
    st.sidebar.title("☰ MENÚ PRINCIPAL")
    st.sidebar.markdown(f"👋 Hola, **{st.session_state.usuario_actual.capitalize()}**!")
    modo_app = st.sidebar.radio("🧭 Herramienta:", ["📈 Seguimiento", "💨 Viento", "🏋️ Gym"])
    if st.sidebar.button("🚪 Salir"): st.session_state.autenticado = False; st.rerun()

    if modo_app == "📈 Seguimiento":
        st.title("📈 Seguimiento de Marcas")
        # Aquí iría toda tu lógica de pestañas de marcas que tenías
        st.info("Panel de seguimiento cargado.")
        
    elif modo_app == "💨 Viento":
        st.title("💨 Calculadora de Viento")
        dist = st.selectbox("Prueba", ["60m", "100m", "200m", "400m"])
        tiempo = st.number_input("Tiempo", step=0.01)
        viento = st.number_input("Viento", step=0.1)
        gen = st.radio("Género", ["Hombre", "Mujer"])
        if st.button("Calcular"):
            st.success(f"Tiempo neutralizado: {tiempo + (viento * obtener_coeficiente(dist, gen)):.2f}s")
            
    elif modo_app == "🏋️ Gym":
        st.title("🏋️ Calculadora 1RM")
        peso = st.number_input("Peso (kg)", step=2.5)
        reps = st.number_input("Reps", min_value=1, max_value=12)
        if st.button("Calcular"):
            st.metric("1RM", f"{peso * (1 + 0.0333 * reps):.1f} kg")
