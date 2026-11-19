# Cómo se construyen los datos (proceso completo)

Esta parte es avanzada. Para analizar no hace falta correr nada: los datos limpios ya están en `datos/limpios/` y la **BD principal** se arma con `python crear_bd_analitica.py` ([bd_principal_capa_analitica.md](bd_principal_capa_analitica.md)). Este documento explica cómo se producen, para actualizarlos cuando la DIAN publique un mes nuevo.

## Estructura del repositorio

```
├── README.md                  ficha del proyecto (plantilla del curso)
├── bitacora.md                decisiones, limpieza y uso de IA
├── diccionario.md             qué significa cada columna (se genera en el paso 9)
├── datos/
│   ├── originales/   muestra de 1.000 filas de la DIAN; los completos (~1,5 GB) no se suben
│   ├── intermedios/  todo lo regenerable, incluidos los productos de los pasos 7 y 8 (no se sube)
│   └── limpios/      BD principal (bd_analitica/) y BD depurada (bd_depurada/) en parquet, y copias en CSV y Excel (sí se sube)
├── consultas/                 consultas SQL con su cifra de control
├── notebooks/                 cuaderno de Colab
├── tablero/                   tablero (sesión 6)
├── config.py                  rutas, periodo y reglas (cámaras de Antioquia, definición minero-energética)
├── run_pipeline.py            corre todo el proceso o un tramo
├── crear_bd_analitica.py      arma la BD PRINCIPAL (.duckdb) desde datos/limpios/bd_analitica/ y bd_depurada/
├── crear_bd_depurada.py       arma el .duckdb de la depurada desde datos/limpios/bd_depurada/
├── requirements.txt
├── pipeline/
│   ├── comun.py                           descargas, API de datos.gov.co, dígito de verificación
│   ├── p01_descargar_dian.py              bases mensuales, directorio y documentación DIAN
│   ├── p02_descargar_datos_abiertos.py    RUES Antioquia, Supersociedades, DIVIPOLA, cámaras, MinCIT, MinAgricultura
│   ├── p03_convertir_dian.py              .zip/.xlsx mensuales → parquet
│   ├── p04_consolidar.py                  una sola tabla DuckDB + lista de NIT
│   ├── p05_descargar_por_nit.py           RUES nacional y SECOP II por NIT (incremental)
│   ├── p06_directorio.py                  directorio por empresa (une las dos búsquedas)
│   ├── p07_exportar.py                    líneas y directorio en parquet/CSV (intermedios)
│   ├── p08_excel.py                       Excel de los productos intermedios
│   ├── p09_bd_depurada.py                 BD única depurada: limpieza, modelo estrella, validación
│   ├── p10_capa_analitica.py              BD principal: llaves, catálogos, atípicos, ajustes, panel y vistas
│   ├── diccionario_bd_depurada.py         descripción de cada columna de la BD depurada
│   └── diccionario_md.py                  escribe diccionario.md con el formato de la plantilla
└── docs/
    ├── pipeline.md               este documento
    ├── metodologia.md            definiciones, validación, problemas de calidad y limitaciones
    ├── fuentes.md                fuentes usadas y descartadas
    ├── bd_principal_capa_analitica.md  la BD principal: proceso, técnicas de depuración y decisiones
    ├── diccionario_bd_analitica.md/.csv, log_bd_analitica.csv, relaciones_llaves_bd_analitica.csv
    ├── limpieza_bd_depurada.md   qué se limpió en la BD depurada, por qué y con qué impacto
    ├── diccionario_bd_depurada.csv, log_bd_depurada.csv
    ├── diccionario_directorio.csv, diccionario_transaccional.csv
    └── referencias/              ficha técnica DIAN y correlativa de países
```

## Reproducir o actualizar

```bash
pip install -r requirements.txt
python run_pipeline.py                 # descarga todo y procesa (~30-40 min la primera vez)
```

Si ya tienes los datos completos, por ejemplo en la carpeta *Datos descargados* de OneDrive, no hace falta volver a descargarlos:

```powershell
$env:EXPO_RAW_DIR = "C:\Users\...\EstudIA\fuente de datos\BD internacional\Datos descargados"
python run_pipeline.py --sin-descargas
```

Cuando la DIAN publique un mes nuevo, unos 35 días después del cierre, basta con correr `python run_pipeline.py`. El paso 1 baja solo los meses que faltan, el paso 3 convierte solo lo nuevo y el paso 5 consulta solo los NIT nuevos. Al final, el paso 9 regenera la depurada y `diccionario.md`, y el paso 10 regenera la BD principal, su diccionario y su log. Después hay que actualizar a mano las cifras de control de la ficha y de `consultas/`.

| Paso | Qué hace | Deja en |
|---|---|---|
| 1 | Descarga DIAN: bases mensuales, directorio anual, ficha técnica | `datos/originales/` |
| 2 | Descarga datos.gov.co: RUES Antioquia, Supersociedades, DIVIPOLA, cámaras, MinCIT NME, MinAgricultura | `datos/originales/` |
| 3 | Convierte los .xlsx mensuales a parquet | `datos/intermedios/` |
| 4 | Consolida en DuckDB, normaliza subpartida y país, corrige el enmascaramiento de septiembre de 2024 | `datos/intermedios/` |
| 5 | Consulta por NIT: RUES (domicilio) y SECOP II (contratos con el Estado) | `datos/originales/` |
| 6 | Directorio: vínculo con Antioquia, sector, Supersociedades, SECOP | `datos/intermedios/` |
| 7 | Líneas y directorio en parquet/CSV, serie y validaciones | `datos/intermedios/productos_paso7/` |
| 8 | Excel de esos productos | `datos/intermedios/productos_paso7/` |
| 9 | BD única depurada, archivos simples y `diccionario.md` | `datos/limpios/` |
| 10 | **BD principal**: capa analítica sobre la depurada (llaves, catálogos, atípicos, ajustes, Supersociedades comparable, panel y vistas) | `datos/limpios/bd_analitica/` y `docs/` |

## Cómo se define "empresa antioqueña"

La dirección del exportador en la base DIAN muchas veces es la de la agencia de aduanas. Por eso **el domicilio se toma del RUES**: es la cámara de comercio de la matrícula principal.

- **A. Empresa antioqueña:** está matriculada en una cámara de Antioquia.
- **B.** Su domicilio está fuera, pero su mercancía viene principalmente de Antioquia.
- **C.** Solo parte de su mercancía es antioqueña.
- **D.** No tiene relación con Antioquia.

El detalle está en [metodologia.md](metodologia.md).

## Validación

| Comparación | Resultado |
|---|---|
| Total trimestral contra MinCIT (2024-T1 a 2026-T2) | Igual al millón de dólares; la mayor diferencia es 0,01 % |
| Serie no minero-energética contra MinCIT | Diferencia menor a 0,25 % por trimestre |
| Exportaciones agrícolas contra MinAgricultura | Igual a nivel nacional; Antioquia, diferencia menor a 1,1 % |
| Origen Antioquia 2025 contra Analdex | USD 10.786 M en ambos |
| Exportadores antioqueños 2024 (≥ USD 1.000) | 2.316 (A+B), frente a 2.395 de Analdex con datos de Legiscomex |

## Fuentes y datos personales

Todas las fuentes son datos abiertos del Estado colombiano (Ley 1712 de 2014): DIAN, Confecámaras (RUES), Supersociedades, DANE, MinCIT, MinAgricultura y Colombia Compra Eficiente. La lista con enlaces está en [fuentes.md](fuentes.md).

Lo que se publica en GitHub no tiene datos personales. La DIAN anonimiza a las personas naturales; del RUES y de SECOP II solo se toman datos de empresas. Además, en la BD depurada se quitan el nombre y el domicilio del comprador en el exterior, que puede ser una persona. La BD principal solo agrega cifras y atributos de empresas.
