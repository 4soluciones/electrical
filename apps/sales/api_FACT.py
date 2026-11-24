import requests
from django.db.models import Max
from django.db.models.functions import Coalesce

from .format_to_dates import utc_to_local
from .models import *
from .views_SUNAT import get_new_correlative
from datetime import datetime, date
from ..comercial.models import Guide
from ..hrm.views import get_subsidiary_by_user

GRAPHQL_URL = "https://ng.tuf4ctur4.net.pe/graphql"
# GRAPHQL_URL = "http://192.168.1.80:9050/graphql"

tokens = {
    "20603890214": "gAAAAABoH8-CRbROAwEiA2258mrFryXlS5o3TJRtcW6fo1VAWt9I1zdUmB3Nun7eZLTc5TBGakxrd1ekG_ldmxhPqEoh_J2OTg==",
}


def get_sale_emission_parts(order_obj):
    register_date = order_obj.create_at
    if register_date:
        hour_date = register_date.strftime("%H:%M:%S")
        formatdate = register_date.strftime("%Y-%m-%d")
    else:
        hour_date = "12:00:00"
        formatdate = date.today().strftime("%Y-%m-%d")
    if order_obj.issue_date:
        formatdate = order_obj.issue_date.strftime("%Y-%m-%d")
    return formatdate, hour_date


def send_bill_4_fact(order_id, serial_suffix=None):  # FACTURA 4 FACT
    order_obj = Order.objects.get(id=int(order_id))
    serial = serial_suffix or order_obj.subsidiary_store.subsidiary.serial
    correlative = get_new_correlative(serial, '1')
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj = order_obj.client
    client_name = str(client_obj.names).replace('"', "'")
    client_first_address = client_obj.clientaddress_set.first()
    client_address = str(client_first_address).replace('"', "'")
    client_document = client_obj.clienttype_set.filter(document_type_id='06').first()
    formatdate, hour_date = get_sale_emission_parts(order_obj)

    items = []
    items_credit_graphql = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    _base_total_v = 0
    _base_amount_v = 0
    _igv = 0

    if order_obj.way_to_pay_type == 'C':
        description = f"{order_obj.pay_condition} Días"
        payment = 9
        credits_detail = PaymentFees.objects.filter(order=order_obj)

        credit = []
        for j, c in enumerate(credits_detail, start=1):
            credit.append({
                "cuota": str(j),
                "transaction_date": c.date.strftime("%Y-%m-%d"),
                "importe": round(float(c.amount), 2),
                "descripcion": description
            })

        items_credit_graphql = ", ".join(
            f"""{{
                transactionDate: "{item['transaction_date']}",
                amount: {item['importe']},
                description: "{item['descripcion']}"
            }}"""
            for item in credit
        )
        items_credit_graphql = f"[{items_credit_graphql}]"
    else:
        payment = 1

    for d in details:
        base_total = d.quantity_sold * d.price_unit  # 5 * 20 = 100
        base_amount = base_total / decimal.Decimal(1.1800)  # 100 / 1.18 = 84.75
        igv = base_total - base_amount  # 100 - 84.75 = 15.25
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv
        # _base_amount_v = float(round((base_amount / d.quantity_sold), 6))
        _base_amount_v = (base_amount / d.quantity_sold).quantize(decimal.Decimal("0.0000000001"))
        product_name = str(d.product.name).replace('"', "'")
        _unit = 'NIU'
        if d.unit.name == 'ZZ':
            _unit = 'ZZ'

        item = {
            "index": str(index),
            "codigoUnidad": str(_unit),
            "codigoProducto": "0000",
            "codigoSunat": "10000000",
            "producto": product_name,
            "cantidad": float(d.quantity_sold),
            # "precioBase": float(round(_base_amount_v, 6)),
            "precioBase": str(_base_amount_v),
            "tipoIgvCodigo": "10"
        }
        items.append(item)

    items_graphql = ", ".join(
        f"""{{  
               producto: "{item['producto']}", 
               cantidad: {item['cantidad']}, 
               precioBase: {item['precioBase']}, 
               codigoSunat: "{item['codigoSunat']}",
               codigoProducto: "{item['codigoProducto']}",
               codigoUnidad: "{item['codigoUnidad']}",                                            
               tipoIgvCodigo: "{item['tipoIgvCodigo']}" 
        }}"""
        for item in items
    )

    items_graphql = f"[{items_graphql}]"

    graphql_query = f"""
    mutation RegisterSale  {{
        registerSale(            
            cliente: {{
                razonSocialNombres: "{client_name}",
                numeroDocumento: "{client_document.document_number}",
                codigoTipoEntidad: 6,
                clienteDireccion: "{client_address}"
            }},
            venta: {{
                serie: "F{serial}",
                numero: "{int(correlative)}",
                fechaEmision: "{formatdate}",
                horaEmision: "{hour_date}",
                fechaVencimiento: "{formatdate}",
                monedaId: 1,                
                formaPagoId: {payment},
                totalGravada: {float(sub_total)},
                totalDescuentoGlobalPorcentaje: 0,
                totalDescuentoGlobal: 0,
                totalIgv: {float(igv_total)},
                totalExonerada: 0,
                totalInafecta: 0,
                totalImporte: {float(round(total, 2))},
                totalAPagar: {float(round(total, 2))},
                tipoDocumentoCodigo: "01",
                nota: " "
            }},
            items: {items_graphql}
            creditPay: {items_credit_graphql}
        ) {{
            message
            success
            operationId
        }}
    }}
    """
    # print(graphql_query)

    token = tokens.get("20603890214", "ID no encontrado")

    HEADERS = {
        "Content-Type": "application/json",
        "token": token
    }

    try:
        response = requests.post(GRAPHQL_URL, json={"query": graphql_query}, headers=HEADERS)
        response.raise_for_status()

        result = response.json()

        success = result.get("data", {}).get("registerSale", {}).get("success")

        if success:
            return {
                "success": success,
                "message": result.get("data", {}).get("registerSale", {}).get("message"),
                "operationId": result.get("data", {}).get("registerSale", {}).get("operationId"),
                "serie": "F" + serial,
                "numero": correlative,
                "tipo_de_comprobante": "1",
            }
        else:
            # Maneja el caso en que la operación no fue exitosa
            return {
                "success": False,
                "message": "La operación no fue exitosa, revise la venta e informe a Sistemas",
            }

    except requests.exceptions.RequestException as e:
        return {"error": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"error": "La respuesta no es un JSON válido"}


def send_receipt_4_fact(order_id, serial_suffix=None):  # BOLETA 4 FACT
    order_obj = Order.objects.get(id=int(order_id))
    serial = serial_suffix or order_obj.subsidiary_store.subsidiary.serial
    correlative = get_new_correlative(serial, '2')
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj = order_obj.client
    client_name = str(client_obj.names).replace('"', "'")
    client_address = ""
    if client_obj.clientaddress_set.first():
        client_address = str(client_obj.clientaddress_set.first().address).replace('"', "'")
    client_document = client_obj.clienttype_set.filter(document_type_id='01').first()
    formatdate, hour_date = get_sale_emission_parts(order_obj)

    items = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    _base_total_v = 0
    _base_amount_v = 0
    _igv = 0
    for d in details:
        base_total = d.quantity_sold * d.price_unit
        base_amount = base_total / decimal.Decimal(1.1800)
        igv = base_total - base_amount
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv
        _base_amount_v = float(round((base_amount / d.quantity_sold), 6))
        product_name = str(d.product.name).replace('"', "'")
        _unit = 'NIU'
        if d.unit.name == 'ZZ':
            _unit = 'ZZ'

        item = {
            "index": str(index),
            "codigoUnidad": _unit,
            "codigoProducto": "0000",
            "codigoSunat": "10000000",
            "producto": product_name,
            "cantidad": float(d.quantity_sold),
            "precioBase": float(round(_base_amount_v, 6)),
            "tipoIgvCodigo": "10"
        }
        items.append(item)

    items_graphql = ", ".join(
        f"""{{                     
                codigoUnidad: "{item['codigoUnidad']}", 
                codigoProducto: "{item['codigoProducto']}", 
                codigoSunat: "{item['codigoSunat']}", 
                producto: "{item['producto']}", 
                cantidad: {item['cantidad']}, 
                precioBase: {item['precioBase']}, 
                tipoIgvCodigo: "{item['tipoIgvCodigo']}" 
            }}"""
        for item in items
    )

    items_graphql = f"[{items_graphql}]"

    graphql_query = f"""
        mutation RegisterSale  {{
            registerSale(            
                cliente: {{
                    razonSocialNombres: "{client_name}",
                    numeroDocumento: "{client_document}",
                    codigoTipoEntidad: 1,
                    clienteDireccion: "{client_address}"
                }},
                venta: {{
                    serie: "B{serial}",
                    numero: "{int(correlative)}",
                    fechaEmision: "{formatdate}",
                    horaEmision: "{hour_date}",
                    fechaVencimiento: "{formatdate}",
                    monedaId: 1,                
                    formaPagoId: 1,
                    totalGravada: {float(sub_total)},
                    totalDescuentoGlobalPorcentaje: 0,
                    totalDescuentoGlobal: 0,
                    totalIgv: {float(igv_total)},
                    totalExonerada: 0,
                    totalInafecta: 0,
                    totalImporte: {float(round(total, 2))},
                    totalAPagar: {float(round(total, 2))},
                    tipoDocumentoCodigo: "03",
                    nota: " "
                }},
                items: {items_graphql}
            ) {{
                message
                success
                operationId
            }}
        }}
        """

    # print(graphql_query)

    token = tokens.get("20603890214", "ID no encontrado")

    HEADERS = {
        "Content-Type": "application/json",
        "token": token
    }

    try:
        response = requests.post(GRAPHQL_URL, json={"query": graphql_query}, headers=HEADERS)
        response.raise_for_status()

        result = response.json()

        success = result.get("data", {}).get("registerSale", {}).get("success")

        if success:
            return {
                "success": success,
                "message": result.get("data", {}).get("registerSale", {}).get("message"),
                "operationId": result.get("data", {}).get("registerSale", {}).get("operationId"),
                "serie": "B" + serial,
                "numero": correlative,
                "tipo_de_comprobante": "2",
            }
        else:
            # Maneja el caso en que la operación no fue exitosa
            return {
                "success": False,
                "message": "La operación no fue exitosa",
            }

    except requests.exceptions.RequestException as e:
        return {"error": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"error": "La respuesta no es un JSON válido"}


def number_note(serial=None):
    number = CreditNote.objects.filter(serial=serial).aggregate(
        r=Coalesce(Max('correlative'), 0)).get('r')
    return number + 1


def _safe_fact_text(value):
    return str(value or '').replace('\\', ' ').replace('"', "'").replace('\n', ' ').strip()


def product_description_with_serials(product_name, detail):
    """
    Arma la descripción del ítem para el facturador.
    Si el detalle tiene series seleccionadas, las agrega entre paréntesis:
    PRODUCTO (SERIE1, SERIE2)
    """
    description = _safe_fact_text(str(product_name).upper())
    serial_ids = detail.get('serials') or []
    serial_numbers = []

    id_list = []
    for sid in serial_ids:
        try:
            id_list.append(int(sid))
        except (TypeError, ValueError):
            continue

    if id_list:
        found = {
            s.id: s.serial_number
            for s in ProductSerial.objects.filter(id__in=id_list)
            if s.serial_number
        }
        for sid in id_list:
            number = found.get(sid)
            if number:
                serial_numbers.append(_safe_fact_text(str(number).upper()))

    if not serial_numbers:
        for number in (detail.get('serialNumbers') or []):
            if number:
                serial_numbers.append(_safe_fact_text(str(number).upper()))

    if serial_numbers:
        description = f"{description} ({', '.join(serial_numbers)})"
    return description


def send_credit_note_fact(pk, details, motive):
    order_obj = Order.objects.get(id=int(pk))
    serial = str(order_obj.voucher_type) + "N01"
    correlative = number_note(serial)
    client_obj = order_obj.client
    # date_voucher = datetime.now().strftime("%d-%m-%Y")
    items = []
    index = 1
    sub_total = 0
    total = 0
    for d in details:
        if d['quantityReturned']:
            product_id = int(d['productID'])
            product_obj = Product.objects.get(id=product_id)
            description = product_description_with_serials(product_obj.name, d)
            total_item_igv = decimal.Decimal(d['quantityReturned']) * decimal.Decimal(d['price'])
            price_igv = decimal.Decimal(d['price'])
            price_sin_igv = price_igv / decimal.Decimal(1.1800)
            total_item_sin_igv = total_item_igv / decimal.Decimal(1.1800)
            igv_item = total_item_igv - total_item_sin_igv
            total = total + total_item_igv
            sub_total = sub_total + total_item_sin_igv
            _unit = 'NIU'
            if d['unit'] == 'ZZ':
                _unit = 'ZZ'

            item = {
                "index": str(index),
                "codigoUnidad": str(_unit),
                "codigoProducto": str(product_obj.code),
                "codigoSunat": "10000000",
                "producto": description,
                "cantidad": round(float(d['quantityReturned']), 4),
                "precioBase": round(price_sin_igv, 6),
                "tipoIgvCodigo": "10"
            }
            items.append(item)

    items_graphql = ", ".join(
        f"""{{  
                   producto: "{item['producto']}", 
                   cantidad: {item['cantidad']}, 
                   precioBase: {item['precioBase']}, 
                   codigoSunat: "{item['codigoSunat']}",
                   codigoProducto: "{item['codigoProducto']}",
                   codigoUnidad: "{item['codigoUnidad']}",                                            
                   tipoIgvCodigo: "{item['tipoIgvCodigo']}" 
            }}"""
        for item in items
    )

    items_graphql = f"[{items_graphql}]"

    _type_document = '01' if order_obj.voucher_type == 'B' else '06'

    client_type = ClientType.objects.get(client=client_obj, document_type=_type_document)
    client_names = str(client_obj.names).replace('"', "'")
    client_document = client_type.document_number
    client_document_type = int(client_type.document_type.id)

    client_first_address = client_obj.clientaddress_set.first()
    client_address = str(client_first_address).replace('"', "'")

    total_engraved = decimal.Decimal(sub_total)
    total_invoice = total_engraved * decimal.Decimal(1.1800)
    total_igv = total_invoice - total_engraved

    formatdate = datetime.now().strftime("%Y-%m-%d")
    hour_date = datetime.now().strftime("%H:%M:%S")

    type_document_code = ''

    order_bill_obj = OrderBill.objects.get(order=order_obj)

    if order_bill_obj.type == '2':
        type_document_code = '03'
    if order_bill_obj.type == '1':
        type_document_code = '01'

    graphql_query = f"""
        mutation RegisterCreditNote  {{
            registerCreditNote(            
                client: {{
                    razonSocialNombres: "{client_names}",
                    numeroDocumento: "{client_document}",
                    codigoTipoEntidad: {client_document_type},
                    clienteDireccion: "{client_address}"
                }},
                creditNote: {{
                    serie: "{serial}",
                    numero: "{correlative}",
                    fechaEmision: "{formatdate}",
                    horaEmision: "{hour_date}",
                    fechaVencimiento: "{formatdate}",
                    monedaId: 1,                
                    formaPagoId: 1,
                    totalGravada: {float(total_engraved)},
                    totalDescuentoGlobalPorcentaje: 0,
                    totalDescuentoGlobal: 0,
                    totalIgv: {float(total_igv)},
                    totalExonerada: 0,
                    totalInafecta: 0,
                    totalImporte: {float(round(total_invoice, 2))},
                    totalAPagar: {float(round(total_invoice, 2))},
                    tipoDocumentoCodigo: "07",
                    nota: "",
                    motiveCreditNote: "{motive}"
                }},
                relatedDocuments: {{
                    serial: "{str(order_bill_obj.serial)}"      
                    number: "{str(order_bill_obj.n_receipt)}"      
                    codeTypeDocument: "{str(type_document_code)}"      
                }},
                items: {items_graphql}
            ) {{
                message
                error
                operationId
            }}
        }}
        """
    # print(graphql_query)

    token = tokens.get("20603890214", "ID no encontrado")

    HEADERS = {
        "Content-Type": "application/json",
        "token": token
    }

    try:
        response = requests.post(GRAPHQL_URL, json={"query": graphql_query}, headers=HEADERS)
        response.raise_for_status()

        result = response.json()

        success = not result.get("data", {}).get("registerCreditNote", {}).get("error")

        if success:
            operation_id = result.get("data", {}).get("registerCreditNote", {}).get("operationId")
            enlace_pdf = f'https://ng.tuf4ctur4.net.pe/operations/print_credit_note/{operation_id}/'
            # enlace_pdf = f'http://192.168.1.80:9050/operations/print_credit_note/{operation_id}/'
            note_total = total_invoice
            return {
                "success": success,
                'tipo_de_comprobante': '3',
                "message": result.get("data", {}).get("registerCreditNote", {}).get("message"),
                'serial': str(serial),
                'correlative': correlative,
                'enlace_del_pdf': enlace_pdf,
                'note_total': note_total,
                'note_description': f'La Nota de Crédito numero {serial}-{correlative}, ha sido aceptado'
            }
        else:
            return {
                "success": False,
                "message": "La operación no fue exitosa, revise la venta e informe a Sistemas",
                "error": result.get("data", {}).get("registerCreditNote", {}).get("error"),
            }

    except requests.exceptions.RequestException as e:
        return {"error": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"error": "La respuesta no es un JSON válido"}


def annul_invoice(order_id):
    order_bill_obj = OrderBill.objects.get(order_id=int(order_id))
    correlative = order_bill_obj.n_receipt
    serial = order_bill_obj.serial

    variables = {
        "correlative": correlative,
        "serial": serial
    }

    mutation = """
    mutation AnnulInvoice($correlative: Int!, $serial: String!) {
        annulInvoice(correlative: $correlative, serial: $serial) {
            message
            success
        }
    }
    """

    token = tokens.get("20603890214", "ID no encontrado")

    HEADERS = {
        "Content-Type": "application/json",
        "token": token
    }

    # print("Enviando mutación GraphQL:")
    # print("Query:", mutation)
    # print("Variables:", variables)
    # print("Headers:", HEADERS)

    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": mutation, "variables": variables},
            headers=HEADERS
        )
        response.raise_for_status()

        result = response.json()

        data = result.get("data", {}).get("annulInvoice")

        if data and data.get("success"):
            return {
                "success": True,
                "message": data.get("message"),
            }
        else:
            return {
                "success": False,
                "message": data.get("message") if data else "No se obtuvo respuesta del servidor.",
            }

    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"success": False, "message": "La respuesta no es un JSON válido"}


def _guide_text(value):
    text = '' if value is None else str(value)
    return text.replace('\\', ' ').replace('"', "'").replace('\n', ' ').replace('\r', ' ').strip()


DEVOLUCION_RUC_MESSAGE = (
    'Para el motivo DEVOLUCIÓN el destinatario tiene que ser una empresa con RUC.'
)


def return_guide_recipient_error(document_number, document_type='6'):
    """Motivo 06: SUNAT exige que el destinatario sea una empresa identificada con RUC."""
    if str(document_type or '').zfill(2) != '06':
        return DEVOLUCION_RUC_MESSAGE
    ruc = ''.join(ch for ch in str(document_number or '') if ch.isdigit())
    if len(ruc) != 11 or not ruc.startswith('20') or not _valid_company_ruc(ruc):
        return DEVOLUCION_RUC_MESSAGE
    return None


def _valid_company_ruc(ruc):
    factors = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    total = sum(int(ruc[index]) * factors[index] for index in range(10))
    check = 11 - (total % 11)
    if check == 10:
        check = 0
    elif check == 11:
        check = 1
    return check == int(ruc[10])


def _send_return_guide_fact(guide_obj, return_guide):
    """Envia una guia de remision por devolucion con el mismo registro SUNAT de las guias de venta."""
    supplier = return_guide.supplier
    date = guide_obj.guide_date
    date_transfer = guide_obj.guide_transfer
    formatdate = date.strftime("%Y-%m-%d")
    formatdate_hour = date.strftime("%H:%M")
    formatdate_transfer = date_transfer.strftime("%Y-%m-%d")

    client_names = _guide_text((supplier.business_name or supplier.name or '').upper())
    client_document = _guide_text(supplier.ruc)
    recipient_error = return_guide_recipient_error(client_document, '6')
    if recipient_error:
        return {"success": False, "message": recipient_error}
    client_address = _guide_text(guide_obj.guide_destiny_address or supplier.address)
    client_phone = _guide_text(supplier.phone)

    items = []
    for detail in return_guide.items.select_related('product', 'unit'):
        quantity_sent = decimal.Decimal(detail.quantity or 0)
        if quantity_sent <= 0:
            continue
        unit_price = decimal.Decimal(detail.price_unit or 0)
        if unit_price <= 0:
            product_detail = detail.product.productdetail_set.filter(is_enabled=True).first()
            unit_price = decimal.Decimal(product_detail.price_purchase if product_detail else '0.01')
        if unit_price <= 0:
            unit_price = decimal.Decimal('0.01')
        base_total = quantity_sent * unit_price
        base_amount = base_total / decimal.Decimal('1.1800')
        product_name = _guide_text(detail.product.name)
        if detail.serial_number:
            product_name = _guide_text('{} SERIE {}'.format(detail.product.name, detail.serial_number))
        items.append({
            "producto": product_name,
            "cantidad": float(quantity_sent),
            "precioBase": float(round(base_amount / quantity_sent, 6)),
            "codigoSunat": "10000000",
            "codigoProducto": _guide_text(detail.product.code or "0000"),
            "codigoUnidad": "NIU",
            "tipoIgvCodigo": "10",
        })

    if not items:
        return {"success": False, "message": "La guia no tiene productos para enviar."}

    items_graphql = ", ".join(
        f"""{{
               producto: "{item['producto']}",
               cantidad: {item['cantidad']},
               precioBase: {item['precioBase']},
               codigoSunat: "{item['codigoSunat']}",
               codigoProducto: "{item['codigoProducto']}",
               codigoUnidad: "{item['codigoUnidad']}",
               tipoIgvCodigo: "{item['tipoIgvCodigo']}"
        }}"""
        for item in items
    )
    items_graphql = f"[{items_graphql}]"

    guide_mode = "01" if guide_obj.guide_modality_transport == "1" else "02"
    related_date = formatdate
    if return_guide.purchase_id and return_guide.purchase.purchase_date:
        related_date = return_guide.purchase.purchase_date.strftime("%Y-%m-%d")

    graphql_query = f"""
    mutation RegisterGuide {{
        registerGuide(
            client: {{
                razonSocialNombres: "{client_names}",
                numeroDocumento: "{client_document}",
                codigoTipoEntidad: 6,
                clienteDireccion: "{client_address}",
                clienteTelefono: "{client_phone}"
            }},
            guide: {{
                serial: "{_guide_text(guide_obj.guide_serial)}",
                number: "{guide_obj.guide_number}",
                guideModeTransfer: "{guide_mode}",
                guideReasonTransfer: "06",
                note: "{_guide_text(guide_obj.observation)}",
                emitDate: "{formatdate}",
                emitHour: "{formatdate_hour}"
            }},
            transportation: {{
                transferDate: "{formatdate_transfer}",
                totalWeight: "{guide_obj.guide_weight}",
                quantityPackages: "{guide_obj.guide_package}"
            }},
            points: {{
                guideOriginSerial: "",
                guideOriginAddress: "{_guide_text(guide_obj.guide_origin_address)}",
                guideOriginDistrictId: "{_guide_text(guide_obj.guide_origin)}",
                guideArrivalSerial: "",
                guideArrivalAddress: "{_guide_text(guide_obj.guide_destiny_address)}",
                guideArrivalDistrictId: "{_guide_text(guide_obj.guide_destiny)}"
            }},
            carrier: {{
                transportationCompanyDocumentType: "6",
                transportationCompanyDocumentNumber: "{_guide_text(guide_obj.guide_carrier_document)}",
                transportationCompanyNames: "{_guide_text(guide_obj.guide_carrier_names)}",
                transportationCompanyMtcRegistrationNumber: "{_guide_text(guide_obj.guide_register_mtc)}",
                mainDriverDocumentNumber: "{_guide_text(guide_obj.guide_driver_dni)}",
                mainDriverNames: "{_guide_text(guide_obj.guide_driver_full_name).upper()}",
                mainDriverLicense: "{_guide_text(guide_obj.guide_driver_license).upper()}",
                mainVehicleLicensePlate: "{_guide_text(guide_obj.guide_truck)}"
            }},
            items: {items_graphql},
            relatedDocuments: {{
                tipoDocumentoCodigo: "{_guide_text(return_guide.related_document_type or '01')}",
                serie: "{_guide_text(return_guide.related_document_serial)}",
                numero: "{_guide_text(return_guide.related_document_number)}",
                fechaEmision: "{related_date}"
            }}
        ) {{
            message
            error
            operationId
        }}
    }}
    """

    token = tokens.get("20603890214", "ID no encontrado")
    headers = {
        "Content-Type": "application/json",
        "token": token
    }

    try:
        response = requests.post(GRAPHQL_URL, json={"query": graphql_query}, headers=headers)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as exc:
        return {"success": False, "message": "Error en la solicitud: {}".format(exc)}
    except ValueError:
        return {"success": False, "message": "La respuesta no es un JSON valido"}

    if result.get("errors"):
        first = result["errors"][0] if result["errors"] else {}
        return {"success": False, "message": first.get("message") or "SUNAT rechazo el envio."}

    data = result.get("data", {}).get("registerGuide") or {}
    if data.get("error"):
        return {
            "success": False,
            "message": data.get("message") or "SUNAT rechazo la guia.",
            "error": data.get("error"),
        }
    return {
        "success": True,
        "message": data.get("message"),
        "operationId": data.get("operationId"),
        "serie": "G" + str(guide_obj.guide_serial or ""),
        "numero": guide_obj.guide_number,
    }


def send_guide_fact(guide_id):
    guide_obj = Guide.objects.get(id=guide_id)
    order_obj = Order.objects.filter(guide=guide_obj).first()
    if order_obj is None:
        from apps.buys.models import ReturnGuide
        return_guide = ReturnGuide.objects.filter(guide=guide_obj).select_related(
            'supplier', 'purchase').prefetch_related('items__product', 'items__unit').first()
        if return_guide is not None:
            return _send_return_guide_fact(guide_obj, return_guide)
        return {"success": False, "message": "La guia no tiene una orden asociada."}
    correlative = order_obj.orderbill.n_receipt
    date_transfer = guide_obj.guide_transfer
    date = guide_obj.guide_date
    subsidiary_obj = guide_obj.subsidiary
    client_obj = order_obj.client

    # Get client information
    client_type_document = '6'
    client_nro_document = client_obj.clienttype_set.last().document_number
    client_names = client_obj.names
    client_address = client_obj.clientaddress_set.last().address
    client_email = client_obj.email

    if guide_obj.guide_motive == '04':
        client_type_document = '6'
        client_nro_document = subsidiary_obj.ruc
        client_names = subsidiary_obj.business_name.upper()
        client_address = subsidiary_obj.address.upper()
        client_email = subsidiary_obj.email

    if str(guide_obj.guide_motive) == '06':
        recipient_error = return_guide_recipient_error(client_nro_document, client_type_document)
        if recipient_error:
            return {"success": False, "message": recipient_error}

    # Format dates
    formatdate = date.strftime("%Y-%m-%d")
    formatdate_hour = date.strftime("%H:%M")
    formatdate_transfer = date_transfer.strftime("%Y-%m-%d")

    # Get items
    items = []
    for d in OrderDetail.objects.filter(order=order_obj):
        quantity_sent = decimal.Decimal(d.quantity_sold)
        base_total = quantity_sent * d.price_unit
        base_amount = base_total / decimal.Decimal(1.1800)
        product_name = str(d.product.name).replace('"', "'")
        item = {
            "producto": product_name,
            "cantidad": float(quantity_sent),
            "precioBase": float(round(base_amount / quantity_sent, 6)),
            "codigoSunat": "10000000",
            "codigoProducto": str(d.product.code) if d.product.code else "0000",
            "codigoUnidad": "NIU",
            "tipoIgvCodigo": "10"
        }
        items.append(item)

    # Format items for GraphQL
    items_graphql = ", ".join(
        f"""{{  
               producto: "{item['producto']}", 
               cantidad: {item['cantidad']}, 
               precioBase: {item['precioBase']}, 
               codigoSunat: "{item['codigoSunat']}",
               codigoProducto: "{item['codigoProducto']}",
               codigoUnidad: "{item['codigoUnidad']}",                                            
               tipoIgvCodigo: "{item['tipoIgvCodigo']}" 
        }}"""
        for item in items
    )
    items_graphql = f"[{items_graphql}]"

    # Determine guide mode and reason
    guide_mode = "01" if guide_obj.guide_modality_transport == "1" else "02"
    guide_reason = guide_obj.guide_motive

    # Build GraphQL mutation
    graphql_query = f"""
    mutation RegisterGuide {{
        registerGuide(
            client: {{
                razonSocialNombres: "{client_names}",
                numeroDocumento: "{client_nro_document}",
                codigoTipoEntidad: {client_type_document},
                clienteDireccion: "{client_address}",
                clienteTelefono: "{client_obj.phone if client_obj.phone else ''}"
            }},
            guide: {{
                serial: "{guide_obj.guide_serial}",
                number: "{guide_obj.guide_number}",
                guideModeTransfer: "{guide_mode}",
                guideReasonTransfer: "{guide_reason}",
                note: "{guide_obj.observation}",
                emitDate: "{formatdate}",
                emitHour: "{formatdate_hour}"
            }},
            transportation: {{
                transferDate: "{formatdate_transfer}",
                totalWeight: "{guide_obj.guide_weight}",
                quantityPackages: "{guide_obj.guide_package}"
            }},
            points: {{
                guideOriginSerial: "",
                guideOriginAddress: "{guide_obj.guide_origin_address}",
                guideOriginDistrictId: "{guide_obj.guide_origin}",
                guideArrivalSerial: "",
                guideArrivalAddress: "{guide_obj.guide_destiny_address}",
                guideArrivalDistrictId: "{guide_obj.guide_destiny}"
            }},
            carrier: {{
                transportationCompanyDocumentType: "6",
                transportationCompanyDocumentNumber: "{guide_obj.guide_carrier_document}",
                transportationCompanyNames: "{guide_obj.guide_carrier_names}",
                transportationCompanyMtcRegistrationNumber: "",
                mainDriverDocumentNumber: "{guide_obj.guide_driver_dni}",
                mainDriverNames: "{guide_obj.guide_driver_full_name.upper()}",
                mainDriverLicense: "{guide_obj.guide_driver_license.upper()}",
                mainVehicleLicensePlate: "{guide_obj.guide_truck}"
            }},
            items: {items_graphql},
            relatedDocuments: {{
                tipoDocumentoCodigo: "01",
                serie: "F{order_obj.subsidiary_store.subsidiary.serial}",
                numero: "{correlative}",
                fechaEmision: "{formatdate}"
            }}
        ) {{
            message
            error
            operationId
        }}
    }}
    """
    print(graphql_query)

    token = tokens.get("20603890214", "ID no encontrado")

    HEADERS = {
        "Content-Type": "application/json",
        "token": token
    }

    try:
        response = requests.post(GRAPHQL_URL, json={"query": graphql_query}, headers=HEADERS)
        response.raise_for_status()

        result = response.json()

        success = not result.get("data", {}).get("registerGuide", {}).get("error")

        if success:
            return {
                "success": success,
                "message": result.get("data", {}).get("registerGuide", {}).get("message"),
                "operationId": result.get("data", {}).get("registerGuide", {}).get("operationId"),
                "serie": "G" + guide_obj.guide_serial,
                "numero": guide_obj.guide_number,
            }
        else:
            return {
                "success": False,
                "message": result.get("data", {}).get("registerGuide", {}).get("message"),
                "error": result.get("data", {}).get("registerGuide", {}).get("error"),
            }

    except requests.exceptions.RequestException as e:
        return {"error": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"error": "La respuesta no es un JSON válido"}