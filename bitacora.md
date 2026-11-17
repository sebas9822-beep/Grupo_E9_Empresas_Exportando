# Bitácora

Una línea por decisión: qué decidimos y por qué. Lo más reciente arriba.

## Decisiones

- 2026-11-17 · Organizamos el repositorio con la plantilla del curso: ficha en el README, bitácora, diccionario, `datos/originales`, `datos/limpios`, `consultas`, `notebooks` y `tablero` · Es el estándar de Estud-IA y permite revisar el proyecto igual que los demás.
- 2026-11-17 · No publicamos el nombre ni el domicilio del comprador en el exterior, ni la dirección de las personas naturales · El repositorio es público y esos datos pueden ser de una persona. Se conservan la ciudad y el país del comprador.
- 2026-11-17 · En `datos/limpios/` solo va la BD depurada y sus copias en CSV y Excel. Las salidas de los pasos 7 y 8 pasan a `datos/intermedios/` y no se suben · Repetían la misma información (Antioquia era un pedazo de lo nacional) y traían errores que la BD depurada ya corrige.
- 2026-11-17 · `datos/originales/` guarda una muestra de 1.000 filas y no los archivos completos · Los completos pesan 1,5 GB. La plantilla pide subir una muestra cuando el archivo es muy grande.
- 2026-11-17 · El archivo `.duckdb` no se sube: se arma con `python crear_bd_depurada.py` · Pesa unos 270 MB y GitHub no acepta archivos de más de 100 MB. Sus tablas sí están en parquet.
- 2026-11-17 · Conservamos 10 líneas idénticas a otra y las marcamos con `FLAG_REGISTRO_IDENTICO` · Sin ellas, el total de 2025-T1 queda 0,28 % por debajo de la cifra oficial de MinCIT.
- 2026-11-17 · Las zonas francas colombianas son un destino aparte (código XCF), con su nombre real · No son exportaciones al exterior, y antes las 31 aparecían como «ZFP de Rionegro».
- 2026-11-17 · Persona natural es quien no tiene NIT publicado; no lo decidimos por la razón social · En septiembre de 2024 la DIAN publicó «PERSONA NATURAL» como razón social de 3.927 empresas.
- 2026-11-17 · País de destino y bandera con un solo código (ISO alfa-3) y un solo nombre · La DIAN cambió de esquema en 2025 y los nombres de 2024 vienen en mayúscula.
- 2026-11-17 · El domicilio de la empresa sale del RUES (cámara de comercio) y no de la dirección DIAN · La dirección DIAN suele ser la de la agencia de aduanas: una sola de Bogotá aparece en 1.183 NIT.
- 2026-11-17 · Empresa antioqueña = vínculo A (matrícula en una cámara de Antioquia). Exportador antioqueño = A o B (B: mercancía principalmente antioqueña) · Separa dónde está la empresa de dónde se produce lo que vende.
- 2026-11-17 · Exportador = al menos USD 1.000 FOB en el año · Es el umbral de Analdex y permite comparar con sus cifras (2.316 frente a 2.395 en 2024).
- 2026-11-17 · Minero-energético = capítulos 26 y 27, oro, plata, platino, ferroníquel y piedras preciosas · Con esa lista la serie cuadra con la de MinCIT a menos del 0,25 % por trimestre.
- 2026-11-17 · Solo usamos fuentes oficiales abiertas · Kaggle y MEData no tienen exportaciones por empresa, y Legiscomex, BACEX y Datasur son de pago ([docs/fuentes.md](docs/fuentes.md)).

## Limpieza (desde la sesión 4)

El detalle con el FOB afectado está en [docs/limpieza_bd_depurada.md](docs/limpieza_bd_depurada.md) y en [docs/log_bd_depurada.csv](docs/log_bd_depurada.csv).

- Persona natural por NIT y líneas de septiembre de 2024 atribuidas a su empresa · 107.212 líneas (USD 4.102 M) · La DIAN enmascaró la razón social de 3.927 empresas.
- NIT sin dígito de verificación ni ceros a la izquierda; NIT «0» de personas naturales a vacío · 16.714 líneas de personas naturales · Un mismo NIT debe escribirse igual en todas las tablas.
- Nombre y domicilio del comprador retirados; dirección de personas naturales vacía · 3.611.689 líneas con comprador y 67 con dirección de persona · Datos personales en un repositorio público.
- Zonas francas con código propio (XCF) y nombre real · 38.520 líneas (USD 2.616 M) · Todas aparecían como «ZFP de Rionegro», y 2 con el código de Puerto Rico.
- Países y banderas homologados a ISO alfa-3 · 1.302.673 líneas de 2024 · Dos esquemas de códigos (2024 frente a 2025).
- Errores de digitación («Correción», «despúes», «Unico») · 1.030.911 líneas, más «Único» en todas · Errores de la fuente.
- Espacios dobles, tabulaciones, comillas y entidades HTML («&#304STANBUL») · 3.574.240 líneas · Textos sucios que impiden agrupar.
- Códigos con ceros a la izquierda («2» → «002») · 24.736 líneas en modalidad · El mismo código escrito de dos formas.
- «0» que significa «no aplica» pasa a vacío; las 1.690 líneas sin formulario se conservan · casi todas las líneas · Un cero se confunde con un dato.
- Fechas como texto pasan a tipo fecha · todas las líneas · Para poder filtrar y ordenar por fecha.
- Peso en cero, marcado con `FLAG_PESO_CERO` · 33 líneas · Dato a revisar; no se borra.
- Columnas redundantes o casi vacías retiradas de la tabla de hechos · de 99 a 61 columnas · Repetían otras columnas o el directorio.
- Una razón social por NIT (la más reciente) y sus variantes en `NOMBRES_EN_FUENTE` · 332 NIT con varios nombres; 119 toman el del RUES · La misma empresa aparecía con varios nombres.
- Revisiones sin hallazgos: FOB ≤ 0, peso neto > bruto, fechas inválidas, tasa de cambio fuera de rango, doble conteo de correcciones · 0 líneas · Se verificó y no hizo falta corregir.

## Uso de IA

- Le pedimos a varias IAs (DeepSeek, Gemini, Grok, Kimi y Claude Opus) que buscaran fuentes de datos de empresas exportadoras · Aceptamos solo fuentes oficiales con NIT y descartamos las de pago y las que no tenían exportaciones · Abrimos cada fuente y dejamos la lista con enlaces en [docs/fuentes.md](docs/fuentes.md).
- Le pedimos a Claude (Anthropic) el código que descarga y une las fuentes (pasos 1 a 8 de `pipeline/`) · Aceptamos el proceso y la regla de domicilio por RUES · Lo verificamos cuadrando los totales con MinCIT, MinAgricultura y Analdex.
- Le pedimos a Claude que depurara la base (paso 9) y organizara el repositorio con la plantilla del curso · Aceptamos las reglas de limpieza. Cambiamos dos cosas: no borrar las 10 líneas idénticas, porque sin ellas el total no cuadra con MinCIT, y quitar el nombre y el domicilio del comprador por la regla de datos personales · Lo verificamos con conteos antes y después, llaves sin huérfanos, el cuadre con MinCIT y las cifras de control de `consultas/`.
