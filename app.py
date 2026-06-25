import streamlit as st
import pandas as pd
import datetime
import altair as alt
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# ==========================================
# BASE DE DATOS Y FUNCIONES GLOBALES
# ==========================================
MINIMAS_DB = {
    "Hombre": {
       "100m": {"Absoluto": 10.60, "Sub23": 10.75, "Sub20": 10.85, "Sub18": 11.05, "Sub16": 11.45, "M35": 11.31, "M40": 11.70, "M45": 11.85, "M50": 12.04, "M55": 12.42, "M60": 12.93},
        "200m": {"Absoluto": 21.40, "Sub23": 21.75, "Sub20": 22.00, "Sub18": 22.40, "M35": 23.02, "M40": 23.60, "M45": 24.07, "M50": 24.69, "M55": 25.78, "M60": 27.04},
        "400m": {"Absoluto": 47.80, "Sub23": 48.00, "Sub20": 48.75, "Sub18": 49.75, "M35": 51.15, "M40": 53.17, "M45": 53.14, "M50": 56.14, "M55": 57.97, "M60": 61.82}
    },
    "Mujer": {
       "100m": {"Absoluto": 11.90, "Sub23": 12.05, "Sub20": 12.30, "Sub18": 12.25, "Sub16": 12.55, "F35": 13.08, "F40": 13.49, "F45": 13.76, "F50": 13.98, "F55": 14.67, "F60": 15.10},
        "200m": {"Absoluto": 24.30, "Sub23": 24.85, "Sub20": 25.20, "Sub18": 25.25, "F35": 26.42, "F40": 27.95, "F45": 28.56, "F50": 28.60, "F55": 30.19, "F60": 32.06},
        "400m": {"Absoluto": 54.50, "Sub23": 56.25, "Sub20": 57.10, "Sub18": 57.75, "F35": 61.15, "F40": 62.69, "F45": 64.29, "F50": 65.95, "F55": 68.18, "F60": 74.29}
    }
}

def obtener_coeficiente(distancia, genero):
    if distancia == "60m":
        return 0.030 if genero == "Hombre" else 0.025
    elif distancia == "100m":
        return 0.055 if genero == "Hombre" else 0.050
    elif distancia == "200m":
        return 0.090 if genero == "Hombre" else 0.080
    elif distancia == "400m":
        return 0.0  
    return 0.0

def limpiar_comentarios(texto):
    texto = str(texto)
    if texto.startswith(("=", "+", "-", "@")):
        return "'" + texto
    return texto

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="BalasTeam - Gestión Atlética", 
    page_icon="🏃‍♂️", 
    layout="centered",
    initial_sidebar_state="expanded"
)

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
    # --- MENÚ DE NAVEGACIÓN LATERAL (SIDEBAR) ---
    st.sidebar.title("☰ MENÚ PRINCIPAL")
    st.sidebar.markdown(f"👋 ¡Hola, **{st.session_state.usuario_actual.capitalize()}**!")
    
    # Selector de modo principal
    modo_app = st.sidebar.radio(
        "🧭 Selecciona herramienta:",
        ["📈 Seguimiento de Marcas", "💨 Calculadora de Viento", "🏋️ Gimnasio (Fuerza y 1RM)"]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True): 
        st.session_state.autenticado = False
        st.rerun()
    
    st.info("👈 **Menú Lateral:** Toca el icono de la esquina superior izquierda ( **>** ) para cambiar de herramienta o cerrar sesión.")

    # Carga de datos base de marcas comunes
    try:
        df = conn.read(worksheet="Hoja 1", ttl=0).dropna(how="all", subset=["usuario", "fecha", "prueba", "marca"])
        df_objetivos = conn.read(worksheet="Objetivos", ttl=0).dropna(how="all", subset=["usuario", "prueba", "objetivo"])
    except:
        df = pd.DataFrame(columns=["usuario", "fecha", "prueba", "marca", "comentarios", "tipo"])
        df_objetivos = pd.DataFrame(columns=["usuario", "prueba", "objetivo"])

    # ==========================================
    # MODO 1: SEGUIMIENTO DE MARCAS
    # ==========================================
    if modo_app == "📈 Seguimiento de Marcas":
        
        try:
            df_competencias = conn.read(worksheet="Competiciones", ttl=0).dropna(how="all", subset=["fecha", "nombre"])
        except:
            df_competencias = pd.DataFrame(columns=["fecha", "nombre", "lugar", "pruebas", "creador", "modificador"])

        if "creador" not in df_competencias.columns: df_competencias["creador"] = "Anónimo"
        if "modificador" not in df_competencias.columns: df_competencias["modificador"] = ""
        df_competencias["creador"] = df_competencias["creador"].fillna("Anónimo")
        df_competencias["modificador"] = df_competencias["modificador"].fillna("")

        lista_pruebas = ["100m lisos", "200m lisos", "400m lisos", "800m lisos", "1500m lisos", "Salto de Longitud", "Triple Salto", "Salto con Pértiga"]
        
        tab_perfil, tab_leaderboard, tab_calendar, tab_faa, tab_rfea = st.tabs([
            "📊 Mi Perfil", "🏆 Clasificación", "📅 BalasTeam", "🌐 Calendario FAA", "🏅 Ranking RFEA"
        ])
        
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
            else: st.info("Ningún atleta ha registrado marcas en esta prueba todavía.")

        with tab_calendar:
            st.subheader("📅 Próximas Competiciones - BalasTeam")
            with st.expander("➕ Añadir Nueva Competición al Calendario"):
                with st.form("form_evento", clear_on_submit=True):
                    fech_ev, nomb_ev, luga_ev, prue_ev = st.date_input("Fecha del Evento", datetime.date.today()), st.text_input("Nombre de la Competición"), st.text_input("Lugar / Pista"), st.text_input("Pruebas convocadas")
                    if st.form_submit_button("Publicar Competición"):
                        if nomb_ev.strip() == "": st.error("Por favor, introduce el nombre del evento.")
                        else:
                            nuevo_evento = pd.DataFrame([{"fecha": fech_ev.strftime("%Y-%m-%d"), "nombre": str(nomb_ev), "lugar": str(luga_ev), "pruebas": str(prue_ev), "creador": st.session_state.usuario_actual, "modificador": ""}])
                            conn.update(worksheet="Competiciones", data=pd.concat([df_competencias, nuevo_evento], ignore_index=True).astype(str))
                            st.success("¡Competición añadida!"); st.rerun()

            if not df_competencias.empty:
                df_competencias = df_competencias.sort_values(by="fecha", ascending=True)
                st.markdown("---")
                for idx, row in df_competencias.iterrows():
                    try: f_formateada = pd.to_datetime(row['fecha']).strftime("%d/%m/%Y")
                    except: f_formateada = row['fecha']
                    creador_formateado = str(row['creador']).capitalize()
                    modificador_formateado = str(row['modificador']).capitalize() if str(row['modificador']).strip() != "" else None
                    
                    with st.container():
                        col_tit, col_btn1, col_btn2 = st.columns([6, 1, 1])
                        col_tit.markdown(f"#### 🏟️ {row['nombre']}")
                        with col_btn1:
                            with st.popover("✏️"):
                                with st.form(f"edit_comp_{idx}"):
                                    n_fech, n_nomb, n_luga, n_prue = st.date_input("Fecha", pd.to_datetime(row['fecha'])), st.text_input("Nombre", row['nombre']), st.text_input("Lugar", row['lugar']), st.text_input("Pruebas", row['pruebas'])
                                    if st.form_submit_button("Actualizar"):
                                        df_competencias.at[idx, 'fecha'], df_competencias.at[idx, 'nombre'], df_competencias.at[idx, 'lugar'], df_competencias.at[idx, 'pruebas'], df_competencias.at[idx, 'modificador'] = n_fech.strftime("%Y-%m-%d"), str(n_nomb), str(n_luga), str(n_prue), st.session_state.usuario_actual
                                        conn.update(worksheet="Competiciones", data=df_competencias.astype(str)); st.rerun()
                        with col_btn2:
                            if st.button("🗑️", key=f"del_comp_{idx}"):
                                conn.update(worksheet="Competiciones", data=df_competencias.drop(idx).astype(str)); st.rerun()
                        
                        col_det1, col_det2 = st.columns(2)
                        with col_det1:
                            st.write(f"📅 **Fecha:** {f_formateada}"); st.write(f"📍 **Lugar:** {row['lugar']}")
                        with col_det2:
                            st.write(f"🏃‍♂️ **Pruebas:** {row['pruebas']}")
                            if modificador_formateado: st.write(f"👤 **De:** {creador_formateado} | ✏️ **Editado por:** {modificador_formateado}")
                            else: st.write(f"👤 **De:** {creador_formateado}")
                        st.markdown("---")
            else: st.info("No hay competiciones registradas.")
                
        with tab_faa:
            st.subheader("🌐 Calendario Oficial de la FAA")
            components.iframe("https://web.faalive.com/Calendar", height=700, scrolling=True)
            st.markdown("👉 *[Abrir Calendario FAA en otra pestaña](https://web.faalive.com/Calendar).*")

        with tab_rfea:
            st.subheader("🇪🇸 Rankings Oficiales de la RFEA")
            st.info("ℹ️ Acceso directo para consultar marcas oficiales:")
            col_b1, col_b2 = st.columns(2)
            col_b1.link_button("🟢 Abrir Ranking Andaluz", "https://atletismorfea.es/federaciones/ranking/and", use_container_width=True)
            col_b2.link_button("🔴 Abrir Ranking Nacional", "https://atletismorfea.es/ranking", use_container_width=True)

    # ==========================================
    # MODO 2: CALCULADORA DE VIENTO
    # ==========================================
    elif modo_app == "💨 Calculadora de Viento":
        st.title("💨 Calculadora de Viento Neutral - BalasTeam")
        st.write("Herramienta de análisis de marcas de velocidad sin influencia del viento y marcas mínimas RFEA.")

        tab1, tab2 = st.tabs(["📊 Cálculo Individual & Simulador", "⚔️ Duelo Virtual (Cara a Cara)"])

        with tab1:
            st.header("⚡ Analizar una Marca")
            col1, col2 = st.columns(2)
            with col1:
                distancia = st.selectbox("Selecciona la distancia:", ["60m", "100m", "200m", "400m"], index=None, placeholder="Elige una prueba...")
                tiempo_real = st.number_input("Tiempo registrado (segundos):", value=None, min_value=0.0, step=0.01, placeholder="Ej: 11.28", key="ind_time")
            with col2:
                if distancia == "400m":
                    viento = st.number_input("Viento medido (m/s):", value=0.0, step=0.1, disabled=True, help="En los 400m no aplica viento.", key="ind_wind_400")
                else:
                    viento = st.number_input("Viento medido (m/s):", value=None, step=0.1, placeholder="Ej: 2.3", key="ind_wind")
                genero = st.radio("Género del atleta:", ["Hombre", "Mujer"], index=None, horizontal=True, key="ind_gen")

            lista_categorias = ["Absoluto", "Sub23", "Sub20", "Sub18", "Sub16", "Máster 35", "Máster 40", "Máster 45", "Máster 50", "Máster 55"]
            categoria_elegida = st.selectbox("🏆 Selecciona tu categoría (Campeonato de España):", lista_categorias, index=None, placeholder="Elige tu campeonato destino...")

            if st.button("🚀 Calcular Rendimiento Completo", type="primary", key="btn_individual"):
                if distancia is None or tiempo_real is None or viento is None or genero is None or categoria_elegida is None:
                    st.error("⚠️ Por favor, rellena todos los campos.")
                else:
                    coef = obtener_coeficiente(distancia, genero)
                    tiempo_neutral = tiempo_real + (viento * coef)
                    
                    st.markdown("---")
                    st.subheader("🚦 Homologación de la Marca")
                    if distancia == "400m":
                        st.success("🟢 **Marca Oficial:** ¡Tu marca es totalmente válida!")
                        estado_legal = "Válida (No aplica viento)"
                    elif viento > 2.0:
                        st.warning(f"🟠 **Marca No Homologable:** El viento ({viento:+} m/s) supera el límite legal de +2.0 m/s.")
                        estado_legal = "No Legal (+2.0)"
                    else:
                        st.success(f"🟢 **Marca 100% Legal:** El viento de {viento:+} m/s cumple la normativa.")
                        estado_legal = "Legal"
                    
                    st.markdown(f"### ⏱️ Tiempo Ajustado Neutral: **{tiempo_neutral:.2f}s**")
                    st.markdown("---")

                    st.subheader(f"🎖️ Objetivo: Campeonato de España {categoria_elegida}")
                    texto_minimas_wa = ""
                    if categoria_elegida in MINIMAS_DB[genero].get(distancia, {}):
                        marca_minima = MINIMAS_DB[genero][distancia][categoria_elegida]
                        if tiempo_neutral <= marca_minima:
                            diferencia = marca_minima - tiempo_neutral
                            st.balloons()
                            st.success(f"🎉 ¡TIENES LA MÍNIMA! Has rebajado los {marca_minima:.2f}s exigidos por {diferencia:.2f}s.")
                            texto_minimas_wa = f"✅ ¡Mínima conseguida para el España {categoria_elegida}!"
                        else:
                            diferencia = tiempo_neutral - marca_minima
                            st.warning(f"🎯 Te has quedado a **{diferencia:.2f}s** de la mínima ({marca_minima:.2f}s).")
                            texto_minimas_wa = f"🚀 Rozando la mínima {categoria_elegida} (a {diferencia:.2f}s)"
                    else:
                        st.info("ℹ️ Distancia no contemplada oficialmente para esta categoría.")
                        texto_minimas_wa = "ℹ️ Sin prueba oficial en esta categoría."

                    st.markdown("---")
                    st.subheader("🎯 Proyector de Marcas (Ventana de Potencial)")
                    proyecciones_rango = {}
                    if distancia == "60m":
                        f_min_100, f_max_100 = (1.50, 1.57) if genero == "Hombre" else (1.51, 1.58)
                        f_min_200, f_max_200 = (2.95, 3.20) if genero == "Hombre" else (3.00, 3.25)
                        proyecciones_rango["100m"] = (tiempo_neutral * f_min_100, tiempo_neutral * f_max_100)
                        proyecciones_rango["200m"] = (tiempo_neutral * f_min_200, tiempo_neutral * f_max_200)
                    elif distancia == "100m":
                        f_min_60, f_max_60 = (1.57, 1.50) if genero == "Hombre" else (1.58, 1.51)
                        f_min_200, f_max_200 = (1.96, 2.06) if genero == "Hombre" else (1.98, 2.08)
                        proyecciones_rango["60m"] = (tiempo_neutral / f_min_60, tiempo_neutral / f_max_60)
                        proyecciones_rango["200m"] = (tiempo_neutral * f_min_200, tiempo_neutral * f_max_200)
                    elif distancia == "200m":
                        f_min_100, f_max_100 = (2.06, 1.96) if genero == "Hombre" else (2.08, 1.98)
                        f_min_400, f_max_400 = (2.15, 2.25) if genero == "Hombre" else (2.20, 2.30)
                        proyecciones_rango["100m"] = (tiempo_neutral / f_min_100, tiempo_neutral / f_max_100)
                        proyecciones_rango["400m"] = (tiempo_neutral * f_min_400, tiempo_neutral * f_max_400)
                    elif distancia == "400m":
                        f_min_200, f_max_200 = (2.25, 2.15) if genero == "Hombre" else (2.30, 2.20)
                        proyecciones_rango["200m"] = (tiempo_neutral / f_min_200, tiempo_neutral / f_max_200)

                    if proyecciones_rango:
                        p_cols = st.columns(len(proyecciones_rango))
                        for idx, (dist, (t_min, t_max)) in enumerate(proyecciones_rango.items()):
                            p_cols[idx].metric(label=f"Rango Estimado {dist}", value=f"{t_min:.2f}s - {t_max:.2f}s")
                    
                    st.markdown("---")
                    st.subheader("📊 Tabla de Simulación de Vientos")
                    vientos_simular = [0.0] if distancia == "400m" else [-2.0, -1.0, 0.0, 1.0, 2.0]
                    filas_simulacion = []
                    for v in vientos_simular:
                        t_estimado = tiempo_neutral - (v * coef)
                        filas_simulacion.append({"Viento Simulado": f"{v:+} m/s" if v != 0 else "0.0 m/s", "Tiempo Estimado": f"{t_estimado:.2f}s", "Nota": "Neutral" if v == 0.0 else ("Límite Legal" if v == 2.0 else "")})
                    st.dataframe(pd.DataFrame(filas_simulacion), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.subheader("📱 Compartir con el Equipo")
                    texto_proyecciones_wa = ""
                    for dist, (t_min, t_max) in proyecciones_rango.items(): texto_proyecciones_wa += f"🎯 *Rango {dist}:* {t_min:.2f}s a {t_max:.2f}s\n"
                    txt_viento = f" (Viento: {viento:+} m/s)" if distancia != "400m" else ""
                    texto_whatsapp = f"🏃‍♂️ *Resultado Calculadora de Viento!*\n Prueba: {distancia} ({genero})\n⏱️ Tiempo Real: {tiempo_real:.2f}s{txt_viento}\n✨ Ajustado (0.0): {tiempo_neutral:.2f}s\n🚦 Estado: {estado_legal}\n\n🏆 *Estatus de Mínima:*\n{texto_minimas_wa}\n\n"
                    if texto_proyecciones_wa: texto_whatsapp += f"🔮 *Ventana de Potencial:*\n{texto_proyecciones_wa}"
                    st.code(texto_whatsapp.strip(), language="text")

        with tab2:
            st.header("⚔️ Duelo Virtual de Atletas")
            duelo_distancia = st.selectbox("Selecciona la distancia del duelo:", ["60m", "100m", "200m", "400m"], index=1)
            col_at1, col_at2 = st.columns(2)
            
            with col_at1:
                st.markdown("### 🏃‍♂️ Atleta 1")
                nom1 = st.text_input("Nombre Atleta 1:", value="Atleta A")
                t1 = st.number_input("Tiempo registrado (s):", value=None, min_value=0.0, step=0.01, placeholder="Ej: 10.65", key="t1")
                v1 = st.number_input("Viento medido (m/s):", value=0.0 if duelo_distancia == "400m" else None, step=0.1, disabled=(duelo_distancia == "400m"), key="v1")
                g1 = st.radio("Género Atleta 1:", ["Hombre", "Mujer"], index=0, key="g1", horizontal=True)
                
            with col_at2:
                st.markdown("### 🏃‍♀️ Atleta 2")
                nom2 = st.text_input("Nombre Atleta 2:", value="Atleta B")
                t2 = st.number_input("Tiempo registrado (s):", value=None, min_value=0.0, step=0.01, placeholder="Ej: 10.75", key="t2")
                v2 = st.number_input("Viento medido (m/s):", value=0.0 if duelo_distancia == "400m" else None, step=0.1, disabled=(duelo_distancia == "400m"), key="v2")
                g2 = st.radio("Género Atleta 2:", ["Hombre", "Mujer"], index=0, key="g2", horizontal=True)

            if st.button("🔥 ¡Iniciar Duelo Virtual!", type="primary"):
                if t1 is None or v1 is None or t2 is None or v2 is None: st.error("⚠️ Rellena todos los tiempos.")
                else:
                    n1 = t1 + (v1 * obtener_coeficiente(duelo_distancia, g1))
                    n2 = t2 + (v2 * obtener_coeficiente(duelo_distancia, g2))
                    st.markdown("### 🏆 Veredicto")
                    st.write(f"👉 Tiempo ajustado de **{nom1}**: **{n1:.2f}s**")
                    st.write(f"👉 Tiempo ajustado de **{nom2}**: **{n2:.2f}s**")
                    if abs(n1 - n2) < 0.001: st.info("🤝 ¡Empate técnico absoluto!")
                    elif n1 < n2: st.success(f"👑 **¡Ganador: {nom1}!** Ventaja virtual de **{n2 - n1:.2f}s**.")
                    else: st.success(f"👑 **¡Ganador: {nom2}!** Ventaja virtual de **{n1 - n2:.2f}s**.")

    # ==========================================
    # MODO 3: GIMNASIO (Calculadora 1RM)
    # ==========================================
    elif modo_app == "🏋️ Gimnasio (Fuerza y 1RM)":
        st.title("🏋️ Calculadora de Fuerza (1RM)")
        st.write("Calcula tu Repetición Máxima (1RM) teórica basándote en lo que has levantado hoy y descubre exactamente qué peso poner en la barra.")

        st.markdown("### ⚙️ Datos del Levantamiento")
        col_gym1, col_gym2 = st.columns(2)
        with col_gym1:
            ejercicio = st.selectbox("Ejercicio:", ["Sentadilla Trasera", "Peso Muerto", "Press de Banca", "Cargada (Clean)", "Arrancada (Snatch)", "Hip Thrust", "Otro"])
            peso_levantado = st.number_input("Peso levantado (kg):", min_value=0.0, step=2.5, value=80.0)
        with col_gym2:
            reps_realizadas = st.number_input("Repeticiones completadas:", min_value=1, max_value=20, step=1, value=5, help="Más de 12 reps pierde precisión.")
        
        if st.button("🔥 Calcular mi 1RM", type="primary", use_container_width=True):
            if reps_realizadas == 1: rm_calculado = peso_levantado
            else:
                epley = peso_levantado * (1 + 0.0333 * reps_realizadas)
                brzycki = peso_levantado * (36 / (37 - reps_realizadas))
                rm_calculado = (epley + brzycki) / 2

            st.markdown("---")
            st.markdown(f"<h2 style='text-align: center; color: #FF4B4B;'>🏆 Tu 1RM en {ejercicio} es: {rm_calculado:.1f} kg</h2>", unsafe_allow_html=True)
            st.markdown("---")

            st.subheader("📊 Zonas de Entrenamiento")
            zonas = [
                {"Porcentaje": "100%", "Carga en Barra": f"{rm_calculado:.1f} kg", "Enfoque": "Fuerza Máxima (1 rep)"},
                {"Porcentaje": "95%", "Carga en Barra": f"{rm_calculado * 0.95:.1f} kg", "Enfoque": "Fuerza Máxima (2 a 3 reps)"},
                {"Porcentaje": "90%", "Carga en Barra": f"{rm_calculado * 0.90:.1f} kg", "Enfoque": "Fuerza Máxima (3 a 4 reps)"},
                {"Porcentaje": "85%", "Carga en Barra": f"{rm_calculado * 0.85:.1f} kg", "Enfoque": "Fuerza / Hipertrofia (5 a 6 reps)"},
                {"Porcentaje": "80%", "Carga en Barra": f"{rm_calculado * 0.80:.1f} kg", "Enfoque": "Hipertrofia Estructural (7 a 8 reps)"},
                {"Porcentaje": "75%", "Carga en Barra": f"{rm_calculado * 0.75:.1f} kg", "Enfoque": "Hipertrofia Básica (9 a 10 reps)"},
                {"Porcentaje": "70%", "Carga en Barra": f"{rm_calculado * 0.70:.1f} kg", "Enfoque": "Hipertrofia / Resistencia (11 a 12 reps)"},
                {"Porcentaje": "60%", "Carga en Barra": f"{rm_calculado * 0.60:.1f} kg", "Enfoque": "Potencia / Explosividad (Velocidad)"},
                {"Porcentaje": "50%", "Carga en Barra": f"{rm_calculado * 0.50:.1f} kg", "Enfoque": "Calentamiento Rápido / Recuperación"}
            ]
            st.dataframe(pd.DataFrame(zonas), use_container_width=True, hide_index=True)
