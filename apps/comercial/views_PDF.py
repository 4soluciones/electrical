import decimal

import reportlab
from django.http import HttpResponse, response
from reportlab.lib.colors import black, white, gray, red, green, blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Spacer, tables
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4, A5, C7
from reportlab.lib.units import mm, cm, inch
from reportlab.platypus import Table, Flowable
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import Canvas
from reportlab.rl_settings import defaultPageSize
from reportlab.lib.colors import PCMYKColor, PCMYKColorSep, Color, black, blue, red, pink
from electrical import settings
from .models import Programming, Guide, GuideMotive, GuideDetail, GuideEmployee, FuelProgramming
from apps.sales.number_to_letters import numero_a_moneda
import io
import os
import datetime

PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Justify_Square', alignment=TA_JUSTIFY, leading=10, fontName='Square', fontSize=10))
styles.add(
    ParagraphStyle(name='header2', alignment=TA_CENTER, leading=13, fontName='Helvetica', fontSize=8))
styles.add(
    ParagraphStyle(name='header1', alignment=TA_CENTER, leading=13, fontName='Helvetica-Bold', fontSize=12))
style = styles["Normal"]
pdfmetrics.registerFont(TTFont('Square', 'square-721-condensed-bt.ttf'))

def guide_print(self, pk=None):
    response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = 'attachment; filename="operating_lease_contract.pdf"'

    buff = io.BytesIO()

    xmax = 595
    ymax = 842

    ml = 3.0 * cm
    mr = 3.0 * cm
    ms = 3.75 * cm
    mi = 2.5 * cm

    doc = SimpleDocTemplate(buff,
                            pagesize=A4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            )
    # Register Fonts
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    pdfmetrics.registerFont(TTFont('Square', 'sqr721bc.ttf'))
    pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY,
                              leading=13, fontName='Newgot', fontSize=12))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER,
                              leading=13, fontName='Square', fontSize=11))

    # pdfmetrics.registerFont(TTFont('Square', os.path.dirname(os.path.abspath(__file__)) + '/static/fonts/sqr721bc.ttf'))
    # products = []
    # styles = getSampleStyleSheet()
    header = Paragraph("Listado de Productos", styles['Center'])

    Story = []

    Story.append(header)
    Story.append(Spacer(1, 13))
    ptext = 'Conste el presente contrato de arrendamiento operativo, que celebran de una parte la \
                empresa SERVICIOS GENERALES TURISMO AREQUIPA S.A.C., representado por su Gerente \
                General don GUSTAVO GUILLERMO MUÑOZ TACUSI, identificado con DNI N° 29326621, con \
                domicilio en la Av. Tacna y Arica 207, distrito Cercado, Provincia de Arequipa, a quien en lo \
                sucesivo se denominará <b>LA EMPRESA</b> y de otra parte don %s \
                identificado con DNI N° %s con domicilio en %s a quien en lo sucesivo se denominará \
                <b>EL PROPIETARIO AFILIADO</b>; en los términos contenidos en las siguientes cláusulas:'

    Story.append(Paragraph(ptext, styles["Justify"]))

    # products.append(header)
    # headings = ('Id', 'Descrición', 'Activo', 'Creación')
    # if not pk:
    #     all_products = [(p.id, p.name, p.is_enabled, p.code)
    #                     for p in Product.objects.all().order_by('pk')]
    # else:
    #     all_products = [(p.id, p.name, p.is_enabled, p.code)
    #                     for p in Product.objects.filter(id=pk)]
    # t = Table([headings] + all_products)
    # t.setStyle(TableStyle(
    #     [
    #         ('GRID', (0, 0), (3, -1), 1, colors.dodgerblue),
    #         ('LINEBELOW', (0, 0), (-1, 0), 2, colors.darkblue),
    #         ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue)
    #     ]
    # ))
    #
    # Story.append(t)

    doc.build(Story, onLaterPages=operating_lease_contract_template)
    response.write(buff.getvalue())
    buff.close()
    return response


def operating_lease_contract_template(canvas, doc):
    xmax = 595
    ymax = 842

    ml = 3.0 * cm
    mr = 3.0 * cm
    ms = 3.75 * cm
    mi = 2.5 * cm

    if doc.page == 1:
        # Save the current settings
        canvas.saveState()

        canvas.setFillColor(black)
        # canvas.setFont('Helvetica-Bold', 10)
        canvas.setDash(1, 1)
        canvas.line(ml - ms + 155, 100, ml - ms + 285, 100)
        canvas.line(ml - ms + 335, 100, ml - ms + 485, 100)

        canvas.drawString(ml - ms + 185, 85, 'LA EMPRESA')
        canvas.drawString(ml - ms + 343, 85, 'EL PROPIETARIO AFILIADO')

        # Restore setting to before function call
        canvas.restoreState()
        # translate then scale
        canvas.translate(2.4 * inch, 1.5 * inch)
        canvas.scale(0.3, 0.5)
        canvas.drawString(0, 2.7 * inch, "Translate then scale")


def myFirstPage(request):
    response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = 'attachment; filename="owners_and_vehicles_update.pdf"'
    xmax = 21 * cm
    ymax = 29.7 * cm

    ml = 3 * cm
    mr = 3 * cm
    ms = 2.5 * cm
    mi = 2.5 * cm

    width_page = xmax - 2 * mr

    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)

    canvas.setLineWidth(.3)

    canvas.setFont('Times-Bold', 12)
    canvas.drawString(ml + 30, 795, 'FICHA DE ACTUALIZACION DEL PROPIETARIO  Y VEHÍCULO')

    canvas.setFillColor(white)
    canvas.rect(ml, 740, 50, 36, stroke=1, fill=1)
    canvas.rect(ml + 50, 740, 35, 36, stroke=1, fill=1)
    canvas.rect(ml + 50 + 35, 740, 35, 36, stroke=1, fill=1)
    canvas.rect(ml + 50 + 35 + 35, 740, 35, 36, stroke=1, fill=1)
    canvas.line(ml + 50, 740 + 18, ml + 50 + 35 + 35 + 35, 740 + 18)

    canvas.rect(ml + 200, 740, 50, 36, stroke=1, fill=1)

    canvas.rect(ml + 275 - 15, 740, 46, 36, stroke=1, fill=1)
    canvas.rect(ml + 275 - 15 + 46, 740, 44, 36, stroke=1, fill=1)
    canvas.rect(ml + 275 - 15 + 46 + 44, 740, 75, 36, stroke=1, fill=1)
    canvas.line(ml + 275 - 15, 740 + 18, ml + 275 + 40 + 40 + 70, 740 + 18)
    canvas.line(ml + 275 + 40 + 40 + 35, 740, ml + 275 + 40 + 40 + 35, 740 + 18)

    canvas.setFillColor(black)
    canvas.setFont('Times-Roman', 10)
    canvas.drawString(ml + 4, 740 + 9 + 4, "FECHA")
    canvas.drawString(ml + 50 + 4, 740 + 18 + 4, "DÍA")
    canvas.drawString(ml + 50 + 35 + 4, 740 + 18 + 4, "MES")
    canvas.drawString(ml + 50 + 35 + 35 + 4, 740 + 18 + 4, "AÑO")

    canvas.drawString(ml + 50 + 35 + 35 + 4, 740 + 4, "2017")

    canvas.drawString(ml + 50 * 2 + 35 * 2 + 4, 740 + 9 + 4, "Móvil")

    canvas.setFont('Helvetica', 6)
    canvas.drawString(ml + 275 - 15 + 2, 740 + 18 + 4, "PROPIETARIO")
    canvas.drawString(ml + 275 - 15 + 46 + 2, 740 + 18 + 4, "CONDUCTOR")
    canvas.drawString(ml + 275 - 15 + 46 + 44 + 2, 740 + 18 + 4, "EQUIPO COMUNICACIÓN")

    canvas.setFont('Times-Roman', 10)
    canvas.drawString(ml + 275 - 15 + 46 + 66 + 2, 740 + 4, "SI")
    canvas.drawString(ml + 275 - 15 + 46 + 66 + 22 + 2, 740 + 4, "NO")

    canvas.setFillColor(black)
    canvas.setFont('Times-Bold', 11)
    canvas.drawString(ml - 0, 715, 'I.- DATOS DE LA PERSONA JURIDICA')

    # canvas.setFillColor(white)
    # canvas.rect(ml - 0, 710, width_page, 10, stroke=1, fill=1)

    canvas.setFillColor(white)
    canvas.rect(ml, 690, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142, 690, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142 + 142, 690, 141, 15, stroke=1, fill=1)

    canvas.rect(ml, 675, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142, 675, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142 + 142, 675, 141, 15, stroke=1, fill=1)

    canvas.rect(ml, 645, 42, 30, stroke=1, fill=1)
    canvas.rect(ml + 42, 645, 100, 30, stroke=1, fill=1)
    canvas.rect(ml + 142, 645, 142, 30, stroke=1, fill=1)
    canvas.rect(ml + 142 + 142, 645, 80, 30, stroke=1, fill=1)
    canvas.rect(ml + 142 + 142 + 80, 645, 61, 30, stroke=1, fill=1)
    canvas.line(ml + 42, 645 + 15, ml + 142 + 142 + 80 + 61, 645 + 15)

    canvas.rect(ml, 630, 42, 15, stroke=1, fill=1)
    canvas.rect(ml + 42, 630, 425 - 42, 15, stroke=1, fill=1)

    canvas.rect(ml, 570, 42, 60, stroke=1, fill=1)
    canvas.rect(ml + 42, 570, 42, 60, stroke=1, fill=1)
    canvas.rect(ml + 42 + 42, 570, 425 - 42 - 42, 60, stroke=1, fill=1)

    canvas.line(ml + 42 + 42, 570 + 15, ml + 42 + 42 + 425 - 42 - 42, 570 + 15)
    canvas.line(ml + 42 + 42, 570 + 30, ml + 42 + 42 + 425 - 42 - 42, 570 + 30)
    canvas.line(ml + 42 + 42, 570 + 45, ml + 42 + 42 + 425 - 42 - 42, 570 + 45)

    canvas.line(ml + 42 + 42 + (425 - 42 - 42) / 3, 570,
                ml + 42 + 42 + (425 - 42 - 42) / 3, 570 + 60)
    canvas.line(ml + 42 + 42 + ((425 - 42 - 42) / 3) * 2, 570,
                ml + 42 + 42 + ((425 - 42 - 42) / 3) * 2, 570 + 30)
    canvas.line(ml + 42 + 42 + 425 - 42 - 42 - (425 - 42 - 42) / 6, 570 + 30,
                ml + 42 + 42 + 425 - 42 - 42 - (425 - 42 - 42) / 6, 570 + 60)

    canvas.setFillColor(black)
    canvas.setFont('Times-Roman', 10)
    canvas.drawString(ml + 4, 690 + 4, "Ap. Paterno")
    canvas.drawString(ml + 142 + 4, 690 + 4, "Ap. Materno")
    canvas.drawString(ml + 142 * 2 + 4, 690 + 4, "Nombres")

    canvas.drawString(ml + 4, 645 + 15 + 4, "DOC")
    canvas.drawString(ml + 4, 645 + 4, "Ident.")

    canvas.drawString(ml + 42 + 4, 645 + 15 + 4, "DNI/L.E.")
    canvas.drawString(ml + 142 + 4, 645 + 15 + 4, "Lic.Cond./Cat.")
    canvas.drawString(ml + 142 * 2 + 4, 645 + 15 + 4, "Fecha Nac.")
    canvas.drawString(ml + 142 * 2 + 80 + 4, 645 + 15 + 4, "Est. Civil")
    canvas.drawString(ml + 4, 630 + 4, "E-mail")

    canvas.drawString(ml + 42 * 2 + 4, 570 + 45 + 4, "Av. Calle, Jr. Pje.")
    canvas.drawString(ml + 42 + 42 + (425 - 42 - 42) / 3 + 4,
                      570 + 45 + 4, "Mz. N°, Zona, Int., Of.")
    canvas.drawString(ml + 42 + 42 + 425 - 42 - 42 - (425 - 42 - 42) / 6 + 4, 570 + 45 + 4, "Tf.")

    canvas.drawString(ml + 42 * 2 + 4, 570 + 15 + 4, "Urb.")
    canvas.drawString(ml + 42 + 42 + (425 - 42 - 42) / 3 + 4, 570 + 15 + 4, "Distr.")
    canvas.drawString(ml + 42 + 42 + ((425 - 42 - 42) / 3) * 2 + 4, 570 + 15 + 4, "Provincia")

    canvas.setFont('Times-Bold', 11)
    canvas.drawString(ml, 545, 'II.- DATOS REGISTRALES')

    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(ml, 528,
                      "Si usted cuenta con alguno de los siguientes documentos, complete los siguientes recuadros:")
    canvas.setFont('Helvetica-Oblique', 8)
    canvas.drawString(ml, 515, "Marque con una (X) en el recuadro seleccionado")

    canvas.setFillColor(colors.lightgrey)

    canvas.line(ml + 105 + 52.5, 360, ml + 105 + 52.5, 360 + 150)

    canvas.rect(ml, 480, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 480 + 15, 105 * 2, 15, stroke=1, fill=1)
    canvas.rect(ml, 450, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 450 + 15, 105 * 2, 15, stroke=1, fill=1)
    canvas.rect(ml, 420, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 420 + 15, 105 * 2, 15, stroke=1, fill=1)
    canvas.rect(ml, 390, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 390 + 15, 105 * 2 + 110, 15, stroke=1, fill=1)
    canvas.rect(ml, 360, 105, 30, stroke=1, fill=1)
    canvas.rect(ml + 105, 360 + 15, 105 * 2 + 110, 15, stroke=1, fill=1)

    canvas.line(ml + 105 * 2, 360, ml + 105 * 2, 360 + 150)
    canvas.line(ml + 105 * 3, 360, ml + 105 * 3, 360 + 150)
    canvas.line(ml + 105 * 3 + 110 - 110 / 3, 360, ml + 105 * 3 + 110 - 110 / 3, 360 + 60)
    canvas.line(ml + 105 * 3 + 110, 360, ml + 105 * 3 + 110, 360 + 60)

    canvas.line(ml + 105, 360, ml + 105 * 3 + 110, 360)

    canvas.setFillColor(black)

    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(ml + 0 + 4, 480 + 7.5 + 4, "SETARE")
    canvas.drawString(ml + 0 + 4, 450 + 15 + 4, "PERMISO")
    canvas.drawString(ml + 0 + 4, 450 + 0 + 4, "PROVISIONAL")
    canvas.drawString(ml + 0 + 4, 420 + 0 + 4, "AFOCAT")
    canvas.drawString(ml + 0 + 4, 390 + 0 + 4, "SOAT")
    canvas.drawString(ml + 0 + 4, 360 + 0 + 4, "REVISION TECNICA")

    canvas.setFont('Helvetica', 8)
    canvas.drawString(ml + 105 * 1 + 30 + 4, 480 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 480 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 480 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 480 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 480 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 480 + 0 + 4, "/")

    canvas.drawString(ml + 105 * 1 + 30 + 4, 450 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 450 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 450 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 450 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 450 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 450 + 0 + 4, "/")

    canvas.drawString(ml + 105 * 1 + 30 + 4, 420 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 420 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 420 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 420 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 420 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 420 + 0 + 4, "/")

    canvas.drawString(ml + 105 * 1 + 30 + 4, 390 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 390 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 3 + 4, 390 + 15 + 4, "PARTICULAR")
    canvas.drawString(ml + 105 * 3 + 80 + 4, 390 + 15 + 4, "TAXI")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 390 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 390 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 390 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 390 + 0 + 4, "/")

    canvas.drawString(ml + 105 * 1 + 30 + 4, 360 + 15 + 4, "VIGENTE")
    canvas.drawString(ml + 105 * 2 + 4, 360 + 15 + 4, "FECHA DE VENCIMIENTO")
    canvas.drawString(ml + 105 * 3 + 4, 360 + 15 + 4, "PARTICULAR")
    canvas.drawString(ml + 105 * 3 + 80 + 4, 360 + 15 + 4, "TAXI")
    canvas.drawString(ml + 105 * 1 + 20 + 4, 360 + 0 + 4, "SI")
    canvas.drawString(ml + 105 * 1 + 70 + 4, 360 + 0 + 4, "NO")
    canvas.drawString(ml + 105 * 2 + 30 + 4, 360 + 0 + 4, "/")
    canvas.drawString(ml + 105 * 2 + 60 + 4, 360 + 0 + 4, "/")

    canvas.setFont('Times-Bold', 11)
    canvas.drawString(ml, 340, 'III.- DATOS DEL VEHÍCULO')

    canvas.setFillColor(white)
    canvas.rect(ml, 310, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85, 310, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 2, 310, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 3, 310, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 4, 310, 85, 15, stroke=1, fill=1)

    canvas.rect(ml, 310 - 15, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85, 310 - 15, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 2, 310 - 15, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 3, 310 - 15, 85, 15, stroke=1, fill=1)
    canvas.rect(ml + 85 * 4, 310 - 15, 85, 15, stroke=1, fill=1)

    canvas.rect(ml, 310 - 15 * 2, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142, 310 - 15 * 2, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142 * 2, 310 - 15 * 2, 141, 15, stroke=1, fill=1)

    canvas.rect(ml, 310 - 15 * 3, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142, 310 - 15 * 3, 142, 15, stroke=1, fill=1)
    canvas.rect(ml + 142 * 2, 310 - 15 * 3, 141, 15, stroke=1, fill=1)

    canvas.setFillColor(black)
    canvas.drawString(ml + 4, 310 + 0 + 4, "Placa")
    canvas.drawString(ml + 85 + 4, 310 + 0 + 4, "Marca")
    canvas.drawString(ml + 85 * 2 + 4, 310 + 0 + 4, "Modelo")
    canvas.drawString(ml + 85 * 3 + 4, 310 + 0 + 4, "Año")
    canvas.drawString(ml + 85 * 4 + 4, 310 + 0 + 4, "Color")

    canvas.drawString(ml + 142 * 0 + 4, 310 - 15 * 2 + 0 + 4, "N° Serie")
    canvas.drawString(ml + 142 * 1 + 4, 310 - 15 * 2 + 0 + 4, "Motor")
    canvas.setFont('Times-Roman', 8)
    canvas.drawString(ml + 142 * 2 + 4, 310 - 15 * 2 + 0 + 4, "CARACTERISTICAS ESPECIALES")

    canvas.setFont('Times-Bold', 11)
    canvas.drawString(ml, 250, 'IV.- DOCUMENTOS ADJUNTOS')

    canvas.setFillColor(white)
    canvas.rect(ml, 220, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20, 220, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 + 122, 220, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122, 220, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122 * 2, 220, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 3 + 122 * 2, 220, 122, 15, stroke=1, fill=1)

    canvas.rect(ml, 220 - 15, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20, 220 - 15, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 + 122, 220 - 15, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122, 220 - 15, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122 * 2, 220 - 15, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 3 + 122 * 2, 220 - 15, 122, 15, stroke=1, fill=1)

    canvas.rect(ml, 220 - 15 * 2, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20, 220 - 15 * 2, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 + 122, 220 - 15 * 2, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122, 220 - 15 * 2, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122 * 2, 220 - 15 * 2, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 3 + 122 * 2, 220 - 15 * 2, 122, 15, stroke=1, fill=1)

    canvas.rect(ml, 220 - 15 * 3, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20, 220 - 15 * 3, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 + 122, 220 - 15 * 3, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122, 220 - 15 * 3, 122, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 2 + 122 * 2, 220 - 15 * 3, 20, 15, stroke=1, fill=1)
    canvas.rect(ml + 20 * 3 + 122 * 2, 220 - 15 * 3, 122, 15, stroke=1, fill=1)

    canvas.setFillColor(black)
    canvas.setFont('Times-Roman', 9)
    canvas.drawString(ml + 20 + 4, 220 - 15 * 0 + 4, "Fotocopia DNI (Propietario).")
    canvas.drawString(ml + 20 * 2 + 122 + 4, 220 - 15 * 0 + 4, "Fotocopia AFOCAT.")
    canvas.drawString(ml + 20 * 3 + 122 * 2 + 4, 220 - 15 * 0 + 4, "Copia recibo agua.")

    canvas.drawString(ml + 20 + 4, 220 - 15 * 1 + 4, "Fotocopia DNI (Cónyuge).")
    canvas.drawString(ml + 20 * 2 + 122 + 4, 220 - 15 * 1 + 4, "Fotocopia R. TECNICA.")
    canvas.drawString(ml + 20 * 3 + 122 * 2 + 4, 220 - 15 * 1 + 4, "Copia recibo luz.")

    canvas.drawString(ml + 20 + 4, 220 - 15 * 2 + 4, "Fotocopia Tarjeta Propiedad.")
    canvas.drawString(ml + 20 * 2 + 122 + 4, 220 - 15 * 2 + 4, "Fotocopia SETARE.")
    canvas.drawString(ml + 20 * 3 + 122 * 2 + 4, 220 - 15 * 2 + 4, "Copia recibo teléfono o cable.")

    canvas.drawString(ml + 20 + 4, 220 - 15 * 3 + 4, "Fotocopia SOAT.")
    canvas.drawString(ml + 20 * 2 + 122 + 4, 220 - 15 * 3 + 4, "Fotocopia P. PROVISIONAL.")
    canvas.drawString(ml + 20 * 3 + 122 * 2 + 4, 220 - 15 * 3 + 4, "Croquis de Ubicación.")

    canvas.setFont('Times-BoldItalic', 12)
    canvas.drawString(
        ml, 160, '• Declaro bajo juramento no tener ni registrar antecedentes policiales, ni judiciales.')
    canvas.drawString(
        ml, 145, '• Cumplir con las obligaciones y reglamento interno de la empresa, caso contrario ')
    canvas.drawString(
        ml + 8, 130, 'acepto a que se me imponga las condiciones y sanciones contempladas.')

    canvas.setDash(1, 1)
    canvas.line(ml + 20, 80, ml + 20 + 122, 80)
    canvas.line(ml + 20 * 2 + 122, 80, ml + 20 * 2 + 122 * 2, 80)
    canvas.line(ml + 20 * 3 + 122 * 2, 80, ml + 20 * 3 + 122 * 3, 80)

    canvas.setDash(2, 2)
    canvas.line(ml + 20 + 21, 55, ml + 20 + 21 + 80, 55)
    canvas.line(ml + 20 + 21 * 4 + 80, 55, ml + 20 + 21 * 4 + 80 * 2, 55)
    # canvas.line(ml + 20 + 21*7 + 80*2, 55, ml + 20 + 21*7 + 80*3, 55)

    canvas.setFillColor(black)
    canvas.setFont('Times-Bold', 9)
    canvas.drawString(ml + 20, 55, 'DNI')
    canvas.drawString(ml + 20 + 21 * 4 + 80 - 21, 55, 'DNI')
    canvas.drawString(ml + 20 + 21 * 7 + 80 * 2 - 21, 55, 'TAXI TURISMO AREQUIPA')
    canvas.setFont('Times-Roman', 11)

    canvas.drawString(ml + 20 + 21 * 2, 70, 'Propietario')
    canvas.drawString(ml + 20 + 21 * 5 + 80, 70, 'Cónyuge')
    canvas.drawString(ml + 20 + 21 * 8 + 80 * 2, 70, 'VºBº')

    canvas.rotate(90)
    # canvas.rect(ml, 570, 42, 60, stroke=1, fill=1)
    canvas.setFont('Times-Roman', 8)
    canvas.drawString(570 + 4, -ml - 20 - 4, "DOMICILIO")
    canvas.setFont('Times-Roman', 12)
    canvas.drawString(580 + 4, -ml - 20 * 3 - 7, "REAL")

    canvas.showPage()
    canvas.save()
    response.write(buffer.getvalue())
    buffer.close()
    return response


def print_programming_guide(request, pk=None):
    # A5

    ml = 1 * cm
    mr = 1 * cm
    ms = 1 * cm
    mi = 1 * cm

    programming_obj = Programming.objects.get(id=pk)
    guide_obj = Guide.objects.filter(programming=programming_obj).first()

    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    # pdfmetrics.registerFont(TTFont('Square', 'square.ttf'))
    pdfmetrics.registerFont(TTFont('Capricus', 'capricus.ttf'))
    pdfmetrics.registerFont(TTFont('Fontanero', 'fontanero.bevel.ttf'))
    pdfmetrics.registerFont(TTFont('DayPoster', 'day-poster-nf.postershadownf.ttf'))

    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=landscape(A5), )
    canvas.setTitle("Guia de remision [{}-{}]".format(guide_obj.serial, guide_obj.code))

    # A4 72 PPI (595 X 842)
    # A5 72 PPI (420 x 595)
    # fixed
    mi = mi + 12 * 4

    canvas.setLineWidth(.3)

    canvas.setFont('DayPoster', 26)
    canvas.drawString(ml + 15, mi + 350 - 35, 'DISTRIBUIDORA D&F MARIN')

    canvas.setFont('Courier-Bold', 12)
    canvas.drawString(ml + 70, mi + 350 - 50, 'SOCIEDAD ANÓNIMA CERRADA')
    canvas.setFont('Helvetica', 9)
    canvas.drawString(ml + 80, mi + 350 - 65, 'Direc. Car. Panamericana Sur, Km 1113')
    canvas.setFont('Helvetica-Bold', 6)
    canvas.drawString(ml + 110, mi + 350 - 75, 'SICUANI - CANCHIS CUSCO')
    canvas.setFont('Times-Roman', 10)
    canvas.drawString(ml + 55, mi + 350 - 90, 'Asoc. Granjeros Forestales el P. Mzna. D - Lote 8-9')
    canvas.setFont('Times-Bold', 9)
    canvas.drawString(ml + 90, mi + 350 - 105, 'YURA - AREQUIPA - AREQUIPA')

    logo = "apps/dishes/static/assets/avatar/logo_marin.PNG"
    glp = "apps/dishes/static/assets/avatar/logo_marin.PNG"

    canvas.drawImage(logo, ml, mi + 350 - 105, mask='auto', width=96 / 2, height=102 / 2)
    canvas.drawImage(glp, ml + 260, mi + 350 - 110, mask='auto', width=150 / 2.2, height=150 / 2.2)
    # Dates
    canvas.setFillColor(white)
    canvas.roundRect(ml, mi + 210, 140, 20, 4, stroke=1, fill=1)
    canvas.roundRect(ml + 170, mi + 210, 140, 20, 4, stroke=1, fill=1)
    # Dates Values
    canvas.setFillColor(black)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(ml + 6, mi + 222, 'Fecha de')
    canvas.drawString(ml + 6, mi + 213, 'Emisión:')
    canvas.drawString(ml + 180, mi + 222, 'Fecha de inicio')
    canvas.drawString(ml + 180, mi + 213, 'de Traslado:')

    departure_date = '-'
    arrival_date = '-'
    if programming_obj.departure_date:
        departure_date = str(programming_obj.departure_date)
    if programming_obj.arrival_date:
        arrival_date = str(programming_obj.arrival_date)
    canvas.drawString(ml + 6 + 70, mi + 222 - 5, departure_date)
    canvas.drawString(ml + 180 + 70, mi + 222 - 5, arrival_date)

    # RUC
    canvas.setFillColor(white)
    canvas.roundRect(ml + 330, mi + 210, 200 + 6, 118 + 6, 4, stroke=1, fill=1)
    canvas.roundRect(ml + 333, mi + 213, 200, 118, 4, stroke=1, fill=1)
    canvas.setFillColor(black)
    canvas.line(ml + 333, mi + 253, ml + 333 + 200, mi + 253)
    canvas.line(ml + 333, mi + 293, ml + 333 + 200, mi + 293)
    # RUC Values
    canvas.setFont('Helvetica-Bold', 20)
    canvas.drawString(ml + 333 + 10, mi + 293 + 10, 'RUC: 20450509125')
    canvas.setFont('Helvetica-Bold', 18)
    canvas.drawString(ml + 333 + 15, mi + 253 + 22, 'GUIA DE REMISION')
    canvas.drawString(ml + 333 + 48, mi + 253 + 5, 'REMITENTE')
    canvas.setFont('Helvetica', 18)
    canvas.drawString(ml + 333 + 30, mi + 210 + 15,
                      '{} - Nº {}'.format(guide_obj.serial, guide_obj.code))
    # Origin - Destiny
    canvas.setFillColor(white)
    canvas.roundRect(ml, mi + 175, 536, 30, 4, stroke=1, fill=1)
    canvas.setFillColor(black)
    canvas.line(ml + 268, mi + 175, ml + 268, mi + 175 + 30)  # vertical
    # canvas.setFillGray(0.50)
    # canvas.setFillColor(red)
    canvas.setStrokeColorRGB(0.5, 0.5, 0.5, alpha=0.3)  # Color de trazo
    # canvas.setFillColor(HexColor('#9199a1'))
    canvas.line(ml + 3, mi + 175 + 3, ml + 268 - 2, mi + 175 + 3)
    canvas.line(ml + 3 + 80, mi + 190 + 0, ml + 268 - 2, mi + 190 + 0)
    canvas.line(ml + 268 + 2, mi + 175 + 3, ml + 536 - 2, mi + 175 + 3)
    canvas.line(ml + 268 + 2 + 80, mi + 190 + 0, ml + 536 - 2, mi + 190 + 0)
    # Origin - Destiny Values
    canvas.setFont('Helvetica', 8)
    canvas.drawString(ml + 3 + 3, mi + 190 + 3, 'Punto de Partida:')
    canvas.drawString(ml + 268 + 2 + 3, mi + 190 + 3, 'Punto de Llegada:')

    canvas.drawString(ml + 3 + 3 + 100, mi + 190 + 3, programming_obj.get_origin().name)
    canvas.drawString(ml + 268 + 2 + 3 + 100, mi + 190 + 3, programming_obj.get_destiny().name)

    # Traslado
    canvas.setFillColor(white)
    canvas.setStrokeColorRGB(0, 0, 0, alpha=1)
    canvas.roundRect(ml, mi + 130, 536, 36, 4, stroke=1, fill=1)
    canvas.line(ml + 268, mi + 130, ml + 268, mi + 130 + 36)  # vertical

    canvas.line(ml, mi + 130 + 18, ml + 268, mi + 130 + 18)
    canvas.line(ml + 268, mi + 130 + 12, ml + 536, mi + 130 + 12)
    canvas.line(ml + 268, mi + 130 + 24, ml + 536, mi + 130 + 24)
    canvas.setFillColor(black)
    canvas.drawString(ml + 6, mi + 130 + 18 + 6, 'Fecha de Inicio de Traslado:')
    canvas.drawString(ml + 6 + 120, mi + 130 + 18 + 6, arrival_date)
    canvas.drawString(ml + 6, mi + 130 + 6, 'Costo minimo S/')
    minimal_cost = '-'
    if guide_obj.minimal_cost:
        minimal_cost = str(guide_obj.minimal_cost)
    canvas.drawString(ml + 6 + 120, mi + 130 + 6, minimal_cost)
    canvas.drawString(ml + 268 + 6 + 20, mi + 130 + 24 + 3,
                      'NOMBRE O RAZON SOCIAL DEL DESTINATARIO')
    canvas.drawString(ml + 268 + 6, mi + 130 + 3, 'Número de RUC:')
    # Vehicle & pilot
    canvas.setFillColor(white)
    canvas.roundRect(ml, mi + 77, 536, 48, 4, stroke=1, fill=1)
    canvas.line(ml + 268, mi + 77, ml + 268, mi + 77 + 48)  # vertical
    canvas.line(ml + 130, mi + 77, ml + 130, mi + 77 + 36)  # vertical
    canvas.line(ml + 268 + 100, mi + 77, ml + 268 + 100, mi + 77 + 36)  # vertical

    canvas.line(ml, mi + 77 + 12, ml + 268, mi + 77 + 12)
    canvas.line(ml, mi + 77 + 24, ml + 268, mi + 77 + 24)
    canvas.line(ml, mi + 77 + 36, ml + 268, mi + 77 + 36)

    canvas.line(ml + 268, mi + 77 + 18, ml + 536, mi + 77 + 18)
    canvas.line(ml + 268, mi + 77 + 36, ml + 536, mi + 77 + 36)
    canvas.setFillColor(black)
    canvas.drawString(ml + 6 + 40, mi + 77 + 36 + 3, 'UNIDAD DE TRANSPORTE Y CONDUCTOR')
    canvas.drawString(ml + 6, mi + 77 + 24 + 3, 'Marca y Número de Placa:')
    canvas.drawString(ml + 6 + 150, mi + 77 + 24 + 3, programming_obj.truck.license_plate)
    canvas.drawString(ml + 6, mi + 77 + 12 + 3, 'Nº de Constancia de Inscripción:')
    canvas.drawString(ml + 6, mi + 77 + 3, 'Nº(s) de Licencia(s) de Conducir:')
    canvas.drawString(ml + 268 + 6 + 80, mi + 77 + 36 + 3, 'EMPRESA DE TRANSPORTES')
    canvas.drawString(ml + 268 + 6, mi + 77 + 18 + 3, 'Nombre o Razón Social:')
    canvas.drawString(ml + 268 + 6, mi + 77 + 3, 'Número de RUC:')

    canvas.drawString(ml, mi + 65 + 3, 'Tipo y Número del Comprobante de Pago:')

    # details
    canvas.setFillColor(white)
    canvas.roundRect(ml, mi + 0 - 12, 536, 77, 4, stroke=1, fill=1)

    canvas.line(ml, mi + 0 + 0, ml + 536, mi + 0 + 0)  # fixed
    canvas.line(ml, mi + 0 + 12, ml + 536, mi + 0 + 12)
    canvas.line(ml, mi + 0 + 24, ml + 536, mi + 0 + 24)
    canvas.line(ml, mi + 0 + 36, ml + 536, mi + 0 + 36)
    canvas.line(ml, mi + 0 + 48, ml + 536, mi + 0 + 48)
    canvas.line(ml + 50, mi + 0, ml + 50, mi + 0 + 65)  # vertical
    canvas.line(ml + 50 + 280, mi + 0, ml + 50 + 280, mi + 0 + 65)  # vertical
    canvas.line(ml + 50 + 280 + 70, mi + 0, ml + 50 + 280 + 70, mi + 0 + 65)  # vertical
    canvas.line(ml + 50 + 280 + 70 + 70, mi + 0, ml + 50 + 280 + 70 + 70, mi + 0 + 65)  # vertical

    canvas.roundRect(ml, mi + 0 - 60, 100, 45, 4, stroke=1, fill=1)
    canvas.roundRect(ml + 100 + 3, mi + 0 - 60, 433, 45, 4, stroke=1, fill=1)

    canvas.setFillColor(black)
    canvas.drawString(ml + 6 + 15, mi + 0 + 48 + 6, 'ITEM')
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 + 48 + 6, 'DESCRIPCION')
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 + 48 + 6, 'CANTIDAD')
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 + 48 + 6, 'UNID. MEDIDA')
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 + 48 + 6, 'PESO TOTAL')
    item1 = ''
    description1 = ''
    quantity1 = ''
    unit_measure1 = ''
    weight1 = ''
    if guide_obj.guidedetail_set.count() > 0:
        item1 = str(guide_obj.guidedetail_set.all()[0].id)
        description1 = str(guide_obj.guidedetail_set.all()[0].product.name)
        quantity1 = str(guide_obj.guidedetail_set.all()[0].quantity)
        unit_measure1 = str(guide_obj.guidedetail_set.all()[0].unit_measure.description)
        weight1 = str(guide_obj.guidedetail_set.all()[0].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 + 36 + 3, item1)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 + 36 + 3, description1)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 + 36 + 3, quantity1)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 + 36 + 3, unit_measure1)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 + 36 + 3, weight1)

    item2 = ''
    description2 = ''
    quantity2 = ''
    unit_measure2 = ''
    weight2 = ''
    if guide_obj.guidedetail_set.count() > 1:
        item2 = str(guide_obj.guidedetail_set.all()[1].id)
        description2 = str(guide_obj.guidedetail_set.all()[1].product.name)
        quantity2 = str(guide_obj.guidedetail_set.all()[1].quantity)
        unit_measure2 = str(guide_obj.guidedetail_set.all()[1].unit_measure.description)
        weight2 = str(guide_obj.guidedetail_set.all()[1].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 + 24 + 3, item2)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 + 24 + 3, description2)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 + 24 + 3, quantity2)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 + 24 + 3, unit_measure2)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 + 24 + 3, weight2)

    item3 = ''
    description3 = ''
    quantity3 = ''
    unit_measure3 = ''
    weight3 = ''
    if guide_obj.guidedetail_set.count() > 2:
        item3 = str(guide_obj.guidedetail_set.all()[2].id)
        description3 = str(guide_obj.guidedetail_set.all()[2].product.name)
        quantity3 = str(guide_obj.guidedetail_set.all()[2].quantity)
        unit_measure3 = str(guide_obj.guidedetail_set.all()[2].unit_measure.description)
        weight3 = str(guide_obj.guidedetail_set.all()[2].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 + 12 + 3, item3)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 + 12 + 3, description3)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 + 12 + 3, quantity3)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 + 12 + 3, unit_measure3)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 + 12 + 3, weight3)

    item4 = ''
    description4 = ''
    quantity4 = ''
    unit_measure4 = ''
    weight4 = ''
    if guide_obj.guidedetail_set.count() > 3:
        item4 = str(guide_obj.guidedetail_set.all()[3].id)
        description4 = str(guide_obj.guidedetail_set.all()[3].product.name)
        quantity4 = str(guide_obj.guidedetail_set.all()[3].quantity)
        unit_measure4 = str(guide_obj.guidedetail_set.all()[3].unit_measure.description)
        weight4 = str(guide_obj.guidedetail_set.all()[3].weight)

    canvas.drawString(ml + 6 + 15, mi + 0 + 0 + 3, item4)
    canvas.drawString(ml + 6 + 100 + 50, mi + 0 + 0 + 3, description4)
    canvas.drawString(ml + 6 + 0 + 50 + 280, mi + 0 + 0 + 3, quantity4)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70, mi + 0 + 0 + 3, unit_measure4)
    canvas.drawString(ml + 6 + 0 + 50 + 280 + 70 + 70, mi + 0 + 0 + 3, weight4)

    canvas.drawString(ml + 100 + 3 + 6, mi + 0 - 60 + 6 + 20, 'MOTIVO DEL')
    canvas.drawString(ml + 100 + 3 + 6, mi + 0 - 60 + 6 + 10, 'TRASLADO')

    canvas.drawString(ml + 100 + 3 + 6 + 60, mi + 0 - 60 + 6 + 28, 'Venta')
    canvas.drawString(ml + 100 + 3 + 6 + 60, mi + 0 - 60 + 6 + 13, 'Venta sujeta a')
    canvas.drawString(ml + 100 + 3 + 6 + 60, mi + 0 - 60 + 6 - 2, 'Compra')
    canvas.acroForm.checkbox(
        name='CB0',
        checked=False,
        x=ml + 100 + 3 + 6 + 120, y=mi + 0 - 60 + 6 + 25,
        size=10,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.acroForm.checkbox(
        name='CB02',
        checked=False,
        x=ml + 100 + 3 + 6 + 120, y=mi + 0 - 60 + 6 + 10,
        size=10,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.acroForm.checkbox(
        name='CB03',
        checked=False,
        x=ml + 100 + 3 + 6 + 120, y=mi + 0 - 60 + 6 - 5,
        size=10,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)

    canvas.drawString(ml + 100 + 3 + 6 + 140, mi + 0 - 60 + 6 + 28, 'Consignación')
    canvas.drawString(ml + 100 + 3 + 6 + 140, mi + 0 - 60 + 6 + 13, 'Devolución')
    canvas.drawString(ml + 100 + 3 + 6 + 140, mi + 0 - 60 + 6 - 2, 'Entre establecimientos')
    canvas.acroForm.checkbox(
        name='CB04',
        checked=False,
        x=ml + 100 + 3 + 6 + 230, y=mi + 0 - 60 + 6 + 25,
        size=10,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.acroForm.checkbox(
        name='CB05',
        checked=False,
        x=ml + 100 + 3 + 6 + 230, y=mi + 0 - 60 + 6 + 10,
        size=10,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.acroForm.checkbox(
        name='CB06',
        checked=False,
        x=ml + 100 + 3 + 6 + 230, y=mi + 0 - 60 + 6 - 5,
        size=10,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.drawString(ml + 100 + 3 + 6 + 250, mi + 0 - 60 + 6 + 28, 'Para transformación')
    canvas.acroForm.checkbox(
        name='CB07',
        checked=False,
        x=ml + 100 + 3 + 6 + 330, y=mi + 0 - 60 + 6 + 25,
        size=10,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.drawString(ml + 100 + 3 + 6 + 350, mi + 0 - 60 + 6 + 28, 'Zona primaria')
    canvas.acroForm.checkbox(
        name='CB8',
        checked=False,
        x=ml + 100 + 3 + 6 + 410, y=mi + 0 - 60 + 6 + 25,
        size=10,
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=False)
    canvas.showPage()
    canvas.save()
    r = HttpResponse(content_type='application/pdf')
    r['Content-Disposition'] = 'attachment; filename="owners_and_vehicles_update.pdf"'
    r['Content-Disposition'] = 'attachment; filename="guia_de_remision[{} - {}].pdf"'.format(
        guide_obj.serial, guide_obj.code)
    r.write(buffer.getvalue())
    buffer.close()
    return r


def get_input_note(self, pk=None):
    # Register Fonts
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _wt = 8.5 * inch - 14 * inch

    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    pdfmetrics.registerFont(TTFont('Square', 'sqr721bc.ttf'))
    pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))

    details = []
    colspan_headings = ('ARTÍCULOS', '', '', '', '', 'VALORES', '')
    headings = ('Id', 'Codigo', 'Descrición', 'Cant.', 'U. Med.', 'Unitario', 'Total')
    my_style_table_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),  # second column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'),  # third column
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),  # four column
        ('RIGHTPADDING', (3, 0), (3, -1), 0.5),  # four column
    ]
    _rows = []
    sub_total = 0
    total = 0
    igv_total = 0
    for g in GuideDetail.objects.filter(guide__id=pk):
        # P0 = Paragraph(g.id, style["Justify"])
        _product = Paragraph(str(g.product.name), styles["Justify_Square"])
        _rows.append((' ', str(g.product.id), _product, str(g.quantity),
                      str(g.unit_measure.name), str(g.product.calculate_minimum_unit()),
                      str(g.product.calculate_minimum_unit())))
        base_total = decimal.Decimal(g.product.calculate_minimum_unit() * g.quantity)
        total = total + base_total
    ana_c_detail = Table(_rows,
                         colWidths=[_wt * 5 / 100, _wt * 5 / 100, _wt * 50 / 100, _wt * 10 / 100, _wt * 10 / 100, _wt * 10 / 100, _wt * 10 / 100])
    ana_c_detail.setStyle(TableStyle(my_style_table_detail))

    all_details = [(g.id, g.product.id, Paragraph(str(g.product.name + ' - ' + g.product.product_brand.name), styles["Justify_Square"]), g.quantity, g.unit_measure.name,
                    g.product.calculate_minimum_unit(), g.product.calculate_minimum_unit() * g.quantity)
                   for g in GuideDetail.objects.filter(guide__id=pk)]
    guide_obj = Guide.objects.get(id=pk)

    footer1 = ('NOTA:', '', 'INGRESO DE BIENES', '', '', '', '')
    footer2 = ('SON:', '', numero_a_moneda(guide_obj.minimal_cost),
               '', '', 'TOTAL S/', str(guide_obj.minimal_cost))
    # t = Table([colspan_headings] + [headings] + all_details + [footer1] + [footer2])
    t = Table([colspan_headings] + [headings] + all_details + [footer1] + [footer2],
              colWidths=[0.5 * inch, 0.7 * inch, 2.5 * inch, 0.5 * inch, 0.7 * inch, 0.7 * inch, 0.7 * inch])

    t.setStyle(TableStyle(
        [
            ('SPAN', (0, 0), (4, 0)),
            ('SPAN', (5, 0), (6, 0)),
            ('ALIGN', (0, 0), (4, 0), 'CENTER'),
            ('ALIGN', (5, 0), (6, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Newgot'),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            # ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
            # ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, -2), (1, -2), 'Helvetica-Bold'),
            ('FONTNAME', (5, -1), (6, -1), 'Helvetica-Oblique'),
            ('ALIGN', (5, -1), (6, -1), 'RIGHT'),
            ('FONTSIZE', (0, -1), (6, -1), 8),
            ('FONTSIZE', (0, -2), (6, -2), 8),
            ('SPAN', (0, -1), (1, -1)),
            ('SPAN', (2, -1), (4, -1)),
            ('SPAN', (0, -2), (1, -2)),
            ('SPAN', (2, -2), (6, -2)),
            ('FONTNAME', (3, 2), (3, -1), 'Helvetica-Oblique'),
            ('FONTNAME', (5, 2), (5, -1), 'Helvetica-Oblique'),
            ('FONTNAME', (6, 2), (6, -1), 'Helvetica-Oblique'),
            ('ALIGN', (3, 2), (3, -1), 'RIGHT'),
            ('ALIGN', (5, 2), (5, -1), 'RIGHT'),
            ('ALIGN', (6, 2), (6, -1), 'RIGHT'),
        ]
    ))

    buff = io.BytesIO()

    ml = 3.0 * cm
    mr = 3.0 * cm
    ms = 3.75 * cm
    mi = 2.5 * cm

    doc = SimpleDocTemplate(buff,
                            pagesize=A4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title="Reporte Nota de Entrada - [{}-{}]".format(
                                guide_obj.get_serial(), guide_obj.code),
                            )

    # styles = getSampleStyleSheet()
    # styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY,
    #                           leading=13, fontName='Newgot', fontSize=12))
    # styles.add(ParagraphStyle(name='header2', alignment=TA_CENTER,
    #                           leading=13, fontName='Helvetica', fontSize=8))
    # styles.add(ParagraphStyle(name='header1', alignment=TA_CENTER,
    #                           leading=13, fontName='Helvetica-Bold', fontSize=12))

    header1 = Paragraph("ROLDEM PERU S.A.C.", styles['header2'])
    header2 = Paragraph("NOTA DE ENTRADA AL ALMACÉN", styles['header1'])

    Story = []

    Story.append(header1)
    Story.append(Spacer(1, 10))
    Story.append(header2)
    Story.append(Spacer(1, 1))
    Story.append(InputGetContext(pk=pk))
    Story.append(Spacer(1, 1))
    Story.append(t)

    r = HttpResponse(content_type='application/pdf')
    r['Content-Disposition'] = 'attachment; filename="nota_de_entrada_[{} - {}].pdf"'.format(
        guide_obj.get_serial(), guide_obj.code)

    doc.build(Story)
    r.write(buff.getvalue())
    buff.close()
    return r


class InputGetContext(Flowable):
    def __init__(self, width=200, height=80, pk=None):
        self.width = width
        self.height = height
        self.pk = pk

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        guide_obj = Guide.objects.get(id=self.pk)
        canvas = self.canv  # El atributo que permite dibujar en canvas
        canvas.saveState()
        canvas.setLineWidth(1)
        # canvas.rect(0, 8, self.width, self.height, fill=0)
        canvas.setFillColor(white)
        canvas.rect(-12 + 347, 90, 90, 30, fill=1)
        canvas.line(-12 + 347, 90 + 15, -12 + 347 + 90, 90 + 15)
        canvas.line(-12 + 347 + 30, 90, -12 + 347 + 30, 90 + 30)  # vertical
        canvas.line(-12 + 347 + 60, 90, -12 + 347 + 60, 90 + 30)  # vertical
        canvas.roundRect(-12, 5, 437, 65, 4, stroke=1, fill=1)
        # canvas.roundRect(-10, 5, 430, 43, 4, stroke=1, fill=1)
        canvas.setFillColor(black)
        # canvas.setFont('Helvetica', 8)
        canvas.setFont('Helvetica-Bold', 8)
        destiny = guide_obj.route_set.get(type='D')
        # canvas.drawString(-12 + 15, 5 + 45, 'PROCEDENCIA: ' + guide_obj.get_origin().name + ' - VENTAS')
        # canvas.drawString(-12 + 15, 5 + 30, 'DESTINO: ' + destiny.subsidiary_store.name.upper())
        canvas.drawString(-12 + 15, 5 + 30, 'DESTINO: ' + guide_obj.get_destiny().name + ' - VENTAS')
        canvas.drawString(-12 + 15, 5 + 15, 'SEGÚN: ' + guide_obj.document_number.upper() + ' MOTIVO: ' + guide_obj.guide_motive.description.upper())
        canvas.drawString(-12 + 347, 90 + 30 + 2, 'Nro ' + str(guide_obj.id))

        canvas.drawString(-12 + 347 + 5, 90 + 15 + 2, 'Día')
        canvas.drawString(-12 + 347 + 30 + 5, 90 + 15 + 2, 'Mes')
        canvas.drawString(-12 + 347 + 60 + 5, 90 + 15 + 2, 'Año')

        canvas.drawString(-12 + 347 + 10, 90 + 5, str(guide_obj.created_at.day))
        canvas.drawString(-12 + 347 + 40, 90 + 5, str(guide_obj.created_at.month))
        canvas.drawString(-12 + 347 + 65, 90 + 5, str(guide_obj.created_at.year))

        canvas.restoreState()


def get_output_note(self, pk=None):
    # Register Fonts
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    pdfmetrics.registerFont(TTFont('Square', 'sqr721bc.ttf'))
    pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))

    details = []
    colspan_headings = ('ARTÍCULOS', '', '', '', '', 'VALORES', '')
    headings = ('Id', 'Codigo', 'Descrición', 'Cant.', 'U. Med.', 'Unitario', 'Total')

    all_details = [(g.id, g.product.id, Paragraph(str(g.product.name), styles["Justify_Square"]), g.quantity, g.unit_measure.name,
                    g.product.calculate_minimum_unit(), g.product.calculate_minimum_unit() * g.quantity)
                   for g in GuideDetail.objects.filter(guide__id=pk)]
    guide_obj = Guide.objects.get(id=pk)

    footer1 = ('NOTA:', '', 'INGRESO DE BIENES', '', '', '', '')
    footer2 = (
        'SON:', '', numero_a_moneda(guide_obj.minimal_cost), '', '', 'TOTAL S/', str(guide_obj.minimal_cost))
    # t = Table([colspan_headings] + [headings] + all_details + [footer1] + [footer2])
    t = Table([colspan_headings] + [headings] + all_details + [footer1] + [footer2],
              colWidths=[0.5 * inch, 0.7 * inch, 2.5 * inch, 0.5 * inch, 0.7 * inch, 0.7 * inch, 0.7 * inch])

    t.setStyle(TableStyle(
        [
            ('SPAN', (0, 0), (4, 0)),
            ('SPAN', (5, 0), (6, 0)),
            ('ALIGN', (0, 0), (4, 0), 'CENTER'),
            ('ALIGN', (5, 0), (6, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Newgot'),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            # ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
            # ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, -2), (1, -2), 'Helvetica-Bold'),
            ('FONTNAME', (5, -1), (6, -1), 'Helvetica-Oblique'),
            ('ALIGN', (5, -1), (6, -1), 'RIGHT'),
            ('FONTSIZE', (0, -1), (6, -1), 8),
            ('FONTSIZE', (0, -2), (6, -2), 8),
            ('SPAN', (0, -1), (1, -1)),
            ('SPAN', (2, -1), (4, -1)),
            ('SPAN', (0, -2), (1, -2)),
            ('SPAN', (2, -2), (6, -2)),
            ('FONTNAME', (3, 2), (3, -1), 'Helvetica-Oblique'),
            ('FONTNAME', (5, 2), (5, -1), 'Helvetica-Oblique'),
            ('FONTNAME', (6, 2), (6, -1), 'Helvetica-Oblique'),
            ('ALIGN', (3, 2), (3, -1), 'RIGHT'),
            ('ALIGN', (5, 2), (5, -1), 'RIGHT'),
            ('ALIGN', (6, 2), (6, -1), 'RIGHT'),
        ]
    ))

    buff = io.BytesIO()

    ml = 3.0 * cm
    mr = 3.0 * cm
    ms = 3.75 * cm
    mi = 2.5 * cm

    doc = SimpleDocTemplate(buff,
                            pagesize=A4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title="Reporte Nota de Salida - [{}-{}]".format(
                                guide_obj.get_serial(), guide_obj.code),
                            )

    # styles = getSampleStyleSheet()
    # styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY,
    #                           leading=13, fontName='Newgot', fontSize=12))
    # styles.add(
    #     ParagraphStyle(name='header2', alignment=TA_CENTER, leading=13, fontName='Helvetica', fontSize=8))
    # styles.add(
    #     ParagraphStyle(name='header1', alignment=TA_CENTER, leading=13, fontName='Helvetica-Bold', fontSize=12))

    header1 = Paragraph("ROLDEM PERU S.A.C.", styles['header2'])
    header2 = Paragraph("NOTA DE SALIDA AL ALMACÉN", styles['header1'])

    Story = []

    Story.append(header1)
    Story.append(Spacer(1, 10))
    Story.append(header2)
    Story.append(Spacer(1, 1))
    Story.append(OutputGetContext(pk=pk))
    Story.append(Spacer(1, 1))
    Story.append(t)

    r = HttpResponse(content_type='application/pdf')
    r['Content-Disposition'] = 'attachment; filename="nota_de_salida_[{} - {}].pdf"'.format(
        guide_obj.get_serial(), guide_obj.code)

    doc.build(Story)
    r.write(buff.getvalue())
    buff.close()
    return r


class OutputGetContext(Flowable):

    def __init__(self, width=200, height=80, pk=None):
        self.width = width
        self.height = height
        self.pk = pk

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        guide_obj = Guide.objects.get(id=self.pk)
        canvas = self.canv  # El atributo que permite dibujar en canvas
        canvas.saveState()
        canvas.setLineWidth(1)
        # canvas.rect(0, 8, self.width, self.height, fill=0)
        canvas.setFillColor(white)
        canvas.rect(-12 + 347, 90, 90, 30, fill=1)
        canvas.line(-12 + 347, 90 + 15, -12 + 347 + 90, 90 + 15)
        canvas.line(-12 + 347 + 30, 90, -12 + 347 + 30, 90 + 30)  # vertical
        canvas.line(-12 + 347 + 60, 90, -12 + 347 + 60, 90 + 30)  # vertical
        canvas.roundRect(-12, 5, 437, 65, 4, stroke=1, fill=1)
        # canvas.roundRect(-10, 5, 430, 43, 4, stroke=1, fill=1)
        canvas.setFillColor(black)
        # canvas.setFont('Helvetica', 8)
        canvas.setFont('Helvetica-Bold', 8)
        origin = guide_obj.route_set.get(type='O')
        subsidiary_destiny = '-'
        subsidiary_store_destiny = '-'
        destiny_set = guide_obj.route_set.filter(type='D')
        if destiny_set.count() > 0:
            subsidiary_destiny = destiny_set.last().subsidiary_store.subsidiary.name.upper()
            subsidiary_store_destiny = destiny_set.last().subsidiary_store.name.upper()

        canvas.drawString(-12 + 15, 5 + 45, 'PROCEDENCIA/SALIDA: ' +
                          origin.subsidiary_store.subsidiary.name.upper() + ' - ' + origin.subsidiary_store.name.upper())
        canvas.drawString(-12 + 15, 5 + 30, 'DESTINO: ' +
                          subsidiary_destiny + ' - ' + subsidiary_store_destiny)
        canvas.drawString(-12 + 15, 5 + 15, 'SEGÚN: ' + guide_obj.document_number.upper() + ' MOTIVO: ' + guide_obj.guide_motive.description.upper())

        canvas.drawString(-12 + 347, 90 + 30 + 2, 'Nro ' + str(guide_obj.id))

        canvas.drawString(-12 + 347 + 5, 90 + 15 + 2, 'Día')
        canvas.drawString(-12 + 347 + 30 + 5, 90 + 15 + 2, 'Mes')
        canvas.drawString(-12 + 347 + 60 + 5, 90 + 15 + 2, 'Año')

        canvas.drawString(-12 + 347 + 10, 90 + 5, str(guide_obj.created_at.day))
        canvas.drawString(-12 + 347 + 40, 90 + 5, str(guide_obj.created_at.month))
        canvas.drawString(-12 + 347 + 65, 90 + 5, str(guide_obj.created_at.year))

        canvas.restoreState()


def NumTomonth(shortMonth):
    return {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre"
    }[shortMonth]


def print_ticket(request, pk=None):
    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    pdfmetrics.registerFont(TTFont('Square', 'sqr721bc.ttf'))
    pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))

    fuel_programming_obj = FuelProgramming.objects.get(id=int(pk))

    tbh_business_name = (fuel_programming_obj.subsidiary.business_name, '')
    tbh_address = (fuel_programming_obj.subsidiary.address, '')
    th = Table([tbh_business_name] + [tbh_address], colWidths=[5.5 * inch, 0.1 * inch])
    th.setStyle(TableStyle(
        [

            ('FONTNAME', (0, 0), (0, -1), 'Square'),
            # ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (0, -1), 'Square'),
            ('FONTSIZE', (0, 0), (0, -1), 12),

            # ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
            # ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
        ]
    ))

    tpl_supplier = ('ABASTECER EN', fuel_programming_obj.supplier.name, '', '')
    tpl_date = ('FECHA', str(fuel_programming_obj.date_fuel.day) + ' ' +
                str(NumTomonth(fuel_programming_obj.date_fuel.month)) + ' ' + str(fuel_programming_obj.date_fuel.year))
    tpl_quantity = ('CANTIDAD', str(fuel_programming_obj.quantity_fuel),
                    str(fuel_programming_obj.unit_fuel.name))
    tpl_license_plate = ('PLACA', str(fuel_programming_obj.programming.truck.license_plate))
    tpl_pilot = ('CONDUCTOR', str(fuel_programming_obj.programming.get_pilot().names) + ' ' + str(
        fuel_programming_obj.programming.get_pilot().paternal_last_name) + ' ' + str(
        fuel_programming_obj.programming.get_pilot().maternal_last_name))
    tpl_route = ('RUTA', str(fuel_programming_obj.programming.get_route()))
    tpl_client = ('PRECIO', 'S/. ' + str(round(fuel_programming_obj.price_fuel, 2)),
                  'IMPORTE', 'S/. ' + str(round(fuel_programming_obj.amount(), 2)))

    t = Table([tpl_supplier] + [tpl_date] + [tpl_quantity] + [tpl_license_plate] + [tpl_pilot] +
              [tpl_route] + [tpl_client], colWidths=[0.65 * inch, 0.7 * inch, 0.8 * inch, 0.9 * inch])

    t.setStyle(TableStyle(
        [
            ('FONTNAME', (2, 2), (3, 2), 'Newgot'),  # galon
            ('FONTNAME', (1, 0), (3, 0), 'Newgot'),  # proveedor
            ('FONTNAME', (1, 5), (3, 5), 'Newgot'),  # ruta
            # ('FONTNAME', (1, 6), (1, 6), 'Square'),  # tpl_client - price
            ('FONTNAME', (2, 6), (2, 6), 'Newgot'),  # tpl_client - import
            ('FONTSIZE', (0, 0), (-1, -1), 7.2),  # tpl_quantity
            ('FONTSIZE', (1, 0), (3, 0), 8),  # proveeodr
            ('FONTSIZE', (1, 5), (3, 5), 8),  # ruta
            ('FONTSIZE', (2, 2), (3, 2), 8),  # galon

            ('SPAN', (1, 0), (3, 0)),
            ('SPAN', (1, 1), (3, 1)),
            ('SPAN', (2, 2), (3, 2)),
            ('SPAN', (1, 3), (3, 3)),
            ('SPAN', (1, 4), (3, 4)),
            ('SPAN', (1, 5), (3, 5)),
            ('FONTNAME', (0, 0), (0, -1), 'Newgot'),
            # ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),#BORDE COLOR
            # ('GRID',(0,0),(-1,-1),1,colors.lightgrey)
            # ('BOX',(0,0),(-1,-1),0.6*mm,(0,0,0))
            # ('LINEBEFORE',(2,1),(2,-2),6,colors.pink)

            # ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
            # ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
        ]
    ))

    buff = io.BytesIO()

    xmax = 595
    ymax = 842

    ml = 0.14 * cm
    mr = 0.05 * cm
    ms = 0.1 * cm
    mi = 0.1 * cm

    doc = SimpleDocTemplate(buff,
                            pagesize=C7,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Combustible'
                            )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY,
                              leading=13, fontName='Newgot', fontSize=12))
    styles.add(
        ParagraphStyle(name='header1', alignment=TA_CENTER, leading=13, fontName='Helvetica-Bold', fontSize=12))

    Story = []

    Story.append(th)
    Story.append(Spacer(1, 60))
    Story.append(t)
    Story.append(OutputGetTicket(fuel_programming_obj=fuel_programming_obj))
    Story.append(Spacer(1, 1))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Combustible_[{}].pdf"'.format(
        fuel_programming_obj.get_correlative())
    doc.build(Story)
    response.write(buff.getvalue())
    buff.close()
    return response


class OutputGetTicket(Flowable):

    def __init__(self, width=200, height=80, fuel_programming_obj=None):
        self.width = width
        self.height = height
        self.fuel_programming_obj = fuel_programming_obj

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        fuel_programming_obj = self.fuel_programming_obj

        canvas = self.canv  # El atributo que permite dibujar en canvas
        canvas.saveState()
        canvas.setLineWidth(1)
        canvas.setFillColor(white)

        trns = Color(0, 0, 200, alpha=0.1)
        canvas.setFillColor(trns)
        canvas.roundRect(120, 240, 80, 18, 3, stroke=1, fill=1)  # rectangulo id
        canvas.line(140, 258, 140, 240)  # vertical

        canvas.roundRect(1, 190, 200, 19, 2, stroke=1, fill=1)  # rectangulo titulo
        canvas.line(42, 209, 42, 190)  # vertical
        canvas.roundRect(1, 80, 200, 107, 2, stroke=1, fill=1)  # rectangulo detalle
        canvas.line(42, 186, 42, 80)  # vertical
        canvas.roundRect(1, 17, 200, 60, 2, stroke=1, fill=1)  # rectangulo firma
        canvas.line(105, 76, 105, 17)

        canvas.setFillColor(black)
        canvas.setFont('Newgot', 9)
        canvas.drawString(126, 246, 'Nº')
        canvas.drawString(150, 246, str(fuel_programming_obj.get_correlative()))

        canvas.drawString(27, 7, 'Firma conductor')
        canvas.drawString(146, 7, 'Firma')
        canvas.setFont('Square', 10)
        canvas.drawString(60, 222, 'VALE DE COMBUSTIBLE')

        canvas.restoreState()
