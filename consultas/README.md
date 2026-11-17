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

**Cómo correrlas.** La 01 corre en el cuaderno `notebooks/01_consultas.ipynb` con la muestra cargada. Las demás corren sobre la BD depurada:

```bash
python crear_bd_depurada.py   # una vez: arma datos/limpios/bd_depurada/BD_exportaciones_Colombia_depurada.duckdb
```

```python
import duckdb
con = duckdb.connect("datos/limpios/bd_depurada/BD_exportaciones_Colombia_depurada.duckdb", read_only=True)
con.sql(open("consultas/02_fob_por_anio.sql", encoding="utf-8").read()).show()
```
