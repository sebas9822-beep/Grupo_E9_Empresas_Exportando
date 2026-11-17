-- Pregunta: ¿cuántas empresas antioqueñas exportaron al menos USD 1.000 cada año?
-- Datos: vista vw_directorio_antioquia (3.195 empresas con vínculo A o B)
-- Cifra de control: 2024 = 2.316 (A+B), comparable con las 2.395 de Analdex; 2026 llega hasta septiembre
SELECT 2024 AS anio, COUNT(*) FILTER (WHERE EXPORTADOR_2024_MIN_1000USD) AS empresas_a_b,
       COUNT(*) FILTER (WHERE EXPORTADOR_2024_MIN_1000USD AND EMPRESA_ANTIOQUENA) AS empresas_a
FROM vw_directorio_antioquia
UNION ALL
SELECT 2025, COUNT(*) FILTER (WHERE EXPORTADOR_2025_MIN_1000USD),
       COUNT(*) FILTER (WHERE EXPORTADOR_2025_MIN_1000USD AND EMPRESA_ANTIOQUENA)
FROM vw_directorio_antioquia
UNION ALL
SELECT 2026, COUNT(*) FILTER (WHERE EXPORTADOR_2026_MIN_1000USD),
       COUNT(*) FILTER (WHERE EXPORTADOR_2026_MIN_1000USD AND EMPRESA_ANTIOQUENA)
FROM vw_directorio_antioquia
ORDER BY anio;
