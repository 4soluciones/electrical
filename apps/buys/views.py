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
from apps.sales.views import kardex_input, kardex_ouput, kardex_initial, calculate_minimum_unit
import json
import decimal
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

        base_total = decimal.Decimal(data_purchase["Base_Total"])
        igv_total = decimal.Decimal(data_purchase["Igv_Total"])
        total_import = decimal.Decimal(data_purchase["Import_Total"])
        total_document = decimal.Decimal(data_purchase["Total_Document"])
        # total_freight = decimal.Decimal(data_purchase["TotalFreight"])

        check_igv = bool(int(data_purchase["Check_Igv"]))
        check_dollar = bool(int(data_purchase["Check_Dollar"]))

        # document_freight = str(data_purchase["Freight"][0]["DocumentFreight"])
        # serial_freight = str(data_purchase["Freight"][0]["SerialFreight"])
        # number_freight = str(data_purchase["Freight"][0]["NumberFreight"])
        # date_freight = str(data_purchase["Freight"][0]["DateFreight"])
        # total_freight = decimal.Decimal(data_purchase["Freight"][0]["TotalFreight"])

        supplier_obj = Supplier.objects.get(id=int(provider_id))

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
            amount_due = decimal.Decimal(due['amountDue'])

            purchase_due_obj = PurchaseDues(
                purchase=purchase_obj,
                due=amount_due
            )
            purchase_due_obj.save()

        for detail in data_purchase['Details']:
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)

            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)

            quantity = str(detail['Quantity'])
            price = decimal.Decimal(detail['Price'])
            price_unit_discount = decimal.Decimal(detail['Price_Unit_Discount'])

            dt1 = decimal.Decimal(detail['Dto1'])
            dt2 = decimal.Decimal(detail['Dto2'])
            dt3 = decimal.Decimal(detail['Dto3'])
            dt4 = decimal.Decimal(detail['Dto4'])

            total_detail = decimal.Decimal(detail['Total'])
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

            for serial in detail['Serials']:
                product_serial_obj = ProductSerial(
                    serial_number=serial['Serial'],
                    purchase_detail=purchase_detail_obj,
                    status='P'
                )
                product_serial_obj.save()

        return JsonResponse({
            'message': 'Compra Registrada Correctamente',
        }, status=HTTPStatus.OK)


@csrf_exempt
def save_detail_purchase_store(request):
    if request.method == 'GET':
        purchase_request = request.GET.get('details_purchase', '')
        data_purchase = json.loads(purchase_request)

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        purchase_id = str(data_purchase["Purchase"])
        subsidiary_store_id = int(data_purchase["id_almacen"])

        check_dollar = bool(int(data_purchase["CheckDollar"]))
        check_soles = bool(int(data_purchase["CheckSoles"]))
        purchase_obj = Purchase.objects.get(id=int(purchase_id))
        if data_purchase["Freight"] is not None:
            freight = decimal.Decimal(data_purchase["Freight"])

        if purchase_obj.status == 'A':
            data = {'error': 'LOS PRODUCTOS YA ESTAN ASIGNADOS A SU ALMACEN.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        try:
            subsidiary_store_obj = SubsidiaryStore.objects.get(id=subsidiary_store_id)
        except SubsidiaryStore.DoesNotExist:
            data = {'error': 'NO EXISTE ALMACEN'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        try:
            with transaction.atomic():
                for detail in data_purchase['Details']:
                    price_unit_with_discount_plus_freight = 0
                    price_unit_igv_money_change = 0
                    price_unit_igv_money_change_plus_freight = 0
                    price_unit_real = 0

                    quantity = decimal.Decimal((detail['Quantity']).replace(",", "."))
                    price = decimal.Decimal((detail['Price']).replace(",", "."))
                    price_unit_with_discount = decimal.Decimal((detail['PriceUnitDiscount']).replace(",", "."))

                    if detail['PriceUnitDiscountPlusFreight'] is not None:
                        price_unit_with_discount_plus_freight = decimal.Decimal(detail['PriceUnitDiscountPlusFreight'])

                    if detail['PriceUnitIgvMoneyChange'] is not None:
                        price_unit_igv_money_change = decimal.Decimal(detail['PriceUnitIgvMoneyChange'])

                    if detail['PriceUnitIgvMoneyChangePlusFreight'] is not None:
                        price_unit_igv_money_change_plus_freight = decimal.Decimal(
                            detail['PriceUnitIgvMoneyChangePlusFreight'])

                    product_id = int(detail['Product'])
                    product_obj = Product.objects.get(id=product_id)

                    unit_id = int(detail['Unit'])
                    unit_obj = Unit.objects.get(id=unit_id)

                    checked = bool(int(detail["Check"]))
                    product_detail_obj = ProductDetail.objects.get(product__id=product_id, unit=unit_obj)

                    if check_dollar:
                        price_unit_real = price_unit_igv_money_change_plus_freight
                        product_detail_obj.price_purchase_dollar = price_unit_with_discount
                    elif check_soles:
                        price_unit_real = price_unit_with_discount_plus_freight

                    if checked:
                        product_detail_obj.price_purchase = decimal.Decimal(price_unit_real)
                        product_detail_obj.user = user_obj
                        product_detail_obj.save()

                    try:
                        product_store_obj = ProductStore.objects.get(product=product_obj,
                                                                     subsidiary_store=subsidiary_store_obj)
                    except ProductStore.DoesNotExist:
                        product_store_obj = None
                    unit_min_detail_product = ProductDetail.objects.get(product=product_obj,
                                                                        unit=unit_obj).quantity_minimum

                    purchase_detail = int(detail['PurchaseDetail'])
                    purchase_detail_obj = PurchaseDetail.objects.get(id=purchase_detail)

                    if product_store_obj is None:

                        new_product_store_obj = ProductStore(
                            product=product_obj,
                            subsidiary_store=subsidiary_store_obj,
                            stock=unit_min_detail_product * quantity
                        )
                        new_product_store_obj.save()

                        product_serial_set = ProductSerial.objects.filter(purchase_detail=purchase_detail_obj)
                        if product_serial_set.exists():
                            for s in product_serial_set:
                                s.product_store = new_product_store_obj
                                s.status = 'C'
                                s.save()
                        kardex_initial(new_product_store_obj, unit_min_detail_product * quantity, price_unit_real,
                                       purchase_detail_obj=purchase_detail_obj)
                    else:
                        product_serial_set = ProductSerial.objects.filter(purchase_detail=purchase_detail_obj)
                        if product_serial_set.exists():
                            for s in product_serial_set:
                                s.product_store = product_store_obj
                                s.status = 'C'
                                s.save()
                        kardex_input(product_store_obj.id, unit_min_detail_product * quantity, price_unit_real,
                                     purchase_detail_obj=purchase_detail_obj)

        except IntegrityError:
            data = {'error': 'HUBO UN ERROR AL ASIGNAR LOS PRODUCTOS AL ALMACÉN. REVISAR LOS PRODUCTOS O CONTACTAR CON SISTEMAS.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        purchase_obj.status = 'A'
        purchase_obj.save()
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
                                                      purchase_date__range=[date_initial, date_final]).distinct('id')
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
        purchase_obj = Purchase.objects.get(id=pk)
        purchase_set = Purchase.objects.filter(id=pk)
        # purchase_details = PurchaseDetail.objects.filter(purchase=purchase_obj)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        try:
            subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category__in=['V'])
        except SubsidiaryStore.DoesNotExist:
            data = {'detalle': 'NO EXISTE ALMACEN DE MERCADERIA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

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
            freight_calculate = float(p.total_freight / p.total_quantity_details())

            for d in p.purchasedetail_set.all():

                if p.check_igv:
                    price_unit_real = round(float(d.price_unit_discount), 2)
                else:
                    price_unit_real = round(float(d.price_unit_discount_with_igv()), 2)

                price_unit_discount_with_igv_money_change = round(float(price_unit_real) * float(type_change), 2)
                price_unit_discount_with_igv_money_change_freight = price_unit_discount_with_igv_money_change + freight_calculate

                details = {
                    'id': d.id,
                    'product_id': d.product.id,
                    'product': d.product.name,
                    'product_code': d.product.code,
                    'product_brand': d.product.product_brand.name,
                    'quantity': d.quantity,
                    'unit_id': d.unit.id,
                    'unit_name': d.unit.name,
                    'price_unit': round(float(d.price_unit), 2),
                    'price_unit_discount': round(float(d.price_unit_discount), 2),
                    'price_unit_discount_with_igv': round(decimal.Decimal(d.price_unit_discount_with_igv()), 2),
                    'discount_one': round(float(d.discount_one), 2),
                    'discount_two': round(float(d.discount_two), 2),
                    'discount_three': round(float(d.discount_three), 2),
                    'discount_four': round(float(d.discount_four), 2),
                    'total_detail': d.total_detail,
                    'check_kardex': d.check_kardex,
                    'multiplicate': round(float(d.multiplicate()), 2),
                    'price_unit_discount_plus_freight': round(price_unit_real + freight_calculate, 2),
                    'price_unit_discount_with_igv_money_change': price_unit_discount_with_igv_money_change,
                    'price_unit_discount_with_igv_money_change_freight': price_unit_discount_with_igv_money_change_freight,
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
            'type_change': type_change,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def get_detail_by_purchase(purchase_set):
    dictionary = []

    for p in purchase_set:

        purchase_detail = p.purchasedetail_set.all()

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
        freight_calculate = p.total_freight / p.total_quantity_details()

        for d in purchase_detail:
            details = {
                'id': d.id,
                'product_id': d.product.id,
                'product': d.product.name,
                'product_code': d.product.code,
                'product_brand': d.product.product_brand.name,
                'quantity': d.quantity,
                'unit_id': d.unit.id,
                'unit_name': d.unit.name,
                'price_unit': d.price_unit,
                'price_unit_discount': d.price_unit_discount,
                'discount_one': d.discount_one,
                'discount_two': d.discount_two,
                'discount_three': d.discount_three,
                'discount_four': d.discount_four,
                'total_detail': d.total_detail,
                'check_kardex': d.check_kardex,
                'multiplicate': d.multiplicate(),
                'price_unit_discount_plus_freight': d.price_unit_discount + freight_calculate,
            }
            purchase.get('purchase_detail_set').append(details)

        dictionary.append(purchase)

    tpl = loader.get_template('buys/assignment_detail_purchase.html')
    context = ({
        'dictionary': dictionary,
    })
    return tpl.render(context)


def get_requirement_programming(request):
    if request.method == 'GET':
        truck_obj = Truck.objects.all()
        programmings = RequirementBuysProgramming.objects.filter(status='P')
        t = loader.get_template('buys/programming_requirement_buy.html')
        c = ({
            'truck_obj': truck_obj,
            'programmings': programmings,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def get_programming_invoice(request):
    if request.method == 'GET':
        programmign_buy_obj = RequirementBuysProgramming.objects.filter(status='P')
        requirement_buys = Requirement_buys.objects.filter(status=2)
        subsidiary_store_obj = SubsidiaryStore.objects.filter(category='I')
        today = datetime.now()
        fomat_today = today.strftime("%Y-%m-%d")
        t = loader.get_template('buys/programmig_invoice.html')
        c = ({
            # 'requirement_buy_obj': requirement_buy_obj,
            'programmign_buy_obj': programmign_buy_obj,
            'subsidiary_store_obj': subsidiary_store_obj,
            'requirement_buys': requirement_buys,
            'today': fomat_today,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def get_expense_programming(request):
    if request.method == 'GET':
        programmign_buy_obj = RequirementBuysProgramming.objects.filter(status='F')
        t = loader.get_template('buys/programming_expense.html')
        c = ({
            # 'requirement_buy_obj': requirement_buy_obj,
            'choices_type': ProgrammingExpense._meta.get_field('type').choices,
            'programmign_buy_obj': programmign_buy_obj,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


@csrf_exempt
def save_programming_buys(request):
    if request.method == 'GET':
        my_date = datetime.now()
        date_programming = my_date.strftime("%Y-%m-%d")

        details_request = request.GET.get('details_send', '')
        data_programming = json.loads(details_request)

        # pk = str(data_programming["pk"])
        # pk_obj = Requirement_buys.objects.get(id=int(pk))
        for detail in data_programming['Details']:
            status = (detail['status'])
            if status == 'R':
                status = 'P'

                number_scop = (detail['Number_scop'])
                truck_id = int(detail['Truck'])
                truck_obj = Truck.objects.get(id=truck_id)

                new_programming_detail = {
                    'date_programming': date_programming,
                    'number_scop': number_scop,
                    'truck': truck_obj,
                    'status': status,

                    # 'requirement_buys': pk_obj,
                }
                new_programming_detail_obj = RequirementBuysProgramming.objects.create(**new_programming_detail)
                new_programming_detail_obj.save()
                return JsonResponse({
                    'message': 'PROGRAMACION REGISTRADA CORRECTAMENTE.',

                }, status=HTTPStatus.OK)

        data = {'error': 'LAS PORGRAMACION YA FUE SE REGISTRARON.'}
        response = JsonResponse(data)
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


def get_units_by_product(request):
    if request.method == 'GET':
        id_product = request.GET.get('ip', '')
        product_obj = Product.objects.get(pk=int(id_product))
        units = Unit.objects.filter(productdetail__product=product_obj)
        units_serialized_obj = serializers.serialize('json', units)

        return JsonResponse({
            'units': units_serialized_obj,
        }, status=HTTPStatus.OK)


def get_units_product(request):
    id_product = request.GET.get('ip', '')
    product_obj = Product.objects.get(pk=int(id_product))
    units = Unit.objects.filter(productdetail__product=product_obj)
    units_serialized_obj = serializers.serialize('json', units)

    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    product_store_obj = ProductStore.objects.filter(product_id=id_product,
                                                    subsidiary_store__subsidiary=subsidiary_obj,
                                                    subsidiary_store__category='V').first()
    return JsonResponse({
        'units': units_serialized_obj,
        'stock': product_store_obj.stock,
    }, status=HTTPStatus.OK)


def get_products_by_requirement(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='G')
        requirement_id = request.GET.get('ip', '')
        requirement_obj = Requirement_buys.objects.get(pk=int(requirement_id))
        details_requirement = RequirementDetail_buys.objects.filter(requirement_buys=requirement_obj)
        product = Product.objects.filter(requirementdetail_buys__in=details_requirement)
        product_serialized_obj = serializers.serialize('json', product)

        # product_obj = Product.objects.get(pk=int(id_product))
        # units = Unit.objects.filter(productdetail__product=product_obj)
        # units_serialized_obj = serializers.serialize('json', units)

        t = loader.get_template('buys/current_stock.html')
        c = ({
            'details': details_requirement,
            'my_subsidiary_store': subsidiary_store_obj,

        })
        return JsonResponse({
            'scop': requirement_obj.number_scop,
            'creation_date': requirement_obj.creation_date,
            'approval_date': requirement_obj.approval_date,
            'products': product_serialized_obj,
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)


def get_scop_truck(request):
    if request.method == 'GET':
        programming_request = request.GET.get('programming_obj', '')
        data_programming = json.loads(programming_request)
        process = data_programming['process']
        programming = data_programming['programming']
        programing_obj = RequirementBuysProgramming.objects.get(id=programming)
        # deteil_obj = RequirementDetail_buys.objects.get(id=programming)
        truck_obj = Truck.objects.get(truck=programing_obj)
        # requirement = data_programming['requirement']
        # requirement_obj = Requirement_buys.objects.get(id=int(requirement))

        # try:
        #     nscop = RequirementBuysProgramming.objects.get(truck__id=truck_obj.id,
        #                                                    requirement_buys__id=requirement_obj.id)
        #     if (process == 'invoice'):
        #         detail_invoice_obj = Programminginvoice.objects.filter(requirementBuysProgramming=nscop)
        #         # se necesita seriezer cuando envio una lista
        #         detail_serialized_obj = serializers.serialize('json', detail_invoice_obj)
        #     else:
        #         detail_fuel_obj = ProgrammingFuel.objects.filter(requirementBuysProgramming=nscop)
        #         detail_serialized_obj = serializers.serialize('json', detail_fuel_obj)
        # except RequirementBuysProgramming.DoesNotExist:
        #     nscop = None

    return JsonResponse({
        'truck': truck_obj.license_plate,
        'condition_owner': truck_obj.condition_owner,
        # 'deteil_onj': deteil_obj,
        # 'nscop': nscop.number_scop,
        # 'programming': nscop.id,
        # 'detail_serialized': detail_serialized_obj,
        # 'units': serialized_units,
        # 'id_product_store': product_store_obj.id
    }, status=HTTPStatus.OK)


@csrf_exempt
def save_programming_invoice(request):
    if request.method == 'GET':
        details_request = request.GET.get('details_send', '')
        data_invoice = json.loads(details_request)
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        my_subsidiary_obj = get_subsidiary_by_user(user_obj)
        try:
            my_subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=my_subsidiary_obj,
                                                                  category='G')
        except SubsidiaryStore.DoesNotExist:
            data = {'error': 'No existe almacen de mercaderia.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        for detail in data_invoice['Details']:
            programing = int(detail['programming'])
            programing_obj = RequirementBuysProgramming.objects.get(id=programing)
            requirement = int(detail['requirement'])
            requirement_obj = Requirement_buys.objects.get(id=requirement)
            product = int(detail['product_id'])
            product_obj = Product.objects.get(pk=product)
            unit = int(detail['unit_id'])
            unit_obj = Unit.objects.get(pk=unit)
            # detail_requirement_obj = RequirementDetail_buys.objects.filter(requirement_buys=requirement_obj).first
            # product_obj = Product.objects.get(id=detail_requirement_obj.id)
            guide = (detail['guide'])
            date_arrive = (detail['date_arrive'])
            quantity = decimal.Decimal(detail['quantity'])
            status = (detail['status'])
            other_subsidiary_store = int(detail['store'])
            other_subsidiary_store_obj = SubsidiaryStore.objects.get(pk=other_subsidiary_store)
            if status == 'P':
                new_programming_detail = {
                    'guide': guide,
                    'quantity': quantity,
                    'requirement_buys': requirement_obj,
                    'requirementBuysProgramming': programing_obj,
                    'date_arrive': date_arrive,
                    'status': status,
                    'subsidiary_store_destiny': other_subsidiary_store_obj,
                    'subsidiary_store_origin': my_subsidiary_store_obj,
                }
                new_programming_invoice_obj = Programminginvoice.objects.create(**new_programming_detail)
                new_programming_invoice_obj.save()
                # kardex final
                try:
                    other_product_store_obj = ProductStore.objects.get(product=product_obj,
                                                                       subsidiary_store=other_subsidiary_store_obj)
                except ProductStore.DoesNotExist:
                    other_product_store_obj = None
                my_product_store = ProductStore.objects.get(product=product_obj,
                                                            subsidiary_store=my_subsidiary_store_obj)
                quantity_minimum_unit = calculate_minimum_unit(quantity, unit_obj, product_obj)
                kardex_ouput(my_product_store.id, quantity_minimum_unit,
                             programming_invoice_obj=new_programming_invoice_obj)
                if other_product_store_obj is None:
                    new_product_store_obj = ProductStore(
                        product=product_obj,
                        subsidiary_store=other_subsidiary_store_obj,
                        stock=quantity_minimum_unit
                    )
                    new_product_store_obj.save()

                    kardex_initial(
                        new_product_store_obj,
                        quantity_minimum_unit,
                        my_product_store.kardex_set.last().remaining_price,
                        programming_invoice_obj=new_programming_invoice_obj)
                else:
                    kardex_input(
                        other_product_store_obj.id,
                        quantity_minimum_unit,
                        my_product_store.kardex_set.last().remaining_price,
                        programming_invoice_obj=new_programming_invoice_obj)

                new_programming_invoice_obj.status = 'R'
                new_programming_invoice_obj.save()
        programing_obj.status = 'F'
        programing_obj.save()
        return JsonResponse({
            'message': 'TRASLADO REGISTRADO',

        }, status=HTTPStatus.OK)


# guardar detalle del requerimiento en almacen(kardex)
@csrf_exempt
def save_detail_requirement_store(request):
    if request.method == 'GET':
        id_requirement = request.GET.get('pk', '')
        requirement_obj = Requirement_buys.objects.get(pk=int(id_requirement))
        details_requirements = RequirementDetail_buys.objects.filter(requirement_buys=requirement_obj)
        # CONSULTA SI LA COMPRA YA ESTA EN ALMACEN Y ROMPE LA SECUENCIA
        if requirement_obj.status == '2':
            data = {'error': 'EL REQUERIMIENTO YA ESTA APROBADO.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        try:
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='G')
        except SubsidiaryStore.DoesNotExist:
            data = {'error': 'NO EXISTE EL ALMACEN.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        for detail in details_requirements:

            quantity = detail.quantity
            price = detail.price
            # recuperamos del producto
            product_obj = detail.product

            # recuperamos la unidad
            unit_obj = detail.unit

            try:
                product_store_obj = ProductStore.objects.get(product=product_obj, subsidiary_store=subsidiary_store_obj)
            except ProductStore.DoesNotExist:
                product_store_obj = None
            unit_min_detail_product = ProductDetail.objects.get(product=product_obj, unit=unit_obj).quantity_minimum

            if product_store_obj is None:
                new_product_store_obj = ProductStore(
                    product=product_obj,
                    subsidiary_store=subsidiary_store_obj,
                    stock=unit_min_detail_product * quantity
                )
                new_product_store_obj.save()
                kardex_initial(new_product_store_obj, unit_min_detail_product * quantity, price,
                               requirement_detail_obj=detail)
            else:
                kardex_input(product_store_obj.id, unit_min_detail_product * quantity, price,
                             requirement_detail_obj=detail)

        requirement_obj.status = '2'
        requirement_obj.save()
        return JsonResponse({
            'message': 'REQUERIMIENTO APROBADO',

        }, status=HTTPStatus.OK)


@csrf_exempt
def save_programming_fuel(request):
    if request.method == 'GET':
        details_request = request.GET.get('details_send', '')
        data_invoice = json.loads(details_request)

        for detail in data_invoice['Details']:
            programming = int(detail['programming'])
            programming_obj = RequirementBuysProgramming.objects.get(id=programming)
            invoice = (detail['invoice'])
            date_invoice = (detail['date_invoice'])
            price = (detail['price'])
            quantity = (detail['quantity'])
            noperation = (detail['noperation'])
            condition_owner = (detail['condition_owner'])
            type = (detail['type'])

            status = (detail['status'])
            if status == 'P':
                status = 'R'
                new_programming_detail = {
                    'invoice': invoice,
                    'date_invoice': date_invoice,
                    'price': price,
                    'quantity': quantity,
                    'noperation': noperation,
                    'requirementBuysProgramming': programming_obj,
                    'status': status,
                    'type': type,
                }
                new_programming_fuel_obj = ProgrammingExpense.objects.create(**new_programming_detail)
                new_programming_fuel_obj.save()

        return JsonResponse({
            'message': 'TANQUEOS REGISTRADOS CORRECTAMENTE.',

        }, status=HTTPStatus.OK)

        # data = {'error': 'LOS TANQUEOS YA SE REGISTRARON.'}
        # response = JsonResponse(data)
        # response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        # return response


@csrf_exempt
def delete_programming_fuel(request):
    if request.method == 'GET':
        details_request = request.GET.get('details_send', '')
        data_invoice = json.loads(details_request)

        pk = int(data_invoice["pk"])
        pk_obj = RequirementBuysProgramming.objects.get(id=pk)

        # new_programming_fuel_obj = ProgrammingFuel.objects.create(**new_programming_detail)
        # new_programming_fuel_obj.save()

        return JsonResponse({
            'message': 'TANQUEOS REGISTRADOS CORRECTAMENTE.',

        }, status=HTTPStatus.OK)

    data = {'error': 'LOS TANQUEOS YA SE REGISTRARON.'}
    response = JsonResponse(data)
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    return response


def get_approve_detail_requirement(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        requirement_buy_obj = Requirement_buys.objects.get(id=pk)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        t = loader.get_template('buys/approve_requirement.html')
        c = ({
            'requirement': requirement_buy_obj,
            'date_now': formatdate,
            'coin_type': RequirementDetail_buys._meta.get_field('coin').choices,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def update_details_requirement_store(request):
    if request.method == 'GET':
        requirement_request = request.GET.get('requirements', '')
        data_requirement = json.loads(requirement_request)
        date_approve = data_requirement['date_approve']
        invoice = data_requirement['invoice']
        id_requirement = data_requirement['pk']
        requirement_obj = Requirement_buys.objects.get(pk=int(id_requirement))
        if requirement_obj.status == '2':
            data = {'error': 'EL REQUERIMIENTO YA ESTA APROBADO.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        try:
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='G')
        except SubsidiaryStore.DoesNotExist:
            data = {'error': 'NO EXISTE EL ALMACEN.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        # Actualiza detalle de requerimiento
        for detail in data_requirement['Details']:
            requirement_detail_id = (detail['detail_requirement_id'])
            _price = decimal.Decimal(detail['price'])
            _amount = decimal.Decimal(detail['amount'])
            _coin = int(detail['coin'])
            _change_coin = decimal.Decimal(detail['change_coin'])
            _price_pen = decimal.Decimal(_price * _change_coin)
            _amount_pen = decimal.Decimal(_amount * _change_coin)
            requirement_detail_obj = RequirementDetail_buys.objects.get(id=requirement_detail_id)
            requirement_detail_obj.price = _price
            requirement_detail_obj.amount = _amount
            requirement_detail_obj.price_pen = _price_pen
            requirement_detail_obj.amount_pen = _amount_pen
            requirement_detail_obj.coin = _coin
            requirement_detail_obj.change_coin = _change_coin
            requirement_detail_obj.save()

            try:
                product_store_obj = ProductStore.objects.get(product=requirement_detail_obj.product,
                                                             subsidiary_store=subsidiary_store_obj)
            except ProductStore.DoesNotExist:
                product_store_obj = None
            unit_min_detail_product = ProductDetail.objects.get(product=requirement_detail_obj.product,
                                                                unit=requirement_detail_obj.unit).quantity_minimum

            if product_store_obj is None:
                new_product_store_obj = ProductStore(
                    product=requirement_detail_obj.product,
                    subsidiary_store=subsidiary_store_obj,
                    stock=unit_min_detail_product * requirement_detail_obj.quantity
                )
                new_product_store_obj.save()
                kardex_initial(new_product_store_obj,
                               round(unit_min_detail_product * requirement_detail_obj.quantity, 2),
                               requirement_detail_obj.price, requirement_detail_obj=requirement_detail_obj)
            else:
                kardex_input(product_store_obj.id, round(unit_min_detail_product * requirement_detail_obj.quantity, 2),
                             requirement_detail_obj.price, requirement_detail_obj=requirement_detail_obj)

    requirement_obj.approval_date = date_approve
    requirement_obj.invoice = invoice
    requirement_obj.status = '2'
    requirement_obj.save()
    return JsonResponse({
        'message': 'REQUERIMIENTO APROBADO',

    }, status=HTTPStatus.OK)


def get_list_requirement_stock(request):
    if request.method == 'GET':
        return JsonResponse({
            'message': 'REQUERIMIENTO APROBADO',

        }, status=HTTPStatus.OK)


def get_requirement_balance(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    requirements_obj = Requirement_buys.objects.all().filter(status=2, subsidiary__id=subsidiary_obj.id).order_by('id')
    requirements_total = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
                                                               requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
        Sum('quantity'))
    programming_invoice_total = Programminginvoice.objects.filter(requirement_buys__subsidiary=subsidiary_obj.id,
                                                                  status='R',
                                                                  requirement_buys__status=2).aggregate(
        Sum('quantity'))
    total_difference = decimal.Decimal(requirements_total['quantity__sum'] - programming_invoice_total['quantity__sum'])
    total_price = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
                                                        requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
        Sum('price'))
    # total_balance_amount = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
    #                                                              requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
    #     Sum('amount'))
    total_price_pen = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
                                                            requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
        Sum('price_pen'))
    # total_balance_amount_pen = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
    #                                                                  requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
    #     Sum('price_pen'))

    return render(request, 'buys/requirement_balance.html', {
        'requirements': requirements_obj,
        'requirements_total': requirements_total['quantity__sum'],
        'programming_invoice_total': programming_invoice_total['quantity__sum'],
        'total_difference': total_difference,
        'total_price': total_price['price__sum'],
        # 'total_amount': total_balance_amount['amount__sum'],
        'total_price_pen': total_price_pen['price_pen__sum'],
        # 'total_amount_pen': total_balance_amount_pen['amount_pen__sum'],
    })


def get_programming_by_truck_and_dates(request):
    if request.method == 'GET':
        details_request = request.GET.get('datos', '')
        if details_request != '':
            data_json = json.loads(details_request)
            id_truck = data_json['id_truck']
            date_initial = (data_json['date_initial'])
            date_final = (data_json['date_final'])
            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            truck_obj = Truck.objects.get(id=int(id_truck))
            requirementprogramming_obj = RequirementBuysProgramming.objects.filter(
                programminginvoice__requirement_buys__subsidiary=subsidiary_obj, truck=truck_obj, status='F',
                programminginvoice__date_arrive__range=(date_initial, date_final)).distinct('number_scop')

            programming_expense_total_price = ProgrammingExpense.objects.filter(
                requirementBuysProgramming__programminginvoice__date_arrive__range=(
                    date_initial, date_final), requirementBuysProgramming__truck=truck_obj,
                requirementBuysProgramming__status='F',
                requirementBuysProgramming__programminginvoice__requirement_buys__subsidiary=subsidiary_obj).aggregate(
                Sum('price'))
            programming_invoice_total_quantity = Programminginvoice.objects.filter(
                date_arrive__range=(date_initial, date_final), requirementBuysProgramming__truck=truck_obj,
                requirementBuysProgramming__status='F',
                requirement_buys__subsidiary=subsidiary_obj, status='R').aggregate(Sum('quantity'))

            tpl = loader.get_template('buys/report_programming_by_truck_and_dates_grid.html')
            context = ({
                # 'programmingsinvoice': programminginvoice_obj,
                'programmings': requirementprogramming_obj,
                'total_price': programming_expense_total_price['price__sum'],
                'total_quantity': programming_invoice_total_quantity['quantity__sum'],
            })
            return JsonResponse({
                'success': True,
                'grid': tpl.render(context),
            }, status=HTTPStatus.OK)
        else:
            trucks_obj = Truck.objects.all()
            mydate = datetime.now()
            formatdate = mydate.strftime("%Y-%m-%d")
            return render(request, 'buys/report_programming_by_truck_and_dates.html', {
                'trucks': trucks_obj,
                'date': formatdate
            })


def get_report_context_kardex_glp(subsidiary_obj, pk, is_pdf=False, get_context=False):
    other_subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(pk))  # otro almacen insumos
    my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='G')  # pluspetrol
    my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj,
                                                                 category='I')  # tu almacen insumos

    product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')
    product_store_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_glp_obj, product=product_obj)

    kardex_set = Kardex.objects.filter(product_store=product_store_obj)

    tpl = loader.get_template('buys/report_kardex_glp_grid.html')
    context = ({
        'is_pdf': is_pdf,
        'kardex_set': kardex_set,
        'my_subsidiary_store_insume': my_subsidiary_store_insume_obj,
        'other_subsidiary_store': other_subsidiary_store_obj,
    })
    if get_context:
        return context
    else:
        return tpl.render(context)


def validate_report_kardex_glp(my_subsidiary_obj):
    is_valid = True
    error = ''

    try:
        my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(
            subsidiary=my_subsidiary_obj, category='G')  # pluspetrol
    except SubsidiaryStore.DoesNotExist:
        error = 'NO EXISTE ALMACEN PLUSPETROL EN ESTA SEDE.'
        is_valid = False

    try:
        my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(
            subsidiary=my_subsidiary_obj, category='I')  # tu almacen insumos
    except SubsidiaryStore.DoesNotExist:
        error = 'NO EXISTE ALMACEN INSUMOS EN ESTA SEDE.'
        is_valid = False

    try:
        product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')
    except Product.DoesNotExist:
        error = 'NO EXISTE EL PRODUCTO GLP.'
        is_valid = False

    try:
        product_store_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_glp_obj, product=product_obj)
    except ProductStore.DoesNotExist:
        error = 'NO EXISTE EL PRODUCTO GLP EN EL ALMACEN DE PLUSPETROL DE ESTA SEDE.'
        is_valid = False

    try:
        my_product_store_supply_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_insume_obj,
                                                               product=product_obj)
    except ProductStore.DoesNotExist:
        error = 'NO EXISTE PRODUCTO GLP EN EL ALMACEN DE INSUMOS DE ESTA SEDE.'
        is_valid = False

    context = ({
        'is_valid': is_valid,
        'error': error,
    })

    return context


def get_report_kardex_glp(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    if request.method == 'GET':
        pk = request.GET.get('option', '')
        date_initial = request.GET.get('date_initial')
        date_final = request.GET.get('date_final')
        if pk != '':
            context = validate_report_kardex_glp(subsidiary_obj)
            if context.get('is_valid'):
                return JsonResponse({
                    'success': True,
                    'grid': get_kardex_dictionary(subsidiary_obj, is_pdf=False, start_date=date_initial,
                                                  end_date=date_final),
                }, status=HTTPStatus.OK)
            else:
                data = {'error': context.get('error')}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
        else:
            mydate = datetime.now()
            formatdate = mydate.strftime("%Y-%m-%d %H:%M:%S")
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            return render(request, 'buys/report_kardex_glp.html', {
                'date': formatdate,
                'date_now': date_now,
                'date_initial': date_initial,
                'date_final': date_final,
            })


def sum_inputs_from_subsidiary_store_supplies(
        k_id,
        product_store_obj,
        subsidiary_store_origin_obj,
        subsidiary_store_destiny_obj
):
    k_initial_quantity = 0
    k_inputs_quantity = 0
    query_set = Kardex.objects.filter(
        product_store=product_store_obj,
        programming_invoice__subsidiary_store_origin=subsidiary_store_origin_obj,
        programming_invoice__subsidiary_store_destiny=subsidiary_store_destiny_obj)

    k_initial_set = query_set.filter(operation='C')
    if k_initial_set.count() > 0:
        k_initial_quantity = k_initial_set.first().remaining_quantity

    k_inputs_set = query_set.filter(operation='E', id__lte=k_id + 1).values('product_store').annotate(
        total=Sum('quantity'))
    if k_inputs_set.count() > 0:
        k_inputs_quantity = k_inputs_set[0].get('total')

    return k_initial_quantity + k_inputs_quantity


def get_kardex_dictionary(my_subsidiary_obj, is_pdf=False, start_date=None, end_date=None):
    my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(
        subsidiary=my_subsidiary_obj, category='G')  # pluspetrol

    my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(
        subsidiary=my_subsidiary_obj, category='I')  # tu almacen insumos

    product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')

    product_store_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_glp_obj, product=product_obj)

    my_product_store_supply_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_insume_obj,
                                                           product=product_obj)

    dictionary = []
    merge_scope = None
    total_charge = 0
    summary = 0
    my_remaining_quantity = 0
    other_remaining_quantity = 0
    _total_quantity = 0
    _total_travel = 0
    _total_expenses = 0

    for k in Kardex.objects.filter(product_store=product_store_obj).filter(Q(
            programming_invoice__date_arrive__range=(start_date, end_date)) | Q(
        requirement_detail__requirement_buys__approval_date__range=(start_date, end_date))).order_by('create_at'):
        # filter(requirement_detail__requirement_buys__approval_date__range=(start_date, end_date)).order_by('create_at'):
        new = {
            'id': k.id,
            'programming_invoice': k.operation,
            'requirement_detail': k.product_store.id,
            'date': k.create_at,
            'inputs': [],
            'outputs': [],
            'initial': [],
            'remaining_quantity': k.remaining_quantity,
        }

        if k.programming_invoice is not None:
            if k.programming_invoice.subsidiary_store_destiny == my_subsidiary_store_insume_obj:
                my_remaining_quantity = sum_inputs_from_subsidiary_store_supplies(
                    k.id,
                    my_product_store_supply_obj,
                    my_subsidiary_store_glp_obj,
                    my_subsidiary_store_insume_obj,
                )

        if k.requirement_detail is not None:  # entradas a pluspetrol

            programming_invoice = {
                'type': '-',
                'quantity': '0',
                'my_charge': '0',
                'other_charge': '0',
                'total_charge': '0',
                'owner': '-',
                'license_plate': '-',
                'subsidiary': '-',
                'invoices': '-',
                'number_scop': '-',
                'date_programming': '-',
                'summary': summary,
                'my_remaining_quantity': my_remaining_quantity,
                'other_remaining_quantity': other_remaining_quantity,
            }
            new.get('outputs').append(programming_invoice)

            rd = k.requirement_detail
            _total_quantity = _total_quantity + rd.quantity
            requirement_detail = {
                'type': 'Compra',
                'quantity': rd.quantity,
                'invoice': rd.requirement_buys.invoice,
                'date': rd.requirement_buys.approval_date,
                'programmings': [],
            }

            new.get('inputs').append(requirement_detail)

            dictionary.append(new)

        else:

            requirement_detail = {
                'type': '-',
                'quantity': '0',
                'invoice': '-',
                'programmings': '-'
            }
            new.get('inputs').append(requirement_detail)

            if k.programming_invoice is not None:  # salida en pluspetrol y entrada en otro almacen

                pi = k.programming_invoice
                invoices = []

                for p in Requirement_buys.objects.filter(
                        programminginvoice__requirementBuysProgramming__id=pi.requirementBuysProgramming.id):
                    i = {
                        'id': p.id,
                        'invoice': p.invoice,
                        'quantity_invoice': p.programminginvoice_set.filter(
                            requirementBuysProgramming__id=pi.requirementBuysProgramming.id,
                            requirement_buys_id=p.id).first().quantity
                    }
                    invoices.append(i)
                # gastos de comustible
                expenses = []
                expenses_set = ProgrammingExpense.objects.filter(
                    requirementBuysProgramming__id=pi.requirementBuysProgramming.id)
                for es in expenses_set:
                    e = {
                        'id': es.id,
                        'invoice': es.invoice,
                        'date': es.date_invoice,
                        'type': es.get_type_display(),
                        'price': es.price,
                        # 'total': es.price * es.quantity,
                    }
                    expenses.append(e)
                    _total_expenses = _total_expenses + es.price

                my_charge = 0
                other_charge = 0

                charge_set = Programminginvoice.objects.filter(
                    requirementBuysProgramming_id=pi.requirementBuysProgramming.id,
                    subsidiary_store_origin=my_subsidiary_store_glp_obj)

                my_charge_set = charge_set.filter(
                    subsidiary_store_destiny=my_subsidiary_store_insume_obj). \
                    values('requirementBuysProgramming').annotate(totals=Sum('quantity'))
                if my_charge_set.count() > 0:
                    my_charge = my_charge_set[0].get('totals')
                    total_charge = total_charge + my_charge

                if merge_scope == pi.requirementBuysProgramming.number_scop:
                    dictionary.pop(len(dictionary) - 1)
                    total_charge = total_charge - other_charge - my_charge
                    _total_travel = _total_travel - 1
                _total_travel = _total_travel + 1
                programming_invoice = {
                    'type': 'Salida' + "-" + str(_total_travel),
                    'quantity': pi.calculate_total_programming_quantity(),
                    'my_charge': my_charge,
                    'other_charge': other_charge,
                    'total_charge': total_charge,
                    'owner': pi.requirementBuysProgramming.truck.owner,
                    'license_plate': pi.requirementBuysProgramming.truck.license_plate,
                    'subsidiary': pi.subsidiary_store_destiny.subsidiary.name,
                    'invoices': invoices,
                    'number_scop': pi.requirementBuysProgramming.number_scop,
                    'expenses': expenses,
                    'date_programming': pi.date_arrive,
                    'summary': summary,
                    'my_remaining_quantity': my_remaining_quantity,
                    'other_remaining_quantity': other_remaining_quantity,
                }
                merge_scope = pi.requirementBuysProgramming.number_scop
                new.get('outputs').append(programming_invoice)

                dictionary.append(new)

            else:  # kardex inicial en pluspetrol
                programming_invoice = {
                    'type': '-',
                    'quantity': '0',
                    'license_plate': '-',
                    'subsidiary': '-',
                    'invoices': '-',
                    'number_scop': '-',
                    'date_programming': '-',
                    'summary': summary,
                    'my_remaining_quantity': my_remaining_quantity,
                    'other_remaining_quantity': other_remaining_quantity,
                }
                new.get('outputs').append(programming_invoice)

                initial = {
                    'type': 'Inicio',
                    'quantity': k.remaining_quantity
                }
                new.get('initial').append(initial)

                dictionary.append(new)

    tpl = loader.get_template('buys/report_kardex_dictionary.html')
    context = ({
        'dictionary': dictionary,
        'is_pdf': is_pdf,
        'start_date': start_date,
        'end_date': end_date,
        'total_input': _total_quantity,
        'total_travel': _total_travel,
        'total_expenses': _total_expenses,
    })

    return tpl.render(context)
    # return render(request, 'buys/report_kardex_dictionary.html', {'dictionary': dictionary}) //un template renderizado


# Actualizar estado de la compra
def update_state_annular_purchase(request):
    if request.method == 'GET':
        id_purchase = request.GET.get('pk', '')
        purchase_obj = Purchase.objects.get(pk=int(id_purchase))
        if purchase_obj.status == 'A':
            data = {'error': 'LA COMPRA YA ESTA APROBADA NO ES POSIBLE ANULAR'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        purchase_obj.status = 'N'
        purchase_obj.save()
    return JsonResponse({
        'message': 'COMPRA ANULADA CORRECTAMENTE',

    }, status=HTTPStatus.OK)


def get_details_by_purchase(request):
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


def get_product_by_criteria_table(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
        value = request.GET.get('value', '')
        array_value = value.split()
        product_query = Product.objects
        full_query = None
        product_list = []

        for i in range(0, len(array_value)):
            q = Q(name__icontains=array_value[i]) | Q(product_brand__name__icontains=array_value[i])
            if full_query is None:
                full_query = q
            else:
                full_query = full_query & q

        product_set = product_query.filter(full_query).select_related(
            'product_family', 'product_brand').order_by('id')

        if not product_set:
            data = {'error': 'NO EXISTE EL PRODUCTO, FAVOR DE INGRESAR PRODUCTO EXISTENTE.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        for e in product_set:
            unit_id = ''
            unit_name = ''
            price_sale = ''
            stock = 0
            product_store_id = ''
            price_purchase = ''
            barcode = ''

            if e.productdetail_set.exists():
                unit_id = e.productdetail_set.last().unit.id
                unit_name = e.productdetail_set.last().unit.name
                price_sale = e.productdetail_set.last().price_sale
                price_purchase = e.productdetail_set.last().price_purchase

            product_store_set = ProductStore.objects.filter(product_id=e.id, subsidiary_store=subsidiary_store_obj)

            if product_store_set.exists():
                product_store_obj = product_store_set.first()
                stock = product_store_obj.stock
                product_store_id = product_store_obj.id

            item_product_list = {
                'id': e.id,
                'name': e.name,
                'brand': e.product_brand.name,
                'unit': unit_name,
                'unit_id': unit_id,
                'price_sale': price_sale,
                'price_purchase': price_purchase,
                'stock': stock,
                'product_store_id': product_store_id,
                'barcode': e.barcode if e.barcode is not None else ''
            }
            product_list.append(item_product_list)

        return JsonResponse({
            'productList': product_list,
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

    return render(request, 'buys/buy_list_edit.html', {
        'purchase': purchase_obj,
        'choices_payments_purchase': Purchase._meta.get_field('type_pay').choices,
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

        base_total = decimal.Decimal(data_purchase["Base_Total"])
        igv_total = decimal.Decimal(data_purchase["Igv_Total"])
        total_import = decimal.Decimal(data_purchase["Import_Total"])
        total_document = decimal.Decimal(data_purchase["Total_Document"])
        # total_freight = decimal.Decimal(data_purchase["TotalFreight"])

        check_igv = bool(int(data_purchase["Check_Igv"]))
        check_dollar = bool(int(data_purchase["Check_Dollar"]))

        # document_freight = str(data_purchase["Freight"][0]["DocumentFreight"])
        # serial_freight = str(data_purchase["Freight"][0]["SerialFreight"])
        # number_freight = str(data_purchase["Freight"][0]["NumberFreight"])
        # date_freight = str(data_purchase["Freight"][0]["DateFreight"])
        # total_freight = decimal.Decimal(data_purchase["Freight"][0]["TotalFreight"])

        supplier_obj = Supplier.objects.get(id=int(provider_id))

        try:
            purchase_id = request.GET.get('purchase_id', '')
            purchase_obj = Purchase.objects.get(id=purchase_id)
        except Purchase.DoesNotExist:
            purchase_id = 0

        if purchase_id == 0:
            data = {'error': 'NO EXISTE COMPRA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        else:
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
                    purchase_due_obj = PurchaseDues.objects.get(id=du_id)
                    amount_due = decimal.Decimal(du['amountDue'])

                    purchase_due_obj.purchase = purchase_obj
                    purchase_due_obj.due = amount_due
                    purchase_due_obj.save()

                else:
                    amount_due = decimal.Decimal(du['amountDue'])

                    purchase_due_obj = PurchaseDues(
                        purchase=purchase_obj,
                        due=amount_due
                    )
                    purchase_due_obj.save()

            for detail in data_purchase['Details']:

                if detail['ProductDetail'] != 'NaN':

                    product_detail_id = int(detail['ProductDetail'])
                    purchase_detail_obj = PurchaseDetail.objects.get(id=product_detail_id)

                    product_id = int(detail['Product'])
                    product_obj = Product.objects.get(id=product_id)

                    unit_id = int(detail['Unit'])
                    unit_obj = Unit.objects.get(id=unit_id)

                    quantity = str(detail['Quantity'])
                    price = decimal.Decimal(detail['Price'])
                    price_unit_discount = decimal.Decimal(detail['Price_Unit_Discount'])

                    dt1 = decimal.Decimal(detail['Dto1'])
                    dt2 = decimal.Decimal(detail['Dto2'])
                    dt3 = decimal.Decimal(detail['Dto3'])
                    dt4 = decimal.Decimal(detail['Dto4'])

                    total_detail = decimal.Decimal(detail['Total'])
                    checked_kardex = bool(int(detail["Check_kardex"]))

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

                    product_serial_to_delete = ProductSerial.objects.filter(purchase_detail=purchase_detail_obj)
                    product_serial_to_delete.delete()

                else:
                    product_id = int(detail['Product'])
                    product_obj = Product.objects.get(id=product_id)

                    unit_id = int(detail['Unit'])
                    unit_obj = Unit.objects.get(id=unit_id)

                    quantity = decimal.Decimal(detail['Quantity'])
                    price = decimal.Decimal(detail['Price'])
                    price_unit_discount = decimal.Decimal(detail['Price_Unit_Discount'])

                    dt1 = decimal.Decimal(detail['Dto1'])
                    dt2 = decimal.Decimal(detail['Dto2'])
                    dt3 = decimal.Decimal(detail['Dto3'])
                    dt4 = decimal.Decimal(detail['Dto4'])

                    total_detail = decimal.Decimal(detail['Total'])
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

                for serial in detail['Serials']:
                    product_serial_obj = ProductSerial(
                        serial_number=serial['Serial'],
                        purchase_detail=purchase_detail_obj,
                        status='P'
                    )
                    product_serial_obj.save()

            purchase_obj.save()

        return JsonResponse({
            'message': 'Compra Actualizada',
        }, status=HTTPStatus.OK)


def delete_item_product_buy(request):
    if request.method == 'GET':
        detail_id = request.GET.get('detail_id', '')
        purchase_detail = PurchaseDetail.objects.get(id=detail_id)
        purchase_detail.delete()

        return JsonResponse({
            'message': 'Eliminado.',
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

        purchase_set = Purchase.objects.filter(supplier__id=int(supplier), type_bill=type_bill, bill_number=correlative)
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
        flag = False
        serial = request.GET.get('serial', '')
        product = request.GET.get('product', '')

        product_serial_set = ProductSerial.objects.filter(serial_number=serial)
        if product_serial_set.exists():
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