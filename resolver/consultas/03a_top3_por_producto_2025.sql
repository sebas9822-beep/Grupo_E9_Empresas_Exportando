-- Pregunta: ¿qué porcentaje de lo que Antioquia vendió de cada producto en 2025 fue a sus tres principales países compradores?
-- Datos: tabla ant (Antioquia al exterior), año 2025; tabla paises para el nombre
-- Cifra de control: 225 productos con al menos USD 1 M; oro (7108) = 70,7 %, café (0901) = 64,4 %, flores (0603) = 84,3 %
WITH producto_pais AS (
  SELECT HS4, COD_PAIS, SUM(FOB) AS fob
  FROM ant
  WHERE ANIO = 2025
  GROUP BY HS4, COD_PAIS
  HAVING SUM(FOB) > 0
),
ranking AS (
  SELECT *,
         fob / SUM(fob) OVER (PARTITION BY HS4) AS parte,
         ROW_NUMBER() OVER (PARTITION BY HS4 ORDER BY fob DESC) AS puesto
  FROM producto_pais
)
SELECT r.HS4 AS partida,
       ROUND(SUM(fob) / 1e6, 1) AS fob_musd,
       COUNT(*) AS paises,
       MAX(CASE WHEN puesto = 1 THEN p.PAIS END) AS comprador_principal,
       ROUND(100 * MAX(CASE WHEN puesto = 1 THEN parte END), 1) AS pct_comprador_principal,
       ROUND(100 * SUM(parte) FILTER (WHERE puesto <= 3), 1) AS pct_top3_paises
FROM ranking r
LEFT JOIN paises p USING (COD_PAIS)
GROUP BY r.HS4
HAVING SUM(fob) >= 1e6
ORDER BY fob_musd DESC;
