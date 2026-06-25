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

# --- CACHÉ PARA EVITAR ERROR 429 ---
@st.cache_data(ttl=300)
def obtener_hoja(nombre):
    return conn.read(worksheet=nombre, ttl=0).astype(str)

def obtener_coeficiente(distancia, genero):
    coefs = {"60m": {"Hombre": 0.030, "Mujer": 0.025}, "100m": {"Hombre": 0.055, "Mujer": 0.050}, "200m": {"Hombre": 0.090, "Mujer": 0.080}}
    return coefs.get(distancia, {}).get(genero, 0.0)

def limpiar_comentarios(texto):
    texto = str(texto)
    if texto.startswith(("=", "+", "-", "@")): return "'" + texto
    return texto

# ==========================================
# AUTENTICACIÓN REFORZADA
# ==========================================
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🏃‍♂️ Acceso al Club")
    df_usuarios = obtener_hoja("Usuarios")
    df_usuarios["usuario"] = df_usuarios["usuario"].str.lower().str.strip()
    df_usuarios["contrasena"] = df_usuarios["contrasena"].str.strip()
    dict_usuarios = dict(zip(df_usuarios["usuario"], df_usuarios["contrasena"]))

    tab_login, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Registro"])
    with tab_login:
        with st.form("login"):
            u = st.text_input("Usuario").lower().strip()
            p = st.text_input("Contraseña", type="password").strip()
            if st.form_submit_button("Entrar"):
                if u in dict_usuarios and dict_usuarios[u] == p:
                    st.session_state.autenticado = True; st.session_state.usuario_actual = u; st.rerun()
                else: st.error("Usuario o contraseña incorrectos.")
    with tab_registro:
        with st.form("reg"):
            u = st.text_input("Nuevo Usuario").lower().strip()
            p = st.text_input("Nueva Contraseña", type="password").strip()
            if st.form_submit_button("Crear"):
                conn.update(worksheet="Usuarios", data=pd.concat([df_usuarios, pd.DataFrame([{"usuario": u, "contrasena": p}])]))
                st.success("Creado. Ya puedes entrar.")
else:
    # ==========================================
    # APP PRINCIPAL
    # ==========================================
    st.sidebar.title("☰ MENÚ PRINCIPAL")
    st.sidebar.markdown(f"👋 Hola, **{st.session_state.usuario_actual.capitalize()}**!")
    modo_app = st.sidebar.radio("🧭 Herramienta:", ["📈 Seguimiento de Marcas", "💨 Calculadora de Viento", "🏋️ Gimnasio (Fuerza y 1RM)"])
    if st.sidebar.button("🚪 Salir"): st.session_state.autenticado = False; st.rerun()

    if modo_app == "📈 Seguimiento de Marcas":
        df = obtener_hoja("Hoja 1")
        df_objetivos = obtener_hoja("Objetivos")
        # [AQUÍ VA TU CÓDIGO ORIGINAL DE SEGUIMIENTO. 
        # IMPORTANTE: Cambia los conn.read por obtener_hoja("NOMBRE_HOJA")]
        st.write("Panel de marcas activo.")

    elif modo_app == "💨 Calculadora de Viento":
        # [AQUÍ VA TU CÓDIGO ORIGINAL DE VIENTO]
        st.write("Calculadora de viento activa.")

    elif modo_app == "🏋️ Gimnasio (Fuerza y 1RM)":
        st.title("🏋️ Calculadora de Fuerza (1RM)")
        # [AQUÍ VA TU CÓDIGO ORIGINAL DE GYM]
