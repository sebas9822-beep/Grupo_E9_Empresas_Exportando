"""Descarga de la DIAN las bases mensuales de exportaciones que necesita el análisis de concentración.

Baja enero de 2016 a diciembre de 2023 (96 archivos, insumo de analisis.py) y enero y julio de 2024
(para comprobar el método contra la BD principal, consulta 00a). Cada archivo es un .zip de unos 20 a 40 MB
con un Excel adentro. Los que ya están en zips/ no se vuelven a bajar.

Uso (desde la raíz del repositorio):
    python resolver/scripts/descargar.py
"""
import pathlib
import time
import urllib.request
import zipfile

BASE = pathlib.Path(__file__).parent
ZIPS = BASE / "zips"
URL = "https://www.dian.gov.co/dian/cifras/Basesestadisticasexportaciones/"
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def archivos():
    for anio in range(2016, 2024):
        for mes in range(1, 13):
            yield f"{mes:02d}_Exportaciones_{anio}_{MESES[mes - 1]}.zip"
    yield "01_Exportaciones_2024_Enero.zip"
    yield "07_Exportaciones_2024_Julio.zip"


def bajar(nombre, intentos=4):
    destino, parcial = ZIPS / nombre, ZIPS / (nombre + ".part")
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(URL + nombre, timeout=900) as r, open(parcial, "wb") as f:
                while bloque := r.read(1 << 20):
                    f.write(bloque)
            with zipfile.ZipFile(parcial) as z:          # comprueba que el zip esté completo
                if z.testzip() is not None:
                    raise zipfile.BadZipFile("zip dañado")
            parcial.replace(destino)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"  intento {intento} falló: {e}")
            time.sleep(5)
    parcial.unlink(missing_ok=True)
    return False


if __name__ == "__main__":
    ZIPS.mkdir(exist_ok=True)
    pendientes = [n for n in archivos() if not (ZIPS / n).exists()]
    print(f"{len(pendientes)} archivos por bajar")
    fallos = [n for n in pendientes if not (print("bajando", n) or bajar(n))]
    print("listo" if not fallos else f"fallaron {len(fallos)}: {fallos}")
