-- Pregunta: ¿qué sectores dependen más de pocos países, y cambió eso entre 2016 y 2025?
-- Datos: tabla ant, años 2016 y 2025; columna SECTOR (11 grupos armados con la partida arancelaria)
-- Cifra de control: 11 sectores × 2 años = 22 filas; oro 2025 = USD 4.159,9 M con 70,7 % en el top 3; flores 2025 = 84,3 %
WITH sector_pais AS (
  SELECT ANIO, SECTOR, COD_PAIS, SUM(FOB) AS fob
  FROM ant
  WHERE ANIO IN (2016, 2025)
  GROUP BY ANIO, SECTOR, COD_PAIS
),
ranking AS (
  SELECT *,
         fob / SUM(fob) OVER (PARTITION BY ANIO, SECTOR) AS parte,
         ROW_NUMBER() OVER (PARTITION BY ANIO, SECTOR ORDER BY fob DESC) AS puesto
  FROM sector_pais
)
SELECT SECTOR, ANIO,
       ROUND(SUM(fob) / 1e6, 1) AS fob_musd,
       COUNT(*) AS paises,
       ROUND(100 * SUM(parte) FILTER (WHERE puesto <= 3), 1) AS pct_top3_paises,
       ROUND(100 * SUM(parte) FILTER (WHERE COD_PAIS = 'USA'), 1) AS pct_eeuu
FROM ranking
GROUP BY SECTOR, ANIO
ORDER BY SECTOR, ANIO;
