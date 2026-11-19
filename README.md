# Empresas que exportan desde Antioquia

Equipo E9 · Análisis de Datos Básico · Estud-IA (Capa 2- Sebastian Gaviria Lopez, Luis Gabriel Cespedes, Julio Cesar Yanez)

> **Fuente real y pública:** los datos salen de las bases de exportaciones de la DIAN y de otras fuentes oficiales abiertas. No son datos sintéticos.

> ### BD principal para trabajar: `BD_exportaciones_Colombia_analitica`
>
> **Esta es la base de datos a procesar.** Todo análisis, consulta, cuaderno o tablero parte de ella. Tiene las exportaciones de Colombia de enero de 2024 a septiembre de 2026 (3.613.237 líneas, USD 142.059,8 M FOB) ya depuradas, con llaves primarias y foráneas, catálogos completos, banderas de precios atípicos, pesos y cantidades corregidos, cifras de Supersociedades comparables, panel por empresa y vistas listas para usar. Cuadra con el DANE en 2024, 2025 y enero-septiembre de 2026 (diferencia máxima 0,009 %).
>
> ```bash
> pip install -r requirements.txt
> python crear_bd_analitica.py   # ~30 s → datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb
> ```
>
> Empieza por la vista `vw_exportaciones`. Qué contiene, cómo se organizó y con qué técnicas se depuró: **[docs/bd_principal_capa_analitica.md](docs/bd_principal_capa_analitica.md)**. Diccionario: [docs/diccionario_bd_analitica.md](docs/diccionario_bd_analitica.md).

## Ficha del proyecto · versión 1

### 1. Usuario y decisión
> ¿Quién usará el resultado (una persona o un área) y qué va a decidir con él?
Propuesta: Consultoras que acompañan o atienden a empresas exportadoras de Antioquia (Cámara de comercio,área comercial,ProColombia), incluso el resultado puede ser usado por las mismas empresas Antioqueñas exportadoras. Con el resultado las empresas exportadoras y consultoras identifican riesgos y oportunidades de diversificación comercial, lo que las llevan a decidir a qué empresas, sectores y mercados darles prioridad.

### 2. Pregunta principal
> Una sola pregunta que ayude a tomar esa decisión.
¿Qué porcentaje de las exportaciones de cada producto se concentra en sus tres principales países compradores?

### 3. Fuente de datos
> Enlace o nombre de la fuente. ¿Es pública o es una muestra de práctica inventada (sintética)? Si es inventada, dilo aquí.
Pública. La base principal son las [bases estadísticas de exportaciones de la DIAN](https://www.dian.gov.co/dian/cifras/Paginas/Bases-Estadisticas-de-Comercio-Exterior-Importaciones-y-Exportaciones.aspx), un archivo por mes. Se completa con datos abiertos del RUES (cámaras de comercio), Supersociedades, SECOP II, MinAgricultura, MinCIT,Procolombia y DIVIPOLA. La lista con enlaces está en [docs/fuentes.md](docs/fuentes.md).
En `datos/originales/` hay una muestra de 1.000 filas de la DIAN; los archivos completos pesan 1,5 GB y no se suben.

### 4. Qué representa una fila

RANKING_NACIONAL_FOB
RANKING_ANTIOQUIA_FOB 
RAZON_SOCIAL
EMPRESA_ANTIOQUENA
TIPO_EXPORTADOR
CLASE_EXPORTADOR
SECTOR_EXPORTADOR_PRINCIPAL
FOB_USD_2024, FOB_USD_2025, FOB_USD_TOTAL, FOB_USD_ORIGEN_ANTIOQUIA,
EXPORTADOR_2024_MIN_1000USD, EXPORTADOR_2025_MIN_1000USD
TOP3_PAISES_DESTINO
MODO_TRANSPORTE_PRINCIPAL

### 5. Periodo
> ¿Qué fechas cubren los datos?
De enero de 2021 a diciembre de 2025.

### 6. Cuatro indicadores
Qué mide y cómo se calcula:
- Participación de cada país en las exportaciones de cada producto (%).
- Concentración en los tres principales países compradores (%).
- Número de países compradores por producto.
- Evolución anual de la concentración de las exportaciones (%).

### 7. Fuera de alcance
Determinar por qué los países compran o dejan de comprar determinados productos, predecir exportaciones futuras o evaluar el impacto económico de perder un comprador. 

## Comparaciones, riesgos y mapa de preguntas

### Dos comparaciones útiles
1. Por año: Concentración de los principales productos desde 2021 hasta 2025, comparando los mismos meses (enero a diciembre).
2. Por producto: Calcular que porcentaje de las exportaciones de cada producto se concentra en sus tres principales destinos.

### Tres riesgos de calidad
1. **Clasificación de productos**: productos	Que un mismo producto aparezca con diferentes códigos o descripciones, generando errores en su agrupación.
2. **Datos incompletos o inconsistentes.**: Que existan registros sin país de destino, sin valor FOB o con información duplicada.
3. **Diferencias en los registros de exportación**: Que existan diferencias entre las fuentes o cambios en la forma de registrar los productos y países durante los años analizados.

### Mapa de preguntas
- **¿Qué pasó?** ¿Cómo se comportaron las exportaciones de los principales productos de Antioquia entre 2021 y 2025?, ¿Cuáles fueron los principales productos exportados?, ¿Cuáles fueron sus principales países compradores?, ¿Qué porcentaje de las exportaciones se concentró en los tres principales destinos?
- **¿Dónde o cuándo es distinto?** ¿Qué productos presentan mayores niveles de concentración y cómo ha cambiado esa situación durante el periodo analizado?, ¿Qué productos tienen mayor diversificación de destinos?, ¿En qué años aumentó o disminuyó la concentración?, ¿Qué productos experimentaron los cambios más importantes?.
- **¿Qué recomendaría y con qué límites?** ¿Qué productos deberían buscar nuevos mercados internacionales?, ¿Qué recomendaciones podrían plantearse a las empresas exportadoras y organismos de promoción comercial?
-  Límites: No se determinarán las causas exactas de la concentración, no se predecirán las exportaciones futuras, no se garantizará que nuevos mercados compren los productos, las recomendaciones se basarán en los patrones encontrados en los datos, no en estudios de demanda de cada país.

## Cifra de control

- **BD principal:** 3.613.237 líneas y USD 142.059,8 M FOB, iguales a la BD depurada. Frente al DANE: 2024 USD 49.556,5 M frente a 49.552,0 (0,009 %); 2025 USD 50.201,5 M frente a 50.199,9 (0,003 %); enero a septiembre de 2026 USD 42.301,8 M en ambos. 113.790 líneas con precio atípico (0,70 % del FOB), 5.742 pesos y 6.534 cantidades reconstruidos, 31 llaves primarias y 0 huérfanos.
- **Tabla de hechos:** 3.613.237 líneas por USD 142.059,8 M FOB. Por año: 2024 USD 49.556,5 M; 2025 USD 50.201,5 M; 2026 (enero a septiembre) USD 42.301,8 M. El total coincide con la cifra oficial de MinCIT en todos los trimestres; la mayor diferencia es 0,01 %.
- **Directorio:** 13.305 empresas. De ellas, 3.195 son exportadores antioqueños: 2.875 con domicilio en Antioquia (A) y 320 con mercancía principalmente antioqueña (B).
- **Personas naturales:** 16.714 líneas por USD 247,6 M. Empresas más personas naturales dan el total.
- **Muestra:** 1.000 filas, 995 de empresas y 5 de personas naturales.

Las consultas que dan estas cifras están en [consultas/](consultas/).

## Archivos del proyecto

| Archivo o carpeta | Qué contiene |
|---|---|
| **[docs/bd_principal_capa_analitica.md](docs/bd_principal_capa_analitica.md)** | **La BD principal:** qué contiene, cómo se organizó y qué técnicas de depuración se usaron |
| [docs/diccionario_bd_analitica.md](docs/diccionario_bd_analitica.md) | Qué significa cada columna de la BD principal |
| [diccionario.md](diccionario.md) | Qué significa cada columna: muestra original, tabla de hechos y directorio de la BD depurada |
| [bitacora.md](bitacora.md) | Decisiones y por qué, reglas de limpieza y uso de IA |
| `datos/originales/` | Muestra de 1.000 filas de la DIAN tal como se descargó (no se modifica) |
| `datos/limpios/bd_analitica/` | **BD principal** en parquet (sin repetir los hechos de la depurada) y su `esquema.sql` |
| `datos/limpios/` | BD depurada en parquet (insumo de la principal), directorio antioqueño (CSV y Excel), serie mensual, validaciones y NIT con ciudad del comprador por completar |
| `consultas/` | Consultas SQL comentadas, con su cifra de control (sesión 3) |
| [resolver/](resolver/) | Cómo se resolvió la concentración de las exportaciones de Antioquia por país y producto (2016-2025): paso a paso, consultas con su cifra de control y scripts para reproducirlo |
| `notebooks/` | Cuaderno de Colab: consultas sobre la muestra y sobre la BD depurada (sesiones 3 a 5) |
| `tablero/` | Capturas y enlace del tablero (sesión 6) |
| `docs/` | Metodología, fuentes, limpieza detallada y cómo correr el proceso completo |
| `crear_bd_analitica.py` | Arma la BD principal en un solo archivo DuckDB desde los parquet del repositorio |
| `pipeline/`, `run_pipeline.py`, `crear_bd_depurada.py`, `config.py`, `requirements.txt` | Código que descarga, une, limpia y prepara los datos: pasos 1 a 10 (avanzado; ver [docs/pipeline.md](docs/pipeline.md)) |

## Cómo empezar

- **La BD principal en tu computador (recomendado):** `pip install -r requirements.txt` y luego `python crear_bd_analitica.py`. Arma un archivo DuckDB de unos 375 MB en menos de un minuto. Empieza por la vista `vw_exportaciones`; para ventas al exterior, `vw_ventas_exterior`. Las consultas de control están en [consultas/07_bd_principal.sql](consultas/07_bd_principal.sql).
- **Sin instalar nada:** abre el cuaderno en Colab desde [notebooks/01_consultas.ipynb](https://colab.research.google.com/github/sebas9822-beep/Grupo_E9_Empresas_Exportando/blob/main/notebooks/01_consultas.ipynb). Hoy lee la BD depurada; sus consultas dan el mismo resultado sobre la principal (cambian dos nombres: `hechos_exportaciones` → `hechos_analitica` y `dim_exportador` → `dim_exportador_analitica`).
- **En Excel:** descarga `datos/limpios/directorio_exportadores_antioquenos.xlsx`.
- **Solo la BD depurada (insumo):** `python crear_bd_depurada.py` (~270 MB).

## Reglas del repositorio

- Es **público**: nada de datos personales (nombres, cédulas, teléfonos, correos, direcciones), contraseñas ni llaves. Por eso no se publican el nombre ni el domicilio del comprador en el exterior, que puede ser una persona, ni la dirección de las personas naturales.
- Lo que está en `datos/originales/` no se modifica: se guarda tal como se descargó.
- Lo que está en `datos/limpios/` se produce con código (`pipeline/` o `notebooks/`), nunca a mano.
- Cada commit dice en su mensaje **qué** se decidió y **por qué**.

---

En la carpeta resolver esta el problema planteado, la respuesta y como se resolvio

Proyecto desarrollado en Estud-IA · Capa 2 · Análisis de Datos.
