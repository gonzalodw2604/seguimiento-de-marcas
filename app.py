import streamlit as st
import pandas as pd
import datetime
import altair as alt
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

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

    tab_login, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Registro"])
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
    col_user, col_out = st.columns([4, 1])
    with col_user:
        st.subheader(f"Atleta: {st.session_state.usuario_actual.capitalize()}")
    with col_out:
        if st.button("Cerrar Sesión"): st.session_state.autenticado = False; st.rerun()
    
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0).dropna(how="all", subset=["usuario", "fecha", "prueba", "marca"])
        df_objetivos = conn.read(worksheet="Objetivos", ttl=0).dropna(how="all", subset=["usuario", "prueba", "objetivo"])
    except:
        df = pd.DataFrame(columns=["usuario", "fecha", "prueba", "marca", "comentarios", "tipo"])
        df_objetivos = pd.DataFrame(columns=["usuario", "prueba", "objetivo"])

    # Base de datos para el Calendario Común
    try:
        df_competencias = conn.read(worksheet="Competiciones", ttl=0).dropna(how="all", subset=["fecha", "nombre"])
    except:
        df_competencias = pd.DataFrame(columns=["fecha", "nombre", "lugar", "pruebas", "creador", "modificador"])

    if "creador" not in df_competencias.columns: df_competencias["creador"] = "Anónimo"
    if "modificador" not in df_competencias.columns: df_competencias["modificador"] = ""

    # Rellenar nulos para evitar errores visuales
    df_competencias["creador"] = df_competencias["creador"].fillna("Anónimo")
    df_competencias["modificador"] = df_competencias["modificador"].fillna("")

    # --- LISTA DE PRUEBAS ---
    lista_pruebas = [
        "100m lisos", 
        "200m lisos", 
        "400m lisos", 
        "800m lisos", 
        "1500m lisos", 
        "Salto de Longitud", 
        "Triple Salto", 
        "Salto con Pértiga"
    ]
    
    # --- CREACIÓN DE PESTAÑAS (TABS) ---
    tab_perfil, tab_leaderboard, tab_calendar, tab_faa, tab_rfea = st.tabs([
        "📊 Mi Perfil", 
        "🏆 Clasificación", 
        "📅 BalasTeam",
        "🌐 Calendario FAA",
        "🇪🇸 Ranking RFEA"
    ])
    
    # PESTAÑA 1: PERFIL PERSONAL
    with tab_perfil:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("form_m", clear_on_submit=True):
                st.markdown("**📝 Nueva Marca**")
                f, p, m, t, c = st.date_input("Fecha"), st.selectbox("Prueba", lista_pruebas), st.number_input("Marca", format="%.2f"), st.selectbox("Tipo", ["Entrenamiento", "Competición"]), st.text_input("Comentarios")
                if st.form_submit_button("Guardar Marca"):
                    conn.update(worksheet="Hoja 1", data=pd.concat([df, pd.DataFrame([{"usuario": st.session_state.usuario_actual, "fecha": f.strftime("%Y-%m-%d"), "prueba": p, "marca": m, "tipo": t, "comentarios": limpiar_comentarios(c)}])]))
                    st.rerun()
        with col2:
            with st.form("form_o", clear_on_submit=True):
                st.markdown("**🎯 Fijar Objetivo**")
                po, mo = st.selectbox("Prueba", lista_pruebas), st.number_input("Objetivo", format="%.2f")
                if st.form_submit_button("Guardar Objetivo"):
                    d_r = df_objetivos[~((df_objetivos["usuario"] == st.session_state.usuario_actual) & (df_objetivos["prueba"] == po))]
                    conn.update(worksheet="Objetivos", data=pd.concat([d_r, pd.DataFrame([{"usuario": st.session_state.usuario_actual, "prueba": po, "objetivo": mo}])]))
                    st.rerun()

        st.subheader("📈 Mi Progreso")
        df_u = df[df["usuario"] == st.session_state.usuario_actual].copy()
        p_sel = st.selectbox("Selecciona prueba para analizar:", lista_pruebas, key="perfil_prueba")
        df_g = df_u[df_u["prueba"] == p_sel].sort_values("fecha").copy()
        df_g["fecha"] = pd.to_datetime(df_g["fecha"])
        
        meta = df_objetivos[(df_objetivos["usuario"]==st.session_state.usuario_actual) & (df_objetivos["prueba"]==p_sel)]
        meta_val = meta.iloc[0]["objetivo"] if not meta.empty else None
        
        es_salto = "Salto" in p_sel or "Triple" in p_sel or "Pértiga" in p_sel
        
        if not df_g.empty:
            mejor = df_g["marca"].max() if es_salto else df_g["marca"].min()
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("🏅 Récord Personal", mejor)
            if meta_val:
                col_m2.metric("🎯 Tu Objetivo", meta_val)
                distancia = round(abs(mejor - meta_val), 2)
                col_m3.metric("📏 Metros a mejorar" if es_salto else "⏱️ Tiempo a bajar", f"{distancia} {'m' if es_salto else 'seg'}")
            
            c = alt.Chart(df_g).mark_line(point=True).encode(x="fecha:T", y="marca:Q", color="tipo:N", tooltip=["fecha","marca","tipo","comentarios"])
            if meta_val: st.altair_chart(alt.layer(c, alt.Chart(pd.DataFrame({'o':[meta_val]})).mark_rule(color='red', strokeDash=[5,5]).encode(y='o:Q')).interactive(), use_container_width=True)
            else: st.altair_chart(c.interactive(), use_container_width=True)

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
                        if st.form_submit_button("Guardar"):
                            df.at[idx, 'fecha'] = nf.strftime("%Y-%m-%d")
                            df.at[idx, 'prueba'] = np
                            df.at[idx, 'marca'] = nm
                            df.at[idx, 'tipo'] = nt
                            df.at[idx, 'comentarios'] = limpiar_comentarios(nc)
                            conn.update(worksheet="Hoja 1", data=df)
                            st.rerun()
            if c3.button("🗑️", key=f"del_{idx}"):
                conn.update(worksheet="Hoja 1", data=df.drop(idx))
                st.rerun()

    # PESTAÑA 2: RANKING DEL CLUB
    with tab_leaderboard:
        st.subheader("🏆 Ranking General del BalasTeam")
        p_leader = st.selectbox("Selecciona prueba para ver el ranking:", lista_pruebas, key="leader_prueba")
        df_p = df[df["prueba"] == p_leader].copy()
        
        if not df_p.empty:
            es_salto_leader = "Salto" in p_leader or "Triple" in p_leader or "Pértiga" in p_leader
            if es_salto_leader:
                leaderboard = df_p.groupby("usuario")["marca"].max().reset_index()
                leaderboard = leaderboard.sort_values(by="marca", ascending=False).reset_index(drop=True)
            else:
                leaderboard = df_p.groupby("usuario")["marca"].min().reset_index()
                leaderboard = leaderboard.sort_values(by="marca", ascending=True).reset_index(drop=True)
            
            leaderboard.index = leaderboard.index + 1
            leaderboard.index.name = "Puesto"
            leaderboard.columns = ["Atleta", "Mejor Marca"]
            leaderboard["Atleta"] = leaderboard["Atleta"].str.capitalize()
            
            unidad = "m" if es_salto_leader else "seg"
            leaderboard["Mejor Marca"] = leaderboard["Mejor Marca"].apply(lambda x: f"{x:.2f} {unidad}")
            
            def asignar_medalla(pos):
                if pos == 1: return "🥇"
                elif pos == 2: return "🥈"
                elif pos == 3: return "🥉"
                return f"{pos}º"
            
            leaderboard_display = leaderboard.copy()
            leaderboard_display["Puesto"] = [asignar_medalla(i) for i in leaderboard_display.index]
            leaderboard_display = leaderboard_display.set_index("Puesto")
            st.dataframe(leaderboard_display, use_container_width=True)
        else:
            st.info("Ningún atleta ha registrado marcas en esta prueba todavía.")

    # PESTAÑA 3: CALENDARIO BALASTEAM
    with tab_calendar:
        st.subheader("📅 Próximas Competiciones - BalasTeam")
        
        with st.expander("➕ Añadir Nueva Competición al Calendario"):
            with st.form("form_evento", clear_on_submit=True):
                fech_ev = st.date_input("Fecha del Evento", datetime.date.today())
                nomb_ev = st.text_input("Nombre de la Competición")
                luga_ev = st.text_input("Lugar / Pista")
                prue_ev = st.text_input("Pruebas convocadas")
                
                if st.form_submit_button("Publicar Competición"):
                    if nomb_ev.strip() == "":
                        st.error("Por favor, introduce el nombre del evento.")
                    else:
                        nuevo_evento = pd.DataFrame([{
                            "fecha": fech_ev.strftime("%Y-%m-%d"),
                            "nombre": str(nomb_ev),
                            "lugar": str(luga_ev),
                            "pruebas": str(prue_ev),
                            "creador": st.session_state.usuario_actual,
                            "modificador": ""
                        }])
                        df_competencias_actualizado = pd.concat([df_competencias, nuevo_evento], ignore_index=True)
                        df_competencias_actualizado = df_competencias_actualizado.astype(str)
                        conn.update(worksheet="Competiciones", data=df_competencias_actualizado)
                        st.success("¡Competición añadida con éxito!")
                        st.rerun()

        if not df_competencias.empty:
            df_competencias = df_competencias.sort_values(by="fecha", ascending=True)
            st.markdown("---")
            
            for idx, row in df_competencias.iterrows():
                try:
                    f_formateada = pd.to_datetime(row['fecha']).strftime("%d/%m/%Y")
                except:
                    f_formateada = row['fecha']
                
                creador_formateado = str(row['creador']).capitalize()
                modificador_formateado = str(row['modificador']).capitalize() if str(row['modificador']).strip() != "" else None
                
                with st.container():
                    col_tit, col_btn1, col_btn2 = st.columns([6, 1, 1])
                    with col_tit:
                        st.markdown(f"#### 🏟️ {row['nombre']}")
                    
                    with col_btn1:
                        with st.popover("✏️"):
                            with st.form(f"edit_comp_{idx}"):
                                n_fech = st.date_input("Fecha", pd.to_datetime(row['fecha']))
                                n_nomb = st.text_input("Nombre", row['nombre'])
                                n_luga = st.text_input("Lugar", row['lugar'])
                                n_prue = st.text_input("Pruebas", row['pruebas'])
                                if st.form_submit_button("Actualizar"):
                                    df_competencias.at[idx, 'fecha'] = n_fech.strftime("%Y-%m-%d")
                                    df_competencias.at[idx, 'nombre'] = str(n_nomb)
                                    df_competencias.at[idx, 'lugar'] = str(n_luga)
                                    df_competencias.at[idx, 'pruebas'] = str(n_prue)
                                    df_competencias.at[idx, 'modificador'] = st.session_state.usuario_actual
                                    df_competencias = df_competencias.astype(str)
                                    conn.update(worksheet="Competiciones", data=df_competencias)
                                    st.rerun()
                    
                    with col_btn2:
                        if st.button("🗑️", key=f"del_comp_{idx}"):
                            df_competencias_reducido = df_competencias.drop(idx).astype(str)
                            conn.update(worksheet="Competiciones", data=df_competencias_reducido)
                            st.rerun()
                    
                    col_det1, col_det2 = st.columns(2)
                    with col_det1:
                        st.write(f"📅 **Fecha:** {f_formateada}")
                        st.write(f"📍 **Lugar:** {row['lugar']}")
                    with col_det2:
                        st.write(f"🏃‍♂️ **Pruebas convocadas:** {row['pruebas']}")
                        if modificador_formateado:
                            st.write(f"👤 **Creado por:** {creador_formateado} | ✏️ **Editado por:** {modificador_formateado}")
                        else:
                            st.write(f"👤 **Publicado por:** {creador_formateado}")
                    
                    st.markdown(" ")
                    st.markdown("---")
        else:
            st.info("No hay competiciones registradas en el calendario. ¡Sé el primero en añadir una!")
            
    # PESTAÑA 4: CALENDARIO FAA (IFRAME)
    with tab_faa:
        st.subheader("🌐 Calendario Oficial de la FAA")
        st.write("Navega por las competiciones oficiales de la Federación Andaluza de Atletismo directamente desde aquí.")
        components.iframe("https://web.faalive.com/Calendar", height=700, scrolling=True)
        st.markdown("👉 *Si no ves el calendario correctamente, [ábrelo en una ventana nueva](https://web.faalive.com/Calendar).*")

    # PESTAÑA 5: RANKING RFEA (ACTUALIZADA)
    with tab_rfea:
        st.subheader("🇪🇸 Rankings Oficiales de la RFEA")
        st.write("Consulta las marcas oficiales para compararte a nivel autonómico o nacional.")
        
        st.info("ℹ️ La RFEA bloquea por seguridad que su web se vea incrustada en otras aplicaciones. ¡Pero tienes acceso directo desde aquí!")
        
        st.write("Selecciona qué ranking quieres consultar:")
        
        # Botones muy visuales que abren en pestaña nueva
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.link_button("🟢 Abrir Ranking Andaluz", "https://atletismorfea.es/federaciones/ranking/and", use_container_width=True)
        with col_btn2:
            st.link_button("🔴 Abrir Ranking Nacional", "https://atletismorfea.es/ranking", use_container_width=True)
