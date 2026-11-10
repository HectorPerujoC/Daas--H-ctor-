from fastapi import FastAPI
import json
import os

app = FastAPI(title="Radar de Subastas Inmobiliarias DaaS")

@app.get("/")
def bienvenida():
    return {"mensaje": "API Inmobiliaria Activa. Visita /subastas/madrid para obtener el JSON depurado, o /docs para ver el panel de control."}

@app.get("/subastas/madrid")
def entregar_subastas_madrid():
    # AHORA APUNTAMOS AL ARCHIVO DEPURADO POR EL LIMPIADOR
    nombre_archivo = "subastas_madrid_limpias.json"
    
    if not os.path.exists(nombre_archivo):
        return {"error": f"Aún no se ha generado la base de datos. Se buscó el archivo: {nombre_archivo}"}
        
    with open(nombre_archivo, "r", encoding="utf-8") as archivo:
        datos_guardados = json.load(archivo)
        
    return datos_guardados  