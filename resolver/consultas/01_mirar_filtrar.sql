-- Pregunta: ¿cuántas líneas de exportación de 2016 a 2025 son de mercancía de origen Antioquia vendida al exterior?
-- Datos: tabla lineas (10.981.096 filas: todos los departamentos y destinos, 2016-2025)
-- Cifra de control: 10.981.096 filas en total y 2.843.817 después del filtro (origen Antioquia, sin zonas francas ni destino Colombia)
SELECT ANIO, MES, NIT, SUBPARTIDA, COD_PAIS, FOB
FROM lineas
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS NOT IN ('XCF', 'COL');
