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
