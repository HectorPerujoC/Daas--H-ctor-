from fastapi import FastAPI
import json

# 1. Creamos la aplicación (tu "tienda" virtual)
app = FastAPI()

# 2. Creamos la puerta principal (la ruta de bienvenida)
@app.get("/")
def bienvenida():
    return {"mensaje": "¡Hola! Esta es mi primera API comercial."}

# 3. Creamos el escaparate de los datos
@app.get("/citas")
def entregar_datos():
    # Leemos el archivo JSON que creaste en el paso anterior
    with open("datos_limpios.json", "r", encoding="utf-8") as archivo:
        datos_guardados = json.load(archivo)
    
    # Se los entregamos a quien visite esta URL
    return datos_guardados