from fastapi import FastAPI, Query
import sqlite3
import os
import unicodedata
from typing import Optional

app = FastAPI(title="Radar de Subastas Inmobiliarias DaaS")

def normalizar(texto: str) -> str:
    """Elimina tildes y convierte a mayúsculas para búsquedas flexibles."""
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFD', str(texto))
    sin_tildes = ''.join(c for c in texto_norm if unicodedata.category(c) != 'Mn')
    return sin_tildes.upper()

@app.get("/")
def bienvenida():
    return {"mensaje": "API Inmobiliaria Nacional Activa conectada al Histórico. Visita /docs para el panel interactivo."}

@app.get("/subastas")
def buscar_subastas(
    provincia: Optional[str] = Query(None, description="Ej: Alicante, Barcelona, Almeria, Madrid"),
    localidad: Optional[str] = Query(None, description="Ej: Marbella, Elche, Alcalá"),
    precio_min: Optional[float] = Query(None, description="Valor mínimo de subasta"),
    precio_max: Optional[float] = Query(None, description="Valor máximo de subasta"),
    deposito_max: Optional[float] = Query(None, description="Depósito máximo exigido"),
    tipo_inmueble: Optional[str] = Query(None, description="Ej: VIVIENDA, GARAJE, LOCAL"),
    origen: Optional[str] = Query(None, description="Ej: Judicial, AEAT, Recaudacion"),
    ticket_bajo: Optional[bool] = Query(False, description="Muestra solo inmuebles con valor <= 50.000€"),
    ultimas_24h: Optional[bool] = Query(False, description="Mostrar solo subastas capturadas en las últimas 24 horas"),
    ordenar_por: Optional[str] = Query("precio", description="Opciones: precio, deposito"),
    orden: Optional[str] = Query("asc", description="Opciones: asc, desc")
):
    nombre_db = "historico_subastas.db" 
    
    if not os.path.exists(nombre_db):
        return {"error": f"Base de datos no encontrada. Se buscó: {nombre_db}"}
        
    # --- CONEXIÓN AL CEREBRO SQLITE ---
    conn = sqlite3.connect(nombre_db)
    conn.row_factory = sqlite3.Row # Permite acceder a las columnas por nombre
    cursor = conn.cursor()
    
    # Filtro nativo ultra-rápido en base de datos para novedades
    if ultimas_24h:
        cursor.execute("SELECT * FROM subastas WHERE Fecha_Captura >= date('now', '-1 day')")
    else:
        cursor.execute("SELECT * FROM subastas")
        
    # Convertimos los resultados a una lista de diccionarios para el motor de Python
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # --- MOTOR DE FILTRADO EN MEMORIA (El mismo que ya dominas) ---
    
    # 1. Atajo "Ticket Bajo"
    if ticket_bajo:
        resultados = [s for s in resultados if s.get("Valor_Num") is not None and s.get("Valor_Num") <= 50000]

    # 2. Filtros de Precio (Mínimo y Máximo)
    if precio_min is not None:
        resultados = [s for s in resultados if s.get("Valor_Num") is not None and s.get("Valor_Num") >= precio_min]
    if precio_max is not None:
        resultados = [s for s in resultados if s.get("Valor_Num") is not None and s.get("Valor_Num") <= precio_max]
        
    # 3. Filtro por Depósito Máximo
    if deposito_max is not None:
        resultados = [s for s in resultados if s.get("Deposito_Num") is not None and s.get("Deposito_Num") <= deposito_max]
        
    # 4. Filtro por Tipo de Inmueble, Origen y Localidad
    if tipo_inmueble is not None:
        resultados = [s for s in resultados if normalizar(tipo_inmueble) in normalizar(s.get("Bien_Tipo", ""))]
    if origen is not None:
        resultados = [s for s in resultados if normalizar(origen) in normalizar(s.get("Origen", ""))]
    if localidad is not None:
        resultados = [s for s in resultados if normalizar(localidad) in normalizar(s.get("Localidad", ""))]
        
    # 5. Filtro por Provincia
    if provincia is not None:
        prov_busqueda = normalizar(provincia)
        resultados = [s for s in resultados if prov_busqueda in normalizar(s.get("Provincia", "")) or prov_busqueda in normalizar(str(s))]

    # 6. Ordenación Dinámica
    reverso = True if orden.lower() == "desc" else False

    if ordenar_por.lower() == "deposito":
        resultados = sorted(resultados, key=lambda x: (x.get("Deposito_Num") or float('inf')), reverse=reverso)
    else: 
        resultados = sorted(resultados, key=lambda x: (x.get("Valor_Num") or float('inf')), reverse=reverso)

    return {
        "total_resultados": len(resultados),
        "datos": resultados
    } 