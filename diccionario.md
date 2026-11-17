# Diccionario de datos

> Qué significa cada columna de la BD depurada, para que otra persona la entienda sin preguntarnos. Se genera con el paso 9 (`pipeline/diccionario_md.py`): el tipo, los valores válidos y el porcentaje de vacíos salen de los datos.

Contenido: [1. Muestra original](#1-muestra-original) · [2. hechos_exportaciones](#2-hechos_exportaciones) · [3. dim_exportador](#3-dim_exportador) · [4. Otras tablas](#4-otras-tablas)

## 1. Muestra original

| Atributo | Valor |
|:---|:---|
| **Archivo** | `datos/originales/muestra_dian_exportaciones_2026_09.csv` |
| **Fuente y fecha de descarga** | DIAN, bases estadísticas de exportaciones, archivo `09_Exportaciones_2026_Septiembre.zip`, descargado en noviembre de 2026 |
| **Cada fila es** | un ítem (serie) de una declaración de exportación, tal como lo publica la DIAN |
| **Filas en la muestra** | 1.000 (las primeras del archivo de septiembre de 2026, que tiene 115.049) |
| **Campo que identifica cada fila (clave)** | no hay uno solo; `NUMERO_FORMULARIO` + `NUMERO_SERIE` casi siempre, pero se repite en algunas líneas |

Trae 70 de las 72 columnas de la DIAN. Se omitieron `RAZON_SOCIAL_DESTINATARIO` y `DOMICILIO_DESTINATARIO` porque pueden ser el nombre y la dirección de una persona, y `DIREC_EXPORTADOR` va vacía en las líneas de personas naturales. La descripción de las 72 columnas originales está en [docs/diccionario_transaccional.csv](docs/diccionario_transaccional.csv) y en la ficha técnica de la DIAN ([docs/referencias/](docs/referencias/)). Abajo se describen las columnas limpias, que son las que se usan para analizar.

## 2. hechos_exportaciones

| Atributo | Valor |
|:---|:---|
| **Archivo** | `datos/limpios/bd_depurada/hechos_exportaciones/` (un parquet por mes) |
| **Fuente y fecha de descarga** | DIAN (descargada en noviembre de 2026) más RUES, Supersociedades, SECOP II, MinAgricultura y MinCIT; procesada con el paso 9. Cubre 2024-01 a 2026-09 |
| **Cada fila es** | un ítem (serie) de una declaración de exportación DIAN: una subpartida exportada por un exportador en una declaración |
| **Filas** | 3.613.237 |
| **Campo que identifica cada fila (clave)** | `ID_REGISTRO` (la DIAN no trae una llave única: formulario + serie se repite y 1.690 líneas no tienen formulario) |

### Columnas

| # | Columna | Qué significa | Origen | Tipo | Unidad o formato | Valores válidos | Si está vacía, significa |
|---:|:---|:---|:---|:---:|:---|:---|:---|
| 1 | `ID_REGISTRO` | Llave única del registro (asignada en la depuración; la DIAN no trae una llave única) | Calculado | número | — | de 1 a 3.613.237 | no hay vacíos |
| 2 | `PERIODO` | Mes de la exportación (primer día del mes) | DIAN | fecha | AAAA-MM-DD (primer día del mes) | de 2024-01-01 a 2026-09-01 | no hay vacíos |
| 3 | `ANIO` | Año de la exportación | DIAN | número | — | de 2024 a 2026 | no hay vacíos |
| 4 | `MES` | Mes de la exportación (1-12) | DIAN | número | — | de 1 a 12 | no hay vacíos |
| 5 | `FECHA_DECLARACION` | Fecha de la declaración de exportación | DIAN FECHA_DECLARACION_EXPORTACION (AAAAMMDD → fecha) | fecha | AAAA-MM-DD | de 2024-01-01 a 2026-09-30 | no hay vacíos |
| 6 | `NUMERO_FORMULARIO` | Número de la declaración de exportación (DEX). NULL en las exportaciones sin formulario (sobre todo hidrocarburos) | DIAN ("0" → NULL) | texto | texto libre | 1.150.878 valores distintos | la línea no tiene número de declaración (sobre todo hidrocarburos de Ecopetrol, Reficar o Frontera); es legítima (0,0 % de las filas) |
| 7 | `NUMERO_SERIE` | Ítem o serie dentro de la declaración | DIAN | número | — | de 0 a 552 | no hay vacíos |
| 8 | `TIPO_DESPACHO` | Inicial / Corrección / Modificación. La base DIAN solo trae la versión vigente de cada declaración | DIAN (ortografía corregida) | texto | texto libre | «Inicial»; «Corrección»; «Modificación» | no hay vacíos |
| 9 | `TIPO_DATOS` | Definitivos al embarque / Definitivos después del embarque | DIAN (ortografía corregida) | texto | texto libre | «Definitivos al embarque»; «Definitivos después del embarque» | no hay vacíos |
| 10 | `TIPO_EMBARQUE` | Único / Fraccionado / Global con cargues parciales | DIAN (se usa la descripción; el código no era 1:1 con ella) | texto | texto libre | «Único»; «Fraccionado»; «Global con cargues parciales» | no hay vacíos |
| 11 | `NUM_DECLARACION_ANTERIOR` | Declaración que la corrección o modificación reemplaza | DIAN ("0" → NULL) | texto | texto libre | 242.309 valores distintos | es una declaración inicial (no corrige a otra) (90,1 % de las filas) |
| 12 | `PERIODO_DECLARACION_ANTERIOR` | Mes de la declaración anterior | DIAN (AAAAMM → fecha) | fecha | AAAA-MM-DD (primer día del mes) | de 2020-04-01 a 2026-09-01 | es una declaración inicial (no corrige a otra) (90,1 % de las filas) |
| 13 | `NUM_DECLARACION_PRECEDENTE` | Declaración precedente (p. ej. importación temporal que se reexporta) | DIAN ("0" → NULL) | texto | texto libre | 17.258 valores distintos | no hay declaración precedente (no viene de una importación temporal) (99,3 % de las filas) |
| 14 | `PERIODO_DECLARACION_PRECEDENTE` | Mes de la declaración precedente | DIAN (AAAAMM → fecha) | fecha | AAAA-MM-DD (primer día del mes) | de 2006-10-01 a 2026-09-01 | no hay declaración precedente (99,6 % de las filas) |
| 15 | `COD_MODALIDAD_PRECEDENTE` | Modalidad de la declaración precedente | DIAN | texto | código | 85 valores distintos | no hay declaración precedente (98,6 % de las filas) |
| 16 | `NUM_AUTORIZACION_EMBARQUE` | Número de la solicitud de autorización de embarque | DIAN NUM_SOLICITUD_AUTO_EMBARQUE | texto | texto libre | 1.216.397 valores distintos | la fuente no trae el dato (0,0 % de las filas) |
| 17 | `PERIODO_AUTORIZACION_EMBARQUE` | Mes de la solicitud de autorización de embarque (562 registros traen meses anteriores a 2023) | DIAN (AAAAMM → fecha) | fecha | AAAA-MM-DD (primer día del mes) | de 2008-11-01 a 2026-09-01 | no hay vacíos |
| 18 | `NIT_EXPORTADOR` | NIT del exportador sin dígito de verificación ni ceros a la izquierda. NULL = persona natural (la DIAN oculta su documento). Llave hacia dim_exportador | DIAN | texto | número de NIT sin dígito de verificación ni ceros a la izquierda | 9.622 valores distintos; cada uno existe en `dim_exportador` | el exportador es una persona natural: la DIAN no publica su documento (0,5 % de las filas) |
| 19 | `TIPO_IDENTIFICACION` | Código del tipo de documento (1 persona natural, 2 NIT). Ver catalogo_codigos | DIAN TIPO_IDENT | texto | código | «2»; «1» | no hay vacíos |
| 20 | `ES_PERSONA_NATURAL` | VERDADERO si el exportador no tiene NIT publicado (la DIAN anonimiza a las personas naturales). Se define por el NIT y no por la razón social, que falla en sep-2024 | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (16.714) o FALSO (3.596.523) | no hay vacíos |
| 21 | `FLAG_RAZON_SOCIAL_ENMASCARADA` | VERDADERO si la DIAN publicó "PERSONA NATURAL" o dejó vacía la razón social aunque la línea trae NIT de empresa (sep-2024). La línea se atribuye a la empresa por el NIT | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (107.212) o FALSO (3.506.025) | no hay vacíos |
| 22 | `CLASE_EXPORTADOR` | Clase declarada: 1 economía mixta, 2 privada, 3 pública. Ver catalogo_codigos | DIAN | texto | código | «2»; «3»; «1» | no hay vacíos |
| 23 | `TIPO_USUARIO` | Código DIAN del tipo de usuario aduanero (sin descripción en la fuente; 36 = 99,9 % de los registros) | DIAN | texto | código | «36»; «22»; «53»; «26»; «55»; «38»; «56»; «7»; «4»; «1» | no hay vacíos |
| 24 | `DIRECCION_DECLARADA` | Dirección del exportador declarada a la DIAN. OJO: muchas veces es la de la agencia de aduanas. Vacía para personas naturales (dato personal) | DIAN DIREC_EXPORTADOR (limpia) | texto | texto libre | 989 valores distintos | persona natural (no se publica por ser dato personal) o la fuente no la trae (0,5 % de las filas) |
| 25 | `COD_MPIO_DIRECCION_DECLARADA` | Municipio DIVIPOLA (5 dígitos) de la dirección declarada. Llave hacia dim_municipio | DIAN COD_DPTO_EXPORTADOR (en realidad es el municipio) | texto | DIVIPOLA de 5 dígitos | 110 valores distintos; cada uno existe en `dim_municipio` | la DIAN no trae un código de municipio válido (0,0 % de las filas) |
| 26 | `DIRECCION_DECLARADA_EN_ANTIOQUIA` | VERDADERO si la dirección declarada está en Antioquia | Calculado (paso 4) | verdadero / falso | VERDADERO / FALSO | VERDADERO (509.234) o FALSO (3.104.003) | no hay vacíos |
| 27 | `NIT_DECLARANTE` | NIT de la agencia de aduanas o declarante. Llave hacia dim_declarante | DIAN | texto | número de NIT sin dígito de verificación ni ceros a la izquierda | 745 valores distintos; cada uno existe en `dim_declarante` | el declarante es una persona natural (la DIAN oculta su NIT) o la fuente no lo trae (0,1 % de las filas) |
| 28 | `CIUDAD_DESTINATARIO` | Ciudad del destinatario, en mayúsculas. Su razón social y su domicilio no se publican porque pueden ser de una persona | DIAN (limpia, entidades HTML decodificadas) | texto | texto libre | 17.441 valores distintos | la fuente no trae la ciudad del comprador (0,0 % de las filas) |
| 29 | `COD_PAIS_DESTINO` | País destino final ISO 3166 alfa-3; "XCF" = zona franca colombiana. Llave hacia dim_pais | DIAN COD_PAIS_DESTINO_ALF (zonas francas corregidas) | texto | ISO 3166 alfa-3 (XCF = zona franca, ND = no declarado) | 227 valores distintos; cada uno existe en `dim_pais` | no hay vacíos |
| 30 | `ES_DESTINO_ZONA_FRANCA` | VERDADERO si la mercancía va a una zona franca en Colombia (no sale del país) | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (38.520) o FALSO (3.574.712) | la fuente no trae el dato (0,0 % de las filas) |
| 31 | `COD_ZONA_FRANCA_DESTINO` | Código de la zona franca de destino. Llave hacia dim_zona_franca | DIAN COD_PAIS_DESTINO_NUM | texto | código | 33 valores distintos; cada uno existe en `dim_zona_franca` | el destino no es una zona franca (98,9 % de las filas) |
| 32 | `OFICINA` | Código de la oficina DIAN (sin descripción en la fuente) | DIAN | texto | código | «99»; «3»; «6»; «11»; «35»; «2»; «5»; «19»; «37» | no hay vacíos |
| 33 | `COD_ADUANA_DESPACHO` | Aduana donde se presentó la declaración. Llave hacia dim_aduana | DIAN (2 dígitos) | texto | código DIAN de 2 dígitos | 24 valores distintos; cada uno existe en `dim_aduana` | no hay vacíos |
| 34 | `COD_ADUANA_SALIDA` | Aduana por donde salió la mercancía. Llave hacia dim_aduana | DIAN (2 dígitos) | texto | código DIAN de 2 dígitos | 23 valores distintos; cada uno existe en `dim_aduana` | no hay vacíos |
| 35 | `COD_LUGAR_SALIDA` | Puerto, aeropuerto o paso de frontera de salida (código alfabético) | DIAN COD_LUG_SALIDA_ALF | texto | código | 24 valores distintos | no hay vacíos |
| 36 | `COD_DEPTO_PROCEDENCIA` | Departamento DIVIPOLA desde donde se despachó la mercancía. Llave hacia dim_departamento | DIAN COD_REGION_PROCEDENCIA | texto | DIVIPOLA de 2 dígitos (00 = departamentos varios) | 33 valores distintos; cada uno existe en `dim_departamento` | no hay vacíos |
| 37 | `COD_DEPTO_ORIGEN` | Departamento DIVIPOLA donde se produjo la mercancía ("00" = departamentos varios). Llave hacia dim_departamento | DIAN COD_REGION_ORIGEN | texto | DIVIPOLA de 2 dígitos (00 = departamentos varios) | 35 valores distintos; cada uno existe en `dim_departamento` | no hay vacíos |
| 38 | `ORIGEN_MERCANCIA_ANTIOQUIA` | VERDADERO si la mercancía es de origen Antioquia (COD_DEPTO_ORIGEN = 05) | Calculado (paso 4) | verdadero / falso | VERDADERO / FALSO | VERDADERO (924.426) o FALSO (2.688.811) | no hay vacíos |
| 39 | `COD_MODO_TRANSPORTE` | Modo de transporte. Ver catalogo_codigos (MODO_TRANSPORTE) | DIAN | texto | código | «4»; «1»; «3»; «7»; «8» | no hay vacíos |
| 40 | `COD_PAIS_BANDERA` | País de la bandera del medio de transporte, ISO alfa-3 ("ND" = no declarado). Llave hacia dim_pais | DIAN (2024 alfa-2 convertido a alfa-3) | texto | ISO 3166 alfa-3 (XCF = zona franca, ND = no declarado) | 146 valores distintos; cada uno existe en `dim_pais` | no hay vacíos |
| 41 | `COD_MODALIDAD_EXPORTACION` | Modalidad de exportación (3 dígitos). Ver catalogo_codigos | DIAN (ceros a la izquierda homogéneos) | texto | código | «198»; «199»; «104»; «002»; «201»; «107»; «004»; «401»; «310»; «402»; «403» | no hay vacíos |
| 42 | `COD_REGIMEN_CAN` | Código de régimen Comunidad Andina (sin descripción en la fuente) | DIAN | texto | código | «1»; «4»; «5»; «3» | no hay vacíos |
| 43 | `FORMA_PAGO` | Código de forma de pago (sin descripción en la fuente) | DIAN | texto | código | «1»; «2» | no hay vacíos |
| 44 | `TIPO_CERTIFICADO_ORIGEN` | Código del tipo de certificado de origen (sin descripción en la fuente) | DIAN | texto | código | «8»; «1»; «2»; «5»; «6»; «3»; «4»; «7» | no hay vacíos |
| 45 | `SISTEMAS_ESPECIALES` | VERDADERO si la operación usa Sistemas Especiales de Importación-Exportación (Plan Vallejo) | DIAN (SI/NO → booleano) | verdadero / falso | VERDADERO / FALSO | VERDADERO (1.208.347) o FALSO (2.404.890) | no hay vacíos |
| 46 | `EXPORTACION_EN_TRANSITO` | VERDADERO si es exportación en tránsito | DIAN (SI/NO → booleano) | verdadero / falso | VERDADERO / FALSO | VERDADERO (141.765) o FALSO (3.471.472) | no hay vacíos |
| 47 | `COD_MONEDA_TRANSACCION` | Moneda de la transacción (ISO 4217) | DIAN | texto | código | 37 valores distintos | no hay vacíos |
| 48 | `SUBPARTIDA` | Subpartida arancelaria a 10 dígitos con cero inicial. Llave hacia dim_subpartida | DIAN | texto | 10 dígitos con cero inicial | 6.620 valores distintos; cada uno existe en `dim_subpartida` | no hay vacíos |
| 49 | `COD_UNIDAD_FISICA` | Unidad de la cantidad física. Ver catalogo_codigos (UNIDAD_FISICA) | DIAN COD_UNIDAD_FISICA_ALF | texto | código | «U»; «KG»; «M2»; «M3»; «L»; «2U»; «MIL»; «C/T»; «KWH»; «CM3» | no hay vacíos |
| 50 | `CANTIDAD_UNIDADES_FISICAS` | Cantidad en la unidad física declarada | DIAN | número | — | de 0,01 a 3.924.109.000,00 | no hay vacíos |
| 51 | `PESO_BRUTO_KGS` | Peso bruto en kilogramos | DIAN | número | kilogramos | de 0,00 a 300.000.000,00 | no hay vacíos |
| 52 | `PESO_NETO_KGS` | Peso neto en kilogramos | DIAN | número | kilogramos | de 0,00 a 300.000.000,00 | no hay vacíos |
| 53 | `VALOR_FOB_USD` | Valor FOB en dólares (medida principal) | DIAN | número | dólares (USD) | de 0,01 a 138.472.440,86 | no hay vacíos |
| 54 | `VALOR_FOB_COP` | Valor FOB en pesos colombianos | DIAN VALOR_FOB_PESOS | número | pesos colombianos | de 30,72 a 514.107.071.810,92 | no hay vacíos |
| 55 | `VALOR_AGREGADO_NACIONAL_USD` | Valor agregado nacional de la serie en dólares | DIAN VLR_SERIE_AGREGADO_NAL_USD | número | dólares (USD) | de 0,00 a 20.448.388,65 | no hay vacíos |
| 56 | `VALOR_FLETES_USD` | Fletes de la serie en dólares | DIAN VALOR_SERIE_FLETES_USD | número | dólares (USD) | de 0,00 a 20.889.155,00 | no hay vacíos |
| 57 | `VALOR_SEGUROS_USD` | Seguros de la serie en dólares | DIAN VALOR_SERIE_SEGUROS_USD | número | dólares (USD) | de 0,00 a 16.490.670,00 | no hay vacíos |
| 58 | `VALOR_OTROS_GASTOS_USD` | Otros gastos de la serie en dólares | DIAN VLR_SERIE_OTROS_GASTOS_USD | número | dólares (USD) | de 0,00 a 5.418.363,00 | no hay vacíos |
| 59 | `FLAG_PESO_CERO` | VERDADERO si el peso neto o bruto viene en cero (dato a revisar) | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (33) o FALSO (3.613.204) | no hay vacíos |
| 60 | `FLAG_REGISTRO_IDENTICO` | VERDADERO en 10 registros idénticos en todo a otro (sin número de formulario). Se conservan porque las cifras oficiales los incluyen; para excluirlos: WHERE NOT FLAG_REGISTRO_IDENTICO | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (10) o FALSO (3.613.227) | no hay vacíos |
| 61 | `ARCHIVO_FUENTE` | Archivo mensual DIAN del que proviene el registro | Trazabilidad | texto | texto libre | 35 valores distintos | no hay vacíos |

## 3. dim_exportador

| Atributo | Valor |
|:---|:---|
| **Archivo** | `datos/limpios/bd_depurada/dim_exportador.parquet` (las antioqueñas también en `datos/limpios/directorio_exportadores_antioquenos.csv`) |
| **Fuente y fecha de descarga** | DIAN (descargada en noviembre de 2026) más RUES, Supersociedades, SECOP II, MinAgricultura y MinCIT; procesada con el paso 9. Cubre 2024-01 a 2026-09 |
| **Cada fila es** | una empresa exportadora (persona jurídica) |
| **Filas** | 13.305 |
| **Campo que identifica cada fila (clave)** | `NIT` |

### Columnas

| # | Columna | Qué significa | Origen | Tipo | Unidad o formato | Valores válidos | Si está vacía, significa |
|---:|:---|:---|:---|:---:|:---|:---|:---|
| 1 | `RANKING_NACIONAL_FOB` | Posición por FOB total del periodo entre todas las empresas exportadoras | Calculado | número | conteo (entero) | de 1 a 13.305 | no hay vacíos |
| 2 | `RANKING_ANTIOQUIA_FOB` | Posición por FOB total entre los exportadores antioqueños (VINCULO A o B) | Calculado | número | conteo (entero) | de 1 a 3.195 | la empresa no es exportador antioqueño (vínculo C o D) (76,0 % de las filas) |
| 3 | `NIT` | NIT sin dígito de verificación ni ceros a la izquierda (llave) | DIAN | texto | número de NIT sin dígito de verificación ni ceros a la izquierda | 9.622 valores distintos | no hay vacíos |
| 4 | `RAZON_SOCIAL` | Razón social canónica: la más reciente publicada por la DIAN; si la DIAN nunca la publicó, la del RUES | DIAN (limpia) / RUES | texto | texto libre | 14.946 valores distintos | la empresa solo aparece en sep-2024 (razón social enmascarada) y no está en el RUES (0,0 % de las filas) |
| 5 | `VINCULO_ANTIOQUIA` | A = matrícula principal en cámara de comercio de Antioquia (o, sin RUES, dirección DIAN propia en Antioquia); B = domicilio fuera pero su mercancía es principalmente de origen Antioquia; C = solo parte de su mercancía es de Antioquia; D = sin relación | Calculado (RUES + DIAN), regla de docs/metodologia.md | texto | texto libre | «D. Sin relación con Antioquia»; «A. Empresa antioqueña (domicilio en Antioquia)»; «C. Domicilio fuera; parte de su mercancía es de origen Antioquia»; «B. Domicilio fuera; origen principal de su mercancía es Antioquia» | no hay vacíos |
| 6 | `EMPRESA_ANTIOQUENA` | VERDADERO si VINCULO_ANTIOQUIA = A | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (2.875) o FALSO (10.430) | no hay vacíos |
| 7 | `ES_EXPORTADOR_ANTIOQUENO` | VERDADERO si VINCULO_ANTIOQUIA es A o B | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (3.195) o FALSO (10.110) | no hay vacíos |
| 8 | `NOMBRES_EN_FUENTE` | Todas las razones sociales distintas con que aparece el NIT (solo si hay más de una) | DIAN | texto | texto libre | 256 valores distintos | la empresa aparece con una sola razón social (97,5 % de las filas) |
| 9 | `RAZON_SOCIAL_RUES` | Razón social en el registro mercantil | RUES | texto | texto libre | 13.061 valores distintos | la fuente no trae el dato (0,4 % de las filas) |
| 10 | `TIPO_EXPORTADOR` | Persona jurídica (las personas naturales no tienen NIT publicado y no están en el directorio) | Calculado | texto | texto libre | «Persona jurídica» | no hay vacíos |
| 11 | `CLASE_EXPORTADOR` | Clase más frecuente declarada (1 mixta, 2 privada, 3 pública) | DIAN | texto | código | «2»; «3»; «1» | no hay vacíos |
| 12 | `CLASE_EXPORTADOR_DESC` | Descripción de la clase | catalogo_codigos | texto | texto libre | «Privada»; «Pública»; «Economía mixta» | no hay vacíos |
| 13 | `CAMARA_COMERCIO` | Cámara de comercio de la matrícula principal (prioriza activa y renovada más recientemente) | RUES Confecámaras (c82u-588k) | texto | texto libre | 58 valores distintos | la empresa no aparece en el RUES (0,4 % de las filas) |
| 14 | `MATRICULA` | Número de matrícula mercantil | RUES | texto | texto libre | 16.158 valores distintos | la fuente no trae el dato (0,4 % de las filas) |
| 15 | `CIIU_PRINCIPAL_RUES` | Actividad económica principal CIIU rev. 4 (4 dígitos) | RUES | texto | código CIIU rev. 4 de 4 dígitos | 430 valores distintos | la empresa no aparece en el RUES (0,4 % de las filas) |
| 16 | `CIIU_SECUNDARIO_RUES` | Actividad económica secundaria CIIU (4 dígitos) | RUES | texto | código CIIU rev. 4 de 4 dígitos | 468 valores distintos | la empresa no registró actividad secundaria o no aparece en el RUES (20,3 % de las filas) |
| 17 | `ORGANIZACION_JURIDICA` | Forma jurídica | RUES | texto | texto libre | 20 valores distintos | la fuente no trae el dato (0,4 % de las filas) |
| 18 | `FECHA_MATRICULA` | Fecha de la matrícula mercantil | RUES (AAAAMMDD → fecha; "00000000" → NULL) | fecha | AAAA-MM-DD | de 1926-04-19 a 2026-11-03 | la fuente no trae el dato (0,4 % de las filas) |
| 19 | `ULTIMO_ANO_RENOVADO` | Último año de renovación de la matrícula | RUES | número | — | de 0 a 2026 | la fuente no trae el dato (0,4 % de las filas) |
| 20 | `ESTADO_MATRICULA` | Estado de la matrícula (ACTIVA, CANCELADA, …) | RUES | texto | texto libre | «ACTIVA»; «MATRÍCULA NUEVA, CONSTITUCIÓN POR TRASLADO»; «CANCELADA»; «MATRÍCULA CANCELADA POR TRASLADO DE DOMICILIO»; «SIN ESTADO»; «MATRÍCULA CANCELADA POR FUSIÓN»; «NO COMPETENCIA DE LA CAMARA»; «NO ASIGNADO» | la fuente no trae el dato (0,4 % de las filas) |
| 21 | `TIENE_MATRICULA_ACTIVA_EN_ANTIOQUIA` | VERDADERO si tiene alguna matrícula activa en una cámara de Antioquia | RUES | verdadero / falso | VERDADERO / FALSO | VERDADERO (2.830) o FALSO (10.428) | la fuente no trae el dato (0,4 % de las filas) |
| 22 | `COD_MPIO_DIAN_DIRECCION_PROPIA` | Municipio de la dirección DIAN usando solo direcciones compartidas por 5 NIT o menos (las demás suelen ser de agencias de aduanas) | Calculado (DIAN) | texto | DIVIPOLA de 5 dígitos | 101 valores distintos | todas sus direcciones DIAN las comparten más de 5 NIT (suelen ser de agencias de aduanas) (94,4 % de las filas) |
| 23 | `MUNICIPIO_DIAN_DIRECCION_PROPIA` | Nombre del municipio anterior | DIVIPOLA | texto | texto libre | 88 valores distintos | todas sus direcciones DIAN las comparten más de 5 NIT (94,4 % de las filas) |
| 24 | `DEPTO_DIAN_DIRECCION_PROPIA` | Departamento del municipio anterior | DIVIPOLA | texto | texto libre | 26 valores distintos | todas sus direcciones DIAN las comparten más de 5 NIT (94,4 % de las filas) |
| 25 | `COD_DEPTO_ORIGEN_PRINCIPAL` | Departamento de origen con mayor FOB de la empresa | Calculado (DIAN) | texto | DIVIPOLA de 2 dígitos (00 = departamentos varios) | 30 valores distintos | no hay vacíos |
| 26 | `DEPTO_ORIGEN_PRINCIPAL_MERCANCIA` | Nombre del departamento anterior | dim_departamento | texto | texto libre | 30 valores distintos | no hay vacíos |
| 27 | `SECTOR_EXPORTADOR_PRINCIPAL` | Sector con mayor FOB: Minero-energético / Agrícola y agroindustrial (MADR) / Industria y otros | Calculado (dim_subpartida) | texto | texto libre | «Industria y otros»; «Agrícola y agroindustrial (MADR)»; «Minero-energético» | no hay vacíos |
| 28 | `PCT_FOB_MINERO_ENERGETICO` | % del FOB en subpartidas minero-energéticas (definición calibrada contra MinCIT NME) | Calculado | número | porcentaje de 0 a 100 | de 0,00 a 100,00 | no hay vacíos |
| 29 | `PCT_FOB_AGRICOLA_MADR` | % del FOB en subpartidas agrícolas y agroindustriales según MinAgricultura | Calculado | número | porcentaje de 0 a 100 | de 0,00 a 100,00 | no hay vacíos |
| 30 | `PRODUCTO_AGRICOLA_PRINCIPAL_MADR` | Producto agrícola con mayor FOB (p. ej. Café, Banano, Flores) | Calculado (MADR) | texto | texto libre | 253 valores distintos | la empresa no exporta productos agrícolas (74,1 % de las filas) |
| 31 | `FOB_USD_2024` | FOB en dólares 2024 (incluye sep-2024, cuya razón social vino enmascarada) | Calculado | número | dólares (USD) | de 0,50 a 10.228.807.360,98 | la empresa no exportó ese año (28,3 % de las filas) |
| 32 | `FOB_USD_2025` | FOB en dólares 2025 | Calculado | número | dólares (USD) | de 0,13 a 8.763.560.533,61 | la empresa no exportó ese año (29,3 % de las filas) |
| 33 | `FOB_USD_2026` | FOB en dólares 2026 (año en curso: llega hasta el último mes publicado, ver info_bd) | Calculado | número | dólares (USD) | de 0,01 a 7.886.015.530,63 | la empresa no exportó ese año (39,7 % de las filas) |
| 34 | `FOB_USD_TOTAL` | FOB total de todo el periodo cubierto | Calculado | número | dólares (USD) | de 0,50 a 26.878.383.425,22 | no hay vacíos |
| 35 | `FOB_USD_ORIGEN_ANTIOQUIA` | FOB de mercancía con origen Antioquia | Calculado | número | dólares (USD) | de 0,00 a 2.689.943.635,90 | no hay vacíos |
| 36 | `PCT_FOB_ORIGEN_ANTIOQUIA` | % del FOB de la empresa con origen Antioquia | Calculado | número | porcentaje de 0 a 100 | de 0,00 a 100,00 | no hay vacíos |
| 37 | `PCT_FOB_DESTINO_ZONA_FRANCA` | % del FOB enviado a zonas francas colombianas | Calculado | número | porcentaje de 0 a 100 | de 0,00 a 100,00 | no hay vacíos |
| 38 | `PESO_NETO_KGS_TOTAL` | Peso neto total exportado (kg) | Calculado | número | kilogramos | de 0,00 a 74.824.230.459,28 | no hay vacíos |
| 39 | `N_REGISTROS` | Número de registros (series) en hechos_exportaciones | Calculado | número | conteo (entero) | de 1 a 184.293 | no hay vacíos |
| 40 | `N_DECLARACIONES` | Número de declaraciones distintas (los registros sin formulario cuentan uno a uno) | Calculado | número | conteo (entero) | de 1 a 57.161 | no hay vacíos |
| 41 | `N_MESES_CON_EXPORTACION` | Meses con al menos una exportación | Calculado | número | conteo (entero) | de 1 a 33 | no hay vacíos |
| 42 | `PRIMER_MES` | Primer mes con exportación (AAAA-MM) | Calculado | texto | AAAA-MM | 32 valores distintos | no hay vacíos |
| 43 | `ULTIMO_MES` | Último mes con exportación (AAAA-MM) | Calculado | texto | AAAA-MM | 32 valores distintos | no hay vacíos |
| 44 | `N_PAISES_DESTINO` | Número de destinos distintos (las zonas francas cuentan como uno) | Calculado | número | conteo (entero) | de 1 a 78 | no hay vacíos |
| 45 | `TOP3_PAISES_DESTINO` | Tres destinos principales con su % del FOB | Calculado (dim_pais) | texto | texto libre | 7.199 valores distintos | no hay vacíos |
| 46 | `N_SUBPARTIDAS` | Número de subpartidas exportadas | Calculado | número | conteo (entero) | de 1 a 729 | no hay vacíos |
| 47 | `TOP5_SUBPARTIDAS` | Cinco subpartidas con mayor FOB | Calculado | texto | texto libre | 9.132 valores distintos | no hay vacíos |
| 48 | `CAPITULO_ARANCEL_PRINCIPAL` | Capítulo arancelario (2 dígitos) de la subpartida principal | Calculado | texto | texto libre | 84 valores distintos | no hay vacíos |
| 49 | `ADUANA_SALIDA_PRINCIPAL` | Aduana de salida más frecuente | Calculado | texto | texto libre | 21 valores distintos | no hay vacíos |
| 50 | `MODO_TRANSPORTE_PRINCIPAL` | Modo de transporte más frecuente | Calculado | texto | texto libre | «Marítimo»; «Aéreo»; «Terrestre (carretero)»; «Instalaciones Fijas»; «Vías navegables interiores» | no hay vacíos |
| 51 | `SS_MACROSECTOR` | Macrosector (solo empresas entre las 10.000 más grandes) | Supersociedades (6cat-2gcs) | texto | texto libre | «MANUFACTURA»; «COMERCIO»; «SERVICIOS»; «AGROPECUARIO»; «MINERO»; «CONSTRUCCIÓN» | la empresa no está entre las 10.000 más grandes de Supersociedades (73,5 % de las filas) |
| 52 | `SS_CIIU` | CIIU reportado a Supersociedades (4 dígitos) | Supersociedades (formato homogeneizado) | texto | código CIIU rev. 4 de 4 dígitos | 297 valores distintos | la fuente no trae el dato (73,5 % de las filas) |
| 53 | `SS_SUPERVISOR` | Superintendencia que la supervisa | Supersociedades | texto | texto libre | «SUPERSOCIEDADES»; «SUPERTRANSPORTE»; «SUPERSALUD»; «SUPERFINANCIERA»; «SUPERSERVICIOS»; «SUPERVIGILANCIA» | la fuente no trae el dato (73,5 % de las filas) |
| 54 | `SS_DEPARTAMENTO_DOMICILIO` | Departamento del domicilio | Supersociedades | texto | texto libre | 32 valores distintos | la fuente no trae el dato (73,5 % de las filas) |
| 55 | `SS_CIUDAD_DOMICILIO` | Ciudad del domicilio | Supersociedades | texto | texto libre | 187 valores distintos | la fuente no trae el dato (73,5 % de las filas) |
| 56 | `SS_INGRESOS_OPERACIONALES_BILLONES_COP` | Ingresos operacionales en billones de pesos (10^12) | Supersociedades | número | pesos colombianos | de 0,01 a 100,59 | la fuente no trae el dato (73,5 % de las filas) |
| 57 | `SS_TOTAL_ACTIVOS_BILLONES_COP` | Activos totales en billones de pesos (10^12) | Supersociedades | número | pesos colombianos | de 0,00 a 198,11 | la fuente no trae el dato (73,5 % de las filas) |
| 58 | `SS_ANO_CORTE` | Año de corte de las cifras de Supersociedades | Supersociedades | número | — | de 2021 a 2025 | la fuente no trae el dato (73,5 % de las filas) |
| 59 | `PROVEEDOR_ESTADO_SECOP_II` | VERDADERO si tiene contratos con entidades públicas en SECOP II | SECOP II (jbjy-vk9h) | verdadero / falso | VERDADERO / FALSO | VERDADERO (1.724) o FALSO (11.581) | no hay vacíos |
| 60 | `SECOP_N_CONTRATOS` | Número de contratos en SECOP II | SECOP II | número | conteo (entero) | de 1 a 1.564 | la empresa no tiene contratos en SECOP II (87,0 % de las filas) |
| 61 | `SECOP_VALOR_CONTRATOS_COP` | Valor total de los contratos en pesos | SECOP II | número | pesos colombianos | de 0,00 a 12.858.452.444.481.594,00 | la fuente no trae el dato (87,0 % de las filas) |
| 62 | `SECOP_PRIMERA_FIRMA` | Fecha del primer contrato firmado | SECOP II | fecha | AAAA-MM-DD | de 2015-09-09 a 2026-11-12 | la fuente no trae el dato (87,5 % de las filas) |
| 63 | `SECOP_ULTIMA_FIRMA` | Fecha del último contrato firmado | SECOP II | fecha | AAAA-MM-DD | de 2017-03-01 a 2026-11-14 | la fuente no trae el dato (87,5 % de las filas) |
| 64 | `SECOP_ES_PYME` | Lo que declaró en SECOP II: Sí / No / Mixto. Única variable de tamaño disponible | SECOP II | texto | texto libre | «No»; «Sí»; «Mixto» | la empresa no tiene contratos en SECOP II (87,0 % de las filas) |
| 65 | `SECOP_N_ENTIDADES` | Número de entidades contratantes | SECOP II | número | conteo (entero) | de 1 a 259 | la fuente no trae el dato (87,0 % de las filas) |
| 66 | `EN_DIRECTORIO_ENTRADA` | VERDADERO si el NIT estaba en el directorio del paso 7 (de ahí salen los atributos RUES, Supersociedades y SECOP) | Trazabilidad | verdadero / falso | VERDADERO / FALSO | VERDADERO (13.305) o FALSO (0) | no hay vacíos |
| 67 | `FUENTE_DOMICILIO` | De dónde sale el domicilio usado para VINCULO_ANTIOQUIA | Calculado | texto | texto libre | «RUES: cámara fuera de Antioquia»; «RUES: cámara de Antioquia»; «Sin RUES»; «Sin RUES; dirección DIAN propia en Antioquia» | no hay vacíos |
| 68 | `EXPORTADOR_2024_MIN_1000USD` | VERDADERO si exportó al menos USD 1.000 FOB en 2024 (umbral Analdex) | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (9.340) o FALSO (3.965) | no hay vacíos |
| 69 | `EXPORTADOR_2025_MIN_1000USD` | Ídem 2025 | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (9.226) o FALSO (4.079) | no hay vacíos |
| 70 | `EXPORTADOR_2026_MIN_1000USD` | Ídem 2026 (año en curso) | Calculado | verdadero / falso | VERDADERO / FALSO | VERDADERO (7.896) o FALSO (5.409) | no hay vacíos |

## 4. Otras tablas

Las dimensiones (`dim_subpartida`, `dim_pais`, `dim_zona_franca`, `dim_departamento`, `dim_municipio`, `dim_aduana`, `dim_declarante`), `catalogo_codigos` y las vistas (`vw_exportaciones`, `vw_exportaciones_antioquia`, `vw_directorio_antioquia`, `vw_serie_mensual`, `vw_validacion_*`) están descritas columna por columna en [docs/diccionario_bd_depurada.csv](docs/diccionario_bd_depurada.csv) y en la tabla `diccionario_datos` de la BD.

_Generado el 2026-11-17._
