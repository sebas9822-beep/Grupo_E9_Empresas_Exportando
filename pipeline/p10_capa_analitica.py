"""Paso 10 · BD principal: capa analítica sobre la BD depurada (versión 2).

Toma la BD depurada del paso 9 (datos/limpios/bd_depurada/, la arma si no existe) y construye la BD PRINCIPAL DE
TRABAJO del proyecto, sin modificar la depurada. Sobre el mismo modelo estrella agrega:
  1. llaves primarias en todas las tablas y foráneas declaradas entre tablas pequeñas; las 21 relaciones de la tabla
     de hechos se validan en cada construcción (0 huérfanos) y quedan en relaciones_llaves,
  2. un catálogo por dominio (cat_*) con fuente y nivel de confianza de cada descripción,
  3. banderas de precio unitario y cantidad atípicos y, solo en exportaciones comerciales con errores de magnitud
     (100 veces o más lejos de la mediana), peso y cantidad reconstruidos; el FOB nunca se toca,
  4. correcciones puntuales y columnas retiradas (OFICINA y COD_MODALIDAD_PRECEDENTE, sin tabla oficial),
  5. cifras de Supersociedades llevadas a pesos de diciembre de 2025 e intensidad exportadora,
  6. historia de razón social y traslados de domicilio por NIT,
  7. referencias oficiales del DANE para el cuadre (incluye enero-septiembre de 2026),
  8. tablas puente, panel exportador-mes y vistas listas para analizar.

Deja (se versiona):
  datos/limpios/bd_analitica/hechos_analitica_complemento.parquet   columnas nuevas de los hechos, por ID_REGISTRO
  datos/limpios/bd_analitica/<tabla>.parquet                        demás tablas de la BD principal
  datos/limpios/bd_analitica/esquema.sql                            tablas con sus llaves y vistas
  datos/limpios/nit_ciudad_comprador_por_completar.csv
  docs/diccionario_bd_analitica.csv y .md, docs/log_bd_analitica.csv, docs/relaciones_llaves_bd_analitica.csv
Y en local (no se versiona): datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb

    python pipeline/p10_capa_analitica.py                 # o: python run_pipeline.py --solo 10
    python crear_bd_analitica.py                          # arma el .duckdb desde los parquet, sin correr este paso

Cada regla queda en la tabla log_preparacion con filas y FOB afectados. El detalle está en
docs/bd_principal_capa_analitica.md.
"""
import argparse
import datetime
import html
import os
import pathlib
import re
import sys
import unicodedata

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
import crear_bd_analitica as CBA  # noqa: E402
import crear_bd_depurada  # noqa: E402

# ---------------------------------------------------------------- parámetros
K_IQR = 3.0                    # banda de atípicos: K rangos intercuartílicos en logaritmo
IQR_MIN = 0.25                 # piso del rango intercuartílico en log
N_MIN = 30                     # líneas comerciales mínimas para que un grupo sirva de referencia de precio
FACTOR_ERROR = 100             # solo se ajusta peso o cantidad si el precio se aleja 100 veces o más de la mediana (error de unidades o decimales)
MODALIDADES_COMERCIALES = ('198', '199')   # exportaciones definitivas con valor comercial
SECOP_MAX_COP = 1e14           # 100 billones de COP: por encima, el total SECOP de una empresa es inválido
FK_EN_HECHOS = False           # True declara las 21 llaves foráneas de la tabla de hechos (el archivo pasa de ~1,3 GB)
# Inflación anual del IPC (diciembre a diciembre, %), DANE. Se usa para llevar cifras de Supersociedades a pesos de dic-2025.
IPC = {2022: 13.12, 2023: 9.28, 2024: 5.20, 2025: 5.10}
# Publicaciones oficiales del DANE (millones de USD FOB) para el cuadre
REF_DANE = [
    ('2024', '2024-01-01', '2024-12-01', 49552.0, 'DANE, total 2024 (vía Analdex, feb-2025)', 'https://analdex.org/2025/02/05/en-2024-las-exportaciones-colombianas-cayeron-04/'),
    ('2025', '2025-01-01', '2025-12-01', 50199.9, 'DANE, total 2025 (vía Infobae, feb-2026)', 'https://www.infobae.com/colombia/2026/02/03/colombia-siente-las-consecuencias-de-dejar-de-vender-petroleo-y-las-cifras-lo-confirman-deberiamos-estar-en-usd100000-millones/'),
    ('2026-01 a 2026-09', '2026-01-01', '2026-09-01', 42301.8, 'DANE, boletín EXPO septiembre 2026 (4-nov-2026), acumulado', 'https://www.portafolio.co/negocios/comercio/exportaciones-colombianas-cerraron-septiembre-en-us-5-410-7-millones-y-alcanzaron-cifra-mensual-mas-alta-desde-505694'),
    ('2026-09', '2026-09-01', '2026-09-01', 5410.7, 'DANE, boletín EXPO septiembre 2026 (4-nov-2026)', 'https://www.dane.gov.co/files/operaciones/EXPORTACIONES/bol-EXPORTACIONES-sep2026.pdf'),
]


def construir(ORIGEN, DESTINO):
    """Arma la BD principal en DESTINO a partir de la BD depurada ORIGEN (que abre en solo lectura)."""
    if os.path.exists(DESTINO):
        os.remove(DESTINO)
    con = duckdb.connect()
    con.execute("SET memory_limit='4GB'; SET preserve_insertion_order=true")
    con.execute(f"ATTACH '{ORIGEN}' AS dep (READ_ONLY)")
    try:
        con.execute(f"ATTACH '{DESTINO}' AS cap (STORAGE_VERSION 'v1.0.0')")
    except duckdb.Error:
        con.execute(f"ATTACH '{DESTINO}' AS cap")
    con.execute("USE cap")

    q = lambda sql: con.execute(sql).fetchone()
    miles = lambda x: f'{x:,}'.replace(',', '.')
    dec = lambda x: f'{x:g}'.replace('.', ',')

    # ---------------------------------------------------------------- utilidades: bitácora, llaves y diccionario
    con.execute("""CREATE TABLE log_preparacion (PASO INTEGER PRIMARY KEY, ETAPA VARCHAR, REGLA VARCHAR,
                   FILAS_AFECTADAS DOUBLE, FOB_USD_AFECTADO DOUBLE, DETALLE VARCHAR)""")
    _paso = [0]
    def log(etapa, regla, filas=None, fob=None, detalle=None):
        _paso[0] += 1
        con.execute("INSERT INTO log_preparacion VALUES (?,?,?,?,?,?)", [_paso[0], etapa, regla, filas, fob, detalle])
        print(f"[{_paso[0]:02d}] {etapa} | {regla[:70]} | filas={filas} fob={fob}", flush=True)

    relaciones = []   # (TABLA, COLUMNAS, TABLA_REFERENCIA, COLUMNAS_REFERENCIA, TIPO, FILAS_HUERFANAS)

    def crear(nombre, sql, pk=None, fks=()):
        """Crea la tabla con PRIMARY KEY y FOREIGN KEY declaradas. Una FK solo se declara si no hay huérfanos."""
        con.execute(f"CREATE OR REPLACE TEMP TABLE _tmp AS {sql}")
        cols = con.execute("DESCRIBE _tmp").fetchall()
        defs = [f'"{c[0]}" {c[1]}' + (' NOT NULL' if pk and c[0] in pk else '') for c in cols]
        if pk:
            n_dup = q(f"SELECT count(*) - count(DISTINCT ({', '.join(pk)})) FROM _tmp")[0]
            assert n_dup == 0, f'{nombre}: llave primaria repetida ({n_dup})'
            defs.append(f"PRIMARY KEY ({', '.join(pk)})")
            relaciones.append((nombre, ', '.join(pk), None, None, 'PRIMARY KEY declarada', 0))
        for col, ref, refcol in fks:
            huerf = q(f"SELECT count(*) FROM _tmp t WHERE t.{col} IS NOT NULL AND t.{col} NOT IN (SELECT {refcol} FROM {ref})")[0]
            if huerf == 0:
                defs.append(f"FOREIGN KEY ({col}) REFERENCES {ref} ({refcol})")
                relaciones.append((nombre, col, ref, refcol, 'FOREIGN KEY declarada', 0))
            else:
                relaciones.append((nombre, col, ref, refcol, 'FOREIGN KEY no declarada: hay huérfanos', huerf))
        con.execute(f"CREATE TABLE {nombre} ({', '.join(defs)})")
        con.execute(f"INSERT INTO {nombre} SELECT * FROM _tmp")
        con.execute("DROP TABLE _tmp")

    dicc = {}   # (TABLA, COLUMNA) -> (TIPO, DESCRIPCION, ORIGEN_O_REGLA)
    for t, c, tipo, d, o in con.execute("SELECT * FROM dep.diccionario_datos").fetchall():
        t = {'hechos_exportaciones': 'hechos_analitica', 'dim_exportador': 'dim_exportador_analitica'}.get(t, t)
        dicc[(t, c)] = (tipo, d, o)
    def dic(t, c, tipo, d, o):
        dicc[(t, c)] = (tipo, d, o)

    # ---------------------------------------------------------------- 1. dimensiones con llaves
    crear('dim_departamento', "SELECT * FROM dep.dim_departamento", ['COD_DEPTO'])
    crear('dim_municipio', "SELECT * FROM dep.dim_municipio", ['COD_MPIO'], [('COD_DEPTO', 'dim_departamento', 'COD_DEPTO')])
    for t, k in [('dim_pais', 'COD_PAIS'), ('dim_zona_franca', 'COD_ZONA_FRANCA'), ('dim_aduana', 'COD_ADUANA'),
                 ('dim_declarante', 'NIT_DECLARANTE'), ('dim_subpartida', 'SUBPARTIDA')]:
        crear(t, f"SELECT * FROM dep.{t}", [k])
    crear('ref_mincit_trimestral', "SELECT * FROM dep.ref_mincit_trimestral", ['TRIMESTRE'])
    crear('ref_madr_agricola_anual', "SELECT * FROM dep.ref_madr_agricola_anual", ['ANIO'])
    crear('log_depuracion', "SELECT * FROM dep.log_depuracion", ['PASO'])
    crear('info_bd_depurada', "SELECT * FROM dep.info_bd", ['CLAVE'])
    con.execute("CREATE TEMP TABLE _ref AS SELECT * FROM (VALUES " + ', '.join(
        f"('{p}', DATE '{a}', DATE '{b}', {v}, '{f}', '{u}')" for p, a, b, v, f, u in REF_DANE) +
        ") t(PERIODO_REFERENCIA, PERIODO_DESDE, PERIODO_HASTA, DANE_FOB_MUSD, FUENTE, URL)")
    crear('ref_dane_publicaciones', "SELECT * FROM _ref", ['PERIODO_REFERENCIA'])
    log('1. Dimensiones', 'Dimensiones, referencias y bitácora de depuración copiadas sin cambios, ahora con llave primaria declarada', None, None,
        'dim_departamento, dim_municipio (con FK a dim_departamento), dim_pais, dim_zona_franca, dim_aduana, dim_declarante, dim_subpartida, '
        'ref_mincit_trimestral, ref_madr_agricola_anual, log_depuracion e info_bd_depurada. Nueva: ref_dane_publicaciones.')

    # ---------------------------------------------------------------- 2. catálogos por dominio
    F600 = 'DIAN, formulario 600 Declaración de Exportación (versión 2014)'
    filas_cat = [(d, c, desc, 'BD depurada (DIAN)', 'oficial', None)
                 for d, c, desc in con.execute("SELECT DOMINIO, CODIGO, DESCRIPCION FROM dep.catalogo_codigos").fetchall()]
    filas_cat += [
        ('TIPO_CERTIFICADO_ORIGEN', '1', 'CAN (Comunidad Andina)', F600 + ', casilla 64', 'oficial', 'Uso observado: Ecuador 74 %, Perú 21 %, Bolivia 6 % de las líneas'),
        ('TIPO_CERTIFICADO_ORIGEN', '2', 'ALADI', F600 + ', casilla 64', 'oficial', 'Uso observado: Chile, Costa Rica, El Salvador, Panamá, Guatemala, Brasil (también acuerdos con Centroamérica)'),
        ('TIPO_CERTIFICADO_ORIGEN', '3', 'G-3 (acuerdo Colombia-México)', F600 + ', casilla 64', 'oficial', 'Uso observado: México 100 %'),
        ('TIPO_CERTIFICADO_ORIGEN', '4', 'CARICOM', F600 + ', casilla 64', 'oficial', 'Uso observado: República Dominicana 84 %, Aruba 9 %, Antigua, Jamaica'),
        ('TIPO_CERTIFICADO_ORIGEN', '5', 'ATPA (preferencias andinas de EE. UU., ya vencidas)', F600 + ', casilla 64', 'oficial con uso actual inferido',
         'Uso observado: Estados Unidos 83 %, Canadá 6 %; en la práctica parece marcar los acuerdos con EE. UU. y Canadá'),
        ('TIPO_CERTIFICADO_ORIGEN', '6', 'SGP (Sistema Generalizado de Preferencias)', F600 + ', casilla 64', 'oficial', 'Uso observado: Países Bajos, EE. UU., Canadá, España, Reino Unido, Kazajistán'),
        ('TIPO_CERTIFICADO_ORIGEN', '7', 'Otros acuerdos', F600 + ', casilla 64', 'oficial', 'Uso observado: Perú 63 %, EE. UU. 18 %'),
        ('TIPO_CERTIFICADO_ORIGEN', '8', 'Ninguno (sin certificado de origen)', F600 + ', casilla 64', 'oficial', '86 % de las líneas'),
        ('FORMA_PAGO', '1', 'Con reintegro de divisas', F600 + ', casilla 54 (S)', 'inferida', 'La base usa 1/2 en vez de S/N; 1 = 94 % de las líneas, casi todo exportación definitiva'),
        ('FORMA_PAGO', '2', 'Sin reintegro de divisas', F600 + ', casilla 54 (N)', 'inferida',
         'Se concentra en muestras sin valor (002), mercancía averiada (104), donaciones (107), temporales (201) y zonas francas'),
        ('COD_REGIMEN_CAN', '1', 'Exportación definitiva', 'Inferida de COD_MODALIDAD_EXPORTACION', 'inferida', 'Modalidades 002, 004, 104, 107, 198, 199 y 310'),
        ('COD_REGIMEN_CAN', '3', 'Reexportación temporal', 'Inferida de COD_MODALIDAD_EXPORTACION', 'inferida', 'Solo modalidad 403'),
        ('COD_REGIMEN_CAN', '4', 'Exportación temporal para perfeccionamiento pasivo', 'Inferida de COD_MODALIDAD_EXPORTACION', 'inferida', 'Solo modalidad 201; 89 % va a zonas francas'),
        ('COD_REGIMEN_CAN', '5', 'Reexportación definitiva', 'Inferida de COD_MODALIDAD_EXPORTACION', 'inferida', 'Modalidades 401 y 402'),
        ('TIPO_USUARIO', '36', 'Usuario general', 'Perfil observado', 'sin fuente oficial', '99,9 % de las líneas y 13.286 NIT'),
        ('TIPO_USUARIO', '22', 'Exportadores de hidrocarburos', 'Perfil observado', 'sin fuente oficial',
         '21 NIT con USD 36.222 M (Ecopetrol, Refinería de Cartagena, Frontera Energy, Trafigura); 1.551 de sus 1.631 líneas no tienen número de formulario'),
    ]
    for c in ['1', '4', '7', '26', '38', '53', '55', '56']:
        filas_cat.append(('TIPO_USUARIO', c, 'Sin descripción oficial', 'Perfil observado', 'sin fuente oficial', 'Menos de 0,1 % de las líneas'))
    for k, v in {'AUC': 'Arauca', 'BAQ': 'Barranquilla', 'BOG': 'Bogotá', 'BGA': 'Bucaramanga', 'BUN': 'Buenaventura', 'CLO': 'Cali',
                 'CAR': 'Cartago', 'CTG': 'Cartagena', 'CUC': 'Cúcuta', 'INI': 'Inírida', 'IPI': 'Ipiales', 'LET': 'Leticia', 'MAI': 'Maicao',
                 'MZL': 'Manizales', 'MDE': 'Medellín', 'PEI': 'Pereira', 'PUU': 'Puerto Asís', 'PCR': 'Puerto Carreño', 'RCH': 'Riohacha',
                 'ADZ': 'San Andrés', 'SMR': 'Santa Marta', 'TCO': 'Tumaco', 'TRB': 'Turbo', 'VUP': 'Valledupar', 'YOP': 'Yopal'}.items():
        filas_cat.append(('LUGAR_SALIDA', k, v, F600 + ', casilla 40', 'oficial', None))
    filas_cat += [
        ('LUGAR_SALIDA', 'CVE', 'Coveñas (terminal petrolero)', 'Inferida: código IATA, aduana de Cartagena y crudo (2709)', 'inferida', 'No está en la tabla del formulario 600'),
        ('LUGAR_SALIDA', 'MAM', 'Mamonal (zona portuaria de Cartagena)', 'Inferida: aduana de Cartagena y refinados (2710)', 'inferida', 'No está en la tabla del formulario 600'),
        ('LUGAR_SALIDA', 'AXM', 'Armenia', 'Inferida: código IATA y aduana de Armenia', 'inferida', 'No está en la tabla del formulario 600'),
        ('LUGAR_SALIDA', 'APO', 'Apartadó', 'Inferida: código IATA y aduana de Urabá', 'inferida', 'No está en la tabla del formulario 600'),
    ]
    con.execute("CREATE TEMP TABLE _cat (DOMINIO VARCHAR, CODIGO VARCHAR, DESCRIPCION VARCHAR, FUENTE VARCHAR, CONFIANZA VARCHAR, NOTA VARCHAR)")
    con.executemany("INSERT INTO _cat VALUES (?,?,?,?,?,?)", filas_cat)
    CATS = {'CLASE_EXPORTADOR': 'cat_clase_exportador', 'MODO_TRANSPORTE': 'cat_modo_transporte',
            'MODALIDAD_EXPORTACION': 'cat_modalidad_exportacion', 'UNIDAD_FISICA': 'cat_unidad_fisica',
            'TIPO_IDENTIFICACION': 'cat_tipo_identificacion', 'TIPO_CERTIFICADO_ORIGEN': 'cat_certificado_origen',
            'FORMA_PAGO': 'cat_forma_pago', 'COD_REGIMEN_CAN': 'cat_regimen_can', 'LUGAR_SALIDA': 'cat_lugar_salida',
            'TIPO_USUARIO': 'cat_tipo_usuario'}
    for dom, tabla in CATS.items():
        crear(tabla, f"SELECT CODIGO, DESCRIPCION, FUENTE, CONFIANZA, NOTA FROM _cat WHERE DOMINIO = '{dom}'", ['CODIGO'])
        dic(tabla, '(tabla)', None, f'Catálogo de {dom}: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA', 'Capa analítica, catálogos')
    con.execute("CREATE VIEW catalogo_codigos AS " + " UNION ALL ".join(
        f"SELECT '{d}' AS DOMINIO, * FROM {t}" for d, t in CATS.items()))
    log('2. Catálogos', 'Un catálogo por dominio (cat_*) con llave primaria; catalogo_codigos queda como vista que los une',
        len(filas_cat), None, 'Nuevas descripciones para certificado de origen, forma de pago, régimen CAN, lugar de salida y tipo de usuario, '
        'cada una con FUENTE y CONFIANZA (oficial, inferida o sin fuente oficial).')

    # ---------------------------------------------------------------- 3. ciudad del comprador normalizada (aproximada)
    US_SUF = ['ESTADOS UNIDOS DE AMERICA', 'ESTADOS UNIDOS', 'ESTADOS UNIDO', 'ESTADOS UNID', 'ESTADOS UNI', 'ESTADOS UN',
              'UNITED STATES', 'EE UU', 'EEUU', 'U S A', 'USA', 'US', 'D C', 'DC']
    US_EST = {'AL': 'ALABAMA', 'AK': 'ALASKA', 'AZ': 'ARIZONA', 'AR': 'ARKANSAS', 'CA': 'CALIFORNIA', 'CO': 'COLORADO',
              'CT': 'CONNECTICUT', 'DE': 'DELAWARE', 'FL': 'FLORIDA', 'GA': 'GEORGIA', 'HI': 'HAWAII', 'ID': 'IDAHO',
              'IL': 'ILLINOIS', 'IN': 'INDIANA', 'IA': 'IOWA', 'KS': 'KANSAS', 'KY': 'KENTUCKY', 'LA': 'LOUISIANA',
              'ME': 'MAINE', 'MD': 'MARYLAND', 'MA': 'MASSACHUSETTS', 'MI': 'MICHIGAN', 'MN': 'MINNESOTA',
              'MS': 'MISSISSIPPI', 'MO': 'MISSOURI', 'MT': 'MONTANA', 'NE': 'NEBRASKA', 'NV': 'NEVADA',
              'NH': 'NEW HAMPSHIRE', 'NJ': 'NEW JERSEY', 'NM': 'NEW MEXICO', 'NY': 'NEW YORK', 'NC': 'NORTH CAROLINA',
              'ND': 'NORTH DAKOTA', 'OH': 'OHIO', 'OK': 'OKLAHOMA', 'OR': 'OREGON', 'PA': 'PENNSYLVANIA',
              'RI': 'RHODE ISLAND', 'SC': 'SOUTH CAROLINA', 'SD': 'SOUTH DAKOTA', 'TN': 'TENNESSEE', 'TX': 'TEXAS',
              'UT': 'UTAH', 'VT': 'VERMONT', 'VA': 'VIRGINIA', 'WA': 'WASHINGTON', 'WV': 'WEST VIRGINIA',
              'WI': 'WISCONSIN', 'WY': 'WYOMING', 'FLA': 'FLORIDA'}
    US_TODOS = sorted(set(US_SUF) | set(US_EST) | set(US_EST.values()), key=len, reverse=True)

    def sin_tildes(s):
        s = unicodedata.normalize('NFKD', s.upper())
        return ''.join(ch for ch in s if not unicodedata.combining(ch))

    def norm_ciudad(c, pais):
        """Quita tildes, puntuación, códigos postales y lo que sigue a , / ; ( o ' - '; en EE. UU. quita estado y país."""
        if c is None:
            return None
        s = sin_tildes(c)
        letras = lambda t: len(re.findall(r'[A-Z]', t))
        partes = [p for p in re.split(r'\s*[,/;()]\s*|\s+-\s+', s) if letras(p) >= 3]
        s = partes[0] if partes else s
        s = re.sub(r'[^A-Z0-9 ]', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        s = re.sub(r'^(\d+\s+)+', '', s)
        s = re.sub(r'(\s+\d+)+$', '', s).strip()
        if pais == 'USA':
            cambio = True
            while cambio:
                cambio = False
                for suf in US_TODOS:
                    resto = re.sub(r'(\s+\d+)+$', '', s[:-(len(suf) + 1)]).strip() if s.endswith(' ' + suf) else ''
                    if letras(resto) >= 3 and resto not in US_EST:
                        s, cambio = resto, True
                        break
        return s if letras(s) >= 2 else None

    pares = con.execute("""SELECT CIUDAD_DESTINATARIO, COD_PAIS_DESTINO, count(*) N_LINEAS
                           FROM dep.hechos_exportaciones WHERE CIUDAD_DESTINATARIO IS NOT NULL GROUP BY 1, 2""").df()
    pares['CIUDAD_NORMALIZADA'] = [norm_ciudad(c, p) for c, p in zip(pares.CIUDAD_DESTINATARIO, pares.COD_PAIS_DESTINO)]
    con.register('pares_df', pares)
    crear('map_ciudad_destinatario', "SELECT CIUDAD_DESTINATARIO, COD_PAIS_DESTINO, CIUDAD_NORMALIZADA, N_LINEAS FROM pares_df ORDER BY N_LINEAS DESC",
          ['CIUDAD_DESTINATARIO', 'COD_PAIS_DESTINO'], [('COD_PAIS_DESTINO', 'dim_pais', 'COD_PAIS')])
    con.unregister('pares_df')
    antes, despues = q("SELECT count(*), count(DISTINCT (CIUDAD_NORMALIZADA, COD_PAIS_DESTINO)) FROM map_ciudad_destinatario")
    log('3. Ciudad', 'Ciudad del comprador normalizada (aproximada): sin tildes, puntuación ni código postal; en EE. UU., sin estado ni país',
        None, None, f'Combinaciones ciudad-país: {miles(antes)} antes y {miles(despues)} después. La vista vw_ciudad_comprador_por_completar '
        'lista por NIT los registros que siguen sin una ciudad confiable.')

    # ---------------------------------------------------------------- 4. directorio: correcciones, Supersociedades comparable e historia de nombres
    COMILLAS = '"“”\''
    def limpia_html(s):
        """Decodifica entidades HTML y quita comillas solo si envuelven todo el nombre."""
        if s is None:
            return None
        s = html.unescape(s).strip()
        if len(s) > 1 and s[0] in COMILLAS and s[-1] in COMILLAS:
            s = s[1:-1].strip()
        return s or None

    FORMAS = [(r'\bSOCIEDAD POR ACCIONES SIMPLIFICADA\b', 'SAS'), (r'\bSOCIEDAD ANONIMA\b', 'SA'),
              (r'\bCOMERCIALIZADORA INTERNACIONAL\b', 'CI'), (r'\bBENEFICIO E INTERES COLECTIVO\b', 'BIC'), (r'\bS A S\b', 'SAS'), (r'\bS C A\b', 'SCA'),
              (r'\bS EN C\b', 'SENC'), (r'\bS A\b', 'SA'), (r'\bE U\b', 'EU'), (r'\bC I\b', 'CI'), (r'\bLIMITADA\b', 'LTDA'),
              (r'\bLIMITED\b', 'LTD'), (r'\bCORPORATION\b', 'CORP'), (r'\bINCORPORATED\b', 'INC')]
    TOK_FORMA = {'SAS', 'SA', 'LTDA', 'SCA', 'SCS', 'EU', 'SENC', 'LTD', 'AG', 'INC', 'LLC', 'CORP', 'GMBH', 'BV', 'SL', 'SRL'}
    TOK_ESTADO = {'LIQUIDACION', 'REORGANIZACION', 'REESTRUCTURACION'}

    def canon(n):
        s = re.sub(r'[^A-Z0-9]+', ' ', sin_tildes(n)).strip()
        for a, b in FORMAS:
            s = re.sub(a, b, s)
        return re.sub(r'\s+', ' ', s).strip()

    def nucleo(c):
        return ' '.join(t for t in c.split() if t not in TOK_FORMA | TOK_ESTADO | {'CI', 'BIC', 'EN', 'SUCURSAL', 'COLOMBIA', 'PYME'}
                        and not t.startswith(('LIQUIDACI', 'REORGANIZACI', 'REESTRUCTURACI')))

    def tipo_cambio(nombres, actual):
        """Clasifica las variantes de razón social de un NIT; la actual es la más reciente de la DIAN."""
        if not nombres or '|' not in nombres:
            return None
        crudos = nombres.split(' | ')
        planos = [re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9]+', ' ', sin_tildes(v))).strip() for v in crudos]
        vs = [canon(v) for v in crudos]
        act = canon(actual) if actual else vs[-1]
        tiene = lambda c, toks: bool(set(c.split()) & toks)
        en_proceso = lambda c: any(t.startswith(('LIQUIDACI', 'REORGANIZACI', 'REESTRUCTURACI')) for t in c.split())
        FORMATO = 'Solo formato (puntuación, abreviatura o texto cortado)'
        if len(set(vs)) == 1 or len({v.replace(' ', '') for v in vs}) == 1:
            return FORMATO
        # la DIAN corta la razón social a 60 caracteres: si la variante cortada es prefijo de otra, es el mismo nombre
        pl = max(planos, key=len)
        if all(p == pl or (pl.startswith(p) and len(c) >= 55) for p, c in zip(planos, crudos)):
            return FORMATO
        nucleos = {nucleo(v) for v in vs}
        nl = max(nucleos, key=len)
        mismo_nucleo = len(nucleos) == 1 or all(n == nl or (nl.startswith(n) and len(n) >= 25) for n in nucleos)
        if not mismo_nucleo:
            return 'Cambió de nombre'
        if any(en_proceso(v) for v in vs):
            return 'Entró en liquidación o reorganización' if en_proceso(act) else 'Salió de liquidación o reorganización'
        if len({tiene(v, {'CI'}) for v in vs}) > 1:
            return 'Adoptó la figura C.I.' if tiene(act, {'CI'}) else 'Dejó la figura C.I.'
        if len({tiene(v, {'BIC'}) for v in vs}) > 1:
            return 'Adoptó la condición BIC' if tiene(act, {'BIC'}) else 'Dejó la condición BIC'
        formas = [frozenset(set(v.split()) & TOK_FORMA) for v in vs]
        if any(not f for f in formas) or len(set(formas)) == 1:
            return FORMATO          # una variante simplemente omite la forma jurídica
        return 'Cambió de forma jurídica'

    def es_ci(dian, rues):
        return any(n and 'CI' in canon(n).split() for n in (dian, rues))

    con.create_function('limpia_html', limpia_html, ['VARCHAR'], 'VARCHAR', null_handling='special')
    con.create_function('tipo_cambio', tipo_cambio, ['VARCHAR', 'VARCHAR'], 'VARCHAR', null_handling='special')
    con.create_function('es_ci', es_ci, ['VARCHAR', 'VARCHAR'], 'BOOLEAN', null_handling='special')

    factor = {a: 1.0 for a in range(2021, 2026)}
    for a in range(2021, 2025):
        for t in range(a + 1, 2026):
            factor[a] *= 1 + IPC[t] / 100
    caso_factor = 'CASE SS_ANO_CORTE ' + ' '.join(f'WHEN {a} THEN {f:.6f}' for a, f in factor.items()) + ' END'
    trm = dict(con.execute("SELECT ANIO, sum(VALOR_FOB_COP) / sum(VALOR_FOB_USD) FROM dep.hechos_exportaciones GROUP BY 1").fetchall())

    crear('dim_exportador_analitica', f"""
      SELECT * EXCLUDE (TIPO_EXPORTADOR, EN_DIRECTORIO_ENTRADA) REPLACE (
               CASE WHEN SECOP_VALOR_CONTRATOS_COP > {SECOP_MAX_COP} THEN NULL ELSE SECOP_VALOR_CONTRATOS_COP END AS SECOP_VALOR_CONTRATOS_COP,
               nullif(ULTIMO_ANO_RENOVADO, 0) AS ULTIMO_ANO_RENOVADO,
               limpia_html(RAZON_SOCIAL_RUES) AS RAZON_SOCIAL_RUES,
               coalesce(FOB_USD_2024, 0) AS FOB_USD_2024, coalesce(FOB_USD_2025, 0) AS FOB_USD_2025, coalesce(FOB_USD_2026, 0) AS FOB_USD_2026),
             coalesce(SECOP_VALOR_CONTRATOS_COP > {SECOP_MAX_COP}, false) AS FLAG_SECOP_VALOR_INVALIDO,
             -- Supersociedades comparable
             (SS_ANO_CORTE >= 2024) AS SS_CIFRAS_RECIENTES,
             round({caso_factor}, 6) AS SS_FACTOR_IPC_A_DIC2025,
             round(SS_INGRESOS_OPERACIONALES_BILLONES_COP * {caso_factor}, 4) AS SS_INGRESOS_BILLONES_COP_DIC2025,
             round(SS_TOTAL_ACTIVOS_BILLONES_COP * {caso_factor}, 4) AS SS_ACTIVOS_BILLONES_COP_DIC2025,
             round(100 * CASE SS_ANO_CORTE WHEN 2024 THEN coalesce(FOB_USD_2024, 0) * {trm[2024]:.4f}
                                           WHEN 2025 THEN coalesce(FOB_USD_2025, 0) * {trm[2025]:.4f} END
                   / nullif(SS_INGRESOS_OPERACIONALES_BILLONES_COP * 1e12, 0), 2) AS SS_INTENSIDAD_EXPORTADORA_PCT,
             -- historia de razón social y domicilio
             CASE WHEN NOMBRES_EN_FUENTE IS NULL THEN 1 ELSE len(string_split(NOMBRES_EN_FUENTE, ' | ')) END AS N_RAZONES_SOCIALES_DIAN,
             tipo_cambio(NOMBRES_EN_FUENTE, RAZON_SOCIAL) AS TIPO_CAMBIO_RAZON_SOCIAL,
             es_ci(RAZON_SOCIAL, RAZON_SOCIAL_RUES) AS ES_COMERCIALIZADORA_INTERNACIONAL,
             (ESTADO_MATRICULA ILIKE '%CONSTITUCI%TRASLADO%') AS ES_TRASLADO_DOMICILIO,
             year(FECHA_MATRICULA) AS ANIO_MATRICULA,
             (ESTADO_MATRICULA ILIKE '%CONSTITUCI%TRASLADO%' AND FECHA_MATRICULA >= DATE '2024-01-01') AS TRASLADO_EN_PERIODO,
             (FECHA_MATRICULA > strptime(PRIMER_MES || '-01', '%Y-%m-%d')) AS MATRICULA_POSTERIOR_A_PRIMERA_EXPORTACION
      FROM dep.dim_exportador ORDER BY RANKING_NACIONAL_FOB""", ['NIT'],
          [('COD_MPIO_DIAN_DIRECCION_PROPIA', 'dim_municipio', 'COD_MPIO'), ('COD_DEPTO_ORIGEN_PRINCIPAL', 'dim_departamento', 'COD_DEPTO')])
    n = q(f"SELECT count(*) FROM dep.dim_exportador WHERE SECOP_VALOR_CONTRATOS_COP > {SECOP_MAX_COP}")[0]
    log('4. Directorio', 'Total SECOP mayor a COP 100 billones pasa a nulo (FLAG_SECOP_VALOR_INVALIDO); la empresa se conserva porque sí exportó',
        n, None, 'NIT 800111618 (Maquinarias para Áreas Verdes S.A.): una exportación de USD 2.236 a EE. UU. en dic-2025 (subpartida 8407900090)')
    log('4. Directorio', 'Año de renovación 0 a nulo; razón social RUES sin entidades HTML ni comillas envolventes; FOB por año nulo a 0; '
        'se retiran TIPO_EXPORTADOR y EN_DIRECTORIO_ENTRADA (un solo valor)',
        q("SELECT count(*) FROM dep.dim_exportador WHERE ULTIMO_ANO_RENOVADO = 0 OR FOB_USD_2024 IS NULL OR FOB_USD_2025 IS NULL OR FOB_USD_2026 IS NULL")[0])
    n = q("SELECT count(*) FROM dim_exportador_analitica WHERE SS_ANO_CORTE IS NOT NULL")[0]
    log('4. Supersociedades', 'Ingresos y activos llevados a pesos de diciembre de 2025 con el IPC; intensidad exportadora = FOB del año de corte × '
        'tasa de cambio DIAN del año / ingresos (solo cortes 2024 y 2025)', n, None,
        'IPC dic-dic: ' + ', '.join(f'{a} {dec(v)} %' for a, v in IPC.items()) + f'. Tasa implícita DIAN: 2024 {trm[2024]:,.0f} y 2025 {trm[2025]:,.0f} COP/USD.'.replace(',', '.'))
    n = q("SELECT count(*) FROM dim_exportador_analitica WHERE N_RAZONES_SOCIALES_DIAN > 1")[0]
    log('4. Historia', 'Historia de razón social (N_RAZONES_SOCIALES_DIAN, TIPO_CAMBIO_RAZON_SOCIAL) y de domicilio (ES_TRASLADO_DOMICILIO, '
        'TRASLADO_EN_PERIODO, MATRICULA_POSTERIOR_A_PRIMERA_EXPORTACION) por NIT', n, None,
        'La base no trae la cámara de origen ni el motivo del traslado; las causas no se pueden inferir con estos datos')

    # ---------------------------------------------------------------- 5. referencias de precio, banderas y ajustes
    con.execute(f"""CREATE TEMP TABLE base_precio AS
      SELECT h.ID_REGISTRO, h.SUBPARTIDA, s.SUBPARTIDA_SA6, h.COD_UNIDAD_FISICA, h.VALOR_FOB_USD, h.PESO_NETO_KGS, h.CANTIDAD_UNIDADES_FISICAS,
             (h.COD_MODALIDAD_EXPORTACION IN {MODALIDADES_COMERCIALES}) AS ES_COMERCIAL,
             CASE WHEN h.PESO_NETO_KGS > 0 THEN ln(h.VALOR_FOB_USD / h.PESO_NETO_KGS) END AS lkg,
             CASE WHEN h.CANTIDAD_UNIDADES_FISICAS > 0 THEN ln(h.VALOR_FOB_USD / h.CANTIDAD_UNIDADES_FISICAS) END AS lun,
             CASE WHEN h.PESO_NETO_KGS > 0 AND h.PESO_BRUTO_KGS >= h.PESO_NETO_KGS THEN h.PESO_BRUTO_KGS / h.PESO_NETO_KGS END AS rbn
      FROM dep.hechos_exportaciones h JOIN dep.dim_subpartida s USING (SUBPARTIDA)""")
    for nombre, val, claves, extra in [('kg_sp', 'lkg', 'SUBPARTIDA', ', median(rbn) rbn'), ('kg_sa6', 'lkg', 'SUBPARTIDA_SA6', ', median(rbn) rbn'),
                                       ('un_sp', 'lun', 'SUBPARTIDA, COD_UNIDAD_FISICA', ''), ('un_sa6', 'lun', 'SUBPARTIDA_SA6, COD_UNIDAD_FISICA', '')]:
        con.execute(f"""CREATE TEMP TABLE ref_{nombre} AS
          SELECT {claves}, count(*) n, quantile_cont({val}, 0.25) q1, quantile_cont({val}, 0.75) q3, median({val}) med {extra}
          FROM base_precio WHERE {val} IS NOT NULL AND ES_COMERCIAL GROUP BY ALL HAVING count(*) >= {N_MIN}""")
    W = f"greatest(q3 - q1, {IQR_MIN})"
    con.execute(f"""CREATE TEMP TABLE banderas AS
      WITH r AS (
        SELECT b.*,
               CASE WHEN a.n IS NOT NULL THEN 'SUBPARTIDA' WHEN c.n IS NOT NULL THEN 'SA6' END AS nk,
               CASE WHEN a.n IS NOT NULL THEN a.q1 ELSE c.q1 END AS k1, CASE WHEN a.n IS NOT NULL THEN a.q3 ELSE c.q3 END AS k3,
               CASE WHEN a.n IS NOT NULL THEN a.med ELSE c.med END AS kmed, CASE WHEN a.n IS NOT NULL THEN a.rbn ELSE c.rbn END AS krbn,
               CASE WHEN d.n IS NOT NULL THEN 'SUBPARTIDA' WHEN e.n IS NOT NULL THEN 'SA6' END AS nu,
               CASE WHEN d.n IS NOT NULL THEN d.q1 ELSE e.q1 END AS u1, CASE WHEN d.n IS NOT NULL THEN d.q3 ELSE e.q3 END AS u3,
               CASE WHEN d.n IS NOT NULL THEN d.med ELSE e.med END AS umed
        FROM base_precio b
        LEFT JOIN ref_kg_sp a USING (SUBPARTIDA) LEFT JOIN ref_kg_sa6 c USING (SUBPARTIDA_SA6)
        LEFT JOIN ref_un_sp d USING (SUBPARTIDA, COD_UNIDAD_FISICA) LEFT JOIN ref_un_sa6 e USING (SUBPARTIDA_SA6, COD_UNIDAD_FISICA)),
      f0 AS (
        SELECT *,
               CASE WHEN lkg IS NOT NULL AND nk IS NOT NULL THEN (lkg < k1 - {K_IQR} * greatest(k3 - k1, {IQR_MIN}) OR lkg > k3 + {K_IQR} * greatest(k3 - k1, {IQR_MIN})) END AS fk,
               CASE WHEN lun IS NOT NULL AND nu IS NOT NULL THEN (lun < u1 - {K_IQR} * greatest(u3 - u1, {IQR_MIN}) OR lun > u3 + {K_IQR} * greatest(u3 - u1, {IQR_MIN})) END AS fu
        FROM r),
      f AS (
        SELECT *,
               coalesce(fk AND abs(lkg - kmed) >= ln({FACTOR_ERROR}), false) AS ek,     -- precio por kilo extremo
               coalesce(fu AND abs(lun - umed) >= ln({FACTOR_ERROR}), false) AS eu,     -- precio por unidad extremo
               (COD_UNIDAD_FISICA = 'KG') AS ukg
        FROM f0),
      g AS (
        SELECT *,
               -- peso y cantidad extremos a la vez (unidad distinta del kilo): no se sabe qué campo falla; posible error de FOB
               (NOT ukg AND ek AND eu) AS conflicto
        FROM f),
      a AS (
        SELECT *,
               (ES_COMERCIAL AND nk IS NOT NULL AND NOT conflicto AND (ek OR coalesce(PESO_NETO_KGS, 0) = 0)) AS peso_mal,
               (ES_COMERCIAL AND nu IS NOT NULL AND NOT conflicto AND eu AND NOT ukg) AS cant_mal
        FROM g)
      SELECT ID_REGISTRO,
             nk AS NIVEL_REFERENCIA_PRECIO_KG, CAST(exp(lkg - kmed) AS FLOAT) AS RAZON_PRECIO_KG_VS_MEDIANA, fk AS FLAG_PRECIO_KG_ATIPICO,
             nu AS NIVEL_REFERENCIA_PRECIO_UNIDAD, CAST(exp(lun - umed) AS FLOAT) AS RAZON_PRECIO_UNIDAD_VS_MEDIANA, fu AS FLAG_CANTIDAD_ATIPICA,
             (coalesce(fk, false) OR coalesce(fu, false)) AS FLAG_ATIPICO,
             conflicto AS FLAG_POSIBLE_ERROR_FOB,
             -- peso: desde la cantidad (kilos por unidad típicos del grupo) si la cantidad es confiable; si no, desde el FOB
             CASE WHEN peso_mal THEN CASE WHEN NOT ukg AND nu IS NOT NULL AND NOT eu AND CANTIDAD_UNIDADES_FISICAS > 0
                                          THEN CANTIDAD_UNIDADES_FISICAS * exp(umed - kmed) ELSE VALOR_FOB_USD / exp(kmed) END END AS PESO_NETO_KGS_AJUSTADO,
             CASE WHEN peso_mal THEN CASE WHEN NOT ukg AND nu IS NOT NULL AND NOT eu AND CANTIDAD_UNIDADES_FISICAS > 0
                                          THEN CANTIDAD_UNIDADES_FISICAS * exp(umed - kmed) ELSE VALOR_FOB_USD / exp(kmed) END * coalesce(krbn, 1) END AS PESO_BRUTO_KGS_AJUSTADO,
             -- cantidad: desde el peso (unidades por kilo típicas del grupo) si el peso es confiable; si no, desde el FOB;
             -- con unidad KG la cantidad es el peso
             CASE WHEN cant_mal THEN CASE WHEN nk IS NOT NULL AND NOT ek AND PESO_NETO_KGS > 0
                                          THEN PESO_NETO_KGS * exp(kmed - umed) ELSE VALOR_FOB_USD / exp(umed) END
                  WHEN peso_mal AND ukg THEN VALOR_FOB_USD / exp(kmed) END AS CANTIDAD_UNIDADES_FISICAS_AJUSTADA,
             CASE WHEN peso_mal AND cant_mal THEN 'Peso y cantidad'
                  WHEN peso_mal THEN CASE WHEN NOT ukg AND nu IS NOT NULL AND NOT eu AND CANTIDAD_UNIDADES_FISICAS > 0 THEN 'Peso desde la cantidad'
                                          ELSE 'Peso desde el FOB' END || CASE WHEN ukg THEN ' (y cantidad en kilos)' ELSE '' END
                  WHEN cant_mal THEN CASE WHEN nk IS NOT NULL AND NOT ek AND PESO_NETO_KGS > 0 THEN 'Cantidad desde el peso' ELSE 'Cantidad desde el FOB' END
             END AS METODO_AJUSTE
      FROM a""")

    # ---------------------------------------------------------------- 6. tabla de hechos
    fks_hechos = [('NIT_EXPORTADOR', 'dim_exportador_analitica', 'NIT'), ('SUBPARTIDA', 'dim_subpartida', 'SUBPARTIDA'),
                  ('COD_PAIS_DESTINO', 'dim_pais', 'COD_PAIS'), ('COD_PAIS_BANDERA', 'dim_pais', 'COD_PAIS'),
                  ('COD_ZONA_FRANCA_DESTINO', 'dim_zona_franca', 'COD_ZONA_FRANCA'), ('COD_ADUANA_DESPACHO', 'dim_aduana', 'COD_ADUANA'),
                  ('COD_ADUANA_SALIDA', 'dim_aduana', 'COD_ADUANA'), ('COD_DEPTO_PROCEDENCIA', 'dim_departamento', 'COD_DEPTO'),
                  ('COD_DEPTO_ORIGEN', 'dim_departamento', 'COD_DEPTO'), ('COD_MPIO_DIRECCION_DECLARADA', 'dim_municipio', 'COD_MPIO'),
                  ('NIT_DECLARANTE', 'dim_declarante', 'NIT_DECLARANTE'), ('CLASE_EXPORTADOR', 'cat_clase_exportador', 'CODIGO'),
                  ('COD_MODO_TRANSPORTE', 'cat_modo_transporte', 'CODIGO'), ('COD_MODALIDAD_EXPORTACION', 'cat_modalidad_exportacion', 'CODIGO'),
                  ('COD_UNIDAD_FISICA', 'cat_unidad_fisica', 'CODIGO'), ('TIPO_IDENTIFICACION', 'cat_tipo_identificacion', 'CODIGO'),
                  ('TIPO_CERTIFICADO_ORIGEN', 'cat_certificado_origen', 'CODIGO'), ('FORMA_PAGO', 'cat_forma_pago', 'CODIGO'),
                  ('COD_REGIMEN_CAN', 'cat_regimen_can', 'CODIGO'), ('COD_LUGAR_SALIDA', 'cat_lugar_salida', 'CODIGO'),
                  ('TIPO_USUARIO', 'cat_tipo_usuario', 'CODIGO')]
    sql_hechos = CBA.sql_hechos('dep.hechos_exportaciones', 'banderas')
    if FK_EN_HECHOS:
        crear('hechos_analitica', sql_hechos, ['ID_REGISTRO'], fks_hechos)
    else:
        crear('hechos_analitica', sql_hechos, ['ID_REGISTRO'])
        for col, ref, refcol in fks_hechos:
            h = q(f"SELECT count(*) FROM hechos_analitica WHERE {col} IS NOT NULL AND {col} NOT IN (SELECT {refcol} FROM {ref})")[0]
            assert h == 0, f'hechos_analitica.{col}: {h} huérfanos'
            relaciones.append(('hechos_analitica', col, ref, refcol, 'FOREIGN KEY validada en cada construcción (no declarada)', h))

    n, f = q("SELECT count(*), sum(VALOR_FOB_USD) FROM dep.hechos_exportaciones WHERE ES_DESTINO_ZONA_FRANCA IS NULL")
    log('5. Correcciones', 'ES_DESTINO_ZONA_FRANCA nulo pasa a FALSO: líneas con destino Namibia (NAM)', n, f,
        'Namibia tiene código ISO alfa-2 "NA", que en la depuración se leyó como nulo')
    n = q("SELECT count(*) FILTER (WHERE OFICINA <> '99' OR COD_MODALIDAD_PRECEDENTE IS NOT NULL) FROM dep.hechos_exportaciones")[0]
    log('5. Columnas', 'Se retiran OFICINA y COD_MODALIDAD_PRECEDENTE: la DIAN no publica su tabla y no se pueden interpretar', n, None,
        'Siguen en la BD depurada. TIPO_USUARIO se conserva: su código 22 identifica el régimen de hidrocarburos (25 % del FOB)')
    for col, txt in [('FLAG_PRECIO_KG_ATIPICO', 'Precio por kilo neto atípico dentro de su subpartida'),
                     ('FLAG_CANTIDAD_ATIPICA', 'Precio por unidad física atípico dentro de su subpartida y unidad (cantidades imposibles)'),
                     ('FLAG_ATIPICO', 'Línea con cualquiera de las dos banderas')]:
        n, f, ne = q(f"SELECT count(*) FILTER (WHERE {col}), sum(VALOR_FOB_USD) FILTER (WHERE {col}), count({col}) FROM hechos_analitica")
        log('6. Atípicos', f'{col}: {txt}', n, f,
            f'Logaritmo del precio fuera de [Q1 - {dec(K_IQR)} RIC, Q3 + {dec(K_IQR)} RIC] (RIC mínimo {dec(IQR_MIN)}), con referencia en las '
            f'exportaciones comerciales ({", ".join(MODALIDADES_COMERCIALES)}) de la subpartida, o del SA6 si tiene menos de {N_MIN} líneas. '
            f'Líneas evaluadas: {miles(ne)}. Una bandera indica precio inusual frente a su producto, no necesariamente un error.')
    n, f, p0, p1 = q("""SELECT count(*) FILTER (WHERE PESO_NETO_KGS_AJUSTADO IS NOT NULL), sum(VALOR_FOB_USD) FILTER (WHERE PESO_NETO_KGS_AJUSTADO IS NOT NULL),
                               sum(PESO_NETO_KGS), sum(coalesce(PESO_NETO_KGS_AJUSTADO, PESO_NETO_KGS)) FROM hechos_analitica""")
    log('6. Ajustes', f'PESO_NETO_KGS_AJUSTADO y PESO_BRUTO_KGS_AJUSTADO en exportaciones comerciales con precio por kilo {FACTOR_ERROR} veces o más lejos '
        f'de la mediana (error de unidades o decimales) o con peso en cero: desde la cantidad (kilos por unidad típicos) si es confiable; si no, FOB / precio mediano', n, f,
        f'El FOB se conserva porque es la cifra oficial que publican DANE y MinCIT; se ajusta la magnitud física. No ajusta las líneas con '
        f'FLAG_POSIBLE_ERROR_FOB. Peso neto total: '
        f'{miles(round(p0 / 1e9, 2))} millones de t antes y {miles(round(p1 / 1e9, 2))} después. El bruto usa la mediana bruto/neto del grupo.')
    n, f = q("SELECT count(*) FILTER (WHERE CANTIDAD_UNIDADES_FISICAS_AJUSTADA IS NOT NULL), sum(VALOR_FOB_USD) FILTER (WHERE CANTIDAD_UNIDADES_FISICAS_AJUSTADA IS NOT NULL) FROM hechos_analitica")
    log('6. Ajustes', f'CANTIDAD_UNIDADES_FISICAS_AJUSTADA en exportaciones comerciales con precio por unidad {FACTOR_ERROR} veces o más lejos de la mediana: '
        f'desde el peso (unidades por kilo típicas) si es confiable; si no, FOB / precio mediano', n, f, f'Las atípicas moderadas (menos de {FACTOR_ERROR} veces) se marcan pero no se ajustan: suelen ser productos '
        'premium o lotes pequeños. Las no comerciales (muestras, averiadas, donaciones, temporales) tampoco se ajustan: su FOB no es un precio de mercado')

    n, f = q("SELECT count(*) FILTER (WHERE FLAG_POSIBLE_ERROR_FOB), sum(VALOR_FOB_USD) FILTER (WHERE FLAG_POSIBLE_ERROR_FOB) FROM hechos_analitica")
    log('6. Atípicos', f'FLAG_POSIBLE_ERROR_FOB: precio por kilo y por unidad extremos a la vez ({FACTOR_ERROR} veces o más, unidad distinta del kilo); '
        'no se sabe qué campo falla y la línea no se ajusta', n, f, 'Excluirlas de análisis de valor por línea si se busca máxima limpieza')

    # ---------------------------------------------------------------- 7. vistas
    con.execute(f"""CREATE VIEW vw_exportaciones AS
    SELECT h.*,
           strftime(h.PERIODO, '%Y-%m') AS ANIO_MES, h.ANIO || '-T' || ((h.MES - 1) // 3 + 1) AS TRIMESTRE,
           coalesce(h.NUMERO_FORMULARIO, 'AE-' || h.NUM_AUTORIZACION_EMBARQUE, 'R-' || h.ID_REGISTRO) AS ID_DECLARACION,
           (NOT h.ES_DESTINO_ZONA_FRANCA AND h.COD_PAIS_DESTINO <> 'COL') AS ES_VENTA_EXTERIOR,
           (h.COD_DEPTO_ORIGEN <> '00') AS DEPTO_ORIGEN_ASIGNADO,
           (h.COD_MODALIDAD_EXPORTACION IN {MODALIDADES_COMERCIALES}) AS ES_EXPORTACION_COMERCIAL,
           coalesce(h.PESO_NETO_KGS_AJUSTADO, h.PESO_NETO_KGS) AS PESO_NETO_KGS_ANALISIS,
           coalesce(h.PESO_BRUTO_KGS_AJUSTADO, h.PESO_BRUTO_KGS) AS PESO_BRUTO_KGS_ANALISIS,
           coalesce(h.CANTIDAD_UNIDADES_FISICAS_AJUSTADA, h.CANTIDAD_UNIDADES_FISICAS) AS CANTIDAD_UNIDADES_FISICAS_ANALISIS,
           h.VALOR_FOB_USD / nullif(h.PESO_NETO_KGS, 0) AS PRECIO_USD_KG,
           h.VALOR_FOB_USD / nullif(coalesce(h.PESO_NETO_KGS_AJUSTADO, h.PESO_NETO_KGS), 0) AS PRECIO_USD_KG_ANALISIS,
           h.VALOR_FOB_USD / nullif(coalesce(h.CANTIDAD_UNIDADES_FISICAS_AJUSTADA, h.CANTIDAD_UNIDADES_FISICAS), 0) AS PRECIO_USD_UNIDAD_ANALISIS,
           sp.CAPITULO, sp.PARTIDA, sp.SUBPARTIDA_SA6, sp.SECTOR_EXPORTACION, sp.ES_MINERO_ENERGETICO, sp.ES_AGRICOLA_MADR,
           sp.PRODUCTO_AGRICOLA_MADR, sp.TRADICION_AGRICOLA_MADR,
           e.RAZON_SOCIAL, e.VINCULO_ANTIOQUIA, coalesce(e.EMPRESA_ANTIOQUENA, false) AS EMPRESA_ANTIOQUENA,
           coalesce(e.ES_EXPORTADOR_ANTIOQUENO, false) AS ES_EXPORTADOR_ANTIOQUENO, e.CAMARA_COMERCIO, e.CIIU_PRINCIPAL_RUES,
           e.SECTOR_EXPORTADOR_PRINCIPAL, m.CIUDAD_NORMALIZADA AS CIUDAD_DESTINATARIO_NORM,
           cl.DESCRIPCION AS CLASE_EXPORTADOR_DESC, dc.RAZON_SOCIAL_DECLARANTE, mu.MUNICIPIO AS MUNICIPIO_DIRECCION_DECLARADA,
           pd.PAIS AS PAIS_DESTINO, pd.TIPO_DESTINO, zf.ZONA_FRANCA AS ZONA_FRANCA_DESTINO,
           ad1.ADUANA AS ADUANA_DESPACHO, ad2.ADUANA AS ADUANA_SALIDA, ls.DESCRIPCION AS LUGAR_SALIDA,
           dp.DEPARTAMENTO AS DEPTO_PROCEDENCIA, dor.DEPARTAMENTO AS DEPTO_ORIGEN, mt.DESCRIPCION AS MODO_TRANSPORTE,
           pb.PAIS AS PAIS_BANDERA, mo.DESCRIPCION AS MODALIDAD_EXPORTACION, un.DESCRIPCION AS UNIDAD_FISICA,
           co.DESCRIPCION AS CERTIFICADO_ORIGEN, fp.DESCRIPCION AS FORMA_PAGO_DESC, rc.DESCRIPCION AS REGIMEN_CAN_DESC,
           tu.DESCRIPCION AS TIPO_USUARIO_DESC
    FROM hechos_analitica h
    JOIN dim_subpartida sp ON sp.SUBPARTIDA = h.SUBPARTIDA
    LEFT JOIN dim_exportador_analitica e ON e.NIT = h.NIT_EXPORTADOR
    LEFT JOIN map_ciudad_destinatario m ON m.CIUDAD_DESTINATARIO = h.CIUDAD_DESTINATARIO AND m.COD_PAIS_DESTINO = h.COD_PAIS_DESTINO
    LEFT JOIN cat_clase_exportador cl ON cl.CODIGO = h.CLASE_EXPORTADOR
    LEFT JOIN dim_declarante dc ON dc.NIT_DECLARANTE = h.NIT_DECLARANTE
    LEFT JOIN dim_municipio mu ON mu.COD_MPIO = h.COD_MPIO_DIRECCION_DECLARADA
    LEFT JOIN dim_pais pd ON pd.COD_PAIS = h.COD_PAIS_DESTINO
    LEFT JOIN dim_zona_franca zf ON zf.COD_ZONA_FRANCA = h.COD_ZONA_FRANCA_DESTINO
    LEFT JOIN dim_aduana ad1 ON ad1.COD_ADUANA = h.COD_ADUANA_DESPACHO
    LEFT JOIN dim_aduana ad2 ON ad2.COD_ADUANA = h.COD_ADUANA_SALIDA
    LEFT JOIN cat_lugar_salida ls ON ls.CODIGO = h.COD_LUGAR_SALIDA
    LEFT JOIN dim_departamento dp ON dp.COD_DEPTO = h.COD_DEPTO_PROCEDENCIA
    LEFT JOIN dim_departamento dor ON dor.COD_DEPTO = h.COD_DEPTO_ORIGEN
    LEFT JOIN cat_modo_transporte mt ON mt.CODIGO = h.COD_MODO_TRANSPORTE
    LEFT JOIN dim_pais pb ON pb.COD_PAIS = h.COD_PAIS_BANDERA
    LEFT JOIN cat_modalidad_exportacion mo ON mo.CODIGO = h.COD_MODALIDAD_EXPORTACION
    LEFT JOIN cat_unidad_fisica un ON un.CODIGO = h.COD_UNIDAD_FISICA
    LEFT JOIN cat_certificado_origen co ON co.CODIGO = h.TIPO_CERTIFICADO_ORIGEN
    LEFT JOIN cat_forma_pago fp ON fp.CODIGO = h.FORMA_PAGO
    LEFT JOIN cat_regimen_can rc ON rc.CODIGO = h.COD_REGIMEN_CAN
    LEFT JOIN cat_tipo_usuario tu ON tu.CODIGO = h.TIPO_USUARIO""")
    con.execute("CREATE VIEW vw_ventas_exterior AS SELECT * FROM vw_exportaciones WHERE ES_VENTA_EXTERIOR")
    con.execute("CREATE VIEW vw_exportaciones_origen_asignado AS SELECT * FROM vw_exportaciones WHERE DEPTO_ORIGEN_ASIGNADO")
    con.execute("CREATE VIEW vw_exportaciones_antioquia AS SELECT * FROM vw_exportaciones WHERE ORIGEN_MERCANCIA_ANTIOQUIA OR ES_EXPORTADOR_ANTIOQUENO")
    con.execute("CREATE VIEW vw_directorio_antioquia AS SELECT * FROM dim_exportador_analitica WHERE ES_EXPORTADOR_ANTIOQUENO ORDER BY RANKING_ANTIOQUIA_FOB")
    con.execute("""CREATE VIEW vw_serie_mensual AS
    SELECT ANIO_MES AS PERIODO,
      -- mismas columnas y nombres que en la BD depurada
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
      count(DISTINCT NIT_EXPORTADOR) AS N_NIT_NACIONAL,
      -- nuevas en la capa analítica
      round(sum(VALOR_FOB_USD) FILTER (WHERE ES_VENTA_EXTERIOR) / 1e6, 3) AS FOB_MUSD_VENTA_EXTERIOR,
      round(sum(VALOR_FOB_USD) FILTER (WHERE DEPTO_ORIGEN_ASIGNADO) / 1e6, 3) AS FOB_MUSD_ORIGEN_ASIGNADO,
      round(sum(PESO_NETO_KGS_ANALISIS) / 1e6, 3) AS PESO_NETO_MILES_T_ANALISIS
    FROM vw_exportaciones GROUP BY 1 ORDER BY 1""")
    con.execute("""CREATE VIEW vw_validacion_mincit AS
    WITH d AS (SELECT h.ANIO || 'Q' || ((h.MES - 1) // 3 + 1) AS TRIMESTRE, round(sum(h.VALOR_FOB_USD) / 1e6) AS DIAN_TOTAL_MUSD,
                      round(sum(h.VALOR_FOB_USD) FILTER (WHERE NOT s.ES_MINERO_ENERGETICO) / 1e6) AS DIAN_NME_MUSD
               FROM hechos_analitica h JOIN dim_subpartida s USING (SUBPARTIDA) GROUP BY 1)
    SELECT d.*, r.MINCIT_TOTAL_MUSD, r.MINCIT_NME_MUSD,
           round(100 * (d.DIAN_TOTAL_MUSD - r.MINCIT_TOTAL_MUSD) / r.MINCIT_TOTAL_MUSD, 2) AS DIF_TOTAL_PCT,
           round(100 * (d.DIAN_NME_MUSD - r.MINCIT_NME_MUSD) / r.MINCIT_NME_MUSD, 2) AS DIF_NME_PCT
    FROM d LEFT JOIN ref_mincit_trimestral r USING (TRIMESTRE) ORDER BY 1""")
    con.execute("""CREATE VIEW vw_validacion_madr AS
    WITH d AS (SELECT h.ANIO, round(sum(h.VALOR_FOB_USD) FILTER (WHERE s.ES_AGRICOLA_MADR AND h.MES <= r.MESES) / 1e6, 1) AS DIAN_AGRICOLA_NACIONAL_MUSD,
                      round(sum(h.VALOR_FOB_USD) FILTER (WHERE s.ES_AGRICOLA_MADR AND h.ORIGEN_MERCANCIA_ANTIOQUIA AND h.MES <= r.MESES) / 1e6, 1) AS DIAN_AGRICOLA_ANTIOQUIA_MUSD
               FROM hechos_analitica h JOIN dim_subpartida s USING (SUBPARTIDA) JOIN ref_madr_agricola_anual r ON r.ANIO = h.ANIO GROUP BY 1)
    SELECT d.ANIO, r.MESES, d.DIAN_AGRICOLA_NACIONAL_MUSD, r.MADR_AGRICOLA_NACIONAL_MUSD, d.DIAN_AGRICOLA_ANTIOQUIA_MUSD, r.MADR_AGRICOLA_ANTIOQUIA_MUSD
    FROM d JOIN ref_madr_agricola_anual r USING (ANIO) ORDER BY 1""")
    con.execute("""CREATE VIEW vw_validacion_dane AS
    SELECT r.PERIODO_REFERENCIA, round(sum(h.VALOR_FOB_USD) / 1e6, 1) AS BASE_FOB_MUSD, r.DANE_FOB_MUSD,
           round(100 * (sum(h.VALOR_FOB_USD) / 1e6 - r.DANE_FOB_MUSD) / r.DANE_FOB_MUSD, 3) AS DIF_PCT, r.FUENTE, r.URL
    FROM ref_dane_publicaciones r JOIN hechos_analitica h ON h.PERIODO BETWEEN r.PERIODO_DESDE AND r.PERIODO_HASTA
    GROUP BY r.PERIODO_REFERENCIA, r.DANE_FOB_MUSD, r.FUENTE, r.URL, r.PERIODO_DESDE, r.PERIODO_HASTA ORDER BY r.PERIODO_DESDE, r.PERIODO_HASTA DESC""")
    ESTADOS_US = "('" + "','".join(sorted(set(US_EST.values()))) + "')"
    con.execute(f"""CREATE VIEW vw_ciudad_comprador_por_completar AS
    WITH x AS (
      SELECT v.NIT_EXPORTADOR AS NIT, v.RAZON_SOCIAL, v.COD_PAIS_DESTINO, v.PAIS_DESTINO, v.CIUDAD_DESTINATARIO, v.VALOR_FOB_USD,
             CASE WHEN v.CIUDAD_DESTINATARIO IS NULL THEN 'Sin ciudad'
                  WHEN v.CIUDAD_DESTINATARIO_NORM IS NULL THEN 'Sin letras'
                  WHEN v.CIUDAD_DESTINATARIO LIKE '%�%' THEN 'Caracteres dañados'
                  WHEN v.COD_PAIS_DESTINO = 'USA' AND v.CIUDAD_DESTINATARIO_NORM IN {ESTADOS_US} THEN 'Estado en vez de ciudad'
                  WHEN upper(strip_accents(v.CIUDAD_DESTINATARIO_NORM)) = upper(strip_accents(v.PAIS_DESTINO))
                       AND v.COD_PAIS_DESTINO NOT IN ('PAN','SGP','MEX','GTM','KWT','LUX','MCO','DJI','SMR','VAT','HKG','MAC','BRN') THEN 'País en vez de ciudad'
             END AS PROBLEMA
      FROM vw_exportaciones v WHERE v.ES_VENTA_EXTERIOR AND v.NIT_EXPORTADOR IS NOT NULL)
    SELECT NIT, RAZON_SOCIAL, count(*) AS N_LINEAS_POR_COMPLETAR, round(sum(VALOR_FOB_USD), 2) AS FOB_USD_POR_COMPLETAR,
           string_agg(DISTINCT PROBLEMA, '; ') AS PROBLEMAS, string_agg(DISTINCT PAIS_DESTINO, '; ') AS PAISES,
           string_agg(DISTINCT coalesce(CIUDAD_DESTINATARIO, '(vacío)'), ' | ') AS VALORES_EN_FUENTE
    FROM x WHERE PROBLEMA IS NOT NULL GROUP BY 1, 2 ORDER BY FOB_USD_POR_COMPLETAR DESC""")
    log('7. Vistas', 'vw_exportaciones (atributos derivados y nombres), vw_ventas_exterior, vw_exportaciones_origen_asignado, vw_exportaciones_antioquia, '
        'vw_directorio_antioquia, vw_serie_mensual, vw_validacion_mincit, vw_validacion_madr, vw_validacion_dane y vw_ciudad_comprador_por_completar', None, None,
        'Los atributos que salen de una dimensión o de una fórmula simple viven en la vista y no se repiten en la tabla de hechos')
    n, f = q("SELECT count(*), sum(VALOR_FOB_USD) FROM vw_exportaciones WHERE NOT DEPTO_ORIGEN_ASIGNADO")
    log('7. Vistas', 'vw_exportaciones_origen_asignado excluye "00 Departamentos varios" para análisis regional; los registros se conservan en la base',
        n, f, 'Son 81 % del crudo exportado (Ecopetrol, Reficar y otras petroleras); borrarlos rompería el cuadre con DANE y MinCIT')

    # ---------------------------------------------------------------- 8. agregados con llaves
    crear('exportador_pais', """
      SELECT NIT_EXPORTADOR AS NIT, COD_PAIS_DESTINO, sum(VALOR_FOB_USD) AS FOB_USD, count(*) AS N_LINEAS,
             round(100 * sum(VALOR_FOB_USD) / sum(sum(VALOR_FOB_USD)) OVER (PARTITION BY NIT_EXPORTADOR), 3) AS PCT_FOB_NIT,
             row_number() OVER (PARTITION BY NIT_EXPORTADOR ORDER BY sum(VALOR_FOB_USD) DESC, COD_PAIS_DESTINO) AS RANKING_EN_NIT
      FROM hechos_analitica WHERE NIT_EXPORTADOR IS NOT NULL GROUP BY 1, 2 ORDER BY 1, RANKING_EN_NIT""",
          ['NIT', 'COD_PAIS_DESTINO'], [('NIT', 'dim_exportador_analitica', 'NIT'), ('COD_PAIS_DESTINO', 'dim_pais', 'COD_PAIS')])
    crear('exportador_subpartida', """
      SELECT NIT_EXPORTADOR AS NIT, SUBPARTIDA, sum(VALOR_FOB_USD) AS FOB_USD, count(*) AS N_LINEAS,
             round(100 * sum(VALOR_FOB_USD) / sum(sum(VALOR_FOB_USD)) OVER (PARTITION BY NIT_EXPORTADOR), 3) AS PCT_FOB_NIT,
             row_number() OVER (PARTITION BY NIT_EXPORTADOR ORDER BY sum(VALOR_FOB_USD) DESC, SUBPARTIDA) AS RANKING_EN_NIT
      FROM hechos_analitica WHERE NIT_EXPORTADOR IS NOT NULL GROUP BY 1, 2 ORDER BY 1, RANKING_EN_NIT""",
          ['NIT', 'SUBPARTIDA'], [('NIT', 'dim_exportador_analitica', 'NIT'), ('SUBPARTIDA', 'dim_subpartida', 'SUBPARTIDA')])
    crear('panel_exportador_mes', """
      SELECT NIT_EXPORTADOR AS NIT, PERIODO, ANIO, MES,
             sum(VALOR_FOB_USD) AS FOB_USD,
             coalesce(sum(VALOR_FOB_USD) FILTER (WHERE ES_VENTA_EXTERIOR), 0) AS FOB_USD_VENTA_EXTERIOR,
             coalesce(sum(VALOR_FOB_USD) FILTER (WHERE NOT ES_MINERO_ENERGETICO), 0) AS FOB_USD_NO_MINERO_ENERGETICO,
             coalesce(sum(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA), 0) AS FOB_USD_ORIGEN_ANTIOQUIA,
             sum(PESO_NETO_KGS_ANALISIS) AS PESO_NETO_KGS_ANALISIS,
             count(*) AS N_LINEAS, count(DISTINCT ID_DECLARACION) AS N_DECLARACIONES,
             count(DISTINCT COD_PAIS_DESTINO) AS N_PAISES, count(DISTINCT SUBPARTIDA) AS N_SUBPARTIDAS,
             count(*) FILTER (WHERE FLAG_ATIPICO) AS N_LINEAS_ATIPICAS
      FROM vw_exportaciones WHERE NIT_EXPORTADOR IS NOT NULL GROUP BY ALL ORDER BY NIT, PERIODO""",
          ['NIT', 'PERIODO'], [('NIT', 'dim_exportador_analitica', 'NIT')])
    log('8. Agregados', 'exportador_pais, exportador_subpartida y panel_exportador_mes, con llave primaria y foráneas declaradas',
        q("SELECT count(*) FROM panel_exportador_mes")[0], None, 'El panel solo tiene meses con exportaciones: para series continuas, completar con 0')

    # ---------------------------------------------------------------- 9. llaves, diccionario e información
    crear('relaciones_llaves', "SELECT * FROM (VALUES " + ', '.join(
        "(" + ', '.join('NULL' if v is None else (str(v) if isinstance(v, int) else "'" + str(v).replace("'", "''") + "'") for v in r) + ")"
        for r in relaciones) + ") t(TABLA, COLUMNAS, TABLA_REFERENCIA, COLUMNAS_REFERENCIA, TIPO, FILAS_HUERFANAS)")
    n_pk = sum(1 for r in relaciones if r[4].startswith('PRIMARY'))
    n_fk = sum(1 for r in relaciones if r[4] == 'FOREIGN KEY declarada')
    n_fv = sum(1 for r in relaciones if r[4].startswith('FOREIGN KEY validada'))
    n_pk_total = q("SELECT count(*) FROM duckdb_constraints() WHERE constraint_type = 'PRIMARY KEY'")[0] + 2  # + diccionario_datos e info_capa, que se crean después
    log('9. Llaves', f'{n_pk_total} llaves primarias (todas las tablas menos relaciones_llaves) y {n_fk} foráneas declaradas; '
        f'{n_fv} relaciones de la tabla de hechos validadas con 0 huérfanos',
        len(relaciones), None, 'En DuckDB cada llave foránea crea un índice ART: en la tabla de hechos cuestan ~47 MB y ~6 s cada una (medido), '
        'por eso se validan en vez de declararse. FK_EN_HECHOS = True las declara.')

    for c in ['OFICINA', 'COD_MODALIDAD_PRECEDENTE']:
        dicc.pop(('hechos_analitica', c), None)
    for c in ['TIPO_EXPORTADOR', 'EN_DIRECTORIO_ENTRADA']:
        dicc.pop(('dim_exportador_analitica', c), None)
    for k in [k for k in dicc if k[0] in ('catalogo_codigos', 'info_bd')]:
        dicc.pop(k)
    H, E, V, R = 'hechos_analitica', 'dim_exportador_analitica', 'vw_exportaciones', 'Capa analítica'
    for c in ['(todas las de hechos_exportaciones)', 'RAZON_SOCIAL, VINCULO_ANTIOQUIA, EMPRESA_ANTIOQUENA, ES_EXPORTADOR_ANTIOQUENO, '
              'CAMARA_COMERCIO, CIIU_PRINCIPAL_RUES, SECTOR_EXPORTADOR_PRINCIPAL', 'TRIMESTRE']:
        dicc.pop((V, c), None)                              # se reemplazan por las descripciones de la capa
    dic(V, '(todas las de hechos_analitica)', None, 'Vista lista para analizar: la tabla de hechos de la BD principal con los nombres '
        'y atributos de las dimensiones y catálogos. Es el punto de partida de cualquier análisis', 'Vista')
    for col, tipo, d in [
        ('ES_DESTINO_ZONA_FRANCA', 'BOOLEAN', 'Destino en zona franca colombiana (XCF); 5 líneas de Namibia que venían nulas pasan a FALSO'),
        ('NIVEL_REFERENCIA_PRECIO_KG', 'VARCHAR', 'Grupo de referencia del precio por kilo (exportaciones comerciales): SUBPARTIDA o SA6; nulo si no hay referencia'),
        ('RAZON_PRECIO_KG_VS_MEDIANA', 'FLOAT', 'Precio por kilo dividido por la mediana de su grupo (1 = igual a la mediana)'),
        ('FLAG_PRECIO_KG_ATIPICO', 'BOOLEAN', 'Precio por kilo fuera de [Q1 - 3 RIC, Q3 + 3 RIC] en logaritmo; nulo si no se pudo evaluar'),
        ('NIVEL_REFERENCIA_PRECIO_UNIDAD', 'VARCHAR', 'Grupo de referencia del precio por unidad física (misma unidad): SUBPARTIDA o SA6'),
        ('RAZON_PRECIO_UNIDAD_VS_MEDIANA', 'FLOAT', 'Precio por unidad dividido por la mediana de su grupo'),
        ('FLAG_CANTIDAD_ATIPICA', 'BOOLEAN', 'Precio por unidad física atípico: delata cantidades imposibles; nulo si no se pudo evaluar'),
        ('FLAG_ATIPICO', 'BOOLEAN', 'VERDADERO si la línea tiene precio por kilo o cantidad atípicos'),
        ('FLAG_POSIBLE_ERROR_FOB', 'BOOLEAN', 'Precio por kilo y por unidad extremos a la vez: posible error de FOB o de varios campos; no se ajusta'),
        ('METODO_AJUSTE', 'VARCHAR', 'Peso desde la cantidad, peso desde el FOB, cantidad desde el peso o cantidad desde el FOB; nulo si no se ajustó'),
        ('PESO_NETO_KGS_AJUSTADO', 'DOUBLE', 'Peso reconstruido (desde la cantidad o desde el FOB) en exportaciones comerciales con precio por kilo 100 veces o más lejos de la mediana o peso 0; nulo si no se ajustó'),
        ('PESO_BRUTO_KGS_AJUSTADO', 'DOUBLE', 'Peso neto ajustado × mediana bruto/neto del grupo; nulo si no se ajustó'),
        ('CANTIDAD_UNIDADES_FISICAS_AJUSTADA', 'DOUBLE', 'Cantidad reconstruida (desde el peso o desde el FOB) en exportaciones comerciales con precio por unidad 100 veces o más lejos de la mediana'),
    ]:
        dic(H, col, tipo, d, R + ', atípicos y ajustes' if col != 'ES_DESTINO_ZONA_FRANCA' else R + ', correcciones')
    for col, d in [
        ('ANIO_MES, TRIMESTRE', 'Periodo en texto (AAAA-MM) y trimestre (AAAA-Tn)'),
        ('ID_DECLARACION', 'Formulario, o autorización de embarque (AE-) si falta, o el registro (R-)'),
        ('ES_VENTA_EXTERIOR', 'VERDADERO si no va a zona franca colombiana ni tiene destino Colombia'),
        ('DEPTO_ORIGEN_ASIGNADO', 'FALSO cuando el origen es 00 Departamentos varios'),
        ('ES_EXPORTACION_COMERCIAL', 'Modalidades 198 y 199 (exportación definitiva con valor comercial)'),
        ('PESO_NETO_KGS_ANALISIS, PESO_BRUTO_KGS_ANALISIS, CANTIDAD_UNIDADES_FISICAS_ANALISIS', 'Valor ajustado si existe; si no, el original. Usar para análisis de volumen'),
        ('PRECIO_USD_KG, PRECIO_USD_KG_ANALISIS, PRECIO_USD_UNIDAD_ANALISIS', 'Precio unitario con las magnitudes originales y con las de análisis'),
        ('RAZON_SOCIAL, VINCULO_ANTIOQUIA, EMPRESA_ANTIOQUENA, ES_EXPORTADOR_ANTIOQUENO, CAMARA_COMERCIO, CIIU_PRINCIPAL_RUES, SECTOR_EXPORTADOR_PRINCIPAL',
         'Atributos del exportador (dim_exportador_analitica); banderas de Antioquia en FALSO para personas naturales'),
        ('CIUDAD_DESTINATARIO_NORM', 'Ciudad del comprador normalizada de forma aproximada (map_ciudad_destinatario)'),
        ('CERTIFICADO_ORIGEN, FORMA_PAGO_DESC, REGIMEN_CAN_DESC, TIPO_USUARIO_DESC, LUGAR_SALIDA', 'Descripciones de los catálogos cat_*'),
    ]:
        dic(V, col, None, d, 'Vista')
    dic('vw_serie_mensual', 'FOB_MUSD_VENTA_EXTERIOR, FOB_MUSD_ORIGEN_ASIGNADO, PESO_NETO_MILES_T_ANALISIS', None,
        'Nuevas en la BD principal: FOB al exterior (sin zonas francas), FOB con departamento de origen asignado y peso neto de análisis '
        '(con los ajustes) en miles de toneladas. Las demás columnas son las mismas de la BD depurada', 'Capa analítica')
    for col, tipo, d in [
        ('FLAG_SECOP_VALOR_INVALIDO', 'BOOLEAN', 'El total SECOP superaba COP 100 billones y se dejó nulo'),
        ('SS_CIFRAS_RECIENTES', 'BOOLEAN', 'Año de corte de Supersociedades 2024 o 2025'),
        ('SS_FACTOR_IPC_A_DIC2025', 'DOUBLE', 'Factor de inflación (IPC dic-dic) desde el año de corte hasta diciembre de 2025'),
        ('SS_INGRESOS_BILLONES_COP_DIC2025', 'DOUBLE', 'Ingresos operacionales en billones de pesos de diciembre de 2025 (comparables entre empresas)'),
        ('SS_ACTIVOS_BILLONES_COP_DIC2025', 'DOUBLE', 'Activos totales en billones de pesos de diciembre de 2025'),
        ('SS_INTENSIDAD_EXPORTADORA_PCT', 'DOUBLE', 'FOB del año de corte × tasa DIAN del año / ingresos operacionales × 100 (solo cortes 2024 y 2025)'),
        ('N_RAZONES_SOCIALES_DIAN', 'BIGINT', 'Razones sociales distintas con que aparece en la DIAN en 2024-2026'),
        ('TIPO_CAMBIO_RAZON_SOCIAL', 'VARCHAR', 'Solo formato, cambió de forma jurídica, adoptó o dejó C.I. o BIC, entró en liquidación o cambió de nombre'),
        ('ES_COMERCIALIZADORA_INTERNACIONAL', 'BOOLEAN', 'La razón social DIAN o RUES incluye C.I. o Comercializadora Internacional'),
        ('ES_TRASLADO_DOMICILIO', 'BOOLEAN', 'Matrícula RUES constituida por traslado de domicilio desde otra cámara'),
        ('ANIO_MATRICULA', 'BIGINT', 'Año de la matrícula vigente (para traslados, el año del traslado)'),
        ('TRASLADO_EN_PERIODO', 'BOOLEAN', 'Traslado de domicilio desde enero de 2024'),
        ('MATRICULA_POSTERIOR_A_PRIMERA_EXPORTACION', 'BOOLEAN', 'La matrícula vigente es posterior a su primer mes exportador en la base'),
    ]:
        dic(E, col, tipo, d, R + ', directorio')
    for t, d in [('cat_* y catalogo_codigos', 'Un catálogo por dominio con llave CODIGO; catalogo_codigos es la vista que los une'),
                 ('map_ciudad_destinatario', 'Ciudad original + país → ciudad normalizada'), ('exportador_pais', 'FOB, participación y ranking de cada país en cada NIT'),
                 ('exportador_subpartida', 'FOB, participación y ranking de cada subpartida en cada NIT'),
                 ('panel_exportador_mes', 'Una fila por NIT y mes con exportaciones'),
                 ('ref_dane_publicaciones', 'Totales oficiales del DANE para el cuadre (incluye enero-septiembre de 2026)'),
                 ('vw_ventas_exterior', 'vw_exportaciones sin zonas francas ni destino Colombia'),
                 ('vw_exportaciones_origen_asignado', 'vw_exportaciones sin 00 Departamentos varios (análisis regional)'),
                 ('vw_validacion_dane', 'Base frente a los totales del DANE'),
                 ('vw_ciudad_comprador_por_completar', 'NIT con líneas cuya ciudad de comprador no es confiable'),
                 ('relaciones_llaves', 'Cada llave primaria y foránea: declarada o validada, con filas huérfanas'),
                 ('log_preparacion', 'Cada regla de la capa con filas y FOB afectados'), ('info_capa', 'Ficha de la capa')]:
        dic(t, '(objeto)', None, d, R)
    con.execute("CREATE TEMP TABLE _dic (TABLA VARCHAR, COLUMNA VARCHAR, TIPO VARCHAR, DESCRIPCION VARCHAR, ORIGEN_O_REGLA VARCHAR)")
    con.executemany("INSERT INTO _dic VALUES (?,?,?,?,?)", [(t, c) + v for (t, c), v in dicc.items()])
    crear('diccionario_datos', "SELECT * FROM _dic ORDER BY TABLA, COLUMNA", ['TABLA', 'COLUMNA'])
    con.execute("CREATE TEMP TABLE _info (CLAVE VARCHAR, VALOR VARCHAR)")
    con.executemany("INSERT INTO _info VALUES (?,?)", [
        ('Nombre', 'BD principal: capa analítica de la BD de exportaciones de Colombia (2024-01 a 2026-09), versión 2'),
        ('Fecha de construcción', datetime.date.today().isoformat()),
        ('Construida con', 'pipeline/p10_capa_analitica.py (duckdb ' + duckdb.__version__ + '); se arma desde parquet con crear_bd_analitica.py'),
        ('Origen', os.path.basename(ORIGEN) + ' (abierta en solo lectura, sin cambios)'),
        ('Parámetros de atípicos', f'K = {dec(K_IQR)} RIC en logaritmo; RIC mínimo {dec(IQR_MIN)}; mínimo {N_MIN} líneas comerciales por grupo'),
        ('Ajustes', f'Peso y cantidad ajustados con la mediana del grupo solo en exportaciones comerciales a {FACTOR_ERROR} veces o más de la mediana; el FOB nunca se modifica'),
        ('Llaves', f'{n_pk_total} primarias y {n_fk} foráneas declaradas; {n_fv} relaciones de hechos validadas (ver relaciones_llaves)'),
        ('Cómo empezar', 'vw_exportaciones · vw_ventas_exterior · vw_exportaciones_origen_asignado · panel_exportador_mes · dim_exportador_analitica'),
        ('Para volúmenes y precios', 'Usar las columnas _ANALISIS de vw_exportaciones, o filtrar WHERE NOT FLAG_ATIPICO'),
    ])
    crear('info_capa', "SELECT * FROM _info", ['CLAVE'])

    # ---------------------------------------------------------------- 10. validaciones
    o_n, o_f = q("SELECT count(*), sum(VALOR_FOB_USD) FROM dep.hechos_exportaciones")
    c_n, c_f = q("SELECT count(*), sum(VALOR_FOB_USD) FROM hechos_analitica")
    assert o_n == c_n and abs(o_f - c_f) < 1, 'Cambió el número de líneas o el FOB'
    assert q("SELECT count(*) FROM vw_exportaciones")[0] == c_n, 'La vista duplica o pierde líneas'
    assert q("SELECT count(*) FROM dim_exportador_analitica")[0] == q("SELECT count(*) FROM dep.dim_exportador")[0]
    assert abs(q("SELECT sum(FOB_USD) FROM panel_exportador_mes")[0] - q("SELECT sum(VALOR_FOB_USD) FROM hechos_analitica WHERE NIT_EXPORTADOR IS NOT NULL")[0]) < 1
    assert q("SELECT count(*) FROM vw_validacion_mincit WHERE abs(DIF_TOTAL_PCT) > 0.05")[0] == 0
    assert q("SELECT count(*) FROM vw_validacion_dane WHERE abs(DIF_PCT) > 0.05")[0] == 0
    assert q("SELECT count(*) FROM hechos_analitica WHERE PESO_NETO_KGS_AJUSTADO <= 0 OR CANTIDAD_UNIDADES_FISICAS_AJUSTADA <= 0")[0] == 0
    log('10. Validación', 'Mismas líneas y mismo FOB que la BD depurada; cuadre con MinCIT y DANE (incluido ene-sep 2026) dentro de 0,05 %', c_n, c_f,
        'Las aserciones del script fallan si algo de esto cambia')
    con.execute("CHECKPOINT")
    print(con.execute("SELECT PASO, ETAPA, FILAS_AFECTADAS, round(FOB_USD_AFECTADO/1e6,1) FOB_MUSD FROM log_preparacion").df().to_string())
    con.close()
    print('Listo:', DESTINO, round(os.path.getsize(DESTINO) / 2**20, 1), 'MB')
    return DESTINO


def exportar(bd, origen, out=C.OUT_BD_ANALITICA, docs=C.DOCS, limpios=C.LIMPIOS):
    """Exporta la BD principal a parquet (sin repetir los hechos de la depurada), su esquema y su documentación."""
    out, docs = pathlib.Path(out), pathlib.Path(docs)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.parquet"):
        f.unlink()
    con = duckdb.connect(str(bd), read_only=True)
    con.execute(f"ATTACH '{origen}' AS dep (READ_ONLY)")
    base = {c for c, in con.execute("SELECT column_name FROM duckdb_columns() WHERE database_name = 'dep' "
                                    "AND table_name = 'hechos_exportaciones'").fetchall()}
    cols = [c for c, in con.execute("SELECT column_name FROM duckdb_columns() WHERE database_name = current_database() "
                                    "AND table_name = 'hechos_analitica' ORDER BY column_index").fetchall()]
    con.execute("DETACH dep")
    complemento = ['ID_REGISTRO'] + [c for c in cols if c not in base]
    con.execute(f"COPY (SELECT {', '.join(complemento)} FROM hechos_analitica ORDER BY ID_REGISTRO) TO "
                f"'{(out / CBA.COMPLEMENTO).as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    tablas = con.execute("SELECT table_name, sql FROM duckdb_tables() WHERE database_name = current_database() "
                         "ORDER BY table_oid").fetchall()
    vistas = con.execute("SELECT view_name, sql FROM duckdb_views() WHERE NOT internal AND database_name = current_database() "
                         "ORDER BY view_oid").fetchall()
    for t, _ in tablas:
        if t != 'hechos_analitica':
            con.execute(f"COPY {t} TO '{(out / f'{t}.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    lineas = ["-- Esquema de la BD principal (capa analítica). Lo genera pipeline/p10_capa_analitica.py; no editar a mano.",
              "-- crear_bd_analitica.py lo usa para crear las tablas con sus llaves, cargarlas desde parquet y crear las vistas.", ""]
    for tipo, filas in (("tabla", tablas), ("vista", vistas)):
        for nombre, sql in filas:
            lineas += [f"-- @@ {tipo} {nombre}", sql.strip().rstrip(';') + ";", ""]
    (out / "esquema.sql").write_text("\n".join(lineas), encoding="utf-8")
    con.execute(f"COPY diccionario_datos TO '{(docs / 'diccionario_bd_analitica.csv').as_posix()}' (HEADER)")
    con.execute(f"COPY log_preparacion TO '{(docs / 'log_bd_analitica.csv').as_posix()}' (HEADER)")
    con.execute(f"COPY relaciones_llaves TO '{(docs / 'relaciones_llaves_bd_analitica.csv').as_posix()}' (HEADER)")
    con.execute(f"COPY (SELECT * FROM vw_ciudad_comprador_por_completar) TO "
                f"'{(pathlib.Path(limpios) / 'nit_ciudad_comprador_por_completar.csv').as_posix()}' (HEADER)")
    escribir_diccionario_md(con, docs / "diccionario_bd_analitica.md")
    con.close()
    return complemento


def escribir_diccionario_md(con, salida):
    """Diccionario legible de la BD principal, agrupado por tabla o vista."""
    orden = ['vw_exportaciones', 'hechos_analitica', 'dim_exportador_analitica', 'panel_exportador_mes', 'exportador_pais',
             'exportador_subpartida', 'dim_subpartida', 'dim_pais', 'dim_departamento', 'dim_municipio', 'map_ciudad_destinatario']
    prioridad = "CASE d.TABLA " + " ".join(f"WHEN '{t}' THEN {i}" for i, t in enumerate(orden)) + f" ELSE {len(orden)} END"
    filas = con.execute(f"""SELECT d.TABLA, d.COLUMNA, coalesce(d.TIPO, ''), coalesce(d.DESCRIPCION, ''), coalesce(d.ORIGEN_O_REGLA, '')
                            FROM diccionario_datos d LEFT JOIN duckdb_columns() c ON c.table_name = d.TABLA AND c.column_name = d.COLUMNA
                            ORDER BY {prioridad}, d.TABLA, coalesce(c.column_index, -1), d.COLUMNA""").fetchall()
    limpio = lambda s: str(s).replace("|", "/").replace("\n", " ")
    md = ["# Diccionario de la BD principal (capa analítica)", "",
          "> Se genera con el paso 10 (`pipeline/p10_capa_analitica.py`) a partir de la tabla `diccionario_datos` de la BD principal. "
          "Las columnas heredadas de la BD depurada conservan su descripción original; el detalle de cada regla está en "
          "[bd_principal_capa_analitica.md](bd_principal_capa_analitica.md). Empieza por `vw_exportaciones`, la vista con la que "
          "se trabaja; las columnas van en el orden de la tabla.", ""]
    actual = None
    for t, c, tipo, d, o in filas:
        if t != actual:
            md += ["", f"## {t}", "", "| Columna | Tipo | Descripción | Origen o regla |", "|---|---|---|---|"]
            actual = t
        md.append(f"| `{limpio(c)}` | {limpio(tipo)} | {limpio(d)} | {limpio(o)} |")
    pathlib.Path(salida).write_text("\n".join(md) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origen", default=str(C.BD_DEPURADA_DUCKDB), help="BD depurada (.duckdb); si no existe se arma desde parquet")
    ap.add_argument("--salida", default=str(C.BD_ANALITICA_DUCKDB), help="BD principal (.duckdb) a crear")
    ap.add_argument("--sin-exportar", action="store_true", help="solo arma el .duckdb local, sin reescribir parquet ni docs")
    a = ap.parse_args()
    origen = pathlib.Path(a.origen)
    if not origen.exists():
        crear_bd_depurada.construir(salida=origen)
    pathlib.Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    bd = construir(str(origen), str(a.salida))
    if not a.sin_exportar:
        cols = exportar(bd, origen)
        print(f"Parquet, esquema y documentación exportados ({len(cols) - 1} columnas nuevas de hechos en el complemento)")


if __name__ == "__main__":
    main()
