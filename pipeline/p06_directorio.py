"""Paso 6 · Directorio de empresas exportadoras (una fila por NIT de persona jurídica).

Une las dos búsquedas:
 1) DIAN + RUES + Supersociedades: domicilio (cámara de comercio), vínculo con Antioquia, FOB por
    año, países, productos, CIIU, matrícula y cifras de las 10.000 empresas más grandes.
 2) MinCIT + MinAgricultura + SECOP II: sector exportador (minero-energético / agrícola / industria),
    producto agrícola principal y contratación con el Estado.

Nota metodológica: en la base DIAN, DIREC_EXPORTADOR/COD_DPTO_EXPORTADOR muchas veces es la dirección
de la agencia de aduanas (una misma dirección aparece en cientos de NIT). Por eso el domicilio se toma del
RUES y la dirección DIAN solo se usa como respaldo cuando no es compartida por más de 5 NIT.
"""
import argparse
import pathlib
import sys

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from pipeline.comun import log, ruta_csv, sql_lista  # noqa: E402

CAM_ANT = f"({sql_lista(C.CAMARAS_ANTIOQUIA)})"


def condicion_minero_energetica(col):
    return (f"(substr({col},1,2) IN ({sql_lista(C.ME_CAPITULOS)}) OR substr({col},1,4) IN ({sql_lista(C.ME_PARTIDAS)}) "
            f"OR substr({col},1,6) IN ({sql_lista(C.ME_SUBPARTIDAS6)}))")


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    con = duckdb.connect(str(C.DUCKDB_PATH))
    con.execute(f"SET memory_limit='4GB'; SET temp_directory='{C.INTERIM / 'tmp_duckdb'}'")
    rues_ant = ruta_csv(C.RAW_DATOSGOV / "RUES_personas_juridicas_camaras_Antioquia.csv", C.INTERIM)
    rues_nac = ruta_csv(C.RAW_DATOSGOV / "RUES_exportadores_nacional_por_NIT.csv", C.INTERIM)
    supers = ruta_csv(C.RAW_DATOSGOV / "Supersociedades_10000_empresas_mas_grandes.csv", C.INTERIM)
    madr = ruta_csv(C.RAW_FUENTES_V2 / "MADR_exportaciones_agricolas_2024_2026.csv", C.INTERIM)
    madr_hist = ruta_csv(C.RAW_FUENTES_V2 / "MinAgricultura_exportaciones_agricolas_2019_2025.csv", C.INTERIM)
    secop = ruta_csv(C.RAW_FUENTES_V2 / "SECOP_II_contratos_exportadores_por_NIT.csv", C.INTERIM)
    anios = [r[0] for r in con.execute("SELECT DISTINCT ANIO FROM expo ORDER BY 1").fetchall()]

    # --- Clasificación sectorial por subpartida (segunda búsqueda) -------------------------------
    con.execute(f"""CREATE OR REPLACE TABLE madr_map AS
    WITH a AS (SELECT lpad(partida,10,'0') s, mode(producto_madr_oai) prod, mode(tradici_n_productos) trad,
                      mode(descripcion_partida10_dig) descr, 1 pri FROM read_csv('{madr}', all_varchar=true) GROUP BY 1),
         b AS (SELECT lpad(partida,10,'0') s, NULL prod, mode(tradici_n_productos) trad,
                      mode(descripcion_partida10_dig) descr, 2 pri FROM read_csv('{madr_hist}', all_varchar=true) GROUP BY 1)
    SELECT s, arg_min(prod, pri) prod, arg_min(trad, pri) trad, arg_min(descr, pri) descr
    FROM (SELECT * FROM a UNION ALL SELECT * FROM b) GROUP BY s""")
    me = condicion_minero_energetica("s.s")
    con.execute(f"""CREATE OR REPLACE TABLE subpartida_map AS
    WITH s AS (SELECT DISTINCT SUBPARTIDA_10D s FROM expo)
    SELECT s.s AS SUBPARTIDA_10D, {me} AS ES_MINERO_ENERGETICO, (m.s IS NOT NULL) AS ES_AGRICOLA_MADR,
      m.prod AS PRODUCTO_AGRICOLA_MADR, m.trad AS TRADICION_AGRICOLA_MADR, m.descr AS DESCRIPCION_PARTIDA_MADR,
      CASE WHEN {me} THEN 'Minero-energético' WHEN m.s IS NOT NULL THEN 'Agrícola y agroindustrial (MADR)'
           ELSE 'Industria y otros' END AS SECTOR_EXPORTACION
    FROM s LEFT JOIN madr_map m ON m.s = s.s""")

    # --- Base por NIT (personas jurídicas) ----------------------------------------------------
    con.execute("""CREATE OR REPLACE TABLE pj AS
        SELECT e.*, regexp_replace(upper(trim(e.DIREC_EXPORTADOR)),'\\s+',' ','g') AS DIR_NORM
        FROM expo e WHERE e.NIT IS NOT NULL""")
    con.execute("CREATE OR REPLACE TABLE dir_comp AS SELECT DIR_NORM, COD_DPTO_EXPORTADOR, count(DISTINCT NIT) n_nit FROM pj GROUP BY 1,2")
    con.execute(f"""CREATE OR REPLACE TABLE sede_dian AS
    WITH t AS (SELECT p.NIT, p.MUNICIPIO_DIRECCION_DECLARADA m, p.DEPTO_DIRECCION_DECLARADA d, count(DISTINCT p.NUMERO_FORMULARIO) n
               FROM pj p JOIN dir_comp c USING (DIR_NORM, COD_DPTO_EXPORTADOR)
               WHERE c.n_nit <= {C.MAX_NIT_DIRECCION_PROPIA} AND p.MUNICIPIO_DIRECCION_DECLARADA IS NOT NULL GROUP BY 1,2,3),
    r AS (SELECT *, row_number() OVER (PARTITION BY NIT ORDER BY n DESC, m, d) rk FROM t)
    SELECT NIT, m MUNICIPIO_DIAN_DIRECCION_PROPIA, d DEPTO_DIAN_DIRECCION_PROPIA FROM r WHERE rk = 1""")
    key = "strftime(PERIODO,'%Y%m') || lpad(CAST(CAST(coalesce(VALOR_FOB_USD,0)*100 AS BIGINT) AS VARCHAR),18,'0')"
    fob_anios = ",\n  ".join(f"round(sum(VALOR_FOB_USD) FILTER (WHERE ANIO={a}),2) FOB_USD_{a}" for a in anios)
    con.execute(f"""CREATE OR REPLACE TABLE dir_base AS
    SELECT NIT, arg_max(RAZON_SOCIAL_EXPORTADOR, {key}) FILTER (WHERE NOT RAZON_SOCIAL_ENMASCARADA) RAZON_SOCIAL_DIAN,
      arg_max(CLASE_EXPORTADOR, {key}) CLASE_EXPORTADOR,
      {fob_anios},
      round(sum(VALOR_FOB_USD),2) FOB_USD_TOTAL,
      round(coalesce(sum(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA),0),2) FOB_USD_ORIGEN_ANTIOQUIA,
      round(sum(PESO_NETO_KGS),2) PESO_NETO_KGS_TOTAL,
      count(*) N_REGISTROS, count(DISTINCT NUMERO_FORMULARIO) N_DECLARACIONES,
      count(DISTINCT PERIODO) N_MESES_CON_EXPORTACION,
      strftime(min(PERIODO),'%Y-%m') PRIMER_MES, strftime(max(PERIODO),'%Y-%m') ULTIMO_MES,
      count(DISTINCT PAIS_DESTINO_NORM) N_PAISES_DESTINO, count(DISTINCT SUBPARTIDA_10D) N_SUBPARTIDAS,
      mode(ADUANA_SALIDA) ADUANA_SALIDA_PRINCIPAL, mode(MODO_TRANSPORTE) MODO_TRANSPORTE_PRINCIPAL
    FROM pj GROUP BY NIT""")
    con.execute("""CREATE OR REPLACE TABLE top_pais AS
    WITH t AS (SELECT NIT, PAIS_DESTINO_NORM p, sum(VALOR_FOB_USD) v FROM pj GROUP BY 1,2),
    r AS (SELECT *, row_number() OVER (PARTITION BY NIT ORDER BY v DESC, p) rk, sum(v) OVER (PARTITION BY NIT) tot FROM t)
    SELECT NIT, string_agg(p || ' (' || CAST(round(100*v/nullif(tot,0)) AS INT) || '%)', '; ' ORDER BY rk)
           FILTER (WHERE rk<=3) TOP3_PAISES_DESTINO FROM r GROUP BY NIT""")
    con.execute("""CREATE OR REPLACE TABLE top_sp AS
    WITH t AS (SELECT NIT, SUBPARTIDA_10D s, sum(VALOR_FOB_USD) v FROM pj GROUP BY 1,2),
    r AS (SELECT *, row_number() OVER (PARTITION BY NIT ORDER BY v DESC, s) rk FROM t)
    SELECT NIT, string_agg(s, '; ' ORDER BY rk) FILTER (WHERE rk<=5) TOP5_SUBPARTIDAS,
           max(CASE WHEN rk=1 THEN substr(s,1,2) END) CAPITULO_ARANCEL_PRINCIPAL FROM r GROUP BY NIT""")
    con.execute("""CREATE OR REPLACE TABLE orig AS
    WITH t AS (SELECT NIT, REGION_DE_ORIGEN o, sum(VALOR_FOB_USD) v FROM pj GROUP BY 1,2)
    SELECT NIT, arg_max(o, v) DEPTO_ORIGEN_PRINCIPAL_MERCANCIA FROM t GROUP BY 1""")
    con.execute("""CREATE OR REPLACE TABLE sect_nit AS
    WITH t AS (SELECT p.NIT, m.SECTOR_EXPORTACION sec, m.PRODUCTO_AGRICOLA_MADR prod, p.VALOR_FOB_USD v,
                      m.ES_MINERO_ENERGETICO me, m.ES_AGRICOLA_MADR ag FROM pj p JOIN subpartida_map m USING (SUBPARTIDA_10D)),
    s AS (SELECT NIT, arg_max(sec, v) sec FROM (SELECT NIT, sec, sum(v) v FROM t GROUP BY 1,2) GROUP BY 1),
    pr AS (SELECT NIT, arg_max(prod, v) prod FROM (SELECT NIT, prod, sum(v) v FROM t WHERE prod IS NOT NULL GROUP BY 1,2) GROUP BY 1),
    a AS (SELECT NIT, round(100*sum(v) FILTER (WHERE me)/nullif(sum(v),0),1) pme,
                 round(100*sum(v) FILTER (WHERE ag)/nullif(sum(v),0),1) pag FROM t GROUP BY 1)
    SELECT a.NIT, s.sec SECTOR_EXPORTADOR_PRINCIPAL, a.pme PCT_FOB_MINERO_ENERGETICO, a.pag PCT_FOB_AGRICOLA_MADR,
           pr.prod PRODUCTO_AGRICOLA_PRINCIPAL_MADR
    FROM a LEFT JOIN s USING (NIT) LEFT JOIN pr USING (NIT)""")

    # --- RUES: matrícula principal vigente ------------------------------------------------------
    # Prioridad: ACTIVA > NUEVA POR TRASLADO (la empresa cambió de domicilio) > sin estado > CANCELADA;
    # luego la renovada y la matriculada más recientemente. Excluye sucursales, agencias y personas naturales.
    con.execute(f"""CREATE OR REPLACE TABLE rues_nit AS
    WITH r AS (SELECT *, regexp_replace(coalesce(nullif(trim(nit),''), CASE WHEN clase_identificacion='NIT'
                    THEN trim(numero_identificacion) END),'^0+','') NIT_,
                 CASE WHEN estado_matricula='ACTIVA' THEN 1 WHEN estado_matricula ILIKE '%NUEVA%TRASLADO%' THEN 2
                      WHEN estado_matricula ILIKE '%CANCELADA%' THEN 4 ELSE 3 END prioridad
               FROM read_csv(['{rues_ant}','{rues_nac}'], all_varchar=true, union_by_name=true)
               WHERE coalesce(categoria_matricula,'') NOT ILIKE '%SUCURSAL%' AND coalesce(categoria_matricula,'') NOT ILIKE '%AGENCIA%'
                 AND coalesce(categoria_matricula,'') <> 'PERSONA NATURAL'),
    k AS (SELECT *, row_number() OVER (PARTITION BY NIT_ ORDER BY prioridad, coalesce(try_cast(fecha_renovacion AS BIGINT),0) DESC,
                 coalesce(try_cast(fecha_matricula AS BIGINT),0) DESC, camara_comercio, matricula) rk FROM r WHERE NIT_ <> ''),
    f AS (SELECT NIT_, bool_or(camara_comercio IN {CAM_ANT} AND prioridad <= 2) act_ant FROM k GROUP BY 1)
    SELECT k.NIT_ AS NIT, razon_social RAZON_SOCIAL_RUES, camara_comercio CAMARA_COMERCIO, matricula MATRICULA, cod_ciiu_act_econ_pri CIIU_PRINCIPAL_RUES,
      cod_ciiu_act_econ_sec CIIU_SECUNDARIO_RUES, organizacion_juridica ORGANIZACION_JURIDICA, fecha_matricula FECHA_MATRICULA,
      ultimo_ano_renovado ULTIMO_ANO_RENOVADO, estado_matricula ESTADO_MATRICULA,
      coalesce(f.act_ant, false) TIENE_MATRICULA_ACTIVA_EN_ANTIOQUIA
    FROM k JOIN f USING (NIT_) WHERE rk = 1""")
    con.execute(f"""CREATE OR REPLACE TABLE super AS
    WITH s AS (SELECT CAST(try_cast(nit AS DOUBLE) AS BIGINT)::VARCHAR NIT, *, try_cast(a_o_de_corte AS DOUBLE)::INT anio
               FROM read_csv('{supers}', all_varchar=true))
    SELECT NIT, arg_max(macrosector, anio) SS_MACROSECTOR, arg_max(ciiu, anio) SS_CIIU, arg_max(supervisor, anio) SS_SUPERVISOR,
      arg_max(departamento_domicilio, anio) SS_DEPARTAMENTO_DOMICILIO, arg_max(ciudad_domicilio, anio) SS_CIUDAD_DOMICILIO,
      arg_max(try_cast(replace(replace(ingresos_operacionales,'$',''),',','') AS DOUBLE), anio) SS_INGRESOS_OPERACIONALES_BILLONES_COP,
      arg_max(try_cast(replace(replace(total_activos,'$',''),',','') AS DOUBLE), anio) SS_TOTAL_ACTIVOS_BILLONES_COP,
      max(anio) SS_ANO_CORTE FROM s GROUP BY NIT""")

    # --- SECOP II por NIT (con o sin dígito de verificación) ----------------------------------
    con.execute(f"""CREATE OR REPLACE TABLE secop_nit AS
    WITH p AS (SELECT * FROM read_csv('{C.NITS_PATH}', all_varchar=true)),
    s AS (SELECT * FROM read_csv('{secop}', all_varchar=true)),
    j AS (SELECT coalesce(p1.NIT, p2.NIT) NIT_, s.* FROM s LEFT JOIN p p1 ON p1.NIT = s.documento_proveedor
          LEFT JOIN p p2 ON p2.NIT_DV = s.documento_proveedor)
    SELECT NIT_ AS NIT, sum(try_cast(n_contratos AS BIGINT)) SECOP_N_CONTRATOS,
      round(sum(try_cast(valor_total_contratos AS DOUBLE))) SECOP_VALOR_CONTRATOS_COP,
      substr(min(primera_firma),1,10) SECOP_PRIMERA_FIRMA, substr(max(ultima_firma),1,10) SECOP_ULTIMA_FIRMA,
      CASE WHEN bool_and(es_pyme_min='Si') THEN 'Sí' WHEN bool_and(es_pyme_max='No') THEN 'No' ELSE 'Mixto' END SECOP_ES_PYME,
      sum(try_cast(n_entidades AS INT)) SECOP_N_ENTIDADES
    FROM j WHERE NIT_ IS NOT NULL GROUP BY NIT_""")

    # --- Directorio final -----------------------------------------------------------------------
    flags = ",\n  ".join(f"(coalesce(FOB_USD_{a},0) >= {C.UMBRAL_EXPORTADOR_USD}) EXPORTADOR_{a}_MIN_1000USD" for a in anios)
    antioquena = f"(CAMARA_COMERCIO IN {CAM_ANT} OR (CAMARA_COMERCIO IS NULL AND DEPTO_DIAN_DIRECCION_PROPIA='ANTIOQUIA'))"
    con.execute(f"""CREATE OR REPLACE TABLE directorio AS
    WITH j AS (
      SELECT d.*, o.DEPTO_ORIGEN_PRINCIPAL_MERCANCIA,
        round(100*FOB_USD_ORIGEN_ANTIOQUIA/nullif(FOB_USD_TOTAL,0),1) PCT_FOB_ORIGEN_ANTIOQUIA,
        r.* EXCLUDE (NIT), sd.MUNICIPIO_DIAN_DIRECCION_PROPIA, sd.DEPTO_DIAN_DIRECCION_PROPIA,
        tp.TOP3_PAISES_DESTINO, ts.TOP5_SUBPARTIDAS, ts.CAPITULO_ARANCEL_PRINCIPAL,
        sn.* EXCLUDE (NIT), s.* EXCLUDE (NIT),
        (sc.NIT IS NOT NULL) PROVEEDOR_ESTADO_SECOP_II, sc.* EXCLUDE (NIT)
      FROM dir_base d LEFT JOIN orig o USING (NIT) LEFT JOIN rues_nit r USING (NIT) LEFT JOIN sede_dian sd USING (NIT)
      LEFT JOIN top_pais tp USING (NIT) LEFT JOIN top_sp ts USING (NIT) LEFT JOIN sect_nit sn USING (NIT)
      LEFT JOIN super s USING (NIT) LEFT JOIN secop_nit sc USING (NIT))
    SELECT coalesce(RAZON_SOCIAL_DIAN, RAZON_SOCIAL_RUES) AS RAZON_SOCIAL, *,
      CASE WHEN CAMARA_COMERCIO IN {CAM_ANT} THEN 'RUES: cámara de Antioquia'
           WHEN CAMARA_COMERCIO IS NOT NULL THEN 'RUES: cámara fuera de Antioquia'
           WHEN DEPTO_DIAN_DIRECCION_PROPIA='ANTIOQUIA' THEN 'Sin RUES; dirección DIAN propia en Antioquia'
           ELSE 'Sin RUES' END AS FUENTE_DOMICILIO,
      CASE WHEN {antioquena} THEN 'A. Empresa antioqueña (domicilio en Antioquia)'
           WHEN DEPTO_ORIGEN_PRINCIPAL_MERCANCIA='ANTIOQUIA' THEN 'B. Domicilio fuera; origen principal de su mercancía es Antioquia'
           WHEN FOB_USD_ORIGEN_ANTIOQUIA>0 THEN 'C. Domicilio fuera; parte de su mercancía es de origen Antioquia'
           ELSE 'D. Sin relación con Antioquia' END AS VINCULO_ANTIOQUIA,
      coalesce({antioquena}, false) AS EMPRESA_ANTIOQUENA,
      coalesce({antioquena} OR DEPTO_ORIGEN_PRINCIPAL_MERCANCIA='ANTIOQUIA', false) AS ES_EXPORTADOR_ANTIOQUENO,
      {flags}
    FROM j""")
    for v, n, *_ in con.execute("SELECT VINCULO_ANTIOQUIA, count(*) FROM directorio GROUP BY 1 ORDER BY 1").fetchall():
        log(f"{v}: {n:,} empresas")
    log(f"Con RUES: {con.execute('SELECT count(CAMARA_COMERCIO) FROM directorio').fetchone()[0]:,} · "
        f"con SECOP II: {con.execute('SELECT sum(PROVEEDOR_ESTADO_SECOP_II::int) FROM directorio').fetchone()[0]:,}")


if __name__ == "__main__":
    main()
