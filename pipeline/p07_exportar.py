"""Paso 7 · Productos de líneas y directorio en datos/intermedios/productos_paso7/ (insumo del paso 9).

- exportaciones_nacional/expo_nacional_AAAA_MM.parquet   todas las líneas del país, un archivo por mes
- exportaciones_antioquia/expo_antioquia_AAAA.parquet    líneas de origen Antioquia o de exportadores antioqueños
- directorio_exportadores_nacional.csv / _antioquenos.csv
- serie_mensual_antioquia.csv, tabla_subpartidas_sector.csv, tabla_nit.csv
- validacion_mincit_nme.csv, validacion_madr_agricolas.csv, cobertura.json
- docs/diccionario_transaccional.csv (columnas del parquet)

Los archivos se parten por mes/año para poder leerlos por partes. No se versionan: lo que se publica es la BD
depurada del paso 9, en datos/limpios/.
"""
import json
import argparse
import pathlib
import sys
from datetime import date

import duckdb
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from pipeline.comun import log, ruta_csv  # noqa: E402

DERIVADAS = {
    "ANIO": "Año de la base mensual DIAN",
    "MES": "Mes de la base mensual DIAN",
    "ARCHIVO_FUENTE": "Nombre del .zip mensual de la DIAN de donde sale la línea",
    "SUBPARTIDA_10D": "Subpartida arancelaria a 10 dígitos con cero inicial (la DIAN la publica como número y pierde el 0 de los capítulos 01-09)",
    "PERIODO": "Primer día del mes (fecha)",
    "COD_MPIO_DIRECCION_DECLARADA": "Código DIVIPOLA de 5 dígitos de COD_DPTO_EXPORTADOR. OJO: muchas veces es la dirección de la agencia de aduanas",
    "MUNICIPIO_DIRECCION_DECLARADA": "Municipio de la dirección declarada (DIVIPOLA). No usar como domicilio de la empresa",
    "DEPTO_DIRECCION_DECLARADA": "Departamento de la dirección declarada (DIVIPOLA). No usar como domicilio de la empresa",
    "DIRECCION_DECLARADA_EN_ANTIOQUIA": "VERDADERO si la dirección declarada está en Antioquia (no confiable como domicilio)",
    "ORIGEN_MERCANCIA_ANTIOQUIA": "VERDADERO si el departamento de origen de la mercancía (COD_REGION_ORIGEN) es Antioquia",
    "ES_PERSONA_NATURAL": "VERDADERO si el exportador es una persona natural anonimizada por la DIAN (razón social PERSONA NATURAL sin NIT de empresa)",
    "RAZON_SOCIAL_ENMASCARADA": "VERDADERO si la DIAN publicó PERSONA NATURAL o dejó vacía la razón social pero la línea trae NIT de empresa (pasa en septiembre de 2024); la línea se atribuye a la empresa",
    "NIT": "NIT del exportador sin ceros a la izquierda (vacío para personas naturales)",
    "PAIS_DESTINO_NORM": "País destino con nombre M49 homogéneo para 2024-2026",
    "SECTOR_EXPORTACION": "Minero-energético / Agrícola y agroindustrial (MADR) / Industria y otros",
    "ES_MINERO_ENERGETICO": "Capítulos 26-27, ferroníquel, oro, plata, platino, desperdicios de metal precioso y piedras preciosas (calibrado con MinCIT NME)",
    "ES_AGRICOLA_MADR": "Subpartida clasificada como agrícola/agroindustrial por MinAgricultura",
    "PRODUCTO_AGRICOLA_MADR": "Producto agrícola MinAgricultura (p. ej. Banano, Café, Flores)",
    "TRADICION_AGRICOLA_MADR": "Tradicional / No tradicional (MinAgricultura)",
    "NIT_EMPRESA_ANTIOQUENA": "La empresa tiene su matrícula principal en una cámara de comercio de Antioquia (vínculo A)",
    "NIT_ES_EXPORTADOR_ANTIOQUENO": "Vínculo A o B con Antioquia",
    "NIT_VINCULO_ANTIOQUIA": "A/B/C/D, ver docs/metodologia.md",
    "NIT_CAMARA_COMERCIO": "Cámara de comercio de la matrícula principal (RUES)",
    "NIT_CIIU_RUES": "CIIU principal de la empresa (RUES)",
    "NIT_SECTOR_EXPORTADOR_PRINCIPAL": "Sector con mayor FOB de la empresa",
    "NIT_PROVEEDOR_ESTADO_SECOP_II": "La empresa tiene contratos con el Estado en SECOP II",
    "NIT_ES_PYME_SECOP": "Lo que la empresa declaró en SECOP II: Sí / No / Mixto",
}


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    con = duckdb.connect(str(C.DUCKDB_PATH))
    con.execute(f"SET memory_limit='4GB'; SET preserve_insertion_order=true; SET temp_directory='{C.INTERIM / 'tmp_duckdb'}'")
    anios = [r[0] for r in con.execute("SELECT DISTINCT ANIO FROM expo ORDER BY 1").fetchall()]
    C.OUT_NACIONAL.mkdir(parents=True, exist_ok=True)
    C.OUT_ANTIOQUIA.mkdir(parents=True, exist_ok=True)

    con.execute("""CREATE OR REPLACE TABLE expo_final AS
    SELECT e.*, s.SECTOR_EXPORTACION, coalesce(s.ES_MINERO_ENERGETICO,false) ES_MINERO_ENERGETICO,
      coalesce(s.ES_AGRICOLA_MADR,false) ES_AGRICOLA_MADR, s.PRODUCTO_AGRICOLA_MADR, s.TRADICION_AGRICOLA_MADR,
      coalesce(d.EMPRESA_ANTIOQUENA,false) NIT_EMPRESA_ANTIOQUENA, coalesce(d.ES_EXPORTADOR_ANTIOQUENO,false) NIT_ES_EXPORTADOR_ANTIOQUENO,
      d.VINCULO_ANTIOQUIA NIT_VINCULO_ANTIOQUIA, d.CAMARA_COMERCIO NIT_CAMARA_COMERCIO, d.CIIU_PRINCIPAL_RUES NIT_CIIU_RUES,
      d.SECTOR_EXPORTADOR_PRINCIPAL NIT_SECTOR_EXPORTADOR_PRINCIPAL,
      coalesce(d.PROVEEDOR_ESTADO_SECOP_II,false) NIT_PROVEEDOR_ESTADO_SECOP_II, d.SECOP_ES_PYME NIT_ES_PYME_SECOP
    FROM expo e LEFT JOIN subpartida_map s USING (SUBPARTIDA_10D) LEFT JOIN directorio d USING (NIT)
    ORDER BY e.PERIODO, e.ARCHIVO_FUENTE""")

    periodos = con.execute("SELECT DISTINCT ANIO, MES FROM expo_final ORDER BY 1,2").fetchall()
    for a, m in periodos:
        con.execute(f"COPY (SELECT * FROM expo_final WHERE ANIO={a} AND MES={m}) TO "
                    f"'{C.OUT_NACIONAL / f'expo_nacional_{a}_{m:02d}.parquet'}' (FORMAT parquet, COMPRESSION zstd)")
    filtro_ant = "ORIGEN_MERCANCIA_ANTIOQUIA OR NIT_ES_EXPORTADOR_ANTIOQUENO"
    for a in anios:
        con.execute(f"COPY (SELECT * FROM expo_final WHERE ANIO={a} AND ({filtro_ant})) TO "
                    f"'{C.OUT_ANTIOQUIA / f'expo_antioquia_{a}.parquet'}' (FORMAT parquet, COMPRESSION zstd)")
    log(f"Parquet: {len(periodos)} meses nacionales y {len(anios)} años de Antioquia")

    # Directorio (orden de columnas pensado para lectura)
    fob_cols = [f"FOB_USD_{a}" for a in anios]
    primeras = ["NIT", "RAZON_SOCIAL", "VINCULO_ANTIOQUIA", "EMPRESA_ANTIOQUENA", "ES_EXPORTADOR_ANTIOQUENO",
                "CAMARA_COMERCIO", "FUENTE_DOMICILIO", "MUNICIPIO_DIAN_DIRECCION_PROPIA", "DEPTO_ORIGEN_PRINCIPAL_MERCANCIA",
                "SECTOR_EXPORTADOR_PRINCIPAL", "PCT_FOB_MINERO_ENERGETICO", "PCT_FOB_AGRICOLA_MADR",
                "PRODUCTO_AGRICOLA_PRINCIPAL_MADR", *fob_cols, "FOB_USD_TOTAL", "FOB_USD_ORIGEN_ANTIOQUIA",
                "PCT_FOB_ORIGEN_ANTIOQUIA"]
    cols = [r[0] for r in con.execute("DESCRIBE directorio").fetchall()]
    orden = primeras + [c for c in cols if c not in primeras]
    d = con.execute(f"SELECT {', '.join(orden)} FROM directorio ORDER BY FOB_USD_TOTAL DESC NULLS LAST, NIT").df()
    d.insert(0, "RANKING_NACIONAL_FOB", range(1, len(d) + 1))
    ant = d[d.ES_EXPORTADOR_ANTIOQUENO].copy()
    ant.insert(0, "RANKING_ANTIOQUIA_FOB", range(1, len(ant) + 1))
    d.to_csv(C.PROCESSED / "directorio_exportadores_nacional.csv", index=False, encoding="utf-8-sig")
    ant.to_csv(C.PROCESSED / "directorio_exportadores_antioquenos.csv", index=False, encoding="utf-8-sig")
    con.execute(f"COPY (SELECT * FROM subpartida_map ORDER BY SUBPARTIDA_10D) TO '{C.PROCESSED / 'tabla_subpartidas_sector.csv'}' (HEADER)")
    con.execute(f"""COPY (SELECT NIT, EMPRESA_ANTIOQUENA, ES_EXPORTADOR_ANTIOQUENO, VINCULO_ANTIOQUIA, CAMARA_COMERCIO,
        CIIU_PRINCIPAL_RUES, SECTOR_EXPORTADOR_PRINCIPAL, PROVEEDOR_ESTADO_SECOP_II, SECOP_ES_PYME FROM directorio ORDER BY NIT)
        TO '{C.PROCESSED / 'tabla_nit.csv'}' (HEADER)""")
    log(f"Directorio: {len(d):,} exportadores en el país, {len(ant):,} antioqueños (A+B)")

    # Serie mensual
    serie = con.execute("""SELECT strftime(PERIODO,'%Y-%m') PERIODO,
      round(sum(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA)/1e6,3) FOB_MUSD_ORIGEN_ANTIOQUIA,
      round(sum(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA AND NOT ES_MINERO_ENERGETICO)/1e6,3) FOB_MUSD_ORIGEN_ANTIOQUIA_NO_MINERO_ENERGETICO,
      round(sum(VALOR_FOB_USD) FILTER (WHERE ORIGEN_MERCANCIA_ANTIOQUIA AND ES_AGRICOLA_MADR)/1e6,3) FOB_MUSD_ORIGEN_ANTIOQUIA_AGRICOLA,
      round(sum(VALOR_FOB_USD) FILTER (WHERE NIT_EMPRESA_ANTIOQUENA)/1e6,3) FOB_MUSD_EMPRESAS_ANTIOQUENAS,
      round(sum(VALOR_FOB_USD) FILTER (WHERE NIT_ES_EXPORTADOR_ANTIOQUENO)/1e6,3) FOB_MUSD_EXPORTADORES_ANTIOQUENOS,
      round(sum(VALOR_FOB_USD)/1e6,3) FOB_MUSD_NACIONAL,
      round(sum(VALOR_FOB_USD) FILTER (WHERE NOT ES_MINERO_ENERGETICO)/1e6,3) FOB_MUSD_NACIONAL_NO_MINERO_ENERGETICO,
      count(DISTINCT NIT) FILTER (WHERE NIT_EMPRESA_ANTIOQUENA) N_NIT_EMPRESAS_ANTIOQUENAS,
      count(DISTINCT NIT) FILTER (WHERE NIT_ES_EXPORTADOR_ANTIOQUENO) N_NIT_EXPORTADORES_ANTIOQUENOS,
      count(DISTINCT NIT) N_NIT_NACIONAL
    FROM expo_final GROUP BY 1 ORDER BY 1""").df()
    serie.to_csv(C.PROCESSED / "serie_mensual_antioquia.csv", index=False)

    # Validación contra MinCIT (total y NME trimestral)
    mincit = pd.read_csv(ruta_csv(C.RAW_FUENTES_V2 / "MinCIT_exportaciones_NME.csv", C.INTERIM))
    mincit["TRIMESTRE"] = pd.to_datetime(mincit.fecha).dt.to_period("Q").astype(str)
    q = con.execute("""SELECT CAST(ANIO AS VARCHAR) || 'Q' || CAST(((MES-1)//3)+1 AS VARCHAR) TRIMESTRE, count(DISTINCT MES) MESES,
        round(sum(VALOR_FOB_USD)/1e6) DIAN_TOTAL_MUSD, round(sum(VALOR_FOB_USD) FILTER (WHERE NOT ES_MINERO_ENERGETICO)/1e6) DIAN_NME_MUSD
        FROM expo_final GROUP BY 1 ORDER BY 1""").df()
    v1 = q[q.MESES == 3].drop(columns="MESES").merge(
        mincit[["TRIMESTRE", "valor_exportaciones_totales", "valor_exportaciones_nme"]].rename(
            columns={"valor_exportaciones_totales": "MINCIT_TOTAL_MUSD", "valor_exportaciones_nme": "MINCIT_NME_MUSD"}),
        on="TRIMESTRE", how="inner")
    v1["DIF_TOTAL_PCT"] = ((v1.DIAN_TOTAL_MUSD - v1.MINCIT_TOTAL_MUSD) / v1.MINCIT_TOTAL_MUSD * 100).round(2)
    v1["DIF_NME_PCT"] = ((v1.DIAN_NME_MUSD - v1.MINCIT_NME_MUSD) / v1.MINCIT_NME_MUSD * 100).round(2)
    v1.to_csv(C.PROCESSED / "validacion_mincit_nme.csv", index=False)

    # Validación contra MinAgricultura (mismos meses que cubre la fuente)
    madr = ruta_csv(C.RAW_FUENTES_V2 / "MADR_exportaciones_agricolas_2024_2026.csv", C.INTERIM)
    meses_sql = ", ".join(f"('{n}', {i})" for i, n in enumerate(C.MESES, 1))
    v2 = con.execute(f"""
    WITH mm AS (SELECT * FROM (VALUES {meses_sql}) t(nombre, mes)),
    m AS (SELECT CAST(a_o AS INT) anio, mm.mes, sum(try_cast(valor_miles_fob_dol_expo AS DOUBLE))/1e3 nac,
                 sum(try_cast(valor_miles_fob_dol_expo AS DOUBLE)) FILTER (WHERE descripci_n_departamento='Antioquia')/1e3 ant
          FROM read_csv('{madr}', all_varchar=true) r JOIN mm ON mm.nombre = r.mes GROUP BY 1,2),
    o AS (SELECT ANIO anio, MES mes, sum(VALOR_FOB_USD) FILTER (WHERE ES_AGRICOLA_MADR)/1e6 nac,
                 sum(VALOR_FOB_USD) FILTER (WHERE ES_AGRICOLA_MADR AND ORIGEN_MERCANCIA_ANTIOQUIA)/1e6 ant FROM expo_final GROUP BY 1,2)
    SELECT m.anio ANIO, count(*) MESES, round(sum(o.nac),1) DIAN_AGRICOLA_NACIONAL_MUSD, round(sum(m.nac),1) MADR_AGRICOLA_NACIONAL_MUSD,
           round(sum(o.ant),1) DIAN_AGRICOLA_ANTIOQUIA_MUSD, round(sum(m.ant),1) MADR_AGRICOLA_ANTIOQUIA_MUSD
    FROM m JOIN o USING (anio, mes) GROUP BY 1 ORDER BY 1""").df()
    v2["DIF_ANTIOQUIA_PCT"] = ((v2.DIAN_AGRICOLA_ANTIOQUIA_MUSD - v2.MADR_AGRICOLA_ANTIOQUIA_MUSD) / v2.MADR_AGRICOLA_ANTIOQUIA_MUSD * 100).round(2)
    v2.to_csv(C.PROCESSED / "validacion_madr_agricolas.csv", index=False)
    log(f"Validación MinCIT NME: diferencia máxima {v1.DIF_NME_PCT.abs().max():.2f} % · "
        f"MADR Antioquia: diferencia máxima {v2.DIF_ANTIOQUIA_PCT.abs().max():.2f} %")

    # Cobertura y diccionario de columnas
    tot = con.execute("SELECT count(*), sum(VALOR_FOB_USD), min(PERIODO), max(PERIODO) FROM expo_final").fetchone()
    n_ant = con.execute(f"SELECT count(*) FROM expo_final WHERE {filtro_ant}").fetchone()[0]
    cobertura = {"fecha_proceso": date.today().isoformat(), "periodo_desde": str(tot[2])[:7], "periodo_hasta": str(tot[3])[:7],
                 "lineas_nacional": tot[0], "lineas_antioquia": n_ant, "fob_usd_total": round(tot[1], 2),
                 "exportadores_personas_juridicas": len(d), "exportadores_antioquenos_A_B": len(ant),
                 "nota": f"Las columnas FOB_USD_{anios[-1]} y EXPORTADOR_{anios[-1]}_MIN_1000USD del directorio "
                         f"acumulan solo hasta {str(tot[3])[:7]}."}
    (C.PROCESSED / "cobertura.json").write_text(json.dumps(cobertura, ensure_ascii=False, indent=2), encoding="utf-8")
    desc = con.execute("DESCRIBE expo_final").df()
    pd.DataFrame({"columna": desc.column_name, "tipo": desc.column_type,
                  "descripcion": [DERIVADAS.get(c, "Variable original DIAN (ver docs/referencias/Ficha-Tecnica-bases-estadisticas-de-Comercio-Exterior.pdf)")
                                  for c in desc.column_name],
                  "origen": ["Derivada" if c in DERIVADAS else "DIAN" for c in desc.column_name]}
                 ).to_csv(C.DOCS / "diccionario_transaccional.csv", index=False, encoding="utf-8")
    log(f"Cobertura {cobertura['periodo_desde']} a {cobertura['periodo_hasta']} · {tot[0]:,} líneas · FOB USD {tot[1] / 1e9:,.2f} mil M")


if __name__ == "__main__":
    main()
