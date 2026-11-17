# Metodología

## 1. Unidad de análisis

- **Línea de declaración** (parquet transaccional). Es una fila de las bases estadísticas de exportaciones de la DIAN, que corresponde a un ítem (subpartida) de una declaración de exportación. La DIAN entrega las bases ya validadas y procesadas, con las correcciones incorporadas.
- **Empresa** (directorio). Una fila por NIT de persona jurídica. Las personas naturales llegan anonimizadas por la DIAN, con razón social "PERSONA NATURAL" y sin NIT, así que solo aparecen en el parquet.

## 2. Cómo se definió "empresa antioqueña"

En la base DIAN, `DIREC_EXPORTADOR` y `COD_DPTO_EXPORTADOR` muchas veces traen la dirección de la **agencia de aduanas** y no la de la empresa. Una sola dirección de Bogotá aparece en 1.183 NIT distintos, y una de Medellín en más de 500. Si se filtra por ese campo, quedan empresas de Bogotá clasificadas como de Medellín, como Drummond o Parex.

Por eso el domicilio se toma del **RUES** (Confecámaras): la cámara de comercio de la matrícula principal, sin contar sucursales ni agencias. Si una empresa tiene varias matrículas se prioriza la ACTIVA. Después va la NUEVA POR TRASLADO: cuando una empresa cambió de domicilio, el RUES deja la matrícula vieja cancelada y una nueva con la misma fecha. Por último, la que se renovó más recientemente. La dirección DIAN solo sirve de respaldo para los pocos NIT sin RUES, y únicamente si no la comparten más de 5 NIT.

| Vínculo | Regla |
|---|---|
| **A. Empresa antioqueña** | Matrícula principal en las cámaras de Medellín para Antioquia, Aburrá Sur, Oriente Antioqueño, Magdalena Medio o Urabá |
| **B. Exportador de mercancía antioqueña** | Domicilio fuera de Antioquia, pero el departamento de origen principal de su mercancía (por FOB) es Antioquia |
| **C. Vínculo parcial** | Domicilio fuera; solo parte de su mercancía es de origen Antioquia |
| **D. Sin relación** | — |

- `EMPRESA_ANTIOQUENA` = A. Es la definición estricta.
- `ES_EXPORTADOR_ANTIOQUENO` = A o B.

## 3. Sector de cada exportación

- **Minero-energético** (`ES_MINERO_ENERGETICO`). Incluye los capítulos 26 (minerales) y 27 (combustibles), el ferroníquel (720260), el oro (7108), la plata (7106), el platino (7110), los desperdicios de metal precioso (7112) y las piedras preciosas (7103). Esta lista se calibró contra la serie oficial de exportaciones no minero-energéticas (NME) de MinCIT: la diferencia es menor a 0,25 % en todos los trimestres entre 2024-T1 y 2026-T2.
- **Agrícola y agroindustrial** (`ES_AGRICOLA_MADR`). Son las subpartidas que MinAgricultura publica en sus estadísticas de exportaciones agrícolas, con el producto y si es tradicional o no.
- **Industria y otros**: el resto.

`SECTOR_EXPORTADOR_PRINCIPAL` (en el directorio) es el sector con mayor FOB de la empresa.

## 4. Contratación con el Estado (SECOP II)

Para cada NIT exportador se consultó el NIT con y sin dígito de verificación en SECOP II Contratos (jbjy-vk9h), agregado por proveedor: número de contratos, valor, fechas, entidades y si se declaró pyme. No se descargan datos personales; ni representantes legales ni cuentas bancarias. `SECOP_ES_PYME` es la única variable de tamaño disponible y solo existe para quienes contratan con el Estado.

## 5. Validación

| Comparación | Resultado |
|---|---|
| Total trimestral DIAN contra MinCIT | Igual al millón de dólares entre 2024-T1 y 2026-T1. En 2026-T2 hay USD 2 millones de diferencia (0,01 %) |
| NME DIAN contra MinCIT | Diferencia menor a 0,25 % por trimestre |
| Agrícola nacional contra MinAgricultura | Igual: USD 11.477,5 M en 2024 y USD 15.317,1 M en 2025 |
| Agrícola de origen Antioquia contra MinAgricultura | Diferencia menor a 1 % |
| Origen Antioquia 2025 contra Analdex | USD 10.786 M en ambos |
| Exportadores antioqueños 2024 (≥ USD 1.000) | A+B = 2.316; Analdex reporta 2.395 con datos de Legiscomex |
| FOB del directorio contra el total nacional | Cuadra exacto: total = FOB de empresas + FOB de personas naturales, en cada año |

Las tablas completas están en `data/processed/validacion_*.csv` y en el Excel.

## 6. Problema de calidad en la base DIAN de septiembre de 2024

En el archivo `09_Exportaciones_2024_Septiembre.zip`, la DIAN publicó como "PERSONA NATURAL" (o dejó vacía) la razón social de casi todas las empresas: 107.212 líneas que suman USD 4.102 millones. Sin embargo, conservó el NIT. El pipeline reconoce estas líneas por el NIT de empresa (9 dígitos que empiezan por 8 o 9, tipo de identificación NIT), se las atribuye a la empresa y las marca con `RAZON_SOCIAL_ENMASCARADA`.

Sin esta corrección, en el directorio se pierde septiembre de 2024 de cada empresa: el FOB de 2024 baja de USD 49.434 M a USD 45.331 M y desaparecen unas 120 empresas.

## 7. Limitaciones

- Las personas naturales no tienen NIT: no entran al directorio.
- El año en curso está incompleto. `data/processed/cobertura.json` dice hasta qué mes llega.
- El RUES no trae municipio; la cámara de comercio sirve como aproximación de la subregión.
- Supersociedades solo cubre las 10.000 empresas más grandes, y sus cifras vienen en billones de pesos con 2 decimales.
- Hay 60 combinaciones repetidas de formulario y serie dentro de un mismo archivo. Se dejaron tal como las publica la DIAN.

## 8. BD única depurada

El paso 9 convierte los productos anteriores en una sola base con modelo estrella y corrige problemas que quedaban en ellos: el país de destino de las zonas francas (todas aparecían como "ZFP de Rionegro S.A."), los dos esquemas de códigos de país y bandera (2024 frente a 2025), errores de digitación, códigos con y sin ceros a la izquierda, ceros que significan "no aplica", fechas guardadas como texto y columnas redundantes. El detalle está en [limpieza_bd_depurada.md](limpieza_bd_depurada.md).
