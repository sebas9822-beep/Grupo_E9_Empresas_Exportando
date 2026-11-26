-- Pregunta: ¿las dos definiciones de «origen Antioquia vendido al exterior» dan las mismas líneas y el mismo FOB? Si no, ¿qué líneas explican la diferencia?
-- Datos: hechos_2026_09.parquet de la BD depurada (115.049 filas; en Colab la tabla se llama datos)
-- Cifra de control: definición 1 = 26.152 líneas y USD 1.220,14 M; definición 2 = 26.372 líneas y USD 1.220,22 M; están en la 2 y no en la 1: 220 líneas (USD 0,09 M); en la 1 y no en la 2: 0
SELECT 'Definición 1: COD_DEPTO_ORIGEN = 05, sin destino XCF ni COL' AS definicion,
       COUNT(*) AS lineas, ROUND(SUM(VALOR_FOB_USD) / 1e6, 2) AS fob_musd
FROM datos
WHERE COD_DEPTO_ORIGEN = '05' AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
UNION ALL
SELECT 'Definición 2: ORIGEN_MERCANCIA_ANTIOQUIA y no ES_DESTINO_ZONA_FRANCA',
       COUNT(*), ROUND(SUM(VALOR_FOB_USD) / 1e6, 2)
FROM datos
WHERE ORIGEN_MERCANCIA_ANTIOQUIA AND NOT ES_DESTINO_ZONA_FRANCA
UNION ALL
SELECT 'Están en la 2 y no en la 1',
       COUNT(*), ROUND(SUM(VALOR_FOB_USD) / 1e6, 2)
FROM datos
WHERE (ORIGEN_MERCANCIA_ANTIOQUIA AND NOT ES_DESTINO_ZONA_FRANCA)
  AND NOT (COD_DEPTO_ORIGEN = '05' AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL'))
UNION ALL
SELECT 'Están en la 1 y no en la 2',
       COUNT(*), ROUND(SUM(VALOR_FOB_USD) / 1e6, 2)
FROM datos
WHERE (COD_DEPTO_ORIGEN = '05' AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL'))
  AND NOT (ORIGEN_MERCANCIA_ANTIOQUIA AND NOT ES_DESTINO_ZONA_FRANCA);
