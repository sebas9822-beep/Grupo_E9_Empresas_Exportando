-- Pregunta: ¿cuánto exportó Antioquia cada año, contando todos los destinos, para compararlo con cifras publicadas?
-- Datos: tabla lineas (2016-2025)
-- Cifra de control: USD 4.336,5 M en 2016 y USD 10.786,4 M en 2025
SELECT ANIO, ROUND(SUM(FOB) / 1e6, 1) AS fob_antioquia_todos_los_destinos_musd
FROM lineas
WHERE COD_DEPTO_ORIGEN = '05'
GROUP BY ANIO
ORDER BY ANIO;
