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

# Conexión global a la base de datos
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SISTEMA DE AUTENTICACIÓN Y REGISTRO ---
if not st.session_state.autenticado:
    st.title("🏃‍♂️ Acceso al Club de Atletismo")
    
    # Intentamos leer la hoja de "Usuarios"
    try:
        df_usuarios = conn.read(worksheet="Usuarios", ttl=0)
        df_usuarios = df_usuarios.dropna(how="all", subset=["usuario", "contrasena"])
        
        # Nos aseguramos de que todo sea texto limpio para comparar bien
        df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.lower().str.strip()
        df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()
        
        # Convertimos la tabla en un diccionario de Python para chequear rápido
        dict_usuarios = dict(zip(df_usuarios["usuario"], df_usuarios["contrasena"]))
    except:
        # Si la hoja está vacía o recién creada
        df_usuarios = pd.DataFrame(columns=["usuario", "contrasena"])
        dict_usuarios = {}

    # Creamos dos pestañas en la web
    tab_login, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Nuevo Registro"])
    
    # -- PESTAÑA 1: LOGIN --
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

    # -- PESTAÑA 2: REGISTRO --
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
                    # Guardamos al nuevo usuario en el Excel
                    nueva_fila_user = pd.DataFrame([{
                        "usuario": nuevo_usuario, 
                        "contrasena": nueva_pass
                    }])
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

    st.write("Registra tus entrenamientos, anota tus sensaciones y analiza tu progreso.")

    # Intentamos leer la hoja principal de marcas (Hoja 1)
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
        df = df.dropna(how="all", subset=["usuario", "fecha", "prueba", "marca"]) 
    except:
        df = pd.DataFrame(columns=["usuario", "fecha", "prueba", "marca", "comentarios"])

    if "comentarios" not in df.columns:
        df["comentarios"] = ""
    else:
        df["comentarios"] = df["comentarios"].fillna("").astype(str)

    # --- 1. FORMULARIO PARA AÑADIR MARCAS ---
    st.subheader("📝 Registrar Nueva Marca")
    
    with st.form("formulario_marcas", clear_on_submit=True):
        fecha = st.date_input("Fecha del entrenamiento", datetime.date.today())
        prueba = st.selectbox("Prueba", ["100m lisos", "200m lisos", "400m lisos", "800m", "1500m", "5km", "Salto de Longitud"])
        marca = st.number_input("Tu marca (en segundos o metros)", min_value=0.0, format="%.2f")
        comentarios = st.text_input("Comentarios / Viento / Sensaciones (Opcional)")
        
        btn_guardar = st.form_submit_button("Guardar en la Nube")
        
        if btn_guardar:
            if marca > 0:
                nueva_fila = pd.DataFrame([{
                    "usuario": st.session_state.usuario_actual,
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "prueba": prueba,
                    "marca": marca,
                    "comentarios": comentarios
                }])
                
                df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                df_actualizado["comentarios"] = df_actualizado["comentarios"].apply(limpiar_comentarios)
                
                conn.update(worksheet="Hoja 1", data=df_actualizado)
                st.cache_data.clear() 
                st.success("¡Marca guardada!")
                st.rerun() 
            else:
                st.warning("Por favor, introduce una marca válida mayor que 0.")

    st.divider()

    # --- 2. ZONA DE EDICIÓN Y BORRADO ---
    st.subheader("⚙️ Edita o Borra tus Marcas")
    
    if not df.empty:
        df_usuario = df[df["usuario"] == st.session_state.usuario_actual].copy()
        df_otros = df[df["usuario"] != st.session_state.usuario_actual].copy()
        
        if not df_usuario.empty:
            st.info("Haz **doble clic** en cualquier celda para cambiar su valor. Para **borrar una fila**, haz clic en la casilla de la izquierda para seleccionarla y pulsa la tecla 'Suprimir' o 'Borrar' de tu teclado.")
            
            df_editado = st.data_editor(
                df_usuario,
                use_container_width=True,
                num_rows="dynamic", 
                hide_index=True,
                column_config={
                    "usuario": None, 
                    "fecha": "Fecha",
                    "prueba": st.column_config.SelectboxColumn("Prueba", options=["100m lisos", "200m lisos", "400m lisos", "800m", "1500m", "5km", "Salto de Longitud"]),
                    "marca": st.column_config.NumberColumn("Marca"),
                    "comentarios": st.column_config.TextColumn("Comentarios")
                }
            )
            
            if not df_editado.equals(df_usuario):
                st.warning("Has realizado cambios en la tabla. No olvides guardarlos.")
                if st.button("💾 Guardar Cambios en la Base de Datos"):
                    df_editado["usuario"] = st.session_state.usuario_actual
                    df_final = pd.concat([df_otros, df_editado], ignore_index=True)
                    df_final["comentarios"] = df_final["comentarios"].apply(limpiar_comentarios)
                    
                    conn.update(worksheet="Hoja 1", data=df_final)
                    st.cache_data.clear()
                    st.success("¡Datos actualizados!")
                    st.rerun()
        else:
            st.write("Aún no tienes marcas para editar.")
    else:
        st.write("Base de datos vacía.")

    st.divider()

    # --- 3. VISUALIZACIÓN DE PROGRESO ---
    st.subheader("📈 Tu Progreso Histórico")

    if not df.empty and not df_usuario.empty:
        pruebas_disponibles = df_usuario["prueba"].unique()
        prueba_seleccionada = st.selectbox("Selecciona la prueba para ver el gráfico:", pruebas_disponibles)
        
        df_grafico = df_usuario[df_usuario["prueba"] == prueba_seleccionada].sort_values(by="fecha")
        
        if not df_grafico.empty:
            df_grafico_listo = df_grafico.set_index("fecha")["marca"]
            st.line_chart(df_grafico_listo)
            
            df_comentarios = df_grafico[df_grafico["comentarios"] != ""]
            df_comentarios = df_comentarios[df_comentarios["comentarios"] != "'"]
            
            if not df_comentarios.empty:
                st.markdown(f"**Tus anotaciones en {prueba_seleccionada}:**")
                st.dataframe(df_comentarios[["fecha", "marca", "comentarios"]], hide_index=True, use_container_width=True)
