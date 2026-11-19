-- Pregunta: ¿qué tan concentrados están en general los productos de Antioquia cada año, y cambió eso entre 2016 y 2025?
-- Datos: tabla ant, 2016-2025
-- Cifra de control: 2025 = 225 productos; 70,1 % ponderado; 73,1 % mediana; 52 productos con 90 % o más; 78 con un país de 50 % o más
WITH producto_pais AS (
  SELECT ANIO, HS4, COD_PAIS, SUM(FOB) AS fob
  FROM ant
  
  GROUP BY ANIO, HS4, COD_PAIS
  HAVING SUM(FOB) > 0
),
ranking AS (
  SELECT *,
         fob / SUM(fob) OVER (PARTITION BY ANIO, HS4) AS parte,
         ROW_NUMBER() OVER (PARTITION BY ANIO, HS4 ORDER BY fob DESC) AS puesto
  FROM producto_pais
),
productos AS (
  SELECT ANIO, HS4, SUM(fob) AS fob_producto,
         SUM(parte) FILTER (WHERE puesto <= 3) AS top3,
         MAX(parte) AS parte_principal
  FROM ranking
  GROUP BY ANIO, HS4
  HAVING SUM(fob) >= 1e6
)
SELECT ANIO,
       COUNT(*) AS productos,
       ROUND(100 * SUM(fob_producto * top3) / SUM(fob_producto), 1) AS pct_top3_ponderado,
       ROUND(100 * MEDIAN(top3), 1) AS pct_top3_mediana,
       COUNT(*) FILTER (WHERE top3 >= 0.9) AS productos_90_o_mas,
       ROUND(100 * SUM(fob_producto) FILTER (WHERE top3 >= 0.9) / SUM(fob_producto), 1) AS pct_valor_90_o_mas,
       COUNT(*) FILTER (WHERE parte_principal >= 0.5) AS productos_un_pais_50_o_mas
FROM productos
GROUP BY ANIO
ORDER BY ANIO;
