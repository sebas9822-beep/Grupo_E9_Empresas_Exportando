# Guía 2 · Tus dos consultas — Grupo E9 (BD depurada)

Sesión 3 · 19 de noviembre de 2026 · Equipo E9

Hoy consultamos la tabla de hechos de la BD depurada de septiembre de 2026: 115.049 líneas de exportación, de las cuales 26.152 son de mercancía de origen Antioquia vendida al exterior (USD 1.220,1 millones). La consulta 1 filtra esas líneas y la consulta 2 las reparte por país de destino: 109 países, y Estados Unidos, Italia y Canadá suman el 53,0 % del valor.

Las consultas quedaron en [`consultas/01_mirar.sql`](../consultas/01_mirar.sql) y [`consultas/02_resumen.sql`](../consultas/02_resumen.sql), cada una en su propio pull request con el profesor como revisor.

## Para ir a la sala: los tres requisitos

- [x] **La tabla carga en Colab:** la celda 3 da **115.049 filas** (61 columnas), igual que el diccionario para septiembre de 2026.
- [x] **Una tabla para hoy:** la tabla de hechos de la BD depurada, septiembre de 2026 (`hechos_2026_09.parquet`).
- [x] **Cada fila es** un ítem (línea) de una declaración de exportación de la DIAN: un producto (subpartida arancelaria) que una empresa envió a un país en septiembre de 2026, con su valor FOB en dólares, su peso y el departamento donde se produjo la mercancía.

## 1. Una tabla para hoy

Elegimos la **tabla de hechos de la BD depurada de septiembre de 2026** (`datos/limpios/bd_depurada/hechos_exportaciones/hechos_2026_09.parquet`).

| Pregunta | Respuesta |
| --- | --- |
| ¿Tiene la cifra que responde tu pregunta principal? | Sí. La pregunta es qué porcentaje de cada producto va a sus tres principales países compradores, y cada fila trae el producto (`SUBPARTIDA`), el país (`COD_PAIS_DESTINO`) y el valor (`VALOR_FOB_USD`). |
| ¿Carga en Colab? | Sí: 115.049 filas y 61 columnas, en pocos segundos (4 MB). Como es parquet, se carga con `pd.read_parquet` (sección 2). |
| ¿Puedes completar «cada fila es…»? | Sí: un ítem de una declaración de exportación de la DIAN, con producto, país, valor y origen. |

Las demás fuentes quedaron en la bitácora, sección Decisiones.

**Ojo: ¿la tabla ya viene contada?** No trae una columna de cantidad de registros, así que `COUNT(*)` cuenta líneas. Pero una declaración ocupa varias filas, una por producto. Para contar declaraciones se usa `COUNT(DISTINCT NUMERO_FORMULARIO)`, para contar empresas `COUNT(DISTINCT NIT_EXPORTADOR)`, y para el valor `SUM(VALOR_FOB_USD)`.

## 2. Carga la tabla en el cuaderno

1. Abre el cuaderno del proyecto (`notebooks/01_consultas.ipynb`) y corre la **celda 1** sin cambios.
2. **Celda 2:** reemplaza su contenido por esto. Así la tabla se sigue llamando `datos` y las celdas 3 a 9 funcionan igual:

```python
# Celda 2 · Cargar la tabla de hoy: hechos de septiembre de 2026 de la BD depurada
ENLACE = "https://raw.githubusercontent.com/sebas9822-beep/Grupo_E9_Empresas_Exportando/main/datos/limpios/bd_depurada/hechos_exportaciones/hechos_2026_09.parquet"
datos = pd.read_parquet(ENLACE)
print(f"Cargué {len(datos)} filas y {len(datos.columns)} columnas.")
datos.head()
```

3. **Celda 3:** debe dar **115.049** filas.
4. **Celda 4:** los nombres de las columnas. Las de hoy son `COD_DEPTO_ORIGEN` (departamento donde se produjo la mercancía; Antioquia es `'05'`), `COD_PAIS_DESTINO` (código de país de tres letras; `'XCF'` = zona franca en Colombia y `'COL'` = destino Colombia), `SUBPARTIDA`, `VALOR_FOB_USD` y `PESO_NETO_KGS`.

## 3. Consulta 1 · Mirar y filtrar

El filtro deja solo la mercancía de origen Antioquia que sale del país: departamento de origen `'05'` (el criterio del DANE y MinCIT) y sin zonas francas colombianas ni destino Colombia, porque esas líneas no son ventas al exterior.

**Celda 5** · filas antes del filtro → **115.049**

```python
sql("""
SELECT COUNT(*) AS filas_total
FROM datos
""")
```

**Celda 6** · filas después del filtro → **26.152**

```python
sql("""
SELECT COUNT(*) AS filas_filtradas
FROM datos
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
""")
```

**Celda 7** · las filas filtradas, solo con las columnas necesarias

```python
sql("""
SELECT SUBPARTIDA, COD_PAIS_DESTINO, VALOR_FOB_USD, PESO_NETO_KGS
FROM datos
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
LIMIT 10
""")
```

**Cifra de control:** 26.152 es menor que 115.049. El filtro quitó 88.897 líneas: 88.411 de otros departamentos, 266 de Antioquia a zonas francas y 220 de Antioquia con destino Colombia.

## 4. La consulta 1 por PR

- **Archivo:** `consultas/01_mirar.sql` · **rama:** `consulta-1` · **revisor:** `santiagom26cc`.
- **Mensaje del commit:** Consulta 1: 26.152 de 115.049 líneas de sep-2026 son de mercancía antioqueña vendida al exterior.
- **Título del PR:** En septiembre de 2026, 26.152 de las 115.049 líneas exportadas son de mercancía antioqueña vendida al exterior.
- **Descripción:** la cifra de control (115.049 filas en total y 26.152 después del filtro) y cómo se comprobó (celdas 5 y 6; las 88.897 líneas que salen son 88.411 de otros departamentos, 266 de Antioquia a zonas francas y 220 de Antioquia con destino Colombia).

## 5. Consulta 2 · Resumir

Agrupa las mismas 26.152 líneas por país de destino, con el **mismo WHERE** de la consulta 1. Cuenta líneas y suma el valor, porque la pregunta principal es sobre qué parte del valor se llevan los principales compradores.

**Celda 8** · resumen por país

```python
sql("""
SELECT COD_PAIS_DESTINO, COUNT(*) AS filas, ROUND(SUM(VALOR_FOB_USD) / 1e6, 1) AS fob_musd
FROM datos
WHERE COD_DEPTO_ORIGEN = '05'
  AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
GROUP BY COD_PAIS_DESTINO
ORDER BY fob_musd DESC
""")
```

Resultado: 109 países. Los tres primeros por valor:

| País | Líneas | FOB (USD M) | % del valor |
| --- | --- | --- | --- |
| USA (Estados Unidos) | 7.742 | 320,3 | 26,3 % |
| ITA (Italia) | 182 | 204,1 | 16,7 % |
| CAN (Canadá) | 926 | 121,9 | 10,0 % |
| **Los tres** | **8.850** | **646,3** | **53,0 %** |

**Celda 9** · cifra de control: ¿los grupos suman lo mismo que la consulta 1? → **26.152**

```python
sql("""
SELECT SUM(filas) AS suma_de_los_grupos
FROM (
    SELECT COD_PAIS_DESTINO, COUNT(*) AS filas
    FROM datos
    WHERE COD_DEPTO_ORIGEN = '05'
      AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')
    GROUP BY COD_PAIS_DESTINO
)
""")
```

Si suman el FOB de los grupos a mano les dará USD 1.219,9 M y no 1.220,1 M, porque cada grupo está redondeado a un decimal. La cifra de control son las filas.

**PR de la consulta 2:** archivo `consultas/02_resumen.sql`, rama `consulta-2`, revisor `santiagom26cc`. Quien construye escribe la consulta; quien verifica corre la celda 9 y suma los grupos.

## Antes de abrir cada PR

- [x] **Los tres comentarios:** pregunta, datos y cifra de control están en los dos archivos.
- [x] **Corre en Colab sin error:** las dos consultas se probaron sobre el mismo archivo de GitHub (115.049 filas, 26.152 filtradas, 109 países).
- [x] **Cifra de control en la descripción del PR.**
- [x] **Nada de datos personales ni contraseñas:** las consultas no muestran nombres ni NIT. Las personas naturales no tienen NIT publicado en la BD depurada.

**Pregunta de control:** ¿qué representa una fila del resultado y de qué filas sale cada suma?

> En la consulta 2, cada fila del resultado es un país de destino. Su número de `filas` es cuántas líneas de declaración de mercancía de origen Antioquia vendida al exterior fueron a ese país en septiembre de 2026, y `fob_musd` es la suma del valor de esas líneas. Cada suma sale de las 26.152 líneas que deja el filtro de la consulta 1, y los 109 países las reparten sin que sobre ni falte ninguna.
