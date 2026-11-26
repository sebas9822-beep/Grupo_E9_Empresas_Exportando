-- Pregunta: al unir las líneas filtradas con la tabla de países, ¿se conservan las líneas y el FOB? ¿Y si la tabla de países tuviera repetido el país de mayor FOB?
-- Datos: hechos_2026_09.parquet (tabla datos), con el filtro de la consulta 1, y dim_pais.parquet (tabla paises, 215 filas)
-- Cifra de control: sin unir y unida con paises, 26.152 líneas y USD 1.220,14 M; con Estados Unidos repetido, 33.894 líneas (+7.742) y USD 1.540,42 M (+320,28 M, +26,2 %)
WITH filtro AS (
  SELECT * FROM datos
  WHERE COD_DEPTO_ORIGEN = '05' AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
),
pais_mayor AS (                                   -- el país de mayor FOB (Estados Unidos)
  SELECT COD_PAIS_DESTINO FROM filtro
  GROUP BY COD_PAIS_DESTINO ORDER BY SUM(VALOR_FOB_USD) DESC LIMIT 1
),
paises_repetido AS (                              -- paises + otra fila igual para ese país
  SELECT * FROM paises
  UNION ALL
  SELECT * FROM paises WHERE COD_PAIS IN (SELECT COD_PAIS_DESTINO FROM pais_mayor)
)
SELECT '1. Sin unir' AS caso, COUNT(*) AS lineas, ROUND(SUM(VALOR_FOB_USD) / 1e6, 2) AS fob_musd FROM filtro
UNION ALL
SELECT '2. Unida con paises', COUNT(*), ROUND(SUM(f.VALOR_FOB_USD) / 1e6, 2)
FROM filtro f JOIN paises p ON p.COD_PAIS = f.COD_PAIS_DESTINO
UNION ALL
SELECT '3. Unida con paises con el país mayor repetido', COUNT(*), ROUND(SUM(f.VALOR_FOB_USD) / 1e6, 2)
FROM filtro f JOIN paises_repetido p ON p.COD_PAIS = f.COD_PAIS_DESTINO;
