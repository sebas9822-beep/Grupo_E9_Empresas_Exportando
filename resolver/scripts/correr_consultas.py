"""Corre las consultas de resolver/consultas/ sobre analisis.duckdb y muestra cada resultado con su cifra de control.

Uso (desde la raíz del repositorio, después de descargar.py, extraer.py y analisis.py):
    python resolver/scripts/correr_consultas.py            # todas
    python resolver/scripts/correr_consultas.py 03a 08b    # solo las que empiezan así

La consulta 00a necesita además la BD principal (python crear_bd_analitica.py) y los parquet de enero
y julio de 2024; se adjunta la BD principal con el nombre bd_principal.
"""
import os
import pathlib
import sys

import duckdb
import pandas as pd

BASE = pathlib.Path(__file__).parent
CONSULTAS = BASE.parent / "consultas"
ANALISIS = os.environ.get("ANALISIS_DB", str(BASE / "analisis.duckdb"))
BD_PRINCIPAL = os.environ.get("BD_PRINCIPAL", "datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb")

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_colwidth", 45)

if __name__ == "__main__":
    con = duckdb.connect(ANALISIS, read_only=True)
    if pathlib.Path(BD_PRINCIPAL).exists():
        con.execute(f"ATTACH '{BD_PRINCIPAL}' AS bd_principal (READ_ONLY)")
    filtros = sys.argv[1:]
    for archivo in sorted(CONSULTAS.glob("*.sql")):
        if filtros and not any(archivo.name.startswith(f) for f in filtros):
            continue
        sql = archivo.read_text(encoding="utf-8")
        control = next((l for l in sql.splitlines() if l.startswith("-- Cifra de control:")), "")
        print(f"\n===== {archivo.name}\n{control}")
        try:
            df = con.sql(sql).df()
            print(f"({len(df)} filas)")
            print(df.head(12).to_string(index=False))
        except Exception as e:  # noqa: BLE001
            print("No se pudo correr:", e)
