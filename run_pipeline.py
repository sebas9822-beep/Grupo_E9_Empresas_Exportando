"""Corre el pipeline completo (o un tramo) de punta a punta.

    python run_pipeline.py                  # todo: descargas + procesamiento (~30-40 min la primera vez)
    python run_pipeline.py --sin-descargas  # solo procesa lo que ya está en data/raw (o en EXPO_RAW_DIR)
    python run_pipeline.py --desde 6        # desde el paso 6 en adelante
    python run_pipeline.py --solo 7 8       # solo esos pasos

Pasos:
  1 Descargar DIAN (bases mensuales, directorio, documentación)
  2 Descargar datos abiertos (RUES Antioquia, Supersociedades, DIVIPOLA, cámaras, MinCIT, MinAgricultura)
  3 Convertir bases mensuales DIAN a parquet
  4 Consolidar en DuckDB y sacar la lista de NIT
  5 Consultar por NIT: RUES nacional y SECOP II
  6 Construir el directorio de empresas
  7 Exportar productos finales y validaciones
  8 Generar el Excel
"""
import argparse
import runpy
import sys
import time
from pathlib import Path

PASOS = {
    1: "p01_descargar_dian.py", 2: "p02_descargar_datos_abiertos.py", 3: "p03_convertir_dian.py",
    4: "p04_consolidar.py", 5: "p05_descargar_por_nit.py", 6: "p06_directorio.py",
    7: "p07_exportar.py", 8: "p08_excel.py",
}
DESCARGAS = {1, 2, 5}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", type=int, default=1)
    ap.add_argument("--hasta", type=int, default=8)
    ap.add_argument("--solo", type=int, nargs="*")
    ap.add_argument("--sin-descargas", action="store_true", help="omite los pasos 1, 2 y 5")
    args = ap.parse_args()
    pasos = args.solo or [p for p in PASOS if args.desde <= p <= args.hasta]
    if args.sin_descargas:
        pasos = [p for p in pasos if p not in DESCARGAS]
    raiz = Path(__file__).resolve().parent
    for p in pasos:
        t = time.time()
        print(f"\n=== Paso {p}: {PASOS[p]} ===", flush=True)
        sys.argv = [PASOS[p]]
        runpy.run_path(str(raiz / "pipeline" / PASOS[p]), run_name="__main__")
        print(f"=== Paso {p} listo en {time.time() - t:,.0f} s ===", flush=True)


if __name__ == "__main__":
    main()
