from django.shortcuts import render
from django.views.generic import TemplateView, View, CreateView, UpdateView
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from http import HTTPStatus
from .models import *
from apps.hrm.models import Subsidiary, Worker, Establishment
from django.template import loader, Context
from django.contrib.auth.models import User
from apps.hrm.views import get_subsidiary_by_user
from apps.sales.views import kardex_input, kardex_ouput, kardex_initial, calculate_minimum_unit, ProductSerial
import json
import decimal
import re
from datetime import datetime
from ..sales.models import Product, Unit, Supplier, SubsidiaryStore, \
    ProductStore, ProductDetail, Kardex, ProductBrand, MoneyChange, TransactionPayment, ProductSerial
from django.core import serializers
from django.db.models import Min, Sum, Max, Q, Prefetch, Subquery, OuterRef, Value

from ..sales.views_SUNAT import query_api_amigo, query_api_facturacioncloud, query_api_money, query_apis_net_money, \
    query_apis_net_dni_ruc
from django.db import transaction, IntegrityError


class Home(TemplateView):
    template_name = 'buys/home.html'


class PurchaseStoreError(Exception):
    """Error de negocio al asignar una compra al almacen.

    Se lanza DENTRO de un ``transaction.atomic()`` para que la transaccion se
    revierta por completo. Nunca se debe hacer ``return`` dentro del bloque
    ``atomic()``: en ese caso Django confirma los cambios ya escritos.
    """


def purchase_form(request):
    # form_obj = FormGuide()
    # programmings = Programming.objects.filter(status__in=['P']).order_by('id')
    supplier_obj = Supplier.objects.all()
    product_obj = Product.objects.all()
    unitmeasurement_obj = Unit.objects.all()

    return render(request, 'buys/purchase_form.html', {
        # 'form': form_obj,
        'supplier_obj': supplier_obj,
        'unitmeasurement_obj': unitmeasurement_obj,
        'product_obj': product_obj,
        # 'list_detail_purchase': get_employees(need_rendering=False),
    })


def get_buy_list(request):
    # form_obj = FormGuide()
    # programmings = Programming.objects.filter(status__in=['P']).order_by('id')
    supplier_obj = Supplier.objects.all()
    product_obj = Product.objects.all()
    unitmeasurement_obj = Unit.objects.all()
    my_date = datetime.now()
    formatdate = my_date.strftime("%Y-%m-%d")
    return render(request, 'buys/buy_list.html', {
        'supplier_obj': supplier_obj,
        'unitmeasurement_obj': unitmeasurement_obj,
        'product_obj': product_obj,
        'choices_payments': TransactionPayment._meta.get_field('type').choices,
        'choices_payments_purchase': Purchase._meta.get_field('type_pay').choices,
        'formatdate': formatdate,
    })


def get_buy_return(request):
    supplier_obj = Supplier.objects.all()
    product_obj = Product.objects.all()
    unitmeasurement_obj = Unit.objects.all()
    my_date = datetime.now()
    formatdate = my_date.strftime("%Y-%m-%d")
    return render(request, 'buys/buy_return.html', {
        'supplier_obj': supplier_obj,
        'unitmeasurement_obj': unitmeasurement_obj,
        'product_obj': product_obj,
        'formatdate': formatdate,
    })


def get_report_buy_return(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'buys/report_buy_return.html', {'formatdate': formatdate, })
    elif request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))

        purchase_return_set = PurchaseReturn.objects.filter(
            purchase_date__range=[start_date, end_date]
        ).order_by('-purchase_date', '-id')

        if subsidiary_obj is not None:
            purchase_return_set = purchase_return_set.filter(subsidiary=subsidiary_obj)

        if not purchase_return_set.exists():
            data = {'error': 'No hay devoluciones de compra registradas en el rango de fechas seleccionado'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        return JsonResponse({
            'grid': get_dict_buy_return(purchase_return_set, start_date, end_date),
        }, status=HTTPStatus.OK)


def get_dict_buy_return(purchase_return_set, start_date, end_date):
    tpl = loader.get_template('buys/report_buy_return_grid.html')
    context = ({
        'purchase_return_set': purchase_return_set,
        'start_date': start_date,
        'end_date': end_date,
    })
    return tpl.render(context)


@csrf_exempt
def save_purchase_return(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        purchase_return_request = request.GET.get('purchase_return', '')
        data_purchase_return = json.loads(purchase_return_request)

        invoice = str(data_purchase_return["Invoice"])
        provider_id = str(data_purchase_return["ProviderId"])
        date = str(data_purchase_return["Date"])
        type_bill = str(data_purchase_return["Type_Bill"])

        base_total = decimal.Decimal(data_purchase_return["Base_Total"])
        igv_total = decimal.Decimal(data_purchase_return["Igv_Total"])
        total_document = decimal.Decimal(data_purchase_return["Total_Document"])

        supplier_obj = Supplier.objects.get(id=int(provider_id))

        purchase_return_obj = PurchaseReturn(
            supplier=supplier_obj,
            purchase_date=date,
            bill_number=invoice,
            type_bill=type_bill,
            user=user_obj,
            subsidiary=subsidiary_obj,
            base_total_purchase=base_total,
            igv_total_purchase=igv_total,
            total_purchase=total_document
        )
        purchase_return_obj.save()

        for detail in data_purchase_return['Details']:
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)

            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)

            quantity = decimal.Decimal(detail['Quantity'])
            price = decimal.Decimal(detail['Price'])
            price_base = decimal.Decimal(detail['Price_Without_Igv'])
            total_detail = decimal.Decimal(detail['Total'])

            serial = str(detail['Serial'])

            purchase_return_detail_obj = PurchaseReturnDetail(
                purchase=purchase_return_obj,
                product=product_obj,
                quantity=quantity,
                unit=unit_obj,
                price_unit=price,
                total_detail=total_detail,
            )
            purchase_return_detail_obj.save()

            #  GUARDANDO EN EL KARDEX
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category__in=['V'])
            unit_min_detail_product = ProductDetail.objects.get(product=product_obj,
                                                                unit=unit_obj).quantity_minimum

            product_store_set = ProductStore.objects.filter(product=product_obj,
                                                            subsidiary_store=subsidiary_store_obj)

            if product_store_set.exists():
                product_store_obj = product_store_set.last()
                product_serial_set = ProductSerial.objects.filter(serial_number=serial)
                if product_serial_set.exists():
                    for s in product_serial_set:
                        s.product_store = product_store_obj
                        s.status = 'D'
                        s.save()
                kardex_ouput(product_store_obj.id, decimal.Decimal(unit_min_detail_product) * quantity, price=price,
                             purchase_return_detail=purchase_return_detail_obj)
        return JsonResponse({
            'message': 'Devolución de Compra Registrada Correctamente',
        }, status=HTTPStatus.OK)


def _dec(valor, defecto=0):
    """Convierte a Decimal tolerando float, int, '' , coma decimal y None.

    Decimal(float) conserva la expansion binaria exacta (11.8 -> 11.8000000000000007),
    por eso se pasa siempre por str().
    """
    if valor is None or valor == '':
        return decimal.Decimal(defecto)
    if isinstance(valor, decimal.Decimal):
        return valor
    texto = str(valor).strip().replace(',', '.')
    if texto == '':
        return decimal.Decimal(defecto)
    try:
        return decimal.Decimal(texto)
    except (decimal.InvalidOperation, ValueError):
        return decimal.Decimal(defecto)


def _clean_serials(raw_serials, quantity=None, product_name=''):
    """Normaliza y valida la lista de series de un detalle de compra.

    Devuelve la lista de series unicas (descartando las vacias).
    Lanza ValueError si hay series repetidas o si superan la cantidad comprada.
    """
    cleaned = []
    seen = set()
    for raw in raw_serials or []:
        if isinstance(raw, dict):
            value = raw.get('Serial', '') or ''
        else:
            value = raw or ''
        value = str(value).strip()
        if not value:
            continue
        key = value.upper()
        if key in seen:
            raise ValueError('EL PRODUCTO "{}" TIENE SERIES REPETIDAS: {}'.format(product_name, value))
        seen.add(key)
        cleaned.append(value)

    if quantity is not None and cleaned:
        max_serials = int(decimal.Decimal(str(quantity)).to_integral_value(rounding=decimal.ROUND_CEILING))
        if len(cleaned) > max_serials:
            raise ValueError(
                'EL PRODUCTO "{}" TIENE {} SERIES PERO LA CANTIDAD COMPRADA ES {}. '
                'NO SE PUEDEN REGISTRAR MAS SERIES QUE UNIDADES COMPRADAS.'.format(
                    product_name, len(cleaned), max_serials)
            )
    return cleaned


def _serials_already_registered(serials, exclude_ids=None):
    """Devuelve un dict {serie normalizada: ProductSerial} de las series ya existentes en el sistema."""
    normalized = set()
    for value in serials or []:
        value = str(value or '').strip().upper()
        if value:
            normalized.add(value)
    if not normalized:
        return {}

    query = Q()
    for value in normalized:
        query |= Q(serial_number__iexact=value)

    product_serial_set = ProductSerial.objects.filter(query)
    if exclude_ids:
        product_serial_set = product_serial_set.exclude(id__in=list(exclude_ids))

    return {str(s.serial_number).strip().upper(): s for s in product_serial_set}


@csrf_exempt
def save_purchase(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        purchase_request = request.GET.get('purchase', '')
        data_purchase = json.loads(purchase_request)

        invoice = str(data_purchase["Invoice"])
        provider_id = str(data_purchase["ProviderId"])
        date = str(data_purchase["Date"])
        type_bill = str(data_purchase["Type_Bill"])
        type_pay = str(data_purchase["Type_Pay"])

        base_total = _dec(data_purchase["Base_Total"])
        igv_total = _dec(data_purchase["Igv_Total"])
        total_import = _dec(data_purchase["Import_Total"])
        total_document = _dec(data_purchase["Total_Document"])
        # total_freight = decimal.Decimal(data_purchase["TotalFreight"])

        check_igv = bool(int(data_purchase["Check_Igv"]))
        check_dollar = bool(int(data_purchase["Check_Dollar"]))

        # document_freight = str(data_purchase["Freight"][0]["DocumentFreight"])
        # serial_freight = str(data_purchase["Freight"][0]["SerialFreight"])
        # number_freight = str(data_purchase["Freight"][0]["NumberFreight"])
        # date_freight = str(data_purchase["Freight"][0]["DateFreight"])
        # total_freight = decimal.Decimal(data_purchase["Freight"][0]["TotalFreight"])

        if not provider_id.isdigit():
            data = {'error': 'EL PROVEEDOR NO FUE VALIDADO. BUSQUELO POR SU RUC.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        try:
            supplier_obj = Supplier.objects.get(id=int(provider_id))
        except Supplier.DoesNotExist:
            data = {'error': 'EL PROVEEDOR NO EXISTE EN EL SISTEMA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        # Se valida todo antes de escribir para no dejar compras a medias.
        detalles_normalizados = []
        series_del_payload = {}
        for detail in data_purchase['Details']:
            try:
                product_obj = Product.objects.get(id=int(detail['Product']))
                unit_obj = Unit.objects.get(id=int(detail['Unit']))
            except (Product.DoesNotExist, Unit.DoesNotExist, TypeError, ValueError):
                data = {'error': 'EXISTE UN DETALLE SIN PRODUCTO O UNIDAD DE MEDIDA VALIDA. REVISAR EL DETALLE.'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            try:
                serials = _clean_serials(detail.get('Serials'), quantity=detail.get('Quantity'),
                                         product_name=product_obj.name)
            except ValueError as error:
                data = {'error': str(error)}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            # La misma serie no puede repetirse en otro renglon de la misma compra.
            for serial_val in serials:
                key = serial_val.upper()
                if key in series_del_payload:
                    data = {'error': 'LA SERIE {} ESTA REPETIDA EN LA MISMA COMPRA (producto "{}").'.format(
                        serial_val, product_obj.name)}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response
                series_del_payload[key] = product_obj.name

            if serials:
                registradas = _serials_already_registered(serials)
                if registradas:
                    data = {
                        'error': 'LA SERIE {} YA FUE REGISTRADA ANTERIORMENTE. REVISAR STOCK.'.format(
                            list(registradas.keys())[0])
                    }
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

            detalles_normalizados.append((detail, product_obj, unit_obj, serials))

        with transaction.atomic():
            purchase_obj = Purchase(
                supplier=supplier_obj,
                purchase_date=date,
                bill_number=invoice,
                type_bill=type_bill,
                type_pay=type_pay,
                user=user_obj,
                subsidiary=subsidiary_obj,
                # document_freight=document_freight,
                # serial_freight=serial_freight,
                # number_freight=number_freight,
                # date_freight=date_freight,
                # total_freight=total_freight,
                base_total_purchase=base_total,
                igv_total_purchase=igv_total,
                total_import=total_import,
                total_purchase=total_document,
                check_igv=check_igv,
                check_dollar=check_dollar
            )
            purchase_obj.save()

            for due in data_purchase['Dues']:
                amount_due = _dec(due['amountDue'])

                purchase_due_obj = PurchaseDues(
                    purchase=purchase_obj,
                    due=amount_due
                )
                purchase_due_obj.save()

            for detail, product_obj, unit_obj, serials in detalles_normalizados:
                quantity = str(_dec(detail['Quantity']))
                price = _dec(detail['Price'])
                price_unit_discount = _dec(detail['Price_Unit_Discount'])

                dt1 = _dec(detail['Dto1'])
                dt2 = _dec(detail['Dto2'])
                dt3 = _dec(detail['Dto3'])
                dt4 = _dec(detail['Dto4'])

                total_detail = _dec(detail['Total'])
                # checked_kardex = bool(int(detail["Check_kardex"]))

                purchase_detail_obj = PurchaseDetail(
                    purchase=purchase_obj,
                    product=product_obj,
                    quantity=quantity,
                    unit=unit_obj,
                    price_unit=price,
                    price_unit_discount=price_unit_discount,
                    discount_one=dt1,
                    discount_two=dt2,
                    discount_three=dt3,
                    discount_four=dt4,
                    total_detail=total_detail,
                )
                purchase_detail_obj.save()

                for serial_val in serials:
                    product_serial_obj = ProductSerial(
                        serial_number=serial_val,
                        purchase_detail=purchase_detail_obj,
                        status='P'
                    )
                    product_serial_obj.save()

        return JsonResponse({
            'message': 'Compra Registrada Correctamente',
        }, status=HTTPStatus.OK)


@csrf_exempt
def save_detail_purchase_store(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'METODO NO PERMITIDO'}, status=HTTPStatus.METHOD_NOT_ALLOWED)

    purchase_request = request.GET.get('details_purchase', '')
    if not purchase_request:
        return JsonResponse({'error': 'NO SE ENVIO EL DETALLE DE LA COMPRA'},
                            status=HTTPStatus.INTERNAL_SERVER_ERROR)
    data_purchase = json.loads(purchase_request)

    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    purchase_id = str(data_purchase["Purchase"])
    subsidiary_store_id = int(data_purchase["id_almacen"])

    check_dollar = bool(int(data_purchase["CheckDollar"]))
    check_soles = bool(int(data_purchase["CheckSoles"]))

    if not purchase_id.isdigit():
        return JsonResponse({'error': 'COMPRA NO VALIDA'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    try:
        purchase_obj = Purchase.objects.get(id=int(purchase_id))
    except Purchase.DoesNotExist:
        return JsonResponse({'error': 'LA COMPRA NO EXISTE'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if purchase_obj.status == 'A':
        return JsonResponse({'error': 'LOS PRODUCTOS YA ESTAN ASIGNADOS A SU ALMACEN.'},
                            status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if purchase_obj.status == 'N':
        return JsonResponse({'error': 'LA COMPRA ESTA ANULADA, NO SE PUEDE ASIGNAR AL ALMACEN.'},
                            status=HTTPStatus.INTERNAL_SERVER_ERROR)

    user_subsidiary = get_subsidiary_by_user(user_obj)
    if user_subsidiary is not None and purchase_obj.subsidiary_id != user_subsidiary.id:
        return JsonResponse({'error': 'LA COMPRA NO PERTENECE A SU SUCURSAL.'},
                            status=HTTPStatus.INTERNAL_SERVER_ERROR)

    freight = None
    if data_purchase.get("Freight") is not None:
        try:
            freight = decimal.Decimal(str(data_purchase["Freight"]))
        except (decimal.InvalidOperation, TypeError, ValueError):
            freight = None

    try:
        subsidiary_store_obj = SubsidiaryStore.objects.get(id=subsidiary_store_id)
    except SubsidiaryStore.DoesNotExist:
        return JsonResponse({'error': 'NO EXISTE ALMACEN'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if user_subsidiary is not None and subsidiary_store_obj.subsidiary_id != user_subsidiary.id:
        return JsonResponse({'error': 'EL ALMACEN SELECCIONADO NO PERTENECE A SU SUCURSAL.'},
                            status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if not data_purchase.get('Details'):
        return JsonResponse({'error': 'LA COMPRA NO TIENE DETALLES PARA ASIGNAR.'},
                            status=HTTPStatus.INTERNAL_SERVER_ERROR)

    try:
        with transaction.atomic():
            for detail in data_purchase['Details']:
                price_unit_real = decimal.Decimal('0')
                price_unit_igv_money_change = decimal.Decimal('0')

                quantity = decimal.Decimal((detail['Quantity']).replace(",", "."))
                price = decimal.Decimal((detail['PriceUnit']).replace(",", "."))
                price_unit_with_discount = decimal.Decimal((detail['PriceUnitDiscount']).replace(",", "."))

                # if detail['PriceUnitDiscountPlusFreight'] is not None: price_unit_with_discount_plus_freight =
                # decimal.Decimal(detail['PriceUnitDiscountPlusFreight'])

                if detail.get('PriceUnitIgvMoneyChange') is not None:
                    try:
                        price_unit_igv_money_change = decimal.Decimal(
                            str(detail['PriceUnitIgvMoneyChange']).replace(",", "."))
                    except (decimal.InvalidOperation, TypeError, ValueError):
                        price_unit_igv_money_change = decimal.Decimal('0')

                # if detail['PriceUnitIgvMoneyChangePlusFreight'] is not None:
                #     price_unit_igv_money_change_plus_freight = decimal.Decimal(
                #         detail['PriceUnitIgvMoneyChangePlusFreight'])

                product_id = int(detail['Product'])
                product_obj = Product.objects.get(id=product_id)

                unit_id = int(detail['Unit'])
                unit_obj = Unit.objects.get(id=unit_id)

                checked = bool(int(detail.get("Check", 0)))
                try:
                    product_detail_obj = ProductDetail.objects.get(product__id=product_id, unit=unit_obj)
                except ProductDetail.DoesNotExist:
                    # Se lanza excepcion (y no se retorna) para que transaction.atomic()
                    # revierta lo ya escrito de los detalles anteriores.
                    raise PurchaseStoreError(
                        'EL PRODUCTO "{}" NO TIENE CONFIGURADO EL DETALLE DE LA UNIDAD DE MEDIDA.'.format(
                            product_obj.name)
                    )

                if check_dollar:
                    # price_unit_real = price_unit_igv_money_change_plus_freight
                    product_detail_obj.price_purchase_dollar = price_unit_with_discount
                    # El kardex y el stock se Valuan en soles: antes se guardaba con
                    # precio 0 porque price_unit_real nunca se asignaba en este caso.
                    price_unit_real = price_unit_igv_money_change
                elif check_soles:
                    price_unit_real = price

                if checked:
                    product_detail_obj.price_purchase = decimal.Decimal(price_unit_real)
                    product_detail_obj.user = user_obj

                if checked or check_dollar:
                    # price_purchase_dollar antes solo se guardaba con "checked" (siempre 0)
                    product_detail_obj.save()

                try:
                    product_store_obj = ProductStore.objects.get(product=product_obj,
                                                                     subsidiary_store=subsidiary_store_obj)
                except ProductStore.DoesNotExist:
                    product_store_obj = None
                unit_min_detail_product = product_detail_obj.quantity_minimum

                purchase_detail = int(detail['PurchaseDetail'])
                try:
                    purchase_detail_obj = PurchaseDetail.objects.get(id=purchase_detail,
                                                                     purchase=purchase_obj)
                except PurchaseDetail.DoesNotExist:
                    raise PurchaseStoreError(
                        'EL DETALLE {} NO PERTENECE A LA COMPRA SELECCIONADA.'.format(purchase_detail)
                    )

                product_serial_set = ProductSerial.objects.filter(purchase_detail=purchase_detail_obj)

                if product_store_obj is None:

                    new_product_store_obj = ProductStore(
                        product=product_obj,
                        subsidiary_store=subsidiary_store_obj,
                        stock=unit_min_detail_product * quantity
                    )
                    new_product_store_obj.save()

                    if product_serial_set.exists():
                        for s in product_serial_set:
                            s.product_store = new_product_store_obj
                            s.status = 'C'
                            s.save()
                    kardex_initial(new_product_store_obj, unit_min_detail_product * quantity, price_unit_real,
                                   purchase_detail_obj=purchase_detail_obj)
                else:
                    if product_serial_set.exists():
                        for s in product_serial_set:
                            s.product_store = product_store_obj
                            s.status = 'C'
                            s.save()
                    kardex_input(product_store_obj.id, unit_min_detail_product * quantity, price_unit_real,
                                 purchase_detail_obj=purchase_detail_obj)

            purchase_obj.status = 'A'
            purchase_obj.save(update_fields=['status'])

    except PurchaseStoreError as error:
        return JsonResponse({'error': str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    except IntegrityError:
        data = {'error': 'HUBO UN ERROR AL ASIGNAR LOS PRODUCTOS AL ALMACÉN. REVISAR LOS PRODUCTOS O CONTACTAR CON SISTEMAS.'}
        response = JsonResponse(data)
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response
    except (Product.DoesNotExist, Unit.DoesNotExist, ProductStore.MultipleObjectsReturned,
            ProductDetail.MultipleObjectsReturned, decimal.InvalidOperation, ValueError, TypeError) as error:
        data = {'error': 'HUBO UN ERROR AL ASIGNAR LOS PRODUCTOS AL ALMACÉN: {}'.format(error)}
        response = JsonResponse(data)
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response

    return JsonResponse({
        'message': 'PRODUCTOS ASIGNADOS AL ALMACEN ' + str(subsidiary_store_obj.name),
    }, status=HTTPStatus.OK)


def requirement_buy_create(request):
    # form_obj = FormGuide()
    # programmings = Programming.objects.filter(status__in=['P']).order_by('id')
    supplier_obj = Supplier.objects.all()
    unitmeasurement_obj = Unit.objects.all()
    product_obj = Product.objects.filter(is_approved_by_osinergmin=True)
    return render(request, 'buys/requirement_buy_create.html', {
        # 'form': form_obj,
        'supplier_obj': supplier_obj,
        'unitmeasurement_obj': unitmeasurement_obj,
        'product_obj': product_obj,

    })


def get_rateroutes_programming(request):
    # form_obj = FormGuide()
    # programmings = Programming.objects.filter(status__in=['P']).order_by('id')
    truck_obj = Truck.objects.filter(condition_owner='A')
    subsidiary_obj = Subsidiary.objects.all()
    return render(request, 'buys/rate_routes_create.html', {
        # 'form': form_obj,
        'truck_obj': truck_obj,
        'subsidiary_obj': subsidiary_obj,
    })


def requirement_buy_save(request):
    if request.method == 'GET':
        requirement_buy_request = request.GET.get('requirement_buy', '')
        data_requirement_buy = json.loads(requirement_buy_request)

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        date_raquirement = str(data_requirement_buy["id_date_raquirement"])
        number_scop = str(data_requirement_buy["id_number_scop"])
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        new_requirement_buy = {
            'creation_date': date_raquirement,
            'number_scop': number_scop,
            'user': user_obj,
            'subsidiary': subsidiary_obj,
        }
        requirement_buy_obj = Requirement_buys.objects.create(**new_requirement_buy)
        requirement_buy_obj.save()

    for detail in data_requirement_buy['Details']:
        quantity = decimal.Decimal(detail['Quantity'])

        # recuperamos del producto
        product_id = int(detail['Product'])
        product_obj = Product.objects.get(id=product_id)

        # recuperamos la unidad
        unit_id = int(detail['Unit'])
        unit_obj = Unit.objects.get(id=unit_id)

        new_detail_requirement_buy = {
            'product': product_obj,
            'requirement_buys': requirement_buy_obj,
            'quantity': quantity,
            'unit': unit_obj,

        }
        new_detail_requirement_buy = RequirementDetail_buys.objects.create(**new_detail_requirement_buy)
        new_detail_requirement_buy.save()

        # recuperamos del almacen
        # store_id = int(detail['Store'])
        #
        # kardex_ouput(store_id, quantity)

    return JsonResponse({
        'message': 'Se guardo la guia correctamente.',
        'requirement_buy': requirement_buy_obj.id,

    }, status=HTTPStatus.OK)


def get_requeriments_buys_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    requiriments_buys = Requirement_buys.objects.filter(subsidiary__id=subsidiary_obj.id, status='1').order_by(
        "creation_date")
    return render(request, 'buys/requirement_buy_list.html', {
        'requiriments_buys': requiriments_buys
    })


def get_purchase_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    purchases = Purchase.objects.filter(subsidiary=subsidiary_obj, status='S')
    return render(request, 'buys/purchase_list.html', {
        'purchases': purchases
    })


def get_purchase_store_list(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        if pk != '':
            dates_request = request.GET.get('dates', '')
            data_dates = json.loads(dates_request)
            date_initial = str(data_dates["date_initial"])
            date_final = str(data_dates["date_final"])
            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            purchases_store = Purchase.objects.filter(subsidiary=subsidiary_obj, status='A',
                                                      purchase_date__range=[date_initial,
                                                                            date_final]).distinct('id', 'purchase_date').order_by('purchase_date')
            # purchases_store_serializers = serializers.serialize('json', purchases_store)
            tpl = loader.get_template('buys/purchase_store_grid_list.html')
            context = ({
                'purchases_store': purchases_store,
            })
            return JsonResponse({
                'success': True,
                'form': tpl.render(context, request),
            })
            # return tpl.render(context)
            #     # context
            # return JsonResponse({
            #     context
            # }, status=HTTPStatus.OK)
        else:
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            return render(request, 'buys/purchase_store_list.html', {
                # 'purchases_store': purchases_store,
                'date_now': date_now,
            })


def get_purchase_annular_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    purchases_annular = Purchase.objects.filter(subsidiary=subsidiary_obj, status='N')
    return render(request, 'buys/purchase_annular_list.html', {
        'purchases_annular': purchases_annular
    })


def get_detail_purchase_store(request):
    if request.method == 'GET':
        dictionary = []
        pk = request.GET.get('pk', '')
        type_change = request.GET.get('type_change', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        if not str(pk).isdigit():
            return JsonResponse({'detalle': 'COMPRA NO VALIDA'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        try:
            purchase_obj = Purchase.objects.get(id=int(pk))
        except Purchase.DoesNotExist:
            return JsonResponse({'detalle': 'LA COMPRA NO EXISTE'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        if subsidiary_obj is not None and purchase_obj.subsidiary_id != subsidiary_obj.id:
            return JsonResponse({'detalle': 'LA COMPRA NO PERTENECE A SU SUCURSAL.'},
                                status=HTTPStatus.INTERNAL_SERVER_ERROR)

        if purchase_obj.status == 'A':
            return JsonResponse({'detalle': 'LOS PRODUCTOS YA ESTAN ASIGNADOS A SU ALMACEN.'},
                                status=HTTPStatus.INTERNAL_SERVER_ERROR)

        if purchase_obj.status == 'N':
            return JsonResponse({'detalle': 'LA COMPRA ESTA ANULADA, NO SE PUEDE ASIGNAR AL ALMACEN.'},
                                status=HTTPStatus.INTERNAL_SERVER_ERROR)

        purchase_set = Purchase.objects.filter(id=purchase_obj.id)

        # Antes se usaba un try/except sobre un .filter(), que nunca lanza DoesNotExist:
        # sin almacen de mercaderia el select de destino quedaba vacio en silencio.
        subsidiary_store_set = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category__in=['V'])
        if not subsidiary_store_set.exists():
            return JsonResponse({'detalle': 'NO EXISTE ALMACEN DE MERCADERIA'},
                                status=HTTPStatus.INTERNAL_SERVER_ERROR)
        subsidiary_store_obj = subsidiary_store_set

        # Si no se pudo obtener el tipo de cambio, float('') lanzaba ValueError y
        # toda la vista respondia 500. Se valida y se avisa al usuario.
        try:
            type_change_value = float(str(type_change).replace(',', '.').strip())
            if type_change_value <= 0:
                raise ValueError
        except (TypeError, ValueError):
            type_change_value = 1
            type_change_valido = False
        else:
            type_change_valido = True

        for p in purchase_set:

            purchase = {
                'id': p.id,
                'date': p.purchase_date,
                'bill_number': p.bill_number,
                'user': p.user,
                'subsidiary': p.subsidiary,
                'document_freight': p.document_freight,
                'serial_freight': p.serial_freight,
                'number_freight': p.number_freight,
                'date_freight': p.date_freight,
                'total_freight': p.total_freight,
                'base_total_purchase': p.base_total_purchase,
                'igv_total_purchase': p.igv_total_purchase,
                'total_import': p.total_import,
                'total_purchase': p.total_purchase,
                'check_igv': p.check_igv,
                'check_dollar': p.check_dollar,
                'type_bill': p.type_bill,
                'total_quantity_details': p.total_quantity_details(),
                'purchase_detail_set': []
            }
            # freight_calculate = float(p.total_freight / p.total_quantity_details())

            for d in p.purchasedetail_set.all():

                if p.check_igv:
                    price_unit_real = round(float(d.price_unit_discount), 2)
                else:
                    price_unit_real = round(float(d.price_unit_discount_with_igv()), 2)

                price_unit_discount_with_igv_money_change = round(float(price_unit_real) * type_change_value, 2)
                # price_unit_discount_with_igv_money_change_freight = price_unit_discount_with_igv_money_change + freight_calculate

                details = {
                    'id': d.id,
                    'product_id': d.product.id,
                    'product': d.product.name,
                    'product_code': d.product.code,
                    'product_brand': d.product.product_brand.name,
                    'quantity': d.quantity,
                    'unit_id': d.unit.id,
                    'unit_name': d.unit.name,
                    'value_unit': round(decimal.Decimal(d.price_unit / decimal.Decimal(1.18)), 4),
                    'price_unit': round(decimal.Decimal(d.price_unit), 4),
                    'price_unit_discount': round(float(d.price_unit_discount), 2),
                    'price_unit_discount_with_igv': round(decimal.Decimal(d.price_unit_discount_with_igv()), 2),
                    'discount_one': round(float(d.discount_one), 2),
                    'discount_two': round(float(d.discount_two), 2),
                    'discount_three': round(float(d.discount_three), 2),
                    'discount_four': round(float(d.discount_four), 2),
                    'total_detail': d.total_detail,
                    'check_kardex': d.check_kardex,
                    'multiplicate': round(float(d.multiplicate()), 2),
                    # 'price_unit_discount_plus_freight': round(price_unit_real + freight_calculate, 2),
                    'price_unit_discount_with_igv_money_change': price_unit_discount_with_igv_money_change,
                    # 'price_unit_discount_with_igv_money_change_freight': price_unit_discount_with_igv_money_change_freight,
                    'serials': []
                }
                for s in d.productserial_set.all().order_by('id'):
                    serials = {
                        'id': s.id,
                        'status': s.status,
                        'serial': s.serial_number,
                    }
                    details.get('serials').append(serials)

                purchase.get('purchase_detail_set').append(details)

            dictionary.append(purchase)

        t = loader.get_template('buys/assignment_detail_purchase.html')
        c = ({
            'purchase': purchase_obj,
            # 'detail_purchase': purchase_details,
            'dictionary': dictionary,
            'subsidiary_stores': subsidiary_store_obj,
            'type_change': type_change_value,
            'type_change_valido': type_change_valido,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def get_detail_by_purchase(request):
    if request.method == 'GET':
        purchase_id = request.GET.get('ip', '')
        purchase_obj = Purchase.objects.get(pk=int(purchase_id))
        details_purchase = PurchaseDetail.objects.filter(purchase=purchase_obj)
        t = loader.get_template('buys/table_details_purchase_by_purchase.html')
        c = ({
            'details': details_purchase,
        })
        return JsonResponse({
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)


def get_products_serial_purchase(request):
    if request.method == 'GET':
        purchase_id = request.GET.get('purchase', '')
        purchase_obj = Purchase.objects.get(id=int(purchase_id))
        products = []
        for d in purchase_obj.purchasedetail_set.all().select_related('product', 'unit'):
            if d.product.is_serial:
                products.append({
                    'purchase_detail_id': d.id,
                    'name': d.product.name,
                    'code': d.product.code,
                    'quantity': d.quantity,
                    'unit': d.unit.name if d.unit else '',
                })
        return JsonResponse({'products': products}, status=HTTPStatus.OK)


def get_serials_by_detail(request):
    if request.method == 'GET':
        purchase_detail_id = request.GET.get('purchase_detail', '')
        purchase_detail_obj = PurchaseDetail.objects.get(id=int(purchase_detail_id))
        serials = []
        for s in purchase_detail_obj.productserial_set.all().order_by('id'):
            serials.append({
                'id': s.id,
                'serial': s.serial_number,
                'status': s.get_status_display(),
                'status_code': s.status,
                'editable': s.status == 'C',
            })
        return JsonResponse({
            'serials': serials,
            'quantity': purchase_detail_obj.quantity,
        }, status=HTTPStatus.OK)


@csrf_exempt
def save_serial_purchase(request):
    if request.method == 'GET':
        serials_request = request.GET.get('serials', '')
        data = json.loads(serials_request)

        purchase_detail_id = int(data['PurchaseDetail'])
        purchase_detail_obj = PurchaseDetail.objects.get(id=purchase_detail_id)
        product_obj = purchase_detail_obj.product

        serials_requested = [
            str(s.get('Serial', '')).strip()
            for s in data.get('Serials', [])
            if str(s.get('Serial', '')).strip()
        ]
        updated_requested = data.get('UpdatedSerials', []) or []

        updates_to_apply = []
        updated_ids = []
        incoming_values = []

        for item in updated_requested:
            serial_id = item.get('id')
            new_val = str(item.get('Serial', '')).strip()
            if not serial_id:
                continue
            if not new_val:
                response = JsonResponse({'error': 'LA SERIE MODIFICADA NO PUEDE ESTAR VACIA'})
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            try:
                product_serial_obj = ProductSerial.objects.get(
                    id=int(serial_id),
                    purchase_detail=purchase_detail_obj
                )
            except ProductSerial.DoesNotExist:
                response = JsonResponse({'error': 'LA SERIE A MODIFICAR NO EXISTE EN ESTA COMPRA'})
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            if product_serial_obj.status != 'C':
                response = JsonResponse({
                    'error': 'SOLO SE PUEDEN MODIFICAR SERIES CON ESTADO COMPRADO. '
                             'LA SERIE ' + str(product_serial_obj.serial_number) + ' ESTA BLOQUEADA'
                })
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            current_val = str(product_serial_obj.serial_number or '').strip()
            if new_val.upper() == current_val.upper():
                continue
            updates_to_apply.append((product_serial_obj, new_val))
            updated_ids.append(product_serial_obj.id)
            incoming_values.append(new_val)

        incoming_values.extend(serials_requested)
        if incoming_values and len({v.upper() for v in incoming_values}) != len(incoming_values):
            response = JsonResponse({'error': 'HAY SERIES DUPLICADAS EN LOS DATOS ENVIADOS'})
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        for _, serial_val in updates_to_apply:
            qs = ProductSerial.objects.filter(serial_number__iexact=serial_val)
            if updated_ids:
                qs = qs.exclude(id__in=updated_ids)
            if qs.exists():
                response = JsonResponse({
                    'error': 'LA SERIE ' + serial_val + ' YA EXISTE EN LA BASE DE DATOS'
                })
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        product_store_obj = None
        if serials_requested:
            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            try:
                subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
                product_store_obj = ProductStore.objects.get(product=product_obj, subsidiary_store=subsidiary_store_obj)
            except (SubsidiaryStore.DoesNotExist, ProductStore.DoesNotExist):
                data = {'error': 'EL PRODUCTO NO SE ENCUENTRA ASIGNADO A NINGUN ALMACEN DE VENTA'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            existing_count = purchase_detail_obj.productserial_set.count()
            if existing_count + len(serials_requested) > int(decimal.Decimal(purchase_detail_obj.quantity)):
                data = {
                    'error': 'LA CANTIDAD DE SERIES SUPERA LA CANTIDAD COMPRADA DEL PRODUCTO (' + str(
                        purchase_detail_obj.quantity) + ')'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        if not updates_to_apply and not serials_requested:
            response = JsonResponse({'error': 'NO HAY SERIES NUEVAS NI MODIFICACIONES PARA GUARDAR'})
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        saved = 0
        updated = 0
        duplicates = []
        with transaction.atomic():
            for product_serial_obj, new_val in updates_to_apply:
                product_serial_obj.serial_number = new_val
                product_serial_obj.save(update_fields=['serial_number'])
                updated += 1
            for serial_val in serials_requested:
                qs = ProductSerial.objects.filter(serial_number__iexact=serial_val)
                if updated_ids:
                    qs = qs.exclude(id__in=updated_ids)
                if qs.exists():
                    duplicates.append(serial_val)
                    continue
                ProductSerial.objects.create(
                    serial_number=serial_val,
                    purchase_detail=purchase_detail_obj,
                    product_store=product_store_obj,
                    status='C'
                )
                saved += 1

        if not saved and not updated:
            if duplicates:
                response = JsonResponse({
                    'error': 'LA(S) SERIE(S) YA EXISTEN EN LA BASE DE DATOS: ' + ', '.join(duplicates)
                })
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            response = JsonResponse({'error': 'NO HAY SERIES NUEVAS NI MODIFICACIONES PARA GUARDAR'})
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        parts = []
        if saved:
            parts.append('Series nuevas guardadas: ' + str(saved))
        if updated:
            parts.append('Series modificadas: ' + str(updated))
        message = '. '.join(parts) + '.' if parts else 'Series guardadas correctamente.'
        if duplicates:
            message += ' Series duplicadas omitidas: ' + ', '.join(duplicates)
        return JsonResponse({'message': message, 'saved': saved, 'updated': updated}, status=HTTPStatus.OK)


def update_serial_purchase(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)

    serial_id = request.GET.get('id', '')
    new_val = str(request.GET.get('serial', '')).strip()
    purchase_detail_id = request.GET.get('purchase_detail', '')

    if not serial_id:
        response = JsonResponse({'error': 'NO SE INDICO LA SERIE A MODIFICAR'})
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response
    if not new_val:
        response = JsonResponse({'error': 'LA SERIE MODIFICADA NO PUEDE ESTAR VACIA'})
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response

    try:
        filters = {'id': int(serial_id)}
        if purchase_detail_id:
            filters['purchase_detail_id'] = int(purchase_detail_id)
        product_serial_obj = ProductSerial.objects.get(**filters)
    except (ProductSerial.DoesNotExist, ValueError, TypeError):
        response = JsonResponse({'error': 'LA SERIE A MODIFICAR NO EXISTE'})
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response

    if product_serial_obj.status != 'C':
        response = JsonResponse({
            'error': 'SOLO SE PUEDEN MODIFICAR SERIES CON ESTADO COMPRADO. '
                     'LA SERIE ' + str(product_serial_obj.serial_number) + ' ESTA BLOQUEADA'
        })
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response

    current_val = str(product_serial_obj.serial_number or '').strip()
    if new_val.upper() == current_val.upper():
        return JsonResponse({
            'message': 'La serie no tiene cambios.',
            'serial': current_val,
            'changed': False,
        }, status=HTTPStatus.OK)

    if ProductSerial.objects.filter(serial_number__iexact=new_val).exclude(id=product_serial_obj.id).exists():
        response = JsonResponse({
            'error': 'LA SERIE ' + new_val + ' YA EXISTE EN LA BASE DE DATOS'
        })
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response

    product_serial_obj.serial_number = new_val
    product_serial_obj.save(update_fields=['serial_number'])
    return JsonResponse({
        'message': 'Serie modificada correctamente.',
        'serial': new_val,
        'changed': True,
    }, status=HTTPStatus.OK)


def get_requirements_buys_list_approved(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        if pk != '':
            dates_request = request.GET.get('dates', '')
            data_dates = json.loads(dates_request)
            date_initial = (data_dates["date_initial"])
            date_final = (data_dates["date_final"])
            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            requirements_buys = Requirement_buys.objects.filter(subsidiary__id=subsidiary_obj.id,
                                                                status='2',
                                                                approval_date__range=(
                                                                    date_initial, date_final)).distinct('id')

            tpl = loader.get_template('buys/requirements_buys_approved_grid_list.html')
            context = ({
                'requirements': requirements_buys,
            })
            return JsonResponse({
                'success': True,
                'form': tpl.render(context, request),
            })
        else:
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            return render(request, 'buys/requirements_buys_approved_list.html', {
                # 'purchases_store': purchases_store,
                'date_now': date_now,
            })


def create_requirement_view(request):
    my_date = datetime.now()
    date_now = my_date.strftime("%Y-%m-%d")
    supplier_set = Supplier.objects.all()
    unit_set = Unit.objects.all()
    product_set = Product.objects.filter(is_approved_by_osinergmin=True)
    t = loader.get_template('buys/requirement_glp.html')
    c = ({
        'supplier_set': supplier_set,
        'unit_set': unit_set,
        'product_set': product_set,
        'date_now': date_now,
    })
    return JsonResponse({
        'form': t.render(c, request),
    })


def new_provider(request):
    t = loader.get_template('buys/buy_modal_provider.html')
    c = ({})
    return JsonResponse({
        'form': t.render(c, request),
    })


def get_sunat(request):
    if request.method == 'GET':
        nro_document = request.GET.get('nro_document', '')
        type_document = str(request.GET.get('type', ''))
        person_obj_search = Supplier.objects.filter(ruc=nro_document)
        if person_obj_search.exists():
            names = person_obj_search.last().business_name
            data = {
                'error': 'EL PROVEEDOR ' + str(names) + ' YA SE ENCUENTRA REGISTRADO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        else:
            if type_document == '01':
                type_name = 'RUC'
                r = query_api_amigo(nro_document, type_name)

                if r.get('ruc') == nro_document:
                    business_name = r.get('razonSocial')
                    address_business = r.get('direccion')
                    result = business_name
                    address = address_business
                    return JsonResponse({'result': result, 'address': address}, status=HTTPStatus.OK)
                else:
                    data = {'error': 'NO EXISTE RUC. REGISTRE MANUAL O CORREGIRLO'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response


@csrf_exempt
def save_provider(request):
    if request.method == 'POST':
        _ruc = request.POST.get('ruc_provider', '')
        _names_business = request.POST.get('name_provider', '')
        _names = request.POST.get('description_provider', '')
        _telephone = request.POST.get('phone_provider', '')
        _email = request.POST.get('email_provider', '')
        _address = request.POST.get('address_provider', '')
        if _names == '' or _names == None:
            _names = _names_business
        supplier_obj = Supplier(
            ruc=_ruc,
            business_name=_names_business,
            name=_names,
            phone=_telephone,
            email=_email,
            address=_address,
        )
        supplier_obj.save()
        return JsonResponse({
            'message': True,
            'resp': 'Se registro exitosamente',
        }, status=HTTPStatus.OK)


@csrf_exempt
def save_requirement(request):
    if request.method == 'POST':
        _date = request.POST.get('date-requirement', '')
        _scop = request.POST.get('scop', '')
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        _product = request.POST.get('product', '')
        product_obj = Product.objects.get(id=int(_product))
        _unit = request.POST.get('units', '')
        unit_obj = Unit.objects.get(id=int(_unit))
        _quantity = decimal.Decimal(request.POST.get('quantity', 0))

        requirement_buy_obj = Requirement_buys(
            creation_date=_date,
            number_scop=_scop,
            user=user_obj,
            subsidiary=subsidiary_obj
        )
        requirement_buy_obj.save()

        new_detail_requirement_buy = {
            'product': product_obj,
            'requirement_buys': requirement_buy_obj,
            'quantity': _quantity,
            'unit': unit_obj,
        }
        new_detail_requirement_buy = RequirementDetail_buys.objects.create(**new_detail_requirement_buy)
        new_detail_requirement_buy.save()

        return JsonResponse({
            'message': 'Requerimiento registrado correctamente.',
            'requirement_buy': requirement_buy_obj.id,
        }, status=HTTPStatus.OK)


# Vocales con sus variantes acentuadas: el usuario escribe "camara" pero el
# producto se llama "CAMARA" / "CÁMARA". icontains no ignora tildes, por eso
# la busqueda se hace ademas con un patron regex insensible a acentos.
_ACCENT_CHARS = {
    'a': 'aáàäâãå',
    'e': 'eéèëê',
    'i': 'iíìïî',
    'o': 'oóòöôõ',
    'u': 'uúùüû',
    'n': 'nñ',
    'c': 'cç',
    'y': 'yýÿ',
    's': 'sś',
    'z': 'zž',
}
_MAX_SEARCH_LENGTH = 60
_MAX_AUTOCOMPLETE_RESULTS = 25


def _unaccent_regex(term):
    """Convierte un texto en un patron POSIX que ignora acentos y mayusculas."""
    chars = []
    for ch in str(term).strip().lower():
        if ch in _ACCENT_CHARS:
            chars.append('[' + _ACCENT_CHARS[ch] + ']')
        else:
            chars.append(re.escape(ch))
    return ''.join(chars)


def get_product_by_criteria_table(request):
    if request.method == 'GET':
        # Los 4 buscadores antiguos dependen del 500 para "no encontrado".
        # El autocomplete nuevo pide format=autocomplete y recibe 200 con lista vacia.
        es_autocomplete = request.GET.get('format', '') == 'autocomplete'

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.filter(
            subsidiary=subsidiary_obj, category='V').first()

        value = str(request.GET.get('value', '') or '').strip()[:_MAX_SEARCH_LENGTH]
        array_value = value.split()

        def sin_resultados(mensaje_extra=''):
            if es_autocomplete:
                return JsonResponse({
                    'productList': [],
                    'total': 0,
                    'message': 'Sin resultados',
                }, status=HTTPStatus.OK)
            data = {'error': 'NO EXISTE EL PRODUCTO, FAVOR DE INGRESAR PRODUCTO EXISTENTE.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if not array_value:
            return sin_resultados()

        def buscar(solo_habilitados=True, usar_regex=False):
            consulta = None
            for palabra in array_value:
                if usar_regex:
                    patron = _unaccent_regex(palabra)
                    q = Q(name__iregex=patron) | Q(product_brand__name__iregex=patron) \
                        | Q(barcode__iregex=patron) | Q(code__iregex=patron)
                else:
                    q = Q(name__icontains=palabra) | Q(product_brand__name__icontains=palabra) \
                        | Q(barcode__icontains=palabra) | Q(code__icontains=palabra)
                consulta = q if consulta is None else (consulta & q)

            query_set = Product.objects.filter(consulta)
            if solo_habilitados:
                query_set = query_set.filter(is_enabled=True)
            return query_set

        # 1) coincidencia directa (usa indice, es lo rapido)
        product_set = buscar(solo_habilitados=True, usar_regex=False)
        coincide = product_set.exists()

        # 2) si no hay coincidencia se reintenta ignorando acentos
        if not coincide:
            product_set = buscar(solo_habilitados=True, usar_regex=True)
            coincide = product_set.exists()

        if not coincide:
            # Diagnostico: puede que el producto exista pero este deshabilitado.
            deshabilitados = buscar(solo_habilitados=False, usar_regex=False).exists() \
                or buscar(solo_habilitados=False, usar_regex=True).exists()
            if deshabilitados and es_autocomplete:
                return JsonResponse({
                    'productList': [],
                    'total': 0,
                    'message': 'Producto deshabilitado',
                    'hint': 'Existe en el catálogo pero está marcado como no habilitado.',
                }, status=HTTPStatus.OK)
            return sin_resultados()

        # 3) una sola consulta para los productos y sus detalles (evita el N+1)
        products = list(
            product_set
            .select_related('product_brand')
            .prefetch_related('productdetail_set__unit')
            .order_by('name')[:_MAX_AUTOCOMPLETE_RESULTS]
        )

        # 4) una sola consulta para el stock de todos los productos
        stock_por_producto = {}
        if subsidiary_store_obj is not None and products:
            for ps in ProductStore.objects.filter(
                    product_id__in=[p.id for p in products],
                    subsidiary_store=subsidiary_store_obj):
                stock_por_producto.setdefault(ps.product_id, ps)

        product_list = []
        for e in products:
            unit_id = ''
            unit_name = ''
            price_sale = ''
            price_purchase = ''

            detalles = list(e.productdetail_set.all())
            if detalles:
                # .last() usa el id como orden cuando el modelo no define ordering
                product_detail_obj = max(detalles, key=lambda d: d.id)
                unit_id = product_detail_obj.unit.id
                unit_name = product_detail_obj.unit.name
                price_sale = product_detail_obj.price_sale
                price_purchase = product_detail_obj.price_purchase

            product_store_row = stock_por_producto.get(e.id)
            stock = product_store_row.stock if product_store_row else 0
            product_store_id = product_store_row.id if product_store_row else ''

            product_list.append({
                'id': e.id,
                'name': e.name,
                # product_brand puede ser None: antes eso rompia toda la respuesta
                'brand': e.product_brand.name if e.product_brand else '',
                'code': e.code if e.code else '',
                'unit': unit_name,
                'unit_id': unit_id,
                'price_sale': price_sale,
                'price_purchase': price_purchase,
                'stock': stock,
                'product_store_id': product_store_id,
                'barcode': e.barcode if e.barcode is not None else ''
            })

        return JsonResponse({
            'productList': product_list,
            'total': len(product_list),
        }, status=HTTPStatus.OK)


def get_provider_by_ruc(request):
    if request.method == 'GET':
        ruc = request.GET.get('ruc', '')
        result = ''
        supplier_obj = None
        address = ''

        supplier_set = Supplier.objects.filter(ruc=ruc)
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        if supplier_set.exists():
            supplier_obj = supplier_set.first()
            business_name = supplier_obj.business_name
            supplier_id = supplier_obj.id

            return JsonResponse({'pk': supplier_id, 'result': business_name},
                                status=HTTPStatus.OK)
        else:
            type_name = 'RUC'
            r = query_api_facturacioncloud(ruc, type_name)

            if r.get('statusMessage') != 'SERVICIO SE VENCIO' and r.get('errors') is None:

                if r.get('ruc') == ruc:
                    business_name = r.get('razonSocial')
                    address_business = r.get('direccion')
                    result = business_name
                    address = address_business

                    supplier_obj = Supplier(
                        name=result,
                        business_name=result,
                        address=address,
                        ruc=ruc
                    )
                    supplier_obj.save()

            else:
                r = query_apis_net_dni_ruc(ruc, type_name)

                if r.get('numeroDocumento') == ruc:

                    business_name = r.get('nombre')
                    address_business = r.get('direccion')
                    result = business_name
                    address = address_business

                    supplier_obj = Supplier(
                        name=result,
                        business_name=result,
                        address=address,
                        ruc=ruc
                    )
                    supplier_obj.save()

                else:
                    data = {
                        'error': 'No esta registrado en la Base de Datos, favor de registrar manualmente'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

            return JsonResponse({'pk': supplier_obj.id, 'result': result, 'address': address},
                                status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_type_change(request):
    if request.method == 'GET':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        money_change_set = MoneyChange.objects.filter(search_date=formatdate)

        if money_change_set.exists():
            money_change_obj = money_change_set.first()
            sell = money_change_obj.sell
            buy = money_change_obj.buy

            return JsonResponse({'sell': sell, 'buy': buy},
                                status=HTTPStatus.OK)
        else:
            r = query_apis_net_money(formatdate)

            if r.get('fecha_busqueda') == formatdate:
                sell = round(r.get('venta'), 3)
                buy = round(r.get('compra'), 3)
                search_date = r.get('fecha_busqueda')
                sunat_date = r.get('fecha_sunat')

                money_change_obj = MoneyChange(
                    search_date=search_date,
                    sunat_date=sunat_date,
                    sell=sell,
                    buy=buy
                )
                money_change_obj.save()

            else:
                data = {'error': 'NO EXISTE TIPO DE CAMBIO'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        return JsonResponse({'sell': sell, 'buy': buy},
                            status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def update_purchase(request, pk=None):
    purchase_obj = Purchase.objects.get(id=int(pk))

    # Solo las compras que aun no ingresaron al almacen pueden editarse: una vez
    # asignadas ya generaron stock, kardex y series en estado COMPRADO.
    if purchase_obj.status != 'S':
        return render(request, 'buys/purchase_edit_blocked.html', {
            'purchase': purchase_obj,
        })

    return render(request, 'buys/buy_list_edit.html', {
        'purchase': purchase_obj,
        'choices_payments_purchase': Purchase._meta.get_field('type_pay').choices,
        'tipo_pay_choices': Purchase._meta.get_field('type_pay').choices,
        'tipo_bill_choices': Purchase._meta.get_field('type_bill').choices,
    })


def save_update_purchase(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        purchase_obj = None
        purchase_detail_obj = None

        purchase_request = request.GET.get('purchase', '')
        data_purchase = json.loads(purchase_request)

        invoice = str(data_purchase["Invoice"])
        provider_id = str(data_purchase["ProviderId"])
        date = str(data_purchase["Date"])
        type_bill = str(data_purchase["Type_Bill"])
        type_pay = str(data_purchase["Type_Pay"])

        base_total = _dec(data_purchase["Base_Total"])
        igv_total = _dec(data_purchase["Igv_Total"])
        total_import = _dec(data_purchase["Import_Total"])
        total_document = _dec(data_purchase["Total_Document"])
        # total_freight = decimal.Decimal(data_purchase["TotalFreight"])

        check_igv = bool(int(data_purchase["Check_Igv"]))
        check_dollar = bool(int(data_purchase["Check_Dollar"]))

        # document_freight = str(data_purchase["Freight"][0]["DocumentFreight"])
        # serial_freight = str(data_purchase["Freight"][0]["SerialFreight"])
        # number_freight = str(data_purchase["Freight"][0]["NumberFreight"])
        # date_freight = str(data_purchase["Freight"][0]["DateFreight"])
        # total_freight = decimal.Decimal(data_purchase["Freight"][0]["TotalFreight"])

        if not provider_id.isdigit():
            data = {'error': 'EL PROVEEDOR NO FUE VALIDADO. BUSQUELO POR SU RUC.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        try:
            supplier_obj = Supplier.objects.get(id=int(provider_id))
        except Supplier.DoesNotExist:
            data = {'error': 'EL PROVEEDOR NO EXISTE EN EL SISTEMA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        purchase_id = request.GET.get('purchase_id', '')
        if not str(purchase_id).isdigit():
            data = {'error': 'NO EXISTE COMPRA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        try:
            purchase_obj = Purchase.objects.get(id=int(purchase_id))
        except Purchase.DoesNotExist:
            data = {'error': 'NO EXISTE COMPRA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if purchase_obj.status == 'A':
            data = {'error': 'LA COMPRA YA FUE ASIGNADA AL ALMACEN, NO SE PUEDE EDITAR.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if purchase_obj.status == 'N':
            data = {'error': 'LA COMPRA ESTA ANULADA, NO SE PUEDE EDITAR.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if subsidiary_obj is not None and purchase_obj.subsidiary_id != subsidiary_obj.id:
            data = {'error': 'LA COMPRA NO PERTENECE A SU SUCURSAL.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        # Se valida el payload completo antes de escribir nada.
        detalles_normalizados = []
        series_del_payload = {}
        for detail in data_purchase['Details']:
            try:
                product_obj = Product.objects.get(id=int(detail['Product']))
                unit_obj = Unit.objects.get(id=int(detail['Unit']))
            except (Product.DoesNotExist, Unit.DoesNotExist, TypeError, ValueError):
                data = {'error': 'EXISTE UN DETALLE SIN PRODUCTO O UNIDAD DE MEDIDA VALIDA. REVISAR EL DETALLE.'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            product_detail_id = detail.get('ProductDetail', 'NaN')
            purchase_detail_obj = None
            ids_actuales = []
            if product_detail_id not in ('NaN', '', None, 'undefined'):
                try:
                    purchase_detail_obj = PurchaseDetail.objects.get(id=int(product_detail_id),
                                                                      purchase=purchase_obj)
                except (PurchaseDetail.DoesNotExist, TypeError, ValueError):
                    purchase_detail_obj = None
                if purchase_detail_obj is not None:
                    ids_actuales = list(
                        ProductSerial.objects.filter(purchase_detail=purchase_detail_obj).values_list('id', flat=True)
                    )

            try:
                serials = _clean_serials(detail.get('Serials'), quantity=detail.get('Quantity'),
                                         product_name=product_obj.name)
            except ValueError as error:
                data = {'error': str(error)}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            # La misma serie no puede repetirse en otro renglon de la misma compra.
            for serial_val in serials:
                key = serial_val.upper()
                if key in series_del_payload:
                    data = {'error': 'LA SERIE {} YA SE INGRESO EN OTRO DETALLE DE ESTA COMPRA.'.format(serial_val)}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response
                series_del_payload[key] = product_obj.name

            # No se admiten series ya registradas por otro producto/compra.
            registradas = _serials_already_registered(serials, exclude_ids=ids_actuales)
            if registradas:
                data = {'error': 'LA SERIE {} YA FUE REGISTRADA ANTERIORMENTE. REVISAR STOCK.'.format(
                    list(registradas.keys())[0])}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            # Las series ya asignadas al almacen o vendidas no se pueden recrear.
            if ids_actuales:
                vivos = ProductSerial.objects.filter(
                    id__in=ids_actuales).exclude(status='P')
                if vivos.exists():
                    data = {'error': 'EL PRODUCTO "{}" YA TIENE SERIES ASIGNADAS AL ALMACEN O VENDIDAS. '
                                     'NO SE PUEDE EDITAR LA COMPRA.'.format(product_obj.name)}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

            detalles_normalizados.append((detail, product_obj, unit_obj, serials, purchase_detail_obj))

        with transaction.atomic():
            purchase_obj.supplier = supplier_obj
            purchase_obj.purchase_date = date
            purchase_obj.bill_number = invoice
            purchase_obj.type_bill = type_bill
            purchase_obj.type_pay = type_pay
            purchase_obj.user = user_obj
            purchase_obj.subsidiary = subsidiary_obj
            # purchase_obj.document_freight = document_freight
            # purchase_obj.serial_freight = serial_freight
            # purchase_obj.document_freight = document_freight
            # purchase_obj.number_freight = number_freight
            # purchase_obj.date_freight = date_freight
            # purchase_obj.total_freight = total_freight
            purchase_obj.base_total_purchase = base_total
            purchase_obj.igv_total_purchase = igv_total
            purchase_obj.total_import = total_import
            purchase_obj.total_purchase = total_document
            purchase_obj.check_igv = check_igv
            purchase_obj.check_dollar = check_dollar

            for du in data_purchase['Dues']:

                if du['amountId'] != 'NaN':

                    du_id = int(du['amountId'])
                    purchase_due_obj = PurchaseDues.objects.filter(id=du_id, purchase=purchase_obj).first()
                    amount_due = _dec(du['amountDue'])

                    if purchase_due_obj is not None:
                        purchase_due_obj.purchase = purchase_obj
                        purchase_due_obj.due = amount_due
                        purchase_due_obj.save()

                else:
                    amount_due = _dec(du['amountDue'])

                    purchase_due_obj = PurchaseDues(
                        purchase=purchase_obj,
                        due=amount_due
                    )
                    purchase_due_obj.save()

            for detail, product_obj, unit_obj, serials, purchase_detail_obj in detalles_normalizados:

                quantity = str(_dec(detail['Quantity']))
                price = _dec(detail['Price'])
                price_unit_discount = _dec(detail['Price_Unit_Discount'])

                dt1 = _dec(detail['Dto1'])
                dt2 = _dec(detail['Dto2'])
                dt3 = _dec(detail['Dto3'])
                dt4 = _dec(detail['Dto4'])

                total_detail = _dec(detail['Total'])

                if purchase_detail_obj is not None:
                    checked_kardex = bool(int(detail.get("Check_kardex", 1)))

                    purchase_detail_obj.purchase = purchase_obj
                    purchase_detail_obj.product = product_obj
                    purchase_detail_obj.quantity = quantity
                    purchase_detail_obj.unit = unit_obj
                    purchase_detail_obj.price_unit = price
                    purchase_detail_obj.price_unit_discount = price_unit_discount
                    purchase_detail_obj.discount_one = dt1
                    purchase_detail_obj.discount_two = dt2
                    purchase_detail_obj.discount_three = dt3
                    purchase_detail_obj.discount_four = dt4
                    purchase_detail_obj.total_detail = total_detail
                    purchase_detail_obj.check_kardex = checked_kardex
                    purchase_detail_obj.save()

                    # Solo se reemplazan las series PENDIENTES de este detalle.
                    # Antes se borraban todas (incluidas COMPRADAS y VENDIDAS),
                    # dejando unidades en stock sin serie y series vendidas sin trazabilidad.
                    ProductSerial.objects.filter(purchase_detail=purchase_detail_obj, status='P').delete()
                else:
                    purchase_detail_obj = PurchaseDetail(
                        purchase=purchase_obj,
                        product=product_obj,
                        quantity=quantity,
                        unit=unit_obj,
                        price_unit=price,
                        price_unit_discount=price_unit_discount,
                        discount_one=dt1,
                        discount_two=dt2,
                        discount_three=dt3,
                        discount_four=dt4,
                        total_detail=total_detail,
                    )
                    purchase_detail_obj.save()

                for serial_val in serials:
                    product_serial_obj = ProductSerial(
                        serial_number=serial_val,
                        purchase_detail=purchase_detail_obj,
                        status='P'
                    )
                    product_serial_obj.save()

            purchase_obj.save()

        return JsonResponse({
            'message': 'Compra Actualizada',
        }, status=HTTPStatus.OK)


def delete_item_product_buy(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'METODO NO PERMITIDO'}, status=HTTPStatus.METHOD_NOT_ALLOWED)

    detail_id = request.GET.get('detail_id', '')
    if not str(detail_id).isdigit():
        return JsonResponse({'error': 'DETALLE NO VALIDO'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    try:
        purchase_detail = PurchaseDetail.objects.get(id=int(detail_id))
    except PurchaseDetail.DoesNotExist:
        return JsonResponse({'error': 'EL DETALLE NO EXISTE'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if purchase_detail.purchase.status == 'A':
        return JsonResponse(
            {'error': 'LA COMPRA YA FUE ASIGNADA AL ALMACEN, NO SE PUEDE ELIMINAR EL DETALLE.'},
            status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    if purchase_detail.purchase.status == 'N':
        return JsonResponse({'error': 'LA COMPRA ESTA ANULADA, NO SE PUEDE EDITAR.'},
                            status=HTTPStatus.INTERNAL_SERVER_ERROR)

    # ProductSerial.purchase_detail usa on_delete=SET_NULL, por lo que al borrar el
    # detalle las series quedaban huerfanas: invisibles para ventas pero ocupando el
    # numero de serie para siempre. Se eliminan junto con el detalle.
    serials_set = ProductSerial.objects.filter(purchase_detail=purchase_detail)
    series_no_eliminables = serials_set.exclude(status='P')
    if series_no_eliminables.exists():
        return JsonResponse(
            {'error': 'EL PRODUCTO "{}" TIENE SERIES ASIGNADAS AL ALMACEN O VENDIDAS. NO SE PUEDE ELIMINAR.'.format(
                purchase_detail.product.name)},
            status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    with transaction.atomic():
        series_eliminadas = serials_set.count()
        serials_set.delete()
        purchase_detail.delete()

    mensaje = 'Eliminado.'
    if series_eliminadas:
        mensaje += ' Se eliminaron {} serie(s).'.format(series_eliminadas)

    return JsonResponse({
        'message': mensaje,
    }, status=HTTPStatus.OK)


def delete_item_due(request):
    if request.method == 'GET':
        due_id = request.GET.get('due_id', '')
        purchase_due_obj = PurchaseDues.objects.get(id=due_id)
        purchase_due_obj.delete()

        return JsonResponse({
            'message': 'Eliminado.',
        }, status=HTTPStatus.OK)


def get_product_by_code_bar(request):
    if request.method == 'GET':
        code_bar = request.GET.get('code_bar', '')
        product_set = Product.objects.filter(barcode=str(code_bar))
        if product_set.exists():
            product_obj = product_set.last()
            user_id = request.user.id
            user_obj = User.objects.get(pk=int(user_id))
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')

            unit_id = ''
            unit_name = ''
            price_sale = ''
            stock = 0
            product_store_id = ''
            price_purchase = ''

            if product_obj.productdetail_set.exists():
                unit_id = product_obj.productdetail_set.last().unit.id
                unit_name = product_obj.productdetail_set.last().unit.name
                price_sale = product_obj.productdetail_set.last().price_sale
                price_purchase = product_obj.productdetail_set.last().price_purchase

            product_store_set = ProductStore.objects.filter(product_id=product_obj.id,
                                                            subsidiary_store=subsidiary_store_obj)
            if product_store_set.exists():
                product_store_obj = product_store_set.first()
                stock = product_store_obj.stock
                product_store_id = product_store_obj.id

            return JsonResponse({
                'success': True,
                'product_code_bar': product_obj.barcode,
                'product_id': product_obj.id,
                'product_name': product_obj.name,
                'brand': product_obj.product_brand.name,
                'unit': unit_name,
                'unit_id': unit_id,
                'price_sale': price_sale,
                'price_purchase': price_purchase,
                'stock': stock,
                'product_store_id': product_store_id
            }, status=HTTPStatus.OK)
        return JsonResponse({
            'success': False,
            'message': 'NO EXISTE CÓDIGO DE BARRAS'
        })
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def check_purchase(request):
    if request.method == 'GET':
        flag = False
        supplier = request.GET.get('supplier', '')
        type_bill = request.GET.get('type_bill', '')
        correlative = request.GET.get('correlative', '')

        if not str(supplier).isdigit():
            return JsonResponse({'success': True, 'flag': flag})

        purchase_set = Purchase.objects.filter(supplier__id=int(supplier), status__in=['S', 'A'],
                                               type_bill=type_bill, bill_number=correlative)
        if purchase_set.exists():
            return JsonResponse({
                'success': True,
                'flag': True
            })
        else:
            return JsonResponse({
                'success': True,
                'flag': flag
            })
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def check_serial(request):
    if request.method == 'GET':
        serial = request.GET.get('serial', '')

        serial = str(serial or '').strip()
        if not serial:
            return JsonResponse({'success': True, 'flag': False})

        # La comparacion es insensible a mayusculas/espacios: "abc-01" y "ABC-01"
        # son la misma serie y antes se aceptaban las dos (-> duplicados).
        product_serial_set = ProductSerial.objects.filter(serial_number__iexact=serial)
        if product_serial_set.exists():
            return JsonResponse({
                'success': True,
                'flag': True,
                'status': product_serial_set.first().status,
            })
        else:
            return JsonResponse({
                'success': True,
                'flag': False,
            })
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


@csrf_exempt
def search_products_for_return(request):
    """
    Busca productos por código de barras, descripción o serie para el formulario de devolución
    """
    if request.method == 'GET':
        search_term = request.GET.get('term', '').strip()
        search_type = request.GET.get('type', 'all')  # barcode, description, serial, all

        if not search_term:
            return JsonResponse({'products': []}, status=HTTPStatus.OK)

        products = []

        try:
            if search_type == 'barcode' or search_type == 'all':
                # Búsqueda por código de barras
                barcode_products = Product.objects.filter(
                    barcode__icontains=search_term,
                    is_enabled=True
                ).select_related('product_family', 'product_brand')[:10]

                for product in barcode_products:
                    from apps.sales.models import ProductSerial
                    # Obtener la unidad mínima y precio de compra
                    product_detail = product.productdetail_set.filter(is_enabled=True).first()
                    if product_detail:
                        # Obtener las seriales del producto
                        serials = []
                        if product.is_serial:
                            product_serials = ProductSerial.objects.filter(
                                product_store__product=product,
                                status='C'  # Solo productos comprados
                            ).values_list('serial_number', flat=True)[:5]  # Máximo 5 seriales
                            serials = list(product_serials)

                        products.append({
                            'id': product.id,
                            'name': product.name,
                            'code': product.code,
                            'barcode': product.barcode,
                            'brand': product.product_brand.name if product.product_brand else '',
                            'family': product.product_family.name if product.product_family else '',
                            'unit_id': product_detail.unit.id,
                            'unit_name': product_detail.unit.name,
                            'price_purchase': float(product_detail.price_purchase),
                            'search_type': 'Código de Barras',
                            'serials': serials
                        })

            if search_type == 'description' or search_type == 'all':
                from apps.sales.models import ProductSerial
                # Búsqueda por descripción
                desc_products = Product.objects.filter(
                    Q(name__icontains=search_term) |
                    Q(name_search__icontains=search_term) |
                    Q(code__icontains=search_term),
                    is_enabled=True
                ).select_related('product_family', 'product_brand')

                for product in desc_products:
                    # Evitar duplicados
                    if not any(p['id'] == product.id for p in products):
                        product_detail = product.productdetail_set.filter(is_enabled=True).first()
                        if product_detail:
                            # Obtener las seriales del producto
                            serials = []
                            if product.is_serial:
                                product_serials = ProductSerial.objects.filter(
                                    product_store__product=product,
                                    status='C'  # Solo productos comprados
                                ).values_list('serial_number', flat=True)[:5]  # Máximo 5 seriales
                                serials = list(product_serials)

                            products.append({
                                'id': product.id,
                                'name': product.name,
                                'code': product.code,
                                'barcode': product.barcode,
                                'brand': product.product_brand.name if product.product_brand else '',
                                'family': product.product_family.name if product.product_family else '',
                                'unit_id': product_detail.unit.id,
                                'unit_name': product_detail.unit.name,
                                'price_purchase': float(product_detail.price_purchase),
                                'search_type': 'Descripción',
                                'serials': serials
                            })

            if search_type == 'serial' or search_type == 'all':
                # Búsqueda por número de serie
                from apps.sales.models import ProductSerial

                serial_products = ProductSerial.objects.filter(
                    serial_number__icontains=search_term,
                    status='C'  # Solo productos comprados
                ).select_related(
                    'product_store__product__product_brand',
                    'product_store__product__product_family'
                )[:10]

                for serial in serial_products:
                    product = serial.product_store.product
                    # Evitar duplicados
                    if not any(p['id'] == product.id for p in products):
                        product_detail = product.productdetail_set.filter(is_enabled=True).first()
                        if product_detail:
                            # Obtener las seriales del producto
                            serials = []
                            if product.is_serial:
                                product_serials = ProductSerial.objects.filter(
                                    product_store__product=product,
                                    status='C'  # Solo productos comprados
                                ).values_list('serial_number', flat=True)[:5]  # Máximo 5 seriales
                                serials = list(product_serials)

                            products.append({
                                'id': product.id,
                                'name': product.name,
                                'code': product.code,
                                'barcode': product.barcode,
                                'brand': product.product_brand.name if product.product_brand else '',
                                'family': product.product_family.name if product.product_family else '',
                                'unit_id': product_detail.unit.id,
                                'unit_name': product_detail.unit.name,
                                'price_purchase': float(product_detail.price_purchase),
                                'search_type': f'Serie: {serial.serial_number}',
                                'serial': serial.serial_number,
                                'serials': serials
                            })

            # Limitar resultados totales
            products = products[:15]

            return JsonResponse({'products': products}, status=HTTPStatus.OK)

        except Exception as e:
            return JsonResponse({
                'error': f'Error en la búsqueda: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return JsonResponse({'error': 'Método no permitido'}, status=HTTPStatus.METHOD_NOT_ALLOWED)


def update_state_annular_purchase(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'METODO NO PERMITIDO'}, status=HTTPStatus.METHOD_NOT_ALLOWED)

    id_purchase = request.GET.get('pk', '')
    if not str(id_purchase).isdigit():
        return JsonResponse({'error': 'COMPRA NO VALIDA'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    try:
        purchase_obj = Purchase.objects.get(pk=int(id_purchase))
    except Purchase.DoesNotExist:
        return JsonResponse({'error': 'LA COMPRA NO EXISTE'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if purchase_obj.status == 'A':
        return JsonResponse(
            {'error': 'LA COMPRA YA ESTA APROBADA (ASIGNADA AL ALMACEN) NO ES POSIBLE ANULAR'},
            status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    if purchase_obj.status == 'N':
        return JsonResponse({'message': 'LA COMPRA YA SE ENCUENTRA ANULADA'}, status=HTTPStatus.OK)

    # Las series que ya estan en stock ('C') o vendidas ('V') no se pueden eliminar:
    # dejarian productos huerfanos en el almacen y romperian la trazabilidad.
    serials_set = ProductSerial.objects.filter(purchase_detail__purchase=purchase_obj)
    serials_live = serials_set.exclude(status__in=['P', 'A', 'D'])
    if serials_live.exists():
        return JsonResponse(
            {'error': 'EXISTEN SERIES ASIGNADAS AL ALMACEN O VENDIDAS. NO SE PUEDE ANULAR LA COMPRA.'},
            status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    with transaction.atomic():
        # Se eliminan fisicamente las series de la compra (quedaban "en el aire"
        # con estado PENDIENTE y bloqueaban el reuso del numero de serie -> duplicados).
        series_eliminadas = serials_set.count()
        serials_set.delete()

        purchase_obj.status = 'N'
        purchase_obj.save(update_fields=['status'])

    mensaje = 'COMPRA ANULADA CORRECTAMENTE'
    if series_eliminadas:
        mensaje += '. SE ELIMINARON {} SERIE(S) ASOCIADAS'.format(series_eliminadas)

    return JsonResponse({'message': mensaje}, status=HTTPStatus.OK)