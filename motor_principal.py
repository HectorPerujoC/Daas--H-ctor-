import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urljoin

BASE_URL = "https://subastas.boe.es/"
FORM_URL = urljoin(BASE_URL, "subastas_ava.php")
PROVINCIA = "28"  # Madrid

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9"
}

def limpiar_dinero(valor):
    if not isinstance(valor, str): return valor
    if "€" not in valor: return None
    valor = valor.replace("€", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except:
        return None

print("Iniciando Motor Principal DaaS...")
sesion = requests.Session()
sesion.headers.update(HEADERS)

# --- FASE 1: RASTREO DINÁMICO (MATRIZ CALIBRADA) ---
print("\n1. Obteniendo cookies de sesión del BOE...")
sesion.get(FORM_URL)

datos_post = [
    ("campo[0]", "SUBASTA.ORIGEN"),                      ("dato[0]", ""),
    ("campo[1]", "SUBASTA.AUTORIDAD"),                   ("dato[1]", ""),
    ("campo[2]", "SUBASTA.ESTADO.CODIGO"),               ("dato[2]", "EJ"),   # Celebrándose
    ("campo[3]", "BIEN.TIPO"),                           ("dato[3]", "I"),    # Inmuebles
    ("dato[4]", ""),
    ("campo[5]", "BIEN.DIRECCION"),                      ("dato[5]", ""),
    ("campo[6]", "BIEN.CODPOSTAL"),                      ("dato[6]", ""),
    ("campo[7]", "BIEN.LOCALIDAD"),                      ("dato[7]", ""),
    ("campo[8]", "BIEN.COD_PROVINCIA"),                  ("dato[8]", PROVINCIA),   
    ("campo[9]", "SUBASTA.POSTURA_MINIMA_MINIMA_LOTES"), ("dato[9]", ""),
    ("campo[10]", "SUBASTA.NUM_CUENTA_EXPEDIENTE_1"),    ("dato[10]", ""),
    ("campo[11]", "SUBASTA.NUM_CUENTA_EXPEDIENTE_2"),    ("dato[11]", ""),
    ("campo[12]", "SUBASTA.NUM_CUENTA_EXPEDIENTE_3"),    ("dato[12]", ""),
    ("campo[13]", "SUBASTA.NUM_CUENTA_EXPEDIENTE_4"),    ("dato[13]", ""),
    ("campo[14]", "SUBASTA.NUM_CUENTA_EXPEDIENTE_5"),    ("dato[14]", ""),
    ("campo[15]", "SUBASTA.ID_SUBASTA_BUSCAR"),          ("dato[15]", ""),
    ("campo[16]", "SUBASTA.ACREEDORES"),                 ("dato[16]", ""),
    ("campo[17]", "SUBASTA.FECHA_FIN"),
    ("dato[17][0]", ""), ("dato[17][1]", ""),
    ("campo[18]", "SUBASTA.FECHA_INICIO"),
    ("dato[18][0]", ""), ("dato[18][1]", ""),
    ("page_hits", "500"),
    ("sort_field[0]", "SUBASTA.FECHA_FIN"),
    ("sort_order[0]", "asc"),
    ("accion", "Buscar")
]

cabeceras_post = HEADERS.copy()
cabeceras_post["Referer"] = FORM_URL
cabeceras_post["Origin"] = "https://subastas.boe.es"

print("2. Descargando listado de subastas activas de Madrid...")
respuesta_post = sesion.post(FORM_URL, data=datos_post, headers=cabeceras_post)
sopa_resultados = BeautifulSoup(respuesta_post.text, "html.parser")

enlaces_inmuebles = []
for a in sopa_resultados.select('a[href*="detalleSubasta.php"]'):
    enlace_completo = urljoin(BASE_URL, a["href"])
    if enlace_completo not in enlaces_inmuebles:
        enlaces_inmuebles.append(enlace_completo)

print(f"¡Éxito! {len(enlaces_inmuebles)} subastas localizadas.")

# --- FASE 2: EXTRACCIÓN AL DETALLE ---
datos_brutos = []
if len(enlaces_inmuebles) > 0:
    for i, enlace in enumerate(enlaces_inmuebles, 1):
        print(f"   -> Procesando expediente {i} de {len(enlaces_inmuebles)}...")
        res_detalle = sesion.get(enlace, headers={"Referer": respuesta_post.url})
        sopa_detalle = BeautifulSoup(res_detalle.text, "html.parser")
        
        filas = sopa_detalle.find_all("tr")
        inmueble = {} 
        for fila in filas:
            titulo = fila.find("th")
            valor = fila.find("td")
            if titulo and valor:
                inmueble[titulo.text.strip()] = valor.text.strip()
                
        datos_brutos.append({
            "Identificador": inmueble.get("Identificador", "No disponible"),
            "Tipo": inmueble.get("Tipo de subasta", "No disponible"),
            "Valor_Subasta": inmueble.get("Valor subasta", "No disponible"),
            "Deposito": inmueble.get("Importe del depósito", "No disponible"),
            "URL_Original": enlace
        })
        time.sleep(2)  

# --- FASE 3: REFINERÍA Y EMPAQUETADO FINAL ---
print("\n3. Limpiando datos con Pandas y exportando JSON comercial...")

if len(datos_brutos) > 0:
    df = pd.DataFrame(datos_brutos)
    
    # Transformación matemática
    df["Valor_Num"] = df["Valor_Subasta"].apply(limpiar_dinero)
    df["Deposito_Num"] = df["Deposito"].apply(limpiar_dinero)
    df_limpio = df.dropna(subset=["Valor_Num"])
    
    # Guardamos el archivo final 
    df_limpio.to_json("subastas_madrid_limpias.json", orient="records", force_ascii=False, indent=4)
    print(f"¡PIPELINE COMPLETADO! Base de datos actualizada con {len(df_limpio)} expedientes listos para la API.")
else:
    print("El rastreo no obtuvo enlaces válidos hoy. No se han sobrescrito los datos.")  