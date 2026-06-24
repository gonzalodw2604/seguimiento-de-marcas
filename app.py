import streamlit as st
import pandas as pd
import datetime
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

# --- SISTEMA DE AUTENTICACIÓN Y REGISTRO ---
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
            st.write("Si ya tienes cuenta, entra aquí:")
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
            st.write("¿Eres nuevo? Crea tu cuenta para guardar tus marcas.")
            nuevo_usuario = st.text_input("Elige un nombre de usuario (sin espacios)").lower().strip()
            nueva_pass = st.text_input("Elige una contraseña", type="password")
            btn_registro = st.form_submit_button("Crear Cuenta")
            
            if btn_registro:
                if nuevo_usuario == "" or nueva_pass == "":
                    st.warning("Por favor, rellena ambos campos.")
                elif " " in nuevo_usuario:
                    st.warning("El nombre de usuario no puede contener espacios.")
                elif nuevo_usuario in dict_usuarios:
                    st.error("Ese usuario ya existe. ¡Elige otro distinto!")
                else:
                    nueva_fila_user = pd.DataFrame([{"usuario": nuevo_usuario, "contrasena": nueva_pass}])
                    df_usuarios_actualizado = pd.concat([df_usuarios, nueva_fila_user], ignore_index=True)
                    conn.update(worksheet="Usuarios", data=df_usuarios_actualizado)
                    st.cache_data.clear()
                    st.success("¡Cuenta creada con éxito! Ya puedes ir a la pestaña 'Iniciar Sesión' para entrar.")

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
        df = pd.DataFrame(columns=["usuario", "fecha", "prueba", "marca", "comentarios"])

    if "comentarios" not in df.columns:
        df["comentarios"] = ""
    else:
        df["comentarios"] = df["comentarios"].fillna("").astype(str)

    try:
        df_objetivos = conn.read(worksheet="Objetivos", ttl=0)
        df_objetivos = df_objetivos.dropna(how="all", subset=["usuario", "prueba", "objetivo"])
    except:
        df_objetivos = pd.DataFrame(columns=["usuario", "prueba", "objetivo"])

    lista_pruebas = ["100m lisos", "200m lisos", "400m lisos", "800m", "Salto de Longitud", "Triple Salto"]

    # --- 1. AÑADIR MARCAS Y OBJETIVOS ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 Nueva Marca")
        with st.form("formulario_marcas", clear_on_submit=True):
            fecha = st.date_input("Fecha", datetime.date.today())
            prueba = st.selectbox("Prueba", lista_pruebas)
            marca = st.number_input("Marca (seg/m)", min_value=0.0, format="%.2f")
            comentarios = st.text_input("Sensaciones/Viento")
            btn_guardar = st.form_submit_button("Guardar Marca")
            
            if btn_guardar and marca > 0:
                nueva_fila = pd.DataFrame([{
                    "usuario": st.session_state.usuario_actual,
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "prueba": prueba,
                    "marca": marca,
                    "comentarios": limpiar_comentarios(comentarios)
                }])
                df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(worksheet="Hoja 1", data=df_actualizado)
                st.cache_data.clear() 
                st.success("¡Marca guardada!")
                st.rerun() 

    with col2:
        st.subheader("🎯 Fijar Objetivo")
        with st.form("formulario_objetivos", clear_on_submit=True):
            prueba_obj = st.selectbox("Prueba a mejorar", lista_pruebas)
            marca_obj = st.number_input("Tu meta (seg/m)", min_value=0.0, format="%.2f")
            btn_objetivo = st.form_submit_button("Guardar Meta")
            
            if btn_objetivo and marca_obj > 0:
                df_resto_obj = df_objetivos[~((df_objetivos["usuario"] == st.session_state.usuario_actual) & (df_objetivos["prueba"] == prueba_obj))]
                nuevo_obj = pd.DataFrame([{"usuario": st.session_state.usuario_actual, "prueba": prueba_obj, "objetivo": marca_obj}])
                df_obj_actualizado = pd.concat([df_resto_obj, nuevo_obj], ignore_index=True)
                
                conn.update(worksheet="Objetivos", data=df_obj_actualizado)
                st.cache_data.clear()
                st.success(f"¡Objetivo de {marca_obj} fijado!")
                st.rerun()

    st.divider()

    # --- 2. VISUALIZACIÓN DE PROGRESO MATEMÁTICO ---
    st.subheader("📈 Análisis de Progreso")

    if not df.empty:
        df_usuario = df[df["usuario"] == st.session_state.usuario_actual].copy()
        
        if not df_usuario.empty:
            pruebas_disponibles = df_usuario["prueba"].unique()
            prueba_seleccionada = st.selectbox("Selecciona la prueba a analizar:", pruebas_disponibles)
            
            df_grafico = df_usuario[df_usuario["prueba"] == prueba_seleccionada].sort_values(by="fecha")
            
            # --- CÁLCULO DE METRICS ---
            es_salto = "Salto" in prueba_seleccionada
            
            if es_salto:
                mejor_marca = df_grafico["marca"].max()
                peor_marca = df_grafico["marca"].min()
            else:
                mejor_marca = df_grafico["marca"].min()
                peor_marca = df_grafico["marca"].max()
                
            primera_marca = df_grafico.iloc[0]["marca"] 
            mejora_total = round(abs(primera_marca - mejor_marca), 2)
            
            meta_actual = None
            if not df_objetivos.empty:
                filtro_obj = df_objetivos[(df_objetivos["usuario"] == st.session_state.usuario_actual) & (df_objetivos["prueba"] == prueba_seleccionada)]
                if not filtro_obj.empty:
                    meta_actual = filtro_obj.iloc[0]["objetivo"]

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("🏅 Récord Personal", mejor_marca, f"Mejora total: {mejora_total}", delta_color="normal" if es_salto else "inverse")
            
            if meta_actual:
                distancia_meta = round(abs(mejor_marca - meta_actual), 2)
                col_m2.metric("🎯 Tu Objetivo", meta_actual)
                col_m3.metric("🚀 Distancia a la meta", f"{distancia_meta} {'m' if es_salto else 'seg'}")
            else:
                col_m2.info("No has fijado un objetivo para esta prueba.")

            # --- GRÁFICA CON LÍNEA DE OBJETIVO ---
            df_grafico_listo = df_grafico.set_index("fecha")[["marca"]]
            
            if meta_actual:
                df_grafico_listo["objetivo"] = meta_actual
            
            st.line_chart(df_grafico_listo)
            
            with st.expander("Ver, editar o borrar historial detallado"):
                df_otros = df[df["usuario"] != st.session_state.usuario_actual].copy()
                
                column_config = {
                    "usuario": None, 
                    "fecha": "Fecha", 
                    "prueba": st.column_config.SelectboxColumn("Prueba", options=lista_pruebas), 
                    "marca": "Marca", 
                    "comentarios": "Comentarios"
                }
                
                df_editado = st.data_editor(
                    df_usuario,
                    use_container_width=True,
                    num_rows="dynamic", hide_index=True,
                    column_config=column_config
                )
                if not df_editado.equals(df_usuario):
                    if st.button("💾 Guardar Cambios"):
                        df_editado["usuario"] = st.session_state.usuario_actual
                        df_final = pd.concat([df_otros, df_editado], ignore_index=True)
                        df_final["comentarios"] = df_final["comentarios"].apply(limpiar_comentarios)
                        conn.update(worksheet="Hoja 1", data=df_final)
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.info("Aún no has registrado ninguna marca.")
    else:
        st.info("La base de datos está vacía.")
