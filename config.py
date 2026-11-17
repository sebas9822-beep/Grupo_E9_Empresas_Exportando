"""Configuración central del proyecto Grupo E9 · Empresas exportando.

Todas las rutas son relativas a la raíz del repositorio. Los datos crudos
pesan ~1,5 GB y no se versionan: por defecto se descargan en data/raw/, pero
si ya los tienes (por ejemplo en la carpeta "Datos descargados" de OneDrive)
puedes apuntar a ellos con la variable de entorno EXPO_RAW_DIR:

    Windows (PowerShell):  $env:EXPO_RAW_DIR = "C:\\...\\BD internacional\\Datos descargados"
    Linux / macOS:         export EXPO_RAW_DIR="/ruta/a/Datos descargados"

data/raw/ usa las mismas subcarpetas que esa carpeta, así que sirve tal cual.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = Path(os.environ.get("EXPO_RAW_DIR", DATA / "raw"))
INTERIM = DATA / "interim"          # intermedios regenerables (no se versionan)
PROCESSED = DATA / "processed"      # productos finales (sí se versionan)
DOCS = ROOT / "docs"

# Subcarpetas de datos crudos (idénticas a la carpeta "Datos descargados")
RAW_DIAN_MENSUAL = RAW / "01_DIAN_Exportaciones_mensuales"
RAW_DIAN_DOCS = RAW / "02_DIAN_Documentacion"
RAW_DANE = RAW / "03_DANE_EXPO_microdatos"
RAW_DATOSGOV = RAW / "04_datos_gov_co"
RAW_DIAN_DIRECTORIO = RAW / "06_DIAN_Directorio_Imp_Exp"
RAW_FUENTES_V2 = RAW / "07_fuentes_v2"

# Intermedios
INTERIM_MENSUAL = INTERIM / "mensual"
DUCKDB_PATH = INTERIM / "expo.duckdb"
NITS_PATH = INTERIM / "nits_exportadores.csv"

# Productos finales
OUT_NACIONAL = PROCESSED / "exportaciones_nacional"     # un parquet por mes
OUT_ANTIOQUIA = PROCESSED / "exportaciones_antioquia"   # un parquet por año
OUT_BD_DEPURADA = PROCESSED / "bd_depurada"            # BD única depurada (paso 9): parquet por tabla
BD_DEPURADA_DUCKDB = OUT_BD_DEPURADA / "BD_exportaciones_Colombia_depurada.duckdb"  # se arma localmente, no se versiona

# Periodo de análisis (el fin se detecta con lo que haya publicado la DIAN)
PERIODO_INICIO = "2024-01"
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# Fuentes
DIAN_MENSUAL_URL = "https://www.dian.gov.co/dian/cifras/Basesestadisticasexportaciones"
DIAN_DIRECTORIO_URL = "https://www.dian.gov.co/dian/cifras/DirectorioImpExpNvo"
DIAN_DOCS_URL = "https://www.dian.gov.co/dian/cifras/Documents"
DIAN_DOCS = ["Ficha-Tecnica-bases-estadisticas-de-Comercio-Exterior.pdf",
             "Ficha-Metodologica-Comercio-Exterior.pdf",
             "Correlativa-M-49-y-ALADIv2.xlsx"]
SOCRATA_URL = "https://www.datos.gov.co/resource"
DANE_EXPO_2025_URL = "https://microdatos.dane.gov.co/index.php/catalog/859/download/24765"

# Cámaras de comercio con jurisdicción en Antioquia (RUES)
CAMARAS_ANTIOQUIA = ("MEDELLIN PARA ANTIOQUIA", "ABURRA SUR", "ORIENTE ANTIOQUENO",
                     "MAGDALENA MEDIO", "URABA")
CODIGOS_CAMARAS_ANTIOQUIA = ("21", "44", "51", "52", "55")

# Definición minero-energética, calibrada contra la serie NME de MinCIT
# (diferencia trimestral < 0,25 % entre 2024-T1 y 2026-T2)
ME_CAPITULOS = ("26", "27")                                   # minerales, combustibles
ME_PARTIDAS = ("7103", "7106", "7108", "7110", "7112")        # piedras y metales preciosos
ME_SUBPARTIDAS6 = ("720260",)                                 # ferroníquel

UMBRAL_EXPORTADOR_USD = 1000       # umbral anual usado por Analdex para contar exportadores
MAX_NIT_DIRECCION_PROPIA = 5       # dirección DIAN compartida por más NIT = agencia de aduanas
