# Cómo se resolvió: concentración de las exportaciones de Antioquia, 2016-2025

19 de noviembre de 2026 · Grupo E9

El informe se armó en tres partes: conseguir los datos de 2016 a 2023 y unirlos con la BD principal con las mismas reglas, comprobar que la unión cuadra con la BD principal y con cifras oficiales, y responder la pregunta con ocho consultas SQL. Cada consulta va aquí con los tres comentarios de la guía 2 (pregunta, datos y cifra de control), su resultado y cómo se comprobó.

## La pregunta y el plan

**Pregunta principal:** ¿qué porcentaje de las exportaciones de cada producto de Antioquia se concentra en sus tres principales países compradores? Y, de ahí, ¿qué tan vulnerable sería el departamento si uno de sus compradores deja de importar?

**Unidad de análisis:** exportaciones por producto (partida arancelaria de 4 dígitos) y país de destino. **Periodo:** 2016 a 2025.

**El obstáculo:** la BD principal del proyecto solo tiene de enero de 2024 a septiembre de 2026. Para cubrir 2016 a 2023 hubo que traer esos años de la misma fuente (la DIAN) y procesarlos con las mismas reglas.

| Paso | Qué responde | Qué produce |
| --- | --- | --- |
| 1. Conseguir y unir los datos | ¿Tenemos 2016 a 2025 con las mismas reglas? | Tabla `lineas` (todas las regiones) y tabla `ant` (Antioquia al exterior) |
| 2. Comprobar la unión | ¿Las cifras son confiables? | Cuadre con la BD principal y con cifras publicadas |
| 3. Consultas 1 y 2 (como la guía) | ¿Cuántas líneas quedan y cómo se reparten por año? | La población del estudio |
| 4. Consultas 3 a 8 | El dato a confirmar, la evolución, los sectores, los escenarios, las empresas y los mercados alternos | Las tablas y gráficos del informe |
| 5. Verificación y armado | ¿Otra vía da lo mismo? | El informe |

**Dónde corren las consultas:** en DuckDB, sobre el archivo `analisis.duckdb` que arma el script `analisis.py` (está en [`scripts/`](scripts/)). Las tres tablas que usan son:

| Tabla | Cada fila es… | Filas |
| --- | --- | --- |
| `lineas` | Un ítem de una declaración de exportación de Colombia, cualquier departamento y destino, 2016-2025 | 10.981.096 |
| `ant` | Lo mismo, pero solo mercancía de origen Antioquia vendida al exterior | 2.843.817 |
| `nac` | Valor exportado por Colombia por año, producto y país (ya sumado) | 175.341 |

La tabla `paises` solo pone el nombre a cada código de país. Ojo con `nac`: ya viene sumada, así que se usa `SUM(FOB)` y no `COUNT(*)`.

## Paso 1 · Conseguir los datos de 2016 a 2023 y unirlos con la BD principal

1. **Descarga.** De la página de bases estadísticas de la DIAN se bajaron los 96 archivos mensuales de exportaciones de enero de 2016 a diciembre de 2023 (un ZIP de 20 a 34 MB por mes, con un Excel adentro). Son los mismos archivos de los que sale la BD principal.
2. **Extracción.** El script `extraer.py` abre cada Excel y guarda en parquet solo las columnas que pide la pregunta: periodo, NIT, departamento de origen, país de destino, subpartida, valor FOB, peso y cantidad.
3. **Unión.** Una consulta pone en una sola tabla los años 2016-2023 (archivos de la DIAN) y 2024-2025 (BD principal), con los mismos nombres y las mismas reglas que usó la BD depurada:

```sql
-- Pregunta: ¿cómo quedan en una sola tabla las exportaciones de 2016 a 2025 con las mismas reglas?
-- Datos: 96 bases mensuales de la DIAN (2016-2023, en parquet) + hechos_analitica de la BD principal (2024-2025)
-- Cifra de control: 10.981.096 filas; enero y julio de 2024 coinciden con la BD principal (paso 2)
CREATE TABLE lineas AS
SELECT ANIO_ARCHIVO AS ANIO, MES_ARCHIVO AS MES,
       NULLIF(LTRIM(NIT_EXPORTADOR, '0'), '') AS NIT,
       LPAD(COD_REGION_ORIGEN, 2, '0') AS COD_DEPTO_ORIGEN,          -- 5 -> '05' (Antioquia)
       CASE WHEN COD_PAIS_DESTINO IN ('ZF', 'XCF') OR COD_PAIS_DESTINO_ALF = 'XCF'
                 OR UPPER(PAIS_DESTINO_FINAL) LIKE 'ZONA FRANCA%'
                 OR UPPER(PAIS_DESTINO_FINAL) LIKE 'ZFP%' THEN 'XCF'      -- zona franca en Colombia
            WHEN COD_PAIS_DESTINO_ALF = 'ZZZ' THEN 'ND'                    -- destino no declarado
            ELSE COD_PAIS_DESTINO_ALF END AS COD_PAIS,                     -- país en 3 letras (ISO)
       LPAD(SUBPARTIDA, 10, '0') AS SUBPARTIDA,
       VALOR_FOB_USD AS FOB
FROM read_parquet('resolver/scripts/parquet/20*.parquet')
WHERE ANIO_ARCHIVO <= 2023
UNION ALL
SELECT ANIO, MES, NIT_EXPORTADOR, COD_DEPTO_ORIGEN, COD_PAIS_DESTINO, SUBPARTIDA, VALOR_FOB_USD
FROM bd_principal.hechos_analitica
WHERE ANIO BETWEEN 2024 AND 2025;
```

4. **Columnas de análisis y tablas de trabajo.** De `lineas` salen la partida (4 primeros dígitos de la subpartida), si el producto es minero-energético y su sector; con eso se arman `ant` y `nac`:

```sql
-- Pregunta: ¿cuáles son las líneas de mercancía antioqueña vendida al exterior, con su partida, su sector y si son minero-energéticas?
-- Datos: tabla lineas
-- Cifra de control: 2.843.817 filas (las mismas que deja el filtro de la consulta 1)
CREATE TABLE ant AS
SELECT *,
       SUBSTR(SUBPARTIDA, 1, 4) AS HS4,
       (SUBSTR(SUBPARTIDA, 1, 2) IN ('26', '27')
        OR SUBSTR(SUBPARTIDA, 1, 4) IN ('7103', '7106', '7108', '7110', '7112')
        OR SUBSTR(SUBPARTIDA, 1, 6) = '720260') AS ES_ME,                  -- minero-energético
       CASE WHEN SUBSTR(SUBPARTIDA, 1, 4) = '7108' THEN 'Oro'
            WHEN SUBSTR(SUBPARTIDA, 1, 4) IN ('0901', '2101') THEN 'Café y derivados'
            WHEN SUBSTR(SUBPARTIDA, 1, 4) = '0803' THEN 'Banano y plátano'
            WHEN SUBSTR(SUBPARTIDA, 1, 4) = '0603' THEN 'Flores'
            -- … y el resto por capítulos del arancel (ver analisis.py)
       END AS SECTOR
FROM lineas
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS NOT IN ('XCF', 'COL');

-- nac: lo que Colombia (todos los departamentos) vendió al exterior, ya sumado por año, producto y país
CREATE TABLE nac AS
SELECT ANIO, SUBSTR(SUBPARTIDA, 1, 4) AS HS4, COD_PAIS, SUM(FOB) AS FOB
FROM lineas
WHERE COD_PAIS NOT IN ('XCF', 'COL')
GROUP BY ANIO, SUBSTR(SUBPARTIDA, 1, 4), COD_PAIS;
```

Las reglas son las de la BD depurada: Antioquia = departamento de origen de la mercancía `'05'` (el criterio del DANE y MinCIT); venta al exterior = sin zonas francas colombianas (`'XCF'`) ni destino Colombia (`'COL'`).

## Paso 2 · Comprobar que la unión es confiable

Antes de calcular nada, se hicieron dos pruebas. Si alguna fallaba, todo lo demás quedaba en duda.

**Prueba A: el método da lo mismo que la BD principal.** Se procesaron enero y julio de 2024 desde los archivos de la DIAN con el método del paso 1, y se compararon contra la BD principal, celda por celda (mes × país × producto):

```sql
-- Pregunta: ¿el método usado para 2016-2023 da exactamente lo mismo que la BD principal en un mes que ambas tienen?
-- Datos: archivos DIAN de enero y julio de 2024 (parquet) vs. hechos_analitica de la BD principal
-- Cifra de control: 5.641 combinaciones de mes, país y producto; 0 diferencias; USD 1.281,7 M en ambas
WITH dian AS (
  SELECT MES_ARCHIVO AS MES,
         CASE WHEN COD_PAIS_DESTINO IN ('ZF', 'XCF') OR COD_PAIS_DESTINO_ALF = 'XCF'
                   OR UPPER(PAIS_DESTINO_FINAL) LIKE 'ZONA FRANCA%'
                   OR UPPER(PAIS_DESTINO_FINAL) LIKE 'ZFP%' THEN 'XCF'
              ELSE COD_PAIS_DESTINO_ALF END AS COD_PAIS,
         SUBSTR(LPAD(SUBPARTIDA, 10, '0'), 1, 4) AS HS4,
         SUM(VALOR_FOB_USD) AS fob
  FROM read_parquet(['resolver/scripts/parquet/2024_01.parquet', 'resolver/scripts/parquet/2024_07.parquet'])
  WHERE LPAD(COD_REGION_ORIGEN, 2, '0') = '05'
  GROUP BY ALL
),
bd AS (
  SELECT MES, COD_PAIS_DESTINO AS COD_PAIS, SUBSTR(SUBPARTIDA, 1, 4) AS HS4,
         SUM(VALOR_FOB_USD) AS fob
  FROM bd_principal.hechos_analitica
  WHERE ANIO = 2024 AND MES IN (1, 7) AND COD_DEPTO_ORIGEN = '05'
  GROUP BY ALL
)
SELECT COUNT(*) AS combinaciones,
       COUNT(*) FILTER (WHERE ABS(COALESCE(dian.fob, 0) - COALESCE(bd.fob, 0)) > 0.01) AS diferencias,
       ROUND(SUM(dian.fob) / 1e6, 1) AS fob_dian_musd,
       ROUND(SUM(bd.fob) / 1e6, 1) AS fob_bd_principal_musd
FROM dian FULL JOIN bd USING (MES, COD_PAIS, HS4)
WHERE COD_PAIS NOT IN ('XCF', 'COL');
```

**Resultado:** 5.641 combinaciones, 0 diferencias, USD 1.281,7 M en las dos. El `FULL JOIN` es clave: si una combinación existiera en un lado y no en el otro, contaría como diferencia.

**Prueba B: los totales anuales cuadran con cifras publicadas.** Para comparar con lo que publican la Cámara de Comercio, MinCIT o la prensa, se suma Antioquia con todos los destinos (incluye zonas francas), porque así se reportan esas cifras:

```sql
-- Pregunta: ¿cuánto exportó Antioquia cada año, contando todos los destinos, para compararlo con cifras publicadas?
-- Datos: tabla lineas (2016-2025)
-- Cifra de control: USD 4.336,5 M en 2016 y USD 10.786,4 M en 2025
SELECT ANIO, ROUND(SUM(FOB) / 1e6, 1) AS fob_antioquia_todos_los_destinos_musd
FROM lineas
WHERE COD_DEPTO_ORIGEN = '05'
GROUP BY ANIO
ORDER BY ANIO;
```

| Año | Esta base (USD M) | Cifra publicada (USD M) | Diferencia | Fuente |
| --- | --- | --- | --- | --- |
| 2025 | 10.786,4 | 10.786,0 | 0,00 % | [El Colombiano](https://www.elcolombiano.com/negocios/antioquia-crecimiento-economico-2025-exportaciones-turismo-BK34497125) |
| 2024 | 8.798,6 | 8.831,7 | −0,37 % | [Analdex (datos de Legiscomex)](https://analdex.org/wp-content/uploads/2025/06/Empresas-exportadoras-colombianas-por-departamento-1.pdf) |
| 2023 | 7.985,7 | 7.983,7 | +0,03 % | [Analdex](https://analdex.org/wp-content/uploads/2025/06/Empresas-exportadoras-colombianas-por-departamento-1.pdf) |
| 2021 | 6.820,8 | 6.821,0 | 0,00 % | [Cámara de Comercio de Medellín](https://abceconomia.co/?p=31823) |
| 2020 | 5.736,5 | 5.735,8 | +0,01 % | [MinCIT, citado por Uninorte](https://www.uninorte.edu.co/documents/19854657/0/Exportaciones-e-importaciones-por-departamentos.pdf/) |
| 2019 | 4.677,2 | 4.676,6 | +0,01 % | [MinCIT, citado por Uninorte](https://www.uninorte.edu.co/documents/19854657/0/Exportaciones-e-importaciones-por-departamentos.pdf/) |
| 2017 | 4.477,4 | 4.478,0 | −0,01 % | [Valora Analitik](https://www.valoraanalitik.com/?p=1525) |
| 2016 | 4.336,5 | 4.329,5 | +0,16 % | [MinCIT, citado por Uninorte](https://www.uninorte.edu.co/documents/19854657/0/Exportaciones-e-importaciones-por-departamentos.pdf/) |

2018 y 2022 no tienen una cifra publicada independiente que se haya podido confirmar. La tabla de MinCIT citada por Uninorte da para 2017 cerca de 10 % menos, pero otra fuente (Valora Analitik) coincide con esta base, así que se mantuvo la serie.

**Por qué importa:** el resto del análisis usa solo ventas al exterior (sin zonas francas). Por eso los totales de las consultas siguientes son algo menores que los de esta tabla; por ejemplo, 2025 queda en USD 10.364,2 M y no en 10.786,4 M.

## Consultas 1 y 2 · Mirar, filtrar y resumir (como en la guía 2)

Son las dos consultas básicas de la guía: la primera mira las columnas y filtra la población; la segunda la resume. Aquí fijan **quién entra al estudio**.

### Consulta 1 · Mirar y filtrar

```sql
-- Pregunta: ¿cuántas líneas de exportación de 2016 a 2025 son de mercancía de origen Antioquia vendida al exterior?
-- Datos: tabla lineas (10.981.096 filas: todos los departamentos y destinos, 2016-2025)
-- Cifra de control: 10.981.096 filas en total y 2.843.817 después del filtro (origen Antioquia, sin zonas francas ni destino Colombia)
SELECT ANIO, MES, NIT, SUBPARTIDA, COD_PAIS, FOB
FROM lineas
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS NOT IN ('XCF', 'COL');
```

Para obtener las dos cifras de control se cambia la primera línea por `SELECT COUNT(*)`, con y sin el `WHERE`.

**Cómo se lee el filtro:**

- `COD_DEPTO_ORIGEN = '05'`: la mercancía se produjo en Antioquia. No importa por dónde salió ni dónde está la empresa.
- `COD_PAIS NOT IN ('XCF', 'COL')`: se quitan las ventas a zonas francas colombianas y las devoluciones a Colombia, porque no son ventas a otro país.

**Resultado:** quedan 2.843.817 de 10.981.096 líneas (25,9 %). Es la misma cifra con la que se creó la tabla `ant` en el paso 1. Desde aquí, las consultas usan `ant` directamente para no repetir el filtro.

### Consulta 2 · Resumir por año

```sql
-- Pregunta: ¿cómo se reparten por año las líneas y el valor de lo que Antioquia vendió al exterior?
-- Datos: tabla lineas, con el filtro de la consulta 1
-- Cifra de control: 10 años; las filas suman 2.843.817 y el valor USD 62.715,5 M; 2025 = USD 10.364,2 M
SELECT ANIO, COUNT(*) AS filas, ROUND(SUM(FOB) / 1e6, 1) AS fob_musd
FROM lineas
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS NOT IN ('XCF', 'COL')
GROUP BY ANIO
ORDER BY ANIO;
```

| Año | Líneas | Valor FOB (USD M) |
| --- | --- | --- |
| 2016 | 233.641 | 4.261,1 |
| 2017 | 245.018 | 4.367,0 |
| 2018 | 252.731 | 4.411,3 |
| 2019 | 261.498 | 4.538,0 |
| 2020 | 253.071 | 5.352,1 |
| 2021 | 297.588 | 6.374,7 |
| 2022 | 317.464 | 7.265,8 |
| 2023 | 314.431 | 7.527,6 |
| 2024 | 323.719 | 8.253,7 |
| 2025 | 344.656 | 10.364,2 |
| **Total** | **2.843.817** | **62.715,5** |

**Cómo se comprobó:** la suma de las filas por año da exactamente las 2.843.817 de la consulta 1, así que ningún registro quedó sin año. El valor de 2025 es el total del que salen todos los porcentajes del informe.

## Consulta 3 · El dato a confirmar: % en los tres principales compradores

Es el corazón del informe. Para cada producto se ordena a sus países compradores de mayor a menor y se suma la parte de los tres primeros.

### 3a · Por producto, 2025

```sql
-- Pregunta: ¿qué porcentaje de lo que Antioquia vendió de cada producto en 2025 fue a sus tres principales países compradores?
-- Datos: tabla ant (Antioquia al exterior), año 2025; tabla paises para el nombre
-- Cifra de control: 225 productos con al menos USD 1 M; oro (7108) = 70,7 %, café (0901) = 64,4 %, flores (0603) = 84,3 %
WITH producto_pais AS (                      -- 1. cuánto se vendió de cada producto a cada país
  SELECT HS4, COD_PAIS, SUM(FOB) AS fob
  FROM ant
  WHERE ANIO = 2025
  GROUP BY HS4, COD_PAIS
  HAVING SUM(FOB) > 0
),
ranking AS (                                 -- 2. parte de cada país y su puesto dentro del producto
  SELECT *,
         fob / SUM(fob) OVER (PARTITION BY HS4) AS parte,
         ROW_NUMBER() OVER (PARTITION BY HS4 ORDER BY fob DESC) AS puesto
  FROM producto_pais
)
SELECT r.HS4 AS partida,                     -- 3. una fila por producto
       ROUND(SUM(fob) / 1e6, 1) AS fob_musd,
       COUNT(*) AS paises,
       MAX(CASE WHEN puesto = 1 THEN p.PAIS END) AS comprador_principal,
       ROUND(100 * MAX(CASE WHEN puesto = 1 THEN parte END), 1) AS pct_comprador_principal,
       ROUND(100 * SUM(parte) FILTER (WHERE puesto <= 3), 1) AS pct_top3_paises
FROM ranking r
LEFT JOIN paises p USING (COD_PAIS)
GROUP BY r.HS4
HAVING SUM(fob) >= 1e6                       -- solo productos relevantes (≥ USD 1 M)
ORDER BY fob_musd DESC;
```

**Cómo funciona, paso a paso:**

1. `producto_pais` suma el valor por producto y país. Es la tabla "producto × país" de la pregunta.
2. `ranking` usa dos funciones de ventana. `SUM(fob) OVER (PARTITION BY HS4)` es el total del producto, así que `fob / total` es la parte de cada país. `ROW_NUMBER()` le da el puesto 1 al país que más compra, el 2 al siguiente, etc.
3. La consulta final suma la parte de los puestos 1 a 3 (`FILTER (WHERE puesto <= 3)`) y deja solo los productos de USD 1 M o más, para que un envío pequeño a un solo país no cuente como "concentración".

**Resultado (los 10 productos de mayor valor; los 225 están en el anexo del informe):**

| Partida | Producto | USD M | Países | Comprador principal | % principal | % top 3 |
| --- | --- | --- | --- | --- | --- | --- |
| 7108 | Oro en bruto o semilabrado | 4.159,9 | 9 | Estados Unidos | 34,1 | 70,7 |
| 0901 | Café | 1.069,6 | 65 | Estados Unidos | 47,1 | 64,4 |
| 0803 | Banano y plátano | 986,0 | 28 | Bélgica | 17,0 | 45,3 |
| 2603 | Minerales de cobre y concentrados | 498,6 | 4 | Perú | 51,2 | 99,7 |
| 0603 | Flores cortadas | 423,6 | 81 | Estados Unidos | 73,4 | 84,3 |
| 2616 | Minerales de metales preciosos | 388,5 | 13 | Perú | 27,1 | 61,9 |
| 0804 | Aguacate, mango, piña y similares | 177,9 | 29 | Estados Unidos | 38,2 | 84,2 |
| 8703 | Automóviles de pasajeros | 169,4 | 13 | Argentina | 36,9 | 92,7 |
| 2716 | Energía eléctrica | 133,8 | 1 | Ecuador | 100,0 | 100,0 |
| 2101 | Extractos de café (café soluble) | 131,2 | 42 | Estados Unidos | 57,2 | 77,5 |

### 3b · Resumen de los 225 productos y evolución 2016-2025

La misma lógica, pero agrupando también por año y resumiendo todos los productos en una fila por año:

```sql
-- Pregunta: ¿qué tan concentrados están en general los productos de Antioquia cada año, y cambió eso entre 2016 y 2025?
-- Datos: tabla ant, 2016-2025
-- Cifra de control: 2025 = 225 productos; 70,1 % ponderado; 73,1 % mediana; 52 productos con 90 % o más; 78 con un país de 50 % o más
WITH producto_pais AS (
  SELECT ANIO, HS4, COD_PAIS, SUM(FOB) AS fob
  FROM ant
  GROUP BY ANIO, HS4, COD_PAIS
  HAVING SUM(FOB) > 0
),
ranking AS (
  SELECT *,
         fob / SUM(fob) OVER (PARTITION BY ANIO, HS4) AS parte,
         ROW_NUMBER() OVER (PARTITION BY ANIO, HS4 ORDER BY fob DESC) AS puesto
  FROM producto_pais
),
productos AS (
  SELECT ANIO, HS4, SUM(fob) AS fob_producto,
         SUM(parte) FILTER (WHERE puesto <= 3) AS top3,
         MAX(parte) AS parte_principal
  FROM ranking
  GROUP BY ANIO, HS4
  HAVING SUM(fob) >= 1e6
)
SELECT ANIO,
       COUNT(*) AS productos,
       ROUND(100 * SUM(fob_producto * top3) / SUM(fob_producto), 1) AS pct_top3_ponderado,
       ROUND(100 * MEDIAN(top3), 1) AS pct_top3_mediana,
       COUNT(*) FILTER (WHERE top3 >= 0.9) AS productos_90_o_mas,
       ROUND(100 * SUM(fob_producto) FILTER (WHERE top3 >= 0.9) / SUM(fob_producto), 1) AS pct_valor_90_o_mas,
       COUNT(*) FILTER (WHERE parte_principal >= 0.5) AS productos_un_pais_50_o_mas
FROM productos
GROUP BY ANIO
ORDER BY ANIO;
```

| Año | Productos | % top 3 ponderado | % top 3 mediana | Productos ≥ 90 % | % del valor en esos productos | Productos con un país ≥ 50 % |
| --- | --- | --- | --- | --- | --- | --- |
| 2016 | 184 | 81,4 | 76,6 | 48 | 46,8 | 67 |
| 2017 | 192 | 79,8 | 77,5 | 48 | 45,7 | 74 |
| 2018 | 201 | 75,5 | 77,8 | 51 | 12,2 | 83 |
| 2019 | 204 | 73,1 | 75,3 | 51 | 13,0 | 76 |
| 2020 | 193 | 75,2 | 76,4 | 50 | 12,0 | 69 |
| 2021 | 220 | 72,0 | 74,5 | 57 | 7,7 | 86 |
| 2022 | 229 | 69,3 | 75,2 | 58 | 8,5 | 90 |
| 2023 | 226 | 75,6 | 74,0 | 52 | 14,2 | 89 |
| 2024 | 234 | 71,5 | 73,1 | 56 | 10,1 | 86 |
| 2025 | 225 | 70,1 | 73,1 | 52 | 10,9 | 78 |

**Cómo leer las dos medidas:**

- **Ponderado (70,1 %):** cada producto pesa según lo que vende. Lo mueve sobre todo el oro, que es el 40 % del valor.
- **Mediana (73,1 %):** el producto "del medio", sin importar su tamaño. Es la que mejor describe al producto típico.

El ponderado bajó de 81,4 % a 70,1 % porque el oro se repartió entre más países. La mediana casi no se movió (de 76,6 % a 73,1 %): el producto típico sigue igual de concentrado. Para quitar el efecto del oro y la minería se corrió la misma consulta con `WHERE NOT ES_ME` en `producto_pais`: en 2025 da 215 productos, 66,3 % ponderado y 72,1 % mediana.

**Un detalle que cambia una cifra:** los umbrales (90 %, 50 %) se aplican sobre la parte **sin redondear**. Si se redondea primero, la partida 0811 (frutas congeladas, 89,98 %) pasa a 90,0 % y el conteo de 2025 da 53 en vez de 52. Por eso `ROUND` solo va en el `SELECT` final.

## Consultas 4 y 5 · Concentración por país y por sector, 2016-2025

La consulta 3 mira cada producto por separado. Estas dos miran la canasta completa: ¿cuánto depende Antioquia de pocos países, y en qué sectores?

### Consulta 4 · Concentración por país, año por año

```sql
-- Pregunta: ¿cuánto pesan Estados Unidos y los tres principales países en lo que vende Antioquia cada año, y a cuántos compradores equivale?
-- Datos: tabla ant, 2016-2025
-- Cifra de control: 2025 = 145 países; EE. UU. 28,9 %; top 3 45,7 %; índice de Herfindahl-Hirschman 1.129; 8,9 países equivalentes
WITH por_pais AS (
  SELECT ANIO, COD_PAIS, SUM(FOB) AS fob
  FROM ant
  GROUP BY ANIO, COD_PAIS
),
partes AS (
  SELECT ANIO, COD_PAIS,
         fob / SUM(fob) OVER (PARTITION BY ANIO) AS parte,
         ROW_NUMBER() OVER (PARTITION BY ANIO ORDER BY fob DESC) AS puesto
  FROM por_pais
)
SELECT ANIO,
       COUNT(*) AS paises,
       ROUND(100 * SUM(parte) FILTER (WHERE COD_PAIS = 'USA'), 1) AS pct_eeuu,
       ROUND(100 * SUM(parte) FILTER (WHERE puesto <= 3), 1) AS pct_top3_paises,
       ROUND(10000 * SUM(parte * parte)) AS hhi_paises,
       ROUND(1 / SUM(parte * parte), 1) AS n_equivalente_paises
FROM partes
GROUP BY ANIO
ORDER BY ANIO;
```

**Los dos indicadores nuevos:**

- **Índice de Herfindahl-Hirschman** = suma de (parte de cada país)² × 10.000. Da 10.000 si hay un solo comprador y se acerca a 0 si hay muchos parejos. Como referencia, la guía de fusiones de 2023 del Departamento de Justicia de EE. UU. llama "altamente concentrado" a un mercado de más de 1.800.
- **Países equivalentes** = 1 / suma de partes² (o 10.000 / el índice). Dice a cuántos compradores del mismo tamaño equivale la canasta.

| Año | Países | % EE. UU. | % top 3 países | Índice H-H | Países equivalentes | % EE. UU. sin minero-energético |
| --- | --- | --- | --- | --- | --- | --- |
| 2016 | 148 | 36,9 | 52,2 | 1.616 | 6,2 | 25,8 |
| 2017 | 154 | 36,1 | 50,1 | 1.533 | 6,5 | 25,5 |
| 2018 | 152 | 30,4 | 43,1 | 1.178 | 8,5 | 26,2 |
| 2019 | 157 | 27,4 | 46,0 | 1.091 | 9,2 | 25,3 |
| 2020 | 152 | 34,8 | 53,6 | 1.528 | 6,5 | 26,5 |
| 2021 | 148 | 35,0 | 50,4 | 1.451 | 6,9 | 28,6 |
| 2022 | 145 | 31,8 | 45,6 | 1.233 | 8,1 | 29,7 |
| 2023 | 153 | 35,3 | 50,1 | 1.482 | 6,7 | 30,9 |
| 2024 | 155 | 33,1 | 48,3 | 1.370 | 7,3 | 29,8 |
| 2025 | 145 | 28,9 | 45,7 | 1.129 | 8,9 | 30,2 |

La última columna sale de la misma consulta con `WHERE NOT ES_ME` en `por_pais`. **Esa es la lectura clave:** en el total, EE. UU. bajó de 36,9 % a 28,9 %, pero porque el oro se fue a Canadá, Emiratos, Italia, India y Suiza. Sin oro ni minería, la dependencia de EE. UU. **subió** de 25,8 % a 30,2 %. Ningún año pasa de 1.800 en el índice, así que la canasta por país no está "altamente concentrada"; la concentración fuerte está dentro de cada producto (consulta 3).

### Consulta 5 · Por sector, 2016 frente a 2025

```sql
-- Pregunta: ¿qué sectores dependen más de pocos países, y cambió eso entre 2016 y 2025?
-- Datos: tabla ant, años 2016 y 2025; columna SECTOR (11 grupos armados con la partida arancelaria)
-- Cifra de control: 11 sectores × 2 años = 22 filas; oro 2025 = USD 4.159,9 M con 70,7 % en el top 3; flores 2025 = 84,3 %
WITH sector_pais AS (
  SELECT ANIO, SECTOR, COD_PAIS, SUM(FOB) AS fob
  FROM ant
  WHERE ANIO IN (2016, 2025)
  GROUP BY ANIO, SECTOR, COD_PAIS
),
ranking AS (
  SELECT *,
         fob / SUM(fob) OVER (PARTITION BY ANIO, SECTOR) AS parte,
         ROW_NUMBER() OVER (PARTITION BY ANIO, SECTOR ORDER BY fob DESC) AS puesto
  FROM sector_pais
)
SELECT SECTOR, ANIO,
       ROUND(SUM(fob) / 1e6, 1) AS fob_musd,
       COUNT(*) AS paises,
       ROUND(100 * SUM(parte) FILTER (WHERE puesto <= 3), 1) AS pct_top3_paises,
       ROUND(100 * SUM(parte) FILTER (WHERE COD_PAIS = 'USA'), 1) AS pct_eeuu
FROM ranking
GROUP BY SECTOR, ANIO
ORDER BY SECTOR, ANIO;
```

| Sector | USD M 2016 | USD M 2025 | % top 3 2016 | % top 3 2025 | % EE. UU. 2025 |
| --- | --- | --- | --- | --- | --- |
| Oro | 1.098,1 | 4.159,9 | 99,5 | 70,7 | 34,1 |
| Café y derivados | 448,8 | 1.200,8 | 63,0 | 63,6 | 48,2 |
| Otros minero-energéticos | 61,4 | 1.072,6 | 82,2 | 64,2 | 2,7 |
| Banano y plátano | 662,2 | 986,0 | 70,0 | 45,3 | 11,9 |
| Otros agropecuarios y alimentos | 204,5 | 780,2 | 51,3 | 56,7 | 39,6 |
| Químicos, plásticos y caucho | 365,2 | 548,0 | 50,3 | 42,4 | 11,6 |
| Flores | 275,7 | 423,6 | 92,8 | 84,3 | 73,4 |
| Metalmecánica, maquinaria y eléctricos | 243,3 | 371,3 | 38,7 | 38,8 | 14,7 |
| Textiles, confecciones, cuero y calzado | 363,3 | 339,5 | 51,4 | 49,5 | 24,4 |
| Otras manufacturas | 189,3 | 281,0 | 44,4 | 32,9 | 9,6 |
| Vehículos y material de transporte | 349,4 | 201,3 | 88,1 | 86,9 | 2,7 |

El sector no viene en la DIAN: se armó con un `CASE` sobre la partida (paso 1). Las flores y los vehículos son los más concentrados; las flores, además, dependen de un solo país (73,4 % a EE. UU.).

## Consultas 6 y 7 · Qué pasa si un comprador deja de comprar, y cuánto dependen las empresas

Esta parte responde la segunda mitad de la idea: la vulnerabilidad.

### Consulta 6 · Escenario de pérdida de un comprador (2025)

La forma más simple y transparente de medirlo: **si un país deja de comprar, Antioquia pierde lo que le vendía**, suponiendo que nada se logra vender en otro lado. Es un techo de corto plazo, no un pronóstico.

```sql
-- Pregunta: ¿cuánto perdería Antioquia, en valor y en % de sus ventas, si cada uno de sus principales compradores dejara de importar?
-- Datos: tabla ant, año 2025; tabla paises para el nombre
-- Cifra de control: EE. UU. = USD 2.998,5 M (28,9 % del total y 30,2 % sin minero-energético); Canadá = USD 935,6 M (9,0 %)
WITH b AS (SELECT * FROM ant WHERE ANIO = 2025)
SELECT p.PAIS,
       ROUND(SUM(b.FOB) / 1e6, 1) AS perdida_directa_musd,
       ROUND(100 * SUM(b.FOB) / (SELECT SUM(FOB) FROM b), 1) AS pct_total,
       ROUND(100 * SUM(b.FOB) FILTER (WHERE NOT b.ES_ME)
             / (SELECT SUM(FOB) FROM b WHERE NOT ES_ME), 1) AS pct_no_minero_energetico
FROM b
JOIN paises p USING (COD_PAIS)
GROUP BY p.PAIS
ORDER BY perdida_directa_musd DESC
LIMIT 8;
```

| País | Pérdida directa (USD M) | % del total | % sin minero-energético |
| --- | --- | --- | --- |
| Estados Unidos | 2.998,5 | 28,9 | 30,2 |
| Canadá | 935,6 | 9,0 | 3,0 |
| Emiratos Árabes Unidos | 801,9 | 7,7 | 0,2 |
| Italia | 559,9 | 5,4 | 3,5 |
| Perú | 555,3 | 5,4 | 3,8 |
| India | 480,9 | 4,6 | 0,2 |
| Ecuador | 451,5 | 4,4 | 6,2 |
| Suiza | 318,9 | 3,1 | 0,0 |

**Cómo leer las dos columnas de %:** Canadá, Emiratos, India y Suiza pesan en el total casi solo por el oro; si se quita el oro y la minería, casi desaparecen. EE. UU. es el único que pesa en las dos, y Ecuador sube cuando se quita la minería (6,2 %), porque le compra sobre todo manufacturas.

Para ver qué hay detrás del riesgo EE. UU. se corrieron tres consultas de apoyo:

```sql
-- Pregunta: ¿qué productos componen lo que Antioquia le vende a EE. UU.?
-- Datos: tabla ant, 2025, país USA
-- Cifra de control: oro 47,3 %, café 16,8 % y flores 10,4 % de lo que compra EE. UU.
SELECT HS4 AS partida,
       ROUND(SUM(FOB) / 1e6, 1) AS fob_a_eeuu_musd,
       ROUND(100 * SUM(FOB) / SUM(SUM(FOB)) OVER (), 1) AS pct_de_lo_que_compra_eeuu
FROM ant
WHERE ANIO = 2025 AND COD_PAIS = 'USA'
GROUP BY HS4
ORDER BY fob_a_eeuu_musd DESC
LIMIT 5;
```

```sql
-- Pregunta: ¿cuántos productos venden la mitad o más a EE. UU.?
-- Datos: tabla ant, 2025, productos de al menos USD 1 M
-- Cifra de control: 29 productos, que suman USD 871,7 M
WITH total_producto AS (
  SELECT HS4, SUM(FOB) AS fob_total
  FROM ant WHERE ANIO = 2025
  GROUP BY HS4 HAVING SUM(FOB) >= 1e6
),
a_eeuu AS (
  SELECT HS4, SUM(FOB) AS fob_eeuu
  FROM ant WHERE ANIO = 2025 AND COD_PAIS = 'USA'
  GROUP BY HS4
)
SELECT COUNT(*) AS productos_que_venden_la_mitad_o_mas_a_eeuu,
       ROUND(SUM(fob_total) / 1e6, 1) AS fob_de_esos_productos_musd
FROM total_producto JOIN a_eeuu USING (HS4)
WHERE fob_eeuu / fob_total >= 0.5;
```

```sql
-- Pregunta: ¿cuántas empresas venden la mitad o más de lo suyo a EE. UU.?
-- Datos: tabla ant, 2025, empresas (NIT) con al menos USD 10.000 exportados
-- Cifra de control: 520 empresas con la mitad o más; 263 de ellas venden solo a EE. UU.
WITH total_empresa AS (
  SELECT NIT, SUM(FOB) AS fob_total
  FROM ant WHERE ANIO = 2025 AND NIT IS NOT NULL
  GROUP BY NIT HAVING SUM(FOB) >= 10000
),
a_eeuu AS (
  SELECT NIT, SUM(FOB) AS fob_eeuu
  FROM ant WHERE ANIO = 2025 AND COD_PAIS = 'USA'
  GROUP BY NIT
)
SELECT COUNT(*) FILTER (WHERE fob_eeuu / fob_total >= 0.5) AS empresas_mitad_o_mas_a_eeuu,
       COUNT(*) FILTER (WHERE fob_eeuu / fob_total >= 0.999) AS empresas_solo_eeuu
FROM total_empresa JOIN a_eeuu USING (NIT);
```

**Resultado:** de los USD 2.998,5 M que compra EE. UU., el oro es el 47,3 % (USD 1.418,9 M), el café el 16,8 % y las flores el 10,4 %. Hay 29 productos (USD 871,7 M) y 520 empresas que le venden a EE. UU. la mitad o más de lo suyo; 263 de esas empresas le venden solo a EE. UU.

### Consulta 7 · Dependencia de las empresas, 2016 frente a 2025

```sql
-- Pregunta: ¿cuántas empresas exportadoras de Antioquia dependen de un solo país, y cambió eso entre 2016 y 2025?
-- Datos: tabla ant, empresas (NIT) con al menos USD 10.000 exportados en el año
-- Cifra de control: 2025 = 2.049 empresas; 44,6 % vende a un solo país; 84,7 % vende la mitad o más a un solo país
WITH empresa_pais AS (
  SELECT ANIO, NIT, COD_PAIS, SUM(FOB) AS fob
  FROM ant WHERE NIT IS NOT NULL
  GROUP BY ANIO, NIT, COD_PAIS
),
empresas AS (
  SELECT ANIO, NIT, SUM(fob) AS fob_total, COUNT(*) AS n_paises,
         MAX(fob) / SUM(fob) AS parte_pais_principal
  FROM empresa_pais
  GROUP BY ANIO, NIT
  HAVING SUM(fob) >= 10000
)
SELECT ANIO,
       COUNT(*) AS empresas,
       ROUND(100 * AVG(CASE WHEN n_paises = 1 THEN 1 ELSE 0 END), 1) AS pct_un_solo_pais,
       ROUND(100 * AVG(CASE WHEN parte_pais_principal >= 0.5 THEN 1 ELSE 0 END), 1) AS pct_mitad_o_mas_en_un_pais,
       MEDIAN(n_paises) AS mediana_paises
FROM empresas
WHERE ANIO IN (2016, 2025)
GROUP BY ANIO
ORDER BY ANIO;
```

| Año | Empresas | % vende a un solo país | % vende la mitad o más a un país | Mediana de países por empresa |
| --- | --- | --- | --- | --- |
| 2016 | 1.641 | 42,9 | 84,5 | 2 |
| 2025 | 2.049 | 44,6 | 84,7 | 2 |

**Cómo se lee:** hay más empresas exportando (de 1.641 a 2.049), pero cada una sigue igual de concentrada: casi la mitad vende a un solo país y la empresa típica vende a dos. El truco de la consulta es `AVG(CASE WHEN … THEN 1 ELSE 0 END)`: el promedio de unos y ceros es el porcentaje de empresas que cumplen la condición. El piso de USD 10.000 deja por fuera envíos sueltos que inflarían el conteo de empresas de un solo país.

## Consulta 8 · Mercados alternos que Colombia ya abrió

Saber qué está concentrado no basta: el informe también propone dónde diversificar. La idea es buscar países donde **otros departamentos ya venden el mismo producto** y adonde Antioquia casi no llega. Allí la demanda, la logística y los permisos ya están probados desde Colombia. Se resuelve cruzando la tabla `nac` (Colombia) con `ant` (Antioquia).

**Las tres reglas de un mercado alterno:**

1. Otros departamentos venden ahí al menos USD 1 M del producto (lo de Colombia menos lo de Antioquia).
2. Antioquia manda ahí menos del 5 % de lo que exporta de ese producto.
3. No es uno de los tres compradores principales de Antioquia para ese producto.

### 8a · Un producto: flores cortadas (0603)

```sql
-- Pregunta: ¿en qué países otros departamentos ya venden flores y Antioquia casi no llega?
-- Datos: tabla ant (Antioquia) y tabla nac (Colombia), año 2025, partida 0603
-- Cifra de control: 26 países; España USD 56,7 M, Países Bajos 55,0 M y Japón 47,5 M de otros departamentos
WITH antioquia AS (
  SELECT COD_PAIS, SUM(FOB) AS fob_ant
  FROM ant WHERE ANIO = 2025 AND HS4 = '0603'
  GROUP BY COD_PAIS
),
ranking AS (
  SELECT *, fob_ant / SUM(fob_ant) OVER () AS parte,
         ROW_NUMBER() OVER (ORDER BY fob_ant DESC) AS puesto
  FROM antioquia
),
colombia AS (
  SELECT COD_PAIS, SUM(FOB) AS fob_col
  FROM nac WHERE ANIO = 2025 AND HS4 = '0603'
  GROUP BY COD_PAIS
)
SELECT p.PAIS,
       ROUND((c.fob_col - COALESCE(r.fob_ant, 0)) / 1e6, 1) AS otros_departamentos_musd,
       ROUND(100 * COALESCE(r.parte, 0), 1) AS pct_flores_antioquia
FROM colombia c
LEFT JOIN ranking r USING (COD_PAIS)
LEFT JOIN paises p USING (COD_PAIS)
WHERE c.fob_col - COALESCE(r.fob_ant, 0) >= 1e6   -- regla 1
  AND COALESCE(r.parte, 0) < 0.05                  -- regla 2
  AND COALESCE(r.puesto, 999) > 3                  -- regla 3
ORDER BY otros_departamentos_musd DESC;
```

| País | Otros departamentos (USD M) | % de las flores de Antioquia que van allí |
| --- | --- | --- |
| España | 56,7 | 2,0 |
| Países Bajos | 55,0 | 2,3 |
| Japón | 47,5 | 0,3 |
| Polonia | 29,8 | 0,0 |
| Corea del Sur | 15,9 | 0,8 |
| … 21 países más |  |  |

**El detalle técnico:** el `LEFT JOIN` desde `colombia` es lo que permite encontrar países donde Antioquia vende **cero**. Si fuera un `JOIN` normal, esos países desaparecerían, y son justamente los más interesantes. Por eso los `COALESCE(…, 0)` y el `999` para el puesto.

### 8b · Todos los productos prioritarios a la vez

La misma lógica, primero eligiendo los productos prioritarios: no minero-energéticos, de más de USD 20 M y con 75 % o más en sus tres principales compradores.

```sql
-- Pregunta: para los productos más concentrados, ¿cuántos mercados alternos ya abiertos por otros departamentos tiene cada uno?
-- Datos: tablas ant y nac, año 2025
-- Cifra de control: 15 productos prioritarios; 9 tienen al menos un mercado alterno; flores = 26 países y USD 283,7 M
WITH concentrados AS (
  SELECT HS4
  FROM (
    SELECT HS4, COD_PAIS, SUM(FOB) AS fob,
           ROW_NUMBER() OVER (PARTITION BY HS4 ORDER BY SUM(FOB) DESC) AS puesto
    FROM ant
    WHERE ANIO = 2025 AND NOT ES_ME
    GROUP BY HS4, COD_PAIS
  )
  GROUP BY HS4
  HAVING SUM(fob) > 20e6
     AND SUM(fob) FILTER (WHERE puesto <= 3) / SUM(fob) >= 0.75
),
antioquia AS (
  SELECT HS4, COD_PAIS, SUM(FOB) AS fob_ant,
         SUM(FOB) / SUM(SUM(FOB)) OVER (PARTITION BY HS4) AS parte,
         ROW_NUMBER() OVER (PARTITION BY HS4 ORDER BY SUM(FOB) DESC) AS puesto
  FROM ant
  WHERE ANIO = 2025 AND HS4 IN (SELECT HS4 FROM concentrados)
  GROUP BY HS4, COD_PAIS
),
colombia AS (
  SELECT HS4, COD_PAIS, SUM(FOB) AS fob_col
  FROM nac
  WHERE ANIO = 2025 AND HS4 IN (SELECT HS4 FROM concentrados)
  GROUP BY HS4, COD_PAIS
)
SELECT c.HS4 AS partida,
       COUNT(*) AS mercados_alternos,
       ROUND(SUM(c.fob_col - COALESCE(a.fob_ant, 0)) / 1e6, 1) AS otros_departamentos_musd
FROM colombia c
LEFT JOIN antioquia a USING (HS4, COD_PAIS)
WHERE c.fob_col - COALESCE(a.fob_ant, 0) >= 1e6
  AND COALESCE(a.parte, 0) < 0.05
  AND COALESCE(a.puesto, 999) > 3
GROUP BY c.HS4
ORDER BY otros_departamentos_musd DESC;
```

| Partida | Producto | Mercados alternos | Otros departamentos (USD M) |
| --- | --- | --- | --- |
| 0603 | Flores cortadas | 26 | 283,7 |
| 2101 | Extractos de café (café soluble) | 16 | 202,2 |
| 7404 | Desperdicios y chatarra de cobre | 8 | 75,4 |
| 0804 | Aguacate, mango, piña y similares | 7 | 50,0 |
| 3402 | Detergentes y productos de limpieza | 9 | 24,6 |
| 0810 | Otras frutas frescas | 7 | 21,1 |
| 1804 | Manteca de cacao | 4 | 9,4 |
| 3506 | Colas y adhesivos | 3 | 6,6 |
| 8703 | Automóviles de pasajeros | 1 | 2,8 |

Los otros 6 productos prioritarios no tienen ningún mercado alterno con estas reglas: artículos de aluminio para el hogar (7615), leche concentrada (0402), lavadoras (8450), medias (6115), grasas y aceites modificados (1518) y motocicletas (8711). Para ellos, diversificar exige abrir mercados que Colombia todavía no tiene. En el informe, el café (0901) y el banano (0803) se agregaron a la tabla por su tamaño, aunque no pasan el filtro de 75 %: para obtenerlos se corre 8a cambiando la partida.

**Atención con la suma:** los USD 283,7 M de las flores se suman sobre todos los países alternos. No es la oportunidad de un solo mercado: es lo que otros departamentos ya venden en los 26 juntos.

## Paso final · Verificación, correcciones y armado del informe

### Verificación por una segunda vía

El dato a confirmar se recalculó sin SQL de ventanas, con pandas, leyendo directamente la BD principal. Si las dos vías no coincidieran, habría un error en alguna:

```python
# Verificación independiente del dato a confirmar (2025), en pandas sobre la BD principal
import duckdb
con = duckdb.connect('datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb', read_only=True)
df = con.sql("""SELECT SUBPARTIDA, COD_PAIS_DESTINO, VALOR_FOB_USD
                FROM hechos_analitica
                WHERE ANIO = 2025 AND COD_DEPTO_ORIGEN = '05'
                  AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')""").df()
df['HS4'] = df['SUBPARTIDA'].str[:4]

pp = (df.groupby(['HS4', 'COD_PAIS_DESTINO'])['VALOR_FOB_USD'].sum()
        .reset_index().sort_values(['HS4', 'VALOR_FOB_USD'], ascending=[True, False]))
pp = pp[pp['VALOR_FOB_USD'] > 0]
total = pp.groupby('HS4')['VALOR_FOB_USD'].sum()
top3 = pp.groupby('HS4').head(3).groupby('HS4')['VALOR_FOB_USD'].sum()   # los 3 primeros de cada producto
res = (top3 / total).rename('top3').to_frame().join(total.rename('fob'))
res = res[res['fob'] >= 1e6]

print(len(res))                                                    # 225
print((res['top3'] * res['fob']).sum() / res['fob'].sum())        # 0,701
print(res['top3'].median())                                       # 0,731
print((res['top3'] >= 0.9).sum())                                 # 52
```

**Resultado:** 225 productos, 70,1 % ponderado, 73,1 % mediana y 52 productos con 90 % o más. Es lo mismo que la consulta 3.

### Errores que se encontraron y corrigieron antes de entregar

| Qué decía el borrador | Qué estaba mal | Cómo quedó |
| --- | --- | --- |
| 53 productos con 90 % o más | Se redondeó antes de comparar con el umbral | 52, calculando sobre la parte sin redondear |
| La concentración "casi no ha cambiado" | Es cierto para la mediana, no para el ponderado | Se dicen las dos: la mediana pasó de 76,6 % a 73,1 %; el ponderado, de 81,4 % a 70,1 % |
| Porcentajes "del oro" de 83,5 %, 98,7 % y 98,2 % | Eran oro más minería y energía, no solo oro | Se reescribió como "minero-energético" |
| Montos de las recomendaciones | Sumaban todos los mercados alternos, no los países nombrados | Se dejaron solo los países que se nombran |
| "Ecuador compra manufacturas y alimentos" | No se había medido | 215 de las 231 empresas que le venden son de manufactura |
| Tabla de MinCIT citada por Uninorte para 2017 | Daba cerca de 10 % menos que esta base | Otra fuente (Valora Analitik) coincide con esta base; se mantuvo la serie y se explica en el informe |

Al rehacer la consulta 8b para este documento apareció un detalle más: el informe dice que "para casi todos" los productos prioritarios hay mercados alternos, pero son **9 de 15**. Conviene cambiar esa frase en el informe.

### Cómo se armó el informe

| Parte del informe | De qué consulta sale |
| --- | --- |
| Cifra principal y hallazgos | Consulta 3 (3a y 3b) |
| Gráfico de % EE. UU. con y sin minero-energético | Consulta 4 |
| Tabla de sectores | Consulta 5 |
| Escenarios de pérdida y riesgo EE. UU. | Consulta 6 y sus tres consultas de apoyo |
| Dependencia de las empresas | Consulta 7 |
| Gráfico de productos prioritarios y tabla de mercados alternos | Consultas 3a y 8 |
| Pestaña "Método y validación" | Pasos 1 y 2 |
| Pestaña "Anexo: productos" | Consulta 3a completa (225 filas) |

Los scripts están en [`scripts/`](scripts/) y cada consulta en su propio archivo en [`consultas/`](consultas/); el [README](README.md) de esta carpeta explica cómo reproducir todas las cifras.

### Cómo explicarlo en un minuto

1. **La BD principal solo tiene datos desde 2024**, así que trajimos 2016-2023 de la misma fuente (DIAN) y los procesamos con las mismas reglas.
2. **Comprobamos la unión dos veces:** el método da exactamente lo mismo que la BD principal en 2024 (cero diferencias), y los totales anuales cuadran con cifras publicadas.
3. **Filtramos** lo que se produjo en Antioquia y se vendió a otro país: 2.843.817 líneas.
4. **Para cada producto** ordenamos sus compradores y sumamos los tres primeros: en 2025, el producto típico vende el 73,1 % a solo tres países, y 52 productos venden el 90 % o más.
5. **Medimos la vulnerabilidad** con lo que se perdería si un país deja de comprar: EE. UU. es el riesgo principal (USD 2.998,5 M, 28,9 % del total), y sin oro la dependencia de EE. UU. subió de 25,8 % a 30,2 %.
6. **Propusimos dónde diversificar:** países donde otros departamentos ya venden el mismo producto y Antioquia casi no llega.
