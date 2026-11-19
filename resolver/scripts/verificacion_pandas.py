"""Verificación independiente del dato a confirmar (2025): pandas sobre la BD principal, sin funciones de ventana.

Debe dar lo mismo que resolver/consultas/03a y 03b: 225 productos, 70,1 % ponderado, 73,1 % mediana,
52 productos con 90 % o más.

Uso (desde la raíz del repositorio, después de python crear_bd_analitica.py):
    python resolver/scripts/verificacion_pandas.py
"""
import os

import duckdb

BD_PRINCIPAL = os.environ.get("BD_PRINCIPAL", "datos/limpios/bd_analitica/BD_exportaciones_Colombia_analitica.duckdb")

# 1. Líneas de 2025 de origen Antioquia vendidas al exterior
con = duckdb.connect(BD_PRINCIPAL, read_only=True)
df = con.sql("""SELECT SUBPARTIDA, COD_PAIS_DESTINO, VALOR_FOB_USD
                FROM hechos_analitica
                WHERE ANIO = 2025 AND COD_DEPTO_ORIGEN = '05'
                  AND COD_PAIS_DESTINO NOT IN ('XCF', 'COL')""").df()
df["HS4"] = df["SUBPARTIDA"].str[:4]

# 2. Valor por producto y país, de mayor a menor dentro de cada producto
pp = (df.groupby(["HS4", "COD_PAIS_DESTINO"])["VALOR_FOB_USD"].sum()
        .reset_index().sort_values(["HS4", "VALOR_FOB_USD"], ascending=[True, False]))
pp = pp[pp["VALOR_FOB_USD"] > 0]

# 3. Por producto: total y parte de los tres primeros compradores
total = pp.groupby("HS4")["VALOR_FOB_USD"].sum()
top3 = pp.groupby("HS4").head(3).groupby("HS4")["VALOR_FOB_USD"].sum()
res = (top3 / total).rename("top3").to_frame().join(total.rename("fob"))
res = res[res["fob"] >= 1e6]

print("productos:", len(res))
print("ponderado: %.1f %%" % (100 * (res["top3"] * res["fob"]).sum() / res["fob"].sum()))
print("mediana: %.1f %%" % (100 * res["top3"].median()))
print("productos con 90 %% o más: %d" % (res["top3"] >= 0.9).sum())
print("total exterior 2025: USD %.1f M" % (df["VALOR_FOB_USD"].sum() / 1e6))
