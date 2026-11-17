# Diccionario de datos

> Qué significa cada columna de la BD depurada, para que otra persona la entienda sin preguntarnos. Se genera con el paso 9 (`pipeline/diccionario_md.py`): el tipo, los valores válidos y el porcentaje de vacíos salen de los datos.

Contenido: [1. Muestra original](#1-muestra-original) · [2. hechos_exportaciones](#2-hechos_exportaciones) · [3. dim_exportador](#3-dim_exportador) · [4. Otras tablas](#4-otras-tablas)

## 1. Muestra original

- **Archivo:** `datos/originales/muestra_dian_exportaciones_2026_09.csv`
- **Fuente y fecha de descarga:** DIAN, bases estadísticas de exportaciones, archivo `09_Exportaciones_2026_Septiembre.zip`, descargado en noviembre de 2026
- **Cada fila es:** un ítem (serie) de una declaración de exportación, tal como lo publica la DIAN
- **Filas en la muestra:** 1.000 (las primeras del archivo de septiembre de 2026, que tiene 115.049)
- **Campo que identifica cada fila (clave):** no hay uno solo; `NUMERO_FORMULARIO` + `NUMERO_SERIE` casi siempre, pero se repite en algunas líneas

Trae 70 de las 72 columnas de la DIAN. Se omitieron `RAZON_SOCIAL_DESTINATARIO` y `DOMICILIO_DESTINATARIO` porque pueden ser el nombre y la dirección de una persona, y `DIREC_EXPORTADOR` va vacía en las líneas de personas naturales. La descripción de las 72 columnas originales está en [docs/diccionario_transaccional.csv](docs/diccionario_transaccional.csv) y en la ficha técnica de la DIAN ([docs/referencias/](docs/referencias/)). Abajo se describen las columnas limpias, que son las que se usan para analizar.

## 2. hechos_exportaciones

- **Archivo:** `datos/limpios/bd_depurada/hechos_exportaciones/` (un parquet por mes)
- **Fuente y fecha de descarga:** DIAN (descargada en noviembre de 2026) más RUES, Supersociedades, SECOP II, MinAgricultura y MinCIT; procesada con el paso 9. Cubre 2024-01 a 2026-09
- **Cada fila es:** un ítem (serie) de una declaración de exportación DIAN: una subpartida exportada por un exportador en una declaración
- **Filas:** 3.613.237
- **Campo que identifica cada fila (clave):** `ID_REGISTRO` (la DIAN no trae una llave única: formulario + serie se repite y 1.690 líneas no tienen formulario)

### Columnas

#### ID_REGISTRO
- Qué significa: Llave única del registro (asignada en la depuración; la DIAN no trae una llave única) · Origen: Calculado
- Tipo: número
- Unidad o formato: —
- Valores válidos: de 1 a 3.613.237
- Si está vacía, significa: no hay vacíos

#### PERIODO
- Qué significa: Mes de la exportación (primer día del mes) · Origen: DIAN
- Tipo: fecha
- Unidad o formato: AAAA-MM-DD (primer día del mes)
- Valores válidos: de 2024-01-01 a 2026-09-01
- Si está vacía, significa: no hay vacíos

#### ANIO
- Qué significa: Año de la exportación · Origen: DIAN
- Tipo: número
- Unidad o formato: —
- Valores válidos: de 2024 a 2026
- Si está vacía, significa: no hay vacíos

#### MES
- Qué significa: Mes de la exportación (1-12) · Origen: DIAN
- Tipo: número
- Unidad o formato: —
- Valores válidos: de 1 a 12
- Si está vacía, significa: no hay vacíos

#### FECHA_DECLARACION
- Qué significa: Fecha de la declaración de exportación · Origen: DIAN FECHA_DECLARACION_EXPORTACION (AAAAMMDD → fecha)
- Tipo: fecha
- Unidad o formato: AAAA-MM-DD
- Valores válidos: de 2024-01-01 a 2026-09-30
- Si está vacía, significa: no hay vacíos

#### NUMERO_FORMULARIO
- Qué significa: Número de la declaración de exportación (DEX). NULL en las exportaciones sin formulario (sobre todo hidrocarburos) · Origen: DIAN ("0" → NULL)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 1.150.878 valores distintos
- Si está vacía, significa: la línea no tiene número de declaración (sobre todo hidrocarburos de Ecopetrol, Reficar o Frontera); es legítima (0,0 % de las filas)

#### NUMERO_SERIE
- Qué significa: Ítem o serie dentro de la declaración · Origen: DIAN
- Tipo: número
- Unidad o formato: —
- Valores válidos: de 0 a 552
- Si está vacía, significa: no hay vacíos

#### TIPO_DESPACHO
- Qué significa: Inicial / Corrección / Modificación. La base DIAN solo trae la versión vigente de cada declaración · Origen: DIAN (ortografía corregida)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «Inicial»; «Corrección»; «Modificación»
- Si está vacía, significa: no hay vacíos

#### TIPO_DATOS
- Qué significa: Definitivos al embarque / Definitivos después del embarque · Origen: DIAN (ortografía corregida)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «Definitivos al embarque»; «Definitivos después del embarque»
- Si está vacía, significa: no hay vacíos

#### TIPO_EMBARQUE
- Qué significa: Único / Fraccionado / Global con cargues parciales · Origen: DIAN (se usa la descripción; el código no era 1:1 con ella)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «Único»; «Fraccionado»; «Global con cargues parciales»
- Si está vacía, significa: no hay vacíos

#### NUM_DECLARACION_ANTERIOR
- Qué significa: Declaración que la corrección o modificación reemplaza · Origen: DIAN ("0" → NULL)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 242.309 valores distintos
- Si está vacía, significa: es una declaración inicial (no corrige a otra) (90,1 % de las filas)

#### PERIODO_DECLARACION_ANTERIOR
- Qué significa: Mes de la declaración anterior · Origen: DIAN (AAAAMM → fecha)
- Tipo: fecha
- Unidad o formato: AAAA-MM-DD (primer día del mes)
- Valores válidos: de 2020-04-01 a 2026-09-01
- Si está vacía, significa: es una declaración inicial (no corrige a otra) (90,1 % de las filas)

#### NUM_DECLARACION_PRECEDENTE
- Qué significa: Declaración precedente (p. ej. importación temporal que se reexporta) · Origen: DIAN ("0" → NULL)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 17.258 valores distintos
- Si está vacía, significa: no hay declaración precedente (no viene de una importación temporal) (99,3 % de las filas)

#### PERIODO_DECLARACION_PRECEDENTE
- Qué significa: Mes de la declaración precedente · Origen: DIAN (AAAAMM → fecha)
- Tipo: fecha
- Unidad o formato: AAAA-MM-DD (primer día del mes)
- Valores válidos: de 2006-10-01 a 2026-09-01
- Si está vacía, significa: no hay declaración precedente (99,6 % de las filas)

#### COD_MODALIDAD_PRECEDENTE
- Qué significa: Modalidad de la declaración precedente · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: 85 valores distintos
- Si está vacía, significa: no hay declaración precedente (98,6 % de las filas)

#### NUM_AUTORIZACION_EMBARQUE
- Qué significa: Número de la solicitud de autorización de embarque · Origen: DIAN NUM_SOLICITUD_AUTO_EMBARQUE
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 1.216.397 valores distintos
- Si está vacía, significa: la fuente no trae el dato (0,0 % de las filas)

#### PERIODO_AUTORIZACION_EMBARQUE
- Qué significa: Mes de la solicitud de autorización de embarque (562 registros traen meses anteriores a 2023) · Origen: DIAN (AAAAMM → fecha)
- Tipo: fecha
- Unidad o formato: AAAA-MM-DD (primer día del mes)
- Valores válidos: de 2008-11-01 a 2026-09-01
- Si está vacía, significa: no hay vacíos

#### NIT_EXPORTADOR
- Qué significa: NIT del exportador sin dígito de verificación ni ceros a la izquierda. NULL = persona natural (la DIAN oculta su documento). Llave hacia dim_exportador · Origen: DIAN
- Tipo: texto
- Unidad o formato: número de NIT sin dígito de verificación ni ceros a la izquierda
- Valores válidos: 9.622 valores distintos; cada uno existe en `dim_exportador`
- Si está vacía, significa: el exportador es una persona natural: la DIAN no publica su documento (0,5 % de las filas)

#### TIPO_IDENTIFICACION
- Qué significa: Código del tipo de documento (1 persona natural, 2 NIT). Ver catalogo_codigos · Origen: DIAN TIPO_IDENT
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «2»; «1»
- Si está vacía, significa: no hay vacíos

#### ES_PERSONA_NATURAL
- Qué significa: VERDADERO si el exportador no tiene NIT publicado (la DIAN anonimiza a las personas naturales). Se define por el NIT y no por la razón social, que falla en sep-2024 · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (16.714) o FALSO (3.596.523)
- Si está vacía, significa: no hay vacíos

#### FLAG_RAZON_SOCIAL_ENMASCARADA
- Qué significa: VERDADERO si la DIAN publicó "PERSONA NATURAL" o dejó vacía la razón social aunque la línea trae NIT de empresa (sep-2024). La línea se atribuye a la empresa por el NIT · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (107.212) o FALSO (3.506.025)
- Si está vacía, significa: no hay vacíos

#### CLASE_EXPORTADOR
- Qué significa: Clase declarada: 1 economía mixta, 2 privada, 3 pública. Ver catalogo_codigos · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «2»; «3»; «1»
- Si está vacía, significa: no hay vacíos

#### TIPO_USUARIO
- Qué significa: Código DIAN del tipo de usuario aduanero (sin descripción en la fuente; 36 = 99,9 % de los registros) · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «36»; «22»; «53»; «26»; «55»; «38»; «56»; «7»; «4»; «1»
- Si está vacía, significa: no hay vacíos

#### DIRECCION_DECLARADA
- Qué significa: Dirección del exportador declarada a la DIAN. OJO: muchas veces es la de la agencia de aduanas. Vacía para personas naturales (dato personal) · Origen: DIAN DIREC_EXPORTADOR (limpia)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 989 valores distintos
- Si está vacía, significa: persona natural (no se publica por ser dato personal) o la fuente no la trae (0,5 % de las filas)

#### COD_MPIO_DIRECCION_DECLARADA
- Qué significa: Municipio DIVIPOLA (5 dígitos) de la dirección declarada. Llave hacia dim_municipio · Origen: DIAN COD_DPTO_EXPORTADOR (en realidad es el municipio)
- Tipo: texto
- Unidad o formato: DIVIPOLA de 5 dígitos
- Valores válidos: 110 valores distintos; cada uno existe en `dim_municipio`
- Si está vacía, significa: la DIAN no trae un código de municipio válido (0,0 % de las filas)

#### DIRECCION_DECLARADA_EN_ANTIOQUIA
- Qué significa: VERDADERO si la dirección declarada está en Antioquia · Origen: Calculado (paso 4)
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (509.234) o FALSO (3.104.003)
- Si está vacía, significa: no hay vacíos

#### NIT_DECLARANTE
- Qué significa: NIT de la agencia de aduanas o declarante. Llave hacia dim_declarante · Origen: DIAN
- Tipo: texto
- Unidad o formato: número de NIT sin dígito de verificación ni ceros a la izquierda
- Valores válidos: 745 valores distintos; cada uno existe en `dim_declarante`
- Si está vacía, significa: el declarante es una persona natural (la DIAN oculta su NIT) o la fuente no lo trae (0,1 % de las filas)

#### CIUDAD_DESTINATARIO
- Qué significa: Ciudad del destinatario, en mayúsculas. Su razón social y su domicilio no se publican porque pueden ser de una persona · Origen: DIAN (limpia, entidades HTML decodificadas)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 17.441 valores distintos
- Si está vacía, significa: la fuente no trae la ciudad del comprador (0,0 % de las filas)

#### COD_PAIS_DESTINO
- Qué significa: País destino final ISO 3166 alfa-3; "XCF" = zona franca colombiana. Llave hacia dim_pais · Origen: DIAN COD_PAIS_DESTINO_ALF (zonas francas corregidas)
- Tipo: texto
- Unidad o formato: ISO 3166 alfa-3 (XCF = zona franca, ND = no declarado)
- Valores válidos: 227 valores distintos; cada uno existe en `dim_pais`
- Si está vacía, significa: no hay vacíos

#### ES_DESTINO_ZONA_FRANCA
- Qué significa: VERDADERO si la mercancía va a una zona franca en Colombia (no sale del país) · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (38.520) o FALSO (3.574.712)
- Si está vacía, significa: la fuente no trae el dato (0,0 % de las filas)

#### COD_ZONA_FRANCA_DESTINO
- Qué significa: Código de la zona franca de destino. Llave hacia dim_zona_franca · Origen: DIAN COD_PAIS_DESTINO_NUM
- Tipo: texto
- Unidad o formato: código
- Valores válidos: 33 valores distintos; cada uno existe en `dim_zona_franca`
- Si está vacía, significa: el destino no es una zona franca (98,9 % de las filas)

#### OFICINA
- Qué significa: Código de la oficina DIAN (sin descripción en la fuente) · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «99»; «3»; «6»; «11»; «35»; «2»; «5»; «19»; «37»
- Si está vacía, significa: no hay vacíos

#### COD_ADUANA_DESPACHO
- Qué significa: Aduana donde se presentó la declaración. Llave hacia dim_aduana · Origen: DIAN (2 dígitos)
- Tipo: texto
- Unidad o formato: código DIAN de 2 dígitos
- Valores válidos: 24 valores distintos; cada uno existe en `dim_aduana`
- Si está vacía, significa: no hay vacíos

#### COD_ADUANA_SALIDA
- Qué significa: Aduana por donde salió la mercancía. Llave hacia dim_aduana · Origen: DIAN (2 dígitos)
- Tipo: texto
- Unidad o formato: código DIAN de 2 dígitos
- Valores válidos: 23 valores distintos; cada uno existe en `dim_aduana`
- Si está vacía, significa: no hay vacíos

#### COD_LUGAR_SALIDA
- Qué significa: Puerto, aeropuerto o paso de frontera de salida (código alfabético) · Origen: DIAN COD_LUG_SALIDA_ALF
- Tipo: texto
- Unidad o formato: código
- Valores válidos: 24 valores distintos
- Si está vacía, significa: no hay vacíos

#### COD_DEPTO_PROCEDENCIA
- Qué significa: Departamento DIVIPOLA desde donde se despachó la mercancía. Llave hacia dim_departamento · Origen: DIAN COD_REGION_PROCEDENCIA
- Tipo: texto
- Unidad o formato: DIVIPOLA de 2 dígitos (00 = departamentos varios)
- Valores válidos: 33 valores distintos; cada uno existe en `dim_departamento`
- Si está vacía, significa: no hay vacíos

#### COD_DEPTO_ORIGEN
- Qué significa: Departamento DIVIPOLA donde se produjo la mercancía ("00" = departamentos varios). Llave hacia dim_departamento · Origen: DIAN COD_REGION_ORIGEN
- Tipo: texto
- Unidad o formato: DIVIPOLA de 2 dígitos (00 = departamentos varios)
- Valores válidos: 35 valores distintos; cada uno existe en `dim_departamento`
- Si está vacía, significa: no hay vacíos

#### ORIGEN_MERCANCIA_ANTIOQUIA
- Qué significa: VERDADERO si la mercancía es de origen Antioquia (COD_DEPTO_ORIGEN = 05) · Origen: Calculado (paso 4)
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (924.426) o FALSO (2.688.811)
- Si está vacía, significa: no hay vacíos

#### COD_MODO_TRANSPORTE
- Qué significa: Modo de transporte. Ver catalogo_codigos (MODO_TRANSPORTE) · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «4»; «1»; «3»; «7»; «8»
- Si está vacía, significa: no hay vacíos

#### COD_PAIS_BANDERA
- Qué significa: País de la bandera del medio de transporte, ISO alfa-3 ("ND" = no declarado). Llave hacia dim_pais · Origen: DIAN (2024 alfa-2 convertido a alfa-3)
- Tipo: texto
- Unidad o formato: ISO 3166 alfa-3 (XCF = zona franca, ND = no declarado)
- Valores válidos: 146 valores distintos; cada uno existe en `dim_pais`
- Si está vacía, significa: no hay vacíos

#### COD_MODALIDAD_EXPORTACION
- Qué significa: Modalidad de exportación (3 dígitos). Ver catalogo_codigos · Origen: DIAN (ceros a la izquierda homogéneos)
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «198»; «199»; «104»; «002»; «201»; «107»; «004»; «401»; «310»; «402»; «403»
- Si está vacía, significa: no hay vacíos

#### COD_REGIMEN_CAN
- Qué significa: Código de régimen Comunidad Andina (sin descripción en la fuente) · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «1»; «4»; «5»; «3»
- Si está vacía, significa: no hay vacíos

#### FORMA_PAGO
- Qué significa: Código de forma de pago (sin descripción en la fuente) · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «1»; «2»
- Si está vacía, significa: no hay vacíos

#### TIPO_CERTIFICADO_ORIGEN
- Qué significa: Código del tipo de certificado de origen (sin descripción en la fuente) · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «8»; «1»; «2»; «5»; «6»; «3»; «4»; «7»
- Si está vacía, significa: no hay vacíos

#### SISTEMAS_ESPECIALES
- Qué significa: VERDADERO si la operación usa Sistemas Especiales de Importación-Exportación (Plan Vallejo) · Origen: DIAN (SI/NO → booleano)
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (1.208.347) o FALSO (2.404.890)
- Si está vacía, significa: no hay vacíos

#### EXPORTACION_EN_TRANSITO
- Qué significa: VERDADERO si es exportación en tránsito · Origen: DIAN (SI/NO → booleano)
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (141.765) o FALSO (3.471.472)
- Si está vacía, significa: no hay vacíos

#### COD_MONEDA_TRANSACCION
- Qué significa: Moneda de la transacción (ISO 4217) · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: 37 valores distintos
- Si está vacía, significa: no hay vacíos

#### SUBPARTIDA
- Qué significa: Subpartida arancelaria a 10 dígitos con cero inicial. Llave hacia dim_subpartida · Origen: DIAN
- Tipo: texto
- Unidad o formato: 10 dígitos con cero inicial
- Valores válidos: 6.620 valores distintos; cada uno existe en `dim_subpartida`
- Si está vacía, significa: no hay vacíos

#### COD_UNIDAD_FISICA
- Qué significa: Unidad de la cantidad física. Ver catalogo_codigos (UNIDAD_FISICA) · Origen: DIAN COD_UNIDAD_FISICA_ALF
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «U»; «KG»; «M2»; «M3»; «L»; «2U»; «MIL»; «C/T»; «KWH»; «CM3»
- Si está vacía, significa: no hay vacíos

#### CANTIDAD_UNIDADES_FISICAS
- Qué significa: Cantidad en la unidad física declarada · Origen: DIAN
- Tipo: número
- Unidad o formato: —
- Valores válidos: de 0,01 a 3.924.109.000,00
- Si está vacía, significa: no hay vacíos

#### PESO_BRUTO_KGS
- Qué significa: Peso bruto en kilogramos · Origen: DIAN
- Tipo: número
- Unidad o formato: kilogramos
- Valores válidos: de 0,00 a 300.000.000,00
- Si está vacía, significa: no hay vacíos

#### PESO_NETO_KGS
- Qué significa: Peso neto en kilogramos · Origen: DIAN
- Tipo: número
- Unidad o formato: kilogramos
- Valores válidos: de 0,00 a 300.000.000,00
- Si está vacía, significa: no hay vacíos

#### VALOR_FOB_USD
- Qué significa: Valor FOB en dólares (medida principal) · Origen: DIAN
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,01 a 138.472.440,86
- Si está vacía, significa: no hay vacíos

#### VALOR_FOB_COP
- Qué significa: Valor FOB en pesos colombianos · Origen: DIAN VALOR_FOB_PESOS
- Tipo: número
- Unidad o formato: pesos colombianos
- Valores válidos: de 30,72 a 514.107.071.810,92
- Si está vacía, significa: no hay vacíos

#### VALOR_AGREGADO_NACIONAL_USD
- Qué significa: Valor agregado nacional de la serie en dólares · Origen: DIAN VLR_SERIE_AGREGADO_NAL_USD
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,00 a 20.448.388,65
- Si está vacía, significa: no hay vacíos

#### VALOR_FLETES_USD
- Qué significa: Fletes de la serie en dólares · Origen: DIAN VALOR_SERIE_FLETES_USD
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,00 a 20.889.155,00
- Si está vacía, significa: no hay vacíos

#### VALOR_SEGUROS_USD
- Qué significa: Seguros de la serie en dólares · Origen: DIAN VALOR_SERIE_SEGUROS_USD
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,00 a 16.490.670,00
- Si está vacía, significa: no hay vacíos

#### VALOR_OTROS_GASTOS_USD
- Qué significa: Otros gastos de la serie en dólares · Origen: DIAN VLR_SERIE_OTROS_GASTOS_USD
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,00 a 5.418.363,00
- Si está vacía, significa: no hay vacíos

#### FLAG_PESO_CERO
- Qué significa: VERDADERO si el peso neto o bruto viene en cero (dato a revisar) · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (33) o FALSO (3.613.204)
- Si está vacía, significa: no hay vacíos

#### FLAG_REGISTRO_IDENTICO
- Qué significa: VERDADERO en 10 registros idénticos en todo a otro (sin número de formulario). Se conservan porque las cifras oficiales los incluyen; para excluirlos: WHERE NOT FLAG_REGISTRO_IDENTICO · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (10) o FALSO (3.613.227)
- Si está vacía, significa: no hay vacíos

#### ARCHIVO_FUENTE
- Qué significa: Archivo mensual DIAN del que proviene el registro · Origen: Trazabilidad
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 35 valores distintos
- Si está vacía, significa: no hay vacíos

## 3. dim_exportador

- **Archivo:** `datos/limpios/bd_depurada/dim_exportador.parquet` (las antioqueñas también en `datos/limpios/directorio_exportadores_antioquenos.csv`)
- **Fuente y fecha de descarga:** DIAN (descargada en noviembre de 2026) más RUES, Supersociedades, SECOP II, MinAgricultura y MinCIT; procesada con el paso 9. Cubre 2024-01 a 2026-09
- **Cada fila es:** una empresa exportadora (persona jurídica)
- **Filas:** 13.305
- **Campo que identifica cada fila (clave):** `NIT`

### Columnas

#### RANKING_NACIONAL_FOB
- Qué significa: Posición por FOB total del periodo entre todas las empresas exportadoras · Origen: Calculado
- Tipo: número
- Unidad o formato: conteo (entero)
- Valores válidos: de 1 a 13.305
- Si está vacía, significa: no hay vacíos

#### RANKING_ANTIOQUIA_FOB
- Qué significa: Posición por FOB total entre los exportadores antioqueños (VINCULO A o B) · Origen: Calculado
- Tipo: número
- Unidad o formato: conteo (entero)
- Valores válidos: de 1 a 3.195
- Si está vacía, significa: la empresa no es exportador antioqueño (vínculo C o D) (76,0 % de las filas)

#### NIT
- Qué significa: NIT sin dígito de verificación ni ceros a la izquierda (llave) · Origen: DIAN
- Tipo: texto
- Unidad o formato: número de NIT sin dígito de verificación ni ceros a la izquierda
- Valores válidos: 9.622 valores distintos
- Si está vacía, significa: no hay vacíos

#### RAZON_SOCIAL
- Qué significa: Razón social canónica: la más reciente publicada por la DIAN; si la DIAN nunca la publicó, la del RUES · Origen: DIAN (limpia) / RUES
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 14.946 valores distintos
- Si está vacía, significa: la empresa solo aparece en sep-2024 (razón social enmascarada) y no está en el RUES (0,0 % de las filas)

#### VINCULO_ANTIOQUIA
- Qué significa: A = matrícula principal en cámara de comercio de Antioquia (o, sin RUES, dirección DIAN propia en Antioquia); B = domicilio fuera pero su mercancía es principalmente de origen Antioquia; C = solo parte de su mercancía es de Antioquia; D = sin relación · Origen: Calculado (RUES + DIAN), regla de docs/metodologia.md
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «D. Sin relación con Antioquia»; «A. Empresa antioqueña (domicilio en Antioquia)»; «C. Domicilio fuera; parte de su mercancía es de origen Antioquia»; «B. Domicilio fuera; origen principal de su mercancía es Antioquia»
- Si está vacía, significa: no hay vacíos

#### EMPRESA_ANTIOQUENA
- Qué significa: VERDADERO si VINCULO_ANTIOQUIA = A · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (2.875) o FALSO (10.430)
- Si está vacía, significa: no hay vacíos

#### ES_EXPORTADOR_ANTIOQUENO
- Qué significa: VERDADERO si VINCULO_ANTIOQUIA es A o B · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (3.195) o FALSO (10.110)
- Si está vacía, significa: no hay vacíos

#### NOMBRES_EN_FUENTE
- Qué significa: Todas las razones sociales distintas con que aparece el NIT (solo si hay más de una) · Origen: DIAN
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 256 valores distintos
- Si está vacía, significa: la empresa aparece con una sola razón social (97,5 % de las filas)

#### RAZON_SOCIAL_RUES
- Qué significa: Razón social en el registro mercantil · Origen: RUES
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 13.061 valores distintos
- Si está vacía, significa: la fuente no trae el dato (0,4 % de las filas)

#### TIPO_EXPORTADOR
- Qué significa: Persona jurídica (las personas naturales no tienen NIT publicado y no están en el directorio) · Origen: Calculado
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «Persona jurídica»
- Si está vacía, significa: no hay vacíos

#### CLASE_EXPORTADOR
- Qué significa: Clase más frecuente declarada (1 mixta, 2 privada, 3 pública) · Origen: DIAN
- Tipo: texto
- Unidad o formato: código
- Valores válidos: «2»; «3»; «1»
- Si está vacía, significa: no hay vacíos

#### CLASE_EXPORTADOR_DESC
- Qué significa: Descripción de la clase · Origen: catalogo_codigos
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «Privada»; «Pública»; «Economía mixta»
- Si está vacía, significa: no hay vacíos

#### CAMARA_COMERCIO
- Qué significa: Cámara de comercio de la matrícula principal (prioriza activa y renovada más recientemente) · Origen: RUES Confecámaras (c82u-588k)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 58 valores distintos
- Si está vacía, significa: la empresa no aparece en el RUES (0,4 % de las filas)

#### MATRICULA
- Qué significa: Número de matrícula mercantil · Origen: RUES
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 16.158 valores distintos
- Si está vacía, significa: la fuente no trae el dato (0,4 % de las filas)

#### CIIU_PRINCIPAL_RUES
- Qué significa: Actividad económica principal CIIU rev. 4 (4 dígitos) · Origen: RUES
- Tipo: texto
- Unidad o formato: código CIIU rev. 4 de 4 dígitos
- Valores válidos: 430 valores distintos
- Si está vacía, significa: la empresa no aparece en el RUES (0,4 % de las filas)

#### CIIU_SECUNDARIO_RUES
- Qué significa: Actividad económica secundaria CIIU (4 dígitos) · Origen: RUES
- Tipo: texto
- Unidad o formato: código CIIU rev. 4 de 4 dígitos
- Valores válidos: 468 valores distintos
- Si está vacía, significa: la empresa no registró actividad secundaria o no aparece en el RUES (20,3 % de las filas)

#### ORGANIZACION_JURIDICA
- Qué significa: Forma jurídica · Origen: RUES
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 20 valores distintos
- Si está vacía, significa: la fuente no trae el dato (0,4 % de las filas)

#### FECHA_MATRICULA
- Qué significa: Fecha de la matrícula mercantil · Origen: RUES (AAAAMMDD → fecha; "00000000" → NULL)
- Tipo: fecha
- Unidad o formato: AAAA-MM-DD
- Valores válidos: de 1926-04-19 a 2026-11-03
- Si está vacía, significa: la fuente no trae el dato (0,4 % de las filas)

#### ULTIMO_ANO_RENOVADO
- Qué significa: Último año de renovación de la matrícula · Origen: RUES
- Tipo: número
- Unidad o formato: —
- Valores válidos: de 0 a 2026
- Si está vacía, significa: la fuente no trae el dato (0,4 % de las filas)

#### ESTADO_MATRICULA
- Qué significa: Estado de la matrícula (ACTIVA, CANCELADA, …) · Origen: RUES
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «ACTIVA»; «MATRÍCULA NUEVA, CONSTITUCIÓN POR TRASLADO»; «CANCELADA»; «MATRÍCULA CANCELADA POR TRASLADO DE DOMICILIO»; «SIN ESTADO»; «MATRÍCULA CANCELADA POR FUSIÓN»; «NO COMPETENCIA DE LA CAMARA»; «NO ASIGNADO»
- Si está vacía, significa: la fuente no trae el dato (0,4 % de las filas)

#### TIENE_MATRICULA_ACTIVA_EN_ANTIOQUIA
- Qué significa: VERDADERO si tiene alguna matrícula activa en una cámara de Antioquia · Origen: RUES
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (2.830) o FALSO (10.428)
- Si está vacía, significa: la fuente no trae el dato (0,4 % de las filas)

#### COD_MPIO_DIAN_DIRECCION_PROPIA
- Qué significa: Municipio de la dirección DIAN usando solo direcciones compartidas por 5 NIT o menos (las demás suelen ser de agencias de aduanas) · Origen: Calculado (DIAN)
- Tipo: texto
- Unidad o formato: DIVIPOLA de 5 dígitos
- Valores válidos: 101 valores distintos
- Si está vacía, significa: todas sus direcciones DIAN las comparten más de 5 NIT (suelen ser de agencias de aduanas) (94,4 % de las filas)

#### MUNICIPIO_DIAN_DIRECCION_PROPIA
- Qué significa: Nombre del municipio anterior · Origen: DIVIPOLA
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 88 valores distintos
- Si está vacía, significa: todas sus direcciones DIAN las comparten más de 5 NIT (94,4 % de las filas)

#### DEPTO_DIAN_DIRECCION_PROPIA
- Qué significa: Departamento del municipio anterior · Origen: DIVIPOLA
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 26 valores distintos
- Si está vacía, significa: todas sus direcciones DIAN las comparten más de 5 NIT (94,4 % de las filas)

#### COD_DEPTO_ORIGEN_PRINCIPAL
- Qué significa: Departamento de origen con mayor FOB de la empresa · Origen: Calculado (DIAN)
- Tipo: texto
- Unidad o formato: DIVIPOLA de 2 dígitos (00 = departamentos varios)
- Valores válidos: 30 valores distintos
- Si está vacía, significa: no hay vacíos

#### DEPTO_ORIGEN_PRINCIPAL_MERCANCIA
- Qué significa: Nombre del departamento anterior · Origen: dim_departamento
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 30 valores distintos
- Si está vacía, significa: no hay vacíos

#### SECTOR_EXPORTADOR_PRINCIPAL
- Qué significa: Sector con mayor FOB: Minero-energético / Agrícola y agroindustrial (MADR) / Industria y otros · Origen: Calculado (dim_subpartida)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «Industria y otros»; «Agrícola y agroindustrial (MADR)»; «Minero-energético»
- Si está vacía, significa: no hay vacíos

#### PCT_FOB_MINERO_ENERGETICO
- Qué significa: % del FOB en subpartidas minero-energéticas (definición calibrada contra MinCIT NME) · Origen: Calculado
- Tipo: número
- Unidad o formato: porcentaje de 0 a 100
- Valores válidos: de 0,00 a 100,00
- Si está vacía, significa: no hay vacíos

#### PCT_FOB_AGRICOLA_MADR
- Qué significa: % del FOB en subpartidas agrícolas y agroindustriales según MinAgricultura · Origen: Calculado
- Tipo: número
- Unidad o formato: porcentaje de 0 a 100
- Valores válidos: de 0,00 a 100,00
- Si está vacía, significa: no hay vacíos

#### PRODUCTO_AGRICOLA_PRINCIPAL_MADR
- Qué significa: Producto agrícola con mayor FOB (p. ej. Café, Banano, Flores) · Origen: Calculado (MADR)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 253 valores distintos
- Si está vacía, significa: la empresa no exporta productos agrícolas (74,1 % de las filas)

#### FOB_USD_2024
- Qué significa: FOB en dólares 2024 (incluye sep-2024, cuya razón social vino enmascarada) · Origen: Calculado
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,50 a 10.228.807.360,98
- Si está vacía, significa: la empresa no exportó ese año (28,3 % de las filas)

#### FOB_USD_2025
- Qué significa: FOB en dólares 2025 · Origen: Calculado
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,13 a 8.763.560.533,61
- Si está vacía, significa: la empresa no exportó ese año (29,3 % de las filas)

#### FOB_USD_2026
- Qué significa: FOB en dólares 2026 (año en curso: llega hasta el último mes publicado, ver info_bd) · Origen: Calculado
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,01 a 7.886.015.530,63
- Si está vacía, significa: la empresa no exportó ese año (39,7 % de las filas)

#### FOB_USD_TOTAL
- Qué significa: FOB total de todo el periodo cubierto · Origen: Calculado
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,50 a 26.878.383.425,22
- Si está vacía, significa: no hay vacíos

#### FOB_USD_ORIGEN_ANTIOQUIA
- Qué significa: FOB de mercancía con origen Antioquia · Origen: Calculado
- Tipo: número
- Unidad o formato: dólares (USD)
- Valores válidos: de 0,00 a 2.689.943.635,90
- Si está vacía, significa: no hay vacíos

#### PCT_FOB_ORIGEN_ANTIOQUIA
- Qué significa: % del FOB de la empresa con origen Antioquia · Origen: Calculado
- Tipo: número
- Unidad o formato: porcentaje de 0 a 100
- Valores válidos: de 0,00 a 100,00
- Si está vacía, significa: no hay vacíos

#### PCT_FOB_DESTINO_ZONA_FRANCA
- Qué significa: % del FOB enviado a zonas francas colombianas · Origen: Calculado
- Tipo: número
- Unidad o formato: porcentaje de 0 a 100
- Valores válidos: de 0,00 a 100,00
- Si está vacía, significa: no hay vacíos

#### PESO_NETO_KGS_TOTAL
- Qué significa: Peso neto total exportado (kg) · Origen: Calculado
- Tipo: número
- Unidad o formato: kilogramos
- Valores válidos: de 0,00 a 74.824.230.459,28
- Si está vacía, significa: no hay vacíos

#### N_REGISTROS
- Qué significa: Número de registros (series) en hechos_exportaciones · Origen: Calculado
- Tipo: número
- Unidad o formato: conteo (entero)
- Valores válidos: de 1 a 184.293
- Si está vacía, significa: no hay vacíos

#### N_DECLARACIONES
- Qué significa: Número de declaraciones distintas (los registros sin formulario cuentan uno a uno) · Origen: Calculado
- Tipo: número
- Unidad o formato: conteo (entero)
- Valores válidos: de 1 a 57.161
- Si está vacía, significa: no hay vacíos

#### N_MESES_CON_EXPORTACION
- Qué significa: Meses con al menos una exportación · Origen: Calculado
- Tipo: número
- Unidad o formato: conteo (entero)
- Valores válidos: de 1 a 33
- Si está vacía, significa: no hay vacíos

#### PRIMER_MES
- Qué significa: Primer mes con exportación (AAAA-MM) · Origen: Calculado
- Tipo: texto
- Unidad o formato: AAAA-MM
- Valores válidos: 32 valores distintos
- Si está vacía, significa: no hay vacíos

#### ULTIMO_MES
- Qué significa: Último mes con exportación (AAAA-MM) · Origen: Calculado
- Tipo: texto
- Unidad o formato: AAAA-MM
- Valores válidos: 32 valores distintos
- Si está vacía, significa: no hay vacíos

#### N_PAISES_DESTINO
- Qué significa: Número de destinos distintos (las zonas francas cuentan como uno) · Origen: Calculado
- Tipo: número
- Unidad o formato: conteo (entero)
- Valores válidos: de 1 a 78
- Si está vacía, significa: no hay vacíos

#### TOP3_PAISES_DESTINO
- Qué significa: Tres destinos principales con su % del FOB · Origen: Calculado (dim_pais)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 7.199 valores distintos
- Si está vacía, significa: no hay vacíos

#### N_SUBPARTIDAS
- Qué significa: Número de subpartidas exportadas · Origen: Calculado
- Tipo: número
- Unidad o formato: conteo (entero)
- Valores válidos: de 1 a 729
- Si está vacía, significa: no hay vacíos

#### TOP5_SUBPARTIDAS
- Qué significa: Cinco subpartidas con mayor FOB · Origen: Calculado
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 9.132 valores distintos
- Si está vacía, significa: no hay vacíos

#### CAPITULO_ARANCEL_PRINCIPAL
- Qué significa: Capítulo arancelario (2 dígitos) de la subpartida principal · Origen: Calculado
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 84 valores distintos
- Si está vacía, significa: no hay vacíos

#### ADUANA_SALIDA_PRINCIPAL
- Qué significa: Aduana de salida más frecuente · Origen: Calculado
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 21 valores distintos
- Si está vacía, significa: no hay vacíos

#### MODO_TRANSPORTE_PRINCIPAL
- Qué significa: Modo de transporte más frecuente · Origen: Calculado
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «Marítimo»; «Aéreo»; «Terrestre (carretero)»; «Instalaciones Fijas»; «Vías navegables interiores»
- Si está vacía, significa: no hay vacíos

#### SS_MACROSECTOR
- Qué significa: Macrosector (solo empresas entre las 10.000 más grandes) · Origen: Supersociedades (6cat-2gcs)
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «MANUFACTURA»; «COMERCIO»; «SERVICIOS»; «AGROPECUARIO»; «MINERO»; «CONSTRUCCIÓN»
- Si está vacía, significa: la empresa no está entre las 10.000 más grandes de Supersociedades (73,5 % de las filas)

#### SS_CIIU
- Qué significa: CIIU reportado a Supersociedades (4 dígitos) · Origen: Supersociedades (formato homogeneizado)
- Tipo: texto
- Unidad o formato: código CIIU rev. 4 de 4 dígitos
- Valores válidos: 297 valores distintos
- Si está vacía, significa: la fuente no trae el dato (73,5 % de las filas)

#### SS_SUPERVISOR
- Qué significa: Superintendencia que la supervisa · Origen: Supersociedades
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «SUPERSOCIEDADES»; «SUPERTRANSPORTE»; «SUPERSALUD»; «SUPERFINANCIERA»; «SUPERSERVICIOS»; «SUPERVIGILANCIA»
- Si está vacía, significa: la fuente no trae el dato (73,5 % de las filas)

#### SS_DEPARTAMENTO_DOMICILIO
- Qué significa: Departamento del domicilio · Origen: Supersociedades
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 32 valores distintos
- Si está vacía, significa: la fuente no trae el dato (73,5 % de las filas)

#### SS_CIUDAD_DOMICILIO
- Qué significa: Ciudad del domicilio · Origen: Supersociedades
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: 187 valores distintos
- Si está vacía, significa: la fuente no trae el dato (73,5 % de las filas)

#### SS_INGRESOS_OPERACIONALES_BILLONES_COP
- Qué significa: Ingresos operacionales en billones de pesos (10^12) · Origen: Supersociedades
- Tipo: número
- Unidad o formato: pesos colombianos
- Valores válidos: de 0,01 a 100,59
- Si está vacía, significa: la fuente no trae el dato (73,5 % de las filas)

#### SS_TOTAL_ACTIVOS_BILLONES_COP
- Qué significa: Activos totales en billones de pesos (10^12) · Origen: Supersociedades
- Tipo: número
- Unidad o formato: pesos colombianos
- Valores válidos: de 0,00 a 198,11
- Si está vacía, significa: la fuente no trae el dato (73,5 % de las filas)

#### SS_ANO_CORTE
- Qué significa: Año de corte de las cifras de Supersociedades · Origen: Supersociedades
- Tipo: número
- Unidad o formato: —
- Valores válidos: de 2021 a 2025
- Si está vacía, significa: la fuente no trae el dato (73,5 % de las filas)

#### PROVEEDOR_ESTADO_SECOP_II
- Qué significa: VERDADERO si tiene contratos con entidades públicas en SECOP II · Origen: SECOP II (jbjy-vk9h)
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (1.724) o FALSO (11.581)
- Si está vacía, significa: no hay vacíos

#### SECOP_N_CONTRATOS
- Qué significa: Número de contratos en SECOP II · Origen: SECOP II
- Tipo: número
- Unidad o formato: conteo (entero)
- Valores válidos: de 1 a 1.564
- Si está vacía, significa: la empresa no tiene contratos en SECOP II (87,0 % de las filas)

#### SECOP_VALOR_CONTRATOS_COP
- Qué significa: Valor total de los contratos en pesos · Origen: SECOP II
- Tipo: número
- Unidad o formato: pesos colombianos
- Valores válidos: de 0,00 a 12.858.452.444.481.594,00
- Si está vacía, significa: la fuente no trae el dato (87,0 % de las filas)

#### SECOP_PRIMERA_FIRMA
- Qué significa: Fecha del primer contrato firmado · Origen: SECOP II
- Tipo: fecha
- Unidad o formato: AAAA-MM-DD
- Valores válidos: de 2015-09-09 a 2026-11-12
- Si está vacía, significa: la fuente no trae el dato (87,5 % de las filas)

#### SECOP_ULTIMA_FIRMA
- Qué significa: Fecha del último contrato firmado · Origen: SECOP II
- Tipo: fecha
- Unidad o formato: AAAA-MM-DD
- Valores válidos: de 2017-03-01 a 2026-11-14
- Si está vacía, significa: la fuente no trae el dato (87,5 % de las filas)

#### SECOP_ES_PYME
- Qué significa: Lo que declaró en SECOP II: Sí / No / Mixto. Única variable de tamaño disponible · Origen: SECOP II
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «No»; «Sí»; «Mixto»
- Si está vacía, significa: la empresa no tiene contratos en SECOP II (87,0 % de las filas)

#### SECOP_N_ENTIDADES
- Qué significa: Número de entidades contratantes · Origen: SECOP II
- Tipo: número
- Unidad o formato: conteo (entero)
- Valores válidos: de 1 a 259
- Si está vacía, significa: la fuente no trae el dato (87,0 % de las filas)

#### EN_DIRECTORIO_ENTRADA
- Qué significa: VERDADERO si el NIT estaba en el directorio del paso 7 (de ahí salen los atributos RUES, Supersociedades y SECOP) · Origen: Trazabilidad
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (13.305) o FALSO (0)
- Si está vacía, significa: no hay vacíos

#### FUENTE_DOMICILIO
- Qué significa: De dónde sale el domicilio usado para VINCULO_ANTIOQUIA · Origen: Calculado
- Tipo: texto
- Unidad o formato: texto libre
- Valores válidos: «RUES: cámara fuera de Antioquia»; «RUES: cámara de Antioquia»; «Sin RUES»; «Sin RUES; dirección DIAN propia en Antioquia»
- Si está vacía, significa: no hay vacíos

#### EXPORTADOR_2024_MIN_1000USD
- Qué significa: VERDADERO si exportó al menos USD 1.000 FOB en 2024 (umbral Analdex) · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (9.340) o FALSO (3.965)
- Si está vacía, significa: no hay vacíos

#### EXPORTADOR_2025_MIN_1000USD
- Qué significa: Ídem 2025 · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (9.226) o FALSO (4.079)
- Si está vacía, significa: no hay vacíos

#### EXPORTADOR_2026_MIN_1000USD
- Qué significa: Ídem 2026 (año en curso) · Origen: Calculado
- Tipo: verdadero / falso
- Unidad o formato: VERDADERO / FALSO
- Valores válidos: VERDADERO (7.896) o FALSO (5.409)
- Si está vacía, significa: no hay vacíos

## 4. Otras tablas

Las dimensiones (`dim_subpartida`, `dim_pais`, `dim_zona_franca`, `dim_departamento`, `dim_municipio`, `dim_aduana`, `dim_declarante`), `catalogo_codigos` y las vistas (`vw_exportaciones`, `vw_exportaciones_antioquia`, `vw_directorio_antioquia`, `vw_serie_mensual`, `vw_validacion_*`) están descritas columna por columna en [docs/diccionario_bd_depurada.csv](docs/diccionario_bd_depurada.csv) y en la tabla `diccionario_datos` de la BD.

_Generado el 2026-11-17._
