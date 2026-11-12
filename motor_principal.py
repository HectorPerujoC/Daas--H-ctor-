"""
Rastreador de subastas inmobiliarias del BOE -> SQLite + JSON
Versión Definitiva: Paginación + Troceado + Extracción Profunda + Exportación API
"""
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE_URL = "https://subastas.boe.es/"
FORM_URL = urljoin(BASE_URL, "subastas_ava.php")
DB_FILE = "historico_subastas.db"
JSON_FILE = "subastas_nacionales.json"

# --- Ajustes ---
PAGE_HITS = 50                  
DIAS_ATRAS = 15                 
DIAS_ADELANTE = 180             
FORMATO_FECHA_BOE = "%d-%m-%Y"  
PAUSA_PAGINA = 2                
PAUSA_BUSQUEDA = 2              
PAUSA_DETALLE = 1               
# ---------------

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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

def pedir(sesion, metodo, url, intentos=3, **kwargs):
    for n in range(1, intentos + 1):
        try:
            r = sesion.request(metodo, url, timeout=30, **kwargs)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if n == intentos: raise
            time.sleep(3 * n)

def investigar_inmueble_oculto(sesion, url_original):
    url_bienes = url_original.replace("ver=1", "ver=3") if "ver=" in url_original else f"{url_original}&ver=3"
    try:
        res = pedir(sesion, "GET", url_bienes, headers={"Referer": url_original})
        sopa = BeautifulSoup(res.text, "html.parser")
        datos = {}
        for fila in sopa.find_all("tr"):
            th = fila.find("th")
            td = fila.find("td")
            if th and td:
                datos[th.get_text(strip=True)] = td.get_text(" ", strip=True)

        tipo = datos.get("Tipo de bien", "")
        desc = datos.get("Descripción", "")
        localidad = datos.get("Localidad", datos.get("Municipio", ""))

        texto_completo = f"{tipo} - {desc}".strip(" -")
        texto_limpio = texto_completo[:160] if texto_completo else "No disponible"
        return texto_limpio, (localidad if localidad else "No disponible")
    except Exception:
        return "No disponible", "No disponible"

def construir_post(cod_prov, desde="", hasta=""):
    return [
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
        ("dato[17][0]", desde), ("dato[17][1]", hasta),
        ("campo[18]", "SUBASTA.FECHA_INICIO"),
        ("dato[18][0]", ""), ("dato[18][1]", ""),
        ("page_hits", str(PAGE_HITS)),
        ("sort_field[0]", "SUBASTA.FECHA_FIN"),
        ("sort_order[0]", "asc"),
        ("accion", "Buscar")
    ]

def buscar_siguiente(sopa):
    for a in sopa.find_all("a", href=True):
        texto = a.get_text(" ", strip=True).lower()
        titulo = (a.get("title") or "").lower()
        if "siguiente" in texto or "siguiente" in titulo: return a
    return None

def recopilar_enlaces(sesion, cod_prov, desde="", hasta=""):
    cabeceras_post = HEADERS.copy()
    cabeceras_post["Referer"] = FORM_URL
    cabeceras_post["Origin"] = "https://subastas.boe.es"

    resp = pedir(sesion, "POST", FORM_URL, data=construir_post(cod_prov, desde, hasta), headers=cabeceras_post)
    enlaces, vistas, paginas_vistas = [], set(), set()

    while True:
        sopa = BeautifulSoup(resp.text, "html.parser")
        nuevos = 0
        for a in sopa.select('a[href*="detalleSubasta.php"]'):
            enlace = urljoin(resp.url, a["href"])
            if enlace not in vistas:
                vistas.add(enlace)
                enlaces.append(enlace)
                nuevos += 1

        print(f"     -> {len(enlaces)} expedientes acumulados (+{nuevos})")
        siguiente = buscar_siguiente(sopa)
        if not siguiente: break

        url_sig = urljoin(resp.url, siguiente["href"])
        if url_sig in paginas_vistas or nuevos == 0: break
        paginas_vistas.add(url_sig)

        time.sleep(PAUSA_PAGINA)
        resp = pedir(sesion, "GET", url_sig, headers={"Referer": resp.url})

    time.sleep(PAUSA_BUSQUEDA)
    return enlaces

def parece_truncado(n):
    return n > 0 and n % PAGE_HITS == 0

def rastrear_rango(sesion, cod_prov, desde, hasta, nivel=0):
    txt_d = desde.strftime(FORMATO_FECHA_BOE)
    txt_h = hasta.strftime(FORMATO_FECHA_BOE)
    sangria = "  " * nivel

    print(f"   {sangria}[{txt_d} -> {txt_h}]")
    enlaces = recopilar_enlaces(sesion, cod_prov, txt_d, txt_h)

    if not parece_truncado(len(enlaces)): return enlaces

    dias = (hasta - desde).days
    if dias < 1:
        print(f"   {sangria}AVISO: Tope en {txt_d}. Pueden faltar expedientes.")
        return enlaces

    mitad = desde + timedelta(days=dias // 2)
    izquierda = rastrear_rango(sesion, cod_prov, desde, mitad, nivel + 1)
    derecha = rastrear_rango(sesion, cod_prov, mitad + timedelta(days=1), hasta, nivel + 1)
    return list(dict.fromkeys(enlaces + izquierda + derecha))

def enlaces_de_provincia(sesion, cod_prov):
    enlaces = recopilar_enlaces(sesion, cod_prov)
    if parece_truncado(len(enlaces)):
        print(f"     Posible tope de resultados ({len(enlaces)}). Troceando por fecha...")
        hoy = datetime.now().date()
        extra = rastrear_rango(sesion, cod_prov, hoy - timedelta(days=DIAS_ATRAS), hoy + timedelta(days=DIAS_ADELANTE))
        enlaces = list(dict.fromkeys(enlaces + extra))
    return enlaces

def guardar_subasta(sesion, cursor, enlace, nombre_prov, fecha_hoy):
    res_detalle = pedir(sesion, "GET", enlace, headers={"Referer": FORM_URL})
    sopa_detalle = BeautifulSoup(res_detalle.text, "html.parser")

    inmueble = {}
    for fila in sopa_detalle.find_all("tr"):
        th = fila.find("th")
        td = fila.find("td")
        if th and td:
            inmueble[th.text.strip()] = td.text.strip()

    identificador = inmueble.get("Identificador", "")
    if not identificador: return None

    origen = inmueble.get("Tipo de subasta", "No disponible")
    bien_tipo = inmueble.get("Bien que se subasta", inmueble.get("Tipo de bien", "No disponible"))
    localidad = inmueble.get("Localidad", inmueble.get("Municipio", "No disponible"))
    fecha_fin = inmueble.get("Fecha de conclusión", "No disponible")
    valor_num = limpiar_dinero(inmueble.get("Valor subasta", ""))
    deposito_num = limpiar_dinero(inmueble.get("Importe del depósito", ""))

    if "No disponible" in bien_tipo or not bien_tipo.strip() or "No disponible" in localidad:
        bien_oculto, loc_oculta = investigar_inmueble_oculto(sesion, enlace)
        if bien_oculto != "No disponible": bien_tipo = bien_oculto
        if loc_oculta != "No disponible": localidad = loc_oculta
        time.sleep(PAUSA_DETALLE)

    cursor.execute("SELECT Identificador FROM subastas WHERE Identificador = ?", (identificador,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE subastas
            SET Bien_Tipo = ?, Localidad = ?, Fecha_Fin = ?, Fecha_Captura = ?
            WHERE Identificador = ?
        """, (bien_tipo, localidad, fecha_fin, fecha_hoy, identificador))
        return "actualizado"

    cursor.execute("""
        INSERT INTO subastas (Identificador, Provincia, Origen, Bien_Tipo, Localidad, Fecha_Fin,
                              Valor_Num, Deposito_Num, URL_Original, Fecha_Captura)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (identificador, nombre_prov, origen, bien_tipo, localidad, fecha_fin,
          valor_num, deposito_num, enlace, fecha_hoy))
    return "nuevo"

def main():
    print("Iniciando Motor Principal DaaS (Paginación + Fechas + Bisturí + Exportador JSON)...")
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    sesion.get(FORM_URL, timeout=30)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subastas (
            Identificador TEXT PRIMARY KEY,
            Provincia TEXT,
            Origen TEXT,
            Bien_Tipo TEXT,
            Localidad TEXT,
            Fecha_Fin TEXT,
            Valor_Num REAL,
            Deposito_Num REAL,
            URL_Original TEXT,
            Fecha_Captura TEXT
        )
    ''')

    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    nuevos_registros = 0
    actualizados = 0

    try:
        for cod_prov, nombre_prov in PROVINCIAS_BOE.items():
            print(f"\n--- Rastreando Provincia: {nombre_prov} ---")
            try:
                enlaces = enlaces_de_provincia(sesion, cod_prov)
            except Exception as e:
                print(f"!!! Error de conexión en {nombre_prov}: {e}. Saltando...")
                time.sleep(3)
                continue

            print(f"    Total en {nombre_prov}: {len(enlaces)} expedientes. Leyendo fichas...")

            for enlace in enlaces:
                try:
                    resultado = guardar_subasta(sesion, cursor, enlace, nombre_prov, fecha_hoy)
                    if resultado == "nuevo": nuevos_registros += 1
                    elif resultado == "actualizado": actualizados += 1
                except Exception:
                    pass
                time.sleep(PAUSA_DETALLE)

            conn.commit()
            time.sleep(3)
            
    finally:
        conn.commit()
        
        # --- EXTRACCIÓN A JSON PARA LA API ---
        print("\nEmpaquetando base de datos completa para la API...")
        try:
            df = pd.read_sql_query("SELECT * FROM subastas", conn)
            df.to_json(JSON_FILE, orient="records", force_ascii=False, indent=4)
            print(f"✅ JSON '{JSON_FILE}' actualizado con {len(df)} expedientes listos para la API.")
        except Exception as e:
            print(f"Error al generar el JSON: {e}")
            
        conn.close()

    print(f"\n✅ RASTREO FINALIZADO. {nuevos_registros} subastas nuevas guardadas, {actualizados} actualizadas.")

if __name__ == "__main__": 
    main() 