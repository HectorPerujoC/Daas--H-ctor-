import sqlite3
import pandas as pd
import plotly.express as px

print("1. Conectando a la memoria histórica...")
conn = sqlite3.connect("historico_subastas.db")

# Extraemos todas las métricas de valor de la base de datos
query = """
SELECT Provincia, Valor_Num, Deposito_Num 
FROM subastas 
WHERE Valor_Num > 0
"""
df = pd.read_sql_query(query, conn)
conn.close()

if df.empty:
    print("No hay datos válidos suficientes para generar estadísticas.")
else:
    print("2. Procesando el panel analítico cruzado...")
    
    # GRÁFICO 1: Precio Medio de Tasación por Provincia
    df_precio = df.groupby("Provincia", as_index=False)["Valor_Num"].mean().sort_values(by="Valor_Num", ascending=False)
    df_precio["Valor_Num"] = df_precio["Valor_Num"].round(2)
    fig1 = px.bar(df_precio, x="Provincia", y="Valor_Num", 
                  title="1. Precio Medio de Tasación por Provincia", 
                  labels={"Valor_Num": "Precio Medio (€)", "Provincia": ""},
                  color_discrete_sequence=['#1f77b4'])

    # GRÁFICO 2: Volumen de Oportunidades (Liquidez del mercado)
    df_volumen = df.groupby("Provincia", as_index=False).size().rename(columns={"size": "Cantidad"}).sort_values(by="Cantidad", ascending=False)
    fig2 = px.bar(df_volumen, x="Provincia", y="Cantidad", 
                  title="2. Volumen de Subastas Activas (Liquidez del mercado)", 
                  labels={"Cantidad": "Nº de Expedientes", "Provincia": ""},
                  color_discrete_sequence=['#ff7f0e'])

    # GRÁFICO 3: Barrera de Entrada (Depósito medio exigido)
    df_deposito = df.groupby("Provincia", as_index=False)["Deposito_Num"].mean().sort_values(by="Deposito_Num", ascending=False)
    df_deposito["Deposito_Num"] = df_deposito["Deposito_Num"].round(2)
    fig3 = px.bar(df_deposito, x="Provincia", y="Deposito_Num", 
                  title="3. Barrera de Entrada: Depósito Medio Exigido", 
                  labels={"Deposito_Num": "Depósito Medio (€)", "Provincia": ""},
                  color_discrete_sequence=['#2ca02c'])

    print("3. Ensamblando el Dashboard en HTML...")
    # Escribimos los tres gráficos en una sola página web profesional interactiva
    nombre_archivo = "dashboard_analitico.html"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write("<html><head><title>Inteligencia de Mercado DaaS</title></head><body style='font-family: Arial; padding: 20px; background-color: #f8f9fa;'>")
        f.write("<h1 style='text-align: center; color: #333;'>Panel Analítico: Mercado de Subastas Nacional</h1>")
        
        # Inyectamos los gráficos interactivos de Plotly
        f.write(fig1.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write(fig2.to_html(full_html=False, include_plotlyjs=False)) 
        f.write(fig3.to_html(full_html=False, include_plotlyjs=False))
        
        f.write("</body></html>")

    print(f"¡Éxito! El Dashboard completo se ha generado en: '{nombre_archivo}'.") 