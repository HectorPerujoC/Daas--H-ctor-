import sqlite3
import pandas as pd

def buscar_chollos(tope_vivienda: float, tope_garaje: float):
    conn = sqlite3.connect("historico_subastas.db")
    
    # Extraemos solo las subastas de las últimas 24h
    query = """
    SELECT Identificador, Provincia, Localidad, Bien_Tipo, Valor_Num, Deposito_Num, URL_Original
    FROM subastas 
    WHERE Fecha_Captura >= date('now', '-1 day')
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("El radar está limpio. No hay subastas nuevas hoy para analizar.")
        return

    print(f"🔍 Analizando {len(df)} subastas recientes (con los 'No disponible' ya resueltos por el motor)...\n")

    # Reglas Matemáticas y de Texto (Ahora el texto siempre es real)
    palabras_vivienda = r'VIVIENDA|PISO|CASA|CHALET|APARTAMENTO|ATICO|ÁTICO|DUPLEX|DÚPLEX|UNIFAMILIAR'
    palabras_trampa = r'TRASTERO|GARAJE|APARCAMIENTO|SOLAR|RUSTICA|RÚSTICA|NAVE|LOCAL|NUDA PROPIEDAD|MITAD INDIVISA|PARTICIPACI'
    palabras_garaje = r'GARAJE|APARCAMIENTO|PLAZA'

    chollos_vivienda = df[
        (df['Bien_Tipo'].str.contains(palabras_vivienda, case=False, na=False, regex=True)) &
        (~df['Bien_Tipo'].str.contains(palabras_trampa, case=False, na=False, regex=True)) &
        (df['Valor_Num'] > 0) & 
        (df['Valor_Num'] <= tope_vivienda)
    ]

    chollos_garaje = df[
        (df['Bien_Tipo'].str.contains(palabras_garaje, case=False, na=False, regex=True)) &
        (~df['Bien_Tipo'].str.contains(r'VIVIENDA|PISO|NAVE|LOCAL', case=False, na=False, regex=True)) &
        (df['Valor_Num'] > 0) & 
        (df['Valor_Num'] <= tope_garaje)
    ]

    total = len(chollos_vivienda) + len(chollos_garaje)
    
    if total == 0:
        print("Hoy no ha saltado la alarma para este perfil de presupuesto.")
    else:
        print(f"🚨 ¡ALERTA! Detectadas {total} oportunidades de inversión reales 🚨\n")
        
        for _, r in chollos_vivienda.iterrows():
            print(f"🏠 VIVIENDA: {r['Provincia']} ({r['Localidad']}) | 💰 {r['Valor_Num']}€ | 📝 {r['Bien_Tipo'][:60]}... | 🔗 {r['URL_Original']}")
            
        for _, r in chollos_garaje.iterrows():
            print(f"🚗 GARAJE: {r['Provincia']} ({r['Localidad']}) | 💰 {r['Valor_Num']}€ | 📝 {r['Bien_Tipo'][:60]}... | 🔗 {r['URL_Original']}")

if __name__ == "__main__":
    buscar_chollos(tope_vivienda=120000, tope_garaje=15000) 