-- Pregunta: ¿qué parte del FOB de Antioquia de septiembre de 2026 es una sola partida?
-- Datos: hechos_2026_09.parquet (tabla datos), con el filtro de la consulta 1 (USD 1.220,14 M)
-- Cifra de control: la partida 7108 (oro) suma USD 671,26 M, el 55,0 % del FOB, en 170 líneas y 6 países; la segunda (0901, café) es el 6,3 %
SELECT SUBSTR(SUBPARTIDA, 1, 4) AS partida,
       COUNT(*) AS lineas,
       COUNT(DISTINCT COD_PAIS_DESTINO) AS paises,
       ROUND(SUM(VALOR_FOB_USD) / 1e6, 2) AS fob_musd,
       ROUND(100 * SUM(VALOR_FOB_USD) / SUM(SUM(VALOR_FOB_USD)) OVER (), 1) AS pct_del_fob
FROM datos
WHERE COD_DEPTO_ORIGEN = '05' AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
GROUP BY partida
ORDER BY fob_musd DESC
LIMIT 5;
