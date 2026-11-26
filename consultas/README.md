# consultas

Consultas SQL del proyecto (sesión 3). Una consulta por archivo `.sql`, con un comentario arriba que dice qué pregunta responde, qué datos usa y qué cifra de control devuelve.

| Archivo | Pregunta | Datos |
|---|---|---|
| `01_mirar_muestra.sql` | ¿Cuántas líneas de la muestra son de empresas y cuántas de personas naturales? | Muestra en `datos/originales/` (tabla `datos` en Colab) |
| `02_fob_por_anio.sql` | ¿Cuánto exportó Colombia cada año y qué parte fue de origen Antioquia? | BD depurada |
| `03_antioquia_por_sector_2026.sql` | ¿Cuánto exportaron en 2026 las empresas antioqueñas por sector? | BD depurada |
| `04_top10_por_sector_2026.sql` | Top 10 de empresas antioqueñas por sector en 2026 y qué exportaron | BD depurada |
| `05_union_hechos_directorio.sql` | ¿La unión de hechos y directorio conserva todas las líneas? | BD depurada |
| `06_exportadores_antioquenos_por_anio.sql` | ¿Cuántas empresas antioqueñas exportaron al menos USD 1.000 por año? | BD depurada |
| `07_bd_principal.sql` | ¿La BD principal está completa y conserva sus cifras de control? | **BD principal** |
| `01_mirar.sql` | ¿Cuántas líneas de septiembre de 2026 son de mercancía de origen Antioquia vendida al exterior? | Hechos de sep-2026 de la BD depurada (tabla `datos` en Colab) |
| `02_resumen.sql` | ¿Cómo se reparte esa mercancía por país de destino? | Hechos de sep-2026 de la BD depurada (tabla `datos` en Colab) |
| `08_a1_dos_definiciones.sql` | Reto A1: ¿las dos definiciones de origen Antioquia dan lo mismo? | Hechos de sep-2026 (tabla `datos`) |
| `08b_a1_que_son_las_diferencias.sql` | Reto A1: ¿qué son las 220 líneas de diferencia? | Hechos de sep-2026 (tabla `datos`) |
| `09_a2_niveles_de_producto.sql` | Reto A2: subpartida, partida o capítulo, ¿cuántos productos y cuántos con 3 países o menos? | Hechos de sep-2026 (tabla `datos`) |
| `10_a3_mediana_vs_ponderada.sql` | Reto A3: mediana frente a concentración ponderada por FOB | Hechos de sep-2026 (tabla `datos`) |
| `11_a4_union_infla.sql` | Reto A4: ¿cuánto infla la unión si un país se repite en la tabla de países? | Hechos de sep-2026 (`datos`) y `dim_pais.parquet` (`paises`) |
| `11b_a4_chequeo_llave.sql` | Reto A4: el chequeo de llave antes de unir | `dim_pais.parquet` (tabla `paises`) |
| `12_a5_partida_mayor.sql` | Reto A5: ¿qué parte del FOB es una sola partida? | Hechos de sep-2026 (tabla `datos`) |
| `12b_a5_con_y_sin_oro.sql` | Reto A5: concentración en 3 países con y sin el oro | Hechos de sep-2026 (tabla `datos`) |

**Retos de la sesión 4 (08 a 12).** Corren en el cuaderno con `datos` y `paises` cargados en la celda 2 como dice el reto: `datos = pd.read_parquet(".../hechos_exportaciones/hechos_2026_09.parquet")` y `paises = pd.read_parquet(".../dim_pais.parquet")`. Las respuestas están en [retos/S4_retos_avanzados.md](../retos/S4_retos_avanzados.md).

**Cómo correrlas.** `01_mirar_muestra.sql` corre en el cuaderno `notebooks/01_consultas.ipynb` con la muestra cargada. `01_mirar.sql` y `02_resumen.sql` (guía 2 de la sesión 3) corren en el mismo cuaderno cargando en la celda 2 la tabla de hechos de septiembre de 2026 con `datos = pd.read_parquet("https://raw.githubusercontent.com/sebas9822-beep/Grupo_E9_Empresas_Exportando/main/datos/limpios/bd_depurada/hechos_exportaciones/hechos_2026_09.parquet")`; el paso a paso está en [docs/guia_s3_dos_consultas_bd_depurada.md](../docs/guia_s3_dos_consultas_bd_depurada.md). Las demás (de `02_fob_por_anio.sql` a `07_bd_principal.sql`) corren sobre la **BD principal**, que es la base de trabajo del proyecto ([docs/bd_principal_capa_analitica.md](../docs/bd_principal_capa_analitica.md)):

```bash
python crear_bd_analitica.py   # una vez: arma datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb
```

```python
import duckdb
con = duckdb.connect("datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb", read_only=True)
con.sql(open("consultas/07_bd_principal.sql", encoding="utf-8").read()).show()
```

Las consultas 02 a 06 se escribieron sobre la BD depurada y dan el mismo resultado en la principal (verificado). Solo la 05 cambia: en la principal, `hechos_exportaciones` se llama `hechos_analitica` y `dim_exportador` se llama `dim_exportador_analitica`.
