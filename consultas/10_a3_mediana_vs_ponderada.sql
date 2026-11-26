-- Pregunta: con la regla mínima de A2, ¿la mediana de la concentración en 3 países entre partidas es igual a la concentración ponderada por FOB?
-- Datos: hechos_2026_09.parquet (tabla datos), con el filtro de la consulta 1; partidas con 4 países o más y al menos USD 100.000
-- Cifra de control: 167 partidas; mediana 79,0 %; ponderada por FOB 74,6 %; la partida más grande (7108, oro) pesa el 59,1 % del FOB
WITH producto_pais AS (
  SELECT SUBSTR(SUBPARTIDA, 1, 4) AS partida, COD_PAIS_DESTINO, SUM(VALOR_FOB_USD) AS fob
  FROM datos
  WHERE COD_DEPTO_ORIGEN = '05' AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
  GROUP BY partida, COD_PAIS_DESTINO
),
ranking AS (
  SELECT *,
         fob / SUM(fob) OVER (PARTITION BY partida) AS parte,
         ROW_NUMBER() OVER (PARTITION BY partida ORDER BY fob DESC) AS puesto
  FROM producto_pais
),
partidas AS (
  SELECT partida, COUNT(*) AS paises, SUM(fob) AS fob,
         SUM(parte) FILTER (WHERE puesto <= 3) AS top3
  FROM ranking
  GROUP BY partida
  HAVING COUNT(*) >= 4 AND SUM(fob) >= 100000          -- regla mínima de A2
)
SELECT COUNT(*) AS partidas,
       ROUND(100 * MEDIAN(top3), 1) AS mediana_top3,
       ROUND(100 * SUM(top3 * fob) / SUM(fob), 1) AS ponderada_por_fob,
       ROUND(100 * MAX(fob) / SUM(fob), 1) AS peso_partida_mayor
FROM partidas;
