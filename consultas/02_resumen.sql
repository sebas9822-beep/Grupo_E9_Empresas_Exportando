-- Pregunta: ¿cómo se reparte por país de destino la mercancía de origen Antioquia vendida al exterior en septiembre de 2026?
-- Datos: datos/limpios/bd_depurada/hechos_exportaciones/hechos_2026_09.parquet (tabla datos), con el mismo filtro de la consulta 1
-- Cifra de control: los 109 países suman 26.152 filas, igual que la consulta 1 (USD 1.220,1 M en total)
SELECT COD_PAIS_DESTINO, COUNT(*) AS filas, ROUND(SUM(VALOR_FOB_USD) / 1e6, 1) AS fob_musd
FROM datos
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
GROUP BY COD_PAIS_DESTINO
ORDER BY fob_musd DESC;
