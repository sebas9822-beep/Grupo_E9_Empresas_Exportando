"""Paso 8 · Excel para usuarios no técnicos: data/processed/directorio_exportadores_antioquenos.xlsx

Hojas: Exportadores_antioquenos (A+B), Vinculo_parcial_Antioquia (C), Serie_mensual,
Validacion_MinCIT, Validacion_MADR y Diccionario.
"""
import pathlib
import sys

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from pipeline.comun import log  # noqa: E402

TEXTO = {"NIT": str, "TOP5_SUBPARTIDAS": str, "CAPITULO_ARANCEL_PRINCIPAL": str, "CIIU_PRINCIPAL_RUES": str,
         "CIIU_SECUNDARIO_RUES": str, "MATRICULA": str, "SS_CIIU": str}
ANCHAS = {"descripcion", "VINCULO_ANTIOQUIA", "TOP3_PAISES_DESTINO", "TOP5_SUBPARTIDAS", "RAZON_SOCIAL"}


def formatear(ruta):
    wb = openpyxl.load_workbook(ruta)
    fondo, letra = PatternFill("solid", fgColor="0033A0"), Font(color="FFFFFF", bold=True)
    for ws in wb.worksheets:
        es_dic = ws.title == "Diccionario"
        ws.freeze_panes = None if es_dic else "A2"
        ws.auto_filter.ref = ws.dimensions
        for c in ws[1]:
            c.fill, c.font = fondo, letra
            c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[1].height = 42
        for i, celda in enumerate(ws[1], start=1):
            col = openpyxl.utils.get_column_letter(i)
            h = str(celda.value or "")
            ws.column_dimensions[col].width = 60 if h in ANCHAS else (28 if es_dic else 16)
            if h.startswith(("FOB_", "PESO", "SECOP_VALOR")):
                for cell in ws[col][1:]:
                    cell.number_format = "#,##0"
        if es_dic:
            for fila in ws.iter_rows(min_row=2):
                for c in fila:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(ruta)


def main():
    P = C.PROCESSED
    nac = pd.read_csv(P / "directorio_exportadores_nacional.csv", dtype=TEXTO)
    ant = pd.read_csv(P / "directorio_exportadores_antioquenos.csv", dtype=TEXTO)
    parcial = nac[nac.VINCULO_ANTIOQUIA.str.startswith("C.")]
    destino = P / "directorio_exportadores_antioquenos.xlsx"
    with pd.ExcelWriter(destino, engine="openpyxl") as w:
        ant.to_excel(w, sheet_name="Exportadores_antioquenos", index=False)
        parcial.to_excel(w, sheet_name="Vinculo_parcial_Antioquia", index=False)
        pd.read_csv(P / "serie_mensual_antioquia.csv").to_excel(w, sheet_name="Serie_mensual", index=False)
        pd.read_csv(P / "validacion_mincit_nme.csv").to_excel(w, sheet_name="Validacion_MinCIT", index=False)
        pd.read_csv(P / "validacion_madr_agricolas.csv").to_excel(w, sheet_name="Validacion_MADR", index=False)
        pd.read_csv(C.DOCS / "diccionario_directorio.csv").to_excel(w, sheet_name="Diccionario", index=False)
    formatear(destino)
    log(f"Excel: {destino.relative_to(C.ROOT)} ({len(ant):,} exportadores antioqueños, {len(parcial):,} con vínculo parcial)")


if __name__ == "__main__":
    main()
