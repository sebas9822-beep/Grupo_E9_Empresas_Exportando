-- Pregunta: si el producto es la subpartida, la partida o el capítulo, ¿cuántos productos hay, cuántos tienen 3 países o menos y cuántos quedan con la regla mínima (4 países o más y al menos USD 100.000)?
-- Datos: hechos_2026_09.parquet (tabla datos), con el filtro de la consulta 1 (26.152 líneas)
-- Cifra de control: subpartida 1.420 productos (997 con 3 países o menos); partida 566 (318); capítulo 82 (15); con 3 países o menos la concentración mínima es 100 %; con la regla quedan 167 partidas
WITH base AS (
  SELECT SUBPARTIDA, COD_PAIS_DESTINO, VALOR_FOB_USD
  FROM datos
  WHERE COD_DEPTO_ORIGEN = '05' AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
),
niveles AS (
  SELECT '1. Subpartida (10 dígitos)' AS nivel, SUBPARTIDA AS producto, COD_PAIS_DESTINO, VALOR_FOB_USD FROM base
  UNION ALL
  SELECT '2. Partida (4 dígitos)', SUBSTR(SUBPARTIDA, 1, 4), COD_PAIS_DESTINO, VALOR_FOB_USD FROM base
  UNION ALL
  SELECT '3. Capítulo (2 dígitos)', SUBSTR(SUBPARTIDA, 1, 2), COD_PAIS_DESTINO, VALOR_FOB_USD FROM base
),
producto_pais AS (
  SELECT nivel, producto, COD_PAIS_DESTINO, SUM(VALOR_FOB_USD) AS fob
  FROM niveles
  GROUP BY nivel, producto, COD_PAIS_DESTINO
),
ranking AS (
  SELECT *,
         fob / SUM(fob) OVER (PARTITION BY nivel, producto) AS parte,
         ROW_NUMBER() OVER (PARTITION BY nivel, producto ORDER BY fob DESC) AS puesto
  FROM producto_pais
),
productos AS (
  SELECT nivel, producto, COUNT(*) AS paises, SUM(fob) AS fob,
         SUM(parte) FILTER (WHERE puesto <= 3) AS top3
  FROM ranking
  GROUP BY nivel, producto
)
SELECT nivel,
       COUNT(*) AS productos,
       COUNT(*) FILTER (WHERE paises <= 3) AS con_3_paises_o_menos,
       COUNT(*) FILTER (WHERE paises = 1) AS con_1_pais,
       ROUND(100 * MIN(top3) FILTER (WHERE paises <= 3), 1) AS top3_minimo_en_esos,
       ROUND(100 * SUM(fob) FILTER (WHERE paises <= 3) / SUM(fob), 1) AS pct_fob_en_esos,
       COUNT(*) FILTER (WHERE paises >= 4 AND fob >= 100000) AS quedan_con_la_regla,
       ROUND(100 * SUM(fob) FILTER (WHERE paises >= 4 AND fob >= 100000) / SUM(fob), 1) AS pct_fob_que_queda
FROM productos
GROUP BY nivel
ORDER BY nivel;
