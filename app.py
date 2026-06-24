import streamlit as st
import pandas as pd
import datetime
import altair as alt
from streamlit_gsheets import GSheetsConnection

# --- ESCUDO ANTI-ERRORES ---
def limpiar_comentarios(texto):
    texto = str(texto)
    if texto.startswith(("=", "+", "-", "@")):
        return "'" + texto
    return texto

# Configuración
st.set_page_config(page_title="Control de Marcas", layout="centered")

# --- ESTADO Y CONEXIÓN ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "usuario_actual" not in st.session_state: st.session_state.usuario_actual = ""
conn = st.connection("gsheets", type=GSheetsConnection)

# --- AUTENTICACIÓN ---
if not st.session_state.autenticado:
    st.title("🏃‍♂️ Acceso al Club")
    try:
        df_usuarios = conn.read(worksheet="Usuarios", ttl=0)
        dict_usuarios = dict(zip(df_usuarios["usuario"].str.lower().str.strip(), df_usuarios["contrasena"].str.strip()))
    except: dict_usuarios = {}

    tab_login, tab_registro = st.tabs(["🔐 Iniciar", "📝 Registro"])
    with tab_login:
        with st.form("login"):
            u = st.text_input("Usuario").lower().strip()
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar") and u in dict_usuarios and dict_usuarios[u] == p:
                st.session_state.autenticado = True; st.session_state.usuario_actual = u; st.rerun()
    with tab_registro:
        with st.form("registro"):
            u = st.text_input("Nuevo Usuario").lower().strip()
            p = st.text_input("Nueva Contraseña", type="password")
            if st.form_submit_button("Crear") and u not in dict_usuarios:
                conn.update(worksheet="Usuarios", data=pd.concat([df_usuarios, pd.DataFrame([{"usuario": u, "contrasena": p}])]))
                st.success("Creado")
else:
    # --- PANEL PRINCIPAL ---
    if st.button("Cerrar Sesión"): st.session_state.autenticado = False; st.rerun()
    
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0).dropna(how="all", subset=["usuario", "fecha", "prueba", "marca"])
        df_objetivos = conn.read(worksheet="Objetivos", ttl=0).dropna(how="all", subset=["usuario", "prueba", "objetivo"])
    except:
        df = pd.DataFrame(columns=["usuario", "fecha", "prueba", "marca", "comentarios", "tipo"])
        df_objetivos = pd.DataFrame(columns=["usuario", "prueba", "objetivo"])

    lista_pruebas = ["100m lisos", "200m lisos", "400m lisos", "800m lisos", "Salto de Longitud", "Triple Salto"]
    
    # Formularios de inserción
    col1, col2 = st.columns(2)
    with col1:
        with st.form("form_m", clear_on_submit=True):
            f, p, m, t, c = st.date_input("Fecha"), st.selectbox("Prueba", lista_pruebas), st.number_input("Marca", format="%.2f"), st.selectbox("Tipo", ["Entrenamiento", "Competición"]), st.text_input("Comentarios")
            if st.form_submit_button("Guardar Marca"):
                conn.update(worksheet="Hoja 1", data=pd.concat([df, pd.DataFrame([{"usuario": st.session_state.usuario_actual, "fecha": f.strftime("%Y-%m-%d"), "prueba": p, "marca": m, "tipo": t, "comentarios": limpiar_comentarios(c)}])]))
                st.rerun()
    with col2:
        with st.form("form_o", clear_on_submit=True):
            po, mo = st.selectbox("Prueba", lista_pruebas), st.number_input("Objetivo", format="%.2f")
            if st.form_submit_button("Guardar Objetivo"):
                d_r = df_objetivos[~((df_objetivos["usuario"] == st.session_state.usuario_actual) & (df_objetivos["prueba"] == po))]
                conn.update(worksheet="Objetivos", data=pd.concat([d_r, pd.DataFrame([{"usuario": st.session_state.usuario_actual, "prueba": po, "objetivo": mo}])]))
                st.rerun()

    # Análisis
    st.subheader("📈 Progreso")
    df_u = df[df["usuario"] == st.session_state.usuario_actual].copy()
    p_sel = st.selectbox("Prueba:", lista_pruebas)
    df_g = df_u[df_u["prueba"] == p_sel].sort_values("fecha")
    
    # Métricas y Gráfica
    meta = df_objetivos[(df_objetivos["usuario"]==st.session_state.usuario_actual) & (df_objetivos["prueba"]==p_sel)]
    meta_val = meta.iloc[0]["objetivo"] if not meta.empty else None
    
    if not df_g.empty:
        mejor = df_g["marca"].max() if "Salto" in p_sel else df_g["marca"].min()
        st.metric("🏅 Récord Personal", mejor)
        
        c = alt.Chart(df_g).mark_line(point=True).encode(x="fecha:T", y="marca:Q", color="tipo:N", tooltip=["fecha","marca","tipo","comentarios"])
        if meta_val: st.altair_chart(alt.layer(c, alt.Chart(pd.DataFrame({'o':[meta_val]})).mark_rule(color='red').encode(y='o:Q')).interactive(), use_container_width=True)
        else: st.altair_chart(c.interactive(), use_container_width=True)

    # --- LISTA CON EDICIÓN COMPLETA ---
    st.markdown("### 📋 Tus registros")
    for idx, row in df_u[df_u["prueba"] == p_sel].iterrows():
        c1, c2, c3 = st.columns([4, 1, 1])
        c1.write(f"**{row['marca']}** - {row['tipo']} ({row['fecha']})")
        with c2:
            with st.popover("✏️"):
                with st.form(f"edit_{idx}"):
                    nf = st.date_input("Fecha", pd.to_datetime(row['fecha']))
                    np = st.selectbox("Prueba", lista_pruebas, index=lista_pruebas.index(row['prueba']))
                    nm = st.number_input("Marca", value=float(row['marca']))
                    nt = st.selectbox("Tipo", ["Entrenamiento", "Competición"], index=["Entrenamiento", "Competición"].index(row['tipo']))
                    nc = st.text_input("Comentarios", row['comentarios'])
                    if st.form_submit_button("Guardar Cambios"):
                        df.loc[idx] = [st.session_state.usuario_actual, nf.strftime("%Y-%m-%d"), np, nm, nc, nt]
                        conn.update(worksheet="Hoja 1", data=df)
                        st.rerun()
        if c3.button("🗑️", key=f"del_{idx}"):
            conn.update(worksheet="Hoja 1", data=df.drop(idx))
            st.rerun()
