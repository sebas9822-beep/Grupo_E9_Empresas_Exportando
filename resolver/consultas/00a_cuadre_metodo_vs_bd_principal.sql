-- Pregunta: ¿el método usado para 2016-2023 da exactamente lo mismo que la BD principal en un mes que ambas tienen?
-- Datos: archivos DIAN de enero y julio de 2024 (resolver/scripts/parquet) vs. hechos_analitica de la BD principal (adjunta como bd_principal)
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
