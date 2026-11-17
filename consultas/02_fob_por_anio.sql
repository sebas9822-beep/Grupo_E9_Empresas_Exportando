-- Pregunta: ¿cuánto exportó Colombia cada año y qué parte fue de origen Antioquia?
-- Datos: BD depurada, vista vw_exportaciones (3.613.237 líneas; 2026 llega hasta septiembre)
-- Cifra de control: los tres años suman USD 142.059,8 M (49.556,5 + 50.201,5 + 42.301,8), igual que MinCIT
SELECT ANIO,
       COUNT(*) AS lineas,
       ROUND(SUM(VALOR_FOB_USD) / 1e6, 1) AS fob_musd,
       ROUND(SUM(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA) / 1e6, 1) AS fob_origen_antioquia_musd,
       ROUND(100 * SUM(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA) / SUM(VALOR_FOB_USD), 1) AS pct_antioquia,
       ROUND(100 * SUM(VALOR_FOB_USD) FILTER (WHERE NOT ES_MINERO_ENERGETICO) / SUM(VALOR_FOB_USD), 1) AS pct_no_minero_energetico
FROM vw_exportaciones
GROUP BY ANIO
ORDER BY ANIO;
