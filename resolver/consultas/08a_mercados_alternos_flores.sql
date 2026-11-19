-- Pregunta: ¿en qué países otros departamentos ya venden flores y Antioquia casi no llega?
-- Datos: tabla ant (Antioquia) y tabla nac (Colombia), año 2025, partida 0603
-- Cifra de control: 26 países; España USD 56,7 M, Países Bajos 55,0 M y Japón 47,5 M de otros departamentos
WITH antioquia AS (
  SELECT COD_PAIS, SUM(FOB) AS fob_ant
  FROM ant WHERE ANIO = 2025 AND HS4 = '0603'
  GROUP BY COD_PAIS
),
ranking AS (
  SELECT *, fob_ant / SUM(fob_ant) OVER () AS parte,
         ROW_NUMBER() OVER (ORDER BY fob_ant DESC) AS puesto
  FROM antioquia
),
colombia AS (
  SELECT COD_PAIS, SUM(FOB) AS fob_col
  FROM nac WHERE ANIO = 2025 AND HS4 = '0603'
  GROUP BY COD_PAIS
)
SELECT p.PAIS,
       ROUND((c.fob_col - COALESCE(r.fob_ant, 0)) / 1e6, 1) AS otros_departamentos_musd,
       ROUND(100 * COALESCE(r.parte, 0), 1) AS pct_flores_antioquia
FROM colombia c
LEFT JOIN ranking r USING (COD_PAIS)
LEFT JOIN paises p USING (COD_PAIS)
WHERE c.fob_col - COALESCE(r.fob_ant, 0) >= 1e6
  AND COALESCE(r.parte, 0) < 0.05
  AND COALESCE(r.puesto, 999) > 3
ORDER BY otros_departamentos_musd DESC;
