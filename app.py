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

# --- PANEL DEL ATLETA ---
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

    if "comentarios" not in df.columns: df["comentarios"] = ""
    if "tipo" not in df.columns: df["tipo"] = "Entrenamiento"
    
    try:
        df_objetivos = conn.read(worksheet="Objetivos", ttl=0)
        df_objetivos = df_objetivos.dropna(how="all", subset=["usuario", "prueba", "objetivo"])
    except:
        df_objetivos = pd.DataFrame(columns=["usuario", "prueba", "objetivo"])

    lista_pruebas = ["100m lisos", "200m lisos", "400m lisos", "800m lisos", "Salto de Longitud", "Triple Salto"]
    lista_tipos = ["Entrenamiento", "Competición"]

    # --- 1. NUEVA MARCA ---
    with st.expander("📝 Registrar Nueva Marca"):
        with st.form("formulario_marcas", clear_on_submit=True):
            fecha = st.date_input("Fecha", datetime.date.today())
            prueba = st.selectbox("Prueba", lista_pruebas)
            marca = st.number_input("Marca (seg/m)", min_value=0.0, format="%.2f")
            tipo = st.selectbox("Tipo de actividad", lista_tipos)
            comentarios = st.text_input("Sensaciones/Viento")
            btn_guardar = st.form_submit_button("Guardar Marca")
            
            if btn_guardar and marca > 0:
                nueva_fila = pd.DataFrame([{
                    "usuario": st.session_state.usuario_actual,
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "prueba": prueba,
                    "marca": marca,
                    "tipo": tipo,
                    "comentarios": limpiar_comentarios(comentarios)
                }])
                df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(worksheet="Hoja 1", data=df_actualizado)
                st.cache_data.clear() 
                st.rerun() 

    # --- 2. OBJETIVOS ---
    with st.expander("🎯 Fijar Objetivo"):
        with st.form("formulario_objetivos", clear_on_submit=True):
            prueba_obj = st.selectbox("Prueba", lista_pruebas)
            marca_obj = st.number_input("Tu objetivo (seg/m)", min_value=0.0, format="%.2f")
            btn_objetivo = st.form_submit_button("Guardar Objetivo")
            
            if btn_objetivo and marca_obj > 0:
                df_resto_obj = df_objetivos[~((df_objetivos["usuario"] == st.session_state.usuario_actual) & (df_objetivos["prueba"] == prueba_obj))]
                nuevo_obj = pd.DataFrame([{"usuario": st.session_state.usuario_actual, "prueba": prueba_obj, "objetivo": marca_obj}])
                df_obj_actualizado = pd.concat([df_resto_obj, nuevo_obj], ignore_index=True)
                conn.update(worksheet="Objetivos", data=df_obj_actualizado)
                st.cache_data.clear()
                st.rerun()

    # --- 3. ANÁLISIS Y LISTADO (CON BOTÓN DE BORRAR) ---
    st.subheader("📈 Análisis de Progreso")
    df_usuario = df[df["usuario"] == st.session_state.usuario_actual].copy()
    
    if not df_usuario.empty:
        prueba_seleccionada = st.selectbox("Selecciona prueba:", df_usuario["prueba"].unique())
        df_grafico = df_usuario[df_usuario["prueba"] == prueba_seleccionada].sort_values(by="fecha")
        df_grafico["fecha"] = pd.to_datetime(df_grafico["fecha"])
        
        # Gráfica
        lineas = alt.Chart(df_grafico).mark_line(point=alt.OverlayMarkDef(filled=True, size=70)).encode(
            x=alt.X("fecha:T", title="Fecha", axis=alt.Axis(format="%Y-%m-%d")),
            y=alt.Y("marca:Q", title="Marca", scale=alt.Scale(zero=False)),
            color="tipo:N", tooltip=["fecha", "marca", "tipo", "comentarios"]
        )
        st.altair_chart(lineas, use_container_width=True)

        st.markdown("### 📋 Tus registros")
        for index, row in df_usuario.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{row['prueba']}** - {row['marca']} ({row['tipo']}) - *{row['fecha']}*")
            with col2:
                # Botón de borrar con un identificador único basado en el índice
                if st.button("🗑️ Borrar", key=f"del_{index}"):
                    df_final = df.drop(index)
                    conn.update(worksheet="Hoja 1", data=df_final)
                    st.cache_data.clear()
                    st.rerun()
    else:
        st.info("No hay marcas registradas.")
