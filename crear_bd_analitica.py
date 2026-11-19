"""Arma la BD PRINCIPAL del proyecto (capa analítica) en un solo archivo DuckDB, a partir de los parquet versionados.

    python crear_bd_analitica.py                      # crea datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb
    python crear_bd_analitica.py --salida otra/ruta.duckdb

Esta es la base con la que se trabaja: la BD depurada (paso 9) más la capa analítica (paso 10), con llaves primarias y
foráneas, catálogos completos, banderas de atípicos, pesos y cantidades reconstruidos, panel por empresa y vistas listas.
No necesita descargar nada ni correr el pipeline: basta con clonar el repositorio. Tarda alrededor de un minuto.

Usa dos carpetas del repositorio:
  datos/limpios/bd_depurada/   hechos de la depurada (un parquet por mes): la capa no los repite
  datos/limpios/bd_analitica/  columnas nuevas de los hechos (por ID_REGISTRO), demás tablas y esquema.sql

El archivo .duckdb no se versiona (pesa ~360 MB y GitHub no acepta archivos de más de 100 MB).
Qué contiene y cómo se construyó: docs/bd_principal_capa_analitica.md.

Uso desde Python:
    import duckdb
    con = duckdb.connect("datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb", read_only=True)
    con.sql("SELECT * FROM vw_ventas_exterior LIMIT 10").df()
"""
import argparse
import pathlib
import re
import sys
import time

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config as C  # noqa: E402

COLUMNAS_RETIRADAS = ("OFICINA", "COD_MODALIDAD_PRECEDENTE")   # sin tabla oficial DIAN (ver docs/bd_principal_capa_analitica.md)
COMPLEMENTO = "hechos_analitica_complemento.parquet"


def sql_hechos(fuente_hechos, fuente_complemento):
    """Tabla de hechos de la BD principal: los hechos depurados con la corrección de zona franca, sin las columnas
    retiradas, más las columnas de la capa unidas por ID_REGISTRO. La usan este script y el paso 10."""
    return f"""
  SELECT h.* EXCLUDE ({', '.join(COLUMNAS_RETIRADAS)})
             REPLACE (coalesce(h.ES_DESTINO_ZONA_FRANCA, h.COD_PAIS_DESTINO = 'XCF') AS ES_DESTINO_ZONA_FRANCA),
         c.* EXCLUDE (ID_REGISTRO)
  FROM {fuente_hechos} h LEFT JOIN {fuente_complemento} c USING (ID_REGISTRO) ORDER BY h.ID_REGISTRO"""


def leer_esquema(ruta):
    """Devuelve [(tipo, nombre, sql)] en el orden de creación guardado por el paso 10."""
    texto = pathlib.Path(ruta).read_text(encoding="utf-8")
    partes = re.split(r"^-- @@ (tabla|vista) (\S+)\n", texto, flags=re.M)
    return [(partes[i], partes[i + 1], partes[i + 2].strip()) for i in range(1, len(partes), 3)]


def construir(depurada=C.OUT_BD_DEPURADA, analitica=C.OUT_BD_ANALITICA, salida=C.BD_ANALITICA_DUCKDB, memoria="4GB"):
    """Crea (o reemplaza) el archivo DuckDB de la BD principal con sus llaves, sus datos y sus vistas."""
    t0 = time.time()
    depurada, analitica, salida = pathlib.Path(depurada), pathlib.Path(analitica), pathlib.Path(salida)
    hechos = depurada / "hechos_exportaciones"
    for requerido in (hechos, analitica / COMPLEMENTO, analitica / "esquema.sql"):
        if not (requerido.exists() and (requerido.is_file() or any(requerido.glob("*.parquet")))):
            sys.exit(f"No encuentro {requerido}. Clona el repositorio completo o corre: python run_pipeline.py --solo 9 10")
    salida.parent.mkdir(parents=True, exist_ok=True)
    for f in (salida, salida.with_name(salida.name + ".wal")):
        f.unlink(missing_ok=True)
    con = duckdb.connect(str(salida))
    con.execute(f"SET memory_limit='{memoria}'; SET preserve_insertion_order=true")
    objetos = leer_esquema(analitica / "esquema.sql")
    for tipo, nombre, sql in objetos:                       # tablas en orden: las referenciadas antes que las que las usan
        if tipo != "tabla":
            continue
        con.execute(sql)
        if nombre == "hechos_analitica":
            fuente = sql_hechos(f"read_parquet('{(hechos / '*.parquet').as_posix()}')",
                                f"read_parquet('{(analitica / COMPLEMENTO).as_posix()}')")
        else:
            fuente = f"SELECT * FROM read_parquet('{(analitica / f'{nombre}.parquet').as_posix()}')"
        con.execute(f"INSERT INTO {nombre} BY NAME {fuente}")
    pendientes = [(n, sql) for tipo, n, sql in objetos if tipo == "vista"]
    while pendientes:                                       # una vista puede depender de otra: se crean en orden de dependencias
        fallidas = []
        for nombre, sql in pendientes:
            try:
                con.execute(sql)
            except duckdb.CatalogException:
                fallidas.append((nombre, sql))
        if len(fallidas) == len(pendientes):
            sys.exit(f"No se pudieron crear las vistas: {', '.join(n for n, _ in fallidas)}")
        pendientes = fallidas
    con.execute("CHECKPOINT")

    # Controles: mismas cifras que la BD depurada y cuadre oficial
    n, fob = con.execute("SELECT count(*), sum(VALOR_FOB_USD) FROM hechos_analitica").fetchone()
    pk, fk = con.execute("SELECT count(*) FILTER (WHERE constraint_type = 'PRIMARY KEY'), "
                         "count(*) FILTER (WHERE constraint_type = 'FOREIGN KEY') FROM duckdb_constraints()").fetchone()
    dane = con.execute("SELECT max(abs(DIF_PCT)) FROM vw_validacion_dane").fetchone()[0]
    con.close()
    assert n > 0, "La tabla de hechos quedó vacía"
    print(f"BD principal creada: {salida} ({salida.stat().st_size / 1e6:,.0f} MB) en {time.time() - t0:,.0f} s · "
          f"{n:,} registros · FOB USD {fob / 1e6:,.1f} M · {pk} llaves primarias y {fk} foráneas · "
          f"diferencia máxima con el DANE {dane:.3f} %")
    return salida


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--depurada", default=str(C.OUT_BD_DEPURADA), help="carpeta con los parquet de la BD depurada")
    ap.add_argument("--analitica", default=str(C.OUT_BD_ANALITICA), help="carpeta con los parquet y el esquema de la capa")
    ap.add_argument("--salida", default=str(C.BD_ANALITICA_DUCKDB), help="ruta del archivo .duckdb a crear")
    a = ap.parse_args()
    construir(a.depurada, a.analitica, a.salida)
