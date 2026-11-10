import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://subastas.boe.es/"
FORM_URL = urljoin(BASE, "subastas_ava.php")
PROVINCIA = "28"  # Madrid

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-ES,es;q=0.9",
}

ERROR_TXT = "no puede ser mostrada"


def extraer_campos(form):
    """Devuelve los valores por defecto de todos los controles del formulario."""
    datos = {}
    for el in form.find_all(["input", "select", "textarea"]):
        name = el.get("name")
        if not name or el.has_attr("disabled"):
            continue
        tipo = (el.get("type") or "").lower()
        if el.name == "select":
            sel = el.find("option", selected=True)
            datos[name] = sel.get("value", "") if sel else ""
        elif tipo in ("checkbox", "radio"):
            if el.has_attr("checked"):
                datos[name] = el.get("value", "on")
        elif tipo in ("submit", "button", "image"):
            continue
        else:
            datos[name] = el.get("value", "")
    return datos


def localizar_select_provincia(form, valor):
    for sel in form.find_all("select"):
        for op in sel.find_all("option"):
            if op.get("value") == valor and "madrid" in op.get_text(strip=True).lower():
                return sel.get("name")
    return None


def buscar_provincia(valor=PROVINCIA, max_paginas=5):
    s = requests.Session()
    s.headers.update(HEADERS)

    r = s.get(FORM_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # El formulario de búsqueda avanzada: el que apunta a subastas_ava.php con POST
    form = next(
        (f for f in soup.find_all("form")
         if "subastas_ava" in (f.get("action") or "") and (f.get("method") or "").lower() == "post"),
        None,
    ) or soup.find("form")
    if form is None:
        raise RuntimeError("No encuentro el formulario; el HTML ha cambiado.")

    datos = extraer_campos(form)
    campo_prov = localizar_select_provincia(form, valor)
    if not campo_prov:
        raise RuntimeError("No encuentro el select de provincia. Imprime los nombres con: print(sorted(datos))")
    datos[campo_prov] = valor
    print("Campo de provincia detectado:", campo_prov)

    # Botón de envío
    submit = form.find(["input", "button"], {"type": "submit"})
    if submit is not None and submit.get("name"):
        datos[submit["name"]] = submit.get("value", "")
    else:
        datos.setdefault("accion", "Buscar")

    action = urljoin(FORM_URL, form.get("action") or FORM_URL)
    headers = {"Referer": FORM_URL, "Origin": BASE.rstrip("/")}
    print({k: v for k, v in datos.items() if k.endswith("[8]")})
    r = s.post(action, data=datos, headers=headers, timeout=30)
    r.raise_for_status()

    if ERROR_TXT in r.text:
        # Depuración: compara lo que envías con lo que hace el navegador (pestaña Red de DevTools)
        raise RuntimeError(f"El servidor rechazó los parámetros. Enviados: {datos}")

    resultados = []
    for pagina in range(max_paginas):
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select('a[href*="detalleSubasta.php"]'):
            resultados.append(urljoin(BASE, a["href"]))

        siguiente = soup.find("a", string=re.compile(r"siguiente", re.I))
        if not siguiente or not siguiente.get("href"):
            break
        time.sleep(2)  # no machacar el servidor
        r = s.get(urljoin(BASE, siguiente["href"]), headers={"Referer": r.url}, timeout=30)
        r.raise_for_status()

    return sorted(set(resultados))


if __name__ == "__main__":
    for u in buscar_provincia():
        print(u)  