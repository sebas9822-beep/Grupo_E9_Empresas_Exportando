-- Pregunta: ¿cómo cambia la concentración total en los 3 principales países si el oro (partida 7108) se reporta aparte?
-- Datos: hechos_2026_09.parquet (tabla datos), con el filtro de la consulta 1
-- Cifra de control: todo Antioquia 53,0 % (EE. UU., Italia, Canadá); sin el oro 44,6 % (EE. UU., Ecuador, India); solo el oro 75,7 % (EE. UU., Italia, Canadá)
WITH base AS (
  SELECT * FROM datos
  WHERE COD_DEPTO_ORIGEN = '05' AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
),
grupos AS (
  SELECT '1. Todo Antioquia' AS grupo, COD_PAIS_DESTINO, VALOR_FOB_USD FROM base
  UNION ALL
  SELECT '2. Sin la partida 7108 (oro)', COD_PAIS_DESTINO, VALOR_FOB_USD FROM base WHERE SUBSTR(SUBPARTIDA, 1, 4) <> '7108'
  UNION ALL
  SELECT '3. Solo la partida 7108 (oro)', COD_PAIS_DESTINO, VALOR_FOB_USD FROM base WHERE SUBSTR(SUBPARTIDA, 1, 4) = '7108'
),
por_pais AS (
  SELECT grupo, COD_PAIS_DESTINO, SUM(VALOR_FOB_USD) AS fob
  FROM grupos
  GROUP BY grupo, COD_PAIS_DESTINO
),
ranking AS (
  SELECT *,
         fob / SUM(fob) OVER (PARTITION BY grupo) AS parte,
         ROW_NUMBER() OVER (PARTITION BY grupo ORDER BY fob DESC) AS puesto
  FROM por_pais
)
SELECT grupo,
       ROUND(SUM(fob) / 1e6, 2) AS fob_musd,
       COUNT(*) AS paises,
       ROUND(100 * SUM(parte) FILTER (WHERE puesto <= 3), 1) AS top3_paises,
       string_agg(COD_PAIS_DESTINO, ', ' ORDER BY puesto) FILTER (WHERE puesto <= 3) AS cuales
FROM ranking
GROUP BY grupo
ORDER BY grupo;
