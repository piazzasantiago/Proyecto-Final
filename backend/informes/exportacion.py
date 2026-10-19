"""Exportación de los informes a Excel (.xlsx) y PDF."""

import datetime
import unicodedata
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF = "application/pdf"


def _fecha_es(texto):
    return datetime.date.fromisoformat(texto).strftime("%d/%m/%Y")


def _subtitulo(informe):
    partes = []
    if informe.get("periodo"):
        p = informe["periodo"]
        partes.append(f"Período: {_fecha_es(p['desde'])} al {_fecha_es(p['hasta'])}")
    partes += [f"{etiqueta}: {valor}" for etiqueta, valor in informe.get("filtros", [])]
    return " · ".join(partes)


def _numero(valor, tipo):
    """Texto de un valor para el PDF (formato argentino)."""
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, str):
        # Etiquetas de la fila de totales ("Total", "Promedio") o fechas ISO.
        try:
            return _fecha_es(valor) if tipo == "fecha" else valor
        except ValueError:
            return valor
    if tipo == "entero":
        return f"{int(valor):,}".replace(",", ".")
    if tipo == "decimal":
        texto = f"{float(valor):,.2f}".rstrip("0").rstrip(".") if float(valor) % 1 else f"{int(valor):,}"
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return str(valor)


def nombre_archivo(informe, extension):
    # Sin tildes: el nombre viaja en un encabezado HTTP.
    titulo = unicodedata.normalize("NFKD", informe["titulo"]).encode("ascii", "ignore").decode()
    base = titulo.lower().replace("informe de ", "informe-").replace("indicador: ", "indicador-")
    base = "".join(c if c.isalnum() or c == "-" else "-" for c in base).strip("-")
    while "--" in base:
        base = base.replace("--", "-")
    if informe.get("periodo"):
        p = informe["periodo"]
        base += f"-{p['desde']}_{p['hasta']}"
    return f"{base}.{extension}"


def a_xlsx(informe):
    columnas = informe["columnas"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Informe"[:31]

    ws["A1"] = informe["titulo"]
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = _subtitulo(informe)
    ws["A3"] = f"Generado el {timezone.localtime():%d/%m/%Y %H:%M}"
    ws["A3"].font = Font(italic=True, color="666666")

    fila_encabezado = 5
    relleno = PatternFill("solid", fgColor="2E7D4F")
    for i, col in enumerate(columnas, start=1):
        celda = ws.cell(row=fila_encabezado, column=i, value=col["titulo"])
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = relleno
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def escribir(fila, datos, negrita=False):
        for i, col in enumerate(columnas, start=1):
            valor = datos.get(col["clave"])
            if col["tipo"] == "fecha" and isinstance(valor, str) and len(valor) == 10 and valor[4] == "-":
                valor = datetime.date.fromisoformat(valor)
            celda = ws.cell(row=fila, column=i, value=valor)
            if col["tipo"] == "fecha" and isinstance(valor, datetime.date):
                celda.number_format = "DD/MM/YYYY"
            elif col["tipo"] == "decimal":
                celda.number_format = "#,##0.00"
            elif col["tipo"] == "entero":
                celda.number_format = "#,##0"
            if negrita:
                celda.font = Font(bold=True)

    fila = fila_encabezado + 1
    for datos in informe["filas"]:
        escribir(fila, datos)
        fila += 1
    if informe.get("totales"):
        escribir(fila, informe["totales"], negrita=True)

    for i, col in enumerate(columnas, start=1):
        largo = max([len(col["titulo"])] + [len(str(f.get(col["clave"]) or "")) for f in informe["filas"]])
        ws.column_dimensions[get_column_letter(i)].width = min(max(largo + 2, 12), 45)
    ws.freeze_panes = ws.cell(row=fila_encabezado + 1, column=1)

    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()


def a_pdf(informe):
    columnas = informe["columnas"]
    estilos = getSampleStyleSheet()
    salida = BytesIO()
    doc = SimpleDocTemplate(
        salida, pagesize=landscape(A4), title=informe["titulo"],
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    historia = [
        Paragraph(informe["titulo"], estilos["Title"]),
        Paragraph(_subtitulo(informe), estilos["Normal"]),
        Paragraph(f"Generado el {timezone.localtime():%d/%m/%Y %H:%M}", estilos["Italic"]),
        Spacer(1, 0.5 * cm),
    ]

    celda = estilos["BodyText"]
    celda.fontSize = 8
    celda.leading = 10

    datos = [[Paragraph(f"<font color='white'><b>{c['titulo']}</b></font>", celda) for c in columnas]]
    for f in informe["filas"]:
        datos.append([Paragraph(_numero(f.get(c["clave"]), c["tipo"]), celda) for c in columnas])
    if informe.get("totales"):
        datos.append([
            Paragraph(f"<b>{_numero(informe['totales'].get(c['clave']), c['tipo'])}</b>", celda)
            for c in columnas
        ])
    if len(datos) == 1:
        historia.append(Paragraph("No hay datos para los filtros elegidos.", estilos["Normal"]))
    else:
        tabla = Table(datos, repeatRows=1)
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D4F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BBBBBB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7F4")]),
        ]
        tabla.setStyle(TableStyle(estilo))
        historia.append(tabla)
    doc.build(historia)
    return salida.getvalue()
