-- Pregunta: ¿qué productos componen lo que Antioquia le vende a EE. UU.?
-- Datos: tabla ant, 2025, país USA
-- Cifra de control: oro 47,3 %, café 16,8 % y flores 10,4 % de lo que compra EE. UU.
SELECT HS4 AS partida,
       ROUND(SUM(FOB) / 1e6, 1) AS fob_a_eeuu_musd,
       ROUND(100 * SUM(FOB) / SUM(SUM(FOB)) OVER (), 1) AS pct_de_lo_que_compra_eeuu
FROM ant
WHERE ANIO = 2025 AND COD_PAIS = 'USA'
GROUP BY HS4
ORDER BY fob_a_eeuu_musd DESC
LIMIT 5;
