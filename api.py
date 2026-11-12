from fastapi import FastAPI, Query
import json
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
    return {"mensaje": "API Inmobiliaria Nacional Activa. Visita /docs para el panel interactivo."}

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
    ordenar_por: Optional[str] = Query("precio", description="Opciones: precio, deposito"),
    orden: Optional[str] = Query("asc", description="Opciones: asc, desc")
):
    nombre_archivo = "subastas_nacionales.json" 
    
    if not os.path.exists(nombre_archivo):
        return {"error": f"Base de datos no encontrada. Se buscó: {nombre_archivo}"}
        
    with open(nombre_archivo, "r", encoding="utf-8") as archivo:
        resultados = json.load(archivo)

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
        
    # 4. Filtro por Tipo de Inmueble, Origen y Localidad (Conectados al nuevo motor)
    if tipo_inmueble is not None:
        resultados = [s for s in resultados if normalizar(tipo_inmueble) in normalizar(s.get("Bien_Tipo", ""))]
    if origen is not None:
        resultados = [s for s in resultados if normalizar(origen) in normalizar(s.get("Origen", ""))]
    if localidad is not None:
        resultados = [s for s in resultados if normalizar(localidad) in normalizar(s.get("Localidad", ""))]
        
    # 5. Filtro por Provincia (Búsqueda insensible a tildes)
    if provincia is not None:
        prov_busqueda = normalizar(provincia)
        resultados = [s for s in resultados if prov_busqueda in normalizar(s.get("Provincia", "")) or prov_busqueda in normalizar(str(s))]

    # 6. Ordenación Dinámica
    reverso = True if orden.lower() == "desc" else False
    
    if ordenar_por.lower() == "deposito":
        resultados = sorted(resultados, key=lambda x: x.get("Deposito_Num", float('inf')), reverse=reverso)
    else: 
        resultados = sorted(resultados, key=lambda x: x.get("Valor_Num", float('inf')), reverse=reverso)

    return {
        "total_resultados": len(resultados),
        "datos": resultados
    } 