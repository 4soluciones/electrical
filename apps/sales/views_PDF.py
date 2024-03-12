from reportlab.lib.pagesizes import letter, landscape, A4, A5, C7
from .models import Product, Client, Order, OrderBill, SubsidiaryStore
from .views import get_context_kardex_glp, get_dict_orders
import io
import pdfkit
import decimal
import reportlab
from django.contrib.auth.models import User
from django.http import HttpResponse
from reportlab.lib.colors import black, blue, red, Color
from reportlab.lib.pagesizes import landscape, A5, portrait, letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Spacer, Image, Flowable
from reportlab.platypus import Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode import qr
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.rl_settings import defaultPageSize
from electrical import settings
from .models import Product
from apps.sales.number_to_letters import numero_a_moneda
import io
from django.conf import settings
from .views import calculate_age
import datetime
from datetime import datetime
import requests
from ..hrm.views import get_subsidiary_by_user
from ..hrm.models import Employee, Subsidiary
from ..accounting.models import CashFlow

PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Justify-Dotcirful', alignment=TA_JUSTIFY, leading=12, fontName='Dotcirful-Regular',
                          fontSize=10))
styles.add(ParagraphStyle(name='Center_Newgot_1', alignment=TA_CENTER, leading=11, fontName='Newgot', fontSize=9))
styles.add(ParagraphStyle(name='Left-text', alignment=TA_LEFT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Center-text', alignment=TA_CENTER, leading=8, fontName='Square', fontSize=7))
styles.add(ParagraphStyle(name='Center_Newgot', alignment=TA_CENTER, leading=11, fontName='Newgot', fontSize=11))
styles.add(ParagraphStyle(name='Justify_Square', alignment=TA_JUSTIFY, leading=10, fontName='Square', fontSize=10))
styles.add(
    ParagraphStyle(name='Justify-Dotcirful-table', alignment=TA_JUSTIFY, leading=12, fontName='Dotcirful-Regular',
                   fontSize=7))
styles.add(ParagraphStyle(name='Left_Square', alignment=TA_LEFT, leading=10, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='Right_Newgot', alignment=TA_RIGHT, leading=12, fontName='Newgot', fontSize=12))
styles.add(ParagraphStyle(name='Justify_Bold', alignment=TA_JUSTIFY, leading=8, fontName='Square-Bold', fontSize=8))
styles.add(ParagraphStyle(name='Justify_Newgot', alignment=TA_JUSTIFY, leading=10, fontName='Newgot', fontSize=10))
styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, leading=8, fontName='Square', fontSize=8))
styles.add(
    ParagraphStyle(name='Center-Dotcirful', alignment=TA_CENTER, leading=12, fontName='Dotcirful-Regular', fontSize=10))
styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='CenterTitle', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=8))
styles.add(ParagraphStyle(name='CenterTitle-Dotcirful', alignment=TA_CENTER, leading=12, fontName='Dotcirful-Regular',
                          fontSize=10))
styles.add(ParagraphStyle(name='CenterTitle2', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=12))
styles.add(ParagraphStyle(name='Center_Regular', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=10))
styles.add(ParagraphStyle(name='Center_Bold_title', alignment=TA_CENTER,
                          leading=14, fontName='Square-Bold', fontSize=14, spaceBefore=8, spaceAfter=8))
styles.add(ParagraphStyle(name='Center_Bold', alignment=TA_CENTER,
                          leading=10, fontName='Square-Bold', fontSize=10, spaceBefore=8, spaceAfter=8))
styles.add(ParagraphStyle(name='Center2', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=8))

styles.add(ParagraphStyle(name='Center3', alignment=TA_JUSTIFY, leading=8, fontName='Ticketing', fontSize=7))
styles.add(
    ParagraphStyle(name='Justify_Newgot_title', alignment=TA_JUSTIFY, leading=14, fontName='Newgot', fontSize=14))
styles.add(
    ParagraphStyle(name='Center_Newgot_title', alignment=TA_CENTER, leading=15, fontName='Newgot', fontSize=15))

style = styles["Normal"]

reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
pdfmetrics.registerFont(TTFont('Square', 'square-721-condensed-bt.ttf'))
pdfmetrics.registerFont(TTFont('Square-Bold', 'sqr721bc.ttf'))
pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))
pdfmetrics.registerFont(TTFont('Ticketing', 'ticketing.regular.ttf'))
pdfmetrics.registerFont(TTFont('Lucida-Console', 'lucida-console.ttf'))
pdfmetrics.registerFont(TTFont('Square-Dot', 'square_dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Serif-Dot', 'serif_dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Enhanced-Dot-Digital', 'enhanced-dot-digital-7.regular.ttf'))
pdfmetrics.registerFont(TTFont('Merchant-Copy-Wide', 'MerchantCopyWide.ttf'))
pdfmetrics.registerFont(TTFont('Dot-Digital', 'dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Raleway-Dots-Regular', 'RalewayDotsRegular.ttf'))
pdfmetrics.registerFont(TTFont('Ordre-Depart', 'Ordre-de-Depart.ttf'))
pdfmetrics.registerFont(TTFont('Dotcirful-Regular', 'DotcirfulRegular.otf'))
pdfmetrics.registerFont(TTFont('Nationfd', 'Nationfd.ttf'))
pdfmetrics.registerFont(TTFont('Kg-Primary-Dots', 'KgPrimaryDots-Pl0E.ttf'))
pdfmetrics.registerFont(TTFont('Dot-line', 'Dotline-LA7g.ttf'))
pdfmetrics.registerFont(TTFont('Dot-line-Light', 'DotlineLight-XXeo.ttf'))
pdfmetrics.registerFont(TTFont('Jd-Lcd-Rounded', 'JdLcdRoundedRegular-vXwE.ttf'))

logo = "apps/sales/static/assets/logo png blanco y negro 1.png"


def product_print(self, pk=None):
    response = HttpResponse(content_type='application/pdf')
    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=letter,
                            rightMargin=40,
                            leftMargin=40,
                            topMargin=60,
                            bottomMargin=18,
                            )
    products = []
    styles = getSampleStyleSheet()
    header = Paragraph("Listado de Productos", styles['Heading1'])
    products.append(header)
    headings = ('Id', 'Descrición', 'Codigo')
    if not pk:
        all_products = [(p.id, p.name, p.code.zfill(4))
                        for p in Product.objects.all().order_by('pk')]
    else:
        all_products = [(p.id, p.name, p.code.zfill(4))
                        for p in Product.objects.filter(id=pk)]
    t = Table([headings] + all_products)
    t.setStyle(TableStyle(
        [
            ('GRID', (0, 0), (3, -1), 1, colors.dodgerblue),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.darkblue),
            ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue)
        ]
    ))

    products.append(t)
    doc.build(products)
    response.write(buff.getvalue())
    buff.close()
    return response


def print_ticket_order_passenger(request, pk=None):  # Boleto de viaje boleta / factura
    _wt = 3.14 * inch - 8 * 0.05 * inch

    order_obj = Order.objects.get(pk=pk)
    order_bill_obj = order_obj.orderbill
    passenger_name = ""
    passenger_document = ""
    client_document = ""
    client_name = ""
    client_address = ""

    tbh_business_name_address = 'CAR.VIA EVITAMIENTO 608 MZA. 21\nLOTE. 5 C.P. SEMI RURAL PACHACUTEC ZONA H (SECCION 5)\n RUC: 20603890214'

    date = order_obj.programming_seat.programming.departure_date
    _format_time = order_obj.programming_seat.programming.get_turn_display()
    _format_date = date.strftime("%d/%m/%Y")

    if order_bill_obj.type == '1':
        tbn_document = 'FACTURA ELECTRÓNICA'
        passenger_set = order_obj.client
        company_set = order_obj.orderaction_set.filter(type='E')
        if passenger_set:
            passenger_name = passenger_set.names
            passenger_document = passenger_set.clienttype_set.first().document_number
        if company_set:
            client_document = company_set.first().client.clienttype_set.first().document_number
            client_name = company_set.first().client.names
            client_address = company_set.first().client.clientaddress_set.first().address
    elif order_bill_obj.type == '2':
        tbn_document = 'BOLETA DE VENTA ELECTRÓNICA'
        passenger_name = order_obj.client.names
        passenger_document = order_obj.client.clienttype_set.first().document_number
        client_name = passenger_name
        client_document = passenger_document
    line = '-------------------------------------------------------'

    I = Image(logo)
    I.drawHeight = 3.95 * inch / 2.9
    I.drawWidth = 4.4 * inch / 2.9

    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
    ]
    colwiths_table = [_wt * 30 / 100, _wt * 70 / 100]

    if order_bill_obj.type == '2':
        p0 = Paragraph(client_name, styles["Right"])
        ana_c1 = Table(
            [('CLIENTE: N DOC ', client_document)] +
            [('SR(A): ', p0)] +
            [('ATENDIDO POR: ', order_obj.user.username.upper() + " " + order_obj.subsidiary.name)],
            colWidths=colwiths_table)
    elif order_bill_obj.type == '1':
        p0 = Paragraph(client_name, styles["Justify"])
        p1 = Paragraph(client_address, styles["Justify"])
        ana_c1 = Table(
            [('RUC ', client_document)] +
            [('RAZÓN SOCIAL: ', p0)] +
            [('DIRECCIÓN: ', p1)] +
            [('ATENDIDO POR: ', order_obj.user.username.upper() + " " + order_obj.subsidiary.name)],
            colWidths=colwiths_table)

    ana_c1.setStyle(TableStyle(style_table))

    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('FONTNAME', (0, 0), (0, -1), 'Ticketing'),  # first column
        ('LEFTPADDING', (2, 0), (2, -1), 2),  # third column
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),  # fourth column
        ('FONTSIZE', (3, 0), (3, -1), 12),  # fourth column
        ('FONTNAME', (3, 0), (3, -1), 'Ticketing'),  # fifth row [col 1:2]

        ('FONTSIZE', (2, 3), (2, 4), 12),  # third column

        ('ALIGNMENT', (1, 2), (1, 4), 'LEFT'),  # second column [row 3:5]
        ('FONTNAME', (2, 3), (2, 4), 'Ticketing'),  # third column [row 4:5]
        ('RIGHTPADDING', (3, 3), (3, 4), 0.5),  # fourth column [row 4:5]
        ('FONTNAME', (0, 4), (1, 4), 'Square-Bold'),  # fifth row [col 1:2]
        ('FONTSIZE', (0, 4), (1, 4), 12),  # fifth row [col 1:2]
        ('LEFTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('SPAN', (1, 0), (3, 0)),  # first row
        ('SPAN', (0, 1), (1, 1)),  # second row
        ('SPAN', (2, 1), (3, 1)),  # second row
    ]
    p10 = Paragraph('SR(A): ' + passenger_document + ' - ' + passenger_name, styles["Justify"])
    colwiths_table = [_wt * 25 / 100, _wt * 25 / 100, _wt * 25 / 100, _wt * 25 / 100]
    ana_c2 = Table(
        [('PASAJERO:', p10, '', '')] +
        [('AGENCIA DE EMBARQUE:', '', order_obj.subsidiary.name, '')] +
        [('ORIG:', order_obj.subsidiary.short_name, '', '')] +
        [('DEST:', order_obj.destiny.name, 'FECHA:', str(_format_date))] +
        [('ASIENTO:', order_obj.programming_seat.plan_detail.name, 'HORA', str(_format_time))],
        colWidths=colwiths_table)
    ana_c2.setStyle(TableStyle(style_table))

    my_style_table3 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),  # all columns
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
    ]
    colwiths_table = [_wt * 80 / 100, _wt * 20 / 100]
    ana_c6 = Table([('DESCRIPCIÓN', 'TOTAL')], colWidths=colwiths_table)
    ana_c6.setStyle(TableStyle(my_style_table3))

    sub_total = 0
    total = 0
    igv_total = 0

    P0 = Paragraph(
        'SER TRANSPORTE RUTA ' + order_obj.subsidiary.short_name + ' - ' + order_obj.destiny.name + '<br/> ASIENTO ' + order_obj.programming_seat.plan_detail.name + '.',
        styles["Justify"])

    base_total = 1 * 45
    base_amount = base_total / 1.1800
    igv = base_total - base_amount
    sub_total = sub_total + base_amount
    total = total + base_total
    igv_total = igv_total + igv

    my_style_table4 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),   # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
    ]
    ana_c7 = Table([(P0, 'S/ ' + str(decimal.Decimal(round(order_obj.total, 2))))],
                   colWidths=[_wt * 80 / 100, _wt * 20 / 100])
    ana_c7.setStyle(TableStyle(my_style_table4))

    my_style_table5 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns

        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),   # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),  # all columns
        ('RIGHTPADDING', (2, 0), (2, -1), 0),  # third column
        ('ALIGNMENT', (2, 0), (2, -1), 'RIGHT'),  # third column
        ('RIGHTPADDING', (3, 0), (3, -1), 0.3),  # four column
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),  # four column
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('FONTNAME', (0, 2), (-1, 2), 'Square-Bold'),  # third row
        ('FONTSIZE', (0, 2), (-1, 2), 10),  # third row
    ]

    ana_c8 = Table(
        [('OP. NO GRAVADA', '', 'S/', str(decimal.Decimal(round(order_obj.total, 2))))] +
        [('I.G.V.  (18.00)', '', 'S/', '0.00')] +
        [('TOTAL', '', 'S/', str(decimal.Decimal(round(order_obj.total, 2))))],
        colWidths=[_wt * 60 / 100, _wt * 10 / 100, _wt * 10 / 100, _wt * 20 / 100]
    )
    ana_c8.setStyle(TableStyle(my_style_table5))
    footer = 'SON: ' + numero_a_moneda(order_obj.total)

    my_style_table6 = [
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),   # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (1, 0)),  # first row
    ]

    datatable = order_bill_obj.code_qr
    ana_c9 = Table([(qr_code(datatable), '')], colWidths=[_wt * 99 / 100, _wt * 1 / 100])
    ana_c9.setStyle(TableStyle(my_style_table6))

    _dictionary = []
    _dictionary.append(I)
    _dictionary.append(Spacer(1, 5))
    _dictionary.append(Paragraph(tbh_business_name_address.replace("\n", "<br />"), styles["Center"]))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Paragraph(tbn_document, styles["Center_Regular"]))
    _dictionary.append(
        Paragraph(order_bill_obj.serial + ' - ' + str(order_bill_obj.n_receipt).zfill(6), styles["Center_Bold"]))
    _dictionary.append(Spacer(1, 3))
    _dictionary.append(ana_c1)

    _dictionary.append(Paragraph(line, styles["Center2"]))

    _dictionary.append(Spacer(1, 6))

    _dictionary.append(Paragraph('DATOS DE VIAJE ', styles["Center_Regular"]))
    _dictionary.append(Spacer(1, 3))
    _dictionary.append(ana_c2)
    _dictionary.append(Spacer(1, 3))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(ana_c6)
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(ana_c7)
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(ana_c8)
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Paragraph(footer, styles["Center"]))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(
        Paragraph("***CONSERVAR SU COMPROBANTE ANTE CUALQUIER EVENTUALIDAD***".replace('***', '"'), styles["Center2"]))
    _dictionary.append(ana_c9)
    _dictionary.append(Paragraph("DE LAS CONDICIONES PARA EL SERVICIO DE TRANSPORTE: "
                                 "1. EL BOLETO DE VIAJE ES PERSONAL, TRANSFERIBLE Y/O PO5TERGABLE."
                                 "2. EL PASAJERO SE PRESENTARÁ 30 MIN ANTES DE LA HORA DE VIAJE, DEBIENDO PRESENTAR SU BOLETO DE VIAJE Y DNI."
                                 "3. LOS MENORES DE EDAD VIAJAN CON SUS PADRES O EN SU DEFECTO DEBEN PRESENTAR PERMISO NOTARIAL DE SUS PADRES, MAYORES DE 5 AÑOS PAGAN SU PASAJE. "
                                 "4. EN CASO DE ACCIDENTES EL PASAJERO VIAJA  ASEGURADO CON SOAT DE LA COMPANIA RIMAC SEGUROS "
                                 "5. EL PASAJEROTIENE DERECHO ATRANSPORTAR 20 KILOS DE EQUIPAJE, SOLO ARTICULOS DE USO PERSONAL (NO CARGA).  EL EXCESO SERÁ ADMITIDO CUANDO LA CAPACIDAD DEL BUS LO PERMITA, PREVIO PAGO DE LA TARIFA."
                                 "6. LA EMPRESA NO SE RESPONSABILIZA POR FALLAS AJENAS AL MISMO SERVICIO DE TRANSPORTE (WIFI, TOMACORRIENTES, PANTALLAS, AUDIO Y OTRAS SIMILARES) PUES ESTOS SERVICIOS SON OFRECIDOS EN CALIDAD DE CORTESIA. "
                                 "7. LAS DEVOLUCIONES DE BOLETOS PAGADOS CON VISA SE EFECTUARÁ SEGÚN LOS PLAZOS, PROCEDIMIENTOS Y CANALES ESTABLECIDOS POR VISA, EN NINGUN CASO SE EFECTUARÁ DEVOLUCIÓN EN EFECTIVO.",
                                 styles["Center3"]))
    _dictionary.append(Spacer(1, 2))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(1, 2))
    _dictionary.append(Paragraph(
        "¡Gracias por viajar en MENDIVIL!",
        styles["Center2"]))
    buff = io.BytesIO()

    ml = 0.05 * inch
    mr = 0.055 * inch
    ms = 0.039 * inch
    mi = 0.039 * inch

    doc = SimpleDocTemplate(buff,
                            pagesize=(3.14961 * inch, 11.6 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='TICKET'
                            )
    doc.build(_dictionary)
    # doc.build(elements)
    # doc.build(Story)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="CPE[{}].pdf"'.format(
        order_obj.serial + '-' + order_obj.correlative_sale)

    response.write(buff.getvalue())

    buff.close()
    return response


def qr_code(table):
    # generate and rescale QR
    qr_code = qr.QrCodeWidget(table)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = Drawing(
        3.5 * cm, 3.5 * cm, transform=[3.5 * cm / width, 0, 0, 3.5 * cm / height, 0, 0])
    drawing.add(qr_code)

    return drawing


def print_ticket_order_sales(request, pk=None, t=None):  # Ticket

    _wt = 3.14 * inch - 8 * 0.05 * inch

    order_obj = Order.objects.get(pk=pk)
    client_id = order_obj.client.id
    client_obj = Client.objects.get(id=client_id)
    info_name = ""
    info_document = ""
    client_document = ""
    client_name = ""
    client_address = ""

    subsidiary_obj = Subsidiary.objects.get(id=order_obj.subsidiary.id)

    tbh_business_name = 'T VISION SAFE E.I.R.L.'

    tbh_business_address = subsidiary_obj.address
    tbh_ruc = subsidiary_obj.ruc

    _title = Paragraph(tbh_business_name.replace("\n", "<br />"), styles["Center_Bold_title"])
    _title2 = Paragraph(tbh_business_address.replace("\n", "<br />"), styles["Center-text"])
    _title3 = Paragraph('RUC: ' + tbh_ruc.replace("\n", "<br />"), styles["Center-text"])

    date = order_obj.update_at
    _format_time = datetime.now().strftime('%H:%M:%S')
    _format_date = date.strftime("%d/%m/%Y")

    if t == 0:
        if order_obj.type == 'T':
            tbn_document = 'COTIZACION'
        else:
            tbn_document = 'TICKET'
    else:
        if order_obj.orderbill.type == '1':
            tbn_document = 'FACTURA ELECTRONICA'
        elif order_obj.orderbill.type == '2':
            tbn_document = 'BOLETA ELECTRONICA'
    info_name = client_obj.names
    info_document = client_obj.clienttype_set.first().document_number
    client_type = client_obj.clienttype_set.first().document_type.id
    client_name = info_name
    client_document = info_document
    if client_type == '06':
        info_address = client_obj.clientaddress_set.last().address.upper()
        client_address = info_address
    line = '-------------------------------------------------------'

    I = Image(logo)
    I.drawHeight = 3.35 * inch / 2.9
    I.drawWidth = 3.4 * inch / 2.9

    _tbl_header = [
        [I, _title],
        ['', _title3],
        ['', _title2],
    ]

    header_page = Table(_tbl_header, colWidths=[_wt * 40 / 100, _wt * 60 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, -1)),  # first row
        # ('BACKGROUND', (1, 2), (2, 2), colors.blue),  # SECOND column
        ('TOPPADDING', (1, 1), (2, 1), -5),  # first column
        ('TOPPADDING', (1, 2), (2, 2), -10),  # first column
    ]
    header_page.setStyle(TableStyle(style_table_header))

    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),  # second column
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
    ]
    colwiths_table = [_wt * 30 / 100, _wt * 70 / 100]

    if client_type == '06':
        p0 = Paragraph(client_name.upper(), styles["Justify"])
        p1 = Paragraph(client_address.upper(), styles["Justify"])
        ana_c1 = Table(
            [('RUC ', client_document)] +
            [('RAZÓN SOCIAL: ', p0)] +
            [('DIRECCIÓN: ', p1)] +
            [('ATENDIDO POR: ', order_obj.user.username.upper() + " ")] +
            [('FECHA: ', _format_date + '  HORA: ' + _format_time)] +
            [('TIPO DE PAGO: ', order_obj.get_way_to_pay_type_display().upper())],
            colWidths=colwiths_table)
    elif client_type != '06':
        p0 = Paragraph(client_name.upper(), styles["Left"])
        ana_c1 = Table(
            [('CLIENTE: N DOC ', client_document)] +
            [('SR(A): ', p0)] +
            [('ATENDIDO POR: ', order_obj.user.username.upper() + " ")] +
            [('FECHA: ', _format_date + '  HORA: ' + _format_time)] +
            [('TIPO DE PAGO: ', order_obj.get_way_to_pay_type_display().upper())],
            colWidths=colwiths_table)

    ana_c1.setStyle(TableStyle(style_table))

    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('FONTNAME', (0, 0), (0, -1), 'Ticketing'),  # first column
        ('LEFTPADDING', (2, 0), (2, -1), 2),  # third column
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),  # fourth column
        ('FONTSIZE', (3, 0), (3, -1), 12),  # fourth column
        ('FONTNAME', (3, 0), (3, -1), 'Ticketing'),  # fifth row [col 1:2]
        ('LEFTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('ALIGNMENT', (1, 0), (3, -1), 'RIGHT'),  # four column
        # ('BACKGROUND', (1, 0), (1, 0), colors.blue),  # four column
        ('SPAN', (1, 0), (3, 0)),  # first row
        ('SPAN', (0, 1), (1, 1)),  # second row
        ('SPAN', (2, 1), (3, 1)),  # second row
    ]
    p10 = Paragraph('SR(A): ' + info_document + ' - ' + info_name, styles["Justify"])
    colwiths_table = [_wt * 25 / 100, _wt * 25 / 100]
    ana_c2 = Table(
        [('CLIENTE:', p10, '', '')] +
        [('SEDE:', order_obj.id, 'FECHA:', str(_format_date))],
        colWidths=colwiths_table)
    ana_c2.setStyle(TableStyle(style_table))
    # -------
    my_style_table_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),  # second column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # first column
        ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'),  # SECOND column
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),  # third column
        ('ALIGNMENT', (4, 0), (4, -1), 'RIGHT'),  # four column
        ('RIGHTPADDING', (4, 0), (4, -1), 0.1),  # first column
        # ('BACKGROUND', (4, 0), (4, -1), colors.blue),  # four column
        ('RIGHTPADDING', (3, 0), (3, -1), 0.5),  # four column
    ]
    _rows = []
    sub_total = 0
    total = 0
    igv_total = 0
    _sum_total_multiply = 0
    for d in order_obj.orderdetail_set.all():
        P0 = Paragraph(d.commentary.upper(), styles["Justify"])
        _rows.append((P0, str(decimal.Decimal(round(d.quantity_sold, 0))), d.unit.name, str(d.price_unit),
                      str(decimal.Decimal(round(d.quantity_sold * d.price_unit, 2)))))
        base_total = d.quantity_sold * d.price_unit
        base_amount = base_total / decimal.Decimal(1.1800)
        igv = base_total - base_amount
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv
        _sum_total_multiply += d.multiply()
    ana_c_detail = Table(_rows,
                         colWidths=[_wt * 50 / 100, _wt * 10 / 100, _wt * 10 / 100, _wt * 15 / 100, _wt * 15 / 100])
    ana_c_detail.setStyle(TableStyle(my_style_table_detail))

    my_style_table5 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square-Bold'),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
    ]
    total = decimal.Decimal(_sum_total_multiply).quantize(decimal.Decimal('0.0'), rounding=decimal.ROUND_HALF_EVEN)
    base = round(total / decimal.Decimal(1.18), 2)
    igv = total - base
    if t == 0:
        ana_c8 = Table(
            # [('OP. NO GRAVADA', '', 'S/', str(base))] +
            # [('I.G.V.  (18.00)', '', 'S/', str(igv))] +
            [('TOTAL', '', 'S/', str(total))],
            colWidths=[_wt * 60 / 100, _wt * 10 / 100, _wt * 10 / 100, _wt * 20 / 100]
        )
    else:
        if order_obj.orderbill.type == '1':
            ana_c8 = Table(

                [('OP. NO GRAVADA', '', 'S/', str(base))] +
                [('I.G.V.  (18.00)', '', 'S/', str(igv))] +
                [('TOTAL', '', 'S/', str(total))],
                colWidths=[_wt * 60 / 100, _wt * 10 / 100, _wt * 10 / 100, _wt * 20 / 100]

            )
        else:
            ana_c8 = Table(
                # [('OP. NO GRAVADA', '', 'S/', str(base))] +
                # [('I.G.V.  (18.00)', '', 'S/', str(igv))] +
                [('TOTAL', '', 'S/', str(total))],
                colWidths=[_wt * 60 / 100, _wt * 10 / 100, _wt * 10 / 100, _wt * 20 / 100]
            )
    ana_c8.setStyle(TableStyle(my_style_table5))
    footer = 'SON: ' + numero_a_moneda(order_obj.total)
    counter = order_obj.orderdetail_set.count()
    my_style_table6 = [
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),   # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (1, 0)),  # first row
    ]

    datatable = 'https://4soluciones.pse.pe/20603890214'
    ana_c9 = Table([(qr_code(datatable), '')], colWidths=[_wt * 99 / 100, _wt * 1 / 100])
    ana_c9.setStyle(TableStyle(my_style_table6))

    _dictionary = []
    _dictionary.append(header_page)
    # _dictionary.append(I)
    _dictionary.append(Spacer(-10, -10))
    # _dictionary.append(Paragraph(tbh_business_name.replace("\n", "<br />"), styles["Center_Bold_title"]))
    # _dictionary.append(Paragraph(tbh_business_address.replace("\n", "<br />"), styles["Center-text"]))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-10, -10))
    _dictionary.append(Paragraph(tbn_document, styles["Center_Bold"]))
    _dictionary.append(Spacer(-10, -10))
    if t == 0:
        _dictionary.append(Spacer(-5, -5))
        _dictionary.append(
            Paragraph(str(order_obj.subsidiary_store.subsidiary.serial) + ' - ' + str(
                str(order_obj.correlative_sale).zfill(10)),
                      styles["Center_Bold"]))
    else:
        _dictionary.append(Spacer(-5, -5))
        _dictionary.append(
            Paragraph(str(order_obj.orderbill.serial) + ' - ' + str(order_obj.orderbill.n_receipt),
                      styles["Center_Bold"]))
    _dictionary.append(Spacer(-5, -5))
    _dictionary.append(ana_c1)
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-1, -1))
    _dictionary.append(Paragraph('DETALLE DE PRODUCTOS', styles["Center_Regular"]))
    _dictionary.append(Spacer(-1, -1))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(ana_c_detail)  # "ana_c2"
    _dictionary.append(Spacer(-1, -1))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-2, -2))
    _dictionary.append(ana_c8)
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Paragraph(footer, styles["Center"]))
    _dictionary.append(Spacer(-2, -2))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    if t == 0:
        if order_obj.type == 'T':
            _dictionary.append(
                Paragraph("***COTIZACION DEL CLIENTE***".replace('***', '"'), styles["Center2"]))
        else:
            _dictionary.append(
                Paragraph("***COMPROBANTE INTERNO NO TRIBUTARIO***".replace('***', '"'), styles["Center2"]))
    _dictionary.append(Spacer(-10, -10))
    _dictionary.append(ana_c9)
    _dictionary.append(Spacer(-15, -15))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-1, -1))
    _dictionary.append(Paragraph(
        "www.4soluciones.net",
        styles["Center2"]))
    buff = io.BytesIO()

    ml = 0.05 * inch
    mr = 0.055 * inch
    ms = 0.039 * inch
    mi = 0.039 * inch

    doc = SimpleDocTemplate(buff,
                            pagesize=(3.14961 * inch, 7.6 * inch + (inch * 0.14 * counter)),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='TICKET'
                            )
    doc.build(_dictionary)
    # doc.build(elements)
    # doc.build(Story)

    response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = 'inline; filename="somefilename.pdf"'
    # response['Content-Disposition'] = 'attachment; filename="ORDEN[{}].pdf"'.format(
    #     str(order_obj.subsidiary_store.subsidiary.serial) + '-' + str(order_obj.id))

    response.write(buff.getvalue())
    buff.close()
    return response


class OutputPrintQuotation(Flowable):
    def __init__(self, width=200, height=3, count_row=None):
        self.width = width
        self.height = height
        self.count_row = count_row

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv  # El atributo que permite dibujar en canvas

        canvas.saveState()
        canvas.setLineWidth(2)
        canvas.setFillColor(red)
        row_d = 0
        row_d = self.count_row
        # canvas.setFont('Newgot', 30)
        # canvas.setFillColorRGB(0.5, 0.5, 0.5)
        if row_d == 1:
            d = 50 + row_d * 25
        else:
            d = 30 + row_d * 25

        # canvas.roundRect(395, 8, 155, 80, 10, stroke=1, fill=0)
        # canvas.roundRect(0, -105, 550, 105, 10, stroke=1, fill=0)
        canvas.roundRect(386, 8, 169, 80, 10, stroke=1, fill=0)
        canvas.roundRect(-7, -130, 563, 130, 10, stroke=1, fill=0)
        # canvas.roundRect(0, -(d + 110), 550, d, 10, stroke=1, fill=0)
        canvas.restoreState()


def print_quotation(request, pk=None, t=None):
    _a4 = (8.3 * inch, 11.7 * inch)
    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    _bts = 8.3 * inch - 0.25 * inch - 0.25 * inch

    order_obj = Order.objects.get(id=pk)

    I = Image(logo)
    I.drawHeight = 3.60 * inch / 2.9
    I.drawWidth = 3.9 * inch / 2.9

    subsidiary_obj = Subsidiary.objects.get(id=order_obj.subsidiary.id)

    telephone_subsidiary = '-'
    email_subsidiary = '-'
    phone_subsidiary = '-'
    address_subsidiary = subsidiary_obj.address

    if subsidiary_obj.contact_phone is not None:
        telephone_subsidiary = subsidiary_obj.contact_phone

    if subsidiary_obj.email is not None:
        email_subsidiary = subsidiary_obj.email

    if subsidiary_obj.phone is not None:
        phone_subsidiary = subsidiary_obj.phone

    # employee_obj = Employee.objects.filter(worker__user=order_obj.user).last()
    # if employee_obj is not None:
    #     telephone_subsidiary = employee_obj.telephone_number
    #     email_subsidiary = employee_obj.email
    # else:
    #     telephone_subsidiary = '999973999'
    #     email_subsidiary = 'roldem@roldem.com'

    tbl1_col__2 = [
        [Paragraph('T VISION SAFE E.I.R.L.', styles["Justify_Newgot_title"])],
        [Paragraph(address_subsidiary, styles['Normal'])],
        ['Celular: ' + str(telephone_subsidiary)],
        ['Teléfono Fijo: ' + str(phone_subsidiary)],
        ['Correo: ' + str(email_subsidiary)],
    ]
    col_2 = Table(tbl1_col__2)
    style_table_col_2 = [
        # ('GRID', (0, 3), (0, 3), 0.9, colors.red),
        ('TEXTCOLOR', (0, 2), (0, 3), colors.blue),
    ]
    col_2.setStyle(TableStyle(style_table_col_2))

    tbl1_col__3 = [
        [Paragraph('RUC: 20603890214', styles["Center_Newgot_title"])],
        [Paragraph('COTIZACIÓN Nº', styles["Center_Newgot_title"])],
        [Paragraph(order_obj.subsidiary.serial + '-' + str(str(order_obj.correlative_sale).zfill(10)),
                   styles["Center_Newgot_title"])],
    ]
    col_3 = Table(tbl1_col__3, colWidths=[_bts * 28 / 100])
    style_table_col_3 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.red),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    col_3.setStyle(TableStyle(style_table_col_3))

    _tbl_header = [
        [I, col_2, col_3],
    ]
    header_page = Table(_tbl_header, colWidths=[_bts * 20 / 100, _bts * 50 / 100, _bts * 30 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    header_page.setStyle(TableStyle(style_table_header))
    # ---------------------------------Datos Cliente----------------------------#
    telephone = '-'
    email = '-'
    client_id = order_obj.client.id
    client_obj = Client.objects.get(id=client_id)
    type_client = client_obj.clienttype_set.first().document_type.id
    info_document = client_obj.clienttype_set.first().document_number

    if client_obj.phone is not None:
        telephone = client_obj.phone
    if client_obj.email is not None:
        email = client_obj.email
    info_address = '-'
    payment = '-'
    description = '-'
    cash_flow_set = CashFlow.objects.filter(order=order_obj)

    if order_obj.way_to_pay_type:
        payment = order_obj.get_way_to_pay_type_display()
    else:
        payment = 'Efectivo'

    info_address = client_obj.clientaddress_set.first().address.upper()

    tbl2_col1 = [
        ['Señor(es) :', Paragraph(str(client_obj.names), styles['Left_Square'])],
        ['RUC/DNI :', Paragraph(str(info_document), styles['Left_Square'])],
        ['Dirección :', Paragraph(str(info_address), styles['Left_Square'])],
        ['Teléfono :', Paragraph(str(telephone), styles['Left_Square'])],
        ['Correo :', Paragraph(str(email), styles['Left_Square'])],
        # ['Forma Pago:', Paragraph(str(description), styles['Left_Square'])],
        ['Lugar de Entrega  : ', Paragraph(str(order_obj.place_delivery.upper()), styles['Left_Square'])],
    ]
    tbl2_col_1 = Table(tbl2_col1, colWidths=[_bts * 20 / 100, _bts * 50 / 100])
    style_table2_col1 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'LEFT'),  # first column
        ('LEFTPADDING', (0, 0), (0, -1), 13),  # first column
    ]
    tbl2_col_1.setStyle(TableStyle(style_table2_col1))

    tbl2_col2 = [
        ['Fecha Emisión: ', Paragraph(order_obj.create_at.strftime("%d-%m-%Y"), styles['Left_Square'])],
        ['Fecha Vencimiento: ', Paragraph(order_obj.validity_date.strftime("%d-%m-%Y"), styles['Left_Square'])],
        ['Vendedor: ', Paragraph(order_obj.user.username.upper(), styles['Left_Square'])],
        # ['Moneda: ', Paragraph(order_obj.get_coin_display(), styles['Left_Square'])],
        ['Cond. Venta: ', Paragraph(str(payment.upper()), styles['Left_Square'])],
        ['Plazo: ', Paragraph(str(order_obj.date_completion) + ' dia(s)', styles['Left_Square'])],
        ['Tipo: ', Paragraph(str(order_obj.get_type_quotation_display()), styles['Left_Square'])],
        ['Nombre: ', Paragraph(str(order_obj.type_name_quotation.upper()), styles['Left_Square'])]
    ]
    tbl2_col_2 = Table(tbl2_col2, colWidths=[_bts * 18 / 100, _bts * 14 / 100])

    _tbl_header2 = [
        [tbl2_col_1, tbl2_col_2],
    ]
    header2_page = Table(_tbl_header2, colWidths=[_bts * 66 / 100, _bts * 34 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    header2_page.setStyle(TableStyle(style_table_header))
    # ------------ENCABEZADO DEL DETALLE-------------------#
    style_table_header_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),  # all columns
        ('GRID', (0, 0), (-1, -1), 1, colors.fidblue),  # all columns
        ('BACKGROUND', (0, 0), (-1, -1), colors.fidblue),  # all columns
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),  # all columns
        ('RIGHTPADDING', (1, 0), (1, -1), 10),  # second column
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
        ('ALIGNMENT', (2, 0), (2, -1), 'LEFT'),  # second column
    ]
    width_table = [_bts * 5 / 100, _bts * 11 / 100, _bts * 44 / 100, _bts * 10 / 100, _bts * 9 / 100,
                   _bts * 8 / 100, _bts * 13 / 100]
    header_detail = Table([('Item', 'Código', 'Descripción', 'Cantidad', 'U.M.', 'P. Unit', 'Total')],
                          colWidths=width_table)
    header_detail.setStyle(TableStyle(style_table_header_detail))
    line = '-------------------------------------------------------------------------------------------------------------'
    # -------------------DETAIL---------------------#
    style_table_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.fidblue),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGNMENT', (6, 0), (6, -1), 'RIGHT'),  # seven column
        ('ALIGNMENT', (5, 0), (5, -1), 'RIGHT'),  # six column
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),  # second column
        # ('ALIGNMENT', (3, 0), (3, -1), 'CENTER'),  # four column
        # ('ALIGNMENT', (4, 0), (4, -1), 'CENTER'),  # five column
        ('ALIGNMENT', (3, 0), (3, -1), 'CENTER'),  # three column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # first column
        ('RIGHTPADDING', (3, 0), (3, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),  # all columns
        # ('BACKGROUND', (4, 0), (4, -1),  colors.green),  # four column
    ]

    detail_rows = []
    count = 0
    sub_total = 0
    _total = 0

    # for d in order_obj.orderdetail_set.all():
    #     P0 = Paragraph(d.commentary.upper(), styles["Justify"])
    #     _rows.append((P0, str(decimal.Decimal(round(d.quantity_sold, 3))), d.unit.name, str(d.price_unit),
    #                   str(decimal.Decimal(round(d.quantity_sold * d.price_unit, 2)))))
    #     base_total = d.quantity_sold * d.price_unit
    #     base_amount = base_total / decimal.Decimal(1.1800)
    #     igv = base_total - base_amount
    #     sub_total = sub_total + base_amount
    #     total = total + base_total
    #     igv_total = igv_total + igv

    details_list = order_obj.orderdetail_set.all()
    total = 0
    for detail in details_list.order_by('id'):
        _code = '-'
        if detail.product.code:
            _code = str(detail.product.code.zfill(6))

        count = count + 1
        _product_plus_brand = Paragraph(str(detail.commentary.upper()) + ' - ' + str(detail.product.product_brand.name),
                                        styles["Justify_Square"])
        # _product_name = Paragraph(str(detail.product.name), styles["Justify_Square"])
        _quantity = str(decimal.Decimal(round(detail.quantity_sold, 2)))
        _unit = str(detail.unit.description)
        _price_unit = round(decimal.Decimal(detail.price_unit) * decimal.Decimal(1.18), 2)
        _total = round(detail.quantity_sold * decimal.Decimal(detail.price_unit), 2)

        detail_rows.append((count, _code, _product_plus_brand, _quantity, _unit, detail.price_unit, _total))
        total += _total

    detail_body = Table(detail_rows,
                        colWidths=[_bts * 5 / 100, _bts * 11 / 100, _bts * 44 / 100, _bts * 10 / 100, _bts * 9 / 100,
                                   _bts * 8 / 100, _bts * 13 / 100])
    detail_body.setStyle(TableStyle(style_table_detail))
    # difference = sub_total * decimal.Decimal(0.18)
    _text = 'DESCUENTO'
    _discount = 0
    total_with_igv = round(total * decimal.Decimal(1.18), 2)
    # if order_obj.type_discount == 'E':
    #     _text = 'DESCUENTO:'
    #     _discount = order_obj.discount
    # elif order_obj.type_discount == 'P':
    #     _text = 'DESCUENTO(' + str(order_obj.discount) + '%)'
    #     _discount = (sub_total * order_obj.discount) / 100
    # difference = (sub_total - _discount) * decimal.Decimal(0.18)
    valor_venta = decimal.Decimal(total) / decimal.Decimal(1.18)
    igv = decimal.Decimal(total) - valor_venta
    # ---------------------Totales-----------------------#
    table_bank = [
        [Paragraph('BANCO', styles['Center_Newgot_1']),
         Paragraph('MONEDA', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA CORRIENTE', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA INTERBANCARIO', styles['Center_Newgot_1'])],

        [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
         Paragraph('SOLES', styles['Center-text']), Paragraph('215-9908678-0-71', styles['Center-text']),
         Paragraph('002-215-009908678071-27', styles['Center-text'])],

        # [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Center-text']), Paragraph('215-9844079-0-56', styles['Center-text']),
        #  Paragraph('002-215-009844079056-20', styles['Center-text'])],
        #
        # [Paragraph('CUENTA BBVA', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Left-text']), Paragraph('0011 0418 0100018341 16', styles['Left-text']),
        #  Paragraph('011 418 000100018341 16', styles['Left-text'])],
        #
        # [Paragraph('BBVA', styles['Center_Newgot_1']),
        #  Paragraph('DOLARES', styles['Left-text']), Paragraph('0011 0418 0100018368 19', styles['Left-text']),
        #  Paragraph('011 418 000100018368 19', styles['Left-text'])],
    ]
    t_bank = Table(table_bank, colWidths=[_bts * 7 / 100, _bts * 7 / 100, _bts * 24 / 100, _bts * 24 / 100])
    style_bank = [
        # ('SPAN', (0, 1), (0, 2)),
        # ('SPAN', (0, 3), (0, 4)),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        # ('BACKGROUND', (2, 1), (2, 1), colors.blue),  # four column
    ]
    t_bank.setStyle(TableStyle(style_bank))

    total_col1 = [
        [Paragraph(
            'OBSERVACION: ' + order_obj.observation,
            styles["Justify_Newgot"])],
        [Paragraph('SON: ' + numero_a_moneda(round(decimal.Decimal(total), 2), ),
                   styles["Justify_Newgot"])],
        [t_bank],
    ]
    total_col_1 = Table(total_col1, colWidths=[_bts * 63 / 100])
    style_table_col1 = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),
    ]
    total_col_1.setStyle(TableStyle(style_table_col1))
    money = 'S/.'
    # if order_obj.coin == 'S':
    #     money = 'S/.'
    # elif order_obj.coin == 'D':
    #     money = '$'

    total_col2 = [
        [Paragraph('VALOR DE VENTA:', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(valor_venta, 2)), styles["Right_Newgot"])],
        # [Paragraph(_text, styles["Justify_Newgot"]),
        #  Paragraph(money + ' ' + str(round(_discount, 3)), styles["Right_Newgot"])],
        # [Paragraph('OPERACION GRAVADAS', styles["Justify_Newgot"]),
        #  Paragraph(money + ' ' + str(round(sub_total - _discount, 3)), styles["Right_Newgot"])],
        [Paragraph('I.G.V(18%):', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(igv, 2)), styles["Right_Newgot"])],
        [Paragraph('IMPORTE TOTAL:', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(valor_venta + igv, 2)), styles["Right_Newgot"])],
    ]
    total_col_2 = Table(total_col2, colWidths=[_bts * 19 / 100, _bts * 14 / 100])

    style_table_col2 = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    total_col_2.setStyle(TableStyle(style_table_col2))

    total_ = [
        [total_col_1, total_col_2],
    ]
    total_page = Table(total_, colWidths=[_bts * 65 / 100, _bts * 35 / 100])
    style_table_page = [
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),  # three column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # first column
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.red),
    ]
    total_page.setStyle(TableStyle(style_table_page))

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=(8.3 * inch, 11.7 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='COTIZACION ' + str(str(order_obj.correlative_sale).zfill(6))
                            )
    dictionary = []
    dictionary.append(header_page)
    dictionary.append(OutputPrintQuotation(count_row=count))
    dictionary.append(header2_page)
    dictionary.append(Spacer(1, 16))
    dictionary.append(header_detail)
    # dictionary.append(Paragraph(line, styles["Center_Newgot_title"]))
    dictionary.append(detail_body)
    dictionary.append(Spacer(1, 15))
    dictionary.append(total_page)
    dictionary.append(Paragraph(line, styles["Center_Newgot_title"]))
    dictionary.append(Paragraph(
        'Cumplimos con las especificaciones tecnicas del requerimiento para lograr un producto que esté a entera satisfacción de nuestros clientes.',
        styles["Center_Newgot"]))
    dictionary.append(Paragraph('www.electrical.com', styles["Center_Newgot"]))
    response = HttpResponse(content_type='application/pdf')
    doc.build(dictionary)
    response.write(buff.getvalue())
    buff.close()
    return response


class OutputInvoiceGuide(Flowable):
    def __init__(self, width=200, height=3, count_row=None):
        self.width = width
        self.height = height
        self.count_row = count_row

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv  # El atributo que permite dibujar en canvas

        canvas.saveState()
        canvas.setLineWidth(1)
        canvas.setFillColor(Color(0, 0, 0, alpha=0.1))
        # canvas.setFont('Newgot', 30)
        # canvas.setFillColorRGB(0.5, 0.5, 0.5)
        # canvas.roundRect(395, 8, 155, 80, 10, stroke=1, fill=0)
        # canvas.roundRect(0, -105, 550, 105, 10, stroke=1, fill=0)
        canvas.roundRect(386, 8, 169, 80, 10, stroke=1, fill=1)
        # canvas.roundRect(-7, -140, 563, 140, 10, stroke=1, fill=0)
        # canvas.roundRect(0, -(d + 110), 550, d, 10, stroke=1, fill=0)
        # canvas.roundRect(left, bottom, width, height, radius, activa borde, activa color fondo)
        canvas.restoreState()


def print_order_bill(request, pk=None):
    _a4 = (8.3 * inch, 11.7 * inch)
    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    _bts = 8.3 * inch - 0.25 * inch - 0.25 * inch

    # service_obj = GuideService.objects.get(id=pk)
    order_obj = Order.objects.get(id=pk)
    subsidiary_obj = Subsidiary.objects.get(id=order_obj.subsidiary.id)
    I = Image(logo)
    I.drawHeight = 3.60 * inch / 2.9
    I.drawWidth = 3.9 * inch / 2.9
    telephone_subsidiary = '-'
    email_subsidiary = '-'
    if subsidiary_obj.email:
        email_subsidiary = subsidiary_obj.email
    if subsidiary_obj.contact_phone is not None:
        telephone_subsidiary = subsidiary_obj.contact_phone
    # employee_obj = Employee.objects.filter(worker__user=service_obj.user).last()
    # if employee_obj is not None:
    #     telephone_user = employee_obj.telephone_number
    #     email_user = employee_obj.email
    # else:
    #     telephone_user = '-'
    #     email_user = '-'

    tbl1_col__2 = [
        [Paragraph('T VISION SAFE E.I.R.L.', styles["Justify_Newgot_title"])],
        [Paragraph(subsidiary_obj.address, styles['Normal'])],
        ['Telefono: ' + str(telephone_subsidiary)],
        ['Correo: ' + str(email_subsidiary)],
    ]
    col_2 = Table(tbl1_col__2)
    style_table_col_2 = [
        # ('GRID', (0, 3), (0, 3), 0.9, colors.red),
        ('TEXTCOLOR', (0, 3), (0, 3), colors.blue),
    ]
    col_2.setStyle(TableStyle(style_table_col_2))
    order_bill_set = OrderBill.objects.filter(order=order_obj)
    # services_sets = Service.objects.filter(guideservice=service_obj)
    # services_obj = None
    order_bill_obj = None
    type_bill = 'None'
    # if services_sets.exists():
    #     services_obj = services_sets.last()
    datatable = 'https://4soluciones.pse.pe/20603890214'
    if order_bill_set.exists():
        order_bill_obj = order_bill_set.last()
        datatable = order_bill_obj.code_qr
        type_bill = order_bill_obj.get_type_display().upper()
    tbl1_col__3 = [
        [Paragraph('RUC 20603890214', styles["Center_Newgot_title"])],
        [Paragraph(str(type_bill) + ' ELECTRÓNICA', styles["Center_Newgot_title"])],
        [Paragraph(order_bill_obj.serial + '-' + str(str(order_bill_obj.n_receipt).zfill(8)),
                   styles["Center_Newgot_title"])],
    ]
    col_3 = Table(tbl1_col__3, colWidths=[_bts * 28 / 100])
    style_table_col_3 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.red),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    col_3.setStyle(TableStyle(style_table_col_3))

    _tbl_header = [
        [I, col_2, col_3],
    ]
    header_page = Table(_tbl_header, colWidths=[_bts * 20 / 100, _bts * 50 / 100, _bts * 30 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    header_page.setStyle(TableStyle(style_table_header))
    # ---------------------------------Datos Cliente----------------------------#
    client_id = order_obj.client.id
    client_obj = Client.objects.get(id=client_id)
    type_client = client_obj.clienttype_set.first().document_type.id
    info_document = client_obj.clienttype_set.first().document_number
    telephone = client_obj.phone
    if telephone is None:
        telephone = '-'
    email = client_obj.email
    if email is None:
        email = '-'
    info_address = ''
    type_payment = order_obj.way_to_pay_type
    payment = order_obj.get_way_to_pay_type_display()
    description = '-'
    detail_credit = []
    cash_flow_set = CashFlow.objects.filter(order=order_obj)
    # if cash_flow_set:
    #     # payment = cash_flow_set.last().get_type_display()
    #     # if cash_flow_set.last().type == 'E':
    #         description = 'descripcion'
    #         cnt = 0
    #         detail_credit.append(
    #             ('MODALIDAD DE PAGO', 'CUOTAS ', 'FECHA',
    #              'IMPORTE'))
    #         for c in order_obj.paymentfees_set.all():
    #             cnt = cnt + 1
    #             detail_credit.append(
    #                 ('CREDITO POR PAGAR', 'CUOTA ' + str(cnt), str(c.date.strftime('%d-%m-%Y')),
    #                  str(round(c.amount, 2))))
    #         credit_list = Table(detail_credit,
    #                             colWidths=[_bts * 60 / 100,
    #                                        _bts * 10 / 100,
    #                                        _bts * 20 / 100,
    #                                        _bts * 10 / 100])
    #         style_credit = [
    #             ('ALIGNMENT', (0, 0), (2, -1), 'CENTER'),
    #             ('ALIGNMENT', (3, 0), (-1, -1), 'RIGHT'),
    #             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    #             ('SPAN', (0, 1), (0, -1)),
    #             ('FONTNAME', (0, 0), (-1, -1), 'Square'),
    #             ('GRID', (0, 0), (-1, -1), 0.3, colors.darkgray),
    #             ('FONTSIZE', (0, 0), (-1, -1), 10),
    #             # ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    #             # ('RIGHTPADDING', (3, 0), (3, -1), 10),  # first column
    #             ('BACKGROUND', (0, 0), (-1, 0), colors.darkgray),  # four column
    #             # ('BACKGROUND', (4, 0), (4, -1), colors.blue),  # four column
    #         ]
    #         credit_list.setStyle(TableStyle(style_credit))

    if type_client == '06':
        info_address = client_obj.clientaddress_set.last().address
    nro_project = 'name project'
    if nro_project is None:
        nro_project = '-'
    tbl2_col1 = [
        ['Señor(es) :', Paragraph(str(client_obj.names), styles['Left_Square'])],
        ['Ruc/dni    :', Paragraph(str(info_document), styles['Left_Square'])],
        ['Direccion :', Paragraph(str(info_address.upper()), styles['Left_Square'])],
        ['Telefono  :', Paragraph(str(telephone), styles['Left_Square'])],
        ['Correo     :', Paragraph(str(email), styles['Left_Square'])],
        ['Des. Pago : ', Paragraph(str(description), styles['Left_Square'])],
    ]
    tbl2_col_1 = Table(tbl2_col1, colWidths=[_bts * 15 / 100, _bts * 54 / 100])
    style_table2_col1 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'LEFT'),  # first column
        ('LEFTPADDING', (0, 0), (0, -1), 13),  # first column
    ]
    tbl2_col_1.setStyle(TableStyle(style_table2_col1))
    nro_purchase_client = 'nro_purchase_client'
    if nro_purchase_client is None:
        nro_purchase_client = '-'
    _row_payment_deposit = []
    if type_payment == 'D':
        _row_payment_deposit = ['Depósito a: ', Paragraph(str(order_obj.cashflow_set.last().cash.name), styles['Left_Square'])]
    tbl2_col2 = [
        ['Fecha Emision: ', Paragraph(order_obj.create_at.strftime("%d-%m-%Y"), styles['Left_Square'])],
        ['Vendedor: ', Paragraph(order_obj.user.username.upper(), styles['Left_Square'])],
        # ['Moneda: ', 'coin'],
        ['Cond. Venta: ', Paragraph(str(payment.upper()), styles['Left_Square'])],
        _row_payment_deposit
        # ['Nº Proyecto : ', Paragraph(str(nro_project), styles['Left_Square'])],
        # ['Nº Compra Cliente: ', Paragraph(str(nro_purchase_client), styles['Left_Square'])]
    ]
    tbl2_col_2 = Table(tbl2_col2, colWidths=[_bts * 18 / 100, _bts * 14 / 100])

    _tbl_header2 = [
        [tbl2_col_1, tbl2_col_2],
    ]
    header2_page = Table(_tbl_header2, colWidths=[_bts * 66 / 100, _bts * 34 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
        # ('GRID', (0, 0), (-1, -1), 2, colors.lightgrey),
        # ('GRID', (0, 0), (0, 1), 3.5, colors.red)
    ]
    header2_page.setStyle(TableStyle(style_table_header))
    # ------------ENCABEZADO DEL DETALLE-------------------#
    style_table_header_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),  # all columns
        ('GRID', (0, 0), (-1, -1), 1, colors.darkgray),  # all columns
        ('BACKGROUND', (0, 0), (-1, -1), colors.darkgray),  # all columns
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),  # all columns
        ('RIGHTPADDING', (1, 0), (1, -1), 10),  # second column
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
        ('ALIGNMENT', (2, 0), (2, -1), 'LEFT'),  # second column
    ]
    width_table = [_bts * 8 / 100, _bts * 8 / 100, _bts * 12 / 100, _bts * 42 / 100, _bts * 14 / 100, _bts * 16 / 100]
    header_detail = Table([('Item', 'Cantidad', 'Unidad', 'Descripción', 'Precio U.', 'Total')], colWidths=width_table)
    header_detail.setStyle(TableStyle(style_table_header_detail))
    line = '-------------------------------------------------------------------------------------------------------------'
    # -------------------DETAIL---------------------#
    style_table_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.darkgray),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
        ('ALIGNMENT', (2, 0), (2, -1), 'LEFT'),  # three column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # first column
        ('RIGHTPADDING', (3, 0), (3, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),  # all columns
        # ('BACKGROUND', (1, 0), (1, -1),  colors.green),  # four column
    ]
    detail_rows = []
    count = 0
    _total = 0
    for detail in order_obj.orderdetail_set.all():
        count = count + 1
        _product = Paragraph(str(detail.commentary), styles["Justify_Square"])
        _product_plus_brand = Paragraph(str(detail.commentary.upper()) + ' - ' + str(detail.product.product_brand.name),
                                        styles["Justify_Square"])
        detail_rows.append(
            (str(count), str(decimal.Decimal(round(detail.quantity_sold, 2))), str(detail.unit.description),
             _product_plus_brand,
             str(detail.price_unit), str(round(detail.quantity_sold * detail.price_unit, 2))))
        _total = _total + detail.quantity_sold * detail.price_unit
    detail_body = Table(detail_rows,
                        colWidths=[_bts * 8 / 100, _bts * 8 / 100, _bts * 12 / 100, _bts * 42 / 100, _bts * 14 / 100,
                                   _bts * 16 / 100])
    detail_body.setStyle(TableStyle(style_table_detail))
    # difference = sub_total * decimal.Decimal(0.18)

    _text = 'DESCUENTO'
    _discount = decimal.Decimal(0.00)
    # if order_obj.type_discount == 'E':
    #     _text = 'DESCUENTO:'
    #     _discount = 'discount'
    # elif order_obj.type_discount == 'P':
    #     _text = 'DESCUENTO(' + str(order_obj.discount) + '%)'
    #     _discount = (_total * order_obj.discount) / 100
    valor_venta = decimal.Decimal(_total) / decimal.Decimal(1.18)
    igv = decimal.Decimal(_total) - valor_venta
    # ---------------------Totales-----------------------#
    table_bank = [
        [Paragraph('BANCO', styles['Center_Newgot_1']),
         Paragraph('MONEDA', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA CORRIENTE', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA INTERBANCARIO', styles['Center_Newgot_1'])],

        [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
         Paragraph('SOLES', styles['Center-text']), Paragraph('215-9908678-0-71', styles['Center-text']),
         Paragraph('002-215-009908678071-27', styles['Center-text'])],

        # [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Center-text']), Paragraph('215-9844079-0-56', styles['Center-text']),
        #  Paragraph('002-215-009844079056-20', styles['Center-text'])],

        # [Paragraph('CUENTA BBVA', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Left-text']), Paragraph('0011 0418 0100018341 16', styles['Left-text']),
        #  Paragraph('011 418 000100018341 16', styles['Left-text'])],
        #
        # [Paragraph('CUENTA BBVA', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Left-text']), Paragraph('0011 0418 0100018341 16', styles['Left-text']),
        #  Paragraph('011 418 000100018341 16', styles['Left-text'])],
        #
        # [Paragraph('BBVA', styles['Center_Newgot_1']),
        #  Paragraph('DOLARES', styles['Left-text']), Paragraph('0011 0418 0100018368 19', styles['Left-text']),
        #  Paragraph('011 418 000100018368 19', styles['Left-text'])],
    ]
    t_bank = Table(table_bank, colWidths=[_bts * 7 / 100, _bts * 7 / 100, _bts * 24 / 100, _bts * 24 / 100])
    style_bank = [
        # ('SPAN', (0, 1), (0, 2)),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
    ]
    t_bank.setStyle(TableStyle(style_bank))
    money = 'S/.'
    # if order_obj.coin == 'S':
    #     money = 'S/.'
    # elif order_obj.coin == 'D':
    #     money = '$'
    retention = ""
    value_r = ""
    # if order_bill_obj.is_retention:
    #     value_r = round(decimal.Decimal(_sub_total * int(order_bill_obj.percentage) / 100), 2)
    #     retention = "OPERACIÓN SUJETA A RETENCIÓN DEL I.G.V. TASA " + str(
    #         round(decimal.Decimal(order_bill_obj.percentage), 2)) + "%  = " + str(money) + str(value_r)
    # elif order_bill_obj.is_detraction:
    #     retention = "OPERACIÓN SUJETA A DETRACCION " + str(
    #         round(decimal.Decimal(order_bill_obj.percentage), 2)) + "%"
    total_col1 = [
        [t_bank],
        [Paragraph('OBSERVACION: ' + order_obj.observation.upper(), styles["Justify_Newgot"])],
        [Paragraph('SON: ' + numero_a_moneda(round(_total, 2), ),
                   styles["Justify_Newgot"])],
        # [Paragraph('GUÍA DE REMISIÓN TRANSPORTISTA: ' + str(order_obj.subsidiary.serial) + '-' + str(order_obj.correlative_sale),
        #            styles["Justify_Newgot"])],
        [Paragraph(str(retention),
                   styles["Justify_Newgot"])]
    ]
    total_col_1 = Table(total_col1, colWidths=[_bts * 63 / 100])
    style_table_col1 = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), -5),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),
    ]
    total_col_1.setStyle(TableStyle(style_table_col1))

    total_col2 = [
        [Paragraph('GRAVADA', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(valor_venta, 2)), styles["Right_Newgot"])],
        [Paragraph(_text, styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(_discount, 2)), styles["Right_Newgot"])],
        [Paragraph('I.G.V.(18.00 %)', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(igv, 2)), styles["Right_Newgot"])],
        [Paragraph('TOTAL', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(valor_venta + igv, 2)), styles["Right_Newgot"])],
    ]
    total_col_2 = Table(total_col2, colWidths=[_bts * 19 / 100, _bts * 14 / 100])

    style_table_col2 = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    total_col_2.setStyle(TableStyle(style_table_col2))

    total_ = [
        [total_col_1, total_col_2],
    ]
    total_page = Table(total_, colWidths=[_bts * 65 / 100, _bts * 35 / 100])
    style_table_page = [
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),  # three column
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # first column
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.red),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]
    total_page.setStyle(TableStyle(style_table_page))
    # -----------------

    footer_1 = [
        [Paragraph('Representación impresa de la ' + str(order_bill_obj.get_type_display()).upper() + ' ELECTRÓNICA, '
                                                                                                      'para ver el '
                                                                                                      'documento '
                                                                                                      'visita',
                   styles["Left-text"])],
        [Paragraph('https://4soluciones.pse.pe/20603890214', styles["Left-text"])],
        [Paragraph(
            'Emitido mediante un PROVEEDOR Autorizado por la SUNAT mediante Resolución de Intendencia No.034-005-0005315',
            styles["Left-text"])],
        [Paragraph('', styles["Left-text"])],
        [Paragraph('', styles["Left-text"])],
    ]
    f_1 = Table(footer_1, colWidths=[_bts * 80 / 100])

    style_f1 = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    f_1.setStyle(TableStyle(style_f1))

    # my_style_qr = [
    #     # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),   # all columns
    #     ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
    #     ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
    #     ('SPAN', (0, 0), (1, 0)),  # first row
    # ]
    # qr_ = Table([(qr_code('kldkdsjkdssd'), '')], colWidths=[_bts * 99 / 100, _bts * 1 / 100])
    # qr_.setStyle(TableStyle(my_style_qr))

    _footer = [
        [f_1, qr_code(datatable)],
    ]
    total_footer = Table(_footer, colWidths=[_bts * 80 / 100, _bts * 20 / 100])
    style_total_footer = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    total_footer.setStyle(TableStyle(style_total_footer))

    type_document = order_obj.orderbill.get_type_display().upper()

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=(8.3 * inch, 11.7 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title=str(order_bill_obj.get_type_display()).upper() + '-' + str(
                                str(order_obj.orderbill.n_receipt).zfill(4))
                            )
    dictionary = []
    dictionary.append(header_page)
    dictionary.append(OutputInvoiceGuide(count_row=count))
    dictionary.append(header2_page)
    dictionary.append(Spacer(1, 16))
    dictionary.append(header_detail)
    # dictionary.append(Paragraph(line, styles["Center_Newgot_title"]))
    dictionary.append(detail_body)
    dictionary.append(Spacer(1, 5))
    dictionary.append(total_page)
    # if cash_flow_set.last().type_payment == 'C':
    #     dictionary.append(credit_list)
    dictionary.append(Spacer(1, 5))
    dictionary.append(total_footer)
    # dictionary.append(Paragraph('www.electrical.com', styles["Center_Newgot"]))
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="{}.pdf"'.format(str(type_document) + ' ' +
                                                                             str(order_bill_obj.serial) + '-' + str(
        order_bill_obj.n_receipt))
    doc.build(dictionary)
    response.write(buff.getvalue())
    buff.close()
    return response


def print_orders_sales(request, start_date=None, end_date=None):
    _a4_horizontal = (8.3 * inch, 11.7 * inch)
    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    sum = 0
    sum_bills = 0
    sum_receipts = 0
    sum_tickets = 0

    total_cash = decimal.Decimal(0)
    total_credit = decimal.Decimal(0)
    total_deposit = decimal.Decimal(0)

    user_dict = {}

    # format_start_date = datetime.datetime(start_date)

    _bts = 8.3 * inch - 0.15 * inch - 0.15 * inch

    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
    order_set = Order.objects.filter(subsidiary_store=subsidiary_store_obj,
                                     create_at__date__range=[start_date, end_date], type='V',
                                     status__in=['P', 'A']).order_by('id')

    sum_sales = 0

    _tbl_header = (
    'REPORTE DE VENTAS DE LA SEDE ' + subsidiary_obj.name + ' DESDE ' + start_date + ' HASTA ' + end_date,)

    ana_c = Table([_tbl_header], colWidths=[_bts * 100 / 100])

    my_style_table_header = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # third column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')  # first column
        # ('LEFTPADDING', (2, 0), (2, 0), 180),
        # ('LEFTPADDING', (1, 0), (1, 0), 291),
        # ('BOTTOMPADDING', (0, 0), (3, 0), -20),
        # ('BACKGROUND',  (0, 0), (3, 0), colors.pink)
    ]
    ana_c.setStyle(TableStyle(my_style_table_header))

    td_title = (
        'TIPO', 'SERIE', 'NRO.', 'CLIENTE', 'USUARIO', 'TOTAL', 'FECHA ', 'PRODUCTO', 'UND.', 'CANT.',
        'PREC.', 'SUBTOT.')

    colwiths_table_title = [
        _bts * 5 / 100,  # TIPO
        _bts * 4 / 100,  # SERIE
        _bts * 6 / 100,  # NRO
        _bts * 15 / 100,  # CLIENTE
        _bts * 10 / 100,  # USUARIO
        _bts * 5 / 100,  # TOTAL
        _bts * 7 / 100,  # FECHA
        _bts * 28 / 100,  # PRODUCTO
        _bts * 5 / 100,  # UNIDAD
        _bts * 5 / 100,  # CANTIDAD
        _bts * 5 / 100,  # PRECIO
        _bts * 5 / 100,  # SUBTOTAL
    ]
    _rows = []
    _rows_users = []
    _rows.append(td_title)

    detail_style = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        # ('FONTNAME', (2, 1), (-5, -1), 'Square-Bold'),
        # ('BACKGROUND', (2, 1), (-5, -1), colors.blue),
        ('FONTNAME', (0, 0), (-1, 0), 'Square'),
        ('FONTNAME', (0, 0), (0, -1), 'Square'),
        # ('FONTSIZE', (0, 0), (0, -1), 10),
        ('FONTSIZE', (0, 0), (-1, 0), 9)
    ]

    y1 = 1
    y2 = 0
    ana_c3 = None
    for o in order_set:

        cash_id = ''
        cash_flow_set = CashFlow.objects.filter(order_id=o.id)
        if cash_flow_set.exists():
            cash_flow_obj = cash_flow_set.first()
            cash_id = cash_flow_obj.cash.id

        _order_detail = o.orderdetail_set.all()
        order_bill_obj = ''
        _correlative = o.correlative_sale
        type_bill = 'TICKET'
        _serial = o.subsidiary.serial
        order_bill_set = OrderBill.objects.filter(order=o.id)

        if order_bill_set.exists():
            order_bill_obj = order_bill_set.first()

            if order_bill_obj.type == '1':
                type_bill = 'FACTURA'
                _serial = order_bill_obj.serial
                _correlative = order_bill_obj.n_receipt
            elif order_bill_obj.type == '2':
                type_bill = 'BOLETA'
                _serial = order_bill_obj.serial
                _correlative = order_bill_obj.n_receipt

        number_details = 1

        if o.status != 'A':
            sum_sales += o.total
            number_details = o.orderdetail_set.all().count()

            key = o.user.id

            if key in user_dict:

                total_bills = 0
                total_receipts = 0
                total_tickets = 0
                user = user_dict[key]
                old_total = user.get('total_sold')
                old_total_bills = user.get('total_bills')
                old_total_receipts = user.get('total_receipts')
                old_total_tickets = user.get('total_tickets')

                order_bill_set = OrderBill.objects.filter(order=o.id)

                if order_bill_set.exists():
                    order_bill_obj = order_bill_set.first()
                    if order_bill_obj.type == '1':
                        total_bills = o.total
                    elif order_bill_obj.type == '2':
                        total_receipts = o.total
                else:
                    total_tickets = o.total

                user_dict[key]['total_bills'] = old_total_bills + total_bills
                user_dict[key]['total_receipts'] = old_total_receipts + total_receipts
                user_dict[key]['total_tickets'] = old_total_tickets + total_tickets
                user_dict[key]['total_sold'] = old_total + o.total

            else:
                user_dict[key] = {
                    'user_id': o.user.id,
                    'user_names': o.user.worker_set.last().employee.names,
                    'total_sold': o.total,
                    'total_bills': 0,
                    'total_receipts': 0,
                    'total_tickets': o.total
                }

        _pi = 0
        _pf = 0
        _c2 = 1
        y2 = y1 + number_details - 1
        _sum_total_multiply = round(decimal.Decimal(0), 2)
        if o.status != 'A':

            for od in o.orderdetail_set.all():
                _rows.append((
                    type_bill,
                    _serial,
                    str(_correlative).zfill(8),
                    Paragraph(o.client.names.upper(), styles["Center"]),
                    o.user.worker_set.last().employee.names.upper(),
                    o.total,
                    o.create_at.date().strftime("%d-%m-%Y"),
                    Paragraph(od.product.name.upper(), styles["Center"]),
                    od.unit.name,
                    int(od.quantity_sold),
                    od.price_unit,
                    od.multiply().quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN),
                ))

                _sum_total_multiply += od.multiply()

            sum = sum + _sum_total_multiply

            detail_style.append(('SPAN', (0, y1), (0, y2)))
            detail_style.append(('SPAN', (1, y1), (1, y2)))
            detail_style.append(('SPAN', (2, y1), (2, y2)))
            detail_style.append(('SPAN', (3, y1), (3, y2)))
            detail_style.append(('SPAN', (4, y1), (4, y2)))
            detail_style.append(('SPAN', (5, y1), (5, y2)))
            detail_style.append(('SPAN', (6, y1), (6, y2)))
            # detail_style.append(('SPAN', (7, y1), (7, y2)))
            if o.way_to_pay_type == 'D':
                detail_style.append(('BACKGROUND', (0, y1), (-1, y2), colors.lightgreen))
            elif o.way_to_pay_type == 'C':
                detail_style.append(('BACKGROUND', (0, y1), (-1, y2), colors.lightsteelblue))
            y1 = y2 + 1

            ana_c3 = Table(_rows, colWidths=colwiths_table_title)

            ana_c3.setStyle(TableStyle(detail_style))

            if order_bill_set.exists():
                order_bill_obj = order_bill_set.first()
                if order_bill_obj.type == '1':
                    sum_bills = sum_bills + _sum_total_multiply
                elif order_bill_obj.type == '2':
                    sum_receipts = sum_receipts + _sum_total_multiply
            else:
                sum_tickets += _sum_total_multiply
            if o.way_to_pay_type == 'E':
                total_cash = total_cash + _sum_total_multiply
            elif o.way_to_pay_type == 'D':
                total_deposit = total_deposit + _sum_total_multiply
            elif o.way_to_pay_type == 'C':
                total_credit = total_credit + _sum_total_multiply


        else:
            _rows.append((
                type_bill,
                _serial,
                str(_correlative).zfill(8),
                str('ANULADA'),
            ))

            detail_style.append(('SPAN', (0, y1), (0, y2)))
            detail_style.append(('SPAN', (1, y1), (1, y2)))
            detail_style.append(('SPAN', (2, y1), (2, y2)))
            detail_style.append(('SPAN', (3, y1), (7, y2)))
            # detail_style.append(('SPAN', (4, y1), (9, y2)))
            # detail_style.append(('SPAN', (5, y1), (5, y2)))
            # detail_style.append(('SPAN', (6, y1), (6, y2)))
            # detail_style.append(('SPAN', (7, y1), (7, y2)))

            detail_style.append(('BACKGROUND', (0, y1), (-1, y2), colors.indianred))

            y1 = y2 + 1

            ana_c3 = Table(_rows, colWidths=colwiths_table_title)

            ana_c3.setStyle(TableStyle(detail_style))

    colwiths_table_totals = [_bts * 35 / 100, _bts * 15 / 100, _bts * 50 / 100]
    _tbl_totals = [
        ['', 'SUMA TOTAL:    ' + 'S/ ' + str(decimal.Decimal(round(sum_sales, 2))), ''],
    ]
    ana_c4 = Table(_tbl_totals, colWidths=colwiths_table_totals)

    my_style_table_totals = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square-Bold'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (1, 0), (1, -1), 'MIDDLE'),  # first column
        # ('SPAN', (1, 0), (2, 0)),  # first row
        ('ALIGNMENT', (1, 0), (2, -1), 'CENTER'),  # second column
    ]
    ana_c4.setStyle(TableStyle(my_style_table_totals))

    my_style_table_user = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (1, 0), (1, -1), 'MIDDLE'),  # first column
        # ('SPAN', (1, 0), (2, 0)),  # first row
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # second column
        ('BACKGROUND', (0, 0), (4, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (4, 0), 'Square-Bold'),
    ]

    td_title_users = ('USUARIO', 'TOTAL \nVENTAS', 'TOTAL \nFACTURAS ', 'TOTAL \nBOLETAS', 'TOTAL \nTICKETS')

    _bts_2 = 5.3 * inch - 0.25 * inch - 0.25 * inch

    colwiths_table_user = [_bts_2 * 40 / 100,  # USER
                           _bts_2 * 15 / 100,  # MONTO TOTAL
                           _bts_2 * 15 / 100,  # TOTAL FACTURAS
                           _bts_2 * 15 / 100,  # TOTAL BOLETAS
                           _bts_2 * 15 / 100,  # TOTAL TICKETS
                           ]

    _rows_users.append(td_title_users)

    for u, v in user_dict.items():
        _rows_users.append((str(v.get('user_names')).upper(), v.get('total_sold'), v.get('total_bills'),
                            v.get('total_receipts'), v.get('total_tickets')))

    ana_c5 = Table(_rows_users, colWidths=colwiths_table_user)

    ana_c5.setStyle(TableStyle(my_style_table_user))

    td_title_totals = ('VENTA TOTAL', 'TOTAL CONTADO', 'TOTAL CREDITO', 'TOTAL DEPOSITO')

    colwiths_table_totals = [_bts_2 * 25 / 100,  # VENTA TOTAL
                             _bts_2 * 25 / 100,  # CONTADO
                             _bts_2 * 25 / 100,  # CREDITO
                             _bts_2 * 25 / 100,  # DEPOSITO
                             ]

    _table_totals = [
        ['VENTA TOTAL', 'TOTAL CONTADO', 'TOTAL CREDITO', 'TOTAL DEPOSITO'],
        [str(decimal.Decimal(round(sum, 2))), str(decimal.Decimal(round(total_cash, 2))),
         str(decimal.Decimal(round(total_credit, 2))), str(decimal.Decimal(round(total_deposit, 2)))]
    ]

    ana_c6 = Table(_table_totals, colWidths=colwiths_table_totals)
    ana_c6.setStyle(TableStyle(my_style_table_user))

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=(8.3 * inch, 11.7 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Reporte de Ventas')

    dictionary = []
    dictionary.append(ana_c)
    dictionary.append(Spacer(10, 10))
    dictionary.append(ana_c3)
    dictionary.append(Spacer(5, 5))
    dictionary.append(ana_c4)
    dictionary.append(Spacer(10, 10))
    dictionary.append(ana_c5)
    dictionary.append(Spacer(20, 20))
    dictionary.append(ana_c6)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="{}.pdf"'.format('Reporte de Ventas')
    doc.build(dictionary)
    response.write(buff.getvalue())
    buff.close()

    return response
