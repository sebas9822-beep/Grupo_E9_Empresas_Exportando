-- Pregunta: ¿cuánto perdería Antioquia, en valor y en % de sus ventas, si cada uno de sus principales compradores dejara de importar?
-- Datos: tabla ant, año 2025; tabla paises para el nombre
-- Cifra de control: EE. UU. = USD 2.998,5 M (28,9 % del total y 30,2 % sin minero-energético); Canadá = USD 935,6 M (9,0 %)
WITH b AS (SELECT * FROM ant WHERE ANIO = 2025)
SELECT p.PAIS,
       ROUND(SUM(b.FOB) / 1e6, 1) AS perdida_directa_musd,
       ROUND(100 * SUM(b.FOB) / (SELECT SUM(FOB) FROM b), 1) AS pct_total,
       ROUND(100 * SUM(b.FOB) FILTER (WHERE NOT b.ES_ME) / (SELECT SUM(FOB) FROM b WHERE NOT ES_ME), 1) AS pct_no_minero_energetico
FROM b
JOIN paises p USING (COD_PAIS)
GROUP BY p.PAIS
ORDER BY perdida_directa_musd DESC
LIMIT 8;
