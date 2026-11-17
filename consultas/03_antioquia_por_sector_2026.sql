-- Pregunta: ¿cuánto exportaron en 2026 las empresas antioqueñas en cada sector?
-- Datos: vista vw_exportaciones, empresas con domicilio en Antioquia (vínculo A), enero a septiembre de 2026
-- Cifra de control: los sectores suman USD 9.755,5 M de 1.760 empresas distintas
--   (una empresa que exporta en dos sectores se cuenta en ambos, por eso la columna empresas suma más de 1.760)
SELECT SECTOR_EXPORTACION,
       COUNT(DISTINCT NIT_EXPORTADOR) AS empresas,
       ROUND(SUM(VALOR_FOB_USD) / 1e6, 1) AS fob_musd
FROM vw_exportaciones
WHERE EMPRESA_ANTIOQUENA AND ANIO = 2026
GROUP BY SECTOR_EXPORTACION
ORDER BY fob_musd DESC;
