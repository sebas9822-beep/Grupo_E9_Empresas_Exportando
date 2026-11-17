"""Arma la BD única depurada (un solo archivo DuckDB) a partir de los parquet versionados en data/processed/bd_depurada/.

    python crear_bd_depurada.py                       # crea data/processed/bd_depurada/BD_exportaciones_Colombia_depurada.duckdb
    python crear_bd_depurada.py --salida otra/ruta.duckdb

No necesita descargar nada ni correr el pipeline: basta con clonar el repositorio. Tarda alrededor de un minuto.
El archivo .duckdb no se versiona (pesa ~340 MB y GitHub no acepta archivos de más de 100 MB); por eso se
reconstruye desde las tablas en parquet, que sí están en el repositorio. Las tablas y las reglas de limpieza
están descritas en docs/limpieza_bd_depurada.md y docs/diccionario_bd_depurada.csv.

Uso desde Python:
    import duckdb
    con = duckdb.connect("data/processed/bd_depurada/BD_exportaciones_Colombia_depurada.duckdb", read_only=True)
    con.sql("SELECT * FROM vw_directorio_antioquia LIMIT 10").df()
"""
import argparse
import pathlib
import sys

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config as C  # noqa: E402

# Tablas que se cargan (cada una es un parquet en data/processed/bd_depurada/, salvo los hechos, partidos por mes)
TABLAS = ["dim_exportador", "dim_subpartida", "dim_pais", "dim_zona_franca", "dim_departamento", "dim_municipio",
          "dim_aduana", "dim_declarante", "catalogo_codigos", "ref_mincit_trimestral", "ref_madr_agricola_anual",
          "log_depuracion", "diccionario_datos", "info_bd"]

VISTAS = [
"""CREATE OR REPLACE VIEW vw_exportaciones AS
SELECT h.*,
  e.RAZON_SOCIAL, e.VINCULO_ANTIOQUIA, coalesce(e.EMPRESA_ANTIOQUENA, false) AS EMPRESA_ANTIOQUENA,
  coalesce(e.ES_EXPORTADOR_ANTIOQUENO, false) AS ES_EXPORTADOR_ANTIOQUENO,
  e.CAMARA_COMERCIO, e.CIIU_PRINCIPAL_RUES, e.SECTOR_EXPORTADOR_PRINCIPAL,
  cl.DESCRIPCION AS CLASE_EXPORTADOR_DESC, dc.RAZON_SOCIAL_DECLARANTE,
  mu.MUNICIPIO AS MUNICIPIO_DIRECCION_DECLARADA,
  pd.PAIS AS PAIS_DESTINO, pd.TIPO_DESTINO, zf.ZONA_FRANCA AS ZONA_FRANCA_DESTINO,
  ad1.ADUANA AS ADUANA_DESPACHO, ad2.ADUANA AS ADUANA_SALIDA,
  dp.DEPARTAMENTO AS DEPTO_PROCEDENCIA, dor.DEPARTAMENTO AS DEPTO_ORIGEN,
  mt.DESCRIPCION AS MODO_TRANSPORTE, pb.PAIS AS PAIS_BANDERA,
  mo.DESCRIPCION AS MODALIDAD_EXPORTACION, un.DESCRIPCION AS UNIDAD_FISICA,
  sp.CAPITULO, sp.PARTIDA, sp.SUBPARTIDA_SA6, sp.SECTOR_EXPORTACION, sp.ES_MINERO_ENERGETICO, sp.ES_AGRICOLA_MADR,
  sp.PRODUCTO_AGRICOLA_MADR, sp.TRADICION_AGRICOLA_MADR,
  CAST(h.ANIO AS VARCHAR) || '-T' || CAST((h.MES - 1) // 3 + 1 AS VARCHAR) AS TRIMESTRE
FROM hechos_exportaciones h
LEFT JOIN dim_exportador e ON e.NIT = h.NIT_EXPORTADOR
LEFT JOIN catalogo_codigos cl ON cl.DOMINIO = 'CLASE_EXPORTADOR' AND cl.CODIGO = h.CLASE_EXPORTADOR
LEFT JOIN dim_declarante dc ON dc.NIT_DECLARANTE = h.NIT_DECLARANTE
LEFT JOIN dim_municipio mu ON mu.COD_MPIO = h.COD_MPIO_DIRECCION_DECLARADA
LEFT JOIN dim_pais pd ON pd.COD_PAIS = h.COD_PAIS_DESTINO
LEFT JOIN dim_zona_franca zf ON zf.COD_ZONA_FRANCA = h.COD_ZONA_FRANCA_DESTINO
LEFT JOIN dim_aduana ad1 ON ad1.COD_ADUANA = h.COD_ADUANA_DESPACHO
LEFT JOIN dim_aduana ad2 ON ad2.COD_ADUANA = h.COD_ADUANA_SALIDA
LEFT JOIN dim_departamento dp ON dp.COD_DEPTO = h.COD_DEPTO_PROCEDENCIA
LEFT JOIN dim_departamento dor ON dor.COD_DEPTO = h.COD_DEPTO_ORIGEN
LEFT JOIN catalogo_codigos mt ON mt.DOMINIO = 'MODO_TRANSPORTE' AND mt.CODIGO = h.COD_MODO_TRANSPORTE
LEFT JOIN dim_pais pb ON pb.COD_PAIS = h.COD_PAIS_BANDERA
LEFT JOIN catalogo_codigos mo ON mo.DOMINIO = 'MODALIDAD_EXPORTACION' AND mo.CODIGO = h.COD_MODALIDAD_EXPORTACION
LEFT JOIN catalogo_codigos un ON un.DOMINIO = 'UNIDAD_FISICA' AND un.CODIGO = h.COD_UNIDAD_FISICA
LEFT JOIN dim_subpartida sp ON sp.SUBPARTIDA = h.SUBPARTIDA""",
"""CREATE OR REPLACE VIEW vw_exportaciones_antioquia AS
SELECT * FROM vw_exportaciones WHERE ORIGEN_MERCANCIA_ANTIOQUIA OR ES_EXPORTADOR_ANTIOQUENO""",
"""CREATE OR REPLACE VIEW vw_directorio_antioquia AS
SELECT * FROM dim_exportador WHERE ES_EXPORTADOR_ANTIOQUENO ORDER BY RANKING_ANTIOQUIA_FOB""",
"""CREATE OR REPLACE VIEW vw_serie_mensual AS
SELECT strftime(PERIODO, '%Y-%m') AS PERIODO,
  round(sum(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA) / 1e6, 3) AS FOB_MUSD_ORIGEN_ANTIOQUIA,
  round(sum(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA AND NOT ES_MINERO_ENERGETICO) / 1e6, 3) AS FOB_MUSD_ORIGEN_ANTIOQUIA_NO_MINERO_ENERGETICO,
  round(sum(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA AND ES_AGRICOLA_MADR) / 1e6, 3) AS FOB_MUSD_ORIGEN_ANTIOQUIA_AGRICOLA,
  round(sum(VALOR_FOB_USD) FILTER (WHERE EMPRESA_ANTIOQUENA) / 1e6, 3) AS FOB_MUSD_EMPRESAS_ANTIOQUENAS,
  round(sum(VALOR_FOB_USD) FILTER (WHERE ES_EXPORTADOR_ANTIOQUENO) / 1e6, 3) AS FOB_MUSD_EXPORTADORES_ANTIOQUENOS,
  round(sum(VALOR_FOB_USD) / 1e6, 3) AS FOB_MUSD_NACIONAL,
  round(sum(VALOR_FOB_USD) FILTER (WHERE NOT ES_MINERO_ENERGETICO) / 1e6, 3) AS FOB_MUSD_NACIONAL_NO_MINERO_ENERGETICO,
  round(sum(VALOR_FOB_USD) FILTER (WHERE ES_DESTINO_ZONA_FRANCA) / 1e6, 3) AS FOB_MUSD_NACIONAL_DESTINO_ZONA_FRANCA,
  count(DISTINCT NIT_EXPORTADOR) FILTER (WHERE EMPRESA_ANTIOQUENA) AS N_NIT_EMPRESAS_ANTIOQUENAS,
  count(DISTINCT NIT_EXPORTADOR) FILTER (WHERE ES_EXPORTADOR_ANTIOQUENO) AS N_NIT_EXPORTADORES_ANTIOQUENOS,
  count(DISTINCT NIT_EXPORTADOR) AS N_NIT_NACIONAL
FROM vw_exportaciones GROUP BY 1 ORDER BY 1""",
"""CREATE OR REPLACE VIEW vw_validacion_mincit AS
WITH d AS (SELECT CAST(h.ANIO AS VARCHAR) || 'Q' || CAST((h.MES - 1) // 3 + 1 AS VARCHAR) AS TRIMESTRE,
                  round(sum(h.VALOR_FOB_USD) / 1e6) AS DIAN_TOTAL_MUSD,
                  round(sum(h.VALOR_FOB_USD) FILTER (WHERE NOT s.ES_MINERO_ENERGETICO) / 1e6) AS DIAN_NME_MUSD
           FROM hechos_exportaciones h JOIN dim_subpartida s USING (SUBPARTIDA) GROUP BY 1)
SELECT d.*, r.MINCIT_TOTAL_MUSD, r.MINCIT_NME_MUSD,
  round(100 * (d.DIAN_TOTAL_MUSD - r.MINCIT_TOTAL_MUSD) / r.MINCIT_TOTAL_MUSD, 2) AS DIF_TOTAL_PCT,
  round(100 * (d.DIAN_NME_MUSD - r.MINCIT_NME_MUSD) / r.MINCIT_NME_MUSD, 2) AS DIF_NME_PCT
FROM d LEFT JOIN ref_mincit_trimestral r USING (TRIMESTRE) ORDER BY 1""",
"""CREATE OR REPLACE VIEW vw_validacion_madr AS
WITH r AS (SELECT * FROM ref_madr_agricola_anual),
d AS (SELECT h.ANIO,
        round(sum(h.VALOR_FOB_USD) FILTER (WHERE s.ES_AGRICOLA_MADR AND h.MES <= r.MESES) / 1e6, 1) AS DIAN_AGRICOLA_NACIONAL_MUSD,
        round(sum(h.VALOR_FOB_USD) FILTER (WHERE s.ES_AGRICOLA_MADR AND h.ORIGEN_MERCANCIA_ANTIOQUIA AND h.MES <= r.MESES) / 1e6, 1) AS DIAN_AGRICOLA_ANTIOQUIA_MUSD
      FROM hechos_exportaciones h JOIN dim_subpartida s USING (SUBPARTIDA) JOIN r ON r.ANIO = h.ANIO GROUP BY 1)
SELECT d.ANIO, r.MESES, d.DIAN_AGRICOLA_NACIONAL_MUSD, r.MADR_AGRICOLA_NACIONAL_MUSD,
       d.DIAN_AGRICOLA_ANTIOQUIA_MUSD, r.MADR_AGRICOLA_ANTIOQUIA_MUSD
FROM d JOIN r USING (ANIO) ORDER BY 1""",
]


def construir(origen=C.OUT_BD_DEPURADA, salida=C.BD_DEPURADA_DUCKDB, memoria="3GB"):
    """Crea (o reemplaza) el archivo DuckDB con las tablas en parquet de `origen` y las vistas de análisis."""
    origen, salida = pathlib.Path(origen), pathlib.Path(salida)
    hechos = origen / "hechos_exportaciones"
    if not any(hechos.glob("*.parquet")):
        sys.exit(f"No encuentro {hechos}/*.parquet. Clona el repositorio completo o corre: python run_pipeline.py --solo 9")
    salida.parent.mkdir(parents=True, exist_ok=True)
    for f in (salida, salida.with_name(salida.name + ".wal")):
        f.unlink(missing_ok=True)
    con = duckdb.connect(str(salida))
    con.execute(f"SET memory_limit='{memoria}'; SET preserve_insertion_order=true")
    con.execute(f"CREATE TABLE hechos_exportaciones AS SELECT * FROM read_parquet('{(hechos / '*.parquet').as_posix()}') ORDER BY ID_REGISTRO")
    for t in TABLAS:
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_parquet('{(origen / f'{t}.parquet').as_posix()}')")
    for v in VISTAS:
        con.execute(v)
    con.execute("CHECKPOINT")
    n, fob = con.execute("SELECT count(*), sum(VALOR_FOB_USD) FROM hechos_exportaciones").fetchone()
    con.close()
    print(f"BD creada: {salida} ({salida.stat().st_size / 1e6:,.0f} MB) · {n:,} registros · FOB USD {fob / 1e6:,.1f} M")
    return salida


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origen", default=str(C.OUT_BD_DEPURADA), help="carpeta con los parquet de la BD depurada")
    ap.add_argument("--salida", default=str(C.BD_DEPURADA_DUCKDB), help="ruta del archivo .duckdb a crear")
    a = ap.parse_args()
    construir(a.origen, a.salida)
