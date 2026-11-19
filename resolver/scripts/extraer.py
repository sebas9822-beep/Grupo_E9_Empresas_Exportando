"""Extrae de cada base mensual DIAN (.zip con un .xlsx) las columnas del análisis de concentración y las guarda en parquet.

Procesa los zip de zips/ que aún no tengan parquet en parquet/. Si se pasa --esperar, sigue revisando hasta que
existan N parquet (para correr mientras avanza la descarga).
"""
import pathlib, re, sys, time, zipfile, shutil
import pyarrow as pa, pyarrow.parquet as pq
from python_calamine import CalamineWorkbook

BASE = pathlib.Path(__file__).parent
ZIPS, OUT, TMP = BASE / "zips", BASE / "parquet", BASE / "tmp"
OUT.mkdir(exist_ok=True); TMP.mkdir(exist_ok=True)
TEXTO = ["FECHA_PROCESO", "NIT_EXPORTADOR", "TIPO_IDENT", "COD_PAIS_DESTINO_NUM", "COD_PAIS_DESTINO_ALF", "COD_PAIS_DESTINO",
         "PAIS_DESTINO_FINAL", "COD_REGION_ORIGEN", "REGION_DE_ORIGEN", "SUBPARTIDA", "COD_MODALIDAD_EXPORTACION",
         "COD_UNIDAD_FISICA_ALF", "RAZON_SOCIAL_EXPORTADOR"]
NUM = ["CANTIDAD_UNIDADES_FISICAS", "PESO_NETO_KGS", "VALOR_FOB_USD"]
MESES = {m: i + 1 for i, m in enumerate(["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
                                         "Septiembre", "Octubre", "Noviembre", "Diciembre"])}


def txt(v):
    if v is None or v == "":
        return None
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    return " ".join(str(v).split()) or None


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(str(v).replace(",", "."))


def procesar(z):
    m = re.match(r"(\d{2})_Exportaciones_(\d{4})_(\w+)\.zip", z.name)
    anio, mes = int(m.group(2)), int(m.group(1))
    destino = OUT / f"{anio}_{mes:02d}.parquet"
    if destino.exists():
        return None
    with zipfile.ZipFile(z) as zf:
        xl = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls", ".csv"))][0]
        ruta = TMP / pathlib.Path(xl).name
        with zf.open(xl) as src, open(ruta, "wb") as dst:
            shutil.copyfileobj(src, dst)
    filas = CalamineWorkbook.from_path(str(ruta)).get_sheet_by_index(0).to_python()
    ruta.unlink()
    enc = [" ".join(str(h).split()).upper() for h in filas[0]]
    idx = {h: i for i, h in enumerate(enc)}
    faltan = [c for c in TEXTO + NUM if c not in idx]
    datos = {c: [] for c in TEXTO + NUM}
    for f in filas[1:]:
        if not any(f):
            continue
        for c in TEXTO:
            datos[c].append(txt(f[idx[c]]) if c in idx else None)
        for c in NUM:
            datos[c].append(num(f[idx[c]]) if c in idx else None)
    tabla = pa.table({**{c: pa.array(datos[c], pa.string()) for c in TEXTO},
                      **{c: pa.array(datos[c], pa.float64()) for c in NUM},
                      "ANIO_ARCHIVO": pa.array([anio] * len(datos["VALOR_FOB_USD"]), pa.int16()),
                      "MES_ARCHIVO": pa.array([mes] * len(datos["VALOR_FOB_USD"]), pa.int8())})
    pq.write_table(tabla, destino, compression="zstd")
    return anio, mes, len(datos["VALOR_FOB_USD"]), faltan


if __name__ == "__main__":
    objetivo = int(sys.argv[sys.argv.index("--esperar") + 1]) if "--esperar" in sys.argv else 0
    while True:
        for z in sorted(ZIPS.glob("*.zip")):
            try:
                r = procesar(z)
                if r:
                    print(*r, flush=True)
            except Exception as e:  # noqa: BLE001
                print("ERROR", z.name, e, flush=True)
        if len(list(OUT.glob("*.parquet"))) >= objetivo:
            break
        time.sleep(20)
    print("FIN", len(list(OUT.glob("*.parquet"))))
