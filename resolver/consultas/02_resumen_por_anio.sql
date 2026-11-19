-- Pregunta: ¿cómo se reparten por año las líneas y el valor de lo que Antioquia vendió al exterior?
-- Datos: tabla lineas, con el filtro de la consulta 1
-- Cifra de control: 10 años; las filas suman 2.843.817 y el valor USD 62.715,5 M; 2025 = USD 10.364,2 M
SELECT ANIO, COUNT(*) AS filas, ROUND(SUM(FOB) / 1e6, 1) AS fob_musd
FROM lineas
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS NOT IN ('XCF', 'COL')
GROUP BY ANIO
ORDER BY ANIO;
