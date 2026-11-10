from bs4 import BeautifulSoup

print("Analizando el expediente HTML guardado en tu disco duro...")

# 1. Abrimos tu archivo local
with open("subasta_detalle.html", "r", encoding="utf-8") as archivo:
    sopa = BeautifulSoup(archivo, "html.parser")

# 2. Localizamos todas las filas <tr> del documento
filas = sopa.find_all("tr")

# 3. Creamos un diccionario (una caja organizadora) para emparejar los datos
datos_inmueble = {}

# 4. El motor de extracción
for fila in filas:
    titulo = fila.find("th")
    valor = fila.find("td")
    
    # Freno de seguridad: Si la fila tiene tanto un título como un valor, lo procesamos
    if titulo and valor:
        # .strip() elimina tabulaciones, espacios y saltos de línea invisibles del HTML
        clave_limpia = titulo.text.strip()
        valor_limpio = valor.text.strip()
        
        # Metemos la pareja de datos en nuestra caja
        datos_inmueble[clave_limpia] = valor_limpio

# 5. Imprimimos por pantalla solo los "Datos de Oro" que importan al cliente
print("\n--- INFORME LIMPIO DEL INMUEBLE ---")
print(f"ID Subasta: {datos_inmueble.get('Identificador', 'No especificado')}")
print(f"Tipo: {datos_inmueble.get('Tipo de subasta', 'No especificado')}")
print(f"Valor Subasta: {datos_inmueble.get('Valor subasta', 'No especificado')}")
print(f"Depósito necesario: {datos_inmueble.get('Importe del depósito', 'No especificado')}")
print("-----------------------------------") 