-- Pregunta: para los productos más concentrados, ¿cuántos mercados alternos ya abiertos por otros departamentos tiene cada uno?
-- Datos: tablas ant y nac, año 2025
-- Cifra de control: 15 productos prioritarios; 9 tienen al menos un mercado alterno; flores = 26 países y USD 283,7 M
WITH concentrados AS (                         -- 1. productos prioritarios: no minero-energéticos, > USD 20 M, ≥ 75 % en el top 3
  SELECT HS4
  FROM (
    SELECT HS4, COD_PAIS, SUM(FOB) AS fob,
           ROW_NUMBER() OVER (PARTITION BY HS4 ORDER BY SUM(FOB) DESC) AS puesto
    FROM ant
    WHERE ANIO = 2025 AND NOT ES_ME
    GROUP BY HS4, COD_PAIS
  )
  GROUP BY HS4
  HAVING SUM(fob) > 20e6
     AND SUM(fob) FILTER (WHERE puesto <= 3) / SUM(fob) >= 0.75
),
antioquia AS (                                 -- 2. lo que Antioquia vende de esos productos a cada país, con su parte y puesto
  SELECT HS4, COD_PAIS, SUM(FOB) AS fob_ant,
         SUM(FOB) / SUM(SUM(FOB)) OVER (PARTITION BY HS4) AS parte,
         ROW_NUMBER() OVER (PARTITION BY HS4 ORDER BY SUM(FOB) DESC) AS puesto
  FROM ant
  WHERE ANIO = 2025 AND HS4 IN (SELECT HS4 FROM concentrados)
  GROUP BY HS4, COD_PAIS
),
colombia AS (                                  -- 3. lo que vende Colombia (todos los departamentos)
  SELECT HS4, COD_PAIS, SUM(FOB) AS fob_col
  FROM nac
  WHERE ANIO = 2025 AND HS4 IN (SELECT HS4 FROM concentrados)
  GROUP BY HS4, COD_PAIS
)
SELECT c.HS4 AS partida,
       COUNT(*) AS mercados_alternos,
       ROUND(SUM(c.fob_col - COALESCE(a.fob_ant, 0)) / 1e6, 1) AS otros_departamentos_musd
FROM colombia c
LEFT JOIN antioquia a USING (HS4, COD_PAIS)
WHERE c.fob_col - COALESCE(a.fob_ant, 0) >= 1e6     -- otros departamentos ya venden ≥ USD 1 M allí
  AND COALESCE(a.parte, 0) < 0.05                    -- Antioquia manda menos del 5 % de ese producto
  AND COALESCE(a.puesto, 999) > 3                    -- y no es uno de sus 3 compradores
GROUP BY c.HS4
ORDER BY otros_departamentos_musd DESC;
