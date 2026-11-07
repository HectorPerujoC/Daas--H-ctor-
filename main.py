import requests
from bs4 import BeautifulSoup
import pandas as pd  # Importamos Pandas y le damos el apodo "pd"

url = "http://quotes.toscrape.com/"
respuesta = requests.get(url)
sopa = BeautifulSoup(respuesta.text, "html.parser")
cajas_de_citas = sopa.find_all("div", class_="quote")

# 1. Creamos una lista vacía para ir guardando los datos (como una caja vacía)
datos_extraidos = []

for caja in cajas_de_citas:
    texto = caja.find("span", class_="text").text
    autor = caja.find("small", class_="author").text
    
    # 2. En lugar de imprimir, metemos cada fila en nuestra "caja"
    datos_extraidos.append({
        "Autor": autor,
        "Cita": texto
    })

# 3. La magia de Pandas: Convertimos la lista en una tabla profesional (DataFrame)
tabla_datos = pd.DataFrame(datos_extraidos)

# 4. Exportamos esa tabla a archivos reales en tu ordenador
tabla_datos.to_csv("datos_limpios.csv", index=False, encoding="utf-8")
tabla_datos.to_json("datos_limpios.json", orient="records", force_ascii=False, indent=4)

print("¡Extracción terminada! Revisa el panel izquierdo de tu VS Code.")