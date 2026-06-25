import streamlit as st
import pandas as pd
import datetime
import altair as alt
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# ==========================================
# CONFIGURACIÓN Y FUNCIONES
# ==========================================
st.set_page_config(page_title="The Balas Team App", page_icon="🏃‍♂️", layout="centered", initial_sidebar_state="expanded")

def obtener_coeficiente(distancia, genero):
    coefs = {"60m": {"Hombre": 0.030, "Mujer": 0.025}, "100m": {"Hombre": 0.055, "Mujer": 0.050}, "200m": {"Hombre": 0.090, "Mujer": 0.080}}
    return coefs.get(distancia, {}).get(genero, 0.0)

def limpiar_texto(texto):
    return str(texto).lower().strip()

# ==========================================
# AUTENTICACIÓN
# ==========================================
if "autenticado" not in st.session_state: st.session_state.autenticado = False
conn = st.connection("gsheets", type=GSheetsConnection)

if not st.session_state.autenticado:
    st.title("🏃‍♂️ The Balas Team - Acceso")
    df_u = conn.read(worksheet="Usuarios", ttl=0).astype(str)
    dict_users = dict(zip(df_u["usuario"].apply(limpiar_texto), df_u["contrasena"].str.strip()))
    
    tab1, tab2 = st.tabs(["🔐 Entrar", "📝 Registro"])
    with tab1:
        with st.form("login"):
            u = st.text_input("Usuario").lower().strip()
            p = st.text_input("Contraseña", type="password").strip()
            if st.form_submit_button("Entrar"):
                if u in dict_users and dict_users[u] == p:
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = u
                    st.rerun()
                else: st.error("Usuario o contraseña incorrectos.")
    with tab2:
        with st.form("reg"):
            u = st.text_input("Nuevo Usuario").lower().strip()
            p = st.text_input("Nueva Contraseña", type="password").strip()
            if st.form_submit_button("Crear"):
                conn.update(worksheet="Usuarios", data=pd.concat([df_u, pd.DataFrame([{"usuario": u, "contrasena": p}])]))
                st.success("Usuario creado. Ya puedes entrar.")
else:
    # ==========================================
    # MENÚ PRINCIPAL
    # ==========================================
    st.sidebar.title("☰ MENÚ PRINCIPAL")
    modo = st.sidebar.radio("Selecciona:", ["📈 Seguimiento", "💨 Viento", "🏋️ Gym"])
    if st.sidebar.button("🚪 Salir"): st.session_state.autenticado = False; st.rerun()
    
    # --- MODO 1: SEGUIMIENTO ---
    if modo == "📈 Seguimiento":
        st.title("📈 Seguimiento de Marcas")
        # (Aquí va toda tu lógica de marcas de tu app original)
        st.write("Bienvenido al panel de control de marcas.")

    # --- MODO 2: VIENTO ---
    elif modo == "💨 Viento":
        st.title("💨 Calculadora de Viento")
        dist = st.selectbox("Prueba", ["60m", "100m", "200m", "400m"])
        tiempo = st.number_input("Tiempo", step=0.01)
        viento = st.number_input("Viento", step=0.1)
        gen = st.radio("Género", ["Hombre", "Mujer"])
        if st.button("Calcular"):
            coef = obtener_coeficiente(dist, gen)
            st.success(f"Tiempo neutralizado: {tiempo + (viento * coef):.2f}s")

    # --- MODO 3: GYM ---
    elif modo == "🏋️ Gym":
        st.title("🏋️ Calculadora 1RM")
        ej = st.text_input("Ejercicio")
        peso = st.number_input("Peso (kg)", step=2.5)
        reps = st.number_input("Reps", min_value=1, max_value=12)
        if st.button("Calcular 1RM"):
            rm = peso * (1 + 0.0333 * reps)
            st.metric("Tu 1RM es", f"{rm:.1f} kg")
