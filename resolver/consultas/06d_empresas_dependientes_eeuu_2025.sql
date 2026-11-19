-- Pregunta: ¿cuántas empresas venden la mitad o más de lo suyo a EE. UU.?
-- Datos: tabla ant, 2025, empresas (NIT) con al menos USD 10.000 exportados
-- Cifra de control: 520 empresas con la mitad o más; 263 de ellas venden solo a EE. UU.
WITH total_empresa AS (
  SELECT NIT, SUM(FOB) AS fob_total
  FROM ant WHERE ANIO = 2025 AND NIT IS NOT NULL
  GROUP BY NIT HAVING SUM(FOB) >= 10000
),
a_eeuu AS (
  SELECT NIT, SUM(FOB) AS fob_eeuu
  FROM ant WHERE ANIO = 2025 AND COD_PAIS = 'USA'
  GROUP BY NIT
)
SELECT COUNT(*) FILTER (WHERE fob_eeuu / fob_total >= 0.5) AS empresas_mitad_o_mas_a_eeuu,
       COUNT(*) FILTER (WHERE fob_eeuu / fob_total >= 0.999) AS empresas_solo_eeuu
FROM total_empresa JOIN a_eeuu USING (NIT);
