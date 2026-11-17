from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
from typing import Optional

app = FastAPI(title="HYENA | Terminal de Inteligencia de Datos")

# --- CONFIGURACIÓN CORS (Permite que la web de HYENA lea esta API) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción puedes restringirlo a tu dominio final (ej. https://hyena.es)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.get("/")
def bienvenida():
    return {
        "marca": "HYENA Data Intelligence",
        "estado": "Operativo",
        "modulos_activos": ["Subastas BOE Nacional"],
        "documentacion": "/docs"
    }

@app.get("/subastas")
def buscar_subastas(
    provincia: Optional[str] = Query(None, description="Ej: Alicante, Barcelona, Madrid"),
    localidad: Optional[str] = Query(None, description="Ej: Marbella, Elche, Alcalá"),
    precio_min: Optional[float] = Query(None, description="Valor mínimo de subasta"),
    precio_max: Optional[float] = Query(None, description="Valor máximo de subasta"),
    deposito_max: Optional[float] = Query(None, description="Depósito máximo exigido"),
    tipo_inmueble: Optional[str] = Query(None, description="Ej: VIVIENDA, GARAJE, LOCAL"),
    origen: Optional[str] = Query(None, description="Ej: Judicial, Agencia Tributaria"),
    solo_hoy: Optional[bool] = Query(False, description="Muestra solo las capturadas en las últimas 24h"),
    ordenar_por: Optional[str] = Query("precio", description="Opciones: precio, deposito"),
    orden: Optional[str] = Query("asc", description="Opciones: asc, desc")
):
    if not os.path.exists("historico_subastas.db"):
        return {"error": "Base de datos SQLite no encontrada."}

    conn = sqlite3.connect("historico_subastas.db")
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    query = "SELECT * FROM subastas WHERE 1=1"
    params = []

    if provincia:
        query += " AND Provincia LIKE ?"
        params.append(f"%{provincia}%")
    if localidad:
        query += " AND Localidad LIKE ?"
        params.append(f"%{localidad}%")
    if tipo_inmueble:
        query += " AND Bien_Tipo LIKE ?"
        params.append(f"%{tipo_inmueble}%")
    if origen:
        query += " AND Origen LIKE ?"
        params.append(f"%{origen}%")

    if precio_min is not None:
        query += " AND Valor_Num >= ?"
        params.append(precio_min)
    if precio_max is not None:
        query += " AND Valor_Num <= ?"
        params.append(precio_max)
    if deposito_max is not None:
        query += " AND Deposito_Num <= ?"
        params.append(deposito_max)

    if solo_hoy:
        query += " AND Fecha_Captura >= date('now', '-1 day')"

    col_orden = "Deposito_Num" if ordenar_por.lower() == "deposito" else "Valor_Num"
    dir_orden = "DESC" if orden.lower() == "desc" else "ASC"
    
    query += f" ORDER BY {col_orden} IS NULL, {col_orden} {dir_orden}"

    cursor.execute(query, params)
    resultados = cursor.fetchall()
    conn.close()

    return {
        "total_resultados": len(resultados),
        "datos": resultados
    } 