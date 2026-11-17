"""Paso 1 · Descarga de la DIAN.

- Bases estadísticas mensuales de exportaciones (un .zip con un .xlsx por mes, ~40 MB c/u).
  Los meses que la DIAN aún no publica (responden 404) se omiten sin error.
- Directorio anual de exportadores (2017 en adelante).
- Ficha técnica, ficha metodológica y correlativa de países.

Uso: python pipeline/p01_descargar_dian.py [--desde 2024-01] [--hasta 2026-12] [--hilos 8]
"""
import argparse
import datetime
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from pipeline.comun import descargar, log, zip_valido  # noqa: E402


def mes(texto):
    a, m = texto.split("-")
    return int(a), int(m)


def rango_meses(desde, hasta):
    a, m = desde
    while (a, m) <= hasta:
        yield a, m
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def nombre_mensual(a, m):
    return f"{m:02d}_Exportaciones_{a}_{C.MESES[m - 1]}.zip"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=C.PERIODO_INICIO, help="AAAA-MM (por defecto %(default)s)")
    ap.add_argument("--hasta", default=None, help="AAAA-MM (por defecto, el mes actual)")
    ap.add_argument("--hilos", type=int, default=8)
    ap.add_argument("--sin-directorio", action="store_true")
    ap.add_argument("--sin-documentos", action="store_true")
    args = ap.parse_args()
    hoy = datetime.date.today()
    hasta = mes(args.hasta) if args.hasta else (hoy.year, hoy.month)

    tareas = []
    for a, m in rango_meses(mes(args.desde), hasta):
        destino = C.RAW_DIAN_MENSUAL / str(a) / nombre_mensual(a, m)
        if not zip_valido(destino):
            tareas.append((f"{C.DIAN_MENSUAL_URL}/{destino.name}", destino))
    for a in range(mes(args.desde)[0], hasta[0] + 1):          # totales anuales que publica la DIAN
        tareas.append((f"{C.DIAN_MENSUAL_URL}/Totales-Exportaciones-{a}.zip",
                       C.RAW_DIAN_MENSUAL / str(a) / f"Totales-Exportaciones-{a}.zip"))
    if not args.sin_directorio:
        for a in range(2017, hoy.year + 1):
            destino = C.RAW_DIAN_DIRECTORIO / f"Directorio-Exportadores-{a}.zip"
            if a >= hoy.year - 1 or not zip_valido(destino):   # el del año en curso se actualiza cada mes
                tareas.append((f"{C.DIAN_DIRECTORIO_URL}/{destino.name}", destino))
    if not args.sin_documentos:
        for doc in C.DIAN_DOCS:
            tareas.append((f"{C.DIAN_DOCS_URL}/{doc}", C.RAW_DIAN_DOCS / doc))

    log(f"{len(tareas)} archivos por descargar en {C.RAW}")
    with ThreadPoolExecutor(args.hilos) as ex:
        resultados = list(ex.map(lambda t: descargar(*t), tareas))
    for (url, destino), ok in zip(tareas, resultados):
        log(("OK          " if ok else "NO PUBLICADO") + f" {destino.relative_to(C.RAW)}")
    mensuales = sorted(C.RAW_DIAN_MENSUAL.glob("*/*_Exportaciones_*.zip"))
    log(f"Bases mensuales disponibles: {len(mensuales)} ({mensuales[0].name} … {mensuales[-1].name})")


if __name__ == "__main__":
    main()
