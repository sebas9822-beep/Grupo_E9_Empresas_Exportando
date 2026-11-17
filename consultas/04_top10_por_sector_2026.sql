-- Pregunta: ¿cuáles son las 10 empresas antioqueñas que más exportaron en 2026 en cada sector y qué exportaron?
-- Datos: vista vw_exportaciones, vínculo A, enero a septiembre de 2026. Cada empresa va en el sector donde tuvo más FOB.
-- Cifra de control: 30 filas (10 por sector); la primera de cada sector es C.I. ESLOP (USD 1.434,4 M, oro),
--   Uniban (USD 478,1 M, banano) y Renault Sofasa (USD 192,3 M, automóviles)
WITH t AS (
    SELECT NIT_EXPORTADOR AS nit, RAZON_SOCIAL, SECTOR_EXPORTACION, PARTIDA, VALOR_FOB_USD AS fob
    FROM vw_exportaciones
    WHERE EMPRESA_ANTIOQUENA AND ANIO = 2026
),
por_sector AS (SELECT nit, SECTOR_EXPORTACION, SUM(fob) AS fob FROM t GROUP BY nit, SECTOR_EXPORTACION),
empresa AS (
    SELECT t.nit, ANY_VALUE(t.RAZON_SOCIAL) AS razon_social, SUM(t.fob) AS fob,
           (SELECT ARG_MAX(SECTOR_EXPORTACION, fob) FROM por_sector p WHERE p.nit = t.nit) AS sector
    FROM t GROUP BY t.nit
),
top AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY sector ORDER BY fob DESC) AS puesto FROM empresa QUALIFY puesto <= 10),
productos AS (
    SELECT nit, PARTIDA, SUM(fob) AS fob, ROW_NUMBER() OVER (PARTITION BY nit ORDER BY SUM(fob) DESC) AS orden,
           SUM(SUM(fob)) OVER (PARTITION BY nit) AS total
    FROM t WHERE nit IN (SELECT nit FROM top) GROUP BY nit, PARTIDA
)
SELECT top.sector, top.puesto, top.razon_social, ROUND(top.fob / 1e6, 1) AS fob_musd,
       STRING_AGG(p.PARTIDA || ' (' || CAST(ROUND(100 * p.fob / p.total) AS INT) || '%)', '; ' ORDER BY p.orden) AS principales_partidas
FROM top JOIN productos p ON p.nit = top.nit AND p.orden <= 3
GROUP BY ALL
ORDER BY top.sector, top.puesto;
