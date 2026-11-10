import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

todos_los_registros = []
numero_pagina = 1

print("Iniciando motor de extracción dinámica...")

while True:
    url = f"https://www.scrapethissite.com/pages/forms/?page_num={numero_pagina}"
    respuesta = requests.get(url)
    sopa = BeautifulSoup(respuesta.text, "html.parser")
    
    # 1. Buscamos las filas
    filas_tabla = sopa.find_all("tr", class_="team")
    
    # 2. Freno de emergencia real: Si no hay filas, se acabó la información
    if len(filas_tabla) == 0:
        print(f"Página {numero_pagina} vacía. Fin de los registros alcanzado.")
        break
        
    print(f"Extrayendo {len(filas_tabla)} registros de la página {numero_pagina}...")
    
    # 3. Extracción de las celdas de la tabla
    for fila in filas_tabla:
        nombre = fila.find("td", class_="name").text.strip()
        año = fila.find("td", class_="year").text.strip()
        victorias = fila.find("td", class_="wins").text.strip()
        
        todos_los_registros.append({
            "Entidad": nombre,
            "Año_Registro": año,
            "Operaciones": victorias
        })
        
    numero_pagina += 1
    
    # 4. Freno de seguridad temporal para la prueba (corta en la página 5)
    if numero_pagina > 5:
        print("Freno de seguridad de prueba activado.")
        break
        
    time.sleep(2) # Pausa ética de 2 segundos para no saturar el servidor

tabla_final = pd.DataFrame(todos_los_registros)
tabla_final.to_csv("registro_dinamico.csv", index=False)
print(f"\n¡Proceso finalizado! Total extraído: {len(tabla_final)} registros.") 