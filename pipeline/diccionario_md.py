"""Escribe diccionario.md (formato de la plantilla del curso) a partir de la BD depurada.

Cada columna lleva: qué significa, tipo, unidad o formato, valores válidos y qué significa si está vacía.
Las descripciones vienen de pipeline/diccionario_bd_depurada.py; el tipo, los valores y el % de vacíos se
calculan sobre los datos, para que el diccionario no se desactualice. Lo llama el paso 9 y también se puede
correr solo:  python pipeline/diccionario_md.py
"""
import datetime
import pathlib
import sys

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

# Qué significa una celda vacía cuando no es simplemente "la fuente no trae el dato"
VACIOS = {
    "NIT_EXPORTADOR": "el exportador es una persona natural: la DIAN no publica su documento",
    "NUMERO_FORMULARIO": "la línea no tiene número de declaración (sobre todo hidrocarburos de Ecopetrol, Reficar o Frontera); es legítima",
    "NUM_DECLARACION_ANTERIOR": "es una declaración inicial (no corrige a otra)",
    "PERIODO_DECLARACION_ANTERIOR": "es una declaración inicial (no corrige a otra)",
    "NUM_DECLARACION_PRECEDENTE": "no hay declaración precedente (no viene de una importación temporal)",
    "PERIODO_DECLARACION_PRECEDENTE": "no hay declaración precedente",
    "COD_MODALIDAD_PRECEDENTE": "no hay declaración precedente",
    "DIRECCION_DECLARADA": "persona natural (no se publica por ser dato personal) o la fuente no la trae",
    "COD_MPIO_DIRECCION_DECLARADA": "la DIAN no trae un código de municipio válido",
    "NIT_DECLARANTE": "el declarante es una persona natural (la DIAN oculta su NIT) o la fuente no lo trae",
    "COD_ZONA_FRANCA_DESTINO": "el destino no es una zona franca",
    "CIUDAD_DESTINATARIO": "la fuente no trae la ciudad del comprador",
    "RAZON_SOCIAL": "la empresa solo aparece en sep-2024 (razón social enmascarada) y no está en el RUES",
    "NOMBRES_EN_FUENTE": "la empresa aparece con una sola razón social",
    "RANKING_ANTIOQUIA_FOB": "la empresa no es exportador antioqueño (vínculo C o D)",
    "CAMARA_COMERCIO": "la empresa no aparece en el RUES",
    "CIIU_PRINCIPAL_RUES": "la empresa no aparece en el RUES",
    "CIIU_SECUNDARIO_RUES": "la empresa no registró actividad secundaria o no aparece en el RUES",
    "COD_MPIO_DIAN_DIRECCION_PROPIA": "todas sus direcciones DIAN las comparten más de 5 NIT (suelen ser de agencias de aduanas)",
    "MUNICIPIO_DIAN_DIRECCION_PROPIA": "todas sus direcciones DIAN las comparten más de 5 NIT",
    "DEPTO_DIAN_DIRECCION_PROPIA": "todas sus direcciones DIAN las comparten más de 5 NIT",
    "PRODUCTO_AGRICOLA_PRINCIPAL_MADR": "la empresa no exporta productos agrícolas",
    "PRODUCTO_AGRICOLA_MADR": "la subpartida no es agrícola",
    "TRADICION_AGRICOLA_MADR": "la subpartida no es agrícola",
    "DESCRIPCION_PARTIDA_MADR": "la subpartida no es agrícola (la base DIAN no trae descripciones)",
    "FOB_USD_2024": "la empresa no exportó ese año", "FOB_USD_2025": "la empresa no exportó ese año",
    "FOB_USD_2026": "la empresa no exportó ese año",
    "SS_MACROSECTOR": "la empresa no está entre las 10.000 más grandes de Supersociedades",
    "SECOP_N_CONTRATOS": "la empresa no tiene contratos en SECOP II",
    "SECOP_ES_PYME": "la empresa no tiene contratos en SECOP II",
}
TABLAS = [
    ("hechos_exportaciones", "`datos/limpios/bd_depurada/hechos_exportaciones/` (un parquet por mes)",
     "un ítem (serie) de una declaración de exportación DIAN: una subpartida exportada por un exportador en una declaración",
     "`ID_REGISTRO` (la DIAN no trae una llave única: formulario + serie se repite y 1.690 líneas no tienen formulario)"),
    ("dim_exportador", "`datos/limpios/bd_depurada/dim_exportador.parquet` (las antioqueñas también en `datos/limpios/directorio_exportadores_antioquenos.csv`)",
     "una empresa exportadora (persona jurídica)", "`NIT`"),
]


def _tipo(t):
    t = t.upper()
    if t in ("BOOLEAN",):
        return "verdadero / falso"
    if t in ("DATE", "TIMESTAMP"):
        return "fecha"
    if any(x in t for x in ("INT", "DOUBLE", "DECIMAL", "FLOAT", "BIGINT")):
        return "número"
    return "texto"


def _formato(col, t):
    t = t.upper()
    if t == "DATE":
        return "AAAA-MM-DD" + (" (primer día del mes)" if col.startswith("PERIODO") else "")
    if t == "BOOLEAN":
        return "VERDADERO / FALSO"
    if col.endswith("_USD") or col.startswith("FOB_USD") or col == "VALOR_FOB_USD":
        return "dólares (USD)"
    if col.endswith("_COP"):
        return "pesos colombianos"
    if col.endswith("_BILLONES_COP"):
        return "billones de pesos (10^12)"
    if "KGS" in col:
        return "kilogramos"
    if col.startswith("PCT_"):
        return "porcentaje de 0 a 100"
    if col in ("PRIMER_MES", "ULTIMO_MES"):
        return "AAAA-MM"
    if col.startswith("N_") or col.startswith("RANKING") or col.endswith("_N_CONTRATOS") or col.endswith("_N_ENTIDADES"):
        return "conteo (entero)"
    if col in ("NIT", "NIT_EXPORTADOR", "NIT_DECLARANTE"):
        return "número de NIT sin dígito de verificación ni ceros a la izquierda"
    if col == "SUBPARTIDA":
        return "10 dígitos con cero inicial"
    if "CIIU" in col:
        return "código CIIU rev. 4 de 4 dígitos"
    if col.startswith("COD_PAIS"):
        return "ISO 3166 alfa-3 (XCF = zona franca, ND = no declarado)"
    if col.startswith("COD_DEPTO"):
        return "DIVIPOLA de 2 dígitos (00 = departamentos varios)"
    if col.startswith("COD_MPIO"):
        return "DIVIPOLA de 5 dígitos"
    if col.startswith("COD_ADUANA"):
        return "código DIAN de 2 dígitos"
    if col.startswith("COD_") or col in ("TIPO_IDENTIFICACION", "CLASE_EXPORTADOR", "TIPO_USUARIO", "OFICINA", "FORMA_PAGO", "TIPO_CERTIFICADO_ORIGEN"):
        return "código"
    return "texto libre" if t.startswith("VARCHAR") else "—"


def _valores(con, tabla, col, t, n_dist):
    t = t.upper()
    if t == "BOOLEAN":
        v, f = con.execute(f'SELECT count(*) FILTER (WHERE "{col}"), count(*) FILTER (WHERE NOT "{col}") FROM {tabla}').fetchone()
        return f"VERDADERO ({v:,}) o FALSO ({f:,})".replace(",", ".")
    if t in ("DATE",) or any(x in t for x in ("INT", "DOUBLE", "DECIMAL", "FLOAT")):
        lo, hi = con.execute(f'SELECT min("{col}"), max("{col}") FROM {tabla}').fetchone()
        if lo is None:
            return "—"
        if "DOUBLE" in t:
            f = lambda x: f"{x:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")  # noqa: E731
        elif "INT" in t and not col.startswith(("ANIO", "SS_ANO", "ULTIMO_ANO")):
            f = lambda x: f"{x:,}".replace(",", ".")  # noqa: E731
        else:
            f = str
        return f"de {f(lo)} a {f(hi)}"
    if n_dist <= 12:
        vals = [r[0] for r in con.execute(f'SELECT "{col}", count(*) n FROM {tabla} WHERE "{col}" IS NOT NULL GROUP BY 1 ORDER BY n DESC').fetchall()]
        return "; ".join(f"«{v}»" for v in vals)
    ref = {"SUBPARTIDA": "dim_subpartida", "COD_PAIS_DESTINO": "dim_pais", "COD_PAIS_BANDERA": "dim_pais",
           "COD_ZONA_FRANCA_DESTINO": "dim_zona_franca", "COD_ADUANA_DESPACHO": "dim_aduana", "COD_ADUANA_SALIDA": "dim_aduana",
           "COD_DEPTO_ORIGEN": "dim_departamento", "COD_DEPTO_PROCEDENCIA": "dim_departamento", "COD_MPIO_DIRECCION_DECLARADA": "dim_municipio",
           "NIT_DECLARANTE": "dim_declarante", "NIT_EXPORTADOR": "dim_exportador", "COD_MODALIDAD_EXPORTACION": "catalogo_codigos",
           "COD_UNIDAD_FISICA": "catalogo_codigos"}.get(col)
    return f"{n_dist:,} valores distintos".replace(",", ".") + (f"; cada uno existe en `{ref}`" if ref else "")


def escribir(bd=C.BD_DEPURADA_DUCKDB, salida=C.ROOT / "diccionario.md"):
    con = duckdb.connect(str(bd), read_only=True)
    desc = {(t, c): (d, o) for t, c, d, o in con.execute("SELECT TABLA, COLUMNA, DESCRIPCION, ORIGEN_O_REGLA FROM diccionario_datos").fetchall()}
    hasta = con.execute("SELECT strftime(max(PERIODO), '%Y-%m') FROM hechos_exportaciones").fetchone()[0]
    L = ["# Diccionario de datos", "",
         "> Qué significa cada columna de la BD depurada, para que otra persona la entienda sin preguntarnos. "
         "Se genera con el paso 9 (`pipeline/diccionario_md.py`): el tipo, los valores válidos y el porcentaje de vacíos salen de los datos.", "",
         "Contenido: [1. Muestra original](#1-muestra-original) · [2. hechos_exportaciones](#2-hechos_exportaciones) · "
         "[3. dim_exportador](#3-dim_exportador) · [4. Otras tablas](#4-otras-tablas)", "",
         "## 1. Muestra original", "",
         "- **Archivo:** `datos/originales/muestra_dian_exportaciones_2026_09.csv`",
         "- **Fuente y fecha de descarga:** DIAN, bases estadísticas de exportaciones, archivo `09_Exportaciones_2026_Septiembre.zip`, descargado en noviembre de 2026",
         "- **Cada fila es:** un ítem (serie) de una declaración de exportación, tal como lo publica la DIAN",
         "- **Filas en la muestra:** 1.000 (las primeras del archivo de septiembre de 2026, que tiene 115.049)",
         "- **Campo que identifica cada fila (clave):** no hay uno solo; `NUMERO_FORMULARIO` + `NUMERO_SERIE` casi siempre, pero se repite en algunas líneas",
         "",
         "Trae 70 de las 72 columnas de la DIAN. Se omitieron `RAZON_SOCIAL_DESTINATARIO` y `DOMICILIO_DESTINATARIO` porque pueden ser el nombre y la "
         "dirección de una persona, y `DIREC_EXPORTADOR` va vacía en las líneas de personas naturales. La descripción de las 72 columnas originales "
         "está en [docs/diccionario_transaccional.csv](docs/diccionario_transaccional.csv) y en la ficha técnica de la DIAN "
         "([docs/referencias/](docs/referencias/)). Abajo se describen las columnas limpias, que son las que se usan para analizar.", ""]
    for i, (tabla, archivo, fila, clave) in enumerate(TABLAS, start=2):
        n = con.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]
        cols = con.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{tabla}' ORDER BY ordinal_position").fetchall()
        L += [f"## {i}. {tabla}", "",
              f"- **Archivo:** {archivo}",
              f"- **Fuente y fecha de descarga:** DIAN (descargada en noviembre de 2026) más RUES, Supersociedades, SECOP II, MinAgricultura y MinCIT; procesada con el paso 9. Cubre 2024-01 a {hasta}",
              f"- **Cada fila es:** {fila}",
              f"- **Filas:** {n:,}".replace(",", "."),
              f"- **Campo que identifica cada fila (clave):** {clave}", "", "### Columnas", ""]
        for col, t in cols:
            n_vac, n_dist = con.execute(f'SELECT count(*) - count("{col}"), approx_count_distinct("{col}") FROM {tabla}').fetchone()
            d, o = desc.get((tabla, col), ("PENDIENTE: describir", ""))
            pct = 100 * n_vac / n if n else 0
            if n_vac == 0:
                vacia = "no hay vacíos"
            else:
                vacia = VACIOS.get(col, "la fuente no trae el dato")
                vacia += f" ({pct:.1f} % de las filas)".replace(".", ",")
            L += [f"#### {col}", f"- Qué significa: {d}" + (f" · Origen: {o}" if o else ""),
                  f"- Tipo: {_tipo(t)}", f"- Unidad o formato: {_formato(col, t)}",
                  f"- Valores válidos: {_valores(con, tabla, col, t, n_dist)}", f"- Si está vacía, significa: {vacia}", ""]
    L += ["## 4. Otras tablas", "",
          "Las dimensiones (`dim_subpartida`, `dim_pais`, `dim_zona_franca`, `dim_departamento`, `dim_municipio`, `dim_aduana`, `dim_declarante`), "
          "`catalogo_codigos` y las vistas (`vw_exportaciones`, `vw_exportaciones_antioquia`, `vw_directorio_antioquia`, `vw_serie_mensual`, "
          "`vw_validacion_*`) están descritas columna por columna en [docs/diccionario_bd_depurada.csv](docs/diccionario_bd_depurada.csv) "
          "y en la tabla `diccionario_datos` de la BD.", "",
          f"_Generado el {datetime.date.today().isoformat()}._", ""]
    con.close()
    pathlib.Path(salida).write_text("\n".join(L), encoding="utf-8")
    return salida


if __name__ == "__main__":
    print(escribir())
