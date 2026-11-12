import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin

BASE_URL = "https://subastas.boe.es/"
FORM_URL = urljoin(BASE_URL, "subastas_ava.php")

# Mapa oficial de provincias del BOE (Códigos 01 a 52)
PROVINCIAS_BOE = {
    "01": "Álava", "02": "Albacete", "03": "Alicante", "04": "Almería", "05": "Ávila",
    "06": "Badajoz", "07": "Balears (Illes)", "08": "Barcelona", "09": "Burgos", "10": "Cáceres",
    "11": "Cádiz", "12": "Castellón", "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña",
    "16": "Cuenca", "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Gipuzkoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León", "25": "Lleida",
    "26": "La Rioja", "27": "Lugo", "28": "Madrid", "29": "Málaga", "30": "Murcia",
    "31": "Navarra", "32": "Ourense", "33": "Asturias", "34": "Palencia", "35": "Las Palmas",
    "36": "Pontevedra", "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria", "40": "Segovia",
    "41": "Sevilla", "42": "Soria", "43": "Tarragona", "44": "Teruel", "45": "Toledo",
    "46": "Valencia", "47": "Valladolid", "48": "Bizkaia", "49": "Zamora", "50": "Zaragoza",
    "51": "Ceuta", "52": "Melilla"
}

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

print("Iniciando Motor Principal DaaS (Nacional + Paginación Extrema + Escudo)...")
sesion = requests.Session()
sesion.headers.update(HEADERS)

# FASE 1: RASTREO DINÁMICO NACIONAL
print("\n1. Obteniendo cookies de sesión del BOE...")
sesion.get(FORM_URL)

datos_brutos_nacionales = []

for cod_prov, nombre_prov in PROVINCIAS_BOE.items():
    print(f"\n--- Rastreando Provincia: {nombre_prov} (Código {cod_prov}) ---")
    try:
        datos_post = [
            ("campo[0]", "SUBASTA.ORIGEN"),                      ("dato[0]", ""),
            ("campo[1]", "SUBASTA.AUTORIDAD"),                   ("dato[1]", ""),
            ("campo[2]", "SUBASTA.ESTADO.CODIGO"),               ("dato[2]", "EJ"),   
            ("campo[3]", "BIEN.TIPO"),                           ("dato[3]", "I"),    
            ("dato[4]", ""),
            ("campo[5]", "BIEN.DIRECCION"),                      ("dato[5]", ""),
            ("campo[6]", "BIEN.CODPOSTAL"),                      ("dato[6]", ""),
            ("campo[7]", "BIEN.LOCALIDAD"),                      ("dato[7]", ""),
            ("campo[8]", "BIEN.COD_PROVINCIA"),                  ("dato[8]", cod_prov),   
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
            ("page_hits", "500"), # ATAQUE 1: Solicitamos hasta 500 expedientes de golpe
            ("sort_field[0]", "SUBASTA.FECHA_FIN"),
            ("sort_order[0]", "asc"),
            ("accion", "Buscar")
        ]

        cabeceras_post = HEADERS.copy()
        cabeceras_post["Referer"] = FORM_URL
        cabeceras_post["Origin"] = "https://subastas.boe.es"

        respuesta = sesion.post(FORM_URL, data=datos_post, headers=cabeceras_post, timeout=15)
        enlaces_provincia = []
        
        while True:
            sopa = BeautifulSoup(respuesta.text, "html.parser")
            
            for a in sopa.select('a[href*="detalleSubasta.php"]'):
                enlace_completo = urljoin(BASE_URL, a["href"])
                if enlace_completo not in enlaces_provincia:
                    enlaces_provincia.append(enlace_completo)
                    
            # ATAQUE 2: Detector de paginación blindado (Múltiples comprobaciones)
            siguiente = sopa.find("a", string=re.compile(r"siguiente", re.I))
            if not siguiente:
                siguiente = sopa.find("a", title=re.compile(r"siguiente", re.I))
            if not siguiente:
                siguiente = sopa.find(lambda tag: tag.name == "a" and "siguiente" in tag.get_text(strip=True).lower())
            
            if not siguiente or not siguiente.get("href"):
                break 
                
            print(f"     Saltando a la página complementaria en {nombre_prov}...")
            time.sleep(2) 
            
            respuesta = sesion.get(urljoin(BASE_URL, siguiente["href"]), headers={"Referer": respuesta.url}, timeout=15)

        print(f"-> Total enlaces localizados en {nombre_prov}: {len(enlaces_provincia)}")
        
        # FASE 2: EXTRACCIÓN AL DETALLE (Bisturí enriquecido)
        if len(enlaces_provincia) > 0:
            for i, enlace in enumerate(enlaces_provincia, 1):
                res_detalle = sesion.get(enlace, headers={"Referer": respuesta.url}, timeout=15)
                sopa_detalle = BeautifulSoup(res_detalle.text, "html.parser")
                
                filas = sopa_detalle.find_all("tr")
                inmueble = {} 
                for fila in filas:
                    titulo = fila.find("th")
                    valor = fila.find("td")
                    if titulo and valor:
                        inmueble[titulo.text.strip()] = valor.text.strip()
                        
                datos_brutos_nacionales.append({
                    "Provincia": nombre_prov,
                    "Identificador": inmueble.get("Identificador", "No disponible"),
                    "Origen": inmueble.get("Tipo de subasta", "No disponible"),
                    "Bien_Tipo": inmueble.get("Bien", inmueble.get("Tipo de bien", "No disponible")),
                    "Localidad": inmueble.get("Localidad", "No disponible"),
                    "Fecha_Fin": inmueble.get("Fecha de conclusión", "No disponible"),
                    "Tasacion": inmueble.get("Valor de tasación", "No disponible"),
                    "Valor_Subasta": inmueble.get("Valor subasta", "No disponible"),
                    "Deposito": inmueble.get("Importe del depósito", "No disponible"),
                    "URL_Original": enlace
                })
                time.sleep(1)
                
        time.sleep(3) 
        
    except Exception as error_servidor:
        print(f"!!! Error de conexión en {nombre_prov}: {error_servidor}")
        print("Saltando a la siguiente provincia para no perder los datos...")
        time.sleep(3)

# FASE 3: REFINERÍA Y EMPAQUETADO FINAL
print("\n3. Limpiando datos con Pandas y exportando JSON nacional...")

if len(datos_brutos_nacionales) > 0:
    df = pd.DataFrame(datos_brutos_nacionales)
    
    df["Valor_Num"] = df["Valor_Subasta"].apply(limpiar_dinero)
    df["Deposito_Num"] = df["Deposito"].apply(limpiar_dinero)
    df["Tasacion_Num"] = df["Tasacion"].apply(limpiar_dinero)
    df_limpio = df.dropna(subset=["Valor_Num"])
    
    df_limpio.to_json("subastas_nacionales.json", orient="records", force_ascii=False, indent=4)
    print(f"¡PIPELINE NACIONAL COMPLETADO! Base de datos generada con {len(df_limpio)} expedientes totales.")
else:
    print("El rastreo no obtuvo enlaces válidos en ninguna provincia hoy.")  