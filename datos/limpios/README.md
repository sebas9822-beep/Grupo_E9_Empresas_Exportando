# datos/limpios

Aquí quedan los datos después de limpiarlos. Cada archivo de esta carpeta se produce con código (`pipeline/p09_bd_depurada.py` y `pipeline/p10_capa_analitica.py`), nunca a mano.

> **La BD principal para trabajar es `bd_analitica/`** (capa analítica sobre la depurada). Se arma con `python crear_bd_analitica.py`. Qué contiene y cómo se construyó: [docs/bd_principal_capa_analitica.md](../../docs/bd_principal_capa_analitica.md). Qué se limpió y por qué está en [bitacora.md](../../bitacora.md) y en [docs/limpieza_bd_depurada.md](../../docs/limpieza_bd_depurada.md).

| Archivo | Qué es |
|---|---|
| `bd_analitica/hechos_analitica_complemento.parquet` | **BD principal:** las 12 columnas que la capa agrega a los hechos (banderas de atípicos y magnitudes ajustadas), por `ID_REGISTRO`. Los hechos de base se leen de `bd_depurada/`, para no repetirlos |
| `bd_analitica/<tabla>.parquet` | **BD principal:** directorio analítico, catálogos `cat_*`, panel empresa-mes, empresa-país, empresa-producto, ciudades, referencias del DANE, log, diccionario y relaciones de llaves |
| `bd_analitica/esquema.sql` | **BD principal:** tablas con sus llaves y vistas, en orden de creación |
| `nit_ciudad_comprador_por_completar.csv` | 2.051 NIT cuyas ventas al exterior no tienen una ciudad del comprador confiable (separado por coma) |
| `bd_depurada/hechos_exportaciones/hechos_AAAA_MM.parquet` | Tabla de hechos: una fila por ítem de declaración. Un archivo por mes, 33 meses y 3.613.237 filas en total |
| `bd_depurada/dim_*.parquet`, `catalogo_codigos.parquet` | Directorio de empresas (`dim_exportador`), productos, países, zonas francas, departamentos, municipios, aduanas y agencias |
| `bd_depurada/log_depuracion.parquet`, `diccionario_datos.parquet`, `info_bd.parquet` | Reglas de limpieza aplicadas, diccionario y metadatos |
| `bd_depurada/ref_*.parquet` | Cifras oficiales de MinCIT y MinAgricultura para validar |
| `directorio_exportadores_antioquenos.csv` / `.xlsx` | Las 3.195 empresas antioqueñas (vínculo A o B), una por fila; el Excel trae además la serie mensual y el diccionario |
| `serie_mensual_antioquia.csv` | FOB y número de exportadores por mes |
| `validacion_mincit_nme.csv`, `validacion_madr_agricolas.csv` | Cuadre contra las cifras oficiales |
| `cobertura.json` | Periodo cubierto, totales y fecha de proceso |

## La BD en un solo archivo

```bash
pip install -r requirements.txt
python crear_bd_analitica.py   # BD PRINCIPAL: bd_analitica/BD_exportaciones_Colombia_analitica.duckdb (~375 MB, no se sube)
python crear_bd_depurada.py    # solo la depurada: bd_depurada/BD_exportaciones_Colombia_depurada.duckdb (~270 MB, no se sube)
```

Empieza por la vista `vw_exportaciones`: la tabla de hechos con todos los nombres (empresa, país, producto, sector, aduana…).
