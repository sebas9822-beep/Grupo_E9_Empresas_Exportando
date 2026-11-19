# resolver

Cómo se resolvió la pregunta **"¿Qué porcentaje de las exportaciones de cada producto de Antioquia se concentra en sus tres principales países compradores?"** y qué tan vulnerable sería el departamento si uno de sus compradores deja de importar (2016-2025).

Empieza por **[como_se_resolvio_concentracion_antioquia.md](como_se_resolvio_concentracion_antioquia.md)**. Ahí está el paso a paso: de dónde salen los datos, cómo se comprobaron, cada consulta con su resultado y cómo explicarlo en un minuto.

> La BD principal del proyecto solo tiene datos desde enero de 2024. Para cubrir 2016-2023 se bajaron esos años de la misma fuente (bases mensuales de la DIAN) y se procesaron con las mismas reglas. En enero y julio de 2024 el método da exactamente lo mismo que la BD principal: 5.641 combinaciones de país y producto, cero diferencias.

## Qué hay en la carpeta

| Archivo | Qué es |
|---|---|
| `como_se_resolvio_concentracion_antioquia.md` | El paso a paso completo, con las consultas, sus resultados y los errores que se corrigieron |
| `consultas/` | Una consulta por archivo `.sql`, con los tres comentarios de la guía 2: pregunta, datos y cifra de control |
| `scripts/descargar.py` | Baja de la DIAN las 96 bases mensuales de 2016-2023, más enero y julio de 2024 |
| `scripts/extraer.py` | Pasa cada base mensual (zip con un Excel) a parquet, solo con las columnas del análisis |
| `scripts/analisis.py` | Une 2016-2023 (parquet) con 2024-2025 (BD principal) y arma `analisis.duckdb` con las tablas `lineas`, `ant`, `nac` y `paises` |
| `scripts/nombres.py` | Nombres cortos en español de las partidas que se citan en el informe |
| `scripts/correr_consultas.py` | Corre todas las consultas de `consultas/` y muestra cada resultado junto a su cifra de control |
| `scripts/verificacion_pandas.py` | Recalcula el dato a confirmar de 2025 por otra vía (pandas sobre la BD principal) |

## Las consultas

| Archivo | Pregunta | Cifra de control |
|---|---|---|
| `00a_cuadre_metodo_vs_bd_principal.sql` | ¿El método de 2016-2023 da lo mismo que la BD principal? | 5.641 combinaciones, 0 diferencias |
| `00b_totales_anuales_vs_cifras_publicadas.sql` | ¿Los totales anuales cuadran con cifras publicadas? | USD 10.786,4 M en 2025 |
| `01_mirar_filtrar.sql` | ¿Cuántas líneas son de origen Antioquia vendidas al exterior? | 2.843.817 de 10.981.096 |
| `02_resumen_por_anio.sql` | ¿Cómo se reparten por año? | USD 10.364,2 M en 2025 |
| `03a_top3_por_producto_2025.sql` | **% en los tres principales compradores, por producto** | 225 productos; oro 70,7 %, flores 84,3 % |
| `03b_resumen_concentracion_por_anio.sql` | ¿Qué tan concentrados están en general, y cambió? | 2025: 70,1 % ponderado, 73,1 % mediana, 52 productos con 90 % o más |
| `04_concentracion_por_pais.sql` | ¿Cuánto pesan EE. UU. y los tres principales países? | 2025: EE. UU. 28,9 %, índice de Herfindahl-Hirschman 1.129 |
| `05_sectores_2016_2025.sql` | ¿Qué sectores dependen más de pocos países? | 22 filas (11 sectores × 2 años) |
| `06a_perdida_por_comprador_2025.sql` | ¿Cuánto se perdería si un comprador deja de importar? | EE. UU.: USD 2.998,5 M |
| `06b` a `06d` | Qué compra EE. UU., y qué productos y empresas dependen de ese país | 29 productos y 520 empresas venden la mitad o más a EE. UU. |
| `07_dependencia_empresas.sql` | ¿Cuántas empresas dependen de un solo país? | 2025: 2.049 empresas, 44,6 % vende a un solo país |
| `08a_mercados_alternos_flores.sql` | ¿Dónde otros departamentos ya venden flores y Antioquia casi no llega? | 26 países |
| `08b_mercados_alternos_prioritarios.sql` | Lo mismo para los 15 productos más concentrados | 9 de 15 tienen al menos un mercado alterno |

## Cómo reproducirlo

Todo se corre desde la raíz del repositorio. Se necesitan los paquetes de `requirements.txt` y unos 3,5 GB de espacio libre (2,8 GB de descargas, 155 MB de parquet y 380 MB de `analisis.duckdb`).

```bash
pip install -r requirements.txt
python crear_bd_analitica.py                    # la BD principal (2024-2026), si aún no la tienes
python resolver/scripts/descargar.py            # 98 archivos de la DIAN; si se corta, vuelve a correrlo y sigue donde iba
python resolver/scripts/extraer.py              # zip -> parquet
python resolver/scripts/analisis.py             # arma resolver/scripts/analisis.duckdb
python resolver/scripts/correr_consultas.py     # corre las consultas y muestra cada cifra de control
python resolver/scripts/verificacion_pandas.py  # segunda vía para el dato a confirmar
```

Para correr una sola consulta: `python resolver/scripts/correr_consultas.py 03a`. Las descargas, los parquet y `analisis.duckdb` no se suben al repositorio: se regeneran con estos pasos.

## Reglas del análisis

Son las mismas de la BD principal:

- **Antioquia:** departamento de origen de la mercancía `'05'`.
- **Venta al exterior:** se excluyen las zonas francas colombianas (`'XCF'`) y el destino Colombia (`'COL'`).
- **Producto:** partida arancelaria de 4 dígitos. Solo cuentan los productos con al menos USD 1 M en el año.
- **Minero-energético:** capítulos 26 y 27, partidas 7103, 7106, 7108, 7110 y 7112, y la subpartida 720260.
- **Empresas:** NIT con al menos USD 10.000 exportados en el año.
