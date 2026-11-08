"""Exportación de los informes a Excel (.xlsx) y PDF."""

import datetime
import unicodedata
from io import BytesIO
from pathlib import Path

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.drawing.image import Image as ImagenExcel
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils.units import pixels_to_EMU
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF = "application/pdf"

# Marca del sistema (logo con la A integrada al huevo dorado). Hay tres versiones:
#   - LOGO_COMPLETO: el logo con el nombre, en blanco y dorado sobre fondo transparente. Va en
#     el encabezado del PDF, sobre la banda verde.
#   - LOGO: el ícono de la app, una baldosa verde con el huevo dorado. Va en el Excel,
#     que tiene fondo blanco.
#   - LOGO_ARO: solo el huevo dorado, con fondo transparente. Va en el PDF, sobre la
#     banda verde del encabezado y como marca de agua.
RECURSOS = Path(__file__).resolve().parent / "recursos"
LOGO = RECURSOS / "logo.png"
LOGO_COMPLETO = RECURSOS / "logo-completo.png"
LOGO_ARO = RECURSOS / "logo-aro.png"


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

    if informe.get("grafico"):
        _grafico_excel(ws, informe, fila_encabezado, fila_encabezado + len(informe["filas"]))

    for i, col in enumerate(columnas, start=1):
        largo = max([len(col["titulo"])] + [len(str(f.get(col["clave"]) or "")) for f in informe["filas"]])
        ws.column_dimensions[get_column_letter(i)].width = min(max(largo + 2, 12), 45)
    ws.freeze_panes = ws.cell(row=fila_encabezado + 1, column=1)

    # Al imprimir, todas las columnas (y el logo) entran en el ancho de la hoja.
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    _logo_excel(ws, columnas)

    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()


def _grafico_excel(ws, informe, fila_encabezado, ultima_fila):
    """Gráfica de líneas con la serie real y, si hay, el valor objetivo."""
    columnas = informe["columnas"]
    claves = [c["clave"] for c in columnas]
    grafico = LineChart()
    grafico.title = informe["titulo"].replace("Indicador: ", "")
    grafico.height, grafico.width = 9, 20
    grafico.y_axis.title = informe["grafico"].get("unidad") or None
    grafico.y_axis.delete = False
    grafico.x_axis.delete = False
    grafico.x_axis.number_format = "DD/MM"
    grafico.y_axis.scaling.min = 0
    for clave in ("valor", "objetivo"):
        if clave in claves:
            col = claves.index(clave) + 1
            grafico.add_data(
                Reference(ws, min_col=col, min_row=fila_encabezado, max_row=ultima_fila), titles_from_data=True
            )
    grafico.set_categories(Reference(ws, min_col=1, min_row=fila_encabezado + 1, max_row=ultima_fila))
    serie_real = grafico.series[0]
    serie_real.graphicalProperties.line.solidFill = "2E7D4F"
    serie_real.marker.symbol = "circle"
    serie_real.smooth = False
    if len(grafico.series) > 1:
        objetivo = grafico.series[1]
        objetivo.graphicalProperties.line.solidFill = "C9962B"
        objetivo.graphicalProperties.line.dashStyle = "dash"
        objetivo.marker.symbol = "none"
        objetivo.smooth = False
    ws.add_chart(grafico, f"{get_column_letter(len(columnas) + 2)}5")


def _grafico_pdf(informe):
    """Dibujo de líneas (reportlab) con la serie real y el valor objetivo."""
    g = informe["grafico"]
    ancho, alto = 24 * cm, 8 * cm
    dibujo = Drawing(ancho, alto)
    n = len(g["etiquetas"])
    colores = [colors.HexColor("#2E7D4F"), colors.HexColor("#C9962B")]

    # Los días sin dato (None) cortan la línea: cada tramo es una serie propia.
    datos, estilos = [], []
    for k, serie in enumerate(g["series"]):
        tramo = []
        for i, v in enumerate(serie["valores"] + [None]):
            if v is None:
                if tramo:
                    datos.append(tramo)
                    estilos.append(k)
                tramo = []
            else:
                tramo.append((i, v))
    if not datos:
        return None

    grafico = LinePlot()
    grafico.x, grafico.y = 1.6 * cm, 1.2 * cm
    grafico.width, grafico.height = ancho - 2.4 * cm, alto - 2 * cm
    grafico.data = datos
    maximo = max(v for tramo in datos for _, v in tramo)
    grafico.yValueAxis.valueMin = 0
    grafico.yValueAxis.valueMax = maximo * 1.1 if maximo > 0 else 10
    grafico.xValueAxis.valueMin = 0
    grafico.xValueAxis.valueMax = max(n - 1, 1)
    paso = max(1, -(-n // 10))
    grafico.xValueAxis.valueSteps = list(range(0, n, paso))
    grafico.xValueAxis.labelTextFormat = lambda i: _fecha_es(g["etiquetas"][int(i)])[:5] if 0 <= int(i) < n else ""
    grafico.xValueAxis.labels.fontSize = 7
    grafico.yValueAxis.labels.fontSize = 7
    grafico.yValueAxis.gridStrokeColor = colors.HexColor("#E4E9E6")
    grafico.yValueAxis.visibleGrid = True
    for i, k in enumerate(estilos):
        grafico.lines[i].strokeColor = colores[k]
        grafico.lines[i].strokeWidth = 1.8
        grafico.lines[i].symbol = None
        if k == 1:
            grafico.lines[i].strokeDashArray = (4, 3)
        elif len(datos[i]) == 1:
            from reportlab.graphics.widgets.markers import makeMarker
            grafico.lines[i].symbol = makeMarker("FilledCircle")
            grafico.lines[i].symbol.size = 4
            grafico.lines[i].symbol.fillColor = colores[k]
    dibujo.add(grafico)

    # Leyenda.
    x = 1.6 * cm
    for k, serie in enumerate(g["series"]):
        dibujo.add(Line(x, alto - 0.5 * cm, x + 0.8 * cm, alto - 0.5 * cm, strokeColor=colores[k], strokeWidth=2))
        dibujo.add(String(x + 1 * cm, alto - 0.75 * cm, serie["nombre"], fontSize=8))
        x += 7 * cm
    return dibujo


VERDE_OSCURO = colors.HexColor("#1B4A34")
DORADO = colors.HexColor("#D9A441")
GRIS = colors.HexColor("#6B7280")

ALTO_ENCABEZADO = 2.1 * cm


def _medidas_aro(alto):
    """Ancho y alto con que se dibuja el huevo para un alto dado, sin deformarlo."""
    from PIL import Image

    with Image.open(LOGO_ARO) as imagen:
        ancho_px, alto_px = imagen.size
    return alto * ancho_px / alto_px, alto


def _proporcion(ruta):
    """Ancho dividido alto de una imagen."""
    from PIL import Image

    with Image.open(ruta) as imagen:
        ancho_px, alto_px = imagen.size
    return ancho_px / alto_px


def _marca_de_agua():
    """El huevo dorado muy tenue (10 % de opacidad) para usarlo de fondo."""
    from PIL import Image

    imagen = Image.open(LOGO_ARO).convert("RGBA")
    alfa = imagen.getchannel("A").point(lambda v: int(v * 0.10))
    imagen.putalpha(alfa)
    memoria = BytesIO()
    imagen.save(memoria, format="PNG")
    memoria.seek(0)
    return ImageReader(memoria)


def _decorar_pdf(informe):
    """Encabezado, marca de agua y pie de cada página (se dibuja debajo del contenido)."""
    generado = f"Generado el {timezone.localtime():%d/%m/%Y %H:%M}"

    def dibujar(lienzo, doc):
        ancho, alto = doc.pagesize
        lienzo.saveState()

        # Marca de agua: el huevo grande y casi transparente, centrado.
        if LOGO_ARO.exists():
            ancho_marca, alto_marca = _medidas_aro(12 * cm)
            lienzo.drawImage(
                _marca_de_agua(), (ancho - ancho_marca) / 2, (alto - alto_marca) / 2 - 0.5 * cm,
                width=ancho_marca, height=alto_marca, mask="auto",
            )

        # Encabezado: banda verde con el logo a la izquierda y la fecha de generación a la derecha.
        lienzo.setFillColor(VERDE_OSCURO)
        lienzo.rect(0, alto - ALTO_ENCABEZADO, ancho, ALTO_ENCABEZADO, stroke=0, fill=1)
        lienzo.setFillColor(DORADO)
        lienzo.rect(0, alto - ALTO_ENCABEZADO - 0.12 * cm, ancho, 0.12 * cm, stroke=0, fill=1)
        if LOGO_COMPLETO.exists():
            alto_logo = 1.2 * cm
            ancho_logo = alto_logo * _proporcion(LOGO_COMPLETO)
            lienzo.drawImage(
                str(LOGO_COMPLETO), doc.leftMargin, alto - 1.5 * cm,
                width=ancho_logo, height=alto_logo, mask="auto",
            )
        else:
            lienzo.setFillColor(colors.white)
            lienzo.setFont("Helvetica-Bold", 20)
            lienzo.drawString(doc.leftMargin, alto - 1.15 * cm, "AviGest")
        lienzo.setFont("Helvetica", 9.5)
        lienzo.setFillColor(colors.HexColor("#EEC568"))
        lienzo.drawString(doc.leftMargin, alto - 1.88 * cm, "Gestión de granja avícola")
        lienzo.setFillColor(colors.white)
        lienzo.setFont("Helvetica", 9)
        lienzo.drawRightString(ancho - doc.rightMargin, alto - 1.2 * cm, generado)

        # Pie: línea fina y título del informe (el número de página lo agrega el lienzo).
        lienzo.setStrokeColor(colors.HexColor("#D1D5DB"))
        lienzo.setLineWidth(0.5)
        lienzo.line(doc.leftMargin, 1.35 * cm, ancho - doc.rightMargin, 1.35 * cm)
        lienzo.setFillColor(GRIS)
        lienzo.setFont("Helvetica", 8)
        lienzo.drawString(doc.leftMargin, 0.85 * cm, f"AviGest · {informe['titulo']}")
        lienzo.restoreState()

    return dibujar


class _LienzoNumerado(Canvas):
    """Lienzo que escribe "Página X de Y" en el pie una vez que se sabe el total."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas = []

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self.setFont("Helvetica", 8)
            self.setFillColor(GRIS)
            ancho = self._pagesize[0]
            self.drawRightString(ancho - 1.5 * cm, 0.85 * cm, f"Página {self._pageNumber} de {total}")
            super().showPage()
        super().save()


def _logo_excel(ws, columnas, lado=56):
    """Logo en el borde superior derecho de la hoja (última columna de la tabla, o la G)."""
    if not LOGO.exists():
        return
    imagen = ImagenExcel(str(LOGO))
    imagen.width = imagen.height = lado
    # Al menos hasta la columna G, para no tapar el subtítulo en los informes con pocas columnas.
    ultima = max(len(columnas), 7)
    ancho_col = ws.column_dimensions[get_column_letter(ultima)].width or 13
    ancho_px = int(ancho_col * 7 + 5)
    # Pegado al borde derecho de la última columna, sin pisar el encabezado (fila 5).
    desplazamiento = max(ancho_px - lado - 4, 0)
    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 22
    imagen.anchor = OneCellAnchor(
        _from=AnchorMarker(col=ultima - 1, colOff=pixels_to_EMU(desplazamiento), row=0, rowOff=pixels_to_EMU(2)),
        ext=XDRPositiveSize2D(pixels_to_EMU(lado), pixels_to_EMU(lado)),
    )
    ws.add_image(imagen)


def a_pdf(informe):
    columnas = informe["columnas"]
    estilos = getSampleStyleSheet()
    salida = BytesIO()
    doc = SimpleDocTemplate(
        salida, pagesize=landscape(A4), title=informe["titulo"],
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=3.2 * cm, bottomMargin=1.9 * cm,
    )
    historia = [
        Paragraph(informe["titulo"], estilos["Title"]),
        Paragraph(_subtitulo(informe), estilos["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    if informe.get("grafico"):
        dibujo = _grafico_pdf(informe)
        if dibujo is not None:
            historia += [dibujo, Spacer(1, 0.4 * cm)]

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
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, colors.Color(0.953, 0.969, 0.957, alpha=0.8)]),
        ]
        tabla.setStyle(TableStyle(estilo))
        historia.append(tabla)
    decorar = _decorar_pdf(informe)
    doc.build(historia, onFirstPage=decorar, onLaterPages=decorar, canvasmaker=_LienzoNumerado)
    return salida.getvalue()
