"""Paso 4 · Une los meses en una sola tabla DuckDB (data/interim/expo.duckdb) y deja la lista
de NIT exportadores (con dígito de verificación) para las consultas por NIT del paso 5.

Agrega: municipio/departamento de la dirección declarada (DIVIPOLA), subpartida a 10 dígitos,
país destino normalizado (nombres M49), banderas de origen Antioquia y de persona natural.
"""
import argparse
import pathlib
import sys

import duckdb
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from pipeline.comun import digito_verificacion, log, ruta_csv  # noqa: E402


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    con = duckdb.connect(str(C.DUCKDB_PATH))
    con.execute(f"SET memory_limit='4GB'; SET preserve_insertion_order=false; SET temp_directory='{C.INTERIM / 'tmp_duckdb'}'")
    divipola = ruta_csv(C.RAW_DATOSGOV / "DIVIPOLA_municipios.csv", C.INTERIM)
    con.execute(f"""CREATE OR REPLACE TABLE divipola AS
        SELECT lpad(cod_mpio,5,'0') cod_mpio, nom_mpio, dpto FROM read_csv('{divipola}', all_varchar=true)""")
    con.execute(f"""CREATE OR REPLACE TABLE expo AS
    WITH b AS (SELECT * FROM read_parquet('{C.INTERIM_MENSUAL}/*.parquet', union_by_name=true)),
    d AS (SELECT *, CASE WHEN trim(COD_DPTO_EXPORTADOR) ~ '^[0-9]{{4,5}}$' THEN lpad(trim(COD_DPTO_EXPORTADOR),5,'0') END cod5,
                 coalesce(upper(trim(RAZON_SOCIAL_EXPORTADOR))='PERSONA NATURAL', false) rs_pn,
                 coalesce(trim(RAZON_SOCIAL_EXPORTADOR),'')='' rs_vacia,
                 coalesce(trim(TIPO_IDENT)='2' AND regexp_matches(regexp_replace(trim(NIT_EXPORTADOR),'^0+',''), '^[89][0-9]{{8}}$'), false) nit_empresa
          FROM b)
    SELECT d.* EXCLUDE (cod5, rs_pn, rs_vacia, nit_empresa),
      lpad(trim(d.SUBPARTIDA),10,'0')                    AS SUBPARTIDA_10D,
      make_date(d.ANIO, d.MES, 1)                        AS PERIODO,
      d.cod5                                             AS COD_MPIO_DIRECCION_DECLARADA,
      v.nom_mpio                                         AS MUNICIPIO_DIRECCION_DECLARADA,
      v.dpto                                             AS DEPTO_DIRECCION_DECLARADA,
      coalesce(substr(d.cod5,1,2)='05', false)           AS DIRECCION_DECLARADA_EN_ANTIOQUIA,
      (trim(d.COD_REGION_ORIGEN)='5')                    AS ORIGEN_MERCANCIA_ANTIOQUIA,
      -- La DIAN anonimiza a las personas naturales como "PERSONA NATURAL". En septiembre de 2024 también
      -- ocultó así (o dejó vacía) la razón social de casi todas las empresas, pero conservó su NIT:
      -- esas líneas son de empresas y se les atribuyen.
      (d.rs_pn AND NOT d.nit_empresa)                    AS ES_PERSONA_NATURAL,
      ((d.rs_pn OR d.rs_vacia) AND d.nit_empresa)        AS RAZON_SOCIAL_ENMASCARADA,
      CASE WHEN d.nit_empresa OR NOT d.rs_pn
           THEN nullif(regexp_replace(trim(d.NIT_EXPORTADOR),'^0+',''),'') END AS NIT
    FROM d LEFT JOIN divipola v ON v.cod_mpio = d.cod5""")
    # País destino normalizado: desde 2025 la DIAN usa nombres M49; se mapea por código alfa-3
    con.execute("""CREATE OR REPLACE TABLE pais_map AS
        SELECT COD_PAIS_DESTINO_ALF alf, mode(PAIS_DESTINO_FINAL) pais
        FROM expo WHERE ANIO>=2025 AND COD_PAIS_DESTINO_ALF IS NOT NULL GROUP BY 1""")
    con.execute("""CREATE OR REPLACE TABLE expo AS
        SELECT e.*, coalesce(p.pais, e.PAIS_DESTINO_FINAL) AS PAIS_DESTINO_NORM
        FROM expo e LEFT JOIN pais_map p ON p.alf = e.COD_PAIS_DESTINO_ALF""")
    for anio, filas, fob, nits in con.execute("""SELECT ANIO, count(*), round(sum(VALOR_FOB_USD)/1e6,1),
            count(DISTINCT NIT) FROM expo GROUP BY 1 ORDER BY 1""").fetchall():
        log(f"{anio}: {filas:,} líneas · FOB USD {fob:,.1f} M · {nits:,} NIT")
    nits = [r[0] for r in con.execute("SELECT DISTINCT NIT FROM expo WHERE NIT ~ '^[0-9]+$' ORDER BY 1").fetchall()]
    pd.DataFrame({"NIT": nits, "NIT_DV": [n + digito_verificacion(n) for n in nits]}).to_csv(C.NITS_PATH, index=False)
    log(f"{len(nits):,} NIT de personas jurídicas → {C.NITS_PATH.relative_to(C.ROOT)}")


if __name__ == "__main__":
    main()
