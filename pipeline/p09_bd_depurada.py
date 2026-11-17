"""Paso 9 · BD única depurada (modelo estrella) a partir de los productos del paso 7.

Entradas (data/processed/):
  exportaciones_nacional/*.parquet          líneas DIAN (base de todo)
  directorio_exportadores_nacional.csv      atributos externos por NIT (RUES, Supersociedades, SECOP)
  tabla_subpartidas_sector.csv              sector de cada subpartida
  validacion_mincit_nme.csv / validacion_madr_agricolas.csv   cifras oficiales para validar
Salidas:
  data/processed/bd_depurada/hechos_exportaciones/hechos_AAAA_MM.parquet   tabla de hechos, un archivo por mes
  data/processed/bd_depurada/<tabla>.parquet                               dimensiones, catálogos, log, diccionario
  data/processed/bd_depurada/BD_exportaciones_Colombia_depurada.duckdb     todo en un archivo (no se versiona)
  docs/diccionario_bd_depurada.csv, docs/log_bd_depurada.csv

Las reglas de limpieza están explicadas en docs/limpieza_bd_depurada.md. Quien clone el repositorio puede
armar el .duckdb sin correr este paso: python crear_bd_depurada.py
"""
import argparse
import datetime
import pathlib
import shutil
import sys

import duckdb
import pandas as pd
import pycountry

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
import crear_bd_depurada  # noqa: E402
from pipeline import diccionario_bd_depurada  # noqa: E402
from pipeline.comun import log  # noqa: E402

N = C.OUT_NACIONAL / "*.parquet"
DIR = C.PROCESSED / "directorio_exportadores_nacional.csv"
SUB = C.PROCESSED / "tabla_subpartidas_sector.csv"
VAL_MINCIT = C.PROCESSED / "validacion_mincit_nme.csv"
VAL_MADR = C.PROCESSED / "validacion_madr_agricolas.csv"
TRABAJO = C.INTERIM / "bd_depurada_trabajo.duckdb"

DEPTOS = [('00', 'DEPARTAMENTOS VARIOS'), ('05', 'ANTIOQUIA'), ('08', 'ATLÁNTICO'), ('11', 'BOGOTÁ, D.C.'), ('13', 'BOLÍVAR'),
          ('15', 'BOYACÁ'), ('17', 'CALDAS'), ('18', 'CAQUETÁ'), ('19', 'CAUCA'), ('20', 'CESAR'), ('23', 'CÓRDOBA'),
          ('25', 'CUNDINAMARCA'), ('27', 'CHOCÓ'), ('41', 'HUILA'), ('44', 'LA GUAJIRA'), ('47', 'MAGDALENA'), ('50', 'META'),
          ('52', 'NARIÑO'), ('54', 'NORTE DE SANTANDER'), ('63', 'QUINDÍO'), ('66', 'RISARALDA'), ('68', 'SANTANDER'),
          ('70', 'SUCRE'), ('73', 'TOLIMA'), ('76', 'VALLE DEL CAUCA'), ('81', 'ARAUCA'), ('85', 'CASANARE'), ('86', 'PUTUMAYO'),
          ('88', 'ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA'), ('91', 'AMAZONAS'), ('94', 'GUAINÍA'),
          ('95', 'GUAVIARE'), ('97', 'VAUPÉS'), ('99', 'VICHADA')]
# Nombres de país que solo aparecen en 2024 (en MAYÚSCULA) o que no son países
PAISES_MANUAL = {'XCF': 'Zona franca (Colombia)', 'ND': 'No declarado', 'NER': 'Níger', 'NPL': 'Nepal', 'SYC': 'Seychelles',
                 'BWA': 'Botswana', 'BFA': 'Burkina Faso', 'LAO': 'República Democrática Popular Lao',
                 'IRN': 'Irán (República Islámica del)'}

ZF = """(COD_PAIS_DESTINO IN ('ZF', 'XCF') OR COD_PAIS_DESTINO_ALF = 'XCF'
         OR upper(PAIS_DESTINO_FINAL) LIKE 'ZONA FRANCA%' OR upper(PAIS_DESTINO_FINAL) LIKE 'ZFP%')"""


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    C.INTERIM.mkdir(parents=True, exist_ok=True)
    TRABAJO.unlink(missing_ok=True)
    c = duckdb.connect(str(TRABAJO))
    c.execute(f"SET threads=2; SET memory_limit='3GB'; SET preserve_insertion_order=false; SET temp_directory='{(C.INTERIM / 'tmp_duckdb').as_posix()}'")
    LOG = []

    def reg_log(etapa, regla, filas=None, fob=None, detalle=''):
        LOG.append((len(LOG) + 1, etapa, regla, None if filas is None else int(filas),
                    None if fob is None else round(float(fob), 2), detalle))

    def one(sql):
        return c.execute(sql).fetchone()

    def fmt(n, d=0):
        return f"{n:,.{d}f}".replace(',', '_').replace('.', ',').replace('_', '.')

    def reg(name, df):
        # pandas 3 usa el dtype 'str', que DuckDB 1.4 aún no reconoce: se pasa a object
        df = df.copy()
        for col in df.columns:
            if str(df[col].dtype) in ('str', 'string') or str(df[col].dtype).startswith('string'):
                df[col] = df[col].astype(object).where(df[col].notna(), None)
        c.register(name, df)

    # ------------------------------------------------------------ 0. macros de limpieza
    c.execute(r"""
    CREATE TEMP MACRO limpia(x) AS nullif(trim(regexp_replace(replace(replace(CAST(x AS VARCHAR), '\t', ' '), chr(9), ' '), '\s+', ' ', 'g')), '');
    CREATE TEMP MACRO limpia_nulo(x) AS CASE WHEN limpia(x) IN ('0', '-', '.', '..', 'NULL', 'NONE', 'NAN') THEN NULL ELSE limpia(x) END;
    CREATE TEMP MACRO sin_comillas(x) AS nullif(trim(regexp_replace(limpia(x), '^["'' ]+|["'' ]+$', '', 'g')), '');
    CREATE TEMP MACRO nit_limpio(x) AS nullif(regexp_replace(trim(CAST(x AS VARCHAR)), '^0+', ''), '');
    CREATE TEMP MACRO aaaamm(x) AS CASE WHEN trim(x) ~ '^[0-9]{6}$' AND trim(x) <> '000000' THEN try_strptime(trim(x) || '01', '%Y%m%d')::DATE END;
    """)

    # ------------------------------------------------------------ 1. carga y llave técnica
    c.execute(f"""CREATE TEMP TABLE s AS
    SELECT row_number() OVER (ORDER BY PERIODO, NUMERO_FORMULARIO, try_cast(NUMERO_SERIE AS INT), NIT_EXPORTADOR, SUBPARTIDA, VALOR_FOB_USD,
                                       FECHA_DECLARACION_EXPORTACION, PESO_NETO_KGS, ARCHIVO_FUENTE) AS ID_REGISTRO, *
    FROM read_parquet('{N.as_posix()}')""")
    n0, fob0 = one("SELECT count(*), sum(VALOR_FOB_USD) FROM s")
    n_ant = one("SELECT count(*) FROM s WHERE ORIGEN_MERCANCIA_ANTIOQUIA OR NIT_ES_EXPORTADOR_ANTIOQUENO")[0]
    reg_log('1. Carga', 'Base única: las líneas DIAN nacionales del paso 7 (exportaciones_nacional/)', n0, fob0,
            f'exportaciones_antioquia/ es un subconjunto exacto de estas líneas ({fmt(n_ant)}) y no se carga aparte: queda como la vista vw_exportaciones_antioquia. '
            'El directorio y las tablas de apoyo se recalculan o se vuelven dimensiones.')
    log(f"Cargadas {n0:,} líneas")

    # ------------------------------------------------------------ 2. filas idénticas
    cols = [r[0] for r in c.execute("DESCRIBE s").fetchall() if r[0] not in ('ID_REGISTRO', 'ARCHIVO_FUENTE')]
    firma = "md5(concat_ws('|', " + ", ".join(f"coalesce(CAST(\"{x}\" AS VARCHAR), '<NULL>')" for x in cols) + "))"
    c.execute(f"""CREATE TEMP TABLE dup AS
    SELECT ID_REGISTRO, row_number() OVER (PARTITION BY firma ORDER BY ID_REGISTRO) rn
    FROM (SELECT ID_REGISTRO, {firma} firma FROM s) QUALIFY count(*) OVER (PARTITION BY firma) > 1""")
    nd, fobd = one("SELECT count(*), coalesce(sum(s.VALOR_FOB_USD), 0) FROM s JOIN dup d USING (ID_REGISTRO) WHERE d.rn > 1")
    reg_log('2. Duplicados', 'Filas idénticas a otra en todas las columnas: se evaluaron, se CONSERVAN y se marcan con FLAG_REGISTRO_IDENTICO', nd, fobd,
            'Todas son líneas sin número de formulario, donde la DIAN no deja un identificador que distinga envíos. Con ellas el FOB trimestral cuadra '
            'con la cifra oficial de MinCIT; sin ellas 2025-T1 queda 0,28 % por debajo (un embarque de crudo de USD 33 M). Se tratan como envíos '
            'iguales legítimos (p. ej. contenedores de banano idénticos el mismo día). Para excluirlas: WHERE NOT FLAG_REGISTRO_IDENTICO.')
    log(f"Filas idénticas: {nd}")

    # ------------------------------------------------------------ 3. ISO alfa-2 → alfa-3 para banderas de 2024
    iso2 = [r[0] for r in c.execute("SELECT DISTINCT COD_NACIONALIDAD_BANDERA FROM s WHERE length(COD_NACIONALIDAD_BANDERA) = 2").fetchall()]
    xw = [(x, (pycountry.countries.get(alpha_2=x).alpha_3 if pycountry.countries.get(alpha_2=x) else None)) for x in iso2]
    reg('xw_df', pd.DataFrame(xw, columns=['ISO2', 'ISO3']))
    c.execute("CREATE TEMP TABLE iso2_iso3 AS SELECT * FROM xw_df")
    sin_iso = [a for a, b in xw if b is None and a != 'ND']
    n_zf_mal = one(f"SELECT count(*) FROM s WHERE {ZF} AND COD_PAIS_DESTINO_ALF <> 'XCF'")[0]

    # ------------------------------------------------------------ 4. tabla de hechos
    c.execute(f"""CREATE TABLE hechos_exportaciones AS
    SELECT
      ID_REGISTRO, PERIODO, CAST(ANIO AS SMALLINT) ANIO, CAST(MES AS TINYINT) MES,
      try_strptime(FECHA_DECLARACION_EXPORTACION, '%Y%m%d')::DATE AS FECHA_DECLARACION,
      nullif(trim(NUMERO_FORMULARIO), '0') AS NUMERO_FORMULARIO,
      try_cast(NUMERO_SERIE AS INTEGER) AS NUMERO_SERIE,
      replace(TIPO_DESPACHO, 'Correción', 'Corrección') AS TIPO_DESPACHO,
      replace(TIPO_DE_DATOS, 'despúes', 'después') AS TIPO_DATOS,
      CASE TIPO_DE_EMBARQUE WHEN 'Unico' THEN 'Único' ELSE TIPO_DE_EMBARQUE END AS TIPO_EMBARQUE,
      limpia_nulo(NUM__DECLA_EXPORTACION_ANT) AS NUM_DECLARACION_ANTERIOR,
      aaaamm(FECH_DECLA_EXPORTACION_ANT) AS PERIODO_DECLARACION_ANTERIOR,
      limpia_nulo(NUM_DECLARACION_PRECEDENTE) AS NUM_DECLARACION_PRECEDENTE,
      aaaamm(FECH_DECLA_PRECEDENTE) AS PERIODO_DECLARACION_PRECEDENTE,
      limpia_nulo(COD_MODALIDAD_PRECEDENTE) AS COD_MODALIDAD_PRECEDENTE,
      limpia_nulo(NUM_SOLICITUD_AUTO_EMBARQUE) AS NUM_AUTORIZACION_EMBARQUE,
      aaaamm(FECHA_SOLICITUD_AUTO_EMBARQUE) AS PERIODO_AUTORIZACION_EMBARQUE,
      nit_limpio(NIT_EXPORTADOR) AS NIT_EXPORTADOR,
      TIPO_IDENT AS TIPO_IDENTIFICACION,
      (nit_limpio(NIT_EXPORTADOR) IS NULL) AS ES_PERSONA_NATURAL,
      (nit_limpio(NIT_EXPORTADOR) IS NOT NULL AND (RAZON_SOCIAL_EXPORTADOR IS NULL OR RAZON_SOCIAL_EXPORTADOR = 'PERSONA NATURAL')) AS FLAG_RAZON_SOCIAL_ENMASCARADA,
      CLASE_EXPORTADOR, TIPO_USUARIO,
      limpia_nulo(upper(DIREC_EXPORTADOR)) AS DIRECCION_DECLARADA,
      COD_MPIO_DIRECCION_DECLARADA, DIRECCION_DECLARADA_EN_ANTIOQUIA,
      nit_limpio(NIT_DECLARANTE) AS NIT_DECLARANTE,
      html_unescape(sin_comillas(limpia_nulo(RAZON_SOCIAL_DESTINATARIO))) AS RAZON_SOCIAL_DESTINATARIO,
      html_unescape(limpia_nulo(DOMICILIO_DESTINATARIO)) AS DOMICILIO_DESTINATARIO,
      upper(html_unescape(limpia_nulo(CIUDAD_DESTINATARIO))) AS CIUDAD_DESTINATARIO,
      CASE WHEN {ZF} THEN 'XCF' ELSE COD_PAIS_DESTINO_ALF END AS COD_PAIS_DESTINO,
      {ZF} AS ES_DESTINO_ZONA_FRANCA,
      CASE WHEN {ZF} THEN COD_PAIS_DESTINO_NUM END AS COD_ZONA_FRANCA_DESTINO,
      OFICINA,
      lpad(trim(COD_ADUANA_DESPACHO), 2, '0') AS COD_ADUANA_DESPACHO,
      lpad(trim(COD_ADUANA_SALIDA), 2, '0') AS COD_ADUANA_SALIDA,
      limpia_nulo(COD_LUG_SALIDA_ALF) AS COD_LUGAR_SALIDA,
      lpad(trim(COD_REGION_PROCEDENCIA), 2, '0') AS COD_DEPTO_PROCEDENCIA,
      lpad(trim(COD_REGION_ORIGEN), 2, '0') AS COD_DEPTO_ORIGEN,
      ORIGEN_MERCANCIA_ANTIOQUIA,
      COD_MODO_TRANSPORTE,
      CASE WHEN COD_NACIONALIDAD_BANDERA IS NULL OR COD_NACIONALIDAD_BANDERA = 'ND' THEN 'ND'
           WHEN length(COD_NACIONALIDAD_BANDERA) = 2 THEN coalesce(x.ISO3, COD_NACIONALIDAD_BANDERA)
           ELSE COD_NACIONALIDAD_BANDERA END AS COD_PAIS_BANDERA,
      lpad(trim(COD_MODALIDAD_EXPORTACION), 3, '0') AS COD_MODALIDAD_EXPORTACION,
      COD_REGIMEN_CAN, FORMA_PAGO, TIPO_CERTIFICADO_ORIGEN,
      (SISTEMAS_ESPECIALES = 'SI') AS SISTEMAS_ESPECIALES,
      (EXPORTACION_EN_TRANSITO = 'SI') AS EXPORTACION_EN_TRANSITO,
      COD_MONEDA_TRANSACCION,
      SUBPARTIDA_10D AS SUBPARTIDA,
      COD_UNIDAD_FISICA_ALF AS COD_UNIDAD_FISICA,
      CANTIDAD_UNIDADES_FISICAS, PESO_BRUTO_KGS, PESO_NETO_KGS,
      VALOR_FOB_USD, VALOR_FOB_PESOS AS VALOR_FOB_COP,
      VLR_SERIE_AGREGADO_NAL_USD AS VALOR_AGREGADO_NACIONAL_USD,
      VALOR_SERIE_FLETES_USD AS VALOR_FLETES_USD,
      VALOR_SERIE_SEGUROS_USD AS VALOR_SEGUROS_USD,
      VLR_SERIE_OTROS_GASTOS_USD AS VALOR_OTROS_GASTOS_USD,
      (coalesce(PESO_NETO_KGS, 0) = 0 OR coalesce(PESO_BRUTO_KGS, 0) = 0) AS FLAG_PESO_CERO,
      coalesce(dup.rn > 1, false) AS FLAG_REGISTRO_IDENTICO,
      ARCHIVO_FUENTE
    FROM s LEFT JOIN iso2_iso3 x ON x.ISO2 = s.COD_NACIONALIDAD_BANDERA LEFT JOIN dup USING (ID_REGISTRO)
    ORDER BY ID_REGISTRO""")
    ncols = len(c.execute("DESCRIBE hechos_exportaciones").fetchall())
    log(f"Hechos: {ncols} columnas")

    r = one("""SELECT count(*), sum(VALOR_FOB_USD), count(DISTINCT nit_limpio(NIT_EXPORTADOR)) FROM s
               WHERE nit_limpio(NIT_EXPORTADOR) IS NOT NULL AND (RAZON_SOCIAL_EXPORTADOR IS NULL OR RAZON_SOCIAL_EXPORTADOR = 'PERSONA NATURAL')""")
    reg_log('3. Exportador', 'Persona natural = sin NIT publicado (ES_PERSONA_NATURAL); las líneas con NIT de empresa y razón social "PERSONA NATURAL" o vacía se atribuyen a la empresa', r[0], r[1],
            f'En el archivo DIAN de sep-2024 la razón social de {fmt(r[2])} NIT de empresas viene enmascarada. Si se usa la razón social para separar personas naturales, '
            'esas empresas pierden septiembre de 2024 en el directorio. Las líneas quedan marcadas con FLAG_RAZON_SOCIAL_ENMASCARADA.')
    r = one("SELECT count(*), sum(VALOR_FOB_USD) FROM s WHERE nit_limpio(NIT_EXPORTADOR) IS NULL")
    reg_log('3. Exportador', 'NIT sin dígito de verificación ni ceros a la izquierda; el NIT "0" o vacío de las personas naturales queda en NULL', r[0], r[1])
    r = one(f"SELECT count(*), sum(VALOR_FOB_USD) FROM s WHERE {ZF}")
    reg_log('4. Destino', 'Zonas francas colombianas como destino: código XCF, bandera ES_DESTINO_ZONA_FRANCA y zona franca específica (dim_zona_franca)', r[0], r[1],
            f'En la entrada, PAIS_DESTINO_NORM ponía "ZFP de Rionegro S.A." a todas las zonas francas (31 distintas) y {n_zf_mal} líneas de zona franca venían con código de Puerto Rico (PRI).')
    r = one("SELECT count(*) FROM s WHERE ANIO = 2024")
    reg_log('4. Destino', 'País destino y país de bandera con un solo código ISO 3166 alfa-3 y un solo nombre (dim_pais)', r[0], None,
            'La DIAN cambió de esquema en 2025: 2024 usa ISO alfa-2 y códigos numéricos propios con nombres en MAYÚSCULA; 2025-2026 usa alfa-3 y M49 '
            'con nombres en tipo oración. Se retiran COD_PAIS_DESTINO_NUM, COD_PAIS_DESTINO, PAIS_DESTINO_FINAL, PAIS_DESTINO_NORM, BANDERA, '
            'COD_NACIONALIDAD_BANDERA y NACIONALIDAD_BANDERA.' + (f' Códigos de bandera sin equivalencia ISO: {sin_iso}.' if sin_iso else ''))
    r = one("SELECT count(*) FROM s WHERE TIPO_DESPACHO = 'Correción' OR TIPO_DE_DATOS LIKE '%despúes%'")
    reg_log('5. Textos', 'Errores de digitación de la fuente: "Correción" → "Corrección", "despúes" → "después" (y "Unico" → "Único" en todas las líneas)', r[0])
    r = one("""SELECT count(*) FROM s WHERE RAZON_SOCIAL_DESTINATARIO LIKE '%  %' OR DOMICILIO_DESTINATARIO LIKE '%  %' OR CIUDAD_DESTINATARIO LIKE '%  %'
               OR DIREC_EXPORTADOR LIKE '%  %' OR RAZON_SOCIAL_EXPORTADOR LIKE '%  %' OR RAZON_SOCIAL_DECLARANTE LIKE '%  %' OR ADUANA_SALIDA LIKE '%  %'""")
    reg_log('5. Textos', 'Espacios dobles, tabulaciones, comillas sobrantes y entidades HTML (p. ej. "&#304STANBUL" → "İSTANBUL") en nombres, direcciones y ciudades', r[0])
    r = one("SELECT count(*) FROM s WHERE COD_MODALIDAD_EXPORTACION IN ('2', '4')")
    reg_log('6. Códigos', 'Ceros a la izquierda homogéneos: modalidad a 3 dígitos ("2" → "002"), aduana y departamento a 2 dígitos, subpartida a 10', r[0])
    r = one("SELECT count(*) FROM s WHERE NUMERO_FORMULARIO = '0'")
    r2 = one("""SELECT count(*) FROM s WHERE NUMERO_FORMULARIO = '0' OR NUM__DECLA_EXPORTACION_ANT = '0' OR NUM_DECLARACION_PRECEDENTE = '0'
                OR FECH_DECLA_PRECEDENTE = '0' OR NIT_DECLARANTE = '0'""")
    reg_log('6. Códigos', 'Valores "0" que significan "no aplica" pasan a NULL (formulario, declaración anterior y precedente, sus fechas, NIT declarante)', r2[0], None,
            f'{fmt(r[0])} líneas sin número de formulario (sobre todo hidrocarburos de Ecopetrol, Reficar y Frontera) se conservan: son legítimas y suman cerca del 25 % del FOB.')
    reg_log('6. Códigos', 'Fechas guardadas como texto (AAAAMMDD y AAAAMM) convertidas a tipo fecha', None)
    r = one("SELECT count(*) FROM s WHERE coalesce(PESO_NETO_KGS, 0) = 0 OR coalesce(PESO_BRUTO_KGS, 0) = 0")
    reg_log('7. Calidad', 'Líneas con peso neto o bruto en cero: se conservan y se marcan con FLAG_PESO_CERO', r[0])
    r = one("""WITH t AS (SELECT PERIODO, VALOR_FOB_PESOS / VALOR_FOB_USD trm FROM s WHERE VALOR_FOB_USD > 0)
               SELECT (SELECT count(*) FROM s WHERE VALOR_FOB_USD <= 0 OR VALOR_FOB_USD IS NULL)
                    + (SELECT count(*) FROM s WHERE PESO_NETO_KGS > PESO_BRUTO_KGS * 1.0001)
                    + (SELECT count(*) FROM s WHERE try_strptime(FECHA_DECLARACION_EXPORTACION, '%Y%m%d') IS NULL)
                    + (SELECT count(*) FROM (SELECT trm, median(trm) OVER (PARTITION BY PERIODO) m FROM t) WHERE trm < m * 0.8 OR trm > m * 1.2)""")
    reg_log('7. Calidad', 'Revisiones: FOB ≤ 0, peso neto > bruto, fechas inválidas y tasa de cambio implícita (FOB COP / FOB USD) a más de ±20 % de la mediana del mes', r[0], None,
            'Sin hallazgos.' if r[0] == 0 else 'Hay hallazgos: revisar.')
    r = one("""SELECT count(*) FROM (SELECT DISTINCT trim(NUM__DECLA_EXPORTACION_ANT) a FROM s WHERE TIPO_DESPACHO <> 'Inicial')
               WHERE a IN (SELECT DISTINCT NUMERO_FORMULARIO FROM s)""")
    reg_log('7. Calidad', 'Correcciones y modificaciones DIAN: ninguna declaración corregida convive con su original, no hay doble conteo', r[0], None,
            'Sin hallazgos.' if r[0] == 0 else 'Hay declaraciones originales junto a su corrección: revisar.')
    reg_log('8. Columnas', 'Columnas redundantes o vacías retiradas de la tabla de hechos: FECHA_PROCESO (= PERIODO), TIPO_DECLARACION (= TIPO_DESPACHO), códigos '
            'que repiten su descripción, COD_USUARIO (99,97 % vacío), COD_LUGAR_SALIDA_NUM (no es 1:1 con el lugar), COD_DPTO_EXPORTADOR (era el municipio: queda '
            'COD_MPIO_DIRECCION_DECLARADA), nombres que viven en dimensiones, NIT duplicado y las columnas NIT_* y de sector que repetían el directorio en cada línea', None, None,
            f'De {len(cols) + 1} columnas se pasa a {ncols}. No se pierde información: los nombres y atributos están en las dimensiones y en vw_exportaciones.')

    # ------------------------------------------------------------ 5. dimensiones
    reg('dep_df', pd.DataFrame(DEPTOS, columns=['COD_DEPTO', 'DEPARTAMENTO']))
    c.execute("CREATE TABLE dim_departamento AS SELECT COD_DEPTO, DEPARTAMENTO, COD_DEPTO = '05' AS ES_ANTIOQUIA FROM dep_df ORDER BY 1")
    reg_log('9. Dimensiones', 'Departamentos de origen y procedencia con código DIVIPOLA de 2 dígitos y nombre oficial (dim_departamento)', None, None,
            'La fuente traía grafías distintas en cada columna (p. ej. "BOGOTA DC" y "BOGOTÁ, D.C."). "00 DEPARTAMENTOS VARIOS" es un código DIAN, no DIVIPOLA.')
    c.execute("""CREATE TABLE dim_municipio AS
    SELECT COD_MPIO_DIRECCION_DECLARADA AS COD_MPIO, mode(MUNICIPIO_DIRECCION_DECLARADA) AS MUNICIPIO, substr(COD_MPIO_DIRECCION_DECLARADA, 1, 2) AS COD_DEPTO
    FROM s WHERE COD_MPIO_DIRECCION_DECLARADA IS NOT NULL GROUP BY 1 ORDER BY 1""")

    dest = c.execute(f"""SELECT CASE WHEN {ZF} THEN 'XCF' ELSE COD_PAIS_DESTINO_ALF END iso3, ANIO >= 2025 nuevo, PAIS_DESTINO_FINAL nom, count(*) n
                         FROM s GROUP BY ALL""").df()
    band = c.execute("""SELECT h.COD_PAIS_BANDERA iso3, s.ANIO >= 2025 nuevo, s.NACIONALIDAD_BANDERA nom, count(*) n
                        FROM s JOIN hechos_exportaciones h USING (ID_REGISTRO) GROUP BY ALL""").df()
    allp = pd.concat([dest.assign(src=0), band.assign(src=1)])

    def limpia_py(x):
        return ' '.join(str(x).split())

    def nombre(iso, g):
        if iso in PAISES_MANUAL:
            return PAISES_MANUAL[iso]
        g2 = g[g.nuevo & (g.src == 0)]
        if g2.empty:
            g2 = g[g.nuevo]
        if not g2.empty:
            return limpia_py(g2.sort_values('n', ascending=False).nom.iloc[0])
        t = limpia_py(g.sort_values('n', ascending=False).nom.iloc[0]).title()
        for a, b in ((' De ', ' de '), (' Del ', ' del '), (' Y ', ' y '), (' La ', ' la '), (' Las ', ' las '), (' Los ', ' los ')):
            t = t.replace(a, b)
        return t

    filas = []
    for iso, g in allp.groupby('iso3'):
        pc = pycountry.countries.get(alpha_3=iso) if iso not in ('XCF', 'ND') else None
        tipo = {'XCF': 'Zona franca colombiana', 'ND': 'No declarado', 'COL': 'Colombia (destino nacional)'}.get(iso, 'País')
        filas.append((iso, nombre(iso, g), pc.alpha_2 if pc else None, pc.numeric if pc else None, tipo,
                      bool((g.src == 0).any()), bool((g.src == 1).any())))
    reg('pais_df', pd.DataFrame(filas, columns=['COD_PAIS', 'PAIS', 'COD_ISO2', 'COD_NUMERICO_M49', 'TIPO_DESTINO',
                                                'APARECE_COMO_DESTINO', 'APARECE_COMO_BANDERA']))
    c.execute("CREATE TABLE dim_pais AS SELECT * FROM pais_df ORDER BY COD_PAIS")

    c.execute(f"""CREATE TABLE dim_zona_franca AS
    WITH t AS (SELECT COD_PAIS_DESTINO_NUM cod, limpia(PAIS_DESTINO_FINAL) nom, max(ANIO) ult, count(*) n FROM s WHERE {ZF} GROUP BY 1, 2)
    SELECT cod AS COD_ZONA_FRANCA, arg_max(nom, ult * 10000000 + n) AS ZONA_FRANCA, string_agg(DISTINCT nom, ' | ') AS NOMBRES_EN_FUENTE
    FROM t GROUP BY 1 ORDER BY 2""")
    c.execute("""CREATE TABLE dim_aduana AS
    WITH t AS (SELECT lpad(trim(COD_ADUANA_SALIDA), 2, '0') cod, limpia(ADUANA_SALIDA) nom FROM s UNION ALL
               SELECT lpad(trim(COD_ADUANA_DESPACHO), 2, '0'), limpia(ADUANA_DESPACHO) FROM s)
    SELECT cod AS COD_ADUANA, mode(nom) AS ADUANA FROM t GROUP BY 1 ORDER BY 1""")
    c.execute("""CREATE TABLE dim_declarante AS
    WITH t AS (SELECT nit_limpio(NIT_DECLARANTE) nit, sin_comillas(RAZON_SOCIAL_DECLARANTE) nom, max(PERIODO) ult, count(*) n
               FROM s WHERE nit_limpio(NIT_DECLARANTE) IS NOT NULL AND coalesce(RAZON_SOCIAL_DECLARANTE, '') <> 'PERSONA NATURAL' GROUP BY 1, 2)
    SELECT nit AS NIT_DECLARANTE, arg_max(nom, strftime(ult, '%Y%m') || lpad(CAST(n AS VARCHAR), 9, '0')) AS RAZON_SOCIAL_DECLARANTE,
           count(DISTINCT nom) AS N_VARIANTES_NOMBRE
    FROM t GROUP BY 1 ORDER BY 1""")
    c.execute(f"""CREATE TABLE dim_subpartida AS
    SELECT SUBPARTIDA_10D AS SUBPARTIDA, substr(SUBPARTIDA_10D, 1, 2) AS CAPITULO, substr(SUBPARTIDA_10D, 1, 4) AS PARTIDA,
      substr(SUBPARTIDA_10D, 1, 6) AS SUBPARTIDA_SA6, SECTOR_EXPORTACION, ES_MINERO_ENERGETICO, ES_AGRICOLA_MADR,
      limpia(PRODUCTO_AGRICOLA_MADR) PRODUCTO_AGRICOLA_MADR, limpia(TRADICION_AGRICOLA_MADR) TRADICION_AGRICOLA_MADR,
      limpia(DESCRIPCION_PARTIDA_MADR) DESCRIPCION_PARTIDA_MADR
    FROM read_csv('{SUB.as_posix()}', types={{'SUBPARTIDA_10D': 'VARCHAR'}}) ORDER BY 1""")
    c.execute("""CREATE TABLE catalogo_codigos AS
    SELECT 'MODO_TRANSPORTE' DOMINIO, COD_MODO_TRANSPORTE CODIGO, mode(MODO_TRANSPORTE) DESCRIPCION FROM s GROUP BY 2
    UNION ALL SELECT 'MODALIDAD_EXPORTACION', lpad(trim(COD_MODALIDAD_EXPORTACION), 3, '0'), mode(limpia(MODALIDAD_EXPORTACION)) FROM s GROUP BY 2
    UNION ALL SELECT 'UNIDAD_FISICA', COD_UNIDAD_FISICA_ALF,
      CASE COD_UNIDAD_FISICA_ALF WHEN 'CM3' THEN 'Centímetro cúbico' WHEN 'KWH' THEN 'Kilovatio hora' ELSE mode(UNIDAD_FISICA) END FROM s GROUP BY 2
    UNION ALL SELECT * FROM (VALUES ('CLASE_EXPORTADOR', '1', 'Economía mixta'), ('CLASE_EXPORTADOR', '2', 'Privada'), ('CLASE_EXPORTADOR', '3', 'Pública'),
      ('TIPO_IDENTIFICACION', '1', 'Documento de persona natural (la DIAN oculta el número)'), ('TIPO_IDENTIFICACION', '2', 'NIT'))
    ORDER BY 1, 2""")
    reg_log('9. Dimensiones', 'La unidad física "CM3" venía con descripción "No disponible": se documenta como "Centímetro cúbico"',
            one("SELECT count(*) FROM s WHERE COD_UNIDAD_FISICA_ALF = 'CM3'")[0])
    log("Dimensiones listas")

    # ------------------------------------------------------------ 6. dimensión exportador (directorio recalculado)
    c.execute(f"CREATE TEMP TABLE dir_in AS SELECT * FROM read_csv('{DIR.as_posix()}', all_varchar=true)")
    dcols = {r[0] for r in c.execute("DESCRIBE dir_in").fetchall()}
    col_fob_total = 'FOB_USD_TOTAL' if 'FOB_USD_TOTAL' in dcols else 'FOB_USD_TOTAL_2024_2026'
    rues_nombre = "limpia(v.RAZON_SOCIAL_RUES)" if 'RAZON_SOCIAL_RUES' in dcols else "NULL"
    c.execute("""CREATE TEMP TABLE nom AS
    WITH t AS (SELECT nit_limpio(NIT_EXPORTADOR) nit, sin_comillas(RAZON_SOCIAL_EXPORTADOR) nom, max(PERIODO) ult, count(*) n
               FROM s WHERE nit_limpio(NIT_EXPORTADOR) IS NOT NULL AND RAZON_SOCIAL_EXPORTADOR IS NOT NULL
                 AND RAZON_SOCIAL_EXPORTADOR <> 'PERSONA NATURAL' GROUP BY 1, 2)
    SELECT nit, arg_max(nom, strftime(ult, '%Y%m') || lpad(CAST(n AS VARCHAR), 9, '0')) canon,
           count(DISTINCT nom) n_var, string_agg(DISTINCT nom, ' | ' ORDER BY nom) todos FROM t GROUP BY 1""")
    c.execute("""CREATE TEMP TABLE pj AS
    SELECT h.*, d.SECTOR_EXPORTACION, d.ES_MINERO_ENERGETICO, d.ES_AGRICOLA_MADR, d.PRODUCTO_AGRICOLA_MADR
    FROM hechos_exportaciones h JOIN dim_subpartida d USING (SUBPARTIDA) WHERE h.NIT_EXPORTADOR IS NOT NULL""")
    anios = [r[0] for r in c.execute("SELECT DISTINCT ANIO FROM pj ORDER BY 1").fetchall()]
    ult_anio, ult_mes = c.execute("SELECT max(ANIO), max(MES) FILTER (WHERE ANIO = (SELECT max(ANIO) FROM pj)) FROM pj").fetchone()
    fob_anios = ",\n      ".join(f"round(sum(VALOR_FOB_USD) FILTER (WHERE ANIO={a}),2) FOB_USD_{a}" for a in anios)
    c.execute(f"""CREATE TEMP TABLE agg AS
    SELECT NIT_EXPORTADOR NIT, mode(CLASE_EXPORTADOR) CLASE_EXPORTADOR,
      {fob_anios},
      round(sum(VALOR_FOB_USD),2) FOB_USD_TOTAL,
      round(coalesce(sum(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA),0),2) FOB_USD_ORIGEN_ANTIOQUIA,
      round(100*coalesce(sum(VALOR_FOB_USD) FILTER (WHERE ES_DESTINO_ZONA_FRANCA),0)/nullif(sum(VALOR_FOB_USD),0),1) PCT_FOB_DESTINO_ZONA_FRANCA,
      round(100*coalesce(sum(VALOR_FOB_USD) FILTER (WHERE ES_MINERO_ENERGETICO),0)/nullif(sum(VALOR_FOB_USD),0),1) PCT_FOB_MINERO_ENERGETICO,
      round(100*coalesce(sum(VALOR_FOB_USD) FILTER (WHERE ES_AGRICOLA_MADR),0)/nullif(sum(VALOR_FOB_USD),0),1) PCT_FOB_AGRICOLA_MADR,
      round(sum(PESO_NETO_KGS),2) PESO_NETO_KGS_TOTAL, count(*) N_REGISTROS,
      count(DISTINCT NUMERO_FORMULARIO) + count(*) FILTER (WHERE NUMERO_FORMULARIO IS NULL) N_DECLARACIONES,
      count(DISTINCT PERIODO) N_MESES_CON_EXPORTACION, strftime(min(PERIODO),'%Y-%m') PRIMER_MES, strftime(max(PERIODO),'%Y-%m') ULTIMO_MES,
      count(DISTINCT COD_PAIS_DESTINO) N_PAISES_DESTINO, count(DISTINCT SUBPARTIDA) N_SUBPARTIDAS,
      mode(COD_ADUANA_SALIDA) COD_ADUANA_SALIDA_PRINCIPAL, mode(COD_MODO_TRANSPORTE) COD_MODO_TRANSPORTE_PRINCIPAL
    FROM pj GROUP BY 1""")
    c.execute("""CREATE TEMP TABLE agg2 AS
    WITH o AS (SELECT NIT_EXPORTADOR NIT, COD_DEPTO_ORIGEN d, sum(VALOR_FOB_USD) v FROM pj GROUP BY 1,2),
         om AS (SELECT NIT, arg_max(d, v) COD_DEPTO_ORIGEN_PRINCIPAL FROM o GROUP BY 1),
         se AS (SELECT NIT_EXPORTADOR NIT, SECTOR_EXPORTACION x, sum(VALOR_FOB_USD) v FROM pj GROUP BY 1,2),
         sem AS (SELECT NIT, arg_max(x, v) SECTOR_EXPORTADOR_PRINCIPAL FROM se GROUP BY 1),
         pr AS (SELECT NIT_EXPORTADOR NIT, PRODUCTO_AGRICOLA_MADR x, sum(VALOR_FOB_USD) v FROM pj WHERE PRODUCTO_AGRICOLA_MADR IS NOT NULL GROUP BY 1,2),
         prm AS (SELECT NIT, arg_max(x, v) PRODUCTO_AGRICOLA_PRINCIPAL_MADR FROM pr GROUP BY 1),
         pa AS (SELECT p.NIT_EXPORTADOR NIT, dp.PAIS x, sum(p.VALOR_FOB_USD) v FROM pj p JOIN dim_pais dp ON dp.COD_PAIS=p.COD_PAIS_DESTINO GROUP BY 1,2),
         par AS (SELECT *, row_number() OVER (PARTITION BY NIT ORDER BY v DESC, x) rk, sum(v) OVER (PARTITION BY NIT) tot FROM pa),
         pam AS (SELECT NIT, string_agg(x || ' (' || CAST(round(100*v/nullif(tot,0)) AS INT) || '%)', '; ' ORDER BY rk) TOP3_PAISES_DESTINO FROM par WHERE rk<=3 GROUP BY 1),
         sp AS (SELECT NIT_EXPORTADOR NIT, SUBPARTIDA x, sum(VALOR_FOB_USD) v FROM pj GROUP BY 1,2),
         spr AS (SELECT *, row_number() OVER (PARTITION BY NIT ORDER BY v DESC, x) rk FROM sp),
         spm AS (SELECT NIT, string_agg(x, '; ' ORDER BY rk) TOP5_SUBPARTIDAS, max(CASE WHEN rk=1 THEN substr(x,1,2) END) CAPITULO_ARANCEL_PRINCIPAL FROM spr WHERE rk<=5 GROUP BY 1)
    SELECT a.NIT, om.COD_DEPTO_ORIGEN_PRINCIPAL, sem.SECTOR_EXPORTADOR_PRINCIPAL, prm.PRODUCTO_AGRICOLA_PRINCIPAL_MADR,
           pam.TOP3_PAISES_DESTINO, spm.TOP5_SUBPARTIDAS, spm.CAPITULO_ARANCEL_PRINCIPAL
    FROM agg a LEFT JOIN om USING (NIT) LEFT JOIN sem USING (NIT) LEFT JOIN prm USING (NIT) LEFT JOIN pam USING (NIT) LEFT JOIN spm USING (NIT)""")
    # Dirección DIAN "propia": compartida por <= MAX_NIT_DIRECCION_PROPIA NIT (las demás suelen ser de la agencia de aduanas)
    c.execute(f"""CREATE TEMP TABLE sede AS
    WITH dc AS (SELECT DIRECCION_DECLARADA, COD_MPIO_DIRECCION_DECLARADA, count(DISTINCT NIT_EXPORTADOR) n_nit FROM pj
                WHERE DIRECCION_DECLARADA IS NOT NULL GROUP BY 1,2),
    t AS (SELECT p.NIT_EXPORTADOR NIT, p.COD_MPIO_DIRECCION_DECLARADA m, count(DISTINCT coalesce(p.NUMERO_FORMULARIO, CAST(p.ID_REGISTRO AS VARCHAR))) n
          FROM pj p JOIN dc USING (DIRECCION_DECLARADA, COD_MPIO_DIRECCION_DECLARADA)
          WHERE dc.n_nit <= {C.MAX_NIT_DIRECCION_PROPIA} AND p.COD_MPIO_DIRECCION_DECLARADA IS NOT NULL GROUP BY 1,2)
    SELECT NIT, arg_max(m, n) COD_MPIO_DIAN_DIRECCION_PROPIA FROM t GROUP BY 1""")
    CAM = "(" + ", ".join(f"'{x}'" for x in C.CAMARAS_ANTIOQUIA) + ")"
    fob_sel = ", ".join(f"a.FOB_USD_{a}" for a in anios)
    exp_sel = ",\n      ".join(f"(coalesce(FOB_USD_{a},0) >= {C.UMBRAL_EXPORTADOR_USD}) EXPORTADOR_{a}_MIN_1000USD" for a in anios)
    c.execute(f"""CREATE TABLE dim_exportador AS
    WITH b AS (
    SELECT a.NIT, coalesce(nm.canon, {rues_nombre}) AS RAZON_SOCIAL,
      CASE WHEN nm.n_var > 1 THEN nm.todos END AS NOMBRES_EN_FUENTE, {rues_nombre} AS RAZON_SOCIAL_RUES,
      'Persona jurídica' AS TIPO_EXPORTADOR, a.CLASE_EXPORTADOR, cc.DESCRIPCION AS CLASE_EXPORTADOR_DESC,
      limpia(v.CAMARA_COMERCIO) CAMARA_COMERCIO, limpia(v.MATRICULA) MATRICULA,
      CASE WHEN limpia(v.CIIU_PRINCIPAL_RUES) IS NOT NULL THEN lpad(limpia(v.CIIU_PRINCIPAL_RUES),4,'0') END CIIU_PRINCIPAL_RUES,
      CASE WHEN limpia(v.CIIU_SECUNDARIO_RUES) IS NOT NULL THEN lpad(limpia(v.CIIU_SECUNDARIO_RUES),4,'0') END CIIU_SECUNDARIO_RUES,
      limpia(v.ORGANIZACION_JURIDICA) ORGANIZACION_JURIDICA,
      CASE WHEN v.FECHA_MATRICULA <> '00000000' THEN try_strptime(v.FECHA_MATRICULA,'%Y%m%d')::DATE END FECHA_MATRICULA,
      try_cast(v.ULTIMO_ANO_RENOVADO AS SMALLINT) ULTIMO_ANO_RENOVADO, limpia(v.ESTADO_MATRICULA) ESTADO_MATRICULA,
      try_cast(v.TIENE_MATRICULA_ACTIVA_EN_ANTIOQUIA AS BOOLEAN) TIENE_MATRICULA_ACTIVA_EN_ANTIOQUIA,
      sd.COD_MPIO_DIAN_DIRECCION_PROPIA, mu.MUNICIPIO MUNICIPIO_DIAN_DIRECCION_PROPIA, dmu.DEPARTAMENTO DEPTO_DIAN_DIRECCION_PROPIA,
      a2.COD_DEPTO_ORIGEN_PRINCIPAL, dor.DEPARTAMENTO DEPTO_ORIGEN_PRINCIPAL_MERCANCIA,
      a2.SECTOR_EXPORTADOR_PRINCIPAL, a.PCT_FOB_MINERO_ENERGETICO, a.PCT_FOB_AGRICOLA_MADR, a2.PRODUCTO_AGRICOLA_PRINCIPAL_MADR,
      {fob_sel}, a.FOB_USD_TOTAL, a.FOB_USD_ORIGEN_ANTIOQUIA,
      round(100*a.FOB_USD_ORIGEN_ANTIOQUIA/nullif(a.FOB_USD_TOTAL,0),1) PCT_FOB_ORIGEN_ANTIOQUIA,
      a.PCT_FOB_DESTINO_ZONA_FRANCA, a.PESO_NETO_KGS_TOTAL, a.N_REGISTROS, a.N_DECLARACIONES, a.N_MESES_CON_EXPORTACION, a.PRIMER_MES, a.ULTIMO_MES,
      a.N_PAISES_DESTINO, a2.TOP3_PAISES_DESTINO, a.N_SUBPARTIDAS, a2.TOP5_SUBPARTIDAS, a2.CAPITULO_ARANCEL_PRINCIPAL,
      ad.ADUANA ADUANA_SALIDA_PRINCIPAL, mt.DESCRIPCION MODO_TRANSPORTE_PRINCIPAL,
      limpia(v.SS_MACROSECTOR) SS_MACROSECTOR,
      CASE WHEN limpia(v.SS_CIIU) IS NOT NULL THEN lpad(regexp_replace(limpia(v.SS_CIIU), '\\.0+$', ''), 4, '0') END SS_CIIU,
      limpia(v.SS_SUPERVISOR) SS_SUPERVISOR, limpia(v.SS_DEPARTAMENTO_DOMICILIO) SS_DEPARTAMENTO_DOMICILIO, limpia(v.SS_CIUDAD_DOMICILIO) SS_CIUDAD_DOMICILIO,
      try_cast(v.SS_INGRESOS_OPERACIONALES_BILLONES_COP AS DOUBLE) SS_INGRESOS_OPERACIONALES_BILLONES_COP,
      try_cast(v.SS_TOTAL_ACTIVOS_BILLONES_COP AS DOUBLE) SS_TOTAL_ACTIVOS_BILLONES_COP, try_cast(v.SS_ANO_CORTE AS SMALLINT) SS_ANO_CORTE,
      coalesce(try_cast(v.PROVEEDOR_ESTADO_SECOP_II AS BOOLEAN), false) PROVEEDOR_ESTADO_SECOP_II,
      try_cast(try_cast(v.SECOP_N_CONTRATOS AS DOUBLE) AS INTEGER) SECOP_N_CONTRATOS, try_cast(v.SECOP_VALOR_CONTRATOS_COP AS DOUBLE) SECOP_VALOR_CONTRATOS_COP,
      try_cast(v.SECOP_PRIMERA_FIRMA AS DATE) SECOP_PRIMERA_FIRMA, try_cast(v.SECOP_ULTIMA_FIRMA AS DATE) SECOP_ULTIMA_FIRMA,
      limpia(v.SECOP_ES_PYME) SECOP_ES_PYME, try_cast(try_cast(v.SECOP_N_ENTIDADES AS DOUBLE) AS INTEGER) SECOP_N_ENTIDADES,
      (v.NIT IS NOT NULL) AS EN_DIRECTORIO_ENTRADA
    FROM agg a JOIN agg2 a2 USING (NIT) LEFT JOIN nom nm ON nm.nit=a.NIT LEFT JOIN dir_in v ON v.NIT=a.NIT LEFT JOIN sede sd ON sd.NIT=a.NIT
    LEFT JOIN dim_municipio mu ON mu.COD_MPIO=sd.COD_MPIO_DIAN_DIRECCION_PROPIA LEFT JOIN dim_departamento dmu ON dmu.COD_DEPTO=mu.COD_DEPTO
    LEFT JOIN dim_departamento dor ON dor.COD_DEPTO=a2.COD_DEPTO_ORIGEN_PRINCIPAL
    LEFT JOIN dim_aduana ad ON ad.COD_ADUANA=a.COD_ADUANA_SALIDA_PRINCIPAL
    LEFT JOIN catalogo_codigos mt ON mt.DOMINIO='MODO_TRANSPORTE' AND mt.CODIGO=a.COD_MODO_TRANSPORTE_PRINCIPAL
    LEFT JOIN catalogo_codigos cc ON cc.DOMINIO='CLASE_EXPORTADOR' AND cc.CODIGO=a.CLASE_EXPORTADOR),
    v AS (
    SELECT *,
      CASE WHEN CAMARA_COMERCIO IN {CAM} THEN 'RUES: cámara de Antioquia'
           WHEN CAMARA_COMERCIO IS NOT NULL THEN 'RUES: cámara fuera de Antioquia'
           WHEN substr(COD_MPIO_DIAN_DIRECCION_PROPIA,1,2)='05' THEN 'Sin RUES; dirección DIAN propia en Antioquia'
           ELSE 'Sin RUES' END AS FUENTE_DOMICILIO,
      CASE WHEN CAMARA_COMERCIO IN {CAM} OR (CAMARA_COMERCIO IS NULL AND substr(COD_MPIO_DIAN_DIRECCION_PROPIA,1,2)='05')
                THEN 'A. Empresa antioqueña (domicilio en Antioquia)'
           WHEN COD_DEPTO_ORIGEN_PRINCIPAL='05' THEN 'B. Domicilio fuera; origen principal de su mercancía es Antioquia'
           WHEN FOB_USD_ORIGEN_ANTIOQUIA>0 THEN 'C. Domicilio fuera; parte de su mercancía es de origen Antioquia'
           ELSE 'D. Sin relación con Antioquia' END AS VINCULO_ANTIOQUIA,
      {exp_sel}
    FROM b),
    f AS (SELECT *, starts_with(VINCULO_ANTIOQUIA, 'A.') AS EMPRESA_ANTIOQUENA,
                 (starts_with(VINCULO_ANTIOQUIA, 'A.') OR starts_with(VINCULO_ANTIOQUIA, 'B.')) AS ES_EXPORTADOR_ANTIOQUENO FROM v)
    SELECT row_number() OVER (ORDER BY FOB_USD_TOTAL DESC NULLS LAST, NIT) AS RANKING_NACIONAL_FOB,
      CASE WHEN ES_EXPORTADOR_ANTIOQUENO THEN row_number() OVER (PARTITION BY ES_EXPORTADOR_ANTIOQUENO ORDER BY FOB_USD_TOTAL DESC NULLS LAST, NIT) END AS RANKING_ANTIOQUIA_FOB,
      NIT, RAZON_SOCIAL, VINCULO_ANTIOQUIA, EMPRESA_ANTIOQUENA, ES_EXPORTADOR_ANTIOQUENO,
      * EXCLUDE (NIT, RAZON_SOCIAL, VINCULO_ANTIOQUIA, EMPRESA_ANTIOQUENA, ES_EXPORTADOR_ANTIOQUENO)
    FROM f ORDER BY RANKING_NACIONAL_FOB""")
    r = one("""SELECT count(*), count(*) FILTER (WHERE NOT EN_DIRECTORIO_ENTRADA), count(*) FILTER (WHERE NOMBRES_EN_FUENTE IS NOT NULL),
                      count(*) FILTER (WHERE RAZON_SOCIAL IS NULL), count(*) FILTER (WHERE RAZON_SOCIAL = RAZON_SOCIAL_RUES AND RAZON_SOCIAL IS NOT NULL
                        AND NIT NOT IN (SELECT nit FROM nom))
               FROM dim_exportador""")
    reg_log('10. Directorio', 'Directorio (dim_exportador) recalculado desde la tabla de hechos depurada: un registro por NIT y una razón social canónica (la más reciente de la DIAN), con sus variantes en NOMBRES_EN_FUENTE', r[0], None,
            f'{fmt(r[2])} NIT tienen más de una razón social en la fuente; {fmt(r[4])} NIT nunca tuvieron razón social DIAN publicada (solo aparecen en sep-2024) y toman la del RUES; '
            f'NIT sin ningún nombre: {fmt(r[3])}. NIT que no estaban en el directorio de entrada: {fmt(r[1])}.')
    r = one(f"""SELECT count(*) FILTER (WHERE abs(coalesce(e.FOB_USD_TOTAL,0) - coalesce(try_cast(v.{col_fob_total} AS DOUBLE),0)) > 0.01),
                       sum(coalesce(e.FOB_USD_TOTAL,0) - coalesce(try_cast(v.{col_fob_total} AS DOUBLE),0)),
                       count(*) FILTER (WHERE e.VINCULO_ANTIOQUIA <> v.VINCULO_ANTIOQUIA),
                       count(*) FILTER (WHERE coalesce(e.TOP3_PAISES_DESTINO,'') <> coalesce(v.TOP3_PAISES_DESTINO,''))
                FROM dim_exportador e JOIN dir_in v USING (NIT)""")
    reg_log('10. Directorio', 'Cuadre del directorio recalculado contra el directorio de entrada (paso 7)', r[0], r[1],
            f'NIT con FOB total distinto: {fmt(r[0])}; NIT que cambian de VINCULO_ANTIOQUIA: {fmt(r[2])}; '
            f'NIT cuyo TOP3_PAISES_DESTINO cambia: {fmt(r[3])} (sobre todo por el error de zona franca, que ya no aparece como "ZFP de Rionegro").')
    reg_log('10. Directorio', 'Formatos homogéneos en atributos externos: CIIU a 4 dígitos (Supersociedades traía "610" y "4620.00"), fechas como fecha, booleanos y números con su tipo', None)
    log("Directorio listo")

    # ------------------------------------------------------------ 7. referencias oficiales
    v1 = pd.read_csv(VAL_MINCIT)[['TRIMESTRE', 'MINCIT_TOTAL_MUSD', 'MINCIT_NME_MUSD']]
    v2 = pd.read_csv(VAL_MADR)[['ANIO', 'MESES', 'MADR_AGRICOLA_NACIONAL_MUSD', 'MADR_AGRICOLA_ANTIOQUIA_MUSD']]
    reg('v1_df', v1)
    reg('v2_df', v2)
    c.execute("CREATE TABLE ref_mincit_trimestral AS SELECT TRIMESTRE, CAST(MINCIT_TOTAL_MUSD AS DOUBLE) MINCIT_TOTAL_MUSD, CAST(MINCIT_NME_MUSD AS DOUBLE) MINCIT_NME_MUSD FROM v1_df")
    c.execute("CREATE TABLE ref_madr_agricola_anual AS SELECT CAST(ANIO AS SMALLINT) ANIO, CAST(MESES AS TINYINT) MESES, MADR_AGRICOLA_NACIONAL_MUSD, MADR_AGRICOLA_ANTIOQUIA_MUSD FROM v2_df")

    # ------------------------------------------------------------ 8. metadatos
    reg('log_df', pd.DataFrame(LOG, columns=['PASO', 'ETAPA', 'REGLA', 'FILAS_AFECTADAS', 'FOB_USD_AFECTADO', 'DETALLE']))
    c.execute("CREATE TABLE log_depuracion AS SELECT * FROM log_df ORDER BY PASO")
    info = [
        ('Nombre', f'BD de exportaciones de Colombia depurada ({anios[0]}-01 a {ult_anio}-{ult_mes:02d})'),
        ('Fecha de construcción', datetime.date.today().isoformat()),
        ('Construida con', 'pipeline/p09_bd_depurada.py a partir de data/processed (paso 7); el .duckdb se arma con crear_bd_depurada.py'),
        ('Fuente principal', 'DIAN: bases estadísticas de exportaciones (archivos mensuales)'),
        ('Fuentes de enriquecimiento', 'RUES Confecámaras, Supersociedades (10.000 empresas), SECOP II, MinAgricultura, MinCIT NME, DIVIPOLA. Ver docs/fuentes.md'),
        ('Granularidad de hechos', 'Una fila por serie (ítem) de declaración de exportación'),
        ('Cómo empezar', 'SELECT * FROM vw_exportaciones (todo con nombres) · dim_exportador (directorio) · vw_directorio_antioquia · vw_serie_mensual'),
        ('Validación', 'FOB trimestral igual a la cifra oficial de MinCIT y FOB agrícola nacional igual a MinAgricultura (vw_validacion_mincit, vw_validacion_madr)'),
        ('Advertencia', 'La dirección declarada a la DIAN suele ser la de la agencia de aduanas; para domicilio usar CAMARA_COMERCIO (RUES) o VINCULO_ANTIOQUIA.'),
        ('Documentación', 'docs/limpieza_bd_depurada.md y docs/diccionario_bd_depurada.csv'),
    ]
    reg('info_df', pd.DataFrame(info, columns=['CLAVE', 'VALOR']))
    c.execute("CREATE TABLE info_bd AS SELECT * FROM info_df")
    dic = diccionario_bd_depurada.tabla()
    reg('dic_df', dic)
    c.execute("""CREATE TABLE diccionario_datos AS
    SELECT d.TABLA, d.COLUMNA, i.data_type AS TIPO, d.DESCRIPCION, d.ORIGEN_O_REGLA
    FROM dic_df d LEFT JOIN information_schema.columns i ON i.table_name = d.TABLA AND i.column_name = d.COLUMNA""")
    sin_doc = c.execute("""SELECT table_name || '.' || column_name FROM information_schema.columns
        WHERE table_schema = 'main' AND table_name IN ('hechos_exportaciones','dim_exportador','dim_subpartida','dim_pais','dim_zona_franca',
              'dim_departamento','dim_municipio','dim_aduana','dim_declarante','catalogo_codigos')
          AND (table_name, column_name) NOT IN (SELECT TABLA, COLUMNA FROM dic_df)""").fetchall()
    if sin_doc:
        log(f"OJO, columnas sin documentar en el diccionario: {[x[0] for x in sin_doc]}")

    # ------------------------------------------------------------ 9. exportar a parquet y armar el .duckdb
    out = C.OUT_BD_DEPURADA
    hechos_dir = out / "hechos_exportaciones"
    if hechos_dir.exists():
        shutil.rmtree(hechos_dir)
    hechos_dir.mkdir(parents=True)
    for a, m in c.execute("SELECT DISTINCT ANIO, MES FROM hechos_exportaciones ORDER BY 1, 2").fetchall():
        c.execute(f"COPY (SELECT * FROM hechos_exportaciones WHERE ANIO={a} AND MES={m} ORDER BY ID_REGISTRO) TO "
                  f"'{(hechos_dir / f'hechos_{a}_{m:02d}.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    for t in crear_bd_depurada.TABLAS:
        c.execute(f"COPY (SELECT * FROM {t}) TO '{(out / f'{t}.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    c.execute(f"COPY diccionario_datos TO '{(C.DOCS / 'diccionario_bd_depurada.csv').as_posix()}' (HEADER)")
    c.execute(f"COPY log_depuracion TO '{(C.DOCS / 'log_bd_depurada.csv').as_posix()}' (HEADER)")
    c.close()
    TRABAJO.unlink(missing_ok=True)
    log(f"Parquet de la BD depurada en {out}")
    crear_bd_depurada.construir(out, C.BD_DEPURADA_DUCKDB)


if __name__ == "__main__":
    main()
