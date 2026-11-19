# Diccionario de la BD principal (capa analítica)

> Se genera con el paso 10 (`pipeline/p10_capa_analitica.py`) a partir de la tabla `diccionario_datos` de la BD principal. Las columnas heredadas de la BD depurada conservan su descripción original; el detalle de cada regla está en [bd_principal_capa_analitica.md](bd_principal_capa_analitica.md). Empieza por `vw_exportaciones`, la vista con la que se trabaja; las columnas van en el orden de la tabla.


## vw_exportaciones

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(todas las de hechos_analitica)` |  | Vista lista para analizar: la tabla de hechos de la BD principal con los nombres y atributos de las dimensiones y catálogos. Es el punto de partida de cualquier análisis | Vista |
| `ADUANA_DESPACHO, ADUANA_SALIDA, DEPTO_PROCEDENCIA, DEPTO_ORIGEN, MUNICIPIO_DIRECCION_DECLARADA` |  | Nombres de aduanas y territorios | dim_aduana, dim_departamento, dim_municipio |
| `ANIO_MES, TRIMESTRE` |  | Periodo en texto (AAAA-MM) y trimestre (AAAA-Tn) | Vista |
| `CAPITULO, PARTIDA, SUBPARTIDA_SA6, SECTOR_EXPORTACION, ES_MINERO_ENERGETICO, ES_AGRICOLA_MADR, PRODUCTO_AGRICOLA_MADR, TRADICION_AGRICOLA_MADR` |  | Clasificación del producto | dim_subpartida |
| `CERTIFICADO_ORIGEN, FORMA_PAGO_DESC, REGIMEN_CAN_DESC, TIPO_USUARIO_DESC, LUGAR_SALIDA` |  | Descripciones de los catálogos cat_* | Vista |
| `MODO_TRANSPORTE, MODALIDAD_EXPORTACION, UNIDAD_FISICA, CLASE_EXPORTADOR_DESC, RAZON_SOCIAL_DECLARANTE` |  | Descripciones de códigos | catalogo_codigos, dim_declarante |
| `PAIS_DESTINO, TIPO_DESTINO, ZONA_FRANCA_DESTINO, PAIS_BANDERA` |  | Nombres de destino y bandera | dim_pais, dim_zona_franca |
| `PESO_NETO_KGS_ANALISIS, PESO_BRUTO_KGS_ANALISIS, CANTIDAD_UNIDADES_FISICAS_ANALISIS` |  | Valor ajustado si existe; si no, el original. Usar para análisis de volumen | Vista |
| `PRECIO_USD_KG, PRECIO_USD_KG_ANALISIS, PRECIO_USD_UNIDAD_ANALISIS` |  | Precio unitario con las magnitudes originales y con las de análisis | Vista |
| `RAZON_SOCIAL, VINCULO_ANTIOQUIA, EMPRESA_ANTIOQUENA, ES_EXPORTADOR_ANTIOQUENO, CAMARA_COMERCIO, CIIU_PRINCIPAL_RUES, SECTOR_EXPORTADOR_PRINCIPAL` |  | Atributos del exportador (dim_exportador_analitica); banderas de Antioquia en FALSO para personas naturales | Vista |
| `ID_DECLARACION` |  | Formulario, o autorización de embarque (AE-) si falta, o el registro (R-) | Vista |
| `ES_VENTA_EXTERIOR` |  | VERDADERO si no va a zona franca colombiana ni tiene destino Colombia | Vista |
| `DEPTO_ORIGEN_ASIGNADO` |  | FALSO cuando el origen es 00 Departamentos varios | Vista |
| `ES_EXPORTACION_COMERCIAL` |  | Modalidades 198 y 199 (exportación definitiva con valor comercial) | Vista |
| `CIUDAD_DESTINATARIO_NORM` |  | Ciudad del comprador normalizada de forma aproximada (map_ciudad_destinatario) | Vista |

## hechos_analitica

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `ID_REGISTRO` | BIGINT | Llave única del registro (asignada en la depuración; la DIAN no trae una llave única) | Calculado |
| `PERIODO` | DATE | Mes de la exportación (primer día del mes) | DIAN |
| `ANIO` | SMALLINT | Año de la exportación | DIAN |
| `MES` | TINYINT | Mes de la exportación (1-12) | DIAN |
| `FECHA_DECLARACION` | DATE | Fecha de la declaración de exportación | DIAN FECHA_DECLARACION_EXPORTACION (AAAAMMDD → fecha) |
| `NUMERO_FORMULARIO` | VARCHAR | Número de la declaración de exportación (DEX). NULL en las exportaciones sin formulario (sobre todo hidrocarburos) | DIAN ("0" → NULL) |
| `NUMERO_SERIE` | INTEGER | Ítem o serie dentro de la declaración | DIAN |
| `TIPO_DESPACHO` | VARCHAR | Inicial / Corrección / Modificación. La base DIAN solo trae la versión vigente de cada declaración | DIAN (ortografía corregida) |
| `TIPO_DATOS` | VARCHAR | Definitivos al embarque / Definitivos después del embarque | DIAN (ortografía corregida) |
| `TIPO_EMBARQUE` | VARCHAR | Único / Fraccionado / Global con cargues parciales | DIAN (se usa la descripción; el código no era 1:1 con ella) |
| `NUM_DECLARACION_ANTERIOR` | VARCHAR | Declaración que la corrección o modificación reemplaza | DIAN ("0" → NULL) |
| `PERIODO_DECLARACION_ANTERIOR` | DATE | Mes de la declaración anterior | DIAN (AAAAMM → fecha) |
| `NUM_DECLARACION_PRECEDENTE` | VARCHAR | Declaración precedente (p. ej. importación temporal que se reexporta) | DIAN ("0" → NULL) |
| `PERIODO_DECLARACION_PRECEDENTE` | DATE | Mes de la declaración precedente | DIAN (AAAAMM → fecha) |
| `NUM_AUTORIZACION_EMBARQUE` | VARCHAR | Número de la solicitud de autorización de embarque | DIAN NUM_SOLICITUD_AUTO_EMBARQUE |
| `PERIODO_AUTORIZACION_EMBARQUE` | DATE | Mes de la solicitud de autorización de embarque (562 registros traen meses anteriores a 2023) | DIAN (AAAAMM → fecha) |
| `NIT_EXPORTADOR` | VARCHAR | NIT del exportador sin dígito de verificación ni ceros a la izquierda. NULL = persona natural (la DIAN oculta su documento). Llave hacia dim_exportador | DIAN |
| `TIPO_IDENTIFICACION` | VARCHAR | Código del tipo de documento (1 persona natural, 2 NIT). Ver catalogo_codigos | DIAN TIPO_IDENT |
| `ES_PERSONA_NATURAL` | BOOLEAN | VERDADERO si el exportador no tiene NIT publicado (la DIAN anonimiza a las personas naturales). Se define por el NIT y no por la razón social, que falla en sep-2024 | Calculado |
| `FLAG_RAZON_SOCIAL_ENMASCARADA` | BOOLEAN | VERDADERO si la DIAN publicó "PERSONA NATURAL" o dejó vacía la razón social aunque la línea trae NIT de empresa (sep-2024). La línea se atribuye a la empresa por el NIT | Calculado |
| `CLASE_EXPORTADOR` | VARCHAR | Clase declarada: 1 economía mixta, 2 privada, 3 pública. Ver catalogo_codigos | DIAN |
| `TIPO_USUARIO` | VARCHAR | Código DIAN del tipo de usuario aduanero (sin descripción en la fuente; 36 = 99,9 % de los registros) | DIAN |
| `DIRECCION_DECLARADA` | VARCHAR | Dirección del exportador declarada a la DIAN. OJO: muchas veces es la de la agencia de aduanas. Vacía para personas naturales (dato personal) | DIAN DIREC_EXPORTADOR (limpia) |
| `COD_MPIO_DIRECCION_DECLARADA` | VARCHAR | Municipio DIVIPOLA (5 dígitos) de la dirección declarada. Llave hacia dim_municipio | DIAN COD_DPTO_EXPORTADOR (en realidad es el municipio) |
| `DIRECCION_DECLARADA_EN_ANTIOQUIA` | BOOLEAN | VERDADERO si la dirección declarada está en Antioquia | Calculado (paso 4) |
| `NIT_DECLARANTE` | VARCHAR | NIT de la agencia de aduanas o declarante. Llave hacia dim_declarante | DIAN |
| `CIUDAD_DESTINATARIO` | VARCHAR | Ciudad del destinatario, en mayúsculas. Su razón social y su domicilio no se publican porque pueden ser de una persona | DIAN (limpia, entidades HTML decodificadas) |
| `COD_PAIS_DESTINO` | VARCHAR | País destino final ISO 3166 alfa-3; "XCF" = zona franca colombiana. Llave hacia dim_pais | DIAN COD_PAIS_DESTINO_ALF (zonas francas corregidas) |
| `ES_DESTINO_ZONA_FRANCA` | BOOLEAN | Destino en zona franca colombiana (XCF); 5 líneas de Namibia que venían nulas pasan a FALSO | Capa analítica, correcciones |
| `COD_ZONA_FRANCA_DESTINO` | VARCHAR | Código de la zona franca de destino. Llave hacia dim_zona_franca | DIAN COD_PAIS_DESTINO_NUM |
| `COD_ADUANA_DESPACHO` | VARCHAR | Aduana donde se presentó la declaración. Llave hacia dim_aduana | DIAN (2 dígitos) |
| `COD_ADUANA_SALIDA` | VARCHAR | Aduana por donde salió la mercancía. Llave hacia dim_aduana | DIAN (2 dígitos) |
| `COD_LUGAR_SALIDA` | VARCHAR | Puerto, aeropuerto o paso de frontera de salida (código alfabético) | DIAN COD_LUG_SALIDA_ALF |
| `COD_DEPTO_PROCEDENCIA` | VARCHAR | Departamento DIVIPOLA desde donde se despachó la mercancía. Llave hacia dim_departamento | DIAN COD_REGION_PROCEDENCIA |
| `COD_DEPTO_ORIGEN` | VARCHAR | Departamento DIVIPOLA donde se produjo la mercancía ("00" = departamentos varios). Llave hacia dim_departamento | DIAN COD_REGION_ORIGEN |
| `ORIGEN_MERCANCIA_ANTIOQUIA` | BOOLEAN | VERDADERO si la mercancía es de origen Antioquia (COD_DEPTO_ORIGEN = 05) | Calculado (paso 4) |
| `COD_MODO_TRANSPORTE` | VARCHAR | Modo de transporte. Ver catalogo_codigos (MODO_TRANSPORTE) | DIAN |
| `COD_PAIS_BANDERA` | VARCHAR | País de la bandera del medio de transporte, ISO alfa-3 ("ND" = no declarado). Llave hacia dim_pais | DIAN (2024 alfa-2 convertido a alfa-3) |
| `COD_MODALIDAD_EXPORTACION` | VARCHAR | Modalidad de exportación (3 dígitos). Ver catalogo_codigos | DIAN (ceros a la izquierda homogéneos) |
| `COD_REGIMEN_CAN` | VARCHAR | Código de régimen Comunidad Andina (sin descripción en la fuente) | DIAN |
| `FORMA_PAGO` | VARCHAR | Código de forma de pago (sin descripción en la fuente) | DIAN |
| `TIPO_CERTIFICADO_ORIGEN` | VARCHAR | Código del tipo de certificado de origen (sin descripción en la fuente) | DIAN |
| `SISTEMAS_ESPECIALES` | BOOLEAN | VERDADERO si la operación usa Sistemas Especiales de Importación-Exportación (Plan Vallejo) | DIAN (SI/NO → booleano) |
| `EXPORTACION_EN_TRANSITO` | BOOLEAN | VERDADERO si es exportación en tránsito | DIAN (SI/NO → booleano) |
| `COD_MONEDA_TRANSACCION` | VARCHAR | Moneda de la transacción (ISO 4217) | DIAN |
| `SUBPARTIDA` | VARCHAR | Subpartida arancelaria a 10 dígitos con cero inicial. Llave hacia dim_subpartida | DIAN |
| `COD_UNIDAD_FISICA` | VARCHAR | Unidad de la cantidad física. Ver catalogo_codigos (UNIDAD_FISICA) | DIAN COD_UNIDAD_FISICA_ALF |
| `CANTIDAD_UNIDADES_FISICAS` | DOUBLE | Cantidad en la unidad física declarada | DIAN |
| `PESO_BRUTO_KGS` | DOUBLE | Peso bruto en kilogramos | DIAN |
| `PESO_NETO_KGS` | DOUBLE | Peso neto en kilogramos | DIAN |
| `VALOR_FOB_USD` | DOUBLE | Valor FOB en dólares (medida principal) | DIAN |
| `VALOR_FOB_COP` | DOUBLE | Valor FOB en pesos colombianos | DIAN VALOR_FOB_PESOS |
| `VALOR_AGREGADO_NACIONAL_USD` | DOUBLE | Valor agregado nacional de la serie en dólares | DIAN VLR_SERIE_AGREGADO_NAL_USD |
| `VALOR_FLETES_USD` | DOUBLE | Fletes de la serie en dólares | DIAN VALOR_SERIE_FLETES_USD |
| `VALOR_SEGUROS_USD` | DOUBLE | Seguros de la serie en dólares | DIAN VALOR_SERIE_SEGUROS_USD |
| `VALOR_OTROS_GASTOS_USD` | DOUBLE | Otros gastos de la serie en dólares | DIAN VLR_SERIE_OTROS_GASTOS_USD |
| `FLAG_PESO_CERO` | BOOLEAN | VERDADERO si el peso neto o bruto viene en cero (dato a revisar) | Calculado |
| `FLAG_REGISTRO_IDENTICO` | BOOLEAN | VERDADERO en 10 registros idénticos en todo a otro (sin número de formulario). Se conservan porque las cifras oficiales los incluyen; para excluirlos: WHERE NOT FLAG_REGISTRO_IDENTICO | Calculado |
| `ARCHIVO_FUENTE` | VARCHAR | Archivo mensual DIAN del que proviene el registro | Trazabilidad |
| `NIVEL_REFERENCIA_PRECIO_KG` | VARCHAR | Grupo de referencia del precio por kilo (exportaciones comerciales): SUBPARTIDA o SA6; nulo si no hay referencia | Capa analítica, atípicos y ajustes |
| `RAZON_PRECIO_KG_VS_MEDIANA` | FLOAT | Precio por kilo dividido por la mediana de su grupo (1 = igual a la mediana) | Capa analítica, atípicos y ajustes |
| `FLAG_PRECIO_KG_ATIPICO` | BOOLEAN | Precio por kilo fuera de [Q1 - 3 RIC, Q3 + 3 RIC] en logaritmo; nulo si no se pudo evaluar | Capa analítica, atípicos y ajustes |
| `NIVEL_REFERENCIA_PRECIO_UNIDAD` | VARCHAR | Grupo de referencia del precio por unidad física (misma unidad): SUBPARTIDA o SA6 | Capa analítica, atípicos y ajustes |
| `RAZON_PRECIO_UNIDAD_VS_MEDIANA` | FLOAT | Precio por unidad dividido por la mediana de su grupo | Capa analítica, atípicos y ajustes |
| `FLAG_CANTIDAD_ATIPICA` | BOOLEAN | Precio por unidad física atípico: delata cantidades imposibles; nulo si no se pudo evaluar | Capa analítica, atípicos y ajustes |
| `FLAG_ATIPICO` | BOOLEAN | VERDADERO si la línea tiene precio por kilo o cantidad atípicos | Capa analítica, atípicos y ajustes |
| `FLAG_POSIBLE_ERROR_FOB` | BOOLEAN | Precio por kilo y por unidad extremos a la vez: posible error de FOB o de varios campos; no se ajusta | Capa analítica, atípicos y ajustes |
| `PESO_NETO_KGS_AJUSTADO` | DOUBLE | Peso reconstruido (desde la cantidad o desde el FOB) en exportaciones comerciales con precio por kilo 100 veces o más lejos de la mediana o peso 0; nulo si no se ajustó | Capa analítica, atípicos y ajustes |
| `PESO_BRUTO_KGS_AJUSTADO` | DOUBLE | Peso neto ajustado × mediana bruto/neto del grupo; nulo si no se ajustó | Capa analítica, atípicos y ajustes |
| `CANTIDAD_UNIDADES_FISICAS_AJUSTADA` | DOUBLE | Cantidad reconstruida (desde el peso o desde el FOB) en exportaciones comerciales con precio por unidad 100 veces o más lejos de la mediana | Capa analítica, atípicos y ajustes |
| `METODO_AJUSTE` | VARCHAR | Peso desde la cantidad, peso desde el FOB, cantidad desde el peso o cantidad desde el FOB; nulo si no se ajustó | Capa analítica, atípicos y ajustes |

## dim_exportador_analitica

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `RANKING_NACIONAL_FOB` | BIGINT | Posición por FOB total del periodo entre todas las empresas exportadoras | Calculado |
| `RANKING_ANTIOQUIA_FOB` | BIGINT | Posición por FOB total entre los exportadores antioqueños (VINCULO A o B) | Calculado |
| `NIT` | VARCHAR | NIT sin dígito de verificación ni ceros a la izquierda (llave) | DIAN |
| `RAZON_SOCIAL` | VARCHAR | Razón social canónica: la más reciente publicada por la DIAN; si la DIAN nunca la publicó, la del RUES | DIAN (limpia) / RUES |
| `VINCULO_ANTIOQUIA` | VARCHAR | A = matrícula principal en cámara de comercio de Antioquia (o, sin RUES, dirección DIAN propia en Antioquia); B = domicilio fuera pero su mercancía es principalmente de origen Antioquia; C = solo parte de su mercancía es de Antioquia; D = sin relación | Calculado (RUES + DIAN), regla de docs/metodologia.md |
| `EMPRESA_ANTIOQUENA` | BOOLEAN | VERDADERO si VINCULO_ANTIOQUIA = A | Calculado |
| `ES_EXPORTADOR_ANTIOQUENO` | BOOLEAN | VERDADERO si VINCULO_ANTIOQUIA es A o B | Calculado |
| `NOMBRES_EN_FUENTE` | VARCHAR | Todas las razones sociales distintas con que aparece el NIT (solo si hay más de una) | DIAN |
| `RAZON_SOCIAL_RUES` | VARCHAR | Razón social en el registro mercantil | RUES |
| `CLASE_EXPORTADOR` | VARCHAR | Clase más frecuente declarada (1 mixta, 2 privada, 3 pública) | DIAN |
| `CLASE_EXPORTADOR_DESC` | VARCHAR | Descripción de la clase | catalogo_codigos |
| `CAMARA_COMERCIO` | VARCHAR | Cámara de comercio de la matrícula principal (prioriza activa y renovada más recientemente) | RUES Confecámaras (c82u-588k) |
| `MATRICULA` | VARCHAR | Número de matrícula mercantil | RUES |
| `CIIU_PRINCIPAL_RUES` | VARCHAR | Actividad económica principal CIIU rev. 4 (4 dígitos) | RUES |
| `CIIU_SECUNDARIO_RUES` | VARCHAR | Actividad económica secundaria CIIU (4 dígitos) | RUES |
| `ORGANIZACION_JURIDICA` | VARCHAR | Forma jurídica | RUES |
| `FECHA_MATRICULA` | DATE | Fecha de la matrícula mercantil | RUES (AAAAMMDD → fecha; "00000000" → NULL) |
| `ULTIMO_ANO_RENOVADO` | SMALLINT | Último año de renovación de la matrícula | RUES |
| `ESTADO_MATRICULA` | VARCHAR | Estado de la matrícula (ACTIVA, CANCELADA, …) | RUES |
| `TIENE_MATRICULA_ACTIVA_EN_ANTIOQUIA` | BOOLEAN | VERDADERO si tiene alguna matrícula activa en una cámara de Antioquia | RUES |
| `COD_MPIO_DIAN_DIRECCION_PROPIA` | VARCHAR | Municipio de la dirección DIAN usando solo direcciones compartidas por 5 NIT o menos (las demás suelen ser de agencias de aduanas) | Calculado (DIAN) |
| `MUNICIPIO_DIAN_DIRECCION_PROPIA` | VARCHAR | Nombre del municipio anterior | DIVIPOLA |
| `DEPTO_DIAN_DIRECCION_PROPIA` | VARCHAR | Departamento del municipio anterior | DIVIPOLA |
| `COD_DEPTO_ORIGEN_PRINCIPAL` | VARCHAR | Departamento de origen con mayor FOB de la empresa | Calculado (DIAN) |
| `DEPTO_ORIGEN_PRINCIPAL_MERCANCIA` | VARCHAR | Nombre del departamento anterior | dim_departamento |
| `SECTOR_EXPORTADOR_PRINCIPAL` | VARCHAR | Sector con mayor FOB: Minero-energético / Agrícola y agroindustrial (MADR) / Industria y otros | Calculado (dim_subpartida) |
| `PCT_FOB_MINERO_ENERGETICO` | DOUBLE | % del FOB en subpartidas minero-energéticas (definición calibrada contra MinCIT NME) | Calculado |
| `PCT_FOB_AGRICOLA_MADR` | DOUBLE | % del FOB en subpartidas agrícolas y agroindustriales según MinAgricultura | Calculado |
| `PRODUCTO_AGRICOLA_PRINCIPAL_MADR` | VARCHAR | Producto agrícola con mayor FOB (p. ej. Café, Banano, Flores) | Calculado (MADR) |
| `FOB_USD_2024` | DOUBLE | FOB en dólares 2024 (incluye sep-2024, cuya razón social vino enmascarada) | Calculado |
| `FOB_USD_2025` | DOUBLE | FOB en dólares 2025 | Calculado |
| `FOB_USD_2026` | DOUBLE | FOB en dólares 2026 (año en curso: llega hasta el último mes publicado, ver info_bd) | Calculado |
| `FOB_USD_TOTAL` | DOUBLE | FOB total de todo el periodo cubierto | Calculado |
| `FOB_USD_ORIGEN_ANTIOQUIA` | DOUBLE | FOB de mercancía con origen Antioquia | Calculado |
| `PCT_FOB_ORIGEN_ANTIOQUIA` | DOUBLE | % del FOB de la empresa con origen Antioquia | Calculado |
| `PCT_FOB_DESTINO_ZONA_FRANCA` | DOUBLE | % del FOB enviado a zonas francas colombianas | Calculado |
| `PESO_NETO_KGS_TOTAL` | DOUBLE | Peso neto total exportado (kg) | Calculado |
| `N_REGISTROS` | BIGINT | Número de registros (series) en hechos_exportaciones | Calculado |
| `N_DECLARACIONES` | BIGINT | Número de declaraciones distintas (los registros sin formulario cuentan uno a uno) | Calculado |
| `N_MESES_CON_EXPORTACION` | BIGINT | Meses con al menos una exportación | Calculado |
| `PRIMER_MES` | VARCHAR | Primer mes con exportación (AAAA-MM) | Calculado |
| `ULTIMO_MES` | VARCHAR | Último mes con exportación (AAAA-MM) | Calculado |
| `N_PAISES_DESTINO` | BIGINT | Número de destinos distintos (las zonas francas cuentan como uno) | Calculado |
| `TOP3_PAISES_DESTINO` | VARCHAR | Tres destinos principales con su % del FOB | Calculado (dim_pais) |
| `N_SUBPARTIDAS` | BIGINT | Número de subpartidas exportadas | Calculado |
| `TOP5_SUBPARTIDAS` | VARCHAR | Cinco subpartidas con mayor FOB | Calculado |
| `CAPITULO_ARANCEL_PRINCIPAL` | VARCHAR | Capítulo arancelario (2 dígitos) de la subpartida principal | Calculado |
| `ADUANA_SALIDA_PRINCIPAL` | VARCHAR | Aduana de salida más frecuente | Calculado |
| `MODO_TRANSPORTE_PRINCIPAL` | VARCHAR | Modo de transporte más frecuente | Calculado |
| `SS_MACROSECTOR` | VARCHAR | Macrosector (solo empresas entre las 10.000 más grandes) | Supersociedades (6cat-2gcs) |
| `SS_CIIU` | VARCHAR | CIIU reportado a Supersociedades (4 dígitos) | Supersociedades (formato homogeneizado) |
| `SS_SUPERVISOR` | VARCHAR | Superintendencia que la supervisa | Supersociedades |
| `SS_DEPARTAMENTO_DOMICILIO` | VARCHAR | Departamento del domicilio | Supersociedades |
| `SS_CIUDAD_DOMICILIO` | VARCHAR | Ciudad del domicilio | Supersociedades |
| `SS_INGRESOS_OPERACIONALES_BILLONES_COP` | DOUBLE | Ingresos operacionales en billones de pesos (10^12) | Supersociedades |
| `SS_TOTAL_ACTIVOS_BILLONES_COP` | DOUBLE | Activos totales en billones de pesos (10^12) | Supersociedades |
| `SS_ANO_CORTE` | SMALLINT | Año de corte de las cifras de Supersociedades | Supersociedades |
| `PROVEEDOR_ESTADO_SECOP_II` | BOOLEAN | VERDADERO si tiene contratos con entidades públicas en SECOP II | SECOP II (jbjy-vk9h) |
| `SECOP_N_CONTRATOS` | INTEGER | Número de contratos en SECOP II | SECOP II |
| `SECOP_VALOR_CONTRATOS_COP` | DOUBLE | Valor total de los contratos en pesos | SECOP II |
| `SECOP_PRIMERA_FIRMA` | DATE | Fecha del primer contrato firmado | SECOP II |
| `SECOP_ULTIMA_FIRMA` | DATE | Fecha del último contrato firmado | SECOP II |
| `SECOP_ES_PYME` | VARCHAR | Lo que declaró en SECOP II: Sí / No / Mixto. Única variable de tamaño disponible | SECOP II |
| `SECOP_N_ENTIDADES` | INTEGER | Número de entidades contratantes | SECOP II |
| `FUENTE_DOMICILIO` | VARCHAR | De dónde sale el domicilio usado para VINCULO_ANTIOQUIA | Calculado |
| `EXPORTADOR_2024_MIN_1000USD` | BOOLEAN | VERDADERO si exportó al menos USD 1.000 FOB en 2024 (umbral Analdex) | Calculado |
| `EXPORTADOR_2025_MIN_1000USD` | BOOLEAN | Ídem 2025 | Calculado |
| `EXPORTADOR_2026_MIN_1000USD` | BOOLEAN | Ídem 2026 (año en curso) | Calculado |
| `FLAG_SECOP_VALOR_INVALIDO` | BOOLEAN | El total SECOP superaba COP 100 billones y se dejó nulo | Capa analítica, directorio |
| `SS_CIFRAS_RECIENTES` | BOOLEAN | Año de corte de Supersociedades 2024 o 2025 | Capa analítica, directorio |
| `SS_FACTOR_IPC_A_DIC2025` | DOUBLE | Factor de inflación (IPC dic-dic) desde el año de corte hasta diciembre de 2025 | Capa analítica, directorio |
| `SS_INGRESOS_BILLONES_COP_DIC2025` | DOUBLE | Ingresos operacionales en billones de pesos de diciembre de 2025 (comparables entre empresas) | Capa analítica, directorio |
| `SS_ACTIVOS_BILLONES_COP_DIC2025` | DOUBLE | Activos totales en billones de pesos de diciembre de 2025 | Capa analítica, directorio |
| `SS_INTENSIDAD_EXPORTADORA_PCT` | DOUBLE | FOB del año de corte × tasa DIAN del año / ingresos operacionales × 100 (solo cortes 2024 y 2025) | Capa analítica, directorio |
| `N_RAZONES_SOCIALES_DIAN` | BIGINT | Razones sociales distintas con que aparece en la DIAN en 2024-2026 | Capa analítica, directorio |
| `TIPO_CAMBIO_RAZON_SOCIAL` | VARCHAR | Solo formato, cambió de forma jurídica, adoptó o dejó C.I. o BIC, entró en liquidación o cambió de nombre | Capa analítica, directorio |
| `ES_COMERCIALIZADORA_INTERNACIONAL` | BOOLEAN | La razón social DIAN o RUES incluye C.I. o Comercializadora Internacional | Capa analítica, directorio |
| `ES_TRASLADO_DOMICILIO` | BOOLEAN | Matrícula RUES constituida por traslado de domicilio desde otra cámara | Capa analítica, directorio |
| `ANIO_MATRICULA` | BIGINT | Año de la matrícula vigente (para traslados, el año del traslado) | Capa analítica, directorio |
| `TRASLADO_EN_PERIODO` | BOOLEAN | Traslado de domicilio desde enero de 2024 | Capa analítica, directorio |
| `MATRICULA_POSTERIOR_A_PRIMERA_EXPORTACION` | BOOLEAN | La matrícula vigente es posterior a su primer mes exportador en la base | Capa analítica, directorio |

## panel_exportador_mes

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | Una fila por NIT y mes con exportaciones | Capa analítica |

## exportador_pais

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | FOB, participación y ranking de cada país en cada NIT | Capa analítica |

## exportador_subpartida

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | FOB, participación y ranking de cada subpartida en cada NIT | Capa analítica |

## dim_subpartida

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `SUBPARTIDA` | VARCHAR | Subpartida arancelaria 10 dígitos (llave) | DIAN |
| `CAPITULO` | VARCHAR | Capítulo del arancel (2 dígitos) | Calculado |
| `PARTIDA` | VARCHAR | Partida (4 dígitos) | Calculado |
| `SUBPARTIDA_SA6` | VARCHAR | Subpartida del Sistema Armonizado a 6 dígitos (comparable internacionalmente) | Calculado |
| `SECTOR_EXPORTACION` | VARCHAR | Minero-energético / Agrícola y agroindustrial (MADR) / Industria y otros | Paso 6: MinCIT + MADR |
| `ES_MINERO_ENERGETICO` | BOOLEAN | Capítulos 26-27, ferroníquel 720260, oro 7108, plata 7106, platino 7110, desperdicios 7112 y piedras 7103 (calibrado contra MinCIT NME, error trimestral < 0,25 %) | Paso 6: MinCIT vwqt-xc3z |
| `ES_AGRICOLA_MADR` | BOOLEAN | Subpartida clasificada como agrícola/agroindustrial por MinAgricultura | Paso 6: MADR rfip-pkv5 y 5fct-ib9u |
| `PRODUCTO_AGRICOLA_MADR` | VARCHAR | Producto agrícola MADR | MADR |
| `TRADICION_AGRICOLA_MADR` | VARCHAR | Tradicional / No tradicional | MADR |
| `DESCRIPCION_PARTIDA_MADR` | VARCHAR | Descripción de la subpartida (solo agrícolas; la base DIAN no trae descripciones) | MADR |

## dim_pais

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `COD_PAIS` | VARCHAR | ISO 3166 alfa-3 (llave); XCF = zona franca colombiana; ND = no declarado | DIAN + ISO 3166 |
| `PAIS` | VARCHAR | Nombre en español (nomenclatura M49 que usa la DIAN desde 2025) | DIAN |
| `COD_ISO2` | VARCHAR | ISO 3166 alfa-2 | ISO 3166 (pycountry) |
| `COD_NUMERICO_M49` | VARCHAR | Código numérico ISO 3166 / M49 | ISO 3166 (pycountry) |
| `TIPO_DESTINO` | VARCHAR | País / Zona franca colombiana / Colombia (destino nacional) / No declarado | Calculado |
| `APARECE_COMO_DESTINO` | BOOLEAN | VERDADERO si aparece como país destino | Calculado |
| `APARECE_COMO_BANDERA` | BOOLEAN | VERDADERO si aparece como bandera del transporte | Calculado |

## dim_departamento

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `COD_DEPTO` | VARCHAR | Código DIVIPOLA de 2 dígitos (llave); 00 = departamentos varios (código DIAN) | DIVIPOLA |
| `DEPARTAMENTO` | VARCHAR | Nombre oficial | DIVIPOLA |
| `ES_ANTIOQUIA` | BOOLEAN | VERDADERO para 05 | Calculado |

## dim_municipio

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `COD_MPIO` | VARCHAR | Código DIVIPOLA de 5 dígitos (llave) | DIVIPOLA |
| `MUNICIPIO` | VARCHAR | Nombre oficial | DIVIPOLA |
| `COD_DEPTO` | VARCHAR | Departamento (llave hacia dim_departamento) | DIVIPOLA |

## map_ciudad_destinatario

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | Ciudad original + país → ciudad normalizada | Capa analítica |

## cat_* y catalogo_codigos

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | Un catálogo por dominio con llave CODIGO; catalogo_codigos es la vista que los une | Capa analítica |

## cat_certificado_origen

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de TIPO_CERTIFICADO_ORIGEN: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## cat_clase_exportador

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de CLASE_EXPORTADOR: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## cat_forma_pago

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de FORMA_PAGO: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## cat_lugar_salida

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de LUGAR_SALIDA: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## cat_modalidad_exportacion

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de MODALIDAD_EXPORTACION: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## cat_modo_transporte

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de MODO_TRANSPORTE: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## cat_regimen_can

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de COD_REGIMEN_CAN: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## cat_tipo_identificacion

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de TIPO_IDENTIFICACION: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## cat_tipo_usuario

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de TIPO_USUARIO: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## cat_unidad_fisica

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(tabla)` |  | Catálogo de UNIDAD_FISICA: CODIGO (llave), DESCRIPCION, FUENTE, CONFIANZA y NOTA | Capa analítica, catálogos |

## diccionario_datos

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(metadatos)` |  | Este diccionario: tabla, columna, tipo, descripción y origen o regla | Trazabilidad |

## dim_aduana

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `COD_ADUANA` | VARCHAR | Código DIAN de la aduana, 2 dígitos (llave) | DIAN |
| `ADUANA` | VARCHAR | Nombre de la dirección seccional | DIAN (limpio) |

## dim_declarante

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `NIT_DECLARANTE` | VARCHAR | NIT de la agencia de aduanas o declarante (llave) | DIAN |
| `RAZON_SOCIAL_DECLARANTE` | VARCHAR | Razón social más reciente | DIAN (limpia) |
| `N_VARIANTES_NOMBRE` | BIGINT | Cuántas grafías distintas tenía en la fuente | Calculado |

## dim_zona_franca

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `COD_ZONA_FRANCA` | VARCHAR | Código DIAN de la zona franca (llave) | DIAN |
| `ZONA_FRANCA` | VARCHAR | Nombre más reciente | DIAN |
| `NOMBRES_EN_FUENTE` | VARCHAR | Nombres con que aparece (2024 en mayúsculas, 2025+ abreviado) | DIAN |

## info_capa

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | Ficha de la capa | Capa analítica |

## log_depuracion

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(log)` |  | Cada regla de limpieza aplicada, filas y FOB afectados | Trazabilidad |

## log_preparacion

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | Cada regla de la capa con filas y FOB afectados | Capa analítica |

## ref_dane_publicaciones

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | Totales oficiales del DANE para el cuadre (incluye enero-septiembre de 2026) | Capa analítica |

## ref_madr_agricola_anual

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(referencia)` |  | Exportaciones agrícolas oficiales nacional y Antioquia (millones USD) y meses cubiertos | MADR datos.gov.co rfip-pkv5 |

## ref_mincit_trimestral

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(referencia)` |  | Exportaciones totales y no minero-energéticas oficiales (millones USD) | MinCIT datos.gov.co vwqt-xc3z |

## relaciones_llaves

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | Cada llave primaria y foránea: declarada o validada, con filas huérfanas | Capa analítica |

## vw_ciudad_comprador_por_completar

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | NIT con líneas cuya ciudad de comprador no es confiable | Capa analítica |

## vw_directorio_antioquia

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(igual a dim_exportador)` |  | Exportadores antioqueños (VINCULO A o B) ordenados por ranking (equivale a directorio_exportadores_antioquenos) | Vista |

## vw_exportaciones_antioquia

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(igual a vw_exportaciones)` |  | Registros con mercancía de origen Antioquia o de exportadores antioqueños (equivale a exportaciones_antioquia/) | Vista |

## vw_exportaciones_origen_asignado

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | vw_exportaciones sin 00 Departamentos varios (análisis regional) | Capa analítica |

## vw_serie_mensual

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(serie)` |  | Serie mensual de FOB y número de exportadores: Antioquia por origen y por empresa, nacional, sin minero-energético, agrícola y a zonas francas | Vista |
| `FOB_MUSD_VENTA_EXTERIOR, FOB_MUSD_ORIGEN_ASIGNADO, PESO_NETO_MILES_T_ANALISIS` |  | Nuevas en la BD principal: FOB al exterior (sin zonas francas), FOB con departamento de origen asignado y peso neto de análisis (con los ajustes) en miles de toneladas. Las demás columnas son las mismas de la BD depurada | Capa analítica |

## vw_validacion_dane

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | Base frente a los totales del DANE | Capa analítica |

## vw_validacion_madr

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(validación)` |  | FOB agrícola nacional y de Antioquia por año frente a MinAgricultura, en los mismos meses que cubre la fuente | Vista + ref_madr_agricola_anual |

## vw_validacion_mincit

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(validación)` |  | FOB total y no minero-energético por trimestre frente a la serie oficial de MinCIT | Vista + ref_mincit_trimestral |

## vw_ventas_exterior

| Columna | Tipo | Descripción | Origen o regla |
|---|---|---|---|
| `(objeto)` |  | vw_exportaciones sin zonas francas ni destino Colombia | Capa analítica |
