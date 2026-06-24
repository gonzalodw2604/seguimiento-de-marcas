# --- GRÁFICA PROFESIONAL ---
            st.markdown("### 📊 Gráfico de evolución")
            
            # Caso 1: Hay marcas registradas
            if not df_grafico.empty:
                lineas = alt.Chart(df_grafico).mark_line(point=alt.OverlayMarkDef(filled=True, size=70, opacity=1)).encode(
                    x=alt.X("fecha:T", title="Fecha", axis=alt.Axis(format="%Y-%m-%d")),
                    y=alt.Y("marca:Q", title="Marca", scale=alt.Scale(zero=False)),
                    color=alt.Color("tipo:N", title="Actividad"),
                    tooltip=["fecha", "marca", "tipo", "comentarios"]
                )
                
                if meta_actual:
                    objetivo_df = pd.DataFrame({'objetivo': [meta_actual]})
                    linea_meta = alt.Chart(objetivo_df).mark_rule(color='red', strokeDash=[5, 5]).encode(y='objetivo:Q')
                    grafica_final = alt.layer(lineas, linea_meta).interactive()
                else:
                    grafica_final = lineas.interactive()
                
                st.altair_chart(grafica_final, use_container_width=True)

            # Caso 2: No hay marcas, pero SÍ hay objetivo
            elif meta_actual:
                st.info(f"Aún no tienes marcas registradas para esta prueba, pero tu objetivo es **{meta_actual}**.")
                objetivo_df = pd.DataFrame({'objetivo': [meta_actual]})
                linea_meta = alt.Chart(objetivo_df).mark_rule(color='red', strokeDash=[5, 5]).encode(
                    y=alt.Y('objetivo:Q', title="Marca")
                ).properties(height=200)
                st.altair_chart(linea_meta, use_container_width=True)

            # Caso 3: No hay nada
            else:
                st.info("Aún no tienes marcas ni objetivos para esta prueba. ¡Regístralos arriba para empezar!")
