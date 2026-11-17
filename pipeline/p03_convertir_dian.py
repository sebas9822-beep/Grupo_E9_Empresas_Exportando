"""Paso 3 · Convierte cada base mensual DIAN (.zip con .xlsx) a parquet en datos/intermedios/mensual/.

Solo procesa los meses nuevos; con --forzar los rehace todos.
"""
import argparse
import io
import pathlib
import re
import sys
import zipfile

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from pipeline.comun import log  # noqa: E402

NUMERICAS = ["CANTIDAD_UNIDADES_FISICAS", "PESO_BRUTO_KGS", "PESO_NETO_KGS", "VALOR_FOB_USD",
             "VALOR_FOB_PESOS", "VLR_SERIE_AGREGADO_NAL_USD", "VALOR_SERIE_FLETES_USD",
             "VALOR_SERIE_SEGUROS_USD", "VLR_SERIE_OTROS_GASTOS_USD"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--forzar", action="store_true")
    args = ap.parse_args()
    C.INTERIM_MENSUAL.mkdir(parents=True, exist_ok=True)
    zips = sorted(C.RAW_DIAN_MENSUAL.glob("*/*_Exportaciones_*.zip"))
    if not zips:
        sys.exit(f"No hay bases mensuales en {C.RAW_DIAN_MENSUAL}. Corre el paso 1.")
    for z in zips:
        m = re.match(r"(\d\d)_Exportaciones_(\d{4})_", z.name)
        mes, anio = int(m.group(1)), int(m.group(2))
        destino = C.INTERIM_MENSUAL / f"expo_{anio}_{mes:02d}.parquet"
        if destino.exists() and not args.forzar and destino.stat().st_mtime >= z.stat().st_mtime:
            continue
        with zipfile.ZipFile(z) as zf:
            nombre = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls", ".csv", ".txt"))][0]
            datos = zf.read(nombre)
        df = pd.read_excel(io.BytesIO(datos), engine="calamine", dtype=str)
        df.columns = [c.strip().upper() for c in df.columns]
        for c in NUMERICAS:
            if c in df:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df.insert(0, "ANIO", anio)
        df.insert(1, "MES", mes)
        df.insert(2, "ARCHIVO_FUENTE", z.name)
        df.to_parquet(destino, index=False)
        log(f"{destino.name}: {len(df):,} filas, FOB USD {df.VALOR_FOB_USD.sum() / 1e6:,.1f} M")
    log(f"{len(list(C.INTERIM_MENSUAL.glob('*.parquet')))} meses en {C.INTERIM_MENSUAL.relative_to(C.ROOT)}")


if __name__ == "__main__":
    main()
