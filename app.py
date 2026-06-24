import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Control de Marcas de Atletismo", layout="centered")

# --- SISTEMA DE AUTENTICACIÓN ---
USUARIOS_PERMITIDOS = {
    "juan": "atletismo123",
    "maria": "velocidad2026",
    "pedro": "fondista99"
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

# Interfaz de Login
if not st.session_state.autenticado:
    st.title("🏃‍♂️ Acceso al Club de Atletismo")
    
    usuario = st.text_input("Usuario").lower().strip()
    contrasena = st.text_input("Contraseña", type="password")
    
    if st.button("Iniciar Sesión"):
        if usuario in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario] == contrasena:
            st.session_state.autenticado = True
            st.session_state.usuario_actual = usuario
            st.rerun() 
        else:
            st.error("Usuario o contraseña incorrectos.")

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

    # --- CONEXIÓN A GOOGLE SHEETS ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Leemos la base de datos
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0)
        # Limpiamos filas que estén completamente en blanco
        df = df.dropna(how="all", subset=["usuario", "fecha", "prueba", "marca"]) 
    except:
        df = pd.DataFrame(columns=["usuario", "fecha", "prueba", "marca", "comentarios"])

    # Seguridad: Si falta la columna comentarios, la creamos vacía para evitar errores
    if "comentarios" not in df.columns:
        df["comentarios"] = ""
    else:
        # Convertimos los "vacíos" de Excel en texto en blanco normal
        df["comentarios"] = df["comentarios"].fillna("").astype(str)

    # --- 1. FORMULARIO PARA AÑADIR MARCAS ---
    st.subheader("📝 Registrar Nueva Marca")
    
    with st.form("formulario_marcas", clear_on_submit=True):
        fecha = st.date_input("Fecha del entrenamiento", datetime.date.today())
        prueba = st.selectbox("Prueba", ["100m lisos", "200m lisos", "400m lisos", "800m", "1500m", "5km", "Salto de Longitud"])
        marca = st.number_input("Tu marca (en segundos o metros)", min_value=0.0, format="%.2f")
        
        # NUEVO: Cajita para los comentarios
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
            
            # Mostramos la tabla editable
            df_editado = st.data_editor(
                df_usuario,
                use_container_width=True,
                num_rows="dynamic", # Permite añadir o borrar filas enteras
                hide_index=True,
                column_config={
                    "usuario": None, # Ocultamos la columna usuario por seguridad (que nadie cambie de dueño)
                    "fecha": "Fecha",
                    "prueba": st.column_config.SelectboxColumn("Prueba", options=["100m lisos", "200m lisos", "400m lisos", "800m", "1500m", "5km", "Salto de Longitud"]),
                    "marca": st.column_config.NumberColumn("Marca"),
                    "comentarios": st.column_config.TextColumn("Comentarios")
                }
            )
            
            # LÓGICA MÁGICA: Solo enseñamos el botón de guardar si detectamos que ha tocado algo
            if not df_editado.equals(df_usuario):
                st.warning("Has realizado cambios en la tabla. No olvides guardarlos.")
                if st.button("💾 Guardar Cambios en la Base de Datos"):
                    # Nos aseguramos de que no hayan borrado su usuario sin querer
                    df_editado["usuario"] = st.session_state.usuario_actual
                    
                    # Unimos la base de datos de los demás usuarios con la tuya actualizada
                    df_final = pd.concat([df_otros, df_editado], ignore_index=True)
                    
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
            # Dibujamos la gráfica
            df_grafico_listo = df_grafico.set_index("fecha")["marca"]
            st.line_chart(df_grafico_listo)
            
            # Debajo de la gráfica enseñamos las notas que tomó el usuario
            df_comentarios = df_grafico[df_grafico["comentarios"] != ""]
            if not df_comentarios.empty:
                st.markdown(f"**Tus anotaciones en {prueba_seleccionada}:**")
                st.dataframe(df_comentarios[["fecha", "marca", "comentarios"]], hide_index=True, use_container_width=True)
