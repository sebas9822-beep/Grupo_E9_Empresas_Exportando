-- Pregunta: ¿cuántas líneas de exportación de septiembre de 2026 son de mercancía de origen Antioquia vendida al exterior?
-- Datos: datos/limpios/bd_depurada/hechos_exportaciones/hechos_2026_09.parquet (115.049 filas; en Colab la tabla se llama datos)
-- Cifra de control: 115.049 filas en total y 26.152 después del filtro (origen Antioquia, sin zonas francas ni destino Colombia)
SELECT SUBPARTIDA, COD_PAIS_DESTINO, VALOR_FOB_USD, PESO_NETO_KGS
FROM datos
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL');
