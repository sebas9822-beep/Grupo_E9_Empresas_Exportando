# Fuentes

## Usadas en el pipeline

| # | Fuente | Qué aporta | Paso | Búsqueda |
|---|---|---|---|---|
| 1 | [DIAN · Bases estadísticas de exportaciones](https://www.dian.gov.co/dian/cifras/Paginas/Bases-Estadisticas-de-Comercio-Exterior-Importaciones-y-Exportaciones.aspx) | Líneas de declaración con NIT, razón social, subpartida, país, FOB, kilos, aduana y departamento de origen (72 variables) | 1 | 1 |
| 2 | [DIAN · Directorio de exportadores](https://www.dian.gov.co/dian/cifras/Paginas/Directorio-de-Importadores-Exportadores.aspx) | Listado anual 2017 en adelante (referencia histórica; no trae departamento) | 1 | 1 |
| 3 | [RUES · Confecámaras](https://www.datos.gov.co/d/c82u-588k) | Cámara de comercio, matrícula, CIIU, estado. Se usa para el domicilio de cada empresa | 2 y 5 | 1 |
| 4 | [Supersociedades · 10.000 empresas más grandes](https://www.datos.gov.co/d/6cat-2gcs) | Macrosector, ingresos y activos | 2 | 1 |
| 5 | [DIVIPOLA](https://www.datos.gov.co/d/gdxc-w37w) | Nombres de municipios | 2 | 1 |
| 6 | Cámaras de comercio antioqueñas (bzeh-ecuk, pb3w-3vmc, 2zc9-bpzw, wed5-aysq, fkdi-8hm8, ssvh-3gwc, we9a-3bys, 5aa8-pf7p) | Estructura empresarial y NIT/CIIU/empleados (contexto; no entran al directorio) | 2 | 1 |
| 7 | [MinCIT · Exportaciones no minero-energéticas](https://www.datos.gov.co/d/vwqt-xc3z) | Serie trimestral oficial: calibración de la bandera minero-energética y validación | 2 | 2 |
| 8 | MinAgricultura · Exportaciones agrícolas ([rfip-pkv5](https://www.datos.gov.co/d/rfip-pkv5), [5fct-ib9u](https://www.datos.gov.co/d/5fct-ib9u)) | Clasificación agrícola por subpartida, producto y tradicional/no tradicional; validación | 2 | 2 |
| 9 | [SECOP II · Contratos](https://www.datos.gov.co/d/jbjy-vk9h) | Contratación con el Estado por NIT y si la empresa se declaró pyme | 5 | 2 |
| 10 | [DANE · Microdatos EXPO 2025-2026](https://microdatos.dane.gov.co/index.php/catalog/859) | Opcional; sin NIT. 2026 exige reCAPTCHA | 2 (`--incluir-dane`) | 1 |

## Revisadas y descartadas

- **MEData (Alcaldía de Medellín)**: no tiene conjuntos de exportaciones ni de comercio exterior.
- **Kaggle**: no hay bases oficiales actualizadas de exportaciones colombianas por empresa. Las de ventas, recursos humanos, panadería, CRM, Instagram y ciberseguridad son de otros temas.
- **UCI** (Bank Marketing, Facebook Metrics), **Medicina Legal**, **Policía**, **MinTIC**, **Migración Colombia**, **MinCIT** (extranjeros no residentes) y **Aerocivil**: no traen exportaciones ni empresas exportadoras.
- **BACEX, Legiscomex, Datasur, ImportGenius**: son de pago, y la DIAN gratuita ya trae lo mismo con NIT.
- **ProColombia y Banco de la República**: no publican directorios descargables de exportadores con NIT.

## Referencias de validación

- [Analdex · Exportaciones por departamento 2025](https://analdex.org/wp-content/uploads/2026/02/Nota-exportaciones-departamentos-2025.pdf)
- [Analdex · Informe Antioquia mayo 2026](https://analdex.org/wp-content/uploads/2026/07/260723-Departamento-Antioquia-Informe-de-Exportaciones-Mayo-2026.pdf)
