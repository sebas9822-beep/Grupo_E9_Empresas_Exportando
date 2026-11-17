-- Pregunta: ¿cada línea de exportación encuentra su empresa al unir los hechos con el directorio?
-- Datos: hechos_exportaciones (3.613.237 filas) unida con dim_exportador (13.305 filas; NIT no se repite)
-- Conteo antes y después de unir: 3.613.237 filas antes y 3.613.237 después con LEFT JOIN (la unión no duplica)
-- Cifra de control: 16.714 líneas quedan sin empresa: son las personas naturales (sin NIT);
--   empresas USD 141.812,2 M + personas naturales USD 247,6 M = USD 142.059,8 M
SELECT e.NIT IS NOT NULL AS tiene_empresa,
       COUNT(*) AS lineas,
       ROUND(SUM(h.VALOR_FOB_USD) / 1e6, 1) AS fob_musd
FROM hechos_exportaciones AS h
LEFT JOIN dim_exportador AS e ON e.NIT = h.NIT_EXPORTADOR
GROUP BY tiene_empresa
ORDER BY tiene_empresa DESC;
