-- Pregunta: ¿cuántas empresas exportadoras de Antioquia dependen de un solo país, y cambió eso entre 2016 y 2025?
-- Datos: tabla ant, empresas (NIT) con al menos USD 10.000 exportados en el año
-- Cifra de control: 2025 = 2.049 empresas; 44,6 % vende a un solo país; 84,7 % vende la mitad o más a un solo país
WITH empresa_pais AS (
  SELECT ANIO, NIT, COD_PAIS, SUM(FOB) AS fob
  FROM ant WHERE NIT IS NOT NULL
  GROUP BY ANIO, NIT, COD_PAIS
),
empresas AS (
  SELECT ANIO, NIT, SUM(fob) AS fob_total, COUNT(*) AS n_paises, MAX(fob) / SUM(fob) AS parte_pais_principal
  FROM empresa_pais
  GROUP BY ANIO, NIT
  HAVING SUM(fob) >= 10000
)
SELECT ANIO,
       COUNT(*) AS empresas,
       ROUND(100 * AVG(CASE WHEN n_paises = 1 THEN 1 ELSE 0 END), 1) AS pct_un_solo_pais,
       ROUND(100 * AVG(CASE WHEN parte_pais_principal >= 0.5 THEN 1 ELSE 0 END), 1) AS pct_mitad_o_mas_en_un_pais,
       MEDIAN(n_paises) AS mediana_paises
FROM empresas
WHERE ANIO IN (2016, 2025)
GROUP BY ANIO
ORDER BY ANIO;
