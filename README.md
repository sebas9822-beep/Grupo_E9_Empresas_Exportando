# Empresas que exportan desde Antioquia

Equipo E9 · Análisis de Datos Básico · Estud-IA (Capa 2)

> **Fuente real y pública:** los datos salen de las bases de exportaciones de la DIAN y de otras fuentes oficiales abiertas. No son datos sintéticos. Lo que todavía falta confirmar en equipo está marcado como **PENDIENTE**.

## Ficha del proyecto · versión 1

### 1. Usuario y decisión
> ¿Quién usará el resultado (una persona o un área) y qué va a decidir con él?

**PENDIENTE:** confirmar en equipo quién es el usuario. Propuesta: un área que acompaña o atiende a empresas exportadoras de Antioquia (por ejemplo, una cámara de comercio o un área comercial). Con el resultado decide a qué empresas y sectores darles prioridad.

### 2. Pregunta principal
> Una sola pregunta que ayude a tomar esa decisión.

¿Qué empresas antioqueñas exportan, qué productos venden y a qué países, y cómo cambió eso entre 2024 y 2026?

**PENDIENTE:** ajustarla cuando se confirme el usuario (punto 1).

### 3. Fuente de datos
> Enlace o nombre de la fuente. ¿Es pública o es una muestra de práctica inventada (sintética)? Si es inventada, dilo aquí.

Pública. La base principal son las [bases estadísticas de exportaciones de la DIAN](https://www.dian.gov.co/dian/cifras/Paginas/Bases-Estadisticas-de-Comercio-Exterior-Importaciones-y-Exportaciones.aspx), un archivo por mes. Se completa con datos abiertos del RUES (cámaras de comercio), Supersociedades, SECOP II, MinAgricultura, MinCIT y DIVIPOLA. La lista con enlaces está en [docs/fuentes.md](docs/fuentes.md).

En `datos/originales/` hay una muestra de 1.000 filas de la DIAN; los archivos completos pesan 1,5 GB y no se suben.

### 4. Qué representa una fila
> Completa la frase: «Cada fila es…». ¿Qué campo distingue una fila de otra?

Cada fila de la tabla de hechos es **un ítem de una declaración de exportación**: una subpartida (producto) que un exportador despachó en una declaración. La distingue `ID_REGISTRO`, que se asignó en la limpieza, porque la DIAN no trae una llave única: formulario + serie a veces se repite y 1.690 líneas no tienen formulario.

En el directorio (`dim_exportador`), cada fila es una empresa y la distingue el `NIT`.

### 5. Periodo
> ¿Qué fechas cubren los datos?

De enero de 2024 a septiembre de 2026 (33 meses). El año 2026 está incompleto: la DIAN publica cada mes unos 35 días después del cierre.

### 6. Cuatro indicadores
> Nombre de cada indicador y, si ya puedes, cómo se calcula (qué se divide entre qué).

1. **Valor exportado (FOB)** = suma de `VALOR_FOB_USD`, en dólares.
2. **Empresas exportadoras** = número de NIT distintos que exportaron al menos USD 1.000 FOB en el año (el umbral que usa Analdex).
3. **Participación de Antioquia** = FOB de mercancía de origen Antioquia ÷ FOB nacional.
4. **Peso no minero-energético** = FOB sin petróleo, carbón, oro, ferroníquel ni demás minerales ÷ FOB total.

### 7. Fuera de alcance
> Lo que este proyecto NO va a responder.

- Exportación de **servicios** (software, consultoría, turismo): no pasa por aduana y no está en la DIAN.
- Rentabilidad, márgenes, empleo o ventas totales de las empresas.
- Las **personas naturales**: la DIAN no publica su documento, así que no entran al directorio.
- Importaciones y pronósticos.

## Comparaciones, riesgos y mapa de preguntas

### Dos comparaciones útiles
1. Por año: 2024, 2025 y 2026, comparando los mismos meses (enero a septiembre).
2. Por sector: minero-energético, agrícola e industria. También por vínculo de la empresa con Antioquia (A: domicilio en Antioquia; B: mercancía principalmente antioqueña).

### Tres riesgos de calidad
1. **La dirección del exportador en la DIAN suele ser la de su agencia de aduanas**: una sola dirección de Bogotá aparece en 1.183 NIT. Por eso el domicilio se toma del RUES (cámara de comercio).
2. **La DIAN cambia formatos entre archivos.** En septiembre de 2024 ocultó la razón social de 3.927 empresas, y en 2025 cambió los códigos de país. Cada regla quedó en la [bitácora](bitacora.md). Si la fuente falla o un mes viene mal, los totales se comparan con MinCIT, que cuadra trimestre a trimestre.
3. **Envíos que no salen del país**: USD 2.616 M van a zonas francas colombianas, y 2026 está incompleto. Se marcan con `ES_DESTINO_ZONA_FRANCA` y los años se comparan en los mismos meses.

### Mapa de preguntas
- **¿Qué pasó?** Cuánto exportaron las empresas antioqueñas y cuántas exportaron, por año y por sector.
- **¿Dónde o cuándo es distinto?** Por sector, producto, país de destino y subregión (cámara de comercio).
- **¿Qué recomendaría y con qué límites?** Qué empresas y sectores priorizar. Límites: solo bienes, sin rentabilidad y sin personas naturales.

## Cifra de control

- **Tabla de hechos:** 3.613.237 líneas por USD 142.059,8 M FOB. Por año: 2024 USD 49.556,5 M; 2025 USD 50.201,5 M; 2026 (enero a septiembre) USD 42.301,8 M. El total coincide con la cifra oficial de MinCIT en todos los trimestres; la mayor diferencia es 0,01 %.
- **Directorio:** 13.305 empresas. De ellas, 3.195 son exportadores antioqueños: 2.875 con domicilio en Antioquia (A) y 320 con mercancía principalmente antioqueña (B).
- **Personas naturales:** 16.714 líneas por USD 247,6 M. Empresas más personas naturales dan el total.
- **Muestra:** 1.000 filas, 995 de empresas y 5 de personas naturales.

Las consultas que dan estas cifras están en [consultas/](consultas/).

## Archivos del proyecto

| Archivo o carpeta | Qué contiene |
|---|---|
| [diccionario.md](diccionario.md) | Qué significa cada columna: muestra original, tabla de hechos y directorio |
| [bitacora.md](bitacora.md) | Decisiones y por qué, reglas de limpieza y uso de IA |
| `datos/originales/` | Muestra de 1.000 filas de la DIAN tal como se descargó (no se modifica) |
| `datos/limpios/` | BD depurada en parquet, directorio antioqueño (CSV y Excel), serie mensual y validaciones |
| `consultas/` | Consultas SQL comentadas, con su cifra de control (sesión 3) |
| `notebooks/` | Cuaderno de Colab: consultas sobre la muestra y sobre la BD depurada (sesiones 3 a 5) |
| `tablero/` | Capturas y enlace del tablero (sesión 6) |
| `docs/` | Metodología, fuentes, limpieza detallada y cómo correr el proceso completo |
| `pipeline/`, `run_pipeline.py`, `crear_bd_depurada.py`, `config.py`, `requirements.txt` | Código que descarga, une y limpia los datos (avanzado; ver [docs/pipeline.md](docs/pipeline.md)) |

## Cómo empezar

- **Sin instalar nada:** abre el cuaderno en Colab desde [notebooks/01_consultas.ipynb](https://colab.research.google.com/github/sebas9822-beep/Grupo_E9_Empresas_Exportando/blob/main/notebooks/01_consultas.ipynb).
- **En Excel:** descarga `datos/limpios/directorio_exportadores_antioquenos.xlsx`.
- **La BD completa en tu computador:** `pip install -r requirements.txt` y luego `python crear_bd_depurada.py`. Arma un archivo DuckDB de unos 270 MB en menos de un minuto. Empieza por la vista `vw_exportaciones`.

## Reglas del repositorio

- Es **público**: nada de datos personales (nombres, cédulas, teléfonos, correos, direcciones), contraseñas ni llaves. Por eso no se publican el nombre ni el domicilio del comprador en el exterior, que puede ser una persona, ni la dirección de las personas naturales.
- Lo que está en `datos/originales/` no se modifica: se guarda tal como se descargó.
- Lo que está en `datos/limpios/` se produce con código (`pipeline/` o `notebooks/`), nunca a mano.
- Cada commit dice en su mensaje **qué** se decidió y **por qué**.

---

Proyecto desarrollado en Estud-IA · Capa 2 · Análisis de Datos.
