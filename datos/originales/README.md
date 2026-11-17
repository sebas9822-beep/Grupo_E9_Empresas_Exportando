# datos/originales

Aquí van los datos **tal como se descargaron**. No se modifican: si hay que corregir algo, se hace con código y el resultado va a `datos/limpios/`.

## Lo que está en GitHub: una muestra

- `muestra_dian_exportaciones_2026_09.csv`: las primeras **1.000 filas** del archivo DIAN `09_Exportaciones_2026_Septiembre.zip`, que tiene 115.049. Cada fila es un ítem de una declaración de exportación.
- Trae **70 de las 72 columnas** de la DIAN, con sus valores originales. Se omitieron `RAZON_SOCIAL_DESTINATARIO` y `DOMICILIO_DESTINATARIO` porque pueden ser el nombre y la dirección de una persona. `DIREC_EXPORTADOR` va vacía en las líneas de personas naturales. Es la regla del repositorio público: nada de datos personales.
- No es una muestra sintética: son datos reales y públicos de la DIAN.
- Cifra de control: 1.000 filas, 995 de empresas y 5 de personas naturales, y 140 con mercancía de origen Antioquia.

Las columnas se describen en [diccionario.md](../../diccionario.md) y en [docs/diccionario_transaccional.csv](../../docs/diccionario_transaccional.csv).

## Los archivos completos: no se suben

Pesan cerca de 1,5 GB, así que Git los ignora. Hay dos formas de tenerlos en esta carpeta:

1. **Descargarlos con el proceso completo**: `python run_pipeline.py`. Los pasos 1, 2 y 5 los dejan aquí.
2. **Usar una carpeta que ya los tenga**, como *Datos descargados* en OneDrive, con la variable de entorno `EXPO_RAW_DIR`:

```powershell
$env:EXPO_RAW_DIR = "C:\Users\...\EstudIA\fuente de datos\BD internacional\Datos descargados"
python run_pipeline.py --sin-descargas
```

Estructura esperada, la misma de *Datos descargados*:

```
01_DIAN_Exportaciones_mensuales/AAAA/MM_Exportaciones_AAAA_Mes.zip   bases mensuales DIAN (~40 MB c/u)
02_DIAN_Documentacion/                                              ficha técnica, ficha metodológica, correlativa
03_DANE_EXPO_microdatos/Expo_2025.zip                               opcional (sin NIT; no lo usa el proceso)
04_datos_gov_co/                                                    RUES, Supersociedades, DIVIPOLA, cámaras de comercio
06_DIAN_Directorio_Imp_Exp/Directorio-Exportadores-AAAA.zip         directorio anual DIAN (referencia)
07_fuentes_v2/                                                      MinCIT NME, MinAgricultura, SECOP II por NIT
```

Los CSV pueden venir comprimidos en un `.zip` con el mismo nombre; el proceso los descomprime solo.
