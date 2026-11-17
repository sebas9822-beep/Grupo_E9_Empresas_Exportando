"""Utilidades compartidas: descargas con reintentos, API de datos.gov.co (Socrata),
lectura de CSV que pueden venir comprimidos y dígito de verificación del NIT."""
import csv
import io
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

ENCABEZADOS = {"User-Agent": "Mozilla/5.0 (proyecto academico Grupo E9 EstudIA)"}


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def descargar(url, destino, intentos=3, timeout=900):
    """Descarga url a destino (vía archivo .part). Devuelve False si la fuente responde 404."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".part")
    for i in range(1, intentos + 1):
        try:
            req = urllib.request.Request(url, headers=ENCABEZADOS)
            with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            tmp.replace(destino)
            return True
        except urllib.error.HTTPError as e:
            tmp.unlink(missing_ok=True)
            if e.code == 404:
                return False
            err = e
        except Exception as e:  # red, timeout, corte de conexión
            tmp.unlink(missing_ok=True)
            err = e
        log(f"  reintento {i}/{intentos} {destino.name}: {err}")
        time.sleep(5 * i)
    raise RuntimeError(f"No se pudo descargar {url}: {err}")


def zip_valido(ruta):
    ruta = Path(ruta)
    if not ruta.exists() or ruta.stat().st_size < 1000 or not zipfile.is_zipfile(ruta):
        return False
    try:
        with zipfile.ZipFile(ruta) as z:
            return len(z.namelist()) > 0
    except zipfile.BadZipFile:
        return False


def _leer_url(url, intentos=5, timeout=600):
    for i in range(1, intentos + 1):
        try:
            req = urllib.request.Request(url, headers=ENCABEZADOS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except Exception as e:
            log(f"  reintento {i}/{intentos}: {e}")
            time.sleep(5 * i)
    raise RuntimeError(f"No se pudo leer {url}")


def socrata_csv(dataset, destino, select=None, where=None, paso=50000):
    """Descarga un conjunto de datos.gov.co a CSV, paginando por :id (evita cortes en descargas grandes)."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".part")
    total, offset = 0, 0
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        while True:
            params = {"$order": ":id", "$limit": paso, "$offset": offset}
            if select:
                params["$select"] = select
            if where:
                params["$where"] = where
            txt = _leer_url(f"https://www.datos.gov.co/resource/{dataset}.csv?" + urllib.parse.urlencode(params))
            lineas = txt.splitlines(keepends=True)
            if offset == 0:
                f.write(lineas[0])
            cuerpo = "".join(lineas[1:])
            n = sum(1 for _ in csv.reader(io.StringIO(cuerpo)))
            f.write(cuerpo)
            total += n
            if n < paso:
                break
            offset += paso
    tmp.replace(destino)
    return total


def socrata_json(dataset, params):
    import json
    return json.loads(_leer_url(f"https://www.datos.gov.co/resource/{dataset}.json?" + urllib.parse.urlencode(params)))


def ruta_csv(ruta, interim):
    """Devuelve la ruta a un CSV; si solo existe la versión .zip (así quedan algunos en OneDrive),
    la descomprime en datos/intermedios/descomprimidos/."""
    ruta = Path(ruta)
    if ruta.exists():
        return ruta
    zp = ruta.with_suffix(".zip")
    if zp.exists():
        destino = Path(interim) / "descomprimidos" / ruta.name
        if not destino.exists() or destino.stat().st_mtime < zp.stat().st_mtime:
            destino.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zp) as z:
                nombre = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
                with z.open(nombre) as src, open(destino, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        return destino
    sys.exit(f"Falta el archivo {ruta} (ni .csv ni .zip). Corre antes el paso de descarga correspondiente.")


PESOS_DV = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]


def digito_verificacion(nit):
    """Dígito de verificación DIAN (coincide con el RUES en 99,9 % de los NIT exportadores)."""
    s = sum(int(d) * PESOS_DV[i] for i, d in enumerate(reversed(str(nit)))) % 11
    return str(s if s < 2 else 11 - s)


def sql_lista(valores):
    return ", ".join("'" + str(v).replace("'", "''") + "'" for v in valores)
