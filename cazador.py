import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9"
}

def inspeccionar_pestana_bienes(url_original: str):
    """Entra en la pestaña 'Bienes' (&ver=3) del BOE para descubrir qué inmueble es realmente."""
    url_bienes = url_original.replace("ver=1", "ver=3") if "ver=" in url_original else f"{url_original}&ver=3"
    
    try:
        res = requests.get(url_bienes, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return None, None
            
        sopa = BeautifulSoup(res.text, "html.parser")
        datos = {}
        for fila in sopa.find_all("tr"):
            th = fila.find("th")
            td = fila.find("td")
            if th and td:
                datos[th.get_text(strip=True)] = td.get_text(" ", strip=True)
                
        tipo = datos.get("Tipo de bien", "")
        desc = datos.get("Descripción", "")
        localidad = datos.get("Localidad", datos.get("Municipio", ""))
        
        texto_completo = f"{tipo} - {desc}".strip(" -")
        texto_limpio = texto_completo[:160] if texto_completo else None
        return texto_limpio, (localidad if localidad else None)
    except Exception:
        return None, None

def buscar_chollos(tope_vivienda: float, tope_garaje: float):
    nombre_db = "historico_subastas.db"
    conn = sqlite3.connect(nombre_db)
    
    presupuesto_maximo = max(tope_vivienda, tope_garaje)
    
    # FASE 1: Pre-filtro rápido en SQLite por presupuesto y frescura
    query = """
    SELECT Identificador, Provincia, Localidad, Bien_Tipo, Valor_Num, Deposito_Num, URL_Original
    FROM subastas 
    WHERE Fecha_Captura >= date('now', '-1 day')
      AND Valor_Num > 0 
      AND Valor_Num <= ?
    """
    df = pd.read_sql_query(query, conn, params=(presupuesto_maximo,))

    if df.empty:
        conn.close()
        print("No hay subastas nuevas dentro de ese rango de presupuesto.")
        return

    print(f"🔎 Pre-seleccionadas {len(df)} subastas dentro de presupuesto. Verificando qué activo es cada una...\n")

    # FASE 2: Enriquecimiento bajo demanda para los expedientes "No disponible"
    cursor = conn.cursor()
    actualizados = 0
    
    for idx, row in df.iterrows():
        bien_actual = str(row['Bien_Tipo'])
        if "No disponible" in bien_actual or not bien_actual.strip():
            nuevo_bien, nueva_loc = inspeccionar_pestana_bienes(row['URL_Original'])
            if nuevo_bien:
                df.at[idx, 'Bien_Tipo'] = nuevo_bien
                loc_final = nueva_loc if nueva_loc else row['Localidad']
                df.at[idx, 'Localidad'] = loc_final
                
                # Guardamos el hallazgo en SQLite para enriquecer la base de datos permanentemente
                cursor.execute(
                    "UPDATE subastas SET Bien_Tipo = ?, Localidad = ? WHERE Identificador = ?",
                    (nuevo_bien, loc_final, row['Identificador'])
                )
                actualizados += 1
            time.sleep(0.8)

    if actualizados > 0:
        conn.commit()
        print(f"💾 Base de datos enriquecida: {actualizados} expedientes misteriosos ya tienen descripción real.\n")
    conn.close()

    # FASE 3: Clasificación quirúrgica
    palabras_vivienda = r'VIVIENDA|PISO|CASA|CHALET|APARTAMENTO|ATICO|ÁTICO|DUPLEX|DÚPLEX|UNIFAMILIAR'
    palabras_trampa = r'TRASTERO|GARAJE|APARCAMIENTO|SOLAR|RUSTICA|RÚSTICA|NAVE|LOCAL|NUDA PROPIEDAD|MITAD INDIVISA|PARTICIPACI'
    
    # Redefinición estricta para garajes
    palabras_garaje = r'GARAJE|APARCAMIENTO|PLAZA'
    trampas_garaje = r'VIVIENDA|PISO|NAVE|LOCAL|TRASTERO|ANEJO|CUOTA|INDIVISA|%|PORCENTAJE|RUSTICA'

    chollos_vivienda = df[
        (df['Bien_Tipo'].str.contains(palabras_vivienda, case=False, na=False, regex=True)) &
        (~df['Bien_Tipo'].str.contains(palabras_trampa, case=False, na=False, regex=True)) &
        (df['Valor_Num'] <= tope_vivienda)
    ]

    chollos_garaje = df[
        (df['Bien_Tipo'].str.contains(palabras_garaje, case=False, na=False, regex=True)) &
        (~df['Bien_Tipo'].str.contains(trampas_garaje, case=False, na=False, regex=True)) &
        (df['Valor_Num'] > 2500) &  # Suelo anti-basura: Elimina participaciones minúsculas y fracciones
        (df['Valor_Num'] <= tope_garaje)
    ]

    total = len(chollos_vivienda) + len(chollos_garaje)
    
    if total == 0:
        print("Hoy no ha saltado ninguna alarma tras verificar el tipo real de cada inmueble.")
    else:
        print(f"🚨 ¡ALERTA VERIFICADA! {total} oportunidades reales detectadas 🚨\n")
        
        if not chollos_vivienda.empty:
            print("--- 🏠 VIVIENDAS REALES EN RANGO ---")
            for _, r in chollos_vivienda.iterrows():
                print(f"📍 {r['Provincia']} ({r['Localidad']}) | 💰 {r['Valor_Num']}€")
                print(f"   📝 {r['Bien_Tipo']}")
                print(f"   🔗 {r['URL_Original']}\n")
                
        if not chollos_garaje.empty:
            print("--- 🚗 GARAJES VERIFICADOS EN RANGO ---")
            for _, r in chollos_garaje.iterrows():
                print(f"📍 {r['Provincia']} ({r['Localidad']}) | 💰 {r['Valor_Num']}€")
                print(f"   📝 {r['Bien_Tipo']}")
                print(f"   🔗 {r['URL_Original']}\n")

if __name__ == "__main__":
    buscar_chollos(tope_vivienda=120000, tope_garaje=6000) 