# datos/limpios

Aquí quedan los datos después de limpiarlos. Cada archivo de esta carpeta se produce con código (`pipeline/p09_bd_depurada.py`), nunca a mano. Qué se limpió y por qué está en [bitacora.md](../../bitacora.md) y en [docs/limpieza_bd_depurada.md](../../docs/limpieza_bd_depurada.md).

| Archivo | Qué es |
|---|---|
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
python crear_bd_depurada.py    # crea bd_depurada/BD_exportaciones_Colombia_depurada.duckdb (~270 MB, no se sube)
```

Empieza por la vista `vw_exportaciones`: la tabla de hechos con todos los nombres (empresa, país, producto, sector, aduana…).
