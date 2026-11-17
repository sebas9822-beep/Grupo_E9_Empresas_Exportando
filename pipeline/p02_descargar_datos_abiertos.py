"""Paso 2 · Descarga de datos abiertos (datos.gov.co) que no dependen de la lista de NIT.

Primera búsqueda: RUES de personas jurídicas de las 5 cámaras de Antioquia, 10.000 empresas
más grandes (Supersociedades), DIVIPOLA y bases de las cámaras de comercio antioqueñas.
Segunda búsqueda: serie NME de MinCIT y exportaciones agrícolas de MinAgricultura.

Uso: python pipeline/p02_descargar_datos_abiertos.py [--forzar] [--solo id1,id2] [--incluir-dane]
"""
import argparse
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from pipeline.comun import descargar, log, socrata_csv, sql_lista  # noqa: E402

# Columnas del RUES que se guardan: solo datos de la empresa (sin representantes legales)
RUES_COLUMNAS = ("codigo_camara,camara_comercio,matricula,razon_social,sigla,clase_identificacion,"
                 "numero_identificacion,nit,digito_verificacion,cod_ciiu_act_econ_pri,cod_ciiu_act_econ_sec,"
                 "ciiu3,ciiu4,fecha_matricula,fecha_renovacion,ultimo_ano_renovado,fecha_vigencia,"
                 "fecha_cancelacion,tipo_sociedad,codigo_organizacion_juridica,organizacion_juridica,"
                 "categoria_matricula,estado_matricula,fecha_actualizacion")

# (id datos.gov.co, archivo, carpeta, select, where, búsqueda)
DATASETS = [
    ("c82u-588k", "RUES_personas_juridicas_camaras_Antioquia.csv", C.RAW_DATOSGOV, RUES_COLUMNAS,
     f"codigo_camara in ({sql_lista(C.CODIGOS_CAMARAS_ANTIOQUIA)}) AND codigo_organizacion_juridica != '01'", 1),
    ("6cat-2gcs", "Supersociedades_10000_empresas_mas_grandes.csv", C.RAW_DATOSGOV, None, None, 1),
    ("gdxc-w37w", "DIVIPOLA_municipios.csv", C.RAW_DATOSGOV, None, None, 1),
    ("vcjz-niiq", "DIVIPOLA_departamentos.csv", C.RAW_DATOSGOV, None, None, 1),
    ("ssvh-3gwc", "CC_Oriente_Antioqueno_NIT_CIIU.csv", C.RAW_DATOSGOV, None, None, 1),
    ("we9a-3bys", "CC_Oriente_Antioqueno_empleados_por_empresa.csv", C.RAW_DATOSGOV, None, None, 1),
    ("5aa8-pf7p", "CC_Magdalena_Medio_NIT_CIIU.csv", C.RAW_DATOSGOV, None, None, 1),
    ("bzeh-ecuk", "CC_Medellin_estructura_empresarial_municipio_tamano.csv", C.RAW_DATOSGOV, None, None, 1),
    ("wed5-aysq", "CC_Medellin_estructura_empresarial_actividad.csv", C.RAW_DATOSGOV, None, None, 1),
    ("fkdi-8hm8", "CC_Medellin_estructura_empresarial_actividad_naturaleza_tamano.csv", C.RAW_DATOSGOV, None, None, 1),
    ("pb3w-3vmc", "CC_Medellin_estructura_comunas_actividad.csv", C.RAW_DATOSGOV, None, None, 1),
    ("2zc9-bpzw", "CC_Medellin_estructura_comunas_CIIU.csv", C.RAW_DATOSGOV, None, None, 1),
    ("vwqt-xc3z", "MinCIT_exportaciones_NME.csv", C.RAW_FUENTES_V2, None, None, 2),
    ("rfip-pkv5", "MADR_exportaciones_agricolas_2024_2026.csv", C.RAW_FUENTES_V2, None, None, 2),
    ("5fct-ib9u", "MinAgricultura_exportaciones_agricolas_2019_2025.csv", C.RAW_FUENTES_V2, None, None, 2),
]


def limpiar_identificaciones(ruta):
    """Deja numero_identificacion solo cuando es un NIT (nunca cédulas de personas)."""
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    df.loc[df["clase_identificacion"] != "NIT", "numero_identificacion"] = ""
    df.to_csv(ruta, index=False, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forzar", action="store_true", help="vuelve a descargar aunque el archivo exista")
    ap.add_argument("--solo", default="", help="ids de datos.gov.co separados por coma")
    ap.add_argument("--incluir-dane", action="store_true",
                    help="descarga también los microdatos EXPO 2025 del DANE (sin NIT; ~53 MB)")
    args = ap.parse_args()
    solo = {s.strip() for s in args.solo.split(",") if s.strip()}

    for ds, archivo, carpeta, select, where, _ in DATASETS:
        if solo and ds not in solo:
            continue
        destino = carpeta / archivo
        if not args.forzar and (destino.exists() or destino.with_suffix(".zip").exists()):
            log(f"ya existe   {destino.relative_to(C.RAW)}")
            continue
        n = socrata_csv(ds, destino, select=select, where=where)
        if ds == "c82u-588k":
            limpiar_identificaciones(destino)
        log(f"descargado  {destino.relative_to(C.RAW)} ({n:,} filas)")

    if args.incluir_dane:
        destino = C.RAW_DANE / "Expo_2025.zip"
        if args.forzar or not destino.exists():
            descargar(C.DANE_EXPO_2025_URL, destino)
            log(f"descargado  {destino.relative_to(C.RAW)}")


if __name__ == "__main__":
    main()
