-- Pregunta: ¿la BD principal está completa y conserva sus cifras de control?
-- Datos: BD principal (python crear_bd_analitica.py → datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb)
-- Cifra de control: 3.613.237 líneas · USD 142.059,8 M · 113.790 líneas atípicas · 5.742 pesos y 6.534 cantidades
--   reconstruidos · 2.784 líneas con posible error de FOB · 13.305 empresas · 31 llaves primarias y 9 foráneas ·
--   0 relaciones con huérfanos · diferencia máxima con el DANE 0,009 %
SELECT orden, indicador, valor FROM (
  SELECT 1 AS orden, 'Líneas de declaración' AS indicador, count(*)::DOUBLE AS valor FROM hechos_analitica
  UNION ALL SELECT 2, 'FOB total (USD millones)', round(sum(VALOR_FOB_USD) / 1e6, 1) FROM hechos_analitica
  UNION ALL SELECT 3, 'Líneas con precio atípico (FLAG_ATIPICO)', count(*) FILTER (WHERE FLAG_ATIPICO) FROM hechos_analitica
  UNION ALL SELECT 4, 'Pesos reconstruidos', count(PESO_NETO_KGS_AJUSTADO) FROM hechos_analitica
  UNION ALL SELECT 5, 'Cantidades reconstruidas', count(CANTIDAD_UNIDADES_FISICAS_AJUSTADA) FROM hechos_analitica
  UNION ALL SELECT 6, 'Líneas con posible error de FOB', count(*) FILTER (WHERE FLAG_POSIBLE_ERROR_FOB) FROM hechos_analitica
  UNION ALL SELECT 7, 'Empresas en el directorio', count(*) FROM dim_exportador_analitica
  UNION ALL SELECT 8, 'Llaves primarias', count(*) FROM duckdb_constraints() WHERE constraint_type = 'PRIMARY KEY'
  UNION ALL SELECT 9, 'Llaves foráneas declaradas', count(*) FROM duckdb_constraints() WHERE constraint_type = 'FOREIGN KEY'
  UNION ALL SELECT 10, 'Relaciones con huérfanos', count(*) FILTER (WHERE FILAS_HUERFANAS > 0) FROM relaciones_llaves
  UNION ALL SELECT 11, 'Diferencia máxima con el DANE (%)', max(abs(DIF_PCT)) FROM vw_validacion_dane
)
ORDER BY orden;
