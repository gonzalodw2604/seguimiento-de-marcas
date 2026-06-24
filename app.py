import streamlit as st
import pandas as pd
import datetime
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- ESCUDO ANTI-ERRORES DE EXCEL ---
def limpiar_comentarios(texto):
    texto = str(texto)
    if texto.startswith(("=", "+", "-", "@")):
        return "'" + texto
    return texto

# Configuración de la página
st.set_page_config(page_title="Control de Marcas de Atletismo", layout="centered")

# --- ESTADO DE LA SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SISTEMA DE AUTENTICACIÓN ---
if not st.session_state.autenticado:
    st.title("🏃‍♂️ Acceso al Club de Atletismo")
    try:
        df_usuarios = conn.read(worksheet="Usuarios", ttl=0)
        df_usuarios = df_usuarios.dropna(how="all", subset=["usuario", "contrasena"])
        df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.lower().str.strip()
        df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()
        dict_usuarios = dict(zip(df_usuarios["usuario"], df_usuarios["contrasena"]))
    except:
        df_usuarios = pd.DataFrame(columns=["usuario", "contrasena"])
        dict_usuarios = {}

    tab_login, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Nuevo Registro"])
    with tab_login:
        with st.form("form_login"):
            usuario_login = st.text_input("Usuario").lower().strip()
            pass_login = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Entrar")
            if btn_login:
                if usuario_login in dict_usuarios and dict_usuarios[usuario_login] == pass_login:
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = usuario_login
                    st.rerun() 
                else:
                    st.error("Usuario o contraseña incorrectos.")
    with tab_registro:
        with st.form("form_registro"):
            nuevo_usuario = st.text_input("Elige un nombre de usuario").lower().strip()
            nueva_pass = st.text_input("Elige una contraseña", type="password")
            btn_registro = st.form_submit_button("Crear Cuenta")
            if btn_registro:
                if nuevo_usuario in dict_usuarios:
                    st.error("Ese usuario ya existe.")
                else:
                    nueva_fila_user = pd.DataFrame([{"usuario": nuevo_usuario, "contrasena": nueva_pass}])
                    df_usuarios_actualizado = pd.concat([df_usuarios, nueva_fila_user], ignore_index=True)
                    conn.update(worksheet="Usuarios", data=df_usuarios_actualizado)
                    st.success("¡Cuenta creada! Ya puedes iniciar sesión.")
else:
    col_titulo, col_logout = st.columns([4, 1])
    with col_titulo:
        st.title(f"Hola, {st.session_state.usuario_actual.capitalize()} 👋")
    with col_logout:
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.session_state.usuario_actual = ""
            st.rerun()

    # --- LECTURA DE BASES DE DATOS ---
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
        df = df.dropna(how="all", subset=["usuario", "fecha", "prueba", "marca"]) 
    except:
        df = pd.DataFrame(columns=["usuario", "fecha", "prueba", "marca", "comentarios", "tipo"])

    df["tipo"] = df["tipo"].fillna("Entrenamiento")
    df["comentarios"] = df["comentarios"].fillna("").astype(str)

    try:
        df_objetivos = conn.read(worksheet="Objetivos", ttl=0)
        df_objetivos = df_objetivos.dropna(how="all", subset=["usuario", "prueba", "objetivo"])
    except:
        df_objetivos = pd.DataFrame(columns=["usuario", "prueba", "objetivo"])

    lista_pruebas = ["100m lisos", "200m lisos", "400m lisos", "800m lisos", "Salto de Longitud", "Triple Salto"]
    
    # --- 1. FORMULARIOS ---
    col1, col2 = st.columns(2)
    with col1:
        with st.form("formulario_marcas", clear_on_submit=True):
            fecha = st.date_input("Fecha", datetime.date.today())
            prueba = st.selectbox("Prueba", lista_pruebas)
            marca = st.number_input("Marca (seg/m)", min_value=0.0, format="%.2f")
            tipo = st.selectbox("Tipo", ["Entrenamiento", "Competición"])
            comentarios = st.text_input("Sensaciones/Viento")
            if st.form_submit_button("Guardar Marca"):
                nueva_fila = pd.DataFrame([{"usuario": st.session_state.usuario_actual, "fecha": fecha.strftime("%Y-%m-%d"), "prueba": prueba, "marca": marca, "tipo": tipo, "comentarios": limpiar_comentarios(comentarios)}])
                conn.update(worksheet="Hoja 1", data=pd.concat([df, nueva_fila], ignore_index=True))
                st.rerun()
    with col2:
        with st.form("formulario_objetivos", clear_on_submit=True):
            prueba_obj = st.selectbox("Prueba", lista_pruebas)
            marca_obj = st.number_input("Tu objetivo (seg/m)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Guardar Objetivo"):
                df_resto = df_objetivos[~((df_objetivos["usuario"] == st.session_state.usuario_actual) & (df_objetivos["prueba"] == prueba_obj))]
                conn.update(worksheet="Objetivos", data=pd.concat([df_resto, pd.DataFrame([{"usuario": st.session_state.usuario_actual, "prueba": prueba_obj, "objetivo": marca_obj}])], ignore_index=True))
                st.rerun()

    # --- 2. ANÁLISIS ---
    st.subheader("📈 Análisis de Progreso")
    df_usuario = df[df["usuario"] == st.session_state.usuario_actual].copy()
    prueba_seleccionada = st.selectbox("Selecciona prueba:", lista_pruebas)
    df_grafico = df_usuario[df_usuario["prueba"] == prueba_seleccionada].sort_values(by="fecha").copy()
    df_grafico["fecha"] = pd.to_datetime(df_grafico["fecha"])
    
    # Buscar objetivo
    meta_actual = None
    filtro_obj = df_objetivos[(df_objetivos["usuario"] == st.session_state.usuario_actual) & (df_objetivos["prueba"] == prueba_seleccionada)]
    if not filtro_obj.empty: meta_actual = filtro_obj.iloc[0]["objetivo"]

    # --- LÓGICA DE GRÁFICA (SIEMPRE VISIBLE) ---
    if not df_grafico.empty:
        # Gráfico con datos
        chart = alt.Chart(df_grafico).mark_line(point=True).encode(
            x=alt.X("fecha:T", title="Fecha"),
            y=alt.Y("marca:Q", title="Marca", scale=alt.Scale(zero=False)),
            color="tipo:N", tooltip=["fecha", "marca", "tipo", "comentarios"]
        )
        # Métricas (solo si hay datos)
        mejor_marca = df_grafico["marca"].max() if ("Salto" in prueba_seleccionada) else df_grafico["marca"].min()
        st.metric("🏅 Récord Personal", mejor_marca)
        
        # Celebración
        if meta_actual and (("Salto" in prueba_seleccionada and mejor_marca >= meta_actual) or (not "Salto" in prueba_seleccionada and mejor_marca <= meta_actual)):
            st.balloons()
            st.success("¡Objetivo superado!")
            if st.button("Limpiar objetivo"):
                conn.update(worksheet="Objetivos", data=df_objetivos[~((df_objetivos["usuario"] == st.session_state.usuario_actual) & (df_objetivos["prueba"] == prueba_seleccionada))])
                st.rerun()
    else:
        # Gráfico vacío (placeholder)
        chart = alt.Chart(pd.DataFrame({'x': [0], 'y': [0]})).mark_line().encode(
            x=alt.X('x', title="Fecha"), y=alt.Y('y', title="Marca")
        ).properties(title="Aún no hay marcas registradas")

    # Añadir línea objetivo siempre que exista
    if meta_actual:
        rule = alt.Chart(pd.DataFrame({'obj': [meta_actual]})).mark_rule(color='red', strokeDash=[5, 5]).encode(y='obj:Q')
        st.altair_chart(alt.layer(chart, rule).interactive(), use_container_width=True)
    else:
        st.altair_chart(chart.interactive(), use_container_width=True)

    # Listado
    st.markdown("### 📋 Tus registros")
    for index, row in df_usuario[df_usuario["prueba"] == prueba_seleccionada].iterrows():
        col1, col2 = st.columns([4, 1])
        with col1: st.write(f"**{row['marca']}** - {row['tipo']} ({row['fecha']})")
        with col2:
            if st.button("🗑️", key=f"del_{index}"):
                conn.update(worksheet="Hoja 1", data=df.drop(index))
                st.rerun()
