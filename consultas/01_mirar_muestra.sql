-- Pregunta: ¿cuántas líneas de la muestra son de empresas y cuántas de personas naturales?
-- Datos: datos/originales/muestra_dian_exportaciones_2026_09.csv (1.000 filas; en Colab la tabla se llama datos)
-- Cifra de control: 1.000 filas en total; 995 de empresas y 5 de personas naturales
SELECT CASE WHEN RAZON_SOCIAL_EXPORTADOR = 'PERSONA NATURAL' THEN 'Persona natural' ELSE 'Empresa' END AS tipo,
       COUNT(*) AS filas
FROM datos
GROUP BY tipo
ORDER BY filas DESC;
