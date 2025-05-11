import requests

from .format_to_dates import utc_to_local
from .models import *
from .views_SUNAT import get_new_correlative
from ..comercial.models import Guide
from ..hrm.views import get_subsidiary_by_user

GRAPHQL_URL = "https://ng.tuf4ctur4.net.pe/graphql"
# GRAPHQL_URL = "http://192.168.1.80:9050/graphql"

tokens = {
    "20603890214": "gAAAAABoH8-CRbROAwEiA2258mrFryXlS5o3TJRtcW6fo1VAWt9I1zdUmB3Nun7eZLTc5TBGakxrd1ekG_ldmxhPqEoh_J2OTg==",
}


def send_bill_4_fact(order_id):  # FACTURA 4 FACT
    order_obj = Order.objects.get(id=int(order_id))
    serial = order_obj.subsidiary_store.subsidiary.serial
    correlative = get_new_correlative(serial, '1')
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj = order_obj.client
    client_name = str(client_obj.names).replace('"', "'")
    client_first_address = client_obj.clientaddress_set.first()
    client_address = str(client_first_address).replace('"', "'")
    client_document = client_obj.clienttype_set.filter(document_type_id='06').first()
    register_date = order_obj.create_at
    formatdate = register_date.strftime("%Y-%m-%d")
    hour_date = register_date.strftime("%H:%M:%S")

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
        _base_amount_v = float(round((base_amount / d.quantity_sold), 6))
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
            "precioBase": float(round(_base_amount_v, 6)),
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
                fechaVencimiento: "",
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


def send_receipt_4_fact(order_id):  # BOLETA 4 FACT
    order_obj = Order.objects.get(id=int(order_id))
    serial = order_obj.subsidiary_store.subsidiary.serial
    correlative = get_new_correlative(serial, '2')
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj = order_obj.client
    client_name = str(client_obj.names).replace('"', "'")
    client_address = ""
    if client_obj.clientaddress_set.first():
        client_address = str(client_obj.clientaddress_set.first().address).replace('"', "'")
    client_document = client_obj.clienttype_set.filter(document_type_id='01').first()
    register_date = utc_to_local(order_obj.create_at)
    formatdate = register_date.strftime("%Y-%m-%d")
    hour_date = register_date.strftime("%H:%M:%S")

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
                    fechaVencimiento: "",
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

