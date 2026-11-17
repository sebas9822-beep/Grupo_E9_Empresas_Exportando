"""Paso 5 · Consultas por NIT en datos.gov.co para todos los exportadores del paso 4.

- RUES (Confecámaras, c82u-588k): matrícula de cada NIT en cualquier cámara del país.
- SECOP II (Colombia Compra Eficiente, jbjy-vk9h): contratos con el Estado, agregados por NIT.
  Se consulta el NIT con y sin dígito de verificación. No se guardan datos personales.

Es incremental: solo consulta los NIT que no se han consultado antes (registro en *_consultados.csv).
Con --forzar vuelve a consultar todos.
"""
import argparse
import csv
import pathlib
import sys
import urllib.parse

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from pipeline.comun import _leer_url, log, socrata_json, sql_lista  # noqa: E402
from pipeline.p02_descargar_datos_abiertos import RUES_COLUMNAS  # noqa: E402

RUES_DESTINO = C.RAW_DATOSGOV / "RUES_exportadores_nacional_por_NIT.csv"
SECOP_DESTINO = C.RAW_FUENTES_V2 / "SECOP_II_contratos_exportadores_por_NIT.csv"


def leer_existente(ruta):
    for p, comp in ((ruta, None), (ruta.with_suffix(".zip"), "zip")):
        if p.exists():
            return pd.read_csv(p, dtype=str, keep_default_na=False, compression=comp)
    return None


def consultados(ruta_datos, ids_en_datos):
    reg = ruta_datos.with_name(ruta_datos.stem + "_consultados.csv")
    if reg.exists():
        return reg, set(pd.read_csv(reg, dtype=str).NIT)
    return reg, ids_en_datos      # archivos anteriores sin registro: se asume consultado lo que ya aparece


def rues_por_nit(nits, lote=200):
    filas, encabezado = [], None
    for i in range(0, len(nits), lote):
        lst = sql_lista(nits[i:i + lote])
        params = {"$select": RUES_COLUMNAS, "$limit": 50000,
                  "$where": f"codigo_organizacion_juridica != '01' AND (nit in ({lst}) OR numero_identificacion in ({lst}))"}
        lineas = list(csv.reader(_leer_url("https://www.datos.gov.co/resource/c82u-588k.csv?" + urllib.parse.urlencode(params)).splitlines()))
        encabezado = encabezado or lineas[0]
        filas += lineas[1:]
        if (i // lote) % 10 == 0:
            log(f"  RUES {min(i + lote, len(nits)):,}/{len(nits):,} NIT · {len(filas):,} matrículas")
    df = pd.DataFrame(filas, columns=encabezado or RUES_COLUMNAS.split(","))
    df.loc[df["clase_identificacion"] != "NIT", "numero_identificacion"] = ""   # nunca cédulas
    return df


def secop_por_nit(pares, lote=150):
    salida = []
    sel = ("documento_proveedor, count(*) as n, sum(valor_del_contrato) as v, min(fecha_de_firma) as f1, "
           "max(fecha_de_firma) as f2, max(es_pyme) as p1, min(es_pyme) as p2, count(distinct nit_entidad) as ne")
    for i in range(0, len(pares), lote):
        ids = [x for p in pares[i:i + lote] for x in p]
        salida += socrata_json("jbjy-vk9h", {"$select": sel, "$where": f"documento_proveedor in ({sql_lista(ids)})",
                                             "$group": "documento_proveedor", "$limit": 50000})
        if (i // lote) % 20 == 0:
            log(f"  SECOP {min(i + lote, len(pares)):,}/{len(pares):,} NIT · {len(salida):,} proveedores")
    cols = {"documento_proveedor": "documento_proveedor", "n": "n_contratos", "v": "valor_total_contratos",
            "f1": "primera_firma", "f2": "ultima_firma", "p1": "es_pyme_max", "p2": "es_pyme_min", "ne": "n_entidades"}
    return pd.DataFrame(salida, columns=list(cols)).rename(columns=cols)


def actualizar(nombre, destino, nits, ids_existentes_fn, consultar_fn, forzar):
    previo = None if forzar else leer_existente(destino)
    ya = set() if previo is None else ids_existentes_fn(previo)
    reg, ya = consultados(destino, ya) if previo is not None else (destino.with_name(destino.stem + "_consultados.csv"), set())
    pendientes = nits[~nits.NIT.isin(ya)]
    if len(pendientes):
        log(f"{nombre}: consultando {len(pendientes):,} NIT nuevos")
        nuevo = consultar_fn(pendientes)
        df = nuevo if previo is None else pd.concat([previo, nuevo], ignore_index=True).drop_duplicates()
        destino.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(destino, index=False, encoding="utf-8")
        log(f"{nombre}: {len(df):,} filas → {destino.relative_to(C.RAW)}")
    else:
        log(f"{nombre}: sin NIT nuevos por consultar")
    pd.DataFrame({"NIT": sorted(ya | set(nits.NIT))}).to_csv(reg, index=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--muestra", type=int, default=0, help="solo los primeros N NIT (para probar)")
    args = ap.parse_args()
    if not C.NITS_PATH.exists():
        sys.exit("Falta la lista de NIT. Corre antes el paso 4.")
    nits = pd.read_csv(C.NITS_PATH, dtype=str)
    if args.muestra:
        nits = nits.head(args.muestra)
    dv = dict(zip(nits.NIT_DV, nits.NIT))
    actualizar("RUES", RUES_DESTINO, nits,
               lambda df: {x.lstrip("0") for x in pd.concat([df["nit"], df["numero_identificacion"]]) if x},
               lambda p: rues_por_nit(p.NIT.tolist()), args.forzar)
    actualizar("SECOP II", SECOP_DESTINO, nits,
               lambda df: {dv.get(x, x) for x in df["documento_proveedor"]},
               lambda p: secop_por_nit(list(zip(p.NIT, p.NIT_DV))), args.forzar)


if __name__ == "__main__":
    main()
