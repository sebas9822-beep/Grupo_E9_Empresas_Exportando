# data/raw — datos crudos (no se versionan)

Pesan ~1,5 GB, así que Git los ignora. Hay dos formas de tenerlos:

1. **Descargarlos con el pipeline**: `python run_pipeline.py`. Los pasos 1, 2 y 5 los dejan aquí.
2. **Reutilizar una carpeta que ya los tenga**, como la carpeta *Datos descargados* de OneDrive. Basta con definir la variable de entorno `EXPO_RAW_DIR`:

```powershell
# Windows PowerShell
$env:EXPO_RAW_DIR = "C:\Users\...\EstudIA\fuente de datos\BD internacional\Datos descargados"
python run_pipeline.py --sin-descargas
```

## Estructura esperada

Es la misma de la carpeta *Datos descargados*:

```
01_DIAN_Exportaciones_mensuales/AAAA/MM_Exportaciones_AAAA_Mes.zip   bases mensuales DIAN (~40 MB c/u)
02_DIAN_Documentacion/                                              ficha técnica, ficha metodológica, correlativa
03_DANE_EXPO_microdatos/Expo_2025.zip                               opcional (sin NIT; no lo usa el pipeline)
04_datos_gov_co/                                                    RUES, Supersociedades, DIVIPOLA, cámaras de comercio
06_DIAN_Directorio_Imp_Exp/Directorio-Exportadores-AAAA.zip         directorio anual DIAN (referencia)
07_fuentes_v2/                                                      MinCIT NME, MinAgricultura, SECOP II por NIT
```

Los CSV pueden estar comprimidos en un `.zip` con el mismo nombre. Así quedaron en OneDrive el RUES de Antioquia y los dos archivos de MinAgricultura, y el pipeline los descomprime solo.
