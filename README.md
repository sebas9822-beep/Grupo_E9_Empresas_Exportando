# Grupo E9 · Empresas exportando

Caso de uso de datos para **EstudIA (EAFIT)**: base actualizada de empresas que exportan desde Colombia, con foco en Antioquia, armada solo con fuentes oficiales abiertas.

Este repositorio une en un solo proceso las dos búsquedas del proyecto:

1. **Primera búsqueda:** DIAN, RUES, Supersociedades y DIVIPOLA. Da quién exporta, cuánto, qué, a dónde y dónde está domiciliada cada empresa.
2. **Segunda búsqueda:** MinCIT, MinAgricultura y SECOP II. Da el sector de cada exportación (minero-energético, agrícola o industria), el producto agrícola y si la empresa contrata con el Estado.

## Qué hay (cobertura enero 2024 – septiembre 2026)

| Producto | Detalle |
|---|---|
| `data/processed/exportaciones_nacional/` | **3.613.237 líneas** de declaración de todo el país (un parquet por mes, 99 columnas) |
| `data/processed/exportaciones_antioquia/` | **1,03 millones de líneas**: mercancía de origen Antioquia y exportadores antioqueños (un parquet por año) |
| `data/processed/directorio_exportadores_antioquenos.xlsx` / `.csv` | **3.195 empresas** antioqueñas (vínculo A: 2.875; B: 320), una fila por NIT. Trae FOB por año, sector, productos, países, cámara de comercio, CIIU, Supersociedades y SECOP II |
| `data/processed/directorio_exportadores_nacional.csv` | **13.305 exportadores** del país (personas jurídicas) |
| `data/processed/serie_mensual_antioquia.csv` | FOB y número de exportadores por mes |
| `data/processed/validacion_*.csv` | Comparación con MinCIT y MinAgricultura |
| `data/processed/cobertura.json` | Periodo cubierto, totales y fecha de proceso |

## Empezar sin correr nada

```python
import pandas as pd

# Antioquia completa: ~1,2 GB en memoria con dtype_backend="pyarrow"
ant = pd.read_parquet("data/processed/exportaciones_antioquia/", dtype_backend="pyarrow")

# Nacional: 99 columnas x 3,6 M filas no caben en un portátil común; carga solo las columnas que necesites
nac = pd.read_parquet("data/processed/exportaciones_nacional/", dtype_backend="pyarrow",
                      columns=["PERIODO", "NIT", "SUBPARTIDA_10D", "PAIS_DESTINO_NORM", "VALOR_FOB_USD",
                               "SECTOR_EXPORTACION", "ORIGEN_MERCANCIA_ANTIOQUIA", "NIT_EMPRESA_ANTIOQUENA"])

directorio = pd.read_csv("data/processed/directorio_exportadores_antioquenos.csv", dtype={"NIT": str})

# Empresas antioqueñas (definición estricta), sin exportaciones minero-energéticas
nme = ant[ant.NIT_EMPRESA_ANTIOQUENA & ~ant.ES_MINERO_ENERGETICO]
```

Con DuckDB puedes consultar la base nacional sin cargarla en memoria:

```python
import duckdb
duckdb.sql("""SELECT PAIS_DESTINO_NORM, round(sum(VALOR_FOB_USD)/1e6,1) AS fob_musd
              FROM 'data/processed/exportaciones_antioquia/*.parquet'
              WHERE ANIO = 2025 GROUP BY 1 ORDER BY 2 DESC LIMIT 10""").show()
```

## Estructura del repositorio

```
├── config.py                  rutas, periodo y reglas (cámaras de Antioquia, definición minero-energética)
├── run_pipeline.py            corre todo el proceso o un tramo
├── requirements.txt
├── pipeline/
│   ├── comun.py               descargas, API de datos.gov.co, dígito de verificación
│   ├── p01_descargar_dian.py              bases mensuales, directorio y documentación DIAN
│   ├── p02_descargar_datos_abiertos.py    RUES Antioquia, Supersociedades, DIVIPOLA, cámaras, MinCIT, MinAgricultura
│   ├── p03_convertir_dian.py              .zip/.xlsx mensuales → parquet
│   ├── p04_consolidar.py                  una sola tabla DuckDB + lista de NIT
│   ├── p05_descargar_por_nit.py           RUES nacional y SECOP II por NIT (incremental)
│   ├── p06_directorio.py                  directorio por empresa (une las dos búsquedas)
│   ├── p07_exportar.py                    productos finales, validaciones, cobertura
│   └── p08_excel.py                       Excel formateado
├── data/
│   ├── raw/          datos crudos (~1,5 GB, no se versionan; ver data/raw/README.md)
│   ├── interim/      intermedios regenerables (no se versionan)
│   └── processed/    productos finales (sí se versionan)
└── docs/
    ├── metodologia.md            definiciones, validación, problemas de calidad y limitaciones
    ├── fuentes.md                fuentes usadas y descartadas
    ├── diccionario_directorio.csv
    ├── diccionario_transaccional.csv
    └── referencias/              ficha técnica DIAN y correlativa de países
```

## Reproducir o actualizar

```bash
pip install -r requirements.txt
python run_pipeline.py                 # descarga todo y procesa (~30-40 min la primera vez)
```

**Si ya tienes los datos crudos**, por ejemplo en la carpeta *Datos descargados* de OneDrive, no hace falta volver a descargarlos:

```powershell
$env:EXPO_RAW_DIR = "C:\Users\...\EstudIA\fuente de datos\BD internacional\Datos descargados"
python run_pipeline.py --sin-descargas
```

**Cuando la DIAN publique un mes nuevo** (unos 35 días después del cierre), basta con correr `python run_pipeline.py`. El paso 1 baja solo los meses que faltan, el paso 3 convierte solo lo nuevo y el paso 5 consulta solo los NIT nuevos.

| Paso | Qué hace | Búsqueda |
|---|---|---|
| 1 | Descarga DIAN: bases mensuales, directorio anual, ficha técnica | 1 |
| 2 | Descarga datos.gov.co: RUES Antioquia, Supersociedades, DIVIPOLA, cámaras / MinCIT NME, MinAgricultura | 1 y 2 |
| 3 | Convierte los .xlsx mensuales a parquet | 1 |
| 4 | Consolida en DuckDB, normaliza subpartida y país, corrige el enmascaramiento de septiembre de 2024 | 1 |
| 5 | Consulta por NIT: RUES (domicilio) y SECOP II (contratos con el Estado) | 1 y 2 |
| 6 | Directorio: vínculo con Antioquia, sector, Supersociedades, SECOP | 1 y 2 |
| 7 | Exporta parquet, CSV, serie, validaciones y diccionario | — |
| 8 | Excel | — |

## Cómo se define "empresa antioqueña"

La dirección del exportador en la base DIAN muchas veces es la de la agencia de aduanas. Por eso **el domicilio se toma del RUES**: es la cámara de comercio de la matrícula principal.

- **A. Empresa antioqueña:** está matriculada en una cámara de Antioquia.
- **B.** Su domicilio está fuera, pero su mercancía viene principalmente de Antioquia.
- **C.** Solo parte de su mercancía es antioqueña.
- **D.** No tiene relación con Antioquia.

El detalle está en [docs/metodologia.md](docs/metodologia.md).

## Validación

| Comparación | Resultado |
|---|---|
| Total trimestral contra MinCIT (2024-T1 a 2026-T2) | Igual al millón de dólares; la mayor diferencia es 0,01 % |
| Serie no minero-energética contra MinCIT | Diferencia menor a 0,25 % por trimestre |
| Exportaciones agrícolas contra MinAgricultura | Igual a nivel nacional; Antioquia, diferencia menor a 1,1 % |
| Origen Antioquia 2025 contra Analdex | USD 10.786 M en ambos |
| Exportadores antioqueños 2024 (≥ USD 1.000) | 2.316 (A+B), frente a 2.395 de Analdex con datos de Legiscomex |

**Problema de calidad detectado:** en la base de septiembre de 2024 la DIAN ocultó la razón social de casi todas las empresas (USD 4.102 M). El pipeline las recupera por el NIT; el detalle está en la metodología.

## Fuentes y uso

Todas las fuentes son datos abiertos del Estado colombiano (Ley 1712 de 2014): DIAN, Confecámaras (RUES), Supersociedades, DANE, MinCIT, MinAgricultura y Colombia Compra Eficiente. La lista con enlaces está en [docs/fuentes.md](docs/fuentes.md). No se guardan datos personales: la DIAN anonimiza a las personas naturales, y del RUES y de SECOP II solo se toman datos de las empresas.
