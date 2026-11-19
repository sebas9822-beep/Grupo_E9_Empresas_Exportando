"""Concentración de las exportaciones de Antioquia por país y producto, 2016-2025, y vulnerabilidad ante la pérdida de un comprador.

Fuente: bases estadísticas mensuales de exportaciones de la DIAN.
  2016-2023: archivos mensuales descargados de la DIAN (parquet/ generado por extraer.py)
  2024-2025: BD principal del proyecto (BD_exportaciones_Colombia_analitica.duckdb), misma fuente ya depurada
Reglas (iguales a la BD principal):
  Antioquia = departamento de origen de la mercancía 05. Venta al exterior = sin zonas francas colombianas ni destino Colombia.
  Producto = partida arancelaria (SA, 4 dígitos). Minero-energético = capítulos 26 y 27, 7103, 7106, 7108, 7110, 7112 y 720260.
"""
import pathlib, sys
import duckdb
import pandas as pd

BASE = pathlib.Path(__file__).parent
import os
BD_PRINCIPAL = os.environ.get("BD_PRINCIPAL", "datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb")  # python crear_bd_analitica.py
OUT = BASE / "out"; OUT.mkdir(exist_ok=True)
ANIOS = list(range(2016, 2026))
UMBRAL_PRODUCTO = 1e6          # producto relevante: al menos USD 1 M en el año
ZF = """(COD_PAIS_DESTINO IN ('ZF', 'XCF') OR COD_PAIS_DESTINO_ALF = 'XCF'
         OR upper(PAIS_DESTINO_FINAL) LIKE 'ZONA FRANCA%' OR upper(PAIS_DESTINO_FINAL) LIKE 'ZFP%')"""
ME = """(substr(SUBPARTIDA,1,2) IN ('26','27') OR substr(SUBPARTIDA,1,4) IN ('7103','7106','7108','7110','7112')
         OR substr(SUBPARTIDA,1,6) = '720260')"""


SECTOR_SQL = """CASE
  WHEN HS4 = '7108' THEN 'Oro'
  WHEN ES_ME THEN 'Otros minero-energéticos'
  WHEN HS4 IN ('0901','2101') THEN 'Café y derivados'
  WHEN HS4 = '0803' THEN 'Banano y plátano'
  WHEN HS4 = '0603' THEN 'Flores'
  WHEN HS2 BETWEEN '01' AND '24' THEN 'Otros agropecuarios y alimentos'
  WHEN HS2 BETWEEN '28' AND '40' THEN 'Químicos, plásticos y caucho'
  WHEN HS2 BETWEEN '50' AND '67' OR HS2 BETWEEN '41' AND '43' THEN 'Textiles, confecciones, cuero y calzado'
  WHEN HS2 BETWEEN '72' AND '85' THEN 'Metalmecánica, maquinaria y eléctricos'
  WHEN HS2 BETWEEN '86' AND '89' THEN 'Vehículos y material de transporte'
  ELSE 'Otras manufacturas' END"""


def construir(con):
    try:
        con.create_function('titulo', lambda x: x.title() if x else x, [str], str)
    except Exception:
        pass
    con.execute(f"ATTACH '{BD_PRINCIPAL}' AS p (READ_ONLY)")
    hist = sorted((BASE / "parquet").glob("20[12]*.parquet"))
    hist = [h.as_posix() for h in hist if int(h.stem[:4]) <= 2023]
    # Todas las líneas de exportación (todas las regiones) en un formato común
    partes = []
    if hist:
        partes.append(f"""
        SELECT ANIO_ARCHIVO AS ANIO, MES_ARCHIVO AS MES, 'DIAN mensual' AS FUENTE,
               nullif(ltrim(NIT_EXPORTADOR, '0'), '') AS NIT,
               lpad(COD_REGION_ORIGEN, 2, '0') AS COD_DEPTO_ORIGEN,
               CASE WHEN {ZF} THEN 'XCF' WHEN COD_PAIS_DESTINO_ALF IN ('ZZZ', 'ND') THEN 'ND' ELSE COD_PAIS_DESTINO_ALF END AS COD_PAIS,
               PAIS_DESTINO_FINAL AS PAIS_FUENTE,
               lpad(SUBPARTIDA, 10, '0') AS SUBPARTIDA, VALOR_FOB_USD AS FOB
        FROM read_parquet({hist})""")
    partes.append("""
        SELECT ANIO, MES, 'BD principal' AS FUENTE, NIT_EXPORTADOR AS NIT, COD_DEPTO_ORIGEN, COD_PAIS_DESTINO AS COD_PAIS,
               NULL AS PAIS_FUENTE, SUBPARTIDA, VALOR_FOB_USD AS FOB
        FROM p.hechos_analitica WHERE ANIO BETWEEN 2024 AND 2025""")
    con.execute("CREATE OR REPLACE TABLE lineas AS " + " UNION ALL ".join(partes))
    con.execute(f"""CREATE OR REPLACE TABLE lineas AS
        SELECT *, substr(SUBPARTIDA,1,4) AS HS4, substr(SUBPARTIDA,1,2) AS HS2, {ME} AS ES_ME,
               (COD_PAIS NOT IN ('XCF','COL') AND COD_PAIS IS NOT NULL) AS ES_EXTERIOR
        FROM lineas""")
    # Nombres de país: los de la BD principal; si un código histórico no está, el nombre de la fuente
    con.execute("""CREATE OR REPLACE TABLE paises AS
        WITH h AS (SELECT COD_PAIS, mode(PAIS_FUENTE) AS nom FROM lineas WHERE PAIS_FUENTE IS NOT NULL GROUP BY 1)
        SELECT coalesce(d.COD_PAIS, h.COD_PAIS) AS COD_PAIS, coalesce(d.PAIS, titulo(h.nom)) AS PAIS
        FROM p.dim_pais d FULL JOIN h USING (COD_PAIS)""")
    con.execute(f"CREATE OR REPLACE TABLE ant AS SELECT *, {SECTOR_SQL} AS SECTOR FROM lineas WHERE COD_DEPTO_ORIGEN = '05' AND ES_EXTERIOR")
    con.execute("CREATE OR REPLACE TABLE nac AS SELECT ANIO, HS4, COD_PAIS, sum(FOB) FOB FROM lineas WHERE ES_EXTERIOR GROUP BY ALL")
    con.execute("DETACH p")





def indicadores_anuales(con, filtro, etiqueta):
    """Concentración del departamento por año: países y productos."""
    return con.execute(f"""
    WITH b AS (SELECT * FROM ant WHERE {filtro}),
    tot AS (SELECT ANIO, sum(FOB) T, count(DISTINCT COD_PAIS) N_PAISES, count(DISTINCT HS4) N_PRODUCTOS,
                   count(DISTINCT NIT) N_NIT FROM b GROUP BY 1),
    pa AS (SELECT ANIO, COD_PAIS, sum(FOB) v FROM b GROUP BY 1, 2),
    pr AS (SELECT ANIO, HS4, sum(FOB) v FROM b GROUP BY 1, 2),
    rp AS (SELECT pa.*, v / T s, row_number() OVER (PARTITION BY pa.ANIO ORDER BY v DESC) r FROM pa JOIN tot USING (ANIO)),
    rr AS (SELECT pr.*, v / T s, row_number() OVER (PARTITION BY pr.ANIO ORDER BY v DESC) r FROM pr JOIN tot USING (ANIO))
    SELECT '{etiqueta}' AS ALCANCE, t.ANIO, round(t.T / 1e6, 1) AS FOB_MUSD, t.N_PAISES, t.N_PRODUCTOS, t.N_NIT,
      (SELECT p.PAIS FROM rp JOIN paises p USING (COD_PAIS) WHERE rp.ANIO = t.ANIO AND r = 1) AS PAIS_1,
      round(100 * (SELECT s FROM rp WHERE rp.ANIO = t.ANIO AND r = 1), 1) AS PCT_PAIS_1,
      round(100 * (SELECT sum(s) FROM rp WHERE rp.ANIO = t.ANIO AND r <= 3), 1) AS PCT_TOP3_PAISES,
      round(100 * (SELECT sum(s) FROM rp WHERE rp.ANIO = t.ANIO AND r <= 5), 1) AS PCT_TOP5_PAISES,
      round(10000 * (SELECT sum(s * s) FROM rp WHERE rp.ANIO = t.ANIO)) AS HHI_PAISES,
      round(1 / (SELECT sum(s * s) FROM rp WHERE rp.ANIO = t.ANIO), 1) AS N_EQUIV_PAISES,
      round(100 * (SELECT sum(s) FROM rr WHERE rr.ANIO = t.ANIO AND r <= 3), 1) AS PCT_TOP3_PRODUCTOS,
      round(10000 * (SELECT sum(s * s) FROM rr WHERE rr.ANIO = t.ANIO)) AS HHI_PRODUCTOS,
      round(1 / (SELECT sum(s * s) FROM rr WHERE rr.ANIO = t.ANIO), 1) AS N_EQUIV_PRODUCTOS
    FROM tot t ORDER BY t.ANIO""").df()


def por_producto(con, anios):
    """CR3 de países por producto (partida) para un año o un periodo (suma de años)."""
    lista = ",".join(str(a) for a in anios)
    return con.execute(f"""
    WITH b AS (SELECT * FROM ant WHERE ANIO IN ({lista})),
    tot AS (SELECT sum(FOB) T FROM b),
    pp AS (SELECT HS4, COD_PAIS, sum(FOB) v FROM b GROUP BY 1, 2 HAVING sum(FOB) > 0),
    pr AS (SELECT HS4, sum(v) VT, count(*) N_PAISES FROM pp GROUP BY 1),
    r AS (SELECT pp.*, v / VT s, row_number() OVER (PARTITION BY pp.HS4 ORDER BY v DESC) rk FROM pp JOIN pr USING (HS4)),
    nit AS (SELECT HS4, count(DISTINCT NIT) N_EMPRESAS FROM b GROUP BY 1)
    SELECT pr.HS4, any_value(sec.SECTOR) AS SECTOR,
      round(pr.VT / {len(anios)} / 1e6, 2) AS FOB_MUSD_ANUAL, round(100 * pr.VT / (SELECT T FROM tot), 2) AS PCT_DEL_TOTAL,
      pr.N_PAISES, any_value(nit.N_EMPRESAS) AS N_EMPRESAS,
      max(CASE WHEN rk = 1 THEN p.PAIS END) AS PAIS_1, round(100 * max(CASE WHEN rk = 1 THEN s END), 1) AS PCT_PAIS_1,
      max(CASE WHEN rk = 2 THEN p.PAIS END) AS PAIS_2, round(100 * max(CASE WHEN rk = 2 THEN s END), 1) AS PCT_PAIS_2,
      max(CASE WHEN rk = 3 THEN p.PAIS END) AS PAIS_3, round(100 * max(CASE WHEN rk = 3 THEN s END), 1) AS PCT_PAIS_3,
      round(100 * sum(s) FILTER (WHERE rk <= 3), 1) AS PCT_TOP3_PAISES,
      round(10000 * sum(s * s)) AS HHI_PAISES, round(1 / sum(s * s), 1) AS N_EQUIV_PAISES
    FROM pr JOIN r USING (HS4) LEFT JOIN paises p USING (COD_PAIS) LEFT JOIN nit USING (HS4)
    LEFT JOIN (SELECT HS4, mode(SECTOR) SECTOR FROM b GROUP BY 1) sec ON sec.HS4 = pr.HS4
    GROUP BY pr.HS4, pr.VT, pr.N_PAISES ORDER BY pr.VT DESC""").df()


if __name__ == "__main__":
    con = duckdb.connect(str(BASE / "analisis.duckdb"))
    con.execute("SET memory_limit='5GB'")
    construir(con)
    print(con.execute("SELECT FUENTE, ANIO, count(*), round(sum(FOB)/1e6,1) FROM ant GROUP BY ALL ORDER BY 2").df().to_string())


def escenarios(con, anio, top=6):
    """Pérdida total de un comprador: qué FOB, qué productos y cuántas empresas quedan expuestas."""
    paises = con.execute(f"""SELECT COD_PAIS FROM ant WHERE ANIO = {anio} GROUP BY 1 ORDER BY sum(FOB) DESC LIMIT {top}""").fetchall()
    paises_nme = con.execute(f"""SELECT COD_PAIS FROM ant WHERE ANIO = {anio} AND NOT ES_ME GROUP BY 1 ORDER BY sum(FOB) DESC LIMIT {top}""").fetchall()
    lista = ",".join(f"'{p}'" for p in dict.fromkeys([p for p, in paises] + [p for p, in paises_nme]))
    return con.execute(f"""
    WITH b AS (SELECT * FROM ant WHERE ANIO = {anio}),
    tot AS (SELECT sum(FOB) T, sum(FOB) FILTER (WHERE NOT ES_ME) TN FROM b),
    prod AS (SELECT HS4, sum(FOB) V FROM b GROUP BY 1 HAVING sum(FOB) >= {UMBRAL_PRODUCTO}),
    pp AS (SELECT b.HS4, COD_PAIS, sum(FOB) / any_value(V) s, sum(FOB) v FROM b JOIN prod USING (HS4) GROUP BY 1, 2),
    emp AS (SELECT NIT, sum(FOB) V FROM b WHERE NIT IS NOT NULL GROUP BY 1 HAVING sum(FOB) >= 10000),
    ep AS (SELECT b.NIT, COD_PAIS, sum(FOB) / any_value(V) s FROM b JOIN emp USING (NIT) GROUP BY 1, 2)
    SELECT p.PAIS, c.COD_PAIS,
      round(sum(b.FOB) / 1e6, 1) AS FOB_MUSD, round(100 * sum(b.FOB) / any_value(tot.T), 1) AS PCT_TOTAL,
      round(sum(b.FOB) FILTER (WHERE NOT b.ES_ME) / 1e6, 1) AS FOB_NME_MUSD,
      round(100 * sum(b.FOB) FILTER (WHERE NOT b.ES_ME) / any_value(tot.TN), 1) AS PCT_NME,
      (SELECT count(*) FROM pp WHERE pp.COD_PAIS = c.COD_PAIS AND s >= 0.5) AS N_PRODUCTOS_DEPENDIENTES_50,
      (SELECT round(sum(prod.V) / 1e6, 1) FROM pp JOIN prod USING (HS4) WHERE pp.COD_PAIS = c.COD_PAIS AND s >= 0.5) AS FOB_PRODUCTOS_DEPENDIENTES_MUSD,
      (SELECT count(*) FROM ep WHERE ep.COD_PAIS = c.COD_PAIS AND s >= 0.5) AS N_EMPRESAS_DEPENDIENTES_50,
      (SELECT count(*) FROM ep WHERE ep.COD_PAIS = c.COD_PAIS AND s >= 0.999) AS N_EMPRESAS_SOLO_ESE_PAIS
    FROM (SELECT unnest([{lista}]) AS COD_PAIS) c JOIN b USING (COD_PAIS) LEFT JOIN paises p USING (COD_PAIS), tot
    GROUP BY p.PAIS, c.COD_PAIS ORDER BY FOB_MUSD DESC""").df()


def empresas(con):
    """Dependencia de las empresas exportadoras (NIT con al menos USD 10.000 de origen Antioquia en el año)."""
    return con.execute("""
    WITH e AS (SELECT ANIO, NIT, COD_PAIS, sum(FOB) v FROM ant WHERE NIT IS NOT NULL GROUP BY ALL),
    t AS (SELECT ANIO, NIT, sum(v) V, count(*) N, max(v) / sum(v) S1 FROM e GROUP BY ALL HAVING sum(v) >= 10000)
    SELECT ANIO, count(*) AS N_EMPRESAS,
      round(100 * avg((N = 1)::INT), 1) AS PCT_UN_SOLO_PAIS,
      round(100 * avg((S1 >= 0.5)::INT), 1) AS PCT_MITAD_O_MAS_EN_UN_PAIS,
      round(median(N), 1) AS MEDIANA_PAISES,
      round(100 * sum(V) FILTER (WHERE S1 >= 0.5) / sum(V), 1) AS PCT_FOB_EMPRESAS_DEPENDIENTES
    FROM t GROUP BY 1 ORDER BY 1""").df()


def alternativas(con, anio, productos, top_n=5):
    """Mercados ya abiertos por Colombia: países fuera del top 3 de Antioquia para la partida, donde otros departamentos
    venden al menos USD 1 M y Antioquia envía menos del 5 % de lo que exporta de esa partida."""
    lista = ",".join(f"'{h}'" for h in productos)
    return con.execute(f"""
    WITH a AS (SELECT HS4, COD_PAIS, sum(FOB) v FROM ant WHERE ANIO = {anio} AND HS4 IN ({lista}) GROUP BY 1, 2),
    ta AS (SELECT HS4, sum(v) VT FROM a GROUP BY 1),
    ra AS (SELECT a.*, v / VT s, row_number() OVER (PARTITION BY HS4 ORDER BY v DESC) rk FROM a JOIN ta USING (HS4)),
    n AS (SELECT HS4, COD_PAIS, sum(FOB) v FROM nac WHERE ANIO = {anio} AND HS4 IN ({lista}) GROUP BY 1, 2),
    c AS (SELECT n.HS4, n.COD_PAIS, n.v - coalesce(ra.v, 0) AS FOB_OTROS, coalesce(ra.s, 0) AS PESO_ANT, coalesce(ra.rk, 999) AS RK_ANT
          FROM n LEFT JOIN ra USING (HS4, COD_PAIS)),
    alt AS (SELECT * FROM c WHERE FOB_OTROS >= {UMBRAL_PRODUCTO} AND PESO_ANT < 0.05 AND RK_ANT > 3),
    r AS (SELECT alt.*, p.PAIS, row_number() OVER (PARTITION BY HS4 ORDER BY FOB_OTROS DESC) rk FROM alt LEFT JOIN paises p USING (COD_PAIS))
    SELECT HS4, count(*) AS N_MERCADOS_ALTERNOS, round(sum(FOB_OTROS) / 1e6, 1) AS FOB_OTROS_DEPTOS_MUSD,
           string_agg(PAIS || ' (' || round(FOB_OTROS / 1e6, 1) || ')', '; ' ORDER BY rk) FILTER (WHERE rk <= {top_n}) AS PRINCIPALES
    FROM r GROUP BY 1""").df()


def sectores(con, anio):
    return con.execute(f"""
    WITH b AS (SELECT * FROM ant WHERE ANIO = {anio}),
    s AS (SELECT SECTOR, sum(FOB) VT, count(DISTINCT COD_PAIS) N FROM b GROUP BY 1),
    sp AS (SELECT SECTOR, COD_PAIS, sum(FOB) v FROM b GROUP BY 1, 2),
    r AS (SELECT sp.*, v / VT sh, row_number() OVER (PARTITION BY SECTOR ORDER BY v DESC) rk FROM sp JOIN s USING (SECTOR))
    SELECT s.SECTOR, round(s.VT / 1e6, 1) FOB_MUSD, round(100 * s.VT / sum(s.VT) OVER (), 1) PCT, s.N AS N_PAISES,
      max(CASE WHEN rk = 1 THEN p.PAIS END) PAIS_1, round(100 * max(CASE WHEN rk = 1 THEN sh END), 1) PCT_PAIS_1,
      round(100 * sum(sh) FILTER (WHERE rk <= 3), 1) PCT_TOP3_PAISES, round(10000 * sum(sh * sh)) HHI_PAISES
    FROM s JOIN r USING (SECTOR) LEFT JOIN paises p USING (COD_PAIS) GROUP BY s.SECTOR, s.VT, s.N ORDER BY s.VT DESC""").df()
