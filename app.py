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

    st.write("Registra tus entrenamientos y analiza tu progreso en el tiempo.")

    # --- CONEXIÓN A GOOGLE SHEETS ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Leemos la hoja obligando a que busque datos nuevos (ttl=0 desactiva la memoria caché)
    try:
        df = conn.read(worksheet="Hoja 1", usecols=[0, 1, 2, 3], ttl=0)
        df = df.dropna(how="all") 
    except:
        df = pd.DataFrame(columns=["usuario", "fecha", "prueba", "marca"])

    # --- FORMULARIO PARA AÑADIR MARCAS ---
    st.subheader("📝 Registrar Nueva Marca")
    
    with st.form("formulario_marcas", clear_on_submit=True):
        fecha = st.date_input("Fecha del entrenamiento", datetime.date.today())
        prueba = st.selectbox("Prueba", ["100m lisos", "200m lisos", "400m lisos", "800m", "1500m", "5km", "Salto de Longitud"])
        marca = st.number_input("Tu marca (en segundos o metros)", min_value=0.0, format="%.2f")
        
        btn_guardar = st.form_submit_button("Guardar en la Nube")
        
        if btn_guardar:
            if marca > 0:
                nueva_fila = pd.DataFrame([{
                    "usuario": st.session_state.usuario_actual,
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "prueba": prueba,
                    "marca": marca
                }])
                
                df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                
                # Enviamos los datos y limpiamos la caché para que el gráfico se dibuje de inmediato
                conn.update(worksheet="Hoja 1", data=df_actualizado)
                st.cache_data.clear() 
                
                st.success("¡Marca guardada correctamente en Google Sheets!")
                st.rerun() 
            else:
                st.warning("Por favor, introduce una marca válida mayor que 0.")

    st.divider()

    # --- VISUALIZACIÓN DE PROGRESO ---
    st.subheader("📈 Tu Progreso Histórico")

    if not df.empty:
        df_usuario = df[df["usuario"] == st.session_state.usuario_actual]
        
        if not df_usuario.empty:
            pruebas_disponibles = df_usuario["prueba"].unique()
            prueba_seleccionada = st.selectbox("Selecciona la prueba para ver el gráfico:", pruebas_disponibles)
            
            # Filtramos y ordenamos por fecha
            df_grafico = df_usuario[df_usuario["prueba"] == prueba_seleccionada].sort_values(by="fecha")
            
            # Mostramos la tabla
            st.dataframe(df_grafico[["fecha", "marca"]].reset_index(drop=True), use_container_width=True)
            
            # Preparamos los datos para que el gráfico entienda que la fecha es el eje X
            df_grafico_listo = df_grafico.set_index("fecha")["marca"]
            
            # Y finalmente dibujamos el gráfico
            st.line_chart(df_grafico_listo)
        else:
            st.info("Aún no has registrado ninguna marca para tu usuario.")
    else:
        st.info("La base de datos está vacía. ¡Inaugura el panel!")
