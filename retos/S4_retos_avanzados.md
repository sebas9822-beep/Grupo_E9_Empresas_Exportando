# Retos avanzados · Sesión 4 · Equipo E9

**Datos:** los hechos de septiembre de 2026 de la BD depurada (`hechos_2026_09.parquet`, 115.049 líneas), que en Colab se llaman `datos`, y la tabla de países (`dim_pais.parquet`, 215 países), que se llama `paises`. Todo con SQL. Cada consulta está en [consultas/](../consultas/) con sus tres comentarios: pregunta, datos y cifra de control.

**Regla del día:** no se borró nada. Cada problema se detectó y se contó; la limpieza con pandas es el jueves, desde el original. Los problemas con su conteo están en la sección Limpieza de la [bitácora](../bitacora.md).

**Población de partida:** la consulta 1 deja 26.152 líneas de mercancía de origen Antioquia vendida al exterior, por USD 1.220,14 M. Todos los retos se cruzan contra esas dos cifras.

| Reto | Respondió | Respuesta corta |
|---|---|---|
| A1 | Sebastian Gaviria Lopez | Las dos definiciones no dan lo mismo: 26.152 frente a 26.372 líneas. Las 220 de diferencia tienen destino Colombia. En la ficha va la definición 1 |
| A2 | Luis Gabriel Cespedes | El producto es la partida. Con 3 países o menos, el indicador da 100 % por construcción. Regla: 4 países o más y USD 100.000 en el mes, y quedan 167 partidas |
| A3 | Julio Cesar Yanez | Mediana 79,0 % y ponderada 74,6 %. Se reporta la mediana, con el oro aparte |
| A4 | Sebastian Gaviria Lopez | Con Estados Unidos repetido, la unión pasa a 33.894 líneas (+29,6 %) y USD 1.540,4 M (+26,2 %) sin dar error. Lo evita comprobar la llave antes de unir |
| A5 | Luis Gabriel Cespedes | El oro es el 55,0 % del FOB. Sin él, la concentración en 3 países baja de 53,0 % a 44,6 % |
| A6 | Los tres, en la sala | Sin IA |

---

## A1 · Dos definiciones, dos cifras

**Respondió:** Sebastian Gaviria Lopez

**Consultas:** [08_a1_dos_definiciones.sql](../consultas/08_a1_dos_definiciones.sql) y [08b_a1_que_son_las_diferencias.sql](../consultas/08b_a1_que_son_las_diferencias.sql).

| Definición | Líneas | FOB (USD M) |
|---|---|---|
| 1: `COD_DEPTO_ORIGEN = '05'`, sin destino XCF ni COL | 26.152 | 1.220,14 |
| 2: `ORIGEN_MERCANCIA_ANTIOQUIA` y no `ES_DESTINO_ZONA_FRANCA` | 26.372 | 1.220,22 |
| Están en la 2 y no en la 1 | 220 | 0,09 (USD 86.409) |
| Están en la 1 y no en la 2 | 0 | — |

**Qué significa:** no dan lo mismo, y la diferencia es una sola cosa. La bandera de origen coincide exactamente con `COD_DEPTO_ORIGEN = '05'`, y la de zona franca con el código XCF. Lo que cambia es el destino Colombia: la definición 2 no quita las líneas con destino COL.

**Qué son las 220 líneas:** son de tres empresas, casi todas de confecciones (113 son sostenes, partida 6212). El comprador está en Medellín (209 líneas) o Bogotá (11), y todo va por carretera. La mercancía no sale del país, así que no es una venta al exterior. Pesan el 0,8 % de las líneas y el 0,007 % del FOB. Que sean ventas a comercializadoras internacionales que luego exportan es una inferencia: la base no lo dice. De paso apareció otro problema: 12 de esas líneas escriben «MEDELL�N», con un carácter dañado.

**Cuál va en la ficha:** la definición 1. Es la misma que usa la BD principal en `ES_VENTA_EXTERIOR`. Con las banderas se escribe `ORIGEN_MERCANCIA_ANTIOQUIA AND NOT ES_DESTINO_ZONA_FRANCA AND COD_PAIS_DESTINO <> 'COL'`.

**Si se quita el filtro de destino:** entran 266 líneas a zonas francas (USD 92,5 M) y las 220 con destino Colombia. El total pasa a 26.638 líneas y USD 1.312,7 M, un 7,6 % más de valor por mercancía que no salió del país.

## A2 · ¿Qué es un «producto»?

**Respondió:** Luis Gabriel Cespedes

**Consulta:** [09_a2_niveles_de_producto.sql](../consultas/09_a2_niveles_de_producto.sql).

| Nivel | Productos | Con 3 países o menos | Con 1 solo país | % del FOB en esos | Quedan con la regla | % del FOB que queda |
|---|---|---|---|---|---|---|
| Subpartida (10 dígitos) | 1.420 | 997 (70,2 %) | 620 | 9,9 % | 220 | 89,5 % |
| Partida (4 dígitos) | 566 | 318 (56,2 %) | 178 | 6,7 % | 167 | 93,1 % |
| Capítulo (2 dígitos) | 82 | 15 (18,3 %) | 7 | 0,6 % | 65 | 99,4 % |

**Qué le pasa al indicador con 3 países o menos:** da 100 % siempre, por construcción, porque esos tres países ya son todos los compradores. No mide concentración: solo dice que hay pocos compradores. Además suelen ser envíos sueltos. La partida típica con 3 países o menos vende USD 10.367 en el mes, frente a USD 258.555 de las demás.

**Pero no son inofensivos:** un producto con un solo comprador es el que más depende de él. El ejemplo es la energía eléctrica (2716): una sola línea de USD 42,3 M, toda a Ecuador. No se borran; se reportan aparte, con su número de países y la parte de su comprador principal.

**Nivel:** la partida. La subpartida es demasiado fina: el 70 % de los productos tiene 3 países o menos. El capítulo es demasiado grueso: el 08 junta banano y aguacate, y el 71 junta oro y bisutería. La partida es el producto como lo entiende un comprador, y es la que usa el [resolver](../resolver/).

**Regla mínima:** 4 países o más y al menos USD 100.000 en el mes. Con 4 países, el indicador ya puede bajar de 100 %. Con USD 100.000 al mes (unos USD 1,2 M al año, en línea con el piso anual del resolver), un envío pequeño no mueve la cifra. **Quedan 167 partidas, con el 93,1 % del FOB.**

## A3 · El promedio que engaña

**Respondió:** Julio Cesar Yanez

**Consulta:** [10_a3_mediana_vs_ponderada.sql](../consultas/10_a3_mediana_vs_ponderada.sql).

| Medida (167 partidas) | Valor |
|---|---|
| Mediana de la concentración en 3 países | **79,0 %** |
| Concentración ponderada por FOB | **74,6 %** |
| Peso de la partida mayor (7108, oro) | 59,1 % del FOB |

**Por qué no dan lo mismo:**

- La mediana cuenta cada partida una vez; la ponderada cuenta cada dólar.
- El oro es el 59,1 % del valor y las 5 partidas más grandes suman el 81,7 %. La ponderada es casi la concentración del oro (75,7 %) mezclada con la del café (58,6 %) y la del banano (50,7 %).
- Las partidas pequeñas están más concentradas: la mediana es 87,2 % en el tercio más pequeño y 73,9 % en el más grande. Por eso la ponderada queda por debajo de la mediana.

**Qué le reportaríamos a la consultora:** la mediana. Su pregunta es qué productos dependen demasiado de pocos países, y cada producto es una decisión distinta; la ponderada describe casi solo el oro. Sin el oro, la ponderada baja a 72,9 % y la mediana casi no cambia (79,1 %). El resolver encontró lo mismo con todo 2025: mediana 73,1 % y ponderada 70,1 %.

## A4 · La unión que infla sin error

**Respondió:** Sebastian Gaviria Lopez

**Consultas:** [11_a4_union_infla.sql](../consultas/11_a4_union_infla.sql) y [11b_a4_chequeo_llave.sql](../consultas/11b_a4_chequeo_llave.sql).

| Caso | Líneas | FOB (USD M) |
|---|---|---|
| Sin unir | 26.152 | 1.220,14 |
| Unida con `paises` | 26.152 | 1.220,14 |
| Unida con Estados Unidos repetido | 33.894 (+7.742; +29,6 %) | 1.540,42 (+320,28; +26,2 %) |

**Qué significa:** la unión normal conserva todo, porque cada código aparece una vez en `paises`. Con Estados Unidos repetido, cada una de sus 7.742 líneas sale dos veces, y no aparece ningún mensaje de error. La parte de Estados Unidos en el valor pasaría de 26,2 % a 41,6 %, y el informe diría que Antioquia depende mucho más de ese país de lo que depende.

**El chequeo que lo evita:** antes de unir, comprobar que la llave no se repite en la tabla que se pega: `COUNT(*)` igual a `COUNT(DISTINCT COD_PAIS)`. Con la tabla buena da 215 y 215; con la repetida daría 216 y 215. Después de unir, contar las líneas antes y después.

**¿Está en la 05?** A medias. [05_union_hechos_directorio.sql](../consultas/05_union_hechos_directorio.sql) compara el conteo antes y después de unir (3.613.237 en los dos casos), y eso habría delatado la inflación. Pero no comprueba la llave antes: el comentario dice que el NIT no se repite y ninguna consulta lo verifica. Hoy lo comprobamos (13.305 filas y 13.305 NIT distintos) y proponemos agregarle ese chequeo.

## A5 · Un producto que lo mueve todo

**Respondió:** Luis Gabriel Cespedes

**Consultas:** [12_a5_partida_mayor.sql](../consultas/12_a5_partida_mayor.sql) y [12b_a5_con_y_sin_oro.sql](../consultas/12b_a5_con_y_sin_oro.sql).

| Grupo | FOB (USD M) | Países | % en los 3 principales | Cuáles |
|---|---|---|---|---|
| Todo Antioquia | 1.220,14 | 109 | 53,0 % | EE. UU., Italia, Canadá |
| Sin el oro (7108) | 548,87 | 109 | 44,6 % | EE. UU., Ecuador, India |
| Solo el oro | 671,26 | 6 | 75,7 % | EE. UU., Italia, Canadá |

**Qué significa:** una sola partida, el oro, es el 55,0 % del FOB de septiembre: USD 671,26 M en 170 líneas, a 6 países. La segunda, el café, es el 6,3 %. El oro decide quiénes salen como principales compradores: sin él, la concentración en 3 países baja casi 8 puntos y entran Ecuador e India.

**Qué le diríamos a la consultora:**

- El oro se reporta siempre aparte; si se mezcla, cualquier cifra total o ponderada habla del oro.
- Es un mercado distinto: 38 empresas le venden oro en bruto a compradores de 6 países. Es minero-energético y no se diversifica con misiones o ferias.
- Para las empresas que acompaña, la cifra relevante es la concentración sin el oro (44,6 %) y la mediana por producto (79,0 %).
- Septiembre no basta para el oro: su comprador principal cambia de un mes a otro. En 2026 fue Estados Unidos de enero a marzo y en septiembre, Canadá en abril e Italia de mayo a agosto, según la BD principal.

## A6 · Explícalo sin IA

Se hace en la sala, sin IA. Cada integrante elige una consulta, la explica línea por línea y, antes de correrla, predice qué pasa con el número si quita un filtro.

| Integrante | Consulta | Filtro que quita | Predicción | Resultado |
|---|---|---|---|---|
| Sebastian Gaviria Lopez | | | | |
| Luis Gabriel Cespedes | | | | |
| Julio Cesar Yanez | | | | |

---

## Cierre honesto

- **Con esta base podemos afirmar** que, en septiembre de 2026, la mercancía antioqueña vendida al exterior (26.152 líneas, USD 1.220,1 M) depende de pocos países. El producto típico (mediana de 167 partidas con al menos 4 países y USD 100.000) le vende el 79,0 % a sus 3 principales compradores, y una sola partida, el oro, es el 55,0 % del valor.
- **No podemos afirmar** que esa concentración sea la del año, porque es un solo mes y el comprador principal del oro cambia de un mes a otro. Tampoco podemos decir nada con este indicador de las 318 partidas con 3 países o menos, donde da 100 % por construcción.
- **Lo siguiente que comprobaríamos** es si el patrón se mantiene en los 12 meses de 2025 y en 2016-2025; el resolver sugiere que sí (mediana 73,1 % y ponderada 70,1 % en 2025). También comprobaríamos si las 220 líneas con destino Colombia son ventas a comercializadoras que después exportan.

**Periodo de la pregunta:** 2016-2025. Ya está escrito en la ficha v2 del README, en el PR #9.

**Uso de IA:** Claude escribió las consultas y las respuestas a partir de lo que le pedimos; está declarado en la bitácora. Cada reto lo firma quien lo explica en la sala.
