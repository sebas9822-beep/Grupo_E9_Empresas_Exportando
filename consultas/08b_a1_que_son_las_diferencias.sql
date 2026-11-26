-- Pregunta: ¿qué son las líneas que están en la definición 2 y no en la 1 (origen Antioquia con destino Colombia)?
-- Datos: hechos_2026_09.parquet de la BD depurada (tabla datos)
-- Cifra de control: 220 líneas y USD 86.409, todas por carretera, con comprador en Medellín (209) o Bogotá (11); 113 son sostenes y similares (partida 6212)
SELECT CIUDAD_DESTINATARIO,
       COD_MODO_TRANSPORTE,              -- 3 = terrestre (carretero)
       SUBSTR(SUBPARTIDA, 1, 4) AS partida,
       COUNT(*) AS lineas,
       ROUND(SUM(VALOR_FOB_USD), 0) AS fob_usd
FROM datos
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS_DESTINO = 'COL'
GROUP BY CIUDAD_DESTINATARIO, COD_MODO_TRANSPORTE, partida
ORDER BY lineas DESC;
