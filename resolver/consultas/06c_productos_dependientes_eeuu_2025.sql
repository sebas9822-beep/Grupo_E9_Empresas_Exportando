-- Pregunta: ¿cuántos productos venden la mitad o más a EE. UU.?
-- Datos: tabla ant, 2025, productos de al menos USD 1 M
-- Cifra de control: 29 productos, que suman USD 871,7 M
WITH total_producto AS (
  SELECT HS4, SUM(FOB) AS fob_total
  FROM ant WHERE ANIO = 2025
  GROUP BY HS4 HAVING SUM(FOB) >= 1e6
),
a_eeuu AS (
  SELECT HS4, SUM(FOB) AS fob_eeuu
  FROM ant WHERE ANIO = 2025 AND COD_PAIS = 'USA'
  GROUP BY HS4
)
SELECT COUNT(*) AS productos_que_venden_la_mitad_o_mas_a_eeuu,
       ROUND(SUM(fob_total) / 1e6, 1) AS fob_de_esos_productos_musd
FROM total_producto JOIN a_eeuu USING (HS4)
WHERE fob_eeuu / fob_total >= 0.5;
