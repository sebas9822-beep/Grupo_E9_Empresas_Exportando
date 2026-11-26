-- Pregunta: antes de unir, ¿el código de país se repite en la tabla de países?
-- Datos: dim_pais.parquet (tabla paises)
-- Cifra de control: 215 filas y 215 códigos distintos (ninguno repetido); si salieran 216 filas y 215 códigos, la unión duplicaría las líneas del código repetido
SELECT COUNT(*) AS filas,
       COUNT(DISTINCT COD_PAIS) AS codigos_distintos,
       COUNT(*) - COUNT(DISTINCT COD_PAIS) AS repetidos
FROM paises;
