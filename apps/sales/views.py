from django.core.exceptions import ValidationError
from django.db.models.functions import Coalesce, Cast
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import TemplateView, View, CreateView, UpdateView
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponse
from http import HTTPStatus

from .api_FACT import send_bill_4_fact, send_receipt_4_fact, send_credit_note_fact, annul_invoice
from .format_dates import validate
from .models import *
from .forms import *
import pytz
from apps.hrm.models import Subsidiary, District, DocumentType, Employee, Worker, Nationality
from apps.comercial.models import DistributionMobil, Truck, DistributionDetail, ClientAdvancement, ClientProduct
from django.contrib.auth.models import User
from apps.hrm.views import get_subsidiary_by_user
from apps.accounting.views import TransactionAccount, LedgerEntry, get_account_cash, Cash, CashFlow, AccountingAccount
import json
import decimal
import math
import random
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import ImageFieldFile
from django.template import loader
from datetime import datetime, date
from django.db import DatabaseError, IntegrityError, transaction
from django.core import serializers
from apps.sales.views_SUNAT import send_bill_nubefact, send_receipt_nubefact, query_dni, query_api_facturacioncloud, \
    query_api_free_ruc, query_api_peru, send_cancel_bill_nubefact, query_apis_net_dni_ruc
from apps.sales.models import OrderBill
from apps.sales.number_to_letters import numero_a_letras, numero_a_moneda
from django.db.models import Min, Sum, Max, Q, Prefetch, Subquery, OuterRef, Value, Exists
from electrical import settings
import os
from django.db.models import F, IntegerField
from ..buys.models import PurchaseDetail, Purchase


class Home(TemplateView):
    template_name = 'sales/home.html'


class ProductList(View):
    model = Product
    form_class = FormProduct
    template_name = 'sales/product_list.html'

    def get_queryset(self):
        return self.model.objects.all()

    def get_context_data(self, **kwargs):
        user = self.request.user.id
        user_obj = User.objects.get(id=int(user))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        product_brand_set = ProductBrand.objects.all()
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        context = {
            'products': self.get_queryset(),
            'subsidiary': subsidiary_obj,
            'product_brand_set': product_brand_set,
            'form': self.form_class,
            'date': formatdate
        }
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class JsonProductList(View):
    def get(self, request):
        products = Product.objects.filter(is_enabled=True)
        user = self.request.user.id
        user_obj = User.objects.get(id=int(user))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        t = loader.get_template('sales/product_grid_list.html')
        c = ({'products': products, 'subsidiary': subsidiary_obj})
        return JsonResponse({'result': t.render(c)})


class JsonProductCreate(CreateView):
    model = Product
    form_class = FormProduct
    template_name = 'sales/product_create.html'

    def post(self, request):
        data = dict()
        form = FormProduct(request.POST, request.FILES)

        if form.is_valid():
            print('isvalid()')
            product = form.save()
            # converting a database model to a dictionary...
            data['product'] = model_to_dict(product)
            # Encode into JSON formatted Data
            result = json.dumps(data, cls=ExtendedEncoder)
            # Para pasar cualquier otro objeto serializable JSON, debe establecer el parámetro seguro en False.
            response = JsonResponse(result, safe=False)
            # change status code in JsonResponse
            response.status_code = HTTPStatus.OK
        else:
            # use form.errors to add the error msg as a dictonary
            data['error'] = "form not valid!"
            data['form_invalid'] = form.errors
            # Por defecto, el primer parámetro de JsonResponse, debe ser una instancia dict.
            # Para pasar cualquier otro objeto serializable JSON, debe establecer el parámetro seguro en False.
            response = JsonResponse(data)
            # change status code in JsonResponse
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


class JsonProductUpdate(UpdateView):
    model = Product
    form_class = FormProduct
    template_name = 'sales/product_update.html'

    def post(self, request, pk):
        data = dict()
        product = self.model.objects.get(pk=pk)
        # form = SnapForm(request.POST, request.FILES, instance=instance)
        form = self.form_class(instance=product, data=request.POST, files=request.FILES)
        if form.is_valid():
            product = form.save()
            data['product'] = model_to_dict(product)
            result = json.dumps(data, cls=ExtendedEncoder)
            response = JsonResponse(result, safe=False)
            response.status_code = HTTPStatus.OK
        else:
            data['error'] = "form not valid!"
            data['form_invalid'] = form.errors
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


def get_product(request):
    data = {}
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            product_obj = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            data['error'] = "producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary = Subsidiary.objects.filter(id=subsidiary_obj.id)
        subsidiary_store_set = SubsidiaryStore.objects.filter(subsidiary__id=subsidiary_obj.id, category='V')

        _product_id = request.GET.get('_product_id', '')
        product_dict = []
        # product = Product.objects.get(id=_product_id)
        product_store_set = ProductStore.objects.filter(product_id=product_obj.id,
                                                        subsidiary_store__subsidiary=subsidiary_obj, ).values(
            'id',
            'subsidiary_store__name',
            'subsidiary_store__category',
            'subsidiary_store__id',
            'subsidiary_store__subsidiary__id',
            'subsidiary_store__subsidiary__name',
            'subsidiary_store__subsidiary__serial',
            'stock',
            'product__name',
            'product__id',
            'product__code',
        )

        for p in product_store_set:
            product_item = {
                'id': p['id'],
                'name': p['product__name'],
                'code': p['product__code'],
                'product_store_set': product_store_set,
            }
            product_dict.append(product_item)

        units = Unit.objects.all()

        unit_min_obj = None
        product_detail = ProductDetail.objects.filter(
            product=product_obj).annotate(Min('quantity_minimum'))

        if product_detail.count() > 0:
            unit_min_obj = product_detail.first().unit

        t = loader.get_template('sales/product_update_quantity_on_hand.html')
        c = ({'product': product_obj,
              'subsidiaries': subsidiary,
              # 'inventories': inventories,
              'units': units,
              'unit_min': unit_min_obj,
              'own_subsidiary': subsidiary_obj,
              # 'product': product,
              'product_dict': product_dict,
              'subsidiary_store': subsidiary_store_set,
              })

        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })
        # return JsonResponse({
        #     'grid': t.render(c, request),
        #
        # }, status=HTTPStatus.OK)


def new_quantity_on_hand(request):
    if request.method == 'GET':
        store_request = request.GET.get('stores', '')
        data = json.loads(store_request)

        product_id = str(data['Product'])
        product = Product.objects.get(pk=int(product_id))

        for detail in data['Details']:
            if detail['Operation'] == 'create':
                subsidiary_store_id = str(detail['SubsidiaryStore'])
                subsidiary_store = SubsidiaryStore.objects.get(pk=int(subsidiary_store_id))

                new_stock = 0
                new_price_unit = 0

                if detail['Quantity']:
                    new_stock = decimal.Decimal(detail['Quantity'])

                    if detail['Price']:
                        new_price_unit = decimal.Decimal(detail['Price'])

                        if detail['Unit'] != '0':
                            unit_obj = Unit.objects.get(id=int(detail['Unit']))

                            search_product_detail_set = ProductDetail.objects.filter(
                                unit=unit_obj, product=product)

                            if search_product_detail_set.count == 0:
                                product_detail_obj = ProductDetail(
                                    product=product,
                                    price_sale=new_price_unit,
                                    unit=unit_obj,
                                    quantity_minimum=1
                                )
                                product_detail_obj.save()
                        # New product store
                        new_product_store = {
                            'product': product,
                            'subsidiary_store': subsidiary_store,
                            'stock': new_stock
                        }
                        product_store_obj = ProductStore.objects.create(**new_product_store)
                        product_store_obj.save()

                        kardex_initial(product_store_obj, new_stock, new_price_unit)

                    else:
                        data = {'error': "Precio no existe!"}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response
        return JsonResponse({
            'success': True,
        })


def get_recipe_by_product(request):
    if request.method == 'GET':
        store_request = request.GET.get('stores', '')
        data = json.loads(store_request)

        product_id = str(data['Product'])
        product = Product.objects.get(pk=int(product_id))

        for detail in data['Details']:
            if detail['Operation'] == 'create':
                subsidiary_store_id = str(detail['SubsidiaryStore'])
                subsidiary_store = SubsidiaryStore.objects.get(pk=int(subsidiary_store_id))

                new_stock = 0
                new_price_unit = 0

                if detail['Quantity']:
                    new_stock = decimal.Decimal(detail['Quantity'])

                    if detail['Price']:
                        new_price_unit = decimal.Decimal(detail['Price'])

                        if detail['Unit'] != '0':
                            unit_obj = Unit.objects.get(id=int(detail['Unit']))

                            product_detail_obj = ProductDetail(
                                product=product,
                                price_sale=new_price_unit,
                                unit=unit_obj,
                                quantity_minimum=1
                            )
                            product_detail_obj.save()

                        # New product store
                        new_product_store = {
                            'product': product,
                            'subsidiary_store': subsidiary_store,
                            'stock': new_stock
                        }
                        product_store_obj = ProductStore.objects.create(**new_product_store)
                        product_store_obj.save()

                        kardex_initial(product_store_obj, new_stock, new_price_unit)

                    else:
                        data = {'error': "Precio no existe!"}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response
        return JsonResponse({
            'success': True,
        })


def get_kardex_by_product(request):
    data = dict()
    mydate = datetime.now()
    formatdate = mydate.strftime("%Y-%m-%d")
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            data['error'] = "producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        # products = Product.objects.all()
        subsidiaries = Subsidiary.objects.all()
        subsidiaries_stores = SubsidiaryStore.objects.filter(category='V')
        # check product detail
        basic_product_detail = ProductDetail.objects.filter(
            product=product, quantity_minimum=1)
        # kardex = Kardex.objects.filter(product_id=pk)
        t = loader.get_template('sales/kardex.html')
        c = ({
            'product': product,
            'subsidiaries': subsidiaries,
            'basic_product_detail': basic_product_detail,
            'subsidiaries_stores': subsidiaries_stores,
            # 'products': products,
            'date_now': formatdate,
        })

        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def get_list_kardex(request):
    data = dict()
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        pk_subsidiary_store = request.GET.get('subsidiary_store', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')

        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            data['error'] = "producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        subsidiary_store = SubsidiaryStore.objects.get(id=pk_subsidiary_store)

        try:
            product_store = ProductStore.objects.filter(
                product_id=product.id).filter(subsidiary_store_id=subsidiary_store.id)

        except ProductStore.DoesNotExist:
            data['error'] = "almacen producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        inventories = None
        if product_store.count() > 0:
            inventories = Kardex.objects.filter(
                product_store=product_store[0], create_at__date__range=[start_date, end_date]
            ).select_related(
                'product_store__product',
                'purchase_detail',
                'order_detail__order',
                'loan_payment',
                'guide_detail__guide__guide_motive',
                'credit_note_detail__credit_note'
            ).order_by('id')

        t = loader.get_template('sales/kardex_grid_list.html')
        c = ({'product': product, 'inventories': inventories})

        return JsonResponse({
            'success': True,
            'form': t.render(c),
        })


class ExtendedEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, ImageFieldFile):
            return str(o)
        else:
            return super().default(o)


class ClientList(View):
    model = Client
    form_class = FormClient
    template_name = 'sales/client_list.html'

    def get_queryset(self):
        return self.model.objects.all().prefetch_related(
            Prefetch(
                'clienttype_set',
                queryset=ClientType.objects.select_related('document_type')
            ),
            Prefetch(
                'clientaddress_set',
                queryset=ClientAddress.objects.select_related('district')
            ),
            Prefetch(
                'clientassociate_set',
                queryset=ClientAssociate.objects.select_related('subsidiary', 'subsidiary__district')
            )
        ).order_by('id')

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['clients'] = self.get_queryset()  # agregamos la consulta al contexto
        contexto['form'] = self.form_class
        contexto['document_types'] = DocumentType.objects.all()
        contexto['districts'] = District.objects.all()
        contexto['subsidiaries'] = Subsidiary.objects.all()
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


@csrf_exempt
def new_client(request):
    data = dict()
    print(request.method)
    if request.method == 'POST':

        names = request.POST.get('names')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        email = request.POST.get('email', '')
        document_number = request.POST.get('document_number', '')
        document_type_id = request.POST.get('document_type', '')
        id_district = request.POST.get('id_district', '')
        reference = request.POST.get('reference', '')
        operation = request.POST.get('operation', '')
        client_id = int(request.POST.get('client_id', ''))  # solo se usa al editar

        if operation == 'N':

            if len(names) > 0:

                data_client = {
                    'names': names,
                    'phone': phone,
                    'email': email,
                }

                client = Client.objects.create(**data_client)
                client.save()

                if len(document_number) > 0:

                    try:
                        document_type = DocumentType.objects.get(id=document_type_id)
                    except DocumentType.DoesNotExist:
                        data['error'] = "Documento no existe!"
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response

                    data_client_type = {
                        'client': client,
                        'document_type': document_type,
                        'document_number': document_number,
                    }
                    client_type = ClientType.objects.create(**data_client_type)
                    client_type.save()

                    if len(address) > 0:

                        try:
                            district = District.objects.get(id=id_district)
                        except District.DoesNotExist:
                            data['error'] = "Distrito no existe!"
                            response = JsonResponse(data)
                            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                            return response

                        data_client_address = {
                            'client': client,
                            'address': address,
                            'district': district,
                            'reference': reference,
                        }
                        client_address = ClientAddress.objects.create(**data_client_address)
                        client_address.save()
                return JsonResponse({'success': True, 'message': 'El cliente se registro correctamente.'})
        else:

            client_obj = Client.objects.get(pk=client_id)
            client_obj.names = names
            client_obj.phone = phone
            client_obj.email = email
            client_obj.save()
            district_obj = None
            if request.POST.get('id_district', '') != '0':
                district_obj = District.objects.get(id=id_district)
            document_type = DocumentType.objects.get(id=document_type_id)

            client_address_set = ClientAddress.objects.filter(client_id=client_id)
            if client_address_set:
                client_address_obj = client_address_set.first()

                client_address_obj.address = address
                client_address_obj.district = district_obj
                client_address_obj.reference = reference
                client_address_obj.save()
            else:
                data_client_address = {
                    'client': client_obj,
                    'address': address,
                    'district': district_obj,
                    'reference': reference,
                }
                client_address = ClientAddress.objects.create(**data_client_address)
                client_address.save()

            client_type_set = ClientType.objects.filter(client_id=client_id)
            if client_type_set:
                client_type_obj = client_type_set.first()
                client_type_obj.document_type = document_type
                client_type_obj.document_number = document_number
                client_type_obj.save()
            else:
                data_client_type = {
                    'client': client_obj,
                    'document_type': document_type,
                    'document_number': document_number,
                }
                client_type = ClientType.objects.create(**data_client_type)
                client_type.save()

            return JsonResponse({'success': True, 'message': 'El cliente se actualizo correctamente.'})
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def new_client_associate(request):
    data = dict()
    print(request.method)
    if request.method == 'GET':

        id = request.GET.get('client_id')
        names = request.GET.get('names')
        associates = request.GET.get('associates', '')
        _arr = []
        if associates != '[]':
            str1 = associates.replace(']', '').replace('[', '')
            _arr = str1.replace('"', '').split(",")
            client_obj = Client.objects.get(id=int(id))
            associated_set = ClientAssociate.objects.filter(client=client_obj)
            associated_set.delete()
            for a in _arr:
                subsidiary_obj = Subsidiary.objects.get(id=int(a))
                client_associate_obj = ClientAssociate(client=client_obj, subsidiary=subsidiary_obj)
                client_associate_obj.save()
        else:
            data['error'] = "Ingrese valores validos."
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        return JsonResponse({'success': True, 'message': 'El cliente se asocio correctamente.'})
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_photo(photo=None):
    # _path = str(settings.MEDIA_URL + p['photo']).replace('/', '\\')
    print('111' + photo)
    _path_real_cache = str(
        settings.MEDIA_ROOT + 'CACHE/images/' + photo.replace('.png', '/').replace('.jpg', '/')
    ).replace('/', '\\')
    dir_path = os.path.dirname(_path_real_cache)
    print('222' + _path_real_cache)
    print('333' + dir_path)
    _file_name = ''
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.jpg'):
                _file_name = str(file)
                print('444' + _file_name)
    _path_cache = str(
        settings.MEDIA_URL + 'CACHE/images/' + photo.replace('.png', '/').replace('.jpg', '/') + _file_name
    )
    print('555' + _path_cache)
    return _path_cache


class SalesList(View):
    template_name = 'sales/sales_list.html'

    def get_context_data(self, **kwargs):
        data = dict()
        error = ""
        user_id = self.request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        pk = self.kwargs.get('pk', None)
        letter = self.kwargs.get('letter', None)
        contexto = {}
        if pk is not None:
            contexto['list_distribution'] = DistributionMobil.objects.get(id=int(pk))
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        # try:
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        sales_store = None
        if subsidiary_obj is None:
            error = "No tiene una sede definida."
        else:
            sales_store = SubsidiaryStore.objects.filter(
                subsidiary=subsidiary_obj, category='V').first()

        product_dic = []
        if sales_store is None:
            error = "No tiene un almacen de ventas registrado, Favor de registrar un almacen primero."
        # else:
        #     price_p = 0
        #     for p in Product.objects.filter(is_enabled=True,
        #                                     productstore__subsidiary_store=sales_store,
        #                                     productdetail__quantity_minimum=1).values('id',
        #                                                                               'name', 'code', 'photo',
        #                                                                               'stock_min', 'stock_max',
        #                                                                               'productstore__stock',
        #                                                                               'productdetail__price_sale',
        #                                                                               'productdetail__unit__name'):
        #         price_p = PurchaseDetail.objects.filter(product__id=p['id']).values('price_unit')
        #         new_product = {
        #             'id': p['id'],
        #             'name': p['name'],
        #             'code': p['code'],
        #             'photo': p['photo'],
        #             'path_cache': get_photo(p['photo']),
        #             'stock_min': p['stock_min'],
        #             'stock_max': p['stock_max'],
        #             'stock': p['productstore__stock'],
        #             'price': p['productdetail__price_sale'],
        #             'unit': p['productdetail__unit__name'],
        #             'price_purchase': price_p.last(),
        #         }
        #         product_dic.append(new_product)

        worker_obj = Worker.objects.filter(user=user_obj).last()
        employee = Employee.objects.get(worker=worker_obj)
        document_types = DocumentType.objects.all()
        # clients = Client.objects.all()
        series_set = Subsidiary.objects.filter(id=subsidiary_obj.id)

        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')

        users_set = User.objects.all()

        contexto['choices_account'] = cash_set
        contexto['choices_account_bank'] = cash_deposit_set
        contexto['employee'] = employee
        contexto['error'] = error
        contexto['sales_store'] = sales_store
        contexto['subsidiary'] = subsidiary_obj
        contexto['product_dic'] = product_dic
        contexto['document_types'] = document_types
        # contexto['clients'] = clients
        contexto['date'] = formatdate
        contexto['distribution'] = pk
        contexto['choices_payments'] = TransactionPayment._meta.get_field('type').choices
        contexto['electronic_invoice'] = letter
        contexto['series'] = series_set
        contexto['users'] = users_set

        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


def get_client(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        client_set = Client.objects.filter(id=pk)
        client_address_set = ClientAddress.objects.filter(client_id=pk)
        client_type_set = ClientType.objects.filter(client_id=pk)
        client_bill_set = OrderBill.objects.filter(order__client__id=client_set.first().id)
        client_serialized_data = serializers.serialize('json', client_set)
        client_serialized_data_address = serializers.serialize('json', client_address_set)
        client_serialized_data_type = serializers.serialize('json', client_type_set)
        client_bill = serializers.serialize('json', client_bill_set)
        client_product_set = ClientProduct.objects.filter(client=client_set.first())
        tpl = loader.get_template('sales/table_client_advancement.html')
        context = ({
            'client_product_set': client_product_set,
        })
        return JsonResponse({
            'success': True,
            'client_names': client_set.first().names,
            'client_serialized': client_serialized_data,
            'client_serialized_data_address': client_serialized_data_address,
            'client_serialized_data_type': client_serialized_data_type,
            'client_bill': client_bill,
            'grid': tpl.render(context),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


# @csrf_exempt
def set_product_detail(request):
    data = {}
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            product_obj = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            data['error'] = "producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        products = Product.objects.all()
        units = Unit.objects.all()
        t = loader.get_template('sales/product_detail.html')
        c = ({
            'product': product_obj,
            'units': units,
            'products': products,
        })

        product_details = ProductDetail.objects.filter(product=product_obj).order_by('id')
        tpl2 = loader.get_template('sales/product_detail_grid_list.html')
        context2 = ({'product_details': product_details, })
        serialized_data = serializers.serialize('json', product_details)
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
            'grid': tpl2.render(context2),
            'serialized_data': serialized_data,
            # 'form': t.render(c),
        }, status=HTTPStatus.OK)
    else:
        if request.method == 'POST':
            id_product = request.POST.get('product', '')
            price_sale = request.POST.get('price_sale', '')
            id_unit = request.POST.get('unit', '')
            p1 = request.POST.get('id_p1', '')
            p2 = request.POST.get('id_p2', '')
            p3 = request.POST.get('id_p3', '')
            price_purchase = request.POST.get('id_price_purchase', '')
            quantity_minimum = request.POST.get('quantity_minimum', '')

            if decimal.Decimal(price_sale) == 0 or decimal.Decimal(quantity_minimum) == 0:
                data['error'] = "Ingrese valores validos."
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            product_obj = Product.objects.get(id=int(id_product))
            unit_obj = Unit.objects.get(id=int(id_unit))

            try:
                product_detail_obj = ProductDetail(
                    product=product_obj,
                    price_sale=decimal.Decimal(price_sale),
                    unit=unit_obj,
                    quantity_minimum=decimal.Decimal(quantity_minimum),
                    percentage_one=p1,
                    percentage_two=p2,
                    percentage_three=p3,
                    price_purchase=decimal.Decimal(price_purchase)
                )
                product_detail_obj.save()
            except DatabaseError as e:
                data['error'] = str(e)
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            except IntegrityError as e:
                data['error'] = str(e)
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            product_details = ProductDetail.objects.filter(product=product_obj).order_by('id')
            tpl2 = loader.get_template('sales/product_detail_grid_list.html')
            context2 = ({'product_details': product_details, })

            return JsonResponse({
                'message': 'Guardado con exito.',
                'grid': tpl2.render(context2),
            }, status=HTTPStatus.OK)


def get_product_detail(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        product_detail_obj = ProductDetail.objects.filter(id=pk)
        serialized_obj = serializers.serialize('json', product_detail_obj)
        return JsonResponse({'obj': serialized_obj}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def toogle_status_product_detail(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        text_status = request.GET.get('status', '')
        status = False
        if text_status == 'True':
            status = True
        product_detail_obj = ProductDetail.objects.get(id=pk)
        product_detail_obj.is_enabled = status
        product_detail_obj.save()

        return JsonResponse({'message': 'Cambios guardados con exito.'}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def delete_product_detail(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        product_detail_obj = ProductDetail.objects.get(id=pk)
        product_detail_obj.delete()

        return JsonResponse({'message': 'Cambios guardados con exito.'}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def update_product_detail(request):
    data = dict()
    if request.method == 'POST':
        id_product_detail = request.POST.get('product_detail', '')
        id_product = request.POST.get('product', '')
        price_sale = request.POST.get('price_sale', '')
        id_unit = request.POST.get('unit', '')
        p1 = request.POST.get('id_p1', '')
        p2 = request.POST.get('id_p2', '')
        p3 = request.POST.get('id_p3', '')
        price_purchase = request.POST.get('id_price_purchase', '')
        quantity_minimum = request.POST.get('quantity_minimum', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        if decimal.Decimal(price_sale) == 0 or decimal.Decimal(quantity_minimum) == 0:
            data['error'] = "Ingrese valores validos."
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        product_obj = Product.objects.get(id=int(id_product))
        unit_obj = Unit.objects.get(id=int(id_unit))

        product_detail_obj = ProductDetail.objects.get(id=int(id_product_detail))
        product_detail_obj.quantity_minimum = decimal.Decimal(quantity_minimum)
        product_detail_obj.price_sale = decimal.Decimal(price_sale)
        product_detail_obj.product = product_obj
        product_detail_obj.unit = unit_obj
        product_detail_obj.percentage_one = p1
        product_detail_obj.percentage_two = p2
        product_detail_obj.percentage_three = p3
        product_detail_obj.price_purchase = decimal.Decimal(price_purchase)
        product_detail_obj.user = user_obj
        product_detail_obj.save()

        product_details = ProductDetail.objects.filter(product=product_obj).order_by('id')
        tpl2 = loader.get_template('sales/product_detail_grid_list.html')
        context2 = ({'product_details': product_details, })

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'grid': tpl2.render(context2),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_rate_product(request):
    if request.method == 'GET':
        id_product = request.GET.get('product', '')
        id_distribution = request.GET.get('distribution')
        distribution_obj = None
        if id_distribution != '0':
            distribution_obj = DistributionMobil.objects.get(pk=int(id_distribution))

        product_obj = Product.objects.get(id=int(id_product))
        product_details = ProductDetail.objects.filter(product=product_obj)
        subsidiaries_stores = SubsidiaryStore.objects.filter(stores__product=product_obj)
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))

        product_stores = ProductStore.objects.filter(product=product_obj)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        store = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V').first()

        serialized_obj1 = serializers.serialize('json', product_details)
        serialized_obj2 = serializers.serialize('json', product_stores)

        tpl = loader.get_template('sales/sales_rates.html')

        context = ({

            'store': store,
            'product_obj': product_obj,
            'subsidiaries_stores': subsidiaries_stores,
            'product_stores': product_stores,
            'product_details': product_details,
            'distribution_obj': distribution_obj,
        })

        return JsonResponse({
            'serialized_obj2': serialized_obj2,
            # 'grid': tpl.render(context),
            'form': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_order_by_correlative(request):
    if request.method == 'GET':
        correlative = request.GET.get('correlative', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        order_set = Order.objects.filter(subsidiary_store__subsidiary=subsidiary_obj, correlative_sale=int(correlative),
                                         type='T')
        if order_set.exists():
            order_obj = order_set.last()
            type_document = order_obj.client.clienttype_set.last().document_type.id
            document_number = order_obj.client.clienttype_set.last().document_number
            client_name = order_obj.client.names
            validity_date = order_obj.validity_date
            date_completion = order_obj.date_completion
            place_delivery = order_obj.place_delivery
            type_quotation = order_obj.type_quotation
            type_name_quotation = order_obj.type_name_quotation
            transaction_payment_type = order_obj.way_to_pay_type
            observation = order_obj.observation
            correlative = order_obj.correlative_sale
            order_detail_set = OrderDetail.objects.filter(order=order_obj)
            detail = []
            for d in order_detail_set:
                product_store_obj = None
                quantity_minimum_unit = calculate_minimum_unit(d.quantity_sold, d.unit, d.product)
                stock = 0
                product_store_id = None
                product_store_set = ProductStore.objects.filter(product=d.product,
                                                                subsidiary_store=d.order.subsidiary_store)

                if product_store_set.exists():
                    product_store_obj = product_store_set.last()
                    product_store_id = product_store_obj.id
                    stock = product_store_obj.stock

                new_row = {
                    'id': d.id,
                    'product_id': d.product.id,
                    'product_name': d.product.name,
                    'product_brand': d.product.product_brand.name,
                    'unit_id': d.unit.id,
                    'unit_name': d.unit.name,
                    'quantity': d.quantity_sold,
                    'price': d.price_unit,
                    'store': product_store_id,
                    'stock': round(stock, 0),
                    'unit_min': quantity_minimum_unit,
                }
                detail.append(new_row)

            return JsonResponse({
                'success': True,
                'order_id': order_obj.id,
                'document_type': type_document,
                'document_number': document_number,
                'client_name': client_name,
                'validity_date': validity_date,
                'date_completion': date_completion,
                'place_delivery': place_delivery,
                'type_quotation': type_quotation,
                'type_name_quotation': type_name_quotation,
                'observation': observation,
                'transaction_payment_type': transaction_payment_type,
                'correlative': correlative,
                'detail': detail,
            }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'success': False,
                'message': 'No se encontro la Cotización Numero: ' + str(correlative),
            }, status=HTTPStatus.OK)


def get_correlative_order(_subsidiary=None, _type=None):
    correlative = Order.objects.filter(subsidiary_store__subsidiary=_subsidiary, type=_type).aggregate(
        r=Coalesce(Max('correlative_sale'), 0))
    return str(correlative['r'] + 1)


# def create_order_detail(request):
#     type_doc = ''
#     product_obj = None
#     order_sale_obj = None
#     try:
#         if request.method == 'GET':
#             sale_request = request.GET.get('sales', '')
#             data_sale = json.loads(sale_request)
#
#             check_print_series = data_sale["CheckPrintSeries"]
#             type_payment = data_sale["type_payment"]
#             cash_finality = None
#             has_quotation_order = ''
#             issue_date = str(data_sale["issueDate"])
#             _date = utc_to_local(datetime.now())
#             if type_payment == 'E':
#                 cash_finality = data_sale["cash"]
#             elif type_payment == 'D':
#                 cash_finality = data_sale["cash_deposit"]
#             cod_operation = str(data_sale["cod_operation"])
#
#             client_address = str(data_sale["Address"])
#             client_id = str(data_sale["Client"])
#             client_obj = Client.objects.get(pk=int(client_id))
#             client_address_set = ClientAddress.objects.filter(client=client_obj)
#             if client_address_set.exists():
#                 client_address_obj = client_address_set.last()
#                 client_address_obj.address = client_address
#                 client_address_obj.save()
#             else:
#                 client_address_obj = ClientAddress(
#                     client=client_obj,
#                     address=client_address
#                 )
#                 client_address_obj.save()
#
#             sale_total = decimal.Decimal(data_sale["SaleTotal"])
#             user_id = request.user.id
#             user_subsidiary_obj = User.objects.get(id=user_id)
#             subsidiary_obj = get_subsidiary_by_user(user_subsidiary_obj)
#             subsidiary_store_sales_obj = SubsidiaryStore.objects.get(
#                 subsidiary=subsidiary_obj, category='V')
#             serie = str(data_sale["Serie"])
#
#             user = int(data_sale["userID"])
#             user_obj = User.objects.get(id=user)
#
#             _type = 'T'
#
#             if data_sale["Type"] == 'B' or data_sale["Type"] == 'F':
#                 _type = 'E'
#
#             '_type = str(data_sale["Type"])'
#
#             _bill_type = str(data_sale["BillType"])
#             order_type = str(data_sale["order_type"])
#             order_sale_quotation = None
#             order_sale_quotation_obj = None
#             if int(data_sale["order_sale_quotation"]) > 0:
#                 order_sale_quotation = int(data_sale["order_sale_quotation"])
#                 order_sale_quotation_obj = Order.objects.get(id=order_sale_quotation)
#             msg_sunat = ''
#             sunat_pdf = ''
#             condition_days = data_sale["condition_days"]
#
#             if order_type == 'T' and order_sale_quotation is None:
#                 has_quotation_order = 'S'
#             elif order_type == 'V' and order_sale_quotation is not None:
#                 has_quotation_order = 'C'
#                 order_sale_quotation_obj.has_quotation_order = 'C'
#                 _type = 'E'
#
#             with transaction.atomic():
#
#                 new_order_sale = {
#                     'type': order_type,
#                     'client': client_obj,
#                     'user': user_obj,
#                     'total': sale_total,
#                     'distribution_mobil': None,
#                     'subsidiary_store': subsidiary_store_sales_obj,
#                     'truck': None,
#                     'create_at': _date,
#                     'correlative_sale': get_correlative_order(subsidiary_obj, order_type),
#                     'subsidiary': subsidiary_obj,
#                     'way_to_pay_type': type_payment,
#                     'has_quotation_order': has_quotation_order,
#                     'order_sale_quotation': order_sale_quotation_obj,
#                     'pay_condition': condition_days,
#                     'issue_date': issue_date
#                 }
#                 order_sale_obj = Order.objects.create(**new_order_sale)
#                 order_sale_obj.save()
#
#                 if order_sale_quotation_obj is not None:
#                     order_sale_quotation_obj.order_sale_quotation = order_sale_obj
#                     order_sale_quotation_obj.save()
#
#                 order_detail_obj = None
#
#                 type_doc = order_sale_obj.type
#                 for detail in data_sale['Details']:
#                     quantity = decimal.Decimal(detail['Quantity'])
#                     price = decimal.Decimal(detail['Price'])
#                     total = decimal.Decimal(detail['DetailTotal'])
#                     product_id = int(detail['Product'])
#                     product_obj = Product.objects.get(id=product_id)
#                     unit_id = int(detail['Unit'])
#                     unit_obj = Unit.objects.get(id=unit_id)
#                     commentary = str(detail['_commentary'])
#
#                     order_detail_obj = OrderDetail(
#                         order=order_sale_obj,
#                         product=product_obj,
#                         quantity_sold=quantity,
#                         price_unit=price,
#                         unit=unit_obj,
#                         commentary=commentary,
#                         status='V'
#                     )
#                     order_detail_obj.save()
#
#                     if order_type == 'V' and unit_obj.name != 'ZZ':
#                         if detail['Serials'] != '':
#                             for serial in detail['Serials']:
#                                 product_serial_set = ProductSerial.objects.filter(serial_number=serial['Serial'])
#                                 if product_serial_set.exists():
#                                     product_serial_obj = product_serial_set.last()
#                                     product_serial_obj.order_detail = order_detail_obj
#                                     product_serial_obj.status = 'V'
#                                     product_serial_obj.save()
#                                 else:
#                                     raise ValidationError(
#                                         f"El número de serie {serial['Serial']} no existe, Actualice la Pagina y vuelva a intentar")
#
#                         if order_detail_obj is None:
#                             raise ValidationError(
#                                 "Error al crear el detalle de la orden. Operación cancelada. Actualice")
#
#                         store_product_id = int(detail['Store'])
#                         product_store_obj = ProductStore.objects.get(id=store_product_id)
#                         quantity_minimum_unit = calculate_minimum_unit(quantity, unit_obj, product_obj)
#                         kardex_ouput(product_store_obj.id, quantity_minimum_unit, order_detail_obj=order_detail_obj)
#
#                 if order_type == 'V':
#                     if type_payment != 'C' and _type != 'E':
#                         new_loan_payments = {
#                             'quantity': 0,
#                             'price': sale_total,
#                             'create_at': _date,
#                             'type': 'V',
#                             'operation_date': _date,
#                             'order_detail': order_detail_obj,
#                             'product': product_obj,
#                         }
#                         new_loan_payment_obj = LoanPayment.objects.create(**new_loan_payments)
#                         new_loan_payment_obj.save()
#
#                         new_transaction_payment = {
#                             'payment': sale_total,
#                             'type': type_payment,
#                             'operation_code': cod_operation,
#                             'loan_payment': new_loan_payment_obj,
#                         }
#                         new_transaction_payment_obj = TransactionPayment.objects.create(**new_transaction_payment)
#                         new_transaction_payment_obj.save()
#                         cash_finality_obj = Cash.objects.get(id=int(cash_finality))
#                         new_cash_flow = {
#                             'transaction_date': _date,
#                             'created_at': _date,
#                             'description': 'TICKET: ' + str(order_sale_obj.subsidiary.serial) + '-' + str(
#                                 order_sale_obj.correlative_sale).zfill(6),
#                             'type': type_payment,
#                             'total': sale_total,
#                             'operation_code': cod_operation,
#                             'cash': cash_finality_obj,
#                             'order': order_sale_obj,
#                             'user': user_obj,
#                             'document_type_attached': 'T'
#                         }
#                         new_cash_flow_obj = CashFlow.objects.create(**new_cash_flow)
#                         new_cash_flow_obj.save()
#
#                     if _type == 'E':
#                         if type_payment == 'C':
#                             for c in data_sale['credit']:
#                                 PaymentFees.objects.create(date=c['date'], order=order_sale_obj,
#                                                            amount=decimal.Decimal(c['amount']))
#
#                         if _bill_type == 'F':
#                             r = send_bill_nubefact(order_sale_obj.id, subsidiary_obj.serial)
#                             msg_sunat = r.get('sunat_description')
#                             sunat_pdf = r.get('enlace_del_pdf')
#                             codigo_hash = r.get('codigo_hash')
#                             if codigo_hash:
#                                 order_bill_obj = OrderBill(order=order_sale_obj,
#                                                            serial=r.get('serie'),
#                                                            type=r.get('tipo_de_comprobante'),
#                                                            sunat_status=r.get('aceptada_por_sunat'),
#                                                            sunat_description=r.get('sunat_description'),
#                                                            user=user_obj,
#                                                            sunat_enlace_pdf=r.get('enlace_del_pdf'),
#                                                            code_qr=r.get('cadena_para_codigo_qr'),
#                                                            code_hash=r.get('codigo_hash'),
#                                                            n_receipt=r.get('numero'),
#                                                            status='E',
#                                                            created_at=order_sale_obj.create_at,
#                                                            )
#                                 order_bill_obj.save()
#                                 order_sale_obj.voucher_type = _bill_type
#                                 order_sale_obj.save()
#                                 if type_payment != 'C':
#                                     new_loan_payments = {
#                                         'quantity': 0,
#                                         'price': sale_total,
#                                         'create_at': _date,
#                                         'type': 'V',
#                                         'operation_date': _date,
#                                         'order_detail': order_detail_obj,
#                                         'product': product_obj,
#                                     }
#                                     new_loan_payment_obj = LoanPayment.objects.create(**new_loan_payments)
#                                     new_loan_payment_obj.save()
#
#                                     new_transaction_payment = {
#                                         'payment': sale_total,
#                                         'type': type_payment,
#                                         'operation_code': cod_operation,
#                                         'loan_payment': new_loan_payment_obj,
#                                     }
#                                     new_transaction_payment_obj = TransactionPayment.objects.create(
#                                         **new_transaction_payment)
#                                     new_transaction_payment_obj.save()
#                                     cash_finality_obj = Cash.objects.get(id=int(cash_finality))
#                                     new_cash_flow = {
#                                         'transaction_date': _date,
#                                         'created_at': _date,
#                                         'description': 'FACTURA: ' + str(
#                                             order_bill_obj.serial) + '-' + str(order_bill_obj.n_receipt).zfill(6),
#                                         'type': type_payment,
#                                         'total': sale_total,
#                                         'operation_code': cod_operation,
#                                         'cash': cash_finality_obj,
#                                         'order': order_sale_obj,
#                                         'user': user_obj,
#                                         'document_type_attached': _type
#                                     }
#                                     new_cash_flow_obj = CashFlow.objects.create(**new_cash_flow)
#                                     new_cash_flow_obj.save()
#
#                             else:
#                                 objects_to_delete = OrderDetail.objects.filter(order=order_sale_obj)
#                                 objects_to_delete.delete()
#                                 order_sale_obj.delete()
#                                 if r.get('errors'):
#                                     data = {'error': str(r.get('errors'))}
#                                 elif r.get('error'):
#                                     data = {'error': str(r.get('error'))}
#                                 response = JsonResponse(data)
#                                 response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
#                                 return response
#
#                         elif _bill_type == 'B':
#                             r = send_receipt_nubefact(order_sale_obj.id, subsidiary_obj.serial)
#                             msg_sunat = r.get('sunat_description')
#                             sunat_pdf = r.get('enlace_del_pdf')
#                             codigo_hash = r.get('codigo_hash')
#
#                             if codigo_hash:
#                                 order_bill_obj = OrderBill(order=order_sale_obj,
#                                                            serial=r.get('serie'),
#                                                            type=r.get('tipo_de_comprobante'),
#                                                            sunat_status=r.get('aceptada_por_sunat'),
#                                                            sunat_description=r.get('sunat_description'),
#                                                            user=user_obj,
#                                                            sunat_enlace_pdf=r.get('enlace_del_pdf'),
#                                                            code_qr=r.get('cadena_para_codigo_qr'),
#                                                            code_hash=r.get('codigo_hash'),
#                                                            n_receipt=r.get('numero'),
#                                                            status='E',
#                                                            created_at=order_sale_obj.create_at,
#                                                            )
#                                 order_bill_obj.save()
#                                 order_sale_obj.voucher_type = _bill_type
#                                 order_sale_obj.save()
#                                 if type_payment != 'C':
#                                     new_loan_payments = {
#                                         'quantity': 0,
#                                         'price': sale_total,
#                                         'create_at': _date,
#                                         'type': 'V',
#                                         'operation_date': _date,
#                                         'order_detail': order_detail_obj,
#                                         'product': product_obj,
#                                     }
#                                     new_loan_payment_obj = LoanPayment.objects.create(**new_loan_payments)
#                                     new_loan_payment_obj.save()
#
#                                     new_transaction_payment = {
#                                         'payment': sale_total,
#                                         'type': type_payment,
#                                         'operation_code': cod_operation,
#                                         'loan_payment': new_loan_payment_obj,
#                                     }
#                                     new_transaction_payment_obj = TransactionPayment.objects.create(
#                                         **new_transaction_payment)
#                                     new_transaction_payment_obj.save()
#                                     cash_finality_obj = Cash.objects.get(id=int(cash_finality))
#                                     new_cash_flow = {
#                                         'transaction_date': _date,
#                                         'created_at': _date,
#                                         'description': 'BOLETA: ' + str(
#                                             order_bill_obj.serial) + '-' + str(order_bill_obj.n_receipt).zfill(6),
#                                         'type': type_payment,
#                                         'total': sale_total,
#                                         'operation_code': cod_operation,
#                                         'cash': cash_finality_obj,
#                                         'order': order_sale_obj,
#                                         'user': user_obj,
#                                         'document_type_attached': _type
#                                     }
#                                     new_cash_flow_obj = CashFlow.objects.create(**new_cash_flow)
#                                     new_cash_flow_obj.save()
#                             else:
#                                 objects_to_delete = OrderDetail.objects.filter(order=order_sale_obj)
#                                 objects_to_delete.delete()
#                                 order_sale_obj.delete()
#
#                                 if r.get('errors'):
#                                     data = {'error': str(r.get('errors'))}
#                                 elif r.get('error'):
#                                     data = {'error': str(r.get('error'))}
#                                 response = JsonResponse(data)
#                                 response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
#                                 return response
#                         # return JsonResponse({
#                         #     'message': 'Comprobante realizado con exito.' if msg_sunat else 'Venta Generada Correctamente',
#                         #     'msg_sunat': msg_sunat,
#                         #     'sunat_pdf': sunat_pdf,
#                         #     'id_sales': order_sale_obj.id,
#                         #     'type_doc': type_doc,
#                         #     'check_print_series': check_print_series,
#                         # }, status=HTTPStatus.OK)
#             return JsonResponse({
#                 'message': 'Comprobante realizado con exito.' if msg_sunat else 'Venta Generada Correctamente',
#                 'msg_sunat': msg_sunat,
#                 'sunat_pdf': sunat_pdf,
#                 'id_sales': order_sale_obj.id,
#                 'type_doc': type_doc,
#                 'check_print_series': check_print_series,
#             }, status=HTTPStatus.OK)
#     except ValidationError as e:
#         # Manejo de errores de validación
#         return JsonResponse({'error': str(e)}, status=HTTPStatus.BAD_REQUEST)
#
#     except Exception as e:
#         # Manejo general de excepciones
#         return JsonResponse({'error': f"Ocurrió un error: {str(e)}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def delete_and_increment(order_obj):
    for od in order_obj.orderdetail_set.all():
        product_id = int(od.product.id)
        product_obj = Product.objects.get(id=product_id)
        product_store_obj = ProductStore.objects.get(product=product_obj,
                                                     subsidiary_store_id=order_obj.subsidiary_store)
        last_kardex = Kardex.objects.filter(product_store_id=product_store_obj.id, order_detail=od.id).last()
        last_remaining_quantity = last_kardex.remaining_quantity
        old_stock = product_store_obj.stock
        new_stock = old_stock + od.quantity

        product_store_obj.stock = new_stock
        product_store_obj.save()

        last_kardex.delete()
        od.delete()

    order_obj.delete()


@csrf_exempt
def generate_receipt_random(request):
    if request.method == 'POST':
        product = request.POST.get('create_product')
        truck = request.POST.get('id_truck')
        client = request.POST.get('id_client_name')
        date = request.POST.get('date')
        is_demo = False
        value_is_demo = 'P'
        if request.POST.get('demo') == '0':
            is_demo = True
            value_is_demo = 'D'

        price = decimal.Decimal(request.POST.get('price'))
        truck_obj = Truck.objects.get(id=int(truck))
        client_obj = Client.objects.get(pk=int(client))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        product_obj = Product.objects.get(id=int(product))
        unit = product_obj.calculate_minimum_unit_id()
        unit_obj = Unit.objects.get(id=unit)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_sales_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='V')

        counter = int(request.POST.get('counter')) + 1
        quantity_min = 1
        limit = 100
        quantity_max = math.floor(limit / price)
        for x in range(1, counter, 1):
            quantity = random.randint(quantity_min, quantity_max)
            total = decimal.Decimal(quantity * price)

            order_obj = Order(type='E',
                              client=client_obj,
                              user=user_obj,
                              total=total,
                              subsidiary_store=subsidiary_store_sales_obj,
                              truck=truck_obj,
                              create_at=date)
            order_obj.save()
            detail_order_obj = OrderDetail(order=order_obj,
                                         product=product_obj,
                                         quantity_sold=quantity,
                                         price_unit=price,
                                         unit=unit_obj,
                                         status='V')
            detail_order_obj.save()
            r = send_receipt_nubefact(order_obj.id, is_demo)
            codigo_hash = r.get('codigo_hash')
            if codigo_hash:
                order_bill_obj = OrderBill(order=order_obj,
                                           serial=r.get('serie'),
                                           type=r.get('tipo_de_comprobante'),
                                           sunat_status=r.get('aceptada_por_sunat'),
                                           sunat_description=r.get('sunat_description'),
                                           user=user_obj,
                                           sunat_enlace_pdf=r.get('enlace_del_pdf'),
                                           code_qr=r.get('cadena_para_codigo_qr'),
                                           code_hash=r.get('codigo_hash'),
                                           n_receipt=r.get('numero'),
                                           status='E',
                                           created_at=order_obj.create_at,
                                           is_demo=value_is_demo
                                           )
                order_bill_obj.save()
            else:
                objects_to_delete = OrderDetail.objects.filter(order=order_obj)
                objects_to_delete.delete()
                order_obj.delete()
                if r.get('errors'):
                    data = {'error': str(r.get('errors'))}
                elif r.get('error'):
                    data = {'error': str(r.get('error'))}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        return JsonResponse({
            'msg_sunat': 'Boletas enviadas correctamente',
        }, status=HTTPStatus.OK)


def calculate_minimum_unit(quantity, unit_obj, product_obj):
    product_detail = ProductDetail.objects.filter(
        product=product_obj).annotate(Min('quantity_minimum')).first()
    product_detail_sent = ProductDetail.objects.get(product=product_obj, unit=unit_obj)
    if product_detail.quantity_minimum > 1:
        new_quantity = quantity * product_detail.quantity_minimum
    else:
        new_quantity = quantity * product_detail.quantity_minimum * product_detail_sent.quantity_minimum
    return new_quantity


def kardex_initial(
        product_store_obj,
        stock,
        price_unit,
        purchase_detail_obj=None,
        requirement_detail_obj=None,
        programming_invoice_obj=None,
        manufacture_detail_obj=None,
        guide_detail_obj=None,
        distribution_detail_obj=None,
        order_detail_obj=None,
        loan_payment_obj=None,
        ball_change_obj=None,
        advance_detail_obj=None,
):
    new_kardex = {
        'operation': 'C',
        'quantity': 0,
        'price_unit': 0,
        'price_total': 0,
        'remaining_quantity': decimal.Decimal(stock),
        'remaining_price': decimal.Decimal(price_unit),
        'remaining_price_total': decimal.Decimal(stock) * decimal.Decimal(price_unit),
        'product_store': product_store_obj,
        'purchase_detail': purchase_detail_obj,
        'requirement_detail': requirement_detail_obj,
        'programming_invoice': programming_invoice_obj,
        'manufacture_detail': manufacture_detail_obj,
        'guide_detail': guide_detail_obj,
        'distribution_detail': distribution_detail_obj,
        'order_detail': order_detail_obj,
        'loan_payment': loan_payment_obj,
        'ball_change': ball_change_obj,
        'advance_detail': advance_detail_obj
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()


def kardex_input(
        product_store_id,
        quantity_purchased,
        price_unit,
        purchase_detail_obj=None,
        requirement_detail_obj=None,
        programming_invoice_obj=None,
        manufacture_detail_obj=None,
        guide_detail_obj=None,
        distribution_detail_obj=None,
        order_detail_obj=None,
        loan_payment_obj=None,
        ball_change_obj=None,
        advance_detail_obj=None,
):
    product_store = ProductStore.objects.get(pk=int(product_store_id))

    old_stock = product_store.stock
    new_quantity = decimal.Decimal(quantity_purchased)
    new_stock = old_stock + new_quantity  # Cantidad nueva de stock
    new_price_unit = decimal.Decimal(price_unit)
    new_price_total = new_quantity * new_price_unit

    last_kardex = Kardex.objects.filter(product_store_id=product_store.id).last()
    last_remaining_quantity = last_kardex.remaining_quantity
    last_remaining_price = last_kardex.remaining_price
    last_remaining_price_total = last_kardex.remaining_price_total

    # new_remaining_quantity = last_remaining_quantity + new_quantity
    # new_remaining_price = (decimal.Decimal(last_remaining_price_total) +
    #                        new_price_total) / new_remaining_quantity
    # new_remaining_price_total = new_remaining_quantity * new_remaining_price

    # Detectar si es una anulación de venta
    is_sale_annulment = order_detail_obj is not None and purchase_detail_obj is None

    if is_sale_annulment:
        # No cambia el precio unitario ni el promedio
        new_remaining_quantity = last_remaining_quantity + new_quantity
        new_remaining_price = last_remaining_price
        new_remaining_price_total = new_remaining_quantity * new_remaining_price
    else:
        # Compra u otra entrada válida que sí afecta el costo promedio
        new_remaining_quantity = last_remaining_quantity + new_quantity
        new_remaining_price = (decimal.Decimal(last_remaining_price_total) + new_price_total) / new_remaining_quantity
        new_remaining_price_total = new_remaining_quantity * new_remaining_price

    new_kardex = {
        'operation': 'E',
        'quantity': new_quantity,
        'price_unit': new_price_unit,
        'price_total': new_price_total,
        'remaining_quantity': new_remaining_quantity,
        'remaining_price': new_remaining_price,
        'remaining_price_total': new_remaining_price_total,
        'product_store': product_store,
        'purchase_detail': purchase_detail_obj,
        'requirement_detail': requirement_detail_obj,
        'programming_invoice': programming_invoice_obj,
        'manufacture_detail': manufacture_detail_obj,
        'guide_detail': guide_detail_obj,
        'distribution_detail': distribution_detail_obj,
        'order_detail': order_detail_obj,
        'loan_payment': loan_payment_obj,
        'ball_change': ball_change_obj,
        'advance_detail': advance_detail_obj,
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()

    product_store.stock = new_stock
    product_store.save()


def kardex_ouput(
        product_store_id,
        quantity_sold,
        order_detail_obj=None,
        programming_invoice_obj=None,
        manufacture_recipe_obj=None,
        guide_detail_obj=None,
        distribution_detail_obj=None,
        loan_payment_obj=None,
        ball_change_obj=None,
        purchase_return_detail=None,
        price=None
):
    product_store = ProductStore.objects.get(pk=int(product_store_id))

    old_stock = product_store.stock
    last_kardex = Kardex.objects.filter(product_store_id=product_store.id).order_by('id').last()
    last_remaining_quantity = last_kardex.remaining_quantity

    if old_stock < 0 or last_remaining_quantity < 0:
        data = {'error': 'stock en negativa'}
        response = JsonResponse(data)
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response

    new_stock = old_stock - decimal.Decimal(quantity_sold)
    new_quantity = decimal.Decimal(quantity_sold)

    old_price_unit = last_kardex.remaining_price
    new_price_total = old_price_unit * new_quantity
    new_remaining_price = old_price_unit
    new_remaining_quantity = last_remaining_quantity - new_quantity
    new_remaining_price_total = new_remaining_quantity * new_remaining_price
    type_document = '00'
    type_operation = '99'
    if price is not None and purchase_return_detail is not None:
        new_remaining_price = old_price_unit
        new_price_total = new_remaining_price * new_quantity
        type_document = '07'
        type_operation = '06'

    new_kardex = {
        'operation': 'S',
        'quantity': new_quantity,
        'price_unit': old_price_unit,
        'price_total': new_price_total,
        'remaining_quantity': new_remaining_quantity,
        'remaining_price': new_remaining_price,
        'remaining_price_total': new_remaining_price_total,
        'product_store': product_store,
        'programming_invoice': programming_invoice_obj,
        'manufacture_recipe': manufacture_recipe_obj,
        'order_detail': order_detail_obj,
        'guide_detail': guide_detail_obj,
        'distribution_detail': distribution_detail_obj,
        'loan_payment': loan_payment_obj,
        'ball_change': ball_change_obj,
        'purchase_return_detail': purchase_return_detail,
        'type_document': type_document,
        'type_operation': type_operation
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()

    product_store.stock = new_stock
    product_store.save()


def kardex_input_credit_note(
        product_store_id,
        quantity_return,
        credit_note_detail_obj=None,
):
    product_store = ProductStore.objects.get(pk=int(product_store_id))

    old_stock = product_store.stock
    last_kardex = Kardex.objects.filter(product_store_id=product_store.id).order_by('id').last()
    last_remaining_quantity = last_kardex.remaining_quantity

    if old_stock < 0 or last_remaining_quantity < 0:
        data = {'error': 'stock en negativa'}
        response = JsonResponse(data)
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response

    new_stock = old_stock + decimal.Decimal(quantity_return)
    new_quantity = decimal.Decimal(quantity_return)
    old_price_unit = last_kardex.remaining_price

    new_price_total = old_price_unit * new_quantity

    new_remaining_quantity = last_remaining_quantity + new_quantity
    new_remaining_price = old_price_unit
    new_remaining_price_total = new_remaining_quantity * new_remaining_price
    new_kardex = {
        'operation': 'E',
        'quantity': new_quantity,
        'price_unit': old_price_unit,
        'price_total': new_price_total,
        'remaining_quantity': new_remaining_quantity,
        'remaining_price': new_remaining_price,
        'remaining_price_total': new_remaining_price_total,
        'product_store': product_store,
        'credit_note_detail': credit_note_detail_obj
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()

    product_store.stock = new_stock
    product_store.save()


def generate_invoice(request):
    if request.method == 'GET':
        id_order = request.GET.get('order', '')

        # print(numero_a_letras(145))

        r = send_bill_nubefact(id_order)

        return JsonResponse({
            'success': True,
            'msg': r.get('errors'),
            # 'numero_a_letras': numero_a_letras(decimal.Decimal(id_order)),
            'numero_a_moneda': numero_a_moneda(decimal.Decimal(id_order)),

            'parameters': r.get('params'),
        }, status=HTTPStatus.OK)


def get_sales_by_subsidiary_store(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/order_sales_list.html', {'formatdate': formatdate, })
    elif request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        orders = None
        if subsidiary_obj is not None:
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
            orders = Order.objects.filter(subsidiary_store=subsidiary_store_obj)
            start_date = str(request.POST.get('start-date'))
            end_date = str(request.POST.get('end-date'))
            voucher_type_filter = str(request.POST.get('voucher-type', 'TODOS'))

            if start_date == end_date:
                orders = orders.filter(create_at__date=start_date, type='V', status__in=['P', 'A']).order_by('id')
            else:
                orders = orders.filter(create_at__date__range=[start_date, end_date], type='V',
                                       status__in=['P', 'A']).order_by('id')
            
            # Aplicar filtro por tipo de comprobante
            if voucher_type_filter != 'TODOS':
                orders = orders.filter(voucher_type=voucher_type_filter)
            
            if orders:
                return JsonResponse({
                    'grid': get_dict_order_queries(orders, start_date, end_date, is_pdf=False, is_unit=False),
                }, status=HTTPStatus.OK)
            else:
                data = {'error': "No hay operaciones registradas"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
        else:
            data = {'error': "No hay sucursal"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response


def get_dict_order_queries(order_set, start_date, end_date, is_pdf=False, is_unit=False):
    dictionary = []
    sum = 0
    sum_bills = 0
    sum_receipts = 0
    sum_tickets = 0
    cash_id = None
    # 1, 4 Caja
    # 2, 3 Bancos
    user_dict = {}

    total_cash = decimal.Decimal(0)
    total_credit = decimal.Decimal(0)
    total_deposit = decimal.Decimal(0)

    for o in order_set:

        _sum_total_multiply = round(decimal.Decimal(0), 2)

        cash_flow_set = CashFlow.objects.filter(order_id=o.id)
        if cash_flow_set.exists():
            cash_flow_obj = cash_flow_set.first()
            cash_id = cash_flow_obj.cash.id

        _order_detail = o.orderdetail_set.all()
        order_bill_obj = ''
        serial_bill = ''
        correlative_bill = ''
        type_bill = 'CONSIGNACIÓN'
        order_bill_set = OrderBill.objects.filter(order=o.id)

        if order_bill_set.exists():
            order_bill_obj = order_bill_set.first()

            if order_bill_obj.type == '1':
                type_bill = 'FACTURA'
                serial_bill = order_bill_obj.serial
                correlative_bill = order_bill_obj.n_receipt
            elif order_bill_obj.type == '2':
                type_bill = 'BOLETA'
                serial_bill = order_bill_obj.serial
                correlative_bill = order_bill_obj.n_receipt

        note_serial = None
        note_number = None
        note_pdf = None

        fully_returned = is_order_fully_returned(o)

        credit_notes_data = []
        credit_note_set = CreditNote.objects.filter(order=o)

        # credit_note_set = CreditNote.objects.filter(order=o)
        # if credit_note_set.exists():
        #     credit_note_obj = credit_note_set.first()
        #     note_serial = credit_note_obj.serial
        #     note_number = credit_note_obj.correlative
        #     note_pdf = credit_note_obj.note_enlace_pdf

        for cn in credit_note_set:
            credit_notes_data.append({
                'serial': cn.serial,
                'correlative': cn.correlative,
                'pdf': cn.note_enlace_pdf,
                'issue_date': cn.issue_date,
                'total': cn.note_total,
                'description': cn.note_description,
            })

        order = {
            'id': o.id,
            # 'status': o.get_status_display(),
            'client': o.client,
            'user': o.user,
            'total': 0,
            'subsidiary': o.subsidiary.name,
            'create_at': o.create_at,
            'serial': o.subsidiary.serial,
            'correlative_sale': o.correlative_sale,
            'order_bill': order_bill_obj,
            'serial_bill': serial_bill,
            'correlative_bill': correlative_bill,
            'order_detail_set': [],
            'type': o.get_type_display(),
            'status': o.status,
            'type_bill': type_bill,
            'cash_id': cash_id,
            'way_to_pay': o.way_to_pay_type,
            'details': _order_detail.count(),
            # 'note_serial': note_serial,
            # 'note_number': note_number,
            # 'note_pdf': note_pdf,
            'credit_notes': credit_notes_data,
            'fully_returned': fully_returned,
        }

        for d in _order_detail:
            order_detail = {
                'id': d.id,
                'product': d.product.name,
                'unit': d.unit.name,
                'quantity_sold': d.quantity_sold,
                'price_unit': d.price_unit,
                'multiply': d.multiply,
                'comentary': d.commentary.upper()
            }
            _sum_total_multiply += d.multiply()

            order.get('order_detail_set').append(order_detail)

        # sum = sum + _sum_total_multiply

        if o.status != 'A':

            sum = sum + o.sum_total_details()

            if order_bill_set.exists():
                order_bill_obj = order_bill_set.first()
                if order_bill_obj.type == '1':
                    sum_bills = sum_bills + o.sum_total_details()
                elif order_bill_obj.type == '2':
                    sum_receipts = sum_receipts + o.sum_total_details()
            else:
                sum_tickets += o.sum_total_details()

            key = o.user.id
            total_bills = 0
            total_receipts = 0
            total_tickets = 0

            if o.way_to_pay_type == 'E':
                total_cash = total_cash + o.sum_total_details()
            elif o.way_to_pay_type == 'D':
                total_deposit = total_deposit + o.sum_total_details()
            elif o.way_to_pay_type == 'C':
                total_credit = total_credit + o.sum_total_details()

            if key in user_dict:

                user = user_dict[key]
                old_total = user.get('total_sold')
                old_total_bills = user.get('total_bills')
                old_total_receipts = user.get('total_receipts')
                old_total_tickets = user.get('total_tickets')

                order_bill_set = OrderBill.objects.filter(order=o.id)

                if order_bill_set.exists():
                    order_bill_obj = order_bill_set.first()
                    if order_bill_obj.type == '1':
                        total_bills = o.sum_total_details()
                    elif order_bill_obj.type == '2':
                        total_receipts = o.sum_total_details()
                else:
                    total_tickets = o.sum_total_details()

                user_dict[key]['total_bills'] = old_total_bills + total_bills
                user_dict[key]['total_receipts'] = old_total_receipts + total_receipts
                user_dict[key]['total_tickets'] = old_total_tickets + total_tickets
                user_dict[key]['total_sold'] = old_total + o.sum_total_details()

            else:

                if order_bill_set.exists():
                    order_bill_obj = order_bill_set.first()
                    if order_bill_obj.type == '1':
                        total_bills = o.sum_total_details()
                    elif order_bill_obj.type == '2':
                        total_receipts = o.sum_total_details()
                else:
                    total_tickets = o.sum_total_details()

                user_dict[key] = {
                    'user_id': o.user.id,
                    'user_names': o.user.worker_set.last().employee.names,
                    'total_sold': round(decimal.Decimal(o.sum_total_details()), 2),
                    'total_bills': round(decimal.Decimal(total_bills), 2),
                    'total_receipts': round(decimal.Decimal(total_receipts), 2),
                    'total_tickets': round(decimal.Decimal(total_tickets), 2),
                }
            # print(user_dict)
        order['total'] = decimal.Decimal(o.sum_total_details()).quantize(decimal.Decimal('0.0'),
                                                                         rounding=decimal.ROUND_HALF_EVEN)
        # product_detail_obj.price_sale.quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)

        dictionary.append(order)

    tpl = loader.get_template('sales/order_sales_grid_list.html')
    context = ({
        'dictionary': dictionary,
        'sum': sum,
        'sum_bills': round(decimal.Decimal(sum_bills), 2),
        'sum_receipts': round(decimal.Decimal(sum_receipts), 2),
        'sum_tickets': round(decimal.Decimal(sum_tickets), 2),
        'is_unit': is_unit,
        'is_pdf': is_pdf,
        'user_dict': user_dict,
        'f1': start_date,
        'f2': end_date,
        'total_cash': decimal.Decimal(total_cash).quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN),
        'total_deposit': decimal.Decimal(total_deposit).quantize(decimal.Decimal('0.00'),
                                                                 rounding=decimal.ROUND_HALF_EVEN),
        'total_credit': decimal.Decimal(total_credit).quantize(decimal.Decimal('0.00'),
                                                               rounding=decimal.ROUND_HALF_EVEN)
    })
    return tpl.render(context)


def is_order_fully_returned(order):
    """
    Retorna True si todos los detalles de la orden han sido devueltos completamente.
    """
    for detail in order.orderdetail_set.all():
        # Total vendido
        quantity_sold = detail.quantity_sold

        # Total devuelto (suma de todas las cantidades de notas de crédito con el mismo producto y orden)
        total_returned = CreditNoteDetail.objects.filter(
            credit_note__order=order,
            product=detail.product,
            unit=detail.unit
        ).aggregate(total=Sum('quantity'))['total'] or 0

        if total_returned < quantity_sold:
            return False  # Si algún detalle no ha sido totalmente devuelto

    return True  # Todos los detalles fueron devueltos completamente



def get_quantity_ball_5kg(order_detail_set):
    _b = order_detail_set.filter(unit__name='B', product__id=2)
    _g = order_detail_set.filter(unit__name='G', product__id=2)
    _gbc = order_detail_set.filter(unit__name='GBC', product__id=2)
    _bg = order_detail_set.filter(unit__name='BG', product__id=2)
    if _b:
        _b = _b.first().quantity_sold
    else:
        _b = 0
    if _g:
        _g = _g.first().quantity_sold
    else:
        _g = 0
    if _gbc:
        _gbc = _gbc.first().quantity_sold
    else:
        _gbc = 0
    if _bg:
        _bg = _bg.first().quantity_sold
    else:
        _bg = 0

    context = ({
        'b': _b,
        'g': _g,
        'gbc': _gbc,
        'bg': _bg,
    })
    return context


def get_quantity_ball_10kg(order_detail_set):
    _b = order_detail_set.filter(unit__name='B', product__id=1)
    _g = order_detail_set.filter(unit__name='G', product__id=1)
    _gbc = order_detail_set.filter(unit__name='GBC', product__id=1)
    _bg = order_detail_set.filter(unit__name='BG', product__id=1)
    if _b:
        _b = _b.first().quantity_sold
    else:
        _b = 0
    if _g:
        _g = _g.first().quantity_sold
    else:
        _g = 0
    if _gbc:
        _gbc = _gbc.first().quantity_sold
    else:
        _gbc = 0
    if _bg:
        _bg = _bg.first().quantity_sold
    else:
        _bg = 0
    context = ({
        'b': _b,
        'g': _g,
        'gbc': _gbc,
        'bg': _bg,
    })
    return context


def get_quantity_ball_45kg(order_detail_set):
    _b = order_detail_set.filter(unit__name='B', product__id=3)
    _g = order_detail_set.filter(unit__name='G', product__id=3)
    _gbc = order_detail_set.filter(unit__name='GBC', product__id=3)
    _bg = order_detail_set.filter(unit__name='BG', product__id=3)
    if _b:
        _b = _b.first().quantity_sold
    else:
        _b = 0
    if _g:
        _g = _g.first().quantity_sold
    else:
        _g = 0
    if _gbc:
        _gbc = _gbc.first().quantity_sold
    else:
        _gbc = 0
    if _bg:
        _bg = _bg.first().quantity_sold
    else:
        _bg = 0
    context = ({
        'b': _b,
        'g': _g,
        'gbc': _gbc,
        'bg': _bg,
    })
    return context


def get_sales_all_subsidiaries(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/all_order_sales_list.html', {
            'formatdate': formatdate,
        })
    elif request.method == 'POST':
        subsidiary_store_set = SubsidiaryStore.objects.filter(category='V')
        orders = Order.objects.filter(subsidiary_store__in=subsidiary_store_set)
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))

        if start_date == end_date:
            orders = orders.filter(create_at__date=start_date, type='V')
        else:
            orders = orders.filter(create_at__date__range=[start_date, end_date], type='V')
        if orders:
            return JsonResponse({
                'grid': get_dict_order_queries(orders, start_date, end_date, is_pdf=False, is_unit=False),
            }, status=HTTPStatus.OK)
        else:
            data = {'error': "No hay operaciones registradas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_products_by_subsidiary(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary = get_subsidiary_by_user(user_obj)

    # Obtener el último precio del kardex para cada producto_store
    from django.db.models import OuterRef, Subquery, DecimalField
    from decimal import Decimal
    
    last_kardex_price = Kardex.objects.filter(
        product_store=OuterRef('id')
    ).order_by('-id').values('remaining_price')[:1]

    stores = ProductStore.objects.filter(subsidiary_store__category='V',
                                         subsidiary_store__subsidiary=subsidiary).select_related('subsidiary_store',
                                                                                                 'subsidiary_store__subsidiary',
                                                                                                 'product').prefetch_related(
        Prefetch(
            'product__productdetail_set',
            queryset=ProductDetail.objects.select_related('unit', 'product__product_brand')
        )
    ).annotate(
        last_purchase_price=Subquery(last_kardex_price)
    ).order_by('product__name')

    form_subsidiary_store = FormSubsidiaryStore()

    return render(request, 'sales/product_by_subsidiary.html', {
        'form': form_subsidiary_store,
        'stores': stores
    })


@csrf_exempt
def toggle_product_enabled(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        is_enabled = request.POST.get('is_enabled') == 'true'
        
        try:
            product = Product.objects.get(id=product_id)
            product.is_enabled = is_enabled
            product.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Producto {"habilitado" if is_enabled else "deshabilitado"} exitosamente.',
            }, status=HTTPStatus.OK)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Producto no encontrado.',
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido.',
    }, status=HTTPStatus.METHOD_NOT_ALLOWED)


def new_subsidiary_store(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        name = request.POST.get('name')
        category = request.POST.get('category', '')

        try:
            subsidiary_store_obj = SubsidiaryStore(
                subsidiary=subsidiary_obj,
                name=name,
                category=category
            )
            subsidiary_store_obj.save()
        except DatabaseError as e:
            data = {'error': str(e)}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        return JsonResponse({
            'success': True,
            'message': 'Registrado con exito.',
        }, status=HTTPStatus.OK)


def get_recipe(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)

    products = Product.objects.filter(is_manufactured=True)
    products_insume = Product.objects.filter(is_supply=True)

    return render(request, 'sales/product_recipe.html', {
        'products': products,
        'products_insume': products_insume,
    })


def get_manufacture(request):
    products_insume = Product.objects.filter(
        is_manufactured=True, recipes__isnull=False).distinct('name')
    inputs = Product.objects.filter(is_supply=True)
    mydate = datetime.now()
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    my_subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='I')
    formatdate = mydate.strftime("%Y-%m-%d %H:%M:%S")
    return render(request, 'sales/recipe_list.html', {
        'products_insume': products_insume,
        'my_subsidiary_store': my_subsidiary_store_obj,
        'date': formatdate,
        'context': validate_manufacture_pendient(subsidiary_obj),
        'inputs': inputs
    })


def get_unit_by_product(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        units = Unit.objects.filter(productdetail__product__id=pk)
        serialized_obj = serializers.serialize('json', units)

    return JsonResponse({'units_serial': serialized_obj})


def get_price_by_product(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        product_detail_obj = ProductDetail.objects.filter(product_id=int(pk)).first()
        price = product_detail_obj.price_sale

    return JsonResponse({'price_unit': price})


def create_recipe(request):
    if request.method == 'GET':
        recipe_request = request.GET.get('recipe_dic', '')
        data_recipe = json.loads(recipe_request)

        for detail in data_recipe['Details']:
            product_create_id = str(detail["ProductCreate"])
            product_create_obj = Product.objects.get(id=product_create_id)

            product_insume_id = str(detail["ProductoInsume"])
            product_insume_obj = Product.objects.get(id=product_insume_id)

            quantity = decimal.Decimal(detail["Quantity"])

            unit_id = str(detail["Unit"])
            unit_obj = Unit.objects.get(id=unit_id)

            price = decimal.Decimal(detail["Price"])

            recipe_product = {
                'product': product_create_obj,
                'product_input': product_insume_obj,
                'quantity': quantity,
                'unit': unit_obj,
                'price': price

            }
            new_recipe_obj = ProductRecipe.objects.create(**recipe_product)
            new_recipe_obj.save()

        return JsonResponse({
            'message': 'La operaciòn se Realizo correctamente.',
        }, status=HTTPStatus.OK)


def get_price_and_total_by_product_recipe(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        product_recipe_obj = ProductRecipe.objects.filter(product__id=int(pk)).first()
        quantity = decimal.Decimal(request.GET.get('quantity', ''))
        price_unit = product_recipe_obj.price
        total = quantity * price_unit
        product_obj = Product.objects.get(id=int(pk))
        total_quantity = 0
        if product_obj.is_granel == True:
            product_recipe = ProductRecipe.objects.filter(product__id=int(pk)).aggregate(Sum('quantity'))
            total_quantity = product_recipe['quantity__sum']

    return JsonResponse({'price_unit': price_unit, 'total': total, 'total_quantity': total_quantity})


def get_stock_insume_by_product_recipe(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        quantity_request = decimal.Decimal(request.GET.get('quantity'))
        status = request.GET.get('status', '')
        product_recipe_set = ProductRecipe.objects.filter(product__id=int(pk))
        product_create_obj = Product.objects.get(id=int(pk))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_supplies_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='I')
        dictionary = []

        for i in product_recipe_set.all():
            current_stock_of_supply = i.product_input.productstore_set.filter(
                subsidiary_store=subsidiary_store_supplies_obj).first().stock
            total_quantity_request = i.quantity * quantity_request
            total_quantity_remaining = current_stock_of_supply - total_quantity_request
            detail = {
                'id': i.product_input.id,
                'name': i.product_input.name,
                'unit': Unit.objects.get(id=i.product_input.calculate_minimum_unit_id()),
                'quantity_supply': i.quantity,
                # 'quantity_supply_galons': float(i.quantity) / float(3785.41),
                'current_stock': current_stock_of_supply,
                'total_quantity_request': total_quantity_request,
                'quantity_remaining_in_stock': total_quantity_remaining,
            }
            dictionary.append(detail)

        tpl = loader.get_template('sales/detail_product_recipe.html')
        context = ({
            'product_details': dictionary,
            'rowspan': len(dictionary) + 1,
            'quantity': quantity_request,
            'status': status,
            'subsidiary_store_insume': subsidiary_store_supplies_obj,
            'product_create': product_create_obj,
        })
        # serialized_data = serializers.serialize('json', product_recipe_set)
        return JsonResponse({
            'success': True,
            # 'form': t.render(c, request),
            'grid': tpl.render(context),
            # 'serialized_data': serialized_data,
            # 'form': t.render(c),
        }, status=HTTPStatus.OK)


def get_context_kardex_glp(subsidiary_obj, pk, is_pdf=False, get_context=False):
    other_subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(pk))  # otro almacen insumos
    my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(
        subsidiary=subsidiary_obj, category='G')  # pluspetrol
    my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj,
                                                                 category='I')  # tu almacen insumos

    product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')
    product_store_obj = ProductStore.objects.get(
        subsidiary_store=my_subsidiary_store_glp_obj, product=product_obj)

    kardex_set = Kardex.objects.filter(product_store=product_store_obj)

    tpl = loader.get_template('sales/kardex_glp_grid.html')
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


def get_kardex_glp(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    if request.method == 'GET':
        pk = request.GET.get('subsidiary_store_id', '')
        if pk != '':

            return JsonResponse({
                'success': True,
                'grid': get_context_kardex_glp(subsidiary_obj, pk),
            }, status=HTTPStatus.OK)
        else:
            subsidiary_store_set = SubsidiaryStore.objects.exclude(
                subsidiary=subsidiary_obj).filter(category='I')
            mydate = datetime.now()
            formatdate = mydate.strftime("%Y-%m-%d %H:%M:%S")
            return render(request, 'sales/kardex_glp.html', {
                'subsidiary_stores': subsidiary_store_set,
                'date': formatdate
            })


def get_only_grid_kardex_glp(request, pk):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    return render(request, 'sales/kardex_glp_grid.html', get_context_kardex_glp(subsidiary_obj, pk, get_context=True))


def create_order_manufacture(request):
    if request.method == 'GET':
        production_request = request.GET.get('production')
        data_production = json.loads(production_request)

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        manufacture_obj_val = ManufactureAction.objects.filter(
            status="1", manufacture__subsidiary=subsidiary_obj)

        # ---Cabecera de Manufacturee---
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        code = str(data_production["Code"])
        total = decimal.Decimal((data_production["Total"]).replace(',', '.'))

        new_manufacture_obj = Manufacture(subsidiary=subsidiary_obj, code=code, total=total)
        new_manufacture_obj.save()

        # --Save ManufactureAction--
        new_manufacture_action_obj = ManufactureAction(
            user=user_obj, manufacture=new_manufacture_obj, status="1")
        new_manufacture_action_obj.save()

        # --Save Manufacturedetail--
        for details in data_production['Details']:

            product_create_id = str(details["Product"])
            product_create_obj = Product.objects.get(id=product_create_id)

            quantity_request = decimal.Decimal(details["Quantity"])
            quantity_total = decimal.Decimal(details["Quantity_total"])
            price = decimal.Decimal(details["Price"])
            if quantity_total == quantity_request:
                new_manufacture_detail_obj = ManufactureDetail(manufacture=new_manufacture_obj,
                                                               product_manufacture=product_create_obj,
                                                               quantity=quantity_request, price=price)
                new_manufacture_detail_obj.save()
            else:
                new_manufacture_detail_obj = ManufactureDetail(manufacture=new_manufacture_obj,
                                                               product_manufacture=product_create_obj,
                                                               quantity=quantity_total, price=price)
                new_manufacture_detail_obj.save()

            for insume in ProductRecipe.objects.filter(product=product_create_obj):
                new_manufacture_recipe_obj = ManufactureRecipe(manufacture_detail=new_manufacture_detail_obj,
                                                               product_input=insume.product_input,
                                                               quantity=insume.quantity * quantity_request)
                new_manufacture_recipe_obj.save()

        return JsonResponse({
            'message': 'La operaciòn se Realizo correctamente.',
        }, status=HTTPStatus.OK)

    else:
        return JsonResponse({
            'error': 'No se puede guardar, existe una Orden pendiente'
        }, status=HTTPStatus.OK)


def orders_manufacture(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        manufactures = Manufacture.objects.filter(subsidiary=subsidiary_obj)
        status = ManufactureAction._meta.get_field('status').choices

        return render(request, 'sales/manufacture_list.html', {
            'manufactures': manufactures,
            'status': status
        })


# Aqui tambien se guardan los productos creados
def update_manufacture_by_id(request):
    if request.method == 'GET':
        manufacture_id = request.GET.get('pk', '')
        status_id = request.GET.get('status', '')
        manufacture_obj = Manufacture.objects.get(id=int(manufacture_id))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        if status_id == '2':  # aprobado
            subsidiary_store_set_obj = SubsidiaryStore.objects.get(
                subsidiary=subsidiary_obj, category='I')
            manufacture_details_set = ManufactureDetail.objects.filter(
                manufacture_id=int(manufacture_id))
            if validate_stock_insume(subsidiary_store_set_obj, manufacture_id):
                for d in manufacture_details_set.all():
                    inputs_set = ManufactureRecipe.objects.filter(manufacture_detail=d)
                    for i in inputs_set:
                        product_store_inputs_obj = ProductStore.objects.get(subsidiary_store=subsidiary_store_set_obj,
                                                                            product=i.product_input)
                        kardex_ouput(product_store_inputs_obj.id,
                                     i.quantity,
                                     manufacture_recipe_obj=i)  # i.quantity = LA CANTIDAD QUE SE DESCONTARA DEL STOCK DEL INSUMO

                new_manufacture_action_obj = ManufactureAction(user=user_obj, date=datetime.now(),
                                                               manufacture=manufacture_obj, status=status_id)
                new_manufacture_action_obj.save()
            else:
                data = {'error': 'No se pudo Aprobar la solicitud por falta de stock de un insumo'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        elif status_id == '3':  # produccion
            new_manufacture_action_obj = ManufactureAction(user=user_obj, date=datetime.now(),
                                                           manufacture=manufacture_obj, status=status_id)
            new_manufacture_action_obj.save()

        elif status_id == '4':
            subsidiary_store_set_obj = SubsidiaryStore.objects.get(
                subsidiary=subsidiary_obj, category='V')
            manufacture_details_set = ManufactureDetail.objects.filter(
                manufacture_id=int(manufacture_id))
            for d in manufacture_details_set.all():
                price_unit = d.price / d.quantity
                try:
                    product_store_create = ProductStore.objects.get(subsidiary_store=subsidiary_store_set_obj,
                                                                    product=d.product_manufacture)
                except ProductStore.DoesNotExist:
                    product_store_create = None

                if product_store_create is None:
                    product_store_create = ProductStore(product=d.product_manufacture, stock=d.quantity,
                                                        subsidiary_store=subsidiary_store_set_obj)
                    product_store_create.save()
                    kardex_initial(product_store_create, d.quantity,
                                   price_unit, manufacture_detail_obj=d)
                else:
                    kardex_input(product_store_create.id, d.quantity,
                                 price_unit, manufacture_detail_obj=d)

            new_manufacture_action_obj = ManufactureAction(user=user_obj, date=datetime.now(),
                                                           manufacture=manufacture_obj, status=status_id)
            new_manufacture_action_obj.save()

        elif status_id == '5':
            new_manufacture_action_obj = ManufactureAction(user=user_obj, date=datetime.now(),
                                                           manufacture=manufacture_obj, status=status_id)
            new_manufacture_action_obj.save()

        return JsonResponse({
            'message': 'Se cambio el estado correctamente.',
        }, status=HTTPStatus.OK)


def validate_stock_insume(subsidiary_store, manufacture_id):
    manufacture_details_set = ManufactureDetail.objects.filter(manufacture_id=int(manufacture_id))
    for d in manufacture_details_set.all():
        inputs_set = ManufactureRecipe.objects.filter(manufacture_detail=d)
        for i in inputs_set:
            product_store_inputs_obj = ProductStore.objects.get(subsidiary_store=subsidiary_store,
                                                                product=i.product_input)
            if product_store_inputs_obj.stock < i.quantity:
                return False
    return True


def validate_manufacture_pendient(subsidiary_obj):
    for m in Manufacture.objects.filter(subsidiary=subsidiary_obj):
        last_action = ManufactureAction.objects.filter(manufacture=m).last()
        if last_action.status == '1':
            context = ({
                'code': last_action.manufacture.code,
                'flag': False,
            })
            return context
    return {'flag': True}


def order_list(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        clients = Client.objects.filter(clientassociate__subsidiary=subsidiary_obj)

        return render(request, 'sales/account_status_list.html', {
            'clients': clients,
            'formatdate': formatdate,
        })


def repay_loan(loan_payment_set=None):
    response = 0

    for lp in loan_payment_set:

        if lp.quantity == 0:
            response += lp.price

    return response


def total_remaining_repay_loan(order_detail_set=None):
    response = decimal.Decimal(0.00)

    for d in order_detail_set:

        multiply = d.quantity_sold * d.price_unit

        if d.unit.name == 'G' or d.unit.name == 'GBC':
            loan_payment_set = d.loanpayment_set.all()
            response += (multiply - repay_loan(loan_payment_set))

    return response


def total_repay_loan(order_detail_set=None):
    response = decimal.Decimal(0.00)

    for d in order_detail_set:
        loan_payment_set = d.loanpayment_set.all()
        response = response + repay_loan(loan_payment_set=loan_payment_set)

    return response


def get_dict_orders(client_obj=None, start_date=None, end_date=None):
    order_set = Order.objects.filter(
        client=client_obj, create_at__date__range=[start_date, end_date], type__in=['V', 'R']
    ).prefetch_related(
        Prefetch(
            'orderdetail_set', queryset=OrderDetail.objects.select_related('product', 'unit').prefetch_related(
                Prefetch(
                    'loanpayment_set',
                    queryset=LoanPayment.objects.select_related('order_detail__order').prefetch_related(
                        Prefetch(
                            'transactionpayment_set',
                            queryset=TransactionPayment.objects.select_related('loan_payment__order_detail__order')
                        )
                    )
                ),
            )
        ),
        Prefetch(
            'cashflow_set', queryset=CashFlow.objects.select_related('cash')
        ),
    ).select_related('client').order_by('id')

    dictionary = []

    sum = decimal.Decimal(0.00)

    for o in order_set:

        if o.orderdetail_set.count() > 0:
            order_detail_set = o.orderdetail_set.all()
            order_bill_obj = ''
            total_repay_loan_v = total_repay_loan(order_detail_set=order_detail_set)
            difference = o.total - total_repay_loan_v

            type_bill = 'TICKET'
            serial = o.subsidiary.serial
            correlative_sale = o.correlative_sale
            order_bill_set = OrderBill.objects.filter(order=o.id)

            if order_bill_set.exists():
                order_bill_obj = order_bill_set.first()

                if order_bill_obj.type == '1':
                    type_bill = 'FACTURA'
                    serial = order_bill_obj.serial
                    correlative_sale = order_bill_obj.n_receipt
                elif order_bill_obj.type == '2':
                    type_bill = 'BOLETA'
                    serial = order_bill_obj.serial
                    correlative_sale = order_bill_obj.n_receipt

            new = {
                'id': o.id,
                'order_bill': order_bill_obj,
                'type': o.get_type_display(),
                'type_bill': type_bill,
                'serial': serial,
                'correlative_sale': correlative_sale,
                'client': o.client.names,
                'date': o.create_at,
                'order_detail_set': [],
                'loan_payment_set': [],
                'status': o.get_status_display(),
                'c_status': o.status,
                'total': '{:,}'.format(o.total.quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)),
                'type_pay': o.way_to_pay_type,
                'total_repay_loan': '{:,}'.format(
                    total_repay_loan(order_detail_set=order_detail_set).quantize(decimal.Decimal('0.00'),
                                                                                 rounding=decimal.ROUND_HALF_EVEN)),
                'total_remaining_repay_loan': '{:,}'.format(
                    difference.quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)),
                'rowspan': 0,
                'loan_count': 0,
                'first_detail': OrderDetail.objects.filter(order=o).first().id,
            }

            if o.status != 'A':
                sum = sum + o.sum_total_details()

            loan_payment_set = []
            for lp in LoanPayment.objects.filter(order_detail__order=o):
                _payment_type = '-'
                _cash_flow = None
                transaction_payment_set = lp.transactionpayment_set

                if transaction_payment_set.count() > 0:
                    transaction_payment = transaction_payment_set.last()
                    _cash_flow = transaction_payment.get_cash_flow()
                    _payment_type = transaction_payment.get_type_display()

                loan_payment = {
                    'id': lp.id,
                    'quantity': lp.quantity,
                    'date': lp.create_at,
                    'operation_date': lp.operation_date,
                    'price': lp.price,
                    'type': _payment_type,
                    'cash_flow': _cash_flow,
                    'detail_id': lp.order_detail.id
                    # 'repay_loan': lp.total,
                    # 'repay_loan': lp.order_detail.repay_loan(),
                }
                # loan_payment_set.append(loan_payment)
                new.get('loan_payment_set').append(loan_payment)

            loans_count = LoanPayment.objects.filter(order_detail__order=o).count()
            new['loans_count'] = loans_count

            for d in OrderDetail.objects.filter(order=o):

                loans_count = d.loanpayment_set.all().count()

                if loans_count == 0:
                    rowspan = 1
                else:
                    rowspan = loans_count

                order_detail = {
                    'id': d.id,
                    'product': d.product.name,
                    'unit': d.unit.name,
                    'quantity_sold': d.quantity_sold,
                    'price_unit': d.price_unit,
                    'multiply': '{:,}'.format(
                        d.multiply().quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)),
                    'repay_loan': d.repay_loan(),
                    'loan_payment_set': loan_payment_set,
                    'rowspan': rowspan,
                }
                new.get('order_detail_set').append(order_detail)
                new['rowspan'] = new['rowspan'] + rowspan

            dictionary.append(new)

    sum_total = 0.00
    sum_total_repay_loan = decimal.Decimal(0.00)
    sum_total_remaining_repay_loan = decimal.Decimal(0.00)
    total_sum_ = 0.00
    if order_set.count() > 0:
        for o in order_set:
            sum_total_repay_loan = sum_total_repay_loan + o.total_repay_loan()
            sum_total_remaining_repay_loan = sum_total_remaining_repay_loan + round(o.total_remaining_repay_loan(), 2)
        total_set = order_set.values('client').annotate(totals=Sum('total'))
        total_ = order_set.values('client').aggregate(Sum('total'))
        total_sum_ = total_['total__sum']
        sum_total = total_set[0].get('totals')
    tpl = loader.get_template('sales/account_order_list.html')
    context = ({
        'dictionary': dictionary,
        'sum_total': '{:,}'.format(sum.quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)),
        'sum_total_repay_loan': '{:,}'.format(
            sum_total_repay_loan.quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)),
        'sum_total_remaining_repay_loan': '{:,}'.format(
            sum_total_remaining_repay_loan.quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_UP)),
        'client_obj': client_obj,
        'start_date': start_date,
        'end_date': end_date,
    })

    return tpl.render(context)


def get_orders_by_client(request):
    if request.method == 'GET':
        client_id = request.GET.get('client_id', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')

        client_obj = Client.objects.get(pk=int(client_id))
        # order_set = Order.objects.filter(client=client_obj, status__in=['P', 'C'], type='V').order_by('id')

        return JsonResponse({
            'grid': get_dict_orders(client_obj=client_obj, start_date=start_date, end_date=end_date),
        }, status=HTTPStatus.OK)


def get_iron_man(product_id):
    # user_id = self.request.user.id
    # user_obj = User.objects.get(id=user_id)
    # subsidiary_obj = get_subsidiary_by_user(user_obj)
    product_obj = Product.objects.get(id=product_id)
    subcategory_obj = ProductSubcategory.objects.get(name='FIERRO', product_category__name='FIERRO')
    product_insume_set = ProductRecipe.objects.filter(product=product_obj,
                                                      product_input__product_subcategory=subcategory_obj)
    product_insume_obj = product_insume_set.first().product_input
    return product_insume_obj


def get_order_detail_for_pay(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        detail_id = request.GET.get('detail_id', '')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        detail_obj = OrderDetail.objects.get(id=int(detail_id))
        order_obj = Order.objects.get(orderdetail=detail_obj)
        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        tpl = loader.get_template('sales/new_payment_from_lending.html')

        selected_choices = 'C', 'L', 'EC'

        context = ({
            # 'choices_payments': TransactionPayment._meta.get_field('type').choices,
            'detail': detail_obj,
            'order': order_obj,
            'choices_account': cash_set,
            'choices_account_bank': cash_deposit_set,
            'choices_payments': [(k, v) for k, v in TransactionPayment._meta.get_field('type').choices
                                 if k not in selected_choices],
            'date': formatdate,
            'start_date': start_date,
            'end_date': end_date
        })

        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_expenses(request):
    if request.method == 'GET':
        transactionaccount_obj = TransactionAccount.objects.all()
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        tpl = loader.get_template('sales/new_expense.html')
        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='104')
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        context = ({
            'choices_document': TransactionAccount._meta.get_field('document_type_attached').choices,
            'transactionaccount': transactionaccount_obj,
            'choices_account': cash_set,
            'choices_account_bank': cash_deposit_set,
            'date': formatdate
        })

        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_expense(request):
    if request.method == 'POST':
        transaction_date = str(request.POST.get('id_date'))
        type_document = str(request.POST.get('id_transaction_document_type'))
        serie = str(request.POST.get('id_serie'))
        nro = str(request.POST.get('id_nro'))
        total_pay = str(request.POST.get('pay-loan')).replace(',', '.')
        order = int(request.POST.get('id_order'))
        order_obj = Order.objects.get(id=order)
        subtotal = str(request.POST.get('id_subtotal'))
        igv = str(request.POST.get('igv'))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        serie_obj = None
        nro_obj = None
        if serie:
            serie_obj = serie
        if nro:
            nro_obj = nro
        description_expense = str(request.POST.get('id_description'))
        total = str(request.POST.get('id_amount'))
        _account = str(request.POST.get('id_cash'))
        cashflow_set = CashFlow.objects.filter(cash_id=_account, transaction_date__date=transaction_date, type='A')
        check_closed = CashFlow.objects.filter(type='C', transaction_date__date=transaction_date, cash_id=_account)

        if cashflow_set.count() > 0:
            cash_obj = cashflow_set.first().cash

            if check_closed:
                data = {"error": "La caja seleccionada se encuentra cerrada, favor de seleccionar otra"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            # if decimal.Decimal(total) > decimal.Decimal(total_pay):
            #     data = {
            #         'error': "El monto excede al total de la deuda"}
            #     response = JsonResponse(data)
            #     response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            #     return response
        else:
            data = {'error': "No existe una Apertura de Caja"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        cashflow_obj = CashFlow(
            created_at=transaction_date,
            transaction_date=transaction_date,
            document_type_attached=type_document,
            serial=serie_obj,
            n_receipt=nro_obj,
            description=description_expense,
            subtotal=subtotal,
            igv=igv,
            total=total,
            order=order_obj,
            type='S',
            cash=cash_obj,
            user=user_obj
        )
        cashflow_obj.save()

        order_set = Order.objects.filter(
            client=order_obj.client).exclude(type='E').order_by('id')

        return JsonResponse({
            'message': 'Registro guardado correctamente.',
            'grid': get_dict_orders(order_set, client_obj=order_obj.client, is_pdf=False)
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def new_loan_payment(request):
    data = dict()
    if request.method == 'POST':

        id_detail = int(request.POST.get('detail'))
        detail_obj = OrderDetail.objects.get(id=id_detail)
        option = str(request.POST.get('radio'))  # G or B or P
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        start_date = str(request.POST.get('start_date'))
        end_date = str(request.POST.get('end_date'))

        payment = 0
        quantity = 0

        if option == 'G':
            _operation_date = request.POST.get('date_return_loan0', '')
            if not validate(_operation_date):
                data = {'error': "Seleccione fecha."}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            if len(request.POST.get('loan_payment', '')) > 0:
                val = decimal.Decimal(request.POST.get('loan_payment'))
                if 0 < val <= detail_obj.order.total_remaining_repay_loan():
                    transaction_payment_type = str(request.POST.get('transaction_payment_type'))
                    number_of_vouchers = decimal.Decimal(
                        request.POST.get('number_of_vouchers', '0'))
                    code_operation = str(request.POST.get('code_operation'))

                    payment = val

                    if transaction_payment_type == 'D':
                        cash_flow_description = str(request.POST.get('description_deposit'))
                        cash_flow_transact_date_deposit = str(request.POST.get('id_date_deposit'))
                        cash_id = str(request.POST.get('id_cash_deposit'))
                        cash_obj = Cash.objects.get(id=cash_id)
                        order_obj = detail_obj.order

                        cashflow_obj = CashFlow(
                            created_at=cash_flow_transact_date_deposit,
                            transaction_date=cash_flow_transact_date_deposit,
                            document_type_attached='O',
                            description=cash_flow_description,
                            order=order_obj,
                            type='D',
                            operation_code=code_operation,
                            total=payment,
                            cash=cash_obj,
                            user=user_obj
                        )
                        cashflow_obj.save()

                        loan_payment_obj = LoanPayment(
                            price=payment,
                            quantity=quantity,
                            product=detail_obj.product,
                            order_detail=detail_obj,
                            operation_date=_operation_date
                        )
                        loan_payment_obj.save()

                        transaction_payment_obj = TransactionPayment(
                            payment=payment,
                            number_of_vouchers=number_of_vouchers,
                            type=transaction_payment_type,
                            operation_code=code_operation,
                            loan_payment=loan_payment_obj
                        )
                        transaction_payment_obj.save()

                    if transaction_payment_type == 'E':

                        cash_flow_transact_date = str(request.POST.get('id_date'))
                        cash_flow_description = str(request.POST.get('id_description'))
                        cash_id = str(request.POST.get('id_cash_efectivo'))
                        cash_obj = Cash.objects.get(id=cash_id)
                        order_obj = detail_obj.order
                        cashflow_set = CashFlow.objects.filter(cash_id=cash_id,
                                                               transaction_date__date=cash_flow_transact_date, type='A')
                        if cashflow_set.count() > 0:
                            cash_obj = cashflow_set.first().cash
                        else:
                            data = {'error': "No existe una Apertura de Caja, Favor de revisar las Control de Cajas"}
                            response = JsonResponse(data)
                            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                            return response

                        cashflow_obj = CashFlow(
                            created_at=cash_flow_transact_date,
                            transaction_date=cash_flow_transact_date,
                            document_type_attached='O',
                            description=cash_flow_description,
                            order=order_obj,
                            type='E',
                            total=payment,
                            cash=cash_obj,
                            user=user_obj
                        )
                        cashflow_obj.save()

                        loan_payment_obj = LoanPayment(
                            price=payment,
                            quantity=quantity,
                            product=detail_obj.product,
                            order_detail=detail_obj,
                            operation_date=_operation_date
                        )
                        loan_payment_obj.save()

                        transaction_payment_obj = TransactionPayment(
                            payment=payment,
                            number_of_vouchers=number_of_vouchers,
                            type=transaction_payment_type,
                            operation_code=code_operation,
                            loan_payment=loan_payment_obj
                        )
                        transaction_payment_obj.save()

                    if transaction_payment_type == 'F':
                        cash_flow_description = str(request.POST.get('id_description_deposit_fise'))
                        cash_flow_transact_date_deposit = str(request.POST.get('id_date_desposit_fise'))
                        cash_id = str(request.POST.get('id_cash_deposit_fise'))
                        cash_obj = Cash.objects.get(id=cash_id)
                        order_obj = detail_obj.order

                        cashflow_obj = CashFlow(
                            created_at=cash_flow_transact_date_deposit,
                            transaction_date=cash_flow_transact_date_deposit,
                            document_type_attached='O',
                            description=cash_flow_description,
                            order=order_obj,
                            type='D',
                            operation_code=code_operation,
                            total=payment,
                            cash=cash_obj,
                            user=user_obj
                        )
                        cashflow_obj.save()

                        loan_payment_obj = LoanPayment(
                            price=payment,
                            quantity=quantity,
                            product=detail_obj.product,
                            order_detail=detail_obj,
                        )
                        loan_payment_obj.save()

                        transaction_payment_obj = TransactionPayment(
                            payment=payment,
                            number_of_vouchers=number_of_vouchers,
                            type=transaction_payment_type,
                            operation_code=code_operation,
                            loan_payment=loan_payment_obj
                        )
                        transaction_payment_obj.save()

        else:
            if option == 'B':
                _operation_date = request.POST.get('date_return_loan', '')
                if not validate(_operation_date):
                    data = {'error': "Seleccione fecha."}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

                if len(request.POST.get('loan_quantity', '')) > 0:
                    val = decimal.Decimal(request.POST.get('loan_quantity'))
                    if 0 < val <= detail_obj.quantity_sold:
                        quantity = val
                        loan_payment_obj = LoanPayment(
                            price=detail_obj.price_unit,
                            quantity=quantity,
                            product=detail_obj.product,
                            order_detail=detail_obj,
                            operation_date=_operation_date
                        )
                        loan_payment_obj.save()
                        if detail_obj.order.type == 'V':
                            if detail_obj.unit.name == 'B':
                                product_supply_obj = get_iron_man(detail_obj.product.id)
                                subsidiary_store_supply_obj = SubsidiaryStore.objects.get(
                                    subsidiary=detail_obj.order.subsidiary_store.subsidiary, category='I')
                                try:
                                    product_store_supply_obj = ProductStore.objects.get(product=product_supply_obj,
                                                                                        subsidiary_store=subsidiary_store_supply_obj)
                                    kardex_input(product_store_supply_obj.id, quantity,
                                                 product_supply_obj.calculate_minimum_price_sale(),
                                                 loan_payment_obj=loan_payment_obj)
                                except ProductStore.DoesNotExist:
                                    product_store_supply_obj = ProductStore(
                                        product=product_supply_obj,
                                        subsidiary_store=subsidiary_store_supply_obj,
                                        stock=quantity
                                    )
                                    product_store_supply_obj.save()
                                    kardex_initial(product_store_supply_obj, quantity,
                                                   product_supply_obj.calculate_minimum_price_sale(),
                                                   loan_payment_obj=loan_payment_obj)

            elif option == 'P':
                _operation_date = request.POST.get('date_return_loan2', '')
                if not validate(_operation_date):
                    data = {'error': "Seleccione fecha."}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response
                if len(request.POST.get('loan_quantity2', '')) > 0:
                    val = decimal.Decimal(request.POST.get('loan_quantity2'))

                    if 0 < val <= detail_obj.quantity_sold:
                        quantity = val
                        if len(request.POST.get('loan_payment2', '')) > 0:
                            val2 = decimal.Decimal(request.POST.get('loan_payment2'))
                            if 0 < val2 <= detail_obj.multiply():
                                transaction_payment_type = str(
                                    request.POST.get('transaction_payment_type2'))
                                code_operation = str(request.POST.get('code_operation2'))
                                payment = val2
                                unit_price_with_discount = payment / quantity
                                product_detail_obj = ProductDetail.objects.get(product=detail_obj.product,
                                                                               unit=detail_obj.unit)
                                unit_price = product_detail_obj.price_sale
                                _discount = unit_price - unit_price_with_discount

                                if transaction_payment_type == 'D':
                                    cash_flow_transact_date = str(request.POST.get('id_date_desposit2'))
                                    cash_flow_description = str(request.POST.get('description_deposit2'))
                                    cash_id = str(request.POST.get('id_cash_deposit2'))
                                    cash_obj = Cash.objects.get(id=cash_id)
                                    order_obj = detail_obj.order

                                    cashflow_obj = CashFlow(
                                        created_at=cash_flow_transact_date,
                                        transaction_date=cash_flow_transact_date,
                                        document_type_attached='O',
                                        description=cash_flow_description,
                                        order=order_obj,
                                        type='D',
                                        operation_code=code_operation,
                                        total=payment,
                                        cash=cash_obj,
                                        user=user_obj
                                    )
                                    cashflow_obj.save()

                                    loan_payment_obj = LoanPayment(
                                        price=unit_price_with_discount,
                                        quantity=quantity,
                                        discount=_discount,
                                        product=detail_obj.product,
                                        order_detail=detail_obj,
                                        operation_date=_operation_date
                                    )
                                    loan_payment_obj.save()

                                    transaction_payment_obj = TransactionPayment(
                                        payment=payment,
                                        type=transaction_payment_type,
                                        operation_code=code_operation,
                                        loan_payment=loan_payment_obj
                                    )
                                    transaction_payment_obj.save()

                                if transaction_payment_type == 'E':

                                    cash_flow_transact_date = str(request.POST.get('id_date2'))
                                    cash_flow_description = str(request.POST.get('id_description2'))
                                    cash_id = str(request.POST.get('id_cash_efectivo2'))
                                    cash_obj = Cash.objects.get(id=cash_id)
                                    order_obj = detail_obj.order
                                    cashflow_set = CashFlow.objects.filter(cash_id=cash_id,
                                                                           transaction_date__date=cash_flow_transact_date,
                                                                           type='A')
                                    if cashflow_set.count() > 0:
                                        cash_obj = cashflow_set.first().cash
                                    else:
                                        data = {
                                            'error': "No existe una Apertura de Caja, Favor de revisar las Control de Cajas"}
                                        response = JsonResponse(data)
                                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                                        return response

                                    cashflow_obj = CashFlow(
                                        created_at=cash_flow_transact_date,
                                        transaction_date=cash_flow_transact_date,
                                        document_type_attached='O',
                                        description=cash_flow_description,
                                        order=order_obj,
                                        type='E',
                                        total=payment,
                                        cash=cash_obj,
                                        user=user_obj
                                    )
                                    cashflow_obj.save()

                                    loan_payment_obj = LoanPayment(
                                        price=unit_price_with_discount,
                                        quantity=quantity,
                                        discount=_discount,
                                        product=detail_obj.product,
                                        order_detail=detail_obj,
                                        operation_date=_operation_date
                                    )
                                    loan_payment_obj.save()

                                    transaction_payment_obj = TransactionPayment(
                                        payment=payment,
                                        type=transaction_payment_type,
                                        operation_code=code_operation,
                                        loan_payment=loan_payment_obj
                                    )
                                    transaction_payment_obj.save()

        order_set = Order.objects.filter(
            client=detail_obj.order.client).exclude(type='E').order_by('id')

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'grid': get_dict_orders(client_obj=detail_obj.order.client, start_date=start_date, end_date=end_date),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def open_loan_account(order_detail_obj, payment=0, quantity=0):
    new_quantity = decimal.Decimal(quantity)
    new_price_unit = decimal.Decimal(payment)
    new_price_total = new_quantity * new_price_unit
    new_remaining_quantity = new_quantity
    new_remaining_price = new_price_unit
    new_remaining_price_total = new_remaining_quantity * new_remaining_price

    new_loan_account = LoanAccount(
        operation='L',
        quantity=new_quantity,
        price_unit=new_price_unit,
        price_total=new_price_total,
        remaining_quantity=new_remaining_quantity,
        remaining_price=new_remaining_price,
        remaining_price_total=new_remaining_price_total,
        product=order_detail_obj.product,
        order_detail=order_detail_obj,
    )
    new_loan_account.save()


def return_loan_account(order_detail_obj, payment=0, quantity=0):
    new_quantity = decimal.Decimal(quantity)
    new_price_unit = decimal.Decimal(payment)
    new_price_total = new_quantity * new_price_unit

    loan_account_set = LoanAccount.objects.filter(
        client=order_detail_obj.order.client, product=order_detail_obj.product)

    if loan_account_set.count > 0:
        last_loan_account = loan_account_set.last()
        last_remaining_quantity = last_loan_account.remaining_quantity
        last_remaining_price_total = last_loan_account.remaining_price_total

        new_remaining_quantity = last_remaining_quantity + new_quantity
        new_remaining_price = (decimal.Decimal(last_remaining_price_total) +
                               new_price_total) / new_remaining_quantity
        new_remaining_price_total = new_remaining_quantity * new_remaining_price

        new_loan_account = LoanAccount(
            operation='P',
            quantity=new_quantity,
            price_unit=new_price_unit,
            price_total=new_price_total,
            remaining_quantity=new_remaining_quantity,
            remaining_price=new_remaining_price,
            remaining_price_total=new_remaining_price_total,
            product=order_detail_obj.product,
            order_detail=order_detail_obj,
        )
        new_loan_account.save()


def get_order_detail_for_ball_change(request):
    if request.method == 'GET':
        detail_id = request.GET.get('detail_id', '')
        detail_obj = OrderDetail.objects.get(id=int(detail_id))
        tpl = loader.get_template('sales/new_ball_change.html')
        context = ({
            'choices_status': BallChange._meta.get_field('status').choices,
            'detail': detail_obj,
        })

        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_ball_change(request):
    if request.method == 'POST':

        id_detail = int(request.POST.get('detail'))
        detail_obj = OrderDetail.objects.get(id=id_detail)

        quantity = 0
        ball_change_obj = None

        if len(request.POST.get('quantity', '')) > 0:
            val = decimal.Decimal(request.POST.get('quantity'))
            if 0 < val <= detail_obj.quantity_sold:
                status = str(request.POST.get('status'))
                observation = str(request.POST.get('observation'))
                quantity = val

                ball_change_obj = BallChange(
                    status=status,
                    observation=observation,
                    quantity=quantity,
                    product=detail_obj.product,
                    order_detail=detail_obj,
                )
                ball_change_obj.save()

        if detail_obj.order.type == 'V':

            # OUTPUT SALES
            subsidiary_store_sales_obj = detail_obj.order.subsidiary_store
            product_store_sales_obj = ProductStore.objects.get(product=detail_obj.product,
                                                               subsidiary_store=subsidiary_store_sales_obj)
            kardex_ouput(product_store_sales_obj.id, quantity, ball_change_obj=ball_change_obj)

            # INPUT MAINTENANCE
            try:
                subsidiary_store_maintenance_obj = SubsidiaryStore.objects.get(
                    subsidiary=detail_obj.order.subsidiary_store.subsidiary, category='R')
            except SubsidiaryStore.DoesNotExist:
                data = {'error': 'No se encontro el almacen de mantenimiento.'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            try:
                product_store_maintenance_obj = ProductStore.objects.get(product=detail_obj.product,
                                                                         subsidiary_store=subsidiary_store_maintenance_obj)
                kardex_input(product_store_maintenance_obj.id, quantity,
                             detail_obj.product.calculate_minimum_price_sale(),
                             ball_change_obj=ball_change_obj)
            except ProductStore.DoesNotExist:
                product_store_maintenance_obj = ProductStore(
                    product=detail_obj.product,
                    subsidiary_store=subsidiary_store_maintenance_obj,
                    stock=quantity
                )
                product_store_maintenance_obj.save()
                kardex_initial(product_store_maintenance_obj, quantity,
                               detail_obj.product.calculate_minimum_price_sale(),
                               ball_change_obj=ball_change_obj)

        order_set = Order.objects.filter(
            client=detail_obj.order.client).exclude(type='E').order_by('id')

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'grid': get_dict_orders(order_set, client_obj=detail_obj.order.client, is_pdf=False),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def generate_receipt(request):
    truck_set = Truck.objects.exclude(truck_model__name__in=['INTER', 'VOLVO'])
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    SubsidiaryStore_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V').first()
    product_store_set = ProductStore.objects.filter(subsidiary_store=SubsidiaryStore_obj)
    products_set = Product.objects.filter(productstore__in=product_store_set)
    clients = Client.objects.all()

    return render(request, 'sales/receipt_random.html', {
        'trucks': truck_set,
        'products_set': products_set,
        'clients': clients
    })


def get_supplies_view(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='I').first()
    product_store_set = ProductStore.objects.filter(subsidiary_store=subsidiary_store_obj)
    products_supplies_set = Product.objects.filter(productstore__in=product_store_set,
                                                   is_supply=True)

    return render(request, 'sales/report_stock_product_supplies_grid.html', {
        'products_supplies_set': products_supplies_set,
    })


def PerceptronList(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        clients_set = Client.objects.filter(clienttype__document_type='06')
        orders = Order.objects.all()
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d %H:%M:%S")
        truck_Set = Truck.objects.all()

        return render(request, 'sales/new_perceptron.html', {
            'orders': orders,
            'clients': clients_set,
            'date': formatdate
        })


def get_stock_product_store(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj)
    truck_set = Truck.objects.filter(subsidiary=subsidiary_obj, drive_type='R')
    product_set = Product.objects.all()
    # dic_stock = ['num':valor]
    dic_stock = {}
    for p in product_set.all():
        stock_ = ProductStore.objects.filter(product__id=p.id,
                                             subsidiary_store__subsidiary=subsidiary_obj).aggregate(
            Sum('stock'))
        # row = {
        #     p.id: stock_['stock__sum'],
        # }s
        dic_stock[p.id] = stock_['stock__sum']
        # dic_stock.append(row)
        # dic_stock[p.id] = {'id': p.id, 'name': p.name, 'stock': stock_['stock__sum']}
    distribution_dictionary = []
    tid = {"B5": 0, "B10": 0, "B15": 0, "B45": 0}
    for t in truck_set.all():
        truck_obj = Truck.objects.get(id=int(t.id))
        distribution_list = DistributionMobil.objects.filter(status='F', truck=truck_obj,
                                                             subsidiary=subsidiary_obj).aggregate(Max('id'))

        if distribution_list['id__max'] is not None:
            distribution_mobil_obj = DistributionMobil.objects.get(id=int(distribution_list['id__max']))
            new = {
                'id_m': distribution_mobil_obj.id,
                'truck': distribution_mobil_obj.truck.license_plate,
                'pilot': distribution_mobil_obj.pilot.full_name(),
                'distribution': [],
            }
            details_list = DistributionDetail.objects.filter(status='C', distribution_mobil=distribution_mobil_obj)
            if details_list.exists():
                for dt_dist in details_list.all():
                    details_mobil = {
                        'id_d': dt_dist.id,
                        'product': dt_dist.product.name,
                        'unit': dt_dist.unit.description,
                        'quantity': dt_dist.quantity,
                    }
                    new.get('distribution').append(details_mobil)
                    if dt_dist.product.code == 'B-10' or dt_dist.product.code == 'F-10':
                        tid['B10'] = tid['B10'] + dt_dist.quantity
                    else:
                        if dt_dist.product.code == 'B-5' or dt_dist.product.code == 'F-5':
                            tid['B5'] = tid['B5'] + dt_dist.quantity
                        else:
                            if dt_dist.product.code == 'B-15' or dt_dist.product.code == 'F-15':
                                tid['B15'] = tid['B15'] + dt_dist.quantity
                            else:
                                if dt_dist.product.code == 'B-45' or dt_dist.product.code == 'F-45':
                                    tid['B45'] = tid['B45'] + dt_dist.quantity

                distribution_dictionary.append(new)

    return render(request, 'sales/report_stock_product_subsidiary.html', {
        'subsidiary_store_set': subsidiary_store_obj,
        'dictionary': distribution_dictionary,
        'dic_stock': dic_stock,
        'tid': tid,
    })


def get_product_recipe_view(request):
    if request.method == 'GET':
        product_pk = request.GET.get('pk', '')
        product_obj = Product.objects.get(id=int(product_pk))
        product_recipe_set = ProductRecipe.objects.filter(product=product_obj)
        products_supplies = Product.objects.filter(is_supply=True)
        unit_set = Unit.objects.all()
        t = loader.get_template('sales/product_recipe_update.html')
        c = ({
            'product_recipe_set': product_recipe_set,
            'products_supplies_set': products_supplies,
            'product_obj': product_obj,
            'unit_set': unit_set,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def delete_recipe(request):
    if request.method == 'GET':
        product_recipe_id = int(request.GET.get('pk', ''))
        product_recipe_obj = ProductRecipe.objects.get(id=product_recipe_id)
        product_recipe_obj.delete()
        return JsonResponse({
            'success': True,
        })


def save_update_recipe(request):
    if request.method == 'GET':
        data = request.GET.get('_details', '')
        registry = json.loads(data)

        product_ins_id = int(registry["_product"])
        product_ins_obj = Product.objects.get(id=product_ins_id)

        _quantity = decimal.Decimal(registry["_quantity"])

        unit_id = int(registry["_unit"])
        unit_obj = Unit.objects.get(id=unit_id)

        _price = decimal.Decimal(registry["_price"])

        product_manufacture_id = int(registry["_product_finality"])
        product_manufacture_obj = Product.objects.get(id=product_manufacture_id)

        try:
            product_recipe_id = int(registry["_id"])
            product_recipe_obj = ProductRecipe.objects.get(id=product_recipe_id)
        except ProductRecipe.DoesNotExist:
            product_recipe_id = 0
        _valor = ''
        _key = 0
        if product_recipe_id == 0:
            recipe_product = {
                'product': product_manufacture_obj,
                'product_input': product_ins_obj,
                'quantity': _quantity,
                'unit': unit_obj,
                'price': _price
            }
            new_recipe_obj = ProductRecipe.objects.create(**recipe_product)
            new_recipe_obj.save()
            _key = new_recipe_obj.id
            _valor = 'Registro ingresado correctamente'
        else:
            product_recipe_obj.product_input = product_ins_obj
            product_recipe_obj.quantity = _quantity
            product_recipe_obj.unit = unit_obj
            product_recipe_obj.price = _price
            product_recipe_obj.save()
            _key = product_recipe_obj.id
            _valor = 'Registro actualizado correctamente'

        return JsonResponse({
            'success': True,
            'key': _key,
            'message': _valor,
        }, status=HTTPStatus.OK)


def new_massiel_payment(request):
    if request.method == 'POST':
        client_orders = int(request.POST.get('client_orders'))  # client_orders
        order_indexes = str(request.POST.get('order_indexes'))  # order_indexes
        order_indexes = order_indexes.replace(']', '').replace('[', '')
        _arr = order_indexes.split(",")
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        payment = 0

        _operation_date = request.POST.get('date_return_loan0', '')
        if not validate(_operation_date):
            data = {'error': "Seleccione fecha."}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if len(request.POST.get('loan_payment', '')) > 0:
            massive_payment = decimal.Decimal(request.POST.get('loan_payment'))  # massive_payment
            transaction_payment_type = str(request.POST.get('transaction_payment_type'))
            number_of_vouchers = 0
            if request.POST.get('number_of_vouchers', '0') != '':
                number_of_vouchers = decimal.Decimal(request.POST.get('number_of_vouchers', '0'))
            code_operation = str(request.POST.get('code_operation'))
            cash_obj = None
            cash_flow_date = ''
            cash_flow_type = ''
            cash_flow_description = ''
            if transaction_payment_type == 'D':
                cash_flow_description = str(request.POST.get('description_deposit'))
                cash_flow_type = 'D'
                cash_flow_date = str(request.POST.get('id_date_deposit'))
                cash_id = str(request.POST.get('id_cash_deposit'))
                cash_obj = Cash.objects.get(id=cash_id)
            elif transaction_payment_type == 'E':
                cash_flow_date = str(request.POST.get('id_date'))
                cash_flow_description = str(request.POST.get('id_description'))
                cash_flow_type = 'E'
                cash_id = str(request.POST.get('id_cash_efectivo'))
                cashflow_set = CashFlow.objects.filter(cash_id=cash_id,
                                                       transaction_date__date=cash_flow_date, type='A')
                if cashflow_set.count() > 0:
                    cash_obj = cashflow_set.first().cash
                else:
                    data = {'error': "No existe una Apertura de Caja, Favor de revisar las Control de Cajas"}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response
            elif transaction_payment_type == 'F':
                cash_flow_description = str(request.POST.get('id_description_deposit_fise'))
                cash_flow_date = str(request.POST.get('id_date_desposit_fise'))
                cash_id = str(request.POST.get('id_cash_deposit_fise'))
                cash_obj = Cash.objects.get(id=cash_id)
                cash_flow_type = 'D'

            for a in _arr:
                order_obj = Order.objects.get(id=int(a))
                detail_with_unit_g_set = order_obj.orderdetail_set.filter(Q(unit__name='G') | Q(unit__name='GBC'))
                for da in detail_with_unit_g_set:
                    # if da.repay_loan() == 0:
                    payment = da.multiply() - da.repay_loan()
                    massive_payment = massive_payment - payment
                    save_loan_payment_in_cash_flow(
                        cash_obj=cash_obj,
                        user_obj=user_obj,
                        order_obj=order_obj,
                        order_detail=da,
                        cash_flow_date=cash_flow_date,
                        cash_flow_type=cash_flow_type,
                        cash_flow_operation_code=code_operation,
                        cash_flow_total=payment,
                        cash_flow_description=(cash_flow_description + ' | IMPORTE: {}').format(str(payment)),
                        loan_payment_quantity=0,
                        loan_payment_operation_date=_operation_date,
                        transaction_payment_number_of_vouchers=number_of_vouchers,
                        transaction_payment_type=transaction_payment_type,
                    )
            client_obj = Client.objects.get(id=client_orders)
            order_set = Order.objects.filter(client=client_obj).exclude(type='E').order_by('id')

        return JsonResponse({
            'success': True,
            'message': 'El cliente se asocio correctamente.',
            'grid': get_dict_orders(order_set, client_obj=client_obj, is_pdf=False),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def save_loan_payment_in_cash_flow(
        cash_obj=None,
        user_obj=None,
        order_obj=None,
        order_detail=None,
        cash_flow_date='',
        cash_flow_type='',
        cash_flow_operation_code='',
        cash_flow_total=0,
        cash_flow_description='',
        loan_payment_quantity=0,
        loan_payment_operation_date='',
        transaction_payment_number_of_vouchers=0,
        transaction_payment_type='',
):
    cash_flow_obj = CashFlow(
        transaction_date=cash_flow_date,
        document_type_attached='O',
        description=cash_flow_description,
        order=order_obj,
        type=cash_flow_type,
        operation_code=cash_flow_operation_code,
        total=cash_flow_total,
        cash=cash_obj,
        user=user_obj
    )
    cash_flow_obj.save()

    loan_payment_obj = LoanPayment(
        price=cash_flow_total,
        quantity=loan_payment_quantity,
        product=order_detail.product,
        order_detail=order_detail,
        operation_date=loan_payment_operation_date
    )
    loan_payment_obj.save()

    transaction_payment_obj = TransactionPayment(
        payment=cash_flow_total,
        number_of_vouchers=transaction_payment_number_of_vouchers,
        type=transaction_payment_type,
        operation_code=cash_flow_operation_code,
        loan_payment=loan_payment_obj
    )
    transaction_payment_obj.save()


def get_massiel_payment_form(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        massive_payment = request.GET.get('massive_payment', '')
        massive_return = request.GET.get('massive_return', '')
        client_orders = request.GET.get('client_orders', '')
        order_indexes = request.GET.get('order_indexes', '')
        massive_type = request.GET.get('massive_type', '')

        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')

        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        tpl = None
        context = ()
        if massive_type == 'MP':
            tpl = loader.get_template('sales/new_massiel_payment_form.html')
            context = ({
                'choices_payments': TransactionPayment._meta.get_field('type').choices,
                'massive_payment': massive_payment,
                'order_indexes': order_indexes,
                'client_orders': client_orders,
                'choices_account': cash_set,
                'choices_account_bank': cash_deposit_set,
                'date': formatdate
            })
        elif massive_type == 'MR':
            tpl = loader.get_template('sales/new_massiel_return_form.html')
            context = ({
                'massive_return': massive_return,
                'order_indexes': order_indexes,
                'client_orders': client_orders,
                'date': formatdate
            })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_massiel_return(request):
    if request.method == 'POST':
        client_orders = int(request.POST.get('client_orders'))  # client_orders
        order_indexes = str(request.POST.get('order_indexes'))  # order_indexes
        order_indexes = order_indexes.replace(']', '').replace('[', '')
        _arr = order_indexes.split(",")
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        _operation_date = request.POST.get('date_return_loan0', '')
        if not validate(_operation_date):
            data = {'error': "Seleccione fecha."}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if len(request.POST.get('loan_quantity', '')) > 0:
            massive_return = decimal.Decimal(request.POST.get('loan_quantity'))  # massive_return

            for a in _arr:
                order_obj = Order.objects.get(id=int(a))
                detail_with_unit_ball_set = order_obj.orderdetail_set.filter(unit__name='B')

                for da in detail_with_unit_ball_set:
                    quantity = da.quantity_sold
                    loan_payment_obj = LoanPayment(
                        price=da.price_unit,
                        quantity=quantity,
                        product=da.product,
                        order_detail=da,
                        operation_date=_operation_date
                    )
                    loan_payment_obj.save()
                    if order_obj.type == 'V':
                        product_supply_obj = get_iron_man(da.product.id)
                        subsidiary_store_supply_obj = SubsidiaryStore.objects.get(
                            subsidiary=da.order.subsidiary_store.subsidiary, category='I')
                        try:
                            product_store_supply_obj = ProductStore.objects.get(product=product_supply_obj,
                                                                                subsidiary_store=subsidiary_store_supply_obj)
                            kardex_input(product_store_supply_obj.id, quantity,
                                         product_supply_obj.calculate_minimum_price_sale(),
                                         loan_payment_obj=loan_payment_obj)
                        except ProductStore.DoesNotExist:
                            product_store_supply_obj = ProductStore(
                                product=product_supply_obj,
                                subsidiary_store=subsidiary_store_supply_obj,
                                stock=quantity
                            )
                            product_store_supply_obj.save()
                            kardex_initial(product_store_supply_obj, quantity,
                                           product_supply_obj.calculate_minimum_price_sale(),
                                           loan_payment_obj=loan_payment_obj)

                    massive_return = massive_return - quantity

        client_obj = Client.objects.get(id=client_orders)
        order_set = Order.objects.filter(client=client_obj).exclude(type='E').order_by('id')

        return JsonResponse({
            'success': True,
            'message': 'El cliente se asocio correctamente.',
            'grid': get_dict_orders(order_set, client_obj=client_obj, is_pdf=False),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def calculate_age(birthdate):
    today = date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age
    # # Driver code
    # print(calculateAge(date(1997, 2, 3)), "years")


def get_name_business(request):
    if request.method == 'GET':
        nro_document = request.GET.get('nro_document', '')
        type_document = request.GET.get('type', '')
        result = ''
        address = ''
        age = ''
        client_obj_search = Client.objects.filter(clienttype__document_number=nro_document)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        client_obj = None
        if client_obj_search:
            if type_document == '01' or type_document == '00':
                names = client_obj_search.first().names
                id_client = client_obj_search.first().id
                search_client_associate = ClientAssociate.objects.filter(subsidiary=subsidiary_obj,
                                                                         client__id=id_client)
                if search_client_associate.count() == 0:
                    client_associate = {
                        'client': client_obj_search.first(),
                        'subsidiary': subsidiary_obj,
                    }
                    client_associate_obj = ClientAssociate.objects.create(**client_associate)
                    client_associate_obj.save()

                try:
                    address_search = ClientAddress.objects.filter(client_id=id_client).last()
                except ClientAddress.DoesNotExist:
                    address_search = None
                if address_search is None:
                    _address__ = '-'
                else:
                    _address__ = address_search.address

                return JsonResponse({'pk': id_client, 'result': names, 'address': _address__, 'age': age},
                                    status=HTTPStatus.OK)

            elif type_document == '06':
                id_client = client_obj_search.first().id
                _address__ = '-'
                try:
                    address_search = ClientAddress.objects.filter(client_id=id_client).last()
                except ClientAddress.DoesNotExist:
                    address_search = None
                if address_search is None:
                    _address__ = '-'
                else:
                    _address__ = address_search.address
                names = client_obj_search.first().names
                search_client_associate = ClientAssociate.objects.filter(subsidiary=subsidiary_obj,
                                                                         client__id=id_client)
                if search_client_associate.count() == 0:
                    client_associate = {
                        'client': client_obj_search.first(),
                        'subsidiary': subsidiary_obj,
                    }
                    client_associate_obj = ClientAssociate.objects.create(**client_associate)
                    client_associate_obj.save()
                return JsonResponse({'pk': id_client, 'result': names, 'address': _address__},
                                    status=HTTPStatus.OK)
        else:
            if type_document == '01':
                type_name = 'DNI'
                r = query_api_facturacioncloud(nro_document, type_name)
                name = r.get('Nombre')
                paternal_name = r.get('Paterno')
                maternal_name = r.get('Materno')

                if r.get('statusMessage') != 'SERVICIO SE VENCIO' and r.get('errors') is None:

                    if paternal_name is not None and len(paternal_name) > 0:
                        result = name + ' ' + paternal_name + ' ' + maternal_name

                        if len(result.strip()) != 0:
                            client_obj = Client(
                                names=result,
                            )
                            client_obj.save()

                            client_type_obj = ClientType(
                                document_number=nro_document,
                                client=client_obj,
                                document_type_id=type_document
                            )
                            client_type_obj.save()
                            search_client_associate = ClientAssociate.objects.filter(subsidiary=subsidiary_obj,
                                                                                     client=client_obj)
                            if search_client_associate.count() == 0:
                                client_associate = {
                                    'client': client_obj,
                                    'subsidiary': subsidiary_obj,
                                }
                                client_associate_obj = ClientAssociate.objects.create(**client_associate)
                                client_associate_obj.save()
                        else:
                            data = {'error': 'NO EXISTE DNI. REGISTRE MANUALMENTE'}
                            response = JsonResponse(data)
                            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                            return response

                else:
                    r = query_apis_net_dni_ruc(nro_document, type_name)
                    name = r.get('nombres')
                    paternal_name = r.get('apellidoPaterno')
                    maternal_name = r.get('apellidoMaterno')

                    if paternal_name is not None and len(paternal_name) > 0:

                        result = name + ' ' + paternal_name + ' ' + maternal_name

                        if len(result.strip()) != 0:
                            client_obj = Client(
                                names=result,
                            )
                            client_obj.save()

                            client_type_obj = ClientType(
                                document_number=nro_document,
                                client=client_obj,
                                document_type_id=type_document
                            )
                            client_type_obj.save()
                            search_client_associate = ClientAssociate.objects.filter(subsidiary=subsidiary_obj,
                                                                                     client=client_obj)
                            if search_client_associate.count() == 0:
                                client_associate = {
                                    'client': client_obj,
                                    'subsidiary': subsidiary_obj,
                                }
                                client_associate_obj = ClientAssociate.objects.create(**client_associate)
                                client_associate_obj.save()
                        else:
                            data = {'error': 'NO EXISTE DNI. REGISTRE MANUALMENTE'}
                            response = JsonResponse(data)
                            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                            return response

                    else:
                        data = {
                            'error': 'PROBLEMAS CON LA CONSULTA A LA RENIEC, FAVOR DE INTENTAR MAS TARDE O REGISTRE MANUALMENTE'}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response

            elif type_document == '06':

                type_name = 'RUC'
                r = query_apis_net_dni_ruc(nro_document, type_name)

                if r.get('numeroDocumento') == nro_document:

                    business_name = r.get('nombre')
                    address_business = r.get('direccion')
                    result = business_name
                    address = address_business

                    client_obj = Client(
                        names=result,
                    )
                    client_obj.save()

                    client_type_obj = ClientType(
                        document_number=nro_document,
                        client=client_obj,
                        document_type_id=type_document
                    )
                    client_type_obj.save()

                    client_address_obj = ClientAddress(
                        address=address,
                        client=client_obj
                    )
                    client_address_obj.save()
                    search_client_associate = ClientAssociate.objects.filter(subsidiary=subsidiary_obj,
                                                                             client=client_obj)
                    if search_client_associate.count() == 0:
                        client_associate = {
                            'client': client_obj,
                            'subsidiary': subsidiary_obj,
                        }
                        client_associate_obj = ClientAssociate.objects.create(**client_associate)
                        client_associate_obj.save()
                else:
                    r = query_api_facturacioncloud(nro_document, type_name)

                    if r.get('statusMessage') != 'SERVICIO SE VENCIO' and r.get('errors') is None:

                        if r.get('ruc') == nro_document:

                            business_name = r.get('razonSocial')
                            address_business = r.get('direccion')
                            result = business_name
                            address = address_business

                            client_obj = Client(
                                names=result,
                            )
                            client_obj.save()

                            client_type_obj = ClientType(
                                document_number=nro_document,
                                client=client_obj,
                                document_type_id=type_document
                            )
                            client_type_obj.save()

                            client_address_obj = ClientAddress(
                                address=address,
                                client=client_obj
                            )
                            client_address_obj.save()
                            search_client_associate = ClientAssociate.objects.filter(subsidiary=subsidiary_obj,
                                                                                     client=client_obj)
                            if search_client_associate.count() == 0:
                                client_associate = {
                                    'client': client_obj,
                                    'subsidiary': subsidiary_obj,
                                }
                                client_associate_obj = ClientAssociate.objects.create(**client_associate)
                                client_associate_obj.save()
                    else:
                        data = {'error': 'NO EXISTE RUC. REGISTRE MANUAL O CORREGIRLO'}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response

        return JsonResponse({'pk': client_obj.id, 'result': result, 'address': address, 'age': age},
                            status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_costs_purchase_dates(request):
    if request.method == 'GET':
        details_request = request.GET.get('data', '')
        if details_request != '':
            data_json = json.loads(details_request)
            date_initial = (data_json['date_initial'])
            date_final = (data_json['date_final'])
            dictionary = []
            total_qp = 0
            total_qs = 0
            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            subsidiary_store_obj = SubsidiaryStore.objects.filter(category='V', subsidiary=subsidiary_obj).first()
            for p in Product.objects.filter(productstore__subsidiary_store=subsidiary_store_obj,
                                            is_enabled=True).values('id', 'name'):
                total_quantity_purchase = PurchaseDetail.objects.filter(
                    purchase__purchase_date__range=(date_initial, date_final), product__id=p['id']).values(
                    'quantity').aggregate(
                    Sum('quantity'))
                if total_quantity_purchase['quantity__sum'] is None:
                    total_qp = 0
                else:
                    total_qp = total_quantity_purchase['quantity__sum']
                try:
                    purchase_detail = PurchaseDetail.objects.filter(product__id=p['id'],
                                                                    purchase__purchase_date__range=(
                                                                        date_initial, date_final)).last()
                except PurchaseDetail.DoesNotExist:
                    price_unit = 0
                    price_total = 0
                if purchase_detail is None:
                    price_unit = 0
                    price_total = 0
                else:
                    price_unit = purchase_detail.price_unit
                    price_total = purchase_detail.price_unit * decimal.Decimal(total_qp)
                total_quantity_sales = OrderDetail.objects.filter(
                    order__create_at__range=(date_initial, date_final), product__id=p['id']).values(
                    'quantity_sold').aggregate(
                    Sum('quantity_sold'))
                if total_quantity_sales['quantity_sold__sum'] is None:
                    total_qs = 0
                else:
                    total_qs = total_quantity_sales['quantity_sold__sum']
                product_store = ProductStore.objects.filter(product__id=p['id'], subsidiary_store__category='V').values(
                    'stock').first()
                new_list = {
                    'product': p['name'],
                    'quantity_purchase': total_qp,
                    'quantity_sales': total_qs,
                    'stock': product_store['stock'],
                    'price_unit_purchase': decimal.Decimal(price_unit),
                    'price_total_purchase': decimal.Decimal(price_total)
                }
                dictionary.append(new_list)
            tpl = loader.get_template('sales/report_product_purchase_grid_list.html')
            context = ({
                'dictionary': dictionary,
            })
            return JsonResponse({
                'success': True,
                'grid': tpl.render(context, request),
            })
        else:
            my_date = datetime.now()
            formatdate = my_date.strftime("%Y-%m-%d")
            return render(request, 'sales/report_product_purchase_list.html', {
                'date': formatdate
            })


# def get_costs_purchase_dates(request):
#     if request.method == 'GET':
#         details_request = request.GET.get('data', '')
#         if details_request != '':
#             data_json = json.loads(details_request)
#             date_initial = (data_json['date_initial'])
#             date_final = (data_json['date_final'])
#             dictionary = []
#             for p in Product.objects.all():
#                 total_quantity_purchase = PurchaseDetail.objects.filter(
#                     purchase__purchase_date__range=(date_initial, date_final), product__id=p.id).aggregate(
#                     Sum('quantity'))
#                 purchase_detail = PurchaseDetail.objects.filter(product__id=p.id).last()
#                 total_quantity_sales = OrderDetail.objects.filter(
#                     order__create_at__range=(date_initial, date_final), product__id=p.id).aggregate(
#                     Sum('quantity_sold'))
#                 product_store = ProductStore.objects.filter(product__id=p.id, subsidiary_store__category='V').first()
#                 new_list = {
#                     'product': p.name,
#                     'quantity_purchase': total_quantity_purchase,
#                     'quantity_sales': total_quantity_sales,
#                     'stock': product_store.stock,
#                     'price_unit_purchase': purchase_detail.price_unit,
#                     'price_total_purchase': purchase_detail.price_unit*total_quantity_purchase
#                 }
#                 dictionary.append(new_list)
#             tpl = loader.get_template('sales/report_product_purchase_grid_list.html')
#             context = ({
#                 'dictionary': dictionary,
#             })
#             return JsonResponse({
#                 'success': True,
#                 'grid': tpl.render(context),
#             }, status=HTTPStatus.OK)

def update_address(request):
    if request.method == 'GET':
        _pk = request.GET.get('pk_', '')
        _address = request.GET.get('address_', '')
        client_obj = Client.objects.get(id=int(_pk))
        client_address_obj = ClientAddress(
            address=_address,
            client=client_obj
        )
        client_address_obj.save()

        return JsonResponse({'message': 'Direccion actualizada'},
                            status=HTTPStatus.OK)


class SalesOrder(View):
    template_name = 'sales/sales_list.html'

    def get_context_data(self, **kwargs):
        error = ""
        user_id = self.request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        contexto = {}
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        sales_store = None
        product_dict = []

        # client_type_set = ClientType.objects.select_related('client').all()
        client_dict = {}
        address = ''
        # for ct in client_type_set:
        #     key = ct.client.id
        #     if key not in client_dict:
        #
        #         if ct.client.clientaddress_set.last() is not None:
        #             address = ct.client.clientaddress_set.last().address
        #
        #         client_dict[key] = {
        #             'client_id': ct.client.id,
        #             'client_names': ct.client.names,
        #             'client_document_number': ct.document_number,
        #             'client_address': address,
        #             'client_type_document': ct.document_type_id
        #         }

        if subsidiary_obj is None:
            error = "No tiene una sede definida."
        else:
            sales_store = SubsidiaryStore.objects.filter(
                subsidiary=subsidiary_obj, category='V').first()

            document_types = DocumentType.objects.all()
            series_set = Subsidiary.objects.filter(id=subsidiary_obj.id)
            cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
            cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')
            family_set = ProductFamily.objects.all()
            users_set = User.objects.filter(is_superuser=False)

            selected_choices = 'EC', 'L', 'Y'

            contexto['choices_account'] = cash_set
            contexto['choices_account_bank'] = cash_deposit_set
            contexto['error'] = error
            contexto['sales_store'] = sales_store
            contexto['subsidiary'] = subsidiary_obj
            contexto['family_set'] = family_set
            # contexto['client_dict'] = client_dict
            contexto['districts'] = District.objects.all()
            contexto['document_types'] = document_types
            contexto['date'] = formatdate
            # contexto['choices_payments'] = TransactionPayment._meta.get_field('type').choices
            contexto['choices_payments'] = [(k, v) for k, v in TransactionPayment._meta.get_field('type').choices
                                            if k not in selected_choices]
            contexto['series'] = series_set
            contexto['order_set'] = Order._meta.get_field('type').choices
            contexto['users'] = users_set

            return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


def get_price_sale(percentage=None, price=None):
    if percentage is None or price is None:
        return 0
    else:
        return round((percentage * price) / 100 + price, 2)


def get_product_sales_grid_new(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        product_set = None
        value = request.GET.get('value', '')
        type_search = request.GET.get('type', '')

        if type_search == 'P':
            array_value = value.split()
            product_query = Product.objects
            full_query = None

            for i in range(0, len(array_value)):
                q = Q(name__icontains=array_value[i]) | Q(product_brand__name__icontains=array_value[i])
                if full_query is None:
                    full_query = q
                else:
                    full_query = full_query & q

            product_set = product_query.filter(full_query, is_enabled=True).select_related(
                'product_family', 'product_brand').prefetch_related(
                Prefetch(
                    'productstore_set',
                    queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary').prefetch_related(
                        Prefetch('productserial_set')
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

        elif type_search == 'B':
            product_set = Product.objects.filter(barcode=value, is_enabled=True).select_related(
                'product_family', 'product_brand').prefetch_related(
                Prefetch(
                    'productstore_set',
                    queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary').prefetch_related(
                        Prefetch('productserial_set')
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

        elif type_search == 'S':
            product_set = Product.objects.filter(is_enabled=True, productstore__productserial__status='C',
                                                 productstore__productserial__serial_number=value).select_related(
                'product_family', 'product_brand'
            ).prefetch_related(
                Prefetch(
                    'productstore_set',
                    queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary').prefetch_related(
                        Prefetch(
                            'productserial_set',
                            queryset=ProductSerial.objects.filter(serial_number=value)
                        )
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')
            # product_set = ProductSerial.objects.filter(serial_number=value, status='C',
            #                                            product_store__product__is_enabled=True).select_related(
            #     'product_store', 'product_store__product').order_by('id')

        # print(get_products_serial_dict(product_set))
        t = loader.get_template('sales/order_sales_product_grid.html')
        c = ({
            'subsidiary': subsidiary_obj,
            'product_dict': product_set,
            'type_search': type_search
        })
        return JsonResponse({
            'grid': t.render(c, request),
            'product_set': get_products_serial_dict(product_set),
        })


def get_products_serial_dict(product_set):
    product_serial_dict = []
    if product_set:
        for p in product_set:
            product_item = {
                'id': p.id,
                'name': p.name,
                'product_store': []
            }
            for ps in p.productstore_set.all():
                item_store = {
                    'id': ps.id,
                    'stock': ps.stock,
                    'serial': []
                }
                for s in ps.productserial_set.filter(status='C'):
                    item_serial = {
                        'id': s.id,
                        'status': s.status,
                        'serial': s.serial_number
                    }
                    item_store.get('serial').append(item_serial)
                product_item.get('product_store').append(item_store)
            product_serial_dict.append(product_item)
    return product_serial_dict


def get_product_sales_grid(request):
    if request.method == 'GET':
        family_pk = request.GET.get('pk', '')
        family_obj = ProductFamily.objects.get(id=int(family_pk))
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        sales_store = None
        product_dict = []
        sales_store = SubsidiaryStore.objects.filter(
            subsidiary=subsidiary_obj, category='V').first()

        product_set = Product.objects.filter(product_family=family_obj,
                                             productstore__subsidiary_store=sales_store).values(
            'id',
            'name',
            'code',
        )

        # product_set = Product.objects.filter(product_family=family_obj, productstore__subsidiary_store=sales_store).select_related(
        #     'product_family', 'product_brand').prefetch_related(
        #     Prefetch(
        #         'productstore_set', queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
        #     ),
        #     Prefetch(
        #         'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
        #     ),
        # ).order_by('id')

        for p in product_set:
            product_store_set = ProductStore.objects.filter(product__id=p['id']).values(
                'id',
                'subsidiary_store__name',
                'subsidiary_store__category',
                'subsidiary_store__subsidiary__id',
                'subsidiary_store__subsidiary__name',
                'stock',
            )

            product_detail_set = ProductDetail.objects.filter(product__id=p['id']).annotate(
                one=(F('percentage_one') * F('price_purchase') / 100) + F('price_purchase')
            ).annotate(
                two=(F('percentage_two') * F('price_purchase') / 100) + F('price_purchase')
            ).annotate(
                three=(F('percentage_three') * F('price_purchase') / 100) + F('price_purchase')
            ).values(
                'id',
                'unit__id',
                'unit__name',
                'unit__description',
                'quantity_minimum',
                'percentage_one',
                'percentage_two',
                'percentage_three',
                'one',
                'two',
                'three',
            )

            product_item = {
                'id': p['id'],
                'name': p['name'],
                'code': p['code'],
                'product_store_set': product_store_set,
                'product_detail_set': product_detail_set,
            }

            product_dict.append(product_item)
        t = loader.get_template('sales/order_sales_product_grid.html')
        c = ({
            'subsidiary': subsidiary_obj,
            'product_dic': product_dict
        })
        return JsonResponse({
            'grid': t.render(c, request),
        })


def get_product_by_criteria(request):
    if request.method == 'GET':
        value = request.GET.get('value', '')
        criteria = request.GET.get('criteria', '')
        brand_id = None
        if request.GET.get('brand', ''):
            brand_id = int(request.GET.get('brand', ''))
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        product_set = get_product_list(criteria=criteria, value=value, brand=brand_id)
        t = loader.get_template('sales/product_grid_list.html')
        c = ({
            'products': product_set,
            'subsidiary': subsidiary_obj,
            'total_price_purchase': get_total_price_purchase(product_set)
        })

        return JsonResponse({
            'message': 'Actualizado correctamente',
            'success': True,
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_product_list(criteria=None, value=None, brand=None):
    product_set = None

    # Subqueries para obtener la última fecha de compra y cantidad comprada
    last_purchase_date = PurchaseDetail.objects.filter(
        product=OuterRef('id'),
        purchase__status='A'
    ).order_by('-purchase__purchase_date').values('purchase__purchase_date')[:1]

    last_purchase_quantity = PurchaseDetail.objects.filter(
        product=OuterRef('id'),
        purchase__status='A'
    ).order_by('-purchase__purchase_date').values('quantity')[:1]

    last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]

    has_serials = Exists(
        ProductSerial.objects.filter(
            product_store__product=OuterRef('id')
        )
    )

    if criteria == 'all':
        product_set = Product.objects.all()

    elif criteria == 'name':
        product_set = Product.objects.filter(name__icontains=value)

    elif brand is not None:
        product_set = Product.objects.filter(product_brand_id=brand, is_enabled=True).select_related(
            'product_family', 'product_brand'
        ).annotate(
            last_purchase_date=Subquery(last_purchase_date),
            last_purchase_quantity=Subquery(last_purchase_quantity),
            has_serials=has_serials
        ).prefetch_related(
            Prefetch(
                'productstore_set',
                queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                .exclude(subsidiary_store__subsidiary=3)
                .annotate(
                    last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                )
            ),
            Prefetch(
                'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
            ),
        ).order_by('id')

    elif criteria == 'name_contains':
        array_value = value.split()
        product_query = Product.objects
        full_query = None

        for term in array_value:
            q = Q(name__icontains=term) | Q(product_brand__name__icontains=term)
            full_query = q if full_query is None else full_query & q

        product_set = product_query.filter(full_query, is_enabled=True).select_related(
            'product_family', 'product_brand'
        ).annotate(
            last_purchase_date=Subquery(last_purchase_date),
            last_purchase_quantity=Subquery(last_purchase_quantity),
            has_serials=has_serials
        ).prefetch_related(
            Prefetch(
                'productstore_set',
                queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                .exclude(subsidiary_store__subsidiary=3)
                .annotate(
                    last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                )
            ),
            Prefetch(
                'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
            ),
        ).order_by('id')

    elif criteria == 'barcode':
        product_set = Product.objects.filter(productdetail__code=value).annotate(
            last_purchase_date=Subquery(last_purchase_date),
            last_purchase_quantity=Subquery(last_purchase_quantity),
            has_serials=has_serials
        )

    return product_set


def get_total_price_purchase(product_set):
    total_price_purchase = decimal.Decimal(0.00)
    for p in product_set:
        for pd in p.productdetail_set.all():
            total_price_purchase += pd.price_purchase
    return round(total_price_purchase, 2)


@csrf_exempt
def save_family(request):
    if request.method == 'POST':
        _name = request.POST.get('id-name', '')
        product_family_obj = ProductFamily(
            name=_name,
        )
        product_family_obj.save()
        return JsonResponse({
            'success': True,
        }, status=HTTPStatus.OK)


def modal_family_save(request):
    if request.method == 'GET':
        t = loader.get_template('sales/modal-family-register.html')
        c = ({})
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def modal_category_save(request):
    if request.method == 'GET':
        t = loader.get_template('sales/modal_category_register.html')
        c = ({})
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def modal_subcategory_save(request):
    if request.method == 'GET':
        category_set = ProductCategory.objects.all()
        t = loader.get_template('sales/modal_subcategory_register.html')
        c = ({
            'category_set': category_set
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


@csrf_exempt
def save_category(request):
    if request.method == 'POST':
        _name = request.POST.get('id-name', '')
        product_category_obj = ProductCategory(
            name=_name,
        )
        product_category_obj.save()
        return JsonResponse({
            'success': True,
        }, status=HTTPStatus.OK)


@csrf_exempt
def save_subcategory(request):
    if request.method == 'POST':
        _name = request.POST.get('id-name', '')
        _category = request.POST.get('id-category', '')
        category_obj = ProductCategory.objects.get(id=int(_category))
        product_subcategory_obj = ProductSubcategory(
            name=_name,
            product_category=category_obj
        )
        product_subcategory_obj.save()
        return JsonResponse({
            'success': True,
        }, status=HTTPStatus.OK)


def modal_brand_save(request):
    if request.method == 'GET':
        t = loader.get_template('sales/modal_brand_register.html')
        c = ({
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


@csrf_exempt
def save_brand(request):
    if request.method == 'POST':
        _name = request.POST.get('id-name', '')
        product_brand_obj = ProductBrand(
            name=_name
        )
        product_brand_obj.save()
        return JsonResponse({
            'success': True,
        }, status=HTTPStatus.OK)


def info_product_detail(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        t = loader.get_template('sales/card_product.html')
        c = ({
            'id_pk': pk,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        }, status=HTTPStatus.OK)


def product_detail(request):
    data = {}
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            product_obj = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            data['error'] = "producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        products = Product.objects.all()
        units = Unit.objects.all()
        t = loader.get_template('sales/card_product_detail.html')
        c = ({
            'product': product_obj,
            'units': units,
            'products': products,
        })

        product_details = ProductDetail.objects.filter(product=product_obj).order_by('id')
        tpl2 = loader.get_template('sales/card_product_detail_grid.html')
        context2 = ({'product_details': product_details, })
        serialized_data = serializers.serialize('json', product_details)
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
            'grid': tpl2.render(context2),
            'serialized_data': serialized_data,
            # 'form': t.render(c),
        }, status=HTTPStatus.OK)
    else:
        if request.method == 'POST':
            id_product = request.POST.get('product', '')
            price_sale = request.POST.get('price_sale', '')
            id_unit = request.POST.get('unit', '')
            p1 = request.POST.get('id_p1', '')
            p2 = request.POST.get('id_p2', '')
            p3 = request.POST.get('id_p3', '')
            price_purchase = request.POST.get('id_price_purchase', '')
            quantity_minimum = request.POST.get('quantity_minimum', '')

            if decimal.Decimal(price_sale) == 0 or decimal.Decimal(quantity_minimum) == 0:
                data['error'] = "Ingrese valores validos."
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            product_obj = Product.objects.get(id=int(id_product))
            unit_obj = Unit.objects.get(id=int(id_unit))

            try:
                product_detail_obj = ProductDetail(
                    product=product_obj,
                    price_sale=decimal.Decimal(price_sale),
                    unit=unit_obj,
                    quantity_minimum=decimal.Decimal(quantity_minimum),
                    percentage_one=p1,
                    percentage_two=p2,
                    percentage_three=p3,
                    price_purchase=decimal.Decimal(price_purchase)
                )
                product_detail_obj.save()
            except DatabaseError as e:
                data['error'] = str(e)
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            except IntegrityError as e:
                data['error'] = str(e)
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            product_details = ProductDetail.objects.filter(product=product_obj).order_by('id')
            tpl2 = loader.get_template('sales/card_product_detail_grid.html.html')
            context2 = ({'product_details': product_details, })

            return JsonResponse({
                'message': 'Guardado con exito.',
                'grid': tpl2.render(context2),
            }, status=HTTPStatus.OK)


def get_modal_update_stock(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        _product_id = request.GET.get('_product_id', '')
        product_dict = []
        product = Product.objects.get(id=_product_id)
        product_store_set = ProductStore.objects.filter(product_id=_product_id,
                                                        subsidiary_store__subsidiary=subsidiary_obj).values(
            'id',
            'subsidiary_store__name',
            'subsidiary_store__category',
            'subsidiary_store__id',
            'subsidiary_store__subsidiary__id',
            'subsidiary_store__subsidiary__name',
            'subsidiary_store__subsidiary__serial',
            'stock',
            'product__name',
            'product__id',
            'product__code',
        )

        for p in product_store_set:
            product_item = {
                'id': p['id'],
                'name': p['product__name'],
                'code': p['product__code'],
                'product_store_set': product_store_set,
            }
            product_dict.append(product_item)
        tpl = loader.get_template('sales/new_stock_update.html')

        context = ({
            'product': product,
            'product_dict': product_dict
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_update_stock(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        product_id = request.POST.get('product', '')
        old_stock = decimal.Decimal(request.POST.get('old-stock'))
        new_stock = request.POST.get('new-stock', '')
        if new_stock == '':
            data = {'error': 'INGRESE UN DIGITO VALIDO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        product_obj = Product.objects.get(id=int(product_id))
        product_store_obj = ProductStore.objects.get(product__id=product_id,
                                                     subsidiary_store__subsidiary=subsidiary_obj)
        kardex_set = Kardex.objects.filter(product_store=product_store_obj)

        if decimal.Decimal(new_stock) <= 0:
            data = {'error': 'EL NUEVO STOCK NO PUEDE SER 0 O UN VALOR NEGATIVO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if len(kardex_set) == 1:
            kardex_obj = kardex_set.first()
            kardex_obj.remaining_quantity = decimal.Decimal(new_stock)
            kardex_obj.remaining_price_total = decimal.Decimal(new_stock)
            kardex_obj.save()
            product_store_obj.stock = decimal.Decimal(new_stock)
            product_store_obj.save()
        else:
            data = {'error': 'NO SE PUEDE ACTUALIZAR EL STOCK, EL PRODUCTO YA CUENTA CON KARDEX'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        return JsonResponse({
            'message': 'Cambio actualizado correctamente',
            'new_stock': decimal.Decimal(new_stock),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_modal_change_price_purchase(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        _product_id = request.GET.get('_product_id', '')
        product_dict = []
        product = Product.objects.get(id=_product_id)

        product_detail_set = ProductDetail.objects.filter(product__id=_product_id).annotate(
            one=(F('percentage_one') * F('price_purchase') / 100) + F('price_purchase')
        ).annotate(
            two=(F('percentage_two') * F('price_purchase') / 100) + F('price_purchase')
        ).annotate(
            three=(F('percentage_three') * F('price_purchase') / 100) + F('price_purchase')
        ).values(
            'id',
            'unit__id',
            'unit__name',
            'unit__description',
            'quantity_minimum',
            'percentage_one',
            'percentage_two',
            'percentage_three',
            'price_purchase',
            'one',
            'two',
            'three',
            'product__id',
            'product__name',
            'product__code',
            'update_at',
            'user__username',
        )

        for p in product_detail_set:
            product_item = {
                'id': p['product__id'],
                'name': p['product__name'],
                'code': p['product__code'],
                'product_detail_set': product_detail_set,
            }
            product_dict.append(product_item)
        tpl = loader.get_template('sales/new_change_price_purchase_product.html')

        context = ({
            'product': product,
            'product_dict': product_dict
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_modal_change_price_purchase_dollar(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        _product_id = request.GET.get('_product_id', '')
        product_dict = []
        product = Product.objects.get(id=_product_id)

        product_detail_set = ProductDetail.objects.filter(product__id=_product_id).annotate(
            one=(F('percentage_one') * F('price_purchase') / 100) + F('price_purchase')
        ).annotate(
            two=(F('percentage_two') * F('price_purchase') / 100) + F('price_purchase')
        ).annotate(
            three=(F('percentage_three') * F('price_purchase') / 100) + F('price_purchase')
        ).values(
            'id',
            'unit__id',
            'unit__name',
            'unit__description',
            'quantity_minimum',
            'percentage_one',
            'percentage_two',
            'percentage_three',
            'price_purchase',
            'price_purchase_dollar',
            'one',
            'two',
            'three',
            'product__id',
            'product__name',
            'product__code',
            'update_at',
            'user__username',
        )

        for p in product_detail_set:
            product_item = {
                'id': p['product__id'],
                'name': p['product__name'],
                'code': p['product__code'],
                'product_detail_set': product_detail_set,
            }
            product_dict.append(product_item)
        tpl = loader.get_template('sales/new_change_price_purchase_dollar.html')

        context = ({
            'product': product,
            'product_dict': product_dict
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_change_price_purchase(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        product_id = request.POST.get('product', '')
        new_price_purchase = request.POST.get('new-price-purchase', '')
        new_percent_one = request.POST.get('new-percent-one', '')
        new_percent_two = request.POST.get('new-percent-two', '')
        new_percent_three = request.POST.get('new-percent-three', '')

        if new_price_purchase == '':
            data = {'error': 'INGRESE UN DIGITO VALIDO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        product_detail_obj = ProductDetail.objects.get(product__id=product_id)

        if decimal.Decimal(new_price_purchase) <= 0:
            data = {'error': 'EL NUEVO PRECIO DE COMPRA NO PUEDE SER 0 O UN VALOR NEGATIVO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        product_detail_obj.price_purchase = decimal.Decimal(new_price_purchase)
        product_detail_obj.user = user_obj
        product_detail_obj.save()

        return JsonResponse({
            'message': 'Cambio actualizado correctamente',
            'new_price_purchase': decimal.Decimal(new_price_purchase),
            'new_percent_calculate_one': new_percent_one,
            'new_percent_calculate_two': new_percent_two,
            'new_percent_calculate_three': new_percent_three,
            'new_percent_one': product_detail_obj.percentage_one,
            'new_percent_two': product_detail_obj.percentage_two,
            'new_percent_three': product_detail_obj.percentage_three,
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def new_change_price_purchase_dollar_product(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        product_id = request.POST.get('product', '')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        # type_change_dollar = request.POST.get('type_change_dollar', '')
        buy_dollar = ''
        new_price_purchase_dollar = decimal.Decimal(request.POST.get('new-price-purchase-dollar', ''))
        new_price_purchase_sol = 0

        if new_price_purchase_dollar == '':
            data = {'error': 'INGRESE UN DIGITO VALIDO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        product_detail_obj = ProductDetail.objects.get(product__id=product_id)

        if decimal.Decimal(new_price_purchase_dollar) <= 0:
            data = {'error': 'EL NUEVO PRECIO DE COMPRA NO PUEDE SER 0 O UN VALOR NEGATIVO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        product_detail_obj.price_purchase_dollar = decimal.Decimal(new_price_purchase_dollar)
        type_change_dollar_set = MoneyChange.objects.filter(search_date=formatdate, sunat_date=formatdate)

        if type_change_dollar_set.exists():
            type_change_dollar_obj = type_change_dollar_set.last()
            buy_dollar = type_change_dollar_obj.buy
        else:
            data = {'error': 'NO EXISTE TIPO DE CAMBIO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        product_detail_obj.price_purchase = decimal.Decimal(new_price_purchase_dollar * decimal.Decimal(buy_dollar))
        # product_detail_obj.user = user_obj
        product_detail_obj.save()

        new_price_purchase_sol = decimal.Decimal(new_price_purchase_dollar * decimal.Decimal(buy_dollar))
        percent1 = round((
                                 product_detail_obj.percentage_one * product_detail_obj.price_purchase) / 100 + product_detail_obj.price_purchase,
                         2)
        percent2 = round((
                                 product_detail_obj.percentage_two * product_detail_obj.price_purchase) / 100 + product_detail_obj.price_purchase,
                         2)
        percent3 = round((
                                 product_detail_obj.percentage_three * product_detail_obj.price_purchase) / 100 + product_detail_obj.price_purchase,
                         2)

        return JsonResponse({
            'message': 'CAMBIO DE PRECIO ACTUALIZADO CORRECTAMENTE',
            'new_price_purchase_dollar': decimal.Decimal(new_price_purchase_dollar),
            'new_price_purchase_sol': new_price_purchase_sol,
            'percent1': percent1,
            'percent2': percent2,
            'percent3': percent3,
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_sales_quotation_by_subsidiary(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/order_quotation_list.html', {'formatdate': formatdate, })
    elif request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        if subsidiary_obj is not None:
            orders = Order.objects.filter(subsidiary=subsidiary_obj, type='T').exclude(status='A')
            start_date = str(request.POST.get('start-date'))
            end_date = str(request.POST.get('end-date'))

            if start_date == end_date:
                orders = orders.filter(create_at__date=start_date)
            else:
                orders = orders.filter(create_at__date__range=[start_date, end_date])
            if orders:
                return JsonResponse({
                    'grid': get_dict_order_quotation(orders),
                }, status=HTTPStatus.OK)
            else:
                data = {'error': "No hay operaciones registradas"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        else:
            data = {'error': "No hay sucursal"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response


def get_dict_order_quotation(order_set):
    dictionary = []
    sum_orders = 0

    for o in order_set:
        _order_detail = o.orderdetail_set.all()
        order_sale_quotation = ''

        if o.order_sale_quotation is not None:
            order_sale_quotation = o.order_sale_quotation.id

        order = {
            'id': o.id,
            'status': o.get_status_display(),
            'client': o.client,
            'client_nro': o.client.clienttype_set.first().document_number,
            'user': o.user,
            'total': o.total,
            'subsidiary': o.subsidiary.name,
            'create_at': o.create_at,
            'serial': o.subsidiary.serial,
            'correlative_sale': o.correlative_sale,
            'validity_date': o.validity_date,
            'date_completion': o.date_completion,
            'place_delivery': o.place_delivery,
            'type_quotation': o.get_type_quotation_display(),
            'type_name_quotation': o.type_name_quotation,
            'observation': o.observation,
            'way_to_pay_type': o.get_way_to_pay_type_display(),
            'order_sale_quotation': order_sale_quotation,
            'type': o.get_type_display(),
            'has_quotation_order': o.has_quotation_order,
            'order_detail_set': [],
            'details': _order_detail.count()
        }
        sum_orders = sum_orders + o.total

        for d in _order_detail:
            order_detail = {
                'id': d.id,
                'product': d.product.name,
                'unit': d.unit.name,
                'quantity_sold': d.quantity_sold,
                'price_unit': d.price_unit,
                'multiply': d.multiply
            }
            order.get('order_detail_set').append(order_detail)

        dictionary.append(order)

    tpl = loader.get_template('sales/order_quotation_grid_list.html')
    context = ({
        'dictionary': dictionary,
        'sum_orders': sum_orders,
    })
    return tpl.render(context)


def cancel_order(request):
    if request.method == 'GET':
        start_date = str(request.GET.get('start-date'))
        end_date = str(request.GET.get('end-date'))
        order_id = int(request.GET.get('pk', ''))

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        order_obj = Order.objects.get(pk=order_id)

        type_bill = 'T'
        order_bill_set = OrderBill.objects.filter(order=order_id)

        if order_bill_set.exists():
            order_bill_obj = order_bill_set.first()
            if order_bill_obj.type == '1':
                type_bill = 'F'
            elif order_bill_obj.type == '2':
                type_bill = 'B'

        if type_bill == 'F' or type_bill == 'B':
            # r = send_cancel_bill_nubefact(order_id)
            # enlace = r.get('enlace')
            # code = r.get('codigo')
            # if enlace or code:
            r = annul_invoice(order_id)
            success = r.get('success')
            if success:
                for d in order_obj.orderdetail_set.all():
                    _product_id = d.product.id
                    product_obj = Product.objects.get(id=int(_product_id))
                    _unit = d.unit.id
                    unit_obj = Unit.objects.get(id=int(_unit))
                    _quantity_sold = d.quantity_sold
                    _price_unit = d.price_unit
                    _subtotal = d.quantity_sold * d.price_unit
                    product_detail_obj = ProductDetail.objects.get(product=product_obj, unit=unit_obj)
                    if product_detail_obj.unit.name != 'ZZ':
                        _minimum_quantity = product_detail_obj.quantity_minimum

                        product_store_obj = ProductStore.objects.get(product__id=_product_id,
                                                                     subsidiary_store__subsidiary=subsidiary_obj,
                                                                     subsidiary_store__category='V')

                        product_serial_set = ProductSerial.objects.filter(order_detail=d,
                                                                          product_store=product_store_obj)
                        if product_serial_set.exists():
                            for ps in product_serial_set:
                                ps.order_detail = None
                                ps.status = 'C'
                                ps.save()

                        kardex_input(product_store_id=product_store_obj.id, price_unit=_price_unit,
                                     quantity_purchased=_quantity_sold,
                                     order_detail_obj=d)

                order_obj.status = 'A'
                order_obj.save()
                cash_obj = CashFlow.objects.filter(order=order_obj)
                cash_obj.delete()

            else:
                data = {'error': "Error de anulación en sunat, "
                                 "Si es BOLETA ELECTRONICA, se debe esperar minimo 24 horas"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        elif type_bill == 'T':

            for d in order_obj.orderdetail_set.all():
                _product_id = d.product.id
                product_obj = Product.objects.get(id=int(_product_id))
                _unit = d.unit.id
                unit_obj = Unit.objects.get(id=int(_unit))
                _quantity_sold = d.quantity_sold
                _price_unit = d.price_unit
                _subtotal = d.quantity_sold * d.price_unit

                product_detail_obj = ProductDetail.objects.get(product=product_obj, unit=unit_obj)
                _minimum_quantity = product_detail_obj.quantity_minimum

                product_store_obj = ProductStore.objects.get(product__id=_product_id,
                                                             subsidiary_store__subsidiary=subsidiary_obj,
                                                             subsidiary_store__category='V')

                product_serial_set = ProductSerial.objects.filter(order_detail=d,
                                                                  product_store=product_store_obj)
                if product_serial_set.exists():
                    for ps in product_serial_set:
                        ps.order_detail = None
                        ps.status = 'C'
                        ps.save()

                kardex_input(product_store_id=product_store_obj.id, price_unit=_price_unit,
                             quantity_purchased=_quantity_sold,
                             order_detail_obj=d)

            order_obj.status = 'A'
            order_obj.save()
            cash_obj = CashFlow.objects.filter(order=order_obj)
            cash_obj.delete()

        if start_date == end_date:
            orders = Order.objects.filter(create_at__date=start_date, subsidiary=subsidiary_obj,
                                          type='V', status__in=['P', 'A']).order_by('id')
        else:
            orders = Order.objects.filter(create_at__date__range=[start_date, end_date], subsidiary=subsidiary_obj,
                                          type='V', status__in=['P', 'A']).order_by('id')

        if orders:
            has_rows = True
        else:
            data = {'error': "No hay encomiendas registradas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        return JsonResponse({
            'grid': get_dict_order_queries(orders, start_date, end_date, is_pdf=False, is_unit=False),
        }, status=HTTPStatus.OK)

        # tpl = loader.get_template('sales/order_sales_grid_list.html')
        # context = ({
        #     'grid': get_dict_order_queries(orders, is_pdf=False, is_unit=False),
        #     'has_rows': has_rows
        # })
        # return JsonResponse({
        #     'grid': tpl.render(context, request),
        # }, status=HTTPStatus.OK)


def save_new_client_sale(request):
    data = dict()
    client_names = ''
    client_address = ''
    client_id = ''
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        client_request = request.GET.get('client_dict', '')
        client_dict = json.loads(client_request)

        client_type_document = (client_dict["ClientTypeDocument"])
        client_document_number = (client_dict["ClientDocumentNumber"])
        client_names = str(client_dict["ClientNames"])
        client_phone = str(client_dict["ClientPhone"])
        client_email = str(client_dict["ClientEmail"])
        client_address = str(client_dict["ClientAddress"])
        client_district = (client_dict["ClientDistrict"])
        client_reference = str(client_dict["ClientReference"])

        client_exists_set = Client.objects.filter(names=client_names)

        if client_exists_set.exists():
            data['error'] = "El cliente ya se encuentra registrado"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        try:
            document_type_obj = DocumentType.objects.get(id=client_type_document)
        except DocumentType.DoesNotExist:
            data['error'] = "El tipo de Documento no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        try:
            district_obj = District.objects.get(id=client_district)
        except District.DoesNotExist:
            data['error'] = "Distrito no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        client_obj = Client(
            names=client_names,
            phone=client_phone,
            email=client_email
        )
        client_obj.save()

        client_id = client_obj.id

        client_type_obj = ClientType(
            document_number=client_document_number,
            document_type=document_type_obj,
            client=client_obj
        )
        client_type_obj.save()

        client_address_obj = ClientAddress(
            address=client_address,
            reference=client_reference,
            district=district_obj,
            client=client_obj
        )
        client_address_obj.save()

        client_associate_obj = ClientAssociate(
            client=client_obj,
            subsidiary=subsidiary_obj
        )
        client_associate_obj.save()

    return JsonResponse({
        'names': client_names,
        'client_id': client_id,
        'client_address': client_address,
        'message': 'CLIENTE GUARDADO CORRECTAMENTE',
    }, status=HTTPStatus.OK)


def get_modal_new_product(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        family_set = ProductFamily.objects.all()
        brand_set = ProductBrand.objects.all()
        unit_set = Unit.objects.all()

        tpl = loader.get_template('sales/new_product.html')

        context = ({
            'families': family_set,
            'brands': brand_set,
            'units': unit_set,
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def save_product_detail(request):
    data = {}
    if request.method == 'POST':
        product_name = request.POST.get('product', '')
        code_product = request.POST.get('code', '')
        price_sale = request.POST.get('price_sale', '')
        get_stock_min = request.POST.get('stock-min', '')
        get_stock_max = request.POST.get('stock-max', '')
        family_product_id = request.POST.get('family-product', '')
        brand_product_id = request.POST.get('brand-product', '')
        id_unit = request.POST.get('unit', '')
        p1 = request.POST.get('id_p1', 0)
        p2 = request.POST.get('id_p2', 0)
        p3 = request.POST.get('id_p3', 0)
        price_purchase = request.POST.get('id_price_purchase', '')
        quantity_minimum = request.POST.get('quantity_minimum', '')
        stock_max = 0
        stock_min = 0
        if get_stock_min == '':
            stock_min = 0
        if get_stock_max == '':
            stock_max = 0

        if product_name == '':
            data['error'] = "Ingrese Nombre del Producto. "
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        try:
            _photo = request.FILES['exampleInputFile']
        except Exception as e:
            _photo = 'pic_folder/None/no-img.jpg'

        try:
            product_family_obj = ProductFamily.objects.get(id=family_product_id)
            product_brand_obj = ProductBrand.objects.get(id=brand_product_id)

            product_obj = Product(
                name=product_name,
                code=code_product,
                stock_min=stock_min,
                stock_max=stock_max,
                product_family=product_family_obj,
                product_brand=product_brand_obj,
                photo=_photo
            )
            product_obj.save()

        except DatabaseError as e:
            data['error'] = str(e)
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if decimal.Decimal(price_sale) == 0 or decimal.Decimal(quantity_minimum) == 0:
            data['error'] = "Ingrese valores validos."
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        # product_obj = Product.objects.get(id=int(id_product))
        unit_obj = Unit.objects.get(id=int(id_unit))

        try:
            product_detail_obj = ProductDetail(
                product=product_obj,
                price_sale=decimal.Decimal(price_sale),
                unit=unit_obj,
                quantity_minimum=decimal.Decimal(quantity_minimum),
                percentage_one=decimal.Decimal(p1),
                percentage_two=decimal.Decimal(p2),
                percentage_three=decimal.Decimal(p3),
                price_purchase=decimal.Decimal(price_purchase)
            )
            product_detail_obj.save()
        except DatabaseError as e:
            data['error'] = str(e)
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        except IntegrityError as e:
            data['error'] = str(e)
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        product_details = ProductDetail.objects.filter(product=product_obj).order_by('id')
        tpl2 = loader.get_template('sales/product_detail_grid_list.html')
        context2 = ({'product_details': product_details, })

        return JsonResponse({
            'message': 'Guardado con exito.',
            'grid': tpl2.render(context2),
        }, status=HTTPStatus.OK)
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def delete_item_product(request):
    if request.method == 'GET':
        detail_id = request.GET.get('detail_id', '')
        order_detail_obj = OrderDetail.objects.get(id=detail_id)
        order_detail_obj.delete()

        return JsonResponse({
            'message': 'Eliminado.',
        }, status=HTTPStatus.OK)


def update_quotation(request):
    if request.method == 'GET':
        sale_request = request.GET.get('sales', '')
        data_sale = json.loads(sale_request)
        type_payment = (data_sale["type_payment"])
        _date = str(data_sale["Date"])
        cod_operation = str(data_sale["cod_operation"])
        client_id = str(data_sale["Client"])
        client_obj = Client.objects.get(pk=int(client_id))
        sale_total = decimal.Decimal(data_sale["SaleTotal"])
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_sales_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='V')
        _type = str(data_sale["Type"])
        _bill_type = str(data_sale["BillType"])
        correlative_sale = int(data_sale['correlative_sale'])

        order_sale_quotation = int(data_sale["order_sale_quotation"])
        order_sale_quotation_obj = Order.objects.get(id=order_sale_quotation)

        validity_date = (data_sale["validity_date"])
        date_completion = (data_sale["date_completion"])
        place_delivery = (data_sale["place_delivery"])
        type_quotation = (data_sale["type_quotation"])
        type_name_quotation = (data_sale["name_type_quotation"])
        observation = (data_sale["observation"])

        order_sale_quotation_obj.type = 'T'
        order_sale_quotation_obj.status = 'P'
        order_sale_quotation_obj.total = sale_total
        order_sale_quotation_obj.correlative_sale = correlative_sale
        order_sale_quotation_obj.client = client_obj
        order_sale_quotation_obj.subsidiary_store_sales_obj = subsidiary_store_sales_obj
        order_sale_quotation_obj.user = user_obj
        order_sale_quotation_obj.subsidiary = subsidiary_obj
        order_sale_quotation_obj.date_completion = date_completion
        order_sale_quotation_obj.place_delivery = place_delivery
        order_sale_quotation_obj.type_quotation = type_quotation
        order_sale_quotation_obj.validity_date = validity_date
        order_sale_quotation_obj.observation = observation
        order_sale_quotation_obj.type_name_quotation = type_name_quotation
        order_sale_quotation_obj.way_to_pay_type = type_payment
        order_sale_quotation_obj.has_quotation_order = 'S'
        order_sale_quotation_obj.distribution_mobil = None
        order_sale_quotation_obj.truck = None
        order_sale_quotation_obj.create_at = _date

        for detail in data_sale['Details']:

            quantity = decimal.Decimal(detail['Quantity'])
            price = decimal.Decimal(detail['Price'])
            unit_id = int(detail['Unit'])
            product_id = int(detail['Product'])
            commentary = str(detail['_commentary'])
            product_obj = Product.objects.get(id=product_id)
            unit_obj = Unit.objects.get(id=unit_id)

            if detail['Detail'] != '0':

                detail_id = int(detail['Detail'])
                order_detail_obj = OrderDetail.objects.get(id=detail_id)
                order_detail_obj.quantity_sold = quantity
                order_detail_obj.price_unit = price
                order_detail_obj.commentary = commentary
                order_detail_obj.status = 'V'
                order_detail_obj.order = order_sale_quotation_obj
                order_detail_obj.product = product_obj
                order_detail_obj.unit = unit_obj
                order_detail_obj.save()
            else:
                order_detail_obj = OrderDetail(
                    quantity_sold=quantity,
                    price_unit=price,
                    commentary=commentary,
                    status='V',
                    product=product_obj,
                    unit=unit_obj,
                    order=order_sale_quotation_obj,
                )
                order_detail_obj.save()

        order_sale_quotation_obj.save()
        id_sales = order_sale_quotation_obj.id

        return JsonResponse({
            'id_sales': id_sales,
            'message': 'COTIZACIÓN ACTUALIZADA CORRECTAMENTE.',

        }, status=HTTPStatus.OK)


def inventory_store(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    subsidiary_store_obj = None
    product_brand_set = ProductBrand.objects.all()
    subsidiary_store_set = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V')
    if subsidiary_store_set.exists():
        subsidiary_store_obj = subsidiary_store_set.first()

    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        format_date_hour = my_date.strftime("%d/%m/%Y %H:%M:%S")

        return render(request, 'sales/inventory_store.html', {
            'formatdate': formatdate,
            'format_date_hour': format_date_hour,
            'product_brand_set': product_brand_set,
            'subsidiary': subsidiary_obj,
        })

    elif request.method == 'POST':
        product_brand_id = int(request.POST.get('product-brand'))
        date = str(request.POST.get('date'))

        inventory_set = Inventory.objects.filter(product_brand_id=product_brand_id,
                                                 subsidiary=subsidiary_obj, end_date__isnull=True)

        if inventory_set.exists():
            inventory_obj = inventory_set.last()
            register_date = inventory_obj.start_date
            format_register_date = register_date.strftime("%d/%m/%Y %H:%M:%S")

            return JsonResponse({
                'start_date': format_register_date,
                'inventory_id': inventory_obj.id,
                'brand_id': inventory_obj.product_brand.id,
                'brand_name': inventory_obj.product_brand.name,
                'message': 'LA MARCA ' + inventory_obj.product_brand.name + ' YA CUENTA CON UN INVENTARIO ABIERTO',
            }, status=HTTPStatus.OK)

        else:
            last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]

            product_set = Product.objects.filter(product_brand__id=product_brand_id).select_related(
                'product_family', 'product_brand').prefetch_related(
                Prefetch(
                    'productstore_set',
                    queryset=ProductStore.objects.filter(subsidiary_store__subsidiary=subsidiary_obj,
                                                         subsidiary_store__category='V').select_related(
                        'subsidiary_store__subsidiary')
                        .annotate(
                        last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

            tpl = loader.get_template('sales/inventory_store_grid.html')
            context = ({
                'product_set': product_set,
                'subsidiary': subsidiary_obj,
                'subsidiary_store_obj': subsidiary_store_obj,
            })
            return JsonResponse({
                'grid': tpl.render(context, request),
            }, status=HTTPStatus.OK)


def product_set_inventory(product_brand_id=None, subsidiary_obj=None):
    last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]

    product_set = Product.objects.filter(product_brand__id=product_brand_id).select_related(
        'product_family', 'product_brand').prefetch_related(
        Prefetch(
            'productstore_set', queryset=ProductStore.objects.filter(subsidiary_store__subsidiary=subsidiary_obj,
                                                                     subsidiary_store__category='V').select_related(
                'subsidiary_store__subsidiary')
                .annotate(
                last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
            )
        ),
        Prefetch(
            'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
        ),
    ).order_by('id')

    return product_set


def save_register_inventory(request):
    data = dict()
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    inventory_obj = None
    if request.method == 'GET':
        start_date = datetime.strptime((request.GET.get('start_date')), '%d/%m/%Y %H:%M:%S')
        start_date_convert = start_date.strftime("%Y/%m/%d %H:%M:%S")
        brand_id = int(request.GET.get('brand_id', ''))
        product_brand_obj = ProductBrand.objects.get(id=brand_id)
        product_set = Product.objects.filter(product_brand=product_brand_obj)
        product_store_set = ProductStore.objects.filter(product__product_brand=product_brand_obj,
                                                        subsidiary_store__subsidiary=subsidiary_obj,
                                                        subsidiary_store__category='V')
        subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')

        try:
            inventory_obj = Inventory(
                start_date=start_date,
                product_brand=product_brand_obj,
                subsidiary=subsidiary_obj,
                subsidiary_store=subsidiary_store_obj,
                user=user_obj
            )
            inventory_obj.save()

            for ps in product_store_set:
                ps.status_inventory = '3'
                ps.save()

        except DatabaseError as e:
            data['error'] = str(e)
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        tpl = loader.get_template('sales/inventory_store_grid.html')

        context = ({
            'product_set': product_set_inventory(product_brand_id=brand_id, subsidiary_obj=subsidiary_obj),
            'subsidiary': subsidiary_obj,
            'subsidiary_store_obj': subsidiary_store_obj,
        })

        return JsonResponse({
            'inventory_id': inventory_obj.id,
            'message': 'Cuadre de Inventario Iniciado Correctamente',
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def save_new_inventory_product(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    if request.method == 'GET':
        new_quantity = 0
        new_price_unit = 0
        new_price_total = 0
        new_remaining_quantity = 0
        new_remaining_price = 0
        new_remaining_price_total = 0
        new_stock = decimal.Decimal(request.GET.get('new_stock'))
        product_id = int(request.GET.get('product_id'))
        inventory_id = int(request.GET.get('inventory_id'))
        product_store_obj = None
        subsidiary_store = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')

        inventory_obj = Inventory.objects.get(id=inventory_id)

        product_store_set = ProductStore.objects.filter(product_id=product_id,
                                                        subsidiary_store__subsidiary=subsidiary_obj,
                                                        subsidiary_store__category='V')
        if product_store_set.exists():
            product_store_obj = product_store_set.last()

        else:
            product_obj = Product.objects.get(id=product_id)
            product_detail_obj = ProductDetail.objects.filter(product__id=product_id).last()
            new_remaining_price = product_detail_obj.price_purchase
            new_product_store_obj = ProductStore(
                product=product_obj,
                subsidiary_store=subsidiary_store,
                stock=new_stock
            )
            new_product_store_obj.save()
            kardex_initial_ci(new_product_store_obj, new_stock, new_remaining_price, inventory=inventory_obj)

            return JsonResponse({
                'message': 'Stock nuevo del producto registrado correctamente',
            }, status=HTTPStatus.OK)

        kardex_set = Kardex.objects.filter(operation='CI', product_store_id=product_store_obj.id,
                                           inventory=inventory_obj)

        if kardex_set.exists():
            if product_store_obj.status_inventory == '1':
                product_store_obj.status_inventory = '2'
                product_store_obj.save()

            data = {
                'error': 'ya inventariado',
                'status': 2

            }
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        old_stock = product_store_obj.stock

        if new_stock < old_stock:
            real_stock = old_stock - new_stock
            new_stock = old_stock - real_stock

            new_quantity = decimal.Decimal(real_stock)
            new_price_unit = decimal.Decimal(0.00)
            new_price_total = new_quantity * new_price_unit

            last_kardex = Kardex.objects.filter(product_store=product_store_obj).last()
            last_remaining_quantity = last_kardex.remaining_quantity
            old_price_unit = last_kardex.remaining_price
            last_remaining_price_total = last_kardex.remaining_price_total
            new_price_total = old_price_unit * new_quantity

            new_remaining_quantity = last_remaining_quantity - new_quantity
            new_remaining_price = old_price_unit
            new_remaining_price_total = new_remaining_quantity * new_remaining_price

            new_kardex = {
                'operation': 'CI',
                'quantity': new_quantity,
                'price_unit': new_price_unit,
                'price_total': new_price_total,
                'remaining_quantity': new_remaining_quantity,
                'remaining_price': new_remaining_price,
                'remaining_price_total': new_remaining_price_total,
                'product_store': product_store_obj,
                'inventory': inventory_obj,
                'purchase_detail': None,
                'requirement_detail': None,
                'programming_invoice': None,
                'manufacture_detail': None,
                'guide_detail': None,
                'distribution_detail': None,
                'order_detail': None,
                'loan_payment': None,
                'ball_change': None,
                'advance_detail': None,
            }
            kardex = Kardex.objects.create(**new_kardex)
            kardex.save()

            product_store_obj.stock = new_stock
            product_store_obj.status_inventory = '2'
            product_store_obj.save()

        elif new_stock > old_stock:

            real_stock = new_stock - old_stock
            new_stock = old_stock + real_stock
            new_quantity = decimal.Decimal(real_stock)
            new_price_unit = decimal.Decimal(0.00)

            new_price_total = new_quantity * new_price_unit

            last_kardex = Kardex.objects.filter(product_store=product_store_obj).last()
            last_remaining_quantity = last_kardex.remaining_quantity
            last_remaining_price_total = last_kardex.remaining_price_total

            new_remaining_quantity = last_remaining_quantity + new_quantity
            new_remaining_price = (decimal.Decimal(last_remaining_price_total) +
                                   new_price_total) / new_remaining_quantity
            new_remaining_price_total = new_remaining_quantity * new_remaining_price

            new_kardex = {
                'operation': 'CI',
                'quantity': new_quantity,
                'price_unit': new_price_unit,
                'price_total': new_price_total,
                'remaining_quantity': new_remaining_quantity,
                'remaining_price': new_remaining_price,
                'remaining_price_total': new_remaining_price_total,
                'product_store': product_store_obj,
                'inventory': inventory_obj,
                'purchase_detail': None,
                'requirement_detail': None,
                'programming_invoice': None,
                'manufacture_detail': None,
                'guide_detail': None,
                'distribution_detail': None,
                'order_detail': None,
                'loan_payment': None,
                'ball_change': None,
                'advance_detail': None,
            }
            kardex = Kardex.objects.create(**new_kardex)
            kardex.save()

            product_store_obj.stock = new_stock
            product_store_obj.status_inventory = '2'
            product_store_obj.save()

        elif new_stock == old_stock:

            real_stock = new_stock
            new_quantity = decimal.Decimal(real_stock)
            new_price_unit = decimal.Decimal(0.00)
            new_price_total = new_quantity * new_price_unit

            last_kardex = Kardex.objects.filter(product_store=product_store_obj).last()
            last_remaining_quantity = last_kardex.remaining_quantity
            last_remaining_price_total = last_kardex.remaining_price_total

            new_remaining_quantity = last_remaining_quantity
            new_remaining_price = last_kardex.remaining_price_total

            new_kardex = {
                'operation': 'CI',
                'quantity': new_quantity,
                'price_unit': new_price_unit,
                'price_total': new_price_total,
                'remaining_quantity': new_remaining_quantity,
                'remaining_price': new_remaining_price,
                'remaining_price_total': new_remaining_price_total,
                'product_store': product_store_obj,
                'inventory': inventory_obj,
                'purchase_detail': None,
                'requirement_detail': None,
                'programming_invoice': None,
                'manufacture_detail': None,
                'guide_detail': None,
                'distribution_detail': None,
                'order_detail': None,
                'loan_payment': None,
                'ball_change': None,
                'advance_detail': None,
            }
            kardex = Kardex.objects.create(**new_kardex)
            kardex.save()

            product_store_obj.stock = new_stock
            product_store_obj.status_inventory = '2'
            product_store_obj.save()

        return JsonResponse({
            'message': 'Stock nuevo del producto registrado correctamente',
        }, status=HTTPStatus.OK)


def get_products_by_inventory(request):
    if request.method == 'GET':
        brand_id = int(request.GET.get('brand_id_exists', ''))
        inventory_id = int(request.GET.get('inventory_id', ''))
        start_date = str(request.GET.get('start_date', ''))

        subsidiary_store_obj = None
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_set = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V')
        if subsidiary_store_set.exists():
            subsidiary_store_obj = subsidiary_store_set.first()

        product_brand_obj = ProductBrand.objects.get(id=brand_id)

        last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]

        has_serials = Exists(
            ProductSerial.objects.filter(
                product_store__product=OuterRef('id')
            )
        )

        product_set = Product.objects.filter(product_brand__id=brand_id).select_related(
            'product_family', 'product_brand').annotate(
            has_serials=has_serials
        ).prefetch_related(
            Prefetch(
                'productstore_set', queryset=ProductStore.objects.filter(subsidiary_store__subsidiary=subsidiary_obj,
                                                                         subsidiary_store__category='V').select_related(
                    'subsidiary_store__subsidiary')
                    .annotate(
                    last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                )
            ),
            Prefetch(
                'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
            ),
        ).order_by('id')

        tpl = loader.get_template('sales/inventory_store_grid.html')
        context = ({
            'inventory_id': inventory_id,
            'product_set': product_set,
            'subsidiary': subsidiary_obj,
            'subsidiary_store_obj': subsidiary_store_obj,
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def close_inventory(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = datetime.strptime(str(my_date.strftime("%Y-%m-%d %H:%M:%S")), '%Y-%m-%d %H:%M:%S')
        inventory_id = int(request.GET.get('inventory_id', ''))
        inventory_obj = Inventory.objects.get(id=inventory_id)
        inventory_obj.end_date = formatdate
        inventory_obj.save()

        return JsonResponse({
            'message': 'Inventario cerrado correctamente',
        }, status=HTTPStatus.OK)


def utc_to_local(utc_dt):
    local_tz = pytz.timezone('America/Bogota')
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


def get_last_inventory(request):
    if request.method == 'GET':
        inventory_obj = None
        format_date_hour = ''
        brand_id = int(request.GET.get('brand_id', ''))
        inventory_set = Inventory.objects.filter(product_brand_id=brand_id, end_date__isnull=False).order_by('id')

        if inventory_set.exists():
            inventory_obj = inventory_set.last()
            last_date = utc_to_local(inventory_obj.end_date)
            format_date_hour = last_date.strftime("%d/%m/%Y %H:%M:%S")

        return JsonResponse({
            'inventory_end_date': format_date_hour,
        }, status=HTTPStatus.OK)


def get_clients_by_criteria(request):
    if request.method == 'GET':
        client_list = []
        value = request.GET.get('value', '').strip()
        client_type_set = ClientType.objects.filter(
            client__names__icontains=value.upper()).select_related('client',
                                                                   'document_type')
        client_dict = {}
        address = ''
        for ct in client_type_set:

            document_type_obj = DocumentType.objects.get(id=ct.document_type_id)

            if ct.client.clientaddress_set.last() is not None:
                address = ct.client.clientaddress_set.last().address

            client_dict = {
                'client_id': ct.client.id,
                'client_names': ct.client.names,
                'client_document_number': ct.document_number,
                'client_address': address,
                'client_type_document': ct.document_type_id,
                'client_type': document_type_obj.short_description,
            }
            client_list.append(client_dict)

        return JsonResponse({
            'client_list': client_list,
            'client_count': len(client_dict),
        }, status=HTTPStatus.OK)


def quotation_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    worker_obj = Worker.objects.filter(user=user_obj).last()
    employee = Employee.objects.get(worker=worker_obj)
    document_types = DocumentType.objects.all()
    mydate = datetime.now()
    formatdate = mydate.strftime("%Y-%m-%d")
    series_set = Subsidiary.objects.filter(id=subsidiary_obj.id)
    cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
    cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')
    sales_store = SubsidiaryStore.objects.filter(
        subsidiary=subsidiary_obj, category='V').first()
    users_set = User.objects.filter(is_superuser=False, is_staff=True)

    return render(request, 'sales/quotation_list.html', {
        'choices_account': cash_set,
        'choices_account_bank': cash_deposit_set,
        'employee': employee,
        'sales_store': sales_store,
        'subsidiary': subsidiary_obj,
        'document_types': document_types,
        'date': formatdate,
        'choices_payments': TransactionPayment._meta.get_field('type').choices,
        'series': series_set,
        'users': users_set
    })


def get_product_quotation(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        sales_store = SubsidiaryStore.objects.filter(
            subsidiary=subsidiary_obj, category='V').first()
        last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]
        product_set = None

        value = request.GET.get('value', '')
        barcode = request.GET.get('barcode', '')

        if value != '' and barcode == '':
            array_value = value.split()
            product_query = Product.objects
            full_query = None

            product_brand_set = ProductBrand.objects.filter(name__icontains=value.upper())

            for i in range(0, len(array_value)):
                q = Q(name__icontains=array_value[i]) | Q(product_brand__name__icontains=array_value[i])
                if full_query is None:
                    full_query = q
                else:
                    full_query = full_query & q

            product_set = product_query.filter(full_query).select_related(
                'product_family', 'product_brand').prefetch_related(
                Prefetch(
                    'productstore_set', queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                        .annotate(
                        last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

        if value == '' and barcode != '':
            product_set = Product.objects.filter(barcode=barcode).select_related(
                'product_family', 'product_brand').prefetch_related(
                Prefetch(
                    'productstore_set', queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                        .annotate(
                        last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

        t = loader.get_template('sales/quotation_product_grid.html')
        c = ({
            'subsidiary': subsidiary_obj,
            'product_dic': product_set
        })
        return JsonResponse({
            'grid': t.render(c, request),
        })


def save_quotation(request):
    if request.method == 'GET':
        quotation_request = request.GET.get('quotations', '')
        data_quotation = json.loads(quotation_request)
        type_payment = (data_quotation["type_payment"])
        has_quotation_order = ''

        _date = str(data_quotation["Date"])
        client_address = str(data_quotation["Address"])
        client_id = str(data_quotation["Client"])
        client_obj = Client.objects.get(pk=int(client_id))
        client_address_set = ClientAddress.objects.filter(client=client_obj)
        if client_address_set.exists():
            client_address_obj = client_address_set.last()
            client_address_obj.address = client_address
            client_address_obj.save()
        else:
            client_address_obj = ClientAddress(
                client=client_obj,
                address=client_address
            )
            client_address_obj.save()

        sale_total = decimal.Decimal(data_quotation["SaleTotal"])
        # user_id = request.user.id
        # user_obj = User.objects.get(id=user_id)
        user_id = request.user.id
        user_subsidiary_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_subsidiary_obj)

        user = int(data_quotation["userID"])
        user_obj = User.objects.get(id=user)

        subsidiary_store_sales_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='V')
        _bill_type = str(data_quotation["BillType"])

        validity_date = (data_quotation["validity_date"])
        date_completion = (data_quotation["date_completion"])
        place_delivery = (data_quotation["place_delivery"])
        type_quotation = (data_quotation["type_quotation"])
        type_name_quotation = (data_quotation["name_type_quotation"])
        observation = (data_quotation["observation"])

        order_sale_quotation = None
        order_sale_quotation_obj = None

        order_obj = Order(
            type='T',
            client=client_obj,
            user=user_obj,
            total=sale_total,
            distribution_mobil=None,
            truck=None,
            subsidiary_store=subsidiary_store_sales_obj,
            create_at=_date,
            correlative_sale=get_correlative_order(subsidiary_obj, 'T'),
            subsidiary=subsidiary_obj,
            validity_date=validity_date,
            date_completion=date_completion,
            place_delivery=place_delivery,
            type_quotation=type_quotation,
            type_name_quotation=type_name_quotation,
            observation=observation,
            way_to_pay_type=type_payment,
            has_quotation_order='S',
            order_sale_quotation=order_sale_quotation,
            voucher_type='CO'
        )
        order_obj.save()

        for detail in data_quotation['Details']:
            quantity = decimal.Decimal(detail['Quantity'])
            price = decimal.Decimal(detail['Price'])
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)
            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)
            commentary = str(detail['_commentary'])

            order_detail_obj = OrderDetail(
                order=order_obj,
                product=product_obj,
                quantity_sold=quantity,
                price_unit=price,
                unit=unit_obj,
                commentary=commentary,
                status='V',
            )
            order_detail_obj.save()

        return JsonResponse({
            'id_sales': order_obj.id,
            'message': 'Cotización generada',
        }, status=HTTPStatus.OK)


def check_stock(request):
    if request.method == 'GET':
        flag = True
        quantity = decimal.Decimal(request.GET.get('quantity', ''))
        product_id = int(request.GET.get('product', ''))

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        product_store_obj = ProductStore.objects.get(product__id=product_id,
                                                     subsidiary_store__subsidiary=subsidiary_obj)
        stock = product_store_obj.stock
        if decimal.Decimal(quantity) > stock:
            flag = False
        return JsonResponse({
            # 'message': 'ff',
            'flag': flag
        }, status=HTTPStatus.OK)


def refresh_stock(request):
    if request.method == 'GET':
        product_store_id = int(request.GET.get('product_store_id', ''))
        product_store_obj = ProductStore.objects.get(id=product_store_id)
        stock = product_store_obj.stock

        return JsonResponse({
            'stock': stock
        }, status=HTTPStatus.OK)


def get_last_id_type_others(request):
    if request.method == 'GET':
        client_type_set = ClientType.objects.filter(document_type__id='00')
        if client_type_set:
            n_order = int(client_type_set.last().document_number)
            new_n_order = n_order + 1
        else:
            new_n_order = 1

        return JsonResponse({
            'new_n_order': new_n_order
        }, status=HTTPStatus.OK)


def kardex_initial_ci(
        product_store_obj,
        stock,
        price_unit,
        inventory,
        purchase_detail_obj=None,
        requirement_detail_obj=None,
        programming_invoice_obj=None,
        manufacture_detail_obj=None,
        guide_detail_obj=None,
        distribution_detail_obj=None,
        order_detail_obj=None,
        loan_payment_obj=None,
        ball_change_obj=None,
        advance_detail_obj=None,
):
    new_kardex = {
        'operation': 'CI',
        'quantity': 0,
        'price_unit': 0,
        'price_total': 0,
        'remaining_quantity': decimal.Decimal(stock),
        'remaining_price': decimal.Decimal(price_unit),
        'remaining_price_total': decimal.Decimal(stock) * decimal.Decimal(price_unit),
        'product_store': product_store_obj,
        'purchase_detail': purchase_detail_obj,
        'requirement_detail': requirement_detail_obj,
        'programming_invoice': programming_invoice_obj,
        'manufacture_detail': manufacture_detail_obj,
        'guide_detail': guide_detail_obj,
        'distribution_detail': distribution_detail_obj,
        'order_detail': order_detail_obj,
        'loan_payment': loan_payment_obj,
        'ball_change': ball_change_obj,
        'advance_detail': advance_detail_obj,
        'inventory': inventory
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()

    product_store_obj.status_inventory = '2'
    product_store_obj.save()


def get_report_summary_sales(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/report_summary_sales.html', {'formatdate': formatdate, })
    elif request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        if subsidiary_obj is not None:
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
            orders = Order.objects.filter(subsidiary_store=subsidiary_store_obj)
            start_date = str(request.POST.get('start-date'))
            end_date = str(request.POST.get('end-date'))

            orders = orders.filter(create_at__date__range=[start_date, end_date], type='V',
                                   status__in=['P', 'A']).order_by('id')
            if orders:
                return JsonResponse({
                    'grid': get_dict_order_summaries(orders, start_date, end_date),
                }, status=HTTPStatus.OK)
            else:
                data = {'error': "No hay operaciones registradas"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
        else:
            data = {'error': "No hay sucursal"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response


def get_dict_order_summaries(order_set, start_date, end_date):
    sum = 0
    total_cash = decimal.Decimal(0)
    total_credit = decimal.Decimal(0)
    total_deposit = decimal.Decimal(0)
    user_dict = {}
    sum_bills = 0
    sum_receipts = 0
    sum_tickets = 0

    for o in order_set:

        order_bill_set = OrderBill.objects.filter(order=o.id)

        if o.status != 'A':
            sum = sum + o.sum_total_details()

            if o.way_to_pay_type == 'E':
                total_cash = total_cash + o.sum_total_details()
            elif o.way_to_pay_type == 'D':
                total_deposit = total_deposit + o.sum_total_details()
            elif o.way_to_pay_type == 'C':
                total_credit = total_credit + o.sum_total_details()

            if order_bill_set.exists():
                order_bill_obj = order_bill_set.first()
                if order_bill_obj.type == '1':
                    sum_bills = sum_bills + o.sum_total_details()
                elif order_bill_obj.type == '2':
                    sum_receipts = sum_receipts + o.sum_total_details()
            else:
                sum_tickets += o.sum_total_details()

            key = o.user.id
            total_bills = 0
            total_receipts = 0
            total_tickets = 0

            if key in user_dict:

                user = user_dict[key]
                old_total = user.get('total_sold')
                old_total_bills = user.get('total_bills')
                old_total_receipts = user.get('total_receipts')
                old_total_tickets = user.get('total_tickets')

                order_bill_set = OrderBill.objects.filter(order=o.id)

                if order_bill_set.exists():
                    order_bill_obj = order_bill_set.first()
                    if order_bill_obj.type == '1':
                        total_bills = o.sum_total_details()
                    elif order_bill_obj.type == '2':
                        total_receipts = o.sum_total_details()
                else:
                    total_tickets = o.sum_total_details()

                user_dict[key]['total_bills'] = old_total_bills + total_bills
                user_dict[key]['total_receipts'] = old_total_receipts + total_receipts
                user_dict[key]['total_tickets'] = old_total_tickets + total_tickets
                user_dict[key]['total_sold'] = old_total + o.sum_total_details()

            else:

                if order_bill_set.exists():
                    order_bill_obj = order_bill_set.first()
                    if order_bill_obj.type == '1':
                        total_bills = o.sum_total_details()
                    elif order_bill_obj.type == '2':
                        total_receipts = o.sum_total_details()
                else:
                    total_tickets = o.sum_total_details()

                user_dict[key] = {
                    'user_id': o.user.id,
                    'user_names': o.user.worker_set.last().employee.names,
                    'total_sold': round(decimal.Decimal(o.sum_total_details()), 2),
                    'total_bills': round(decimal.Decimal(total_bills), 2),
                    'total_receipts': round(decimal.Decimal(total_receipts), 2),
                    'total_tickets': round(decimal.Decimal(total_tickets), 2),
                }

    tpl = loader.get_template('sales/report_summary_sales_grid.html')
    context = ({
        'sum': sum,
        'total_cash': decimal.Decimal(total_cash).quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN),
        'total_deposit': decimal.Decimal(total_deposit).quantize(decimal.Decimal('0.00'),
                                                                 rounding=decimal.ROUND_HALF_EVEN),
        'total_credit': decimal.Decimal(total_credit).quantize(decimal.Decimal('0.00'),
                                                               rounding=decimal.ROUND_HALF_EVEN),
        'user_dict': user_dict,
        'sum_bills': round(decimal.Decimal(sum_bills), 2),
        'sum_receipts': round(decimal.Decimal(sum_receipts), 2),
        'sum_tickets': round(decimal.Decimal(sum_tickets), 2),
    })
    return tpl.render(context)


def get_all_products(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        # product_set = None
        last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]

        last_purchase_date = PurchaseDetail.objects.filter(
            product=OuterRef('id'),
            purchase__status='A'
        ).order_by('-purchase__purchase_date').values('purchase__purchase_date')[:1]

        last_purchase_quantity = PurchaseDetail.objects.filter(
            product=OuterRef('id'),
            purchase__status='A'
        ).order_by('-purchase__purchase_date').values('quantity')[:1]

        # Subquery para verificar si el producto tiene series
        has_serials = Exists(
            ProductSerial.objects.filter(
                product_store__product=OuterRef('id')
            )
        )

        product_set = Product.objects.filter(is_enabled=True).select_related(
            'product_family', 'product_brand'
        ).annotate(
            last_purchase_date=Subquery(last_purchase_date),
            last_purchase_quantity=Subquery(last_purchase_quantity),
            has_serials=has_serials  # Ahora sí funciona con Exists
        ).prefetch_related(
            Prefetch(
                'productstore_set',
                queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                    .exclude(subsidiary_store__subsidiary=3)
                    .annotate(
                    last_remaining_quantity=Subquery(
                        Kardex.objects.filter(product_store=OuterRef('id'))
                            .order_by('-id')
                            .values('remaining_quantity')[:1]
                    )
                )
            ),
            Prefetch(
                'productdetail_set',
                queryset=ProductDetail.objects.select_related('unit')
            ),
        ).order_by('id')

        t = loader.get_template('sales/product_grid_list.html')
        c = ({
            'products': product_set,
            'total_price_purchase': get_total_price_purchase(product_set)
            # 'subsidiary': subsidiary_obj
        })

        return JsonResponse({
            'message': 'Actualizado correctamente',
            'success': True,
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def calculate_square_quantity(request):
    if request.method == 'GET':
        ps_id = request.GET.get('ps', '')
        new_price_purchase = request.GET.get('new_price_purchase', '').replace(',', '.')

        kardex_set = Kardex.objects.filter(product_store__id=ps_id).order_by('create_at')
        kardex_initial = Kardex.objects.filter(product_store__id=ps_id, operation='C').first()
        var_remaining_quantity = kardex_initial.remaining_quantity
        var_remaining_price = decimal.Decimal(new_price_purchase.replace(',', '.'))
        var_remaining_price_total = kardex_initial.remaining_price_total

        for k in kardex_set:
            if k.operation == 'E':
                var_remaining_quantity += k.quantity
                if var_remaining_quantity == 0:
                    var_remaining_price = 0
                else:
                    var_remaining_price = (var_remaining_price_total + k.price_total) / var_remaining_quantity
                var_remaining_price_total = var_remaining_quantity * var_remaining_price

                k.remaining_quantity = var_remaining_quantity
                k.remaining_price = var_remaining_price
                k.remaining_price_total = var_remaining_price_total
                k.save()
            elif k.operation == 'S':
                var_remaining_quantity -= k.quantity
                var_remaining_price_total = var_remaining_quantity * var_remaining_price
                k.remaining_quantity = var_remaining_quantity
                k.remaining_price = var_remaining_price
                k.remaining_price_total = var_remaining_price_total
                k.save()

            kardex_initial.remaining_price = decimal.Decimal(new_price_purchase)
            kardex_initial.remaining_price_total = decimal.Decimal(new_price_purchase) * decimal.Decimal(kardex_initial.remaining_quantity)
            kardex_initial.save()

        last_inventory = Kardex.objects.filter(id__lt=OuterRef("pk"), product_store__id=ps_id).order_by(
            "-id")

        inventories = Kardex.objects.filter(product_store__id=ps_id).annotate(
            last_remaining_quantity=Subquery(last_inventory.values('remaining_quantity')[:1])
        ).order_by('id')

        t = loader.get_template('sales/kardex_grid_list.html')
        c = ({'inventories': inventories})
        return JsonResponse({
            'success': True,
            'message': 'Actualizado correctamente',
            'form': t.render(c),
        })


def modal_serial(request):
    if request.method == 'GET':
        ps_id = request.GET.get('ps', '')
        product_store_obj = ProductStore.objects.get(id=int(ps_id))
        product_serial_set = ProductSerial.objects.filter(product_store__id=int(ps_id), status='C')
        if product_serial_set.exists():
            product_obj = product_store_obj.product
            tpl = loader.get_template('sales/modal_serial.html')
            context = ({
                'product_serial': product_serial_set,
                'product_obj': product_obj,
                'product_store_obj': product_store_obj
            })
            return JsonResponse({
                'success': True,
                'form': tpl.render(context, request),
            }, status=HTTPStatus.OK)

        else:
            return JsonResponse({
                'success': False,
                'message': 'El Producto no cuenta con Stock en Series. Revisar el Producto'
            }, status=HTTPStatus.OK)


def get_product_photo(request):
    if request.method == 'GET':
        pk = request.GET.get('pk')
        try:
            product = Product.objects.get(pk=pk)
            image_url = product.photo.url if product.photo else '/mediafiles/product/empty_image.jpg'
            product_name = product.name
            return JsonResponse({'image_url': image_url, 'product_name': product_name})
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)


def search_sell_by_serial(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/search_sell_serial.html', {'formatdate': formatdate, })
    elif request.method == 'POST':
        serial = str(request.POST.get('serial'))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        product_serial_set = ProductSerial.objects.filter(serial_number=serial)
        if product_serial_set.exists():
            product_serial_obj = product_serial_set.last()
            order_detail_obj = product_serial_obj.order_detail
            purchase_detail_obj = product_serial_obj.purchase_detail
            tpl = loader.get_template('sales/search_sell_serial_grid.html')
            context = ({
                'order_detail_obj': order_detail_obj,
                'purchase_detail_obj': purchase_detail_obj
            })
            return JsonResponse({
                'grid': tpl.render(context, request),
            }, status=HTTPStatus.OK)
        else:
            data = {'error': "EL PRODUCTO NO TIENE SERIES"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response


def report_sales_by_brand(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        brand_set = ProductBrand.objects.all().order_by('name')
        return render(request, 'sales/report_sales_by_brand.html', {
            'formatdate': formatdate, 'brand_set': brand_set})
    elif request.method == 'POST':
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        brand_id = int(request.POST.get('brand'))
        brand_obj = ProductBrand.objects.get(id=brand_id)
        order_set = Order.objects.filter(type='V',
                                         create_at__date__range=[start_date, end_date]).select_related('client', 'user',
                                                                                                       'orderbill').prefetch_related(
            Prefetch(
                'orderdetail_set', queryset=OrderDetail.objects.select_related('product', 'unit',
                                                                               'product__product_brand')
            )
        ).order_by('create_at')

        # produc_set = OrderDetail.objects.filter(product__productstore__productserial__isnull=False)

        order_dict = []
        sum_quantity = 0
        if order_set.exists():
            for o in order_set:
                _order_detail = o.orderdetail_set.filter(product__product_brand__id=brand_id)
                if _order_detail:
                    flag_serial = False
                    serial_number = str(o.subsidiary.serial) + '-' + str(o.correlative_sale)
                    order_bill_obj = False
                    if hasattr(o, 'orderbill'):
                        order_bill_obj = True
                        serial_number = str(o.orderbill.serial) + '-' + str(o.orderbill.n_receipt)

                    order = {
                        'id': o.id,
                        'client': o.client,
                        'user': o.user,
                        'serial_number': serial_number,
                        'total': 0,
                        'create_at': o.create_at,
                        'order_detail_set': [],
                        'order_bill': order_bill_obj,
                        'type': o.get_type_display(),
                        'status': o.status,
                        'way_to_pay': o.way_to_pay_type,
                        'details': _order_detail.count(),
                    }

                    for d in _order_detail:
                        if d.product.productstore_set.last().productserial_set.all():
                            flag_serial = True
                        order_detail = {
                            'id': d.id,
                            'product': d.product.name,
                            'unit': d.unit.name,
                            'quantity_sold': d.quantity_sold,
                            'price_unit': d.price_unit,
                            'multiply': d.multiply,
                            'comentary': d.commentary.upper(),
                            'flag_serial': flag_serial
                        }
                        if o.status != 'A':
                            sum_quantity += d.quantity_sold
                        order.get('order_detail_set').append(order_detail)
                    order['total'] = decimal.Decimal(o.sum_total_details()).quantize(decimal.Decimal('0.0'),
                                                                                     rounding=decimal.ROUND_HALF_EVEN)
                    order_dict.append(order)
            # print(order_dict)
            tpl = loader.get_template('sales/report_sales_by_brand_grid.html')

            context = ({
                'order_dict': order_dict,
                'brand_obj': brand_obj,
                'sum_quantity': str(round(sum_quantity, 0)),
            })
            return JsonResponse({
                'grid': tpl.render(context, request),
            }, status=HTTPStatus.OK)
        else:
            data = {'error': "LA MARCA NO CUENTA CON VENTAS EN EL RANGO SELECCIONADO"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response


def recalculate(request):
    if request.method == 'GET':
        kardex_set = Kardex.objects.filter(product_store__id=400)
        for k in kardex_set:
            if k.operation == 'E':
                if k.purchase_detail:
                    k.price_unit = k.purchase_detail.price_unit
                    k.price_total = decimal.Decimal(k.quantity) * decimal.Decimal(k.purchase_detail.price_unit)
                    k.save()
                else:
                    k.price_unit = k.order_detail.price_unit
                    k.price_total = decimal.Decimal(k.quantity) * decimal.Decimal(k.order_detail.price_unit)
                    k.save()
            elif k.operation == 'S':
                k.price_unit = k.order_detail.price_unit
                k.price_total = decimal.Decimal(k.quantity) * decimal.Decimal(k.order_detail.price_unit)
                k.save()
        return JsonResponse({
            'success': True,
        }, status=HTTPStatus.OK)


def get_client_search(request):
    if request.method == 'GET':
        search = request.GET.get('search')
        client = []
        if search:
            client_set = Client.objects.filter(names__icontains=search)
            for c in client_set:
                client_address_set = c.clientaddress_set.all()
                if client_address_set.exists():
                    address_dict = [{
                        'id': cd.id,
                        'address': cd.address,
                        'district': cd.district.description if cd.district else '-',
                        'reference': cd.reference
                    } for cd in client_address_set]
                else:
                    address_dict = []

                client.append({
                    'id': c.id,
                    'names': c.names,
                    'number_document': c.clienttype_set.last().document_number,
                    'typeDocument': c.clienttype_set.last().document_type.short_description,
                    'address': address_dict,
                    'last_address': c.clientaddress_set.last().address if c.clientaddress_set.last() else '-'
                })

        return JsonResponse({
            'status': True,
            'client': client
        })


def get_correlative_by_type(request):
    if request.method != 'GET':
        return JsonResponse({'status': False, 'message': 'Método no permitido'}, status=405)

    type_bill_document = request.GET.get('type_bill_document')
    subsidiary = Subsidiary.objects.get(id=1)
    serial_suffix = subsidiary.serial

    document_type_map = {
        'F': ('F' + serial_suffix, '1'),
        'B': ('B' + serial_suffix, '2'),
    }

    new_serial, doc_type = document_type_map.get(type_bill_document, ('T001', 'T'))

    if type_bill_document in document_type_map:
        last_receipt = (
            OrderBill.objects
            .filter(serial=new_serial, type=doc_type)
            .order_by('n_receipt')
            .last()
        )
        new_n_receipt = (last_receipt.n_receipt + 1) if last_receipt else 1
    else:
        max_correlative = Order.objects.filter(
            subsidiary=subsidiary,
            type='V',
            voucher_type=type_bill_document
        ).annotate(
            correlative_int=Cast('correlative', IntegerField())
        ).aggregate(
            r=Coalesce(Max('correlative_int'), 0)
        )['r']

        new_n_receipt = max_correlative + 1

    return JsonResponse({
        'status': True,
        'correlative': str(new_n_receipt).zfill(6),
        'serial': new_serial
    })


@csrf_exempt
def save_order(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_subsidiary_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_subsidiary_obj)
        # subsidiary_store_sales_obj = SubsidiaryStore.objects.get(
        #     subsidiary=subsidiary_obj, category='V')
        print_series = request.POST.get('print-series', '')
        _type_payment = request.POST.get('transaction_payment_type', '')
        _client_id = request.POST.get('client-id', '')
        _issue_date = request.POST.get('date', '')
        cash_finality = None
        if _type_payment == 'E':
            cash_finality = request.POST.get('cash_box', '')
        elif _type_payment == 'D':
            cash_finality = request.POST.get('id_cash_deposit', '')

        client_address = request.POST.get('client-address', '')
        client_id = request.POST.get('client-id', '')

        client_obj = Client.objects.get(pk=int(client_id))
        client_address_set = ClientAddress.objects.filter(client=client_obj)
        if client_address_set.exists():
            client_address_obj = client_address_set.last()
            client_address_obj.address = client_address
            client_address_obj.save()
        else:
            client_address_obj = ClientAddress(
                client=client_obj,
                address=client_address
            )
            client_address_obj.save()

        _sum_total = request.POST.get('sum-total', '')

        serial = request.POST.get('serial', '')
        issue_date = request.POST.get('issue_date', '')
        format_pdf = request.POST.get('format-pdf', '')

        user = request.POST.get('user', '')
        user_obj = User.objects.get(id=user)

        _condition_days = request.POST.get('condition_days', '')

        subsidiary_store_sales_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')

        _correlative = request.POST.get('correlative', '')
        # _type_bill_document = request.POST.get('type_bill_document', '')
        voucher_type = request.POST.get('type_bill_document', '')

        detail = json.loads(request.POST.get('detail', ''))
        credit = json.loads(request.POST.get('credit', ''))
        _date = utc_to_local(datetime.now())

        order_obj = Order(
            type='V',
            client=client_obj,
            user=user_obj,
            total=decimal.Decimal(_sum_total),
            status='P',
            subsidiary_store=subsidiary_store_sales_obj,
            correlative_sale=get_correlative_order(subsidiary_obj, 'V'),
            subsidiary=subsidiary_obj,
            create_at=_date,
            correlative=_correlative,
            way_to_pay_type=_type_payment,
            voucher_type=voucher_type,
            pay_condition=_condition_days,
            issue_date=issue_date
        )
        order_obj.save()

        for detail in detail:
            quantity = decimal.Decimal(detail['quantity'])
            price = decimal.Decimal(detail['price'])
            total = decimal.Decimal(detail['detailTotal'])
            product_id = int(detail['product'])
            product_obj = Product.objects.get(id=product_id)
            unit_id = int(detail['unit'])
            unit_obj = Unit.objects.get(id=unit_id)
            commentary = str(detail['commentary'])
            # store_product_id = int(detail['store'])
            # product_store_obj = ProductStore.objects.get(id=store_product_id)
            # quantity_minimum_unit = calculate_minimum_unit(quantity, unit_obj, product_obj)

            order_detail_obj = OrderDetail(
                order=order_obj,
                product=product_obj,
                quantity_sold=quantity,
                price_unit=price,
                unit=unit_obj,
                commentary=commentary,
                status='V',
            )
            order_detail_obj.save()

            if unit_obj.name != 'ZZ':
                if detail['serials'] != '':
                    for serial in detail['serials']:
                        product_serial_set = ProductSerial.objects.filter(serial_number=serial['Serial'])
                        if product_serial_set.exists():
                            product_serial_obj = product_serial_set.last()
                            product_serial_obj.order_detail = order_detail_obj
                            product_serial_obj.status = 'V'
                            product_serial_obj.save()
                        else:
                            raise ValidationError(
                                f"El número de serie {serial['Serial']} no existe, Actualice la Pagina y vuelva a intentar")

                if order_detail_obj is None:
                    raise ValidationError(
                        "Error al crear el detalle de la orden. Operación cancelada. Actualice")

                store_product_id = int(detail['store'])
                product_store_obj = ProductStore.objects.get(id=store_product_id)
                quantity_minimum_unit = calculate_minimum_unit(quantity, unit_obj, product_obj)
                kardex_ouput(product_store_obj.id, quantity_minimum_unit, order_detail_obj=order_detail_obj)

        code_operation = '-'
        if _type_payment in ['E', 'D']:
            cash_id = request.POST.get('cash_box' if _type_payment == 'E' else 'id_cash_deposit', '')
            cash_obj = Cash.objects.get(id=int(cash_id))

            if _type_payment == 'D':
                code_operation = request.POST.get('code-operation', '')

            loan_payment_obj = LoanPayment(
                price=decimal.Decimal(_sum_total),
                order=order_obj,
                create_at=_date,
                type='V',
                operation_date=_date
            )
            loan_payment_obj.save()

            transaction_payment_obj = TransactionPayment(
                payment=decimal.Decimal(_sum_total),
                type=_type_payment,
                operation_code=code_operation,
                loan_payment=loan_payment_obj
            )
            transaction_payment_obj.save()

            cash_flow_obj = CashFlow(
                transaction_date=_date,
                description=f"{order_obj.subsidiary.serial}-{str(order_obj.correlative).zfill(6)}",
                document_type_attached='T',
                type=_type_payment,
                total=_sum_total,
                operation_code=code_operation,
                order=order_obj,
                user=user_obj,
                cash=cash_obj
            )
            cash_flow_obj.save()

        elif _type_payment == 'C':
            for c in credit:
                PaymentFees.objects.create(date=c['date'], order=order_obj,
                                           amount=decimal.Decimal(c['amount']))
        msg_sunat = None
        sunat_pdf = None
        if voucher_type == 'F':
            # r = send_bill_nubefact(order_obj.id, subsidiary_obj.serial)
            # codigo_hash = r.get('codigo_hash')
            # msg_sunat = r.get('sunat_description')
            # sunat_pdf = r.get('enlace_del_pdf')
            # # codigo_hash = True
            # if codigo_hash:
            #     order_bill_obj = OrderBill(order=order_obj,
            #                                serial=r.get('serie'),
            #                                type=r.get('tipo_de_comprobante'),
            #                                sunat_status=r.get('aceptada_por_sunat'),
            #                                sunat_description=r.get('sunat_description'),
            #                                user=user_obj,
            #                                sunat_enlace_pdf=r.get('enlace_del_pdf'),
            #                                code_qr=r.get('cadena_para_codigo_qr'),
            #                                code_hash=r.get('codigo_hash'),
            #                                n_receipt=r.get('numero'),
            #                                status='E',
            #                                created_at=order_obj.create_at,
            #                                )
            #     order_bill_obj.save()
            #
            # else:
            #     objects_to_delete = OrderDetail.objects.filter(order=order_obj)
            #     objects_to_delete.delete()
            #     order_obj.delete()
            #     if r.get('errors'):
            #         data = {'error': str(r.get('errors'))}
            #     elif r.get('error'):
            #         data = {'error': str(r.get('error'))}
            #     response = JsonResponse(data)
            #     response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            #     return response
            r = send_bill_4_fact(order_obj.id)
            if r.get('success'):
                order_bill_obj = OrderBill(order=order_obj,
                                           serial=r.get('serie'),
                                           type=r.get('tipo_de_comprobante'),
                                           user=user_obj,
                                           n_receipt=r.get('numero'),
                                           status='E',
                                           created_at=order_obj.create_at,
                                           invoice_id=r.get('operationId'),
                                           )
                order_bill_obj.save()
                sunat_pdf = True
            else:
                objects_to_delete = OrderDetail.objects.filter(order=order_obj)
                objects_to_delete.delete()
                order_obj.delete()
                if r.get('errors'):
                    data = {'error': str(r.get('errors'))}
                elif r.get('error'):
                    data = {'error': str(r.get('error'))}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        elif voucher_type == 'B':
            # r = send_receipt_nubefact(order_obj.id, subsidiary_obj.serial)
            # codigo_hash = r.get('codigo_hash')
            # msg_sunat = r.get('sunat_description')
            # sunat_pdf = r.get('enlace_del_pdf')
            # # codigo_hash = True
            # if codigo_hash:
            #     order_bill_obj = OrderBill(order=order_obj,
            #                                serial=r.get('serie'),
            #                                type=r.get('tipo_de_comprobante'),
            #                                sunat_status=r.get('aceptada_por_sunat'),
            #                                sunat_description=r.get('sunat_description'),
            #                                user=user_obj,
            #                                sunat_enlace_pdf=r.get('enlace_del_pdf'),
            #                                code_qr=r.get('cadena_para_codigo_qr'),
            #                                code_hash=r.get('codigo_hash'),
            #                                n_receipt=r.get('numero'),
            #                                status='E',
            #                                created_at=order_obj.create_at,
            #                                )
            #     order_bill_obj.save()
            # else:
            #     objects_to_delete = OrderDetail.objects.filter(order=order_obj)
            #     objects_to_delete.delete()
            #     order_obj.delete()
            #
            #     if r.get('errors'):
            #         data = {'error': str(r.get('errors'))}
            #     elif r.get('error'):
            #         data = {'error': str(r.get('error'))}
            #     response = JsonResponse(data)
            #     response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            #     return response
            r = send_receipt_4_fact(order_obj.id)
            if r.get('success'):
                order_bill_obj = OrderBill(order=order_obj,
                                           serial=r.get('serie'),
                                           type=r.get('tipo_de_comprobante'),
                                           user=user_obj,
                                           n_receipt=r.get('numero'),
                                           status='E',
                                           created_at=order_obj.create_at,
                                           invoice_id=r.get('operationId'),
                                           )
                order_bill_obj.save()
                sunat_pdf = True
            else:
                objects_to_delete = OrderDetail.objects.filter(order=order_obj)
                objects_to_delete.delete()
                order_obj.delete()
                if r.get('errors'):
                    data = {'error': str(r.get('errors'))}
                elif r.get('error'):
                    data = {'error': str(r.get('error'))}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        return JsonResponse({
            'message': 'Venta Generada Correctamente',
            'id_sales': order_obj.id,
            'type_doc': order_obj.type,
            'voucher_type': order_obj.voucher_type,
            'format_pdf': format_pdf,
            'check_print_series': print_series,
            'msg_sunat': msg_sunat,
            'sunat_pdf': sunat_pdf,
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def modal_credit_note(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        if pk:
            details = []
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            order_obj = Order.objects.get(id=int(pk))
            order_bill_obj = OrderBill.objects.get(order=int(pk))

            credit_note_totals = CreditNoteDetail.objects.filter(
                credit_note__order=order_obj
            ).values('product_id', 'unit_id').annotate(total_returned=Sum('quantity'))

            credit_note_map = {
                (item['product_id'], item['unit_id']): item['total_returned']
                for item in credit_note_totals
            }
            for d in order_obj.orderdetail_set.all():

                product_id = d.product.id
                unit_id = d.unit.id
                quantity_sold = d.quantity_sold
                quantity_returned = credit_note_map.get((product_id, unit_id), 0)
                quantity_pending = max(quantity_sold - quantity_returned, 0)

                if quantity_pending <= 0:
                    continue

                item = {
                    'id': d.id,
                    'order': d.order.id,
                    # 'quantity': d.quantity_sold,
                    'quantity': quantity_pending,
                    'price': d.price_unit,
                    'unit': d.unit,
                    'product_id': d.product.id,
                    'product_name': d.product.name,
                    'product_code': d.product.code,
                    'price_unit': d.price_unit,
                    'multiply': d.multiply(),
                    'serials': [],
                }

                for s in d.productserial_set.all():
                    item_serial = {
                        'id': s.id,
                        'serial_number': s.serial_number
                    }
                    item.get('serials').append(item_serial)

                details.append(item)

            tpl = loader.get_template('sales/modal_credit_note.html')
            context = ({
                'date_now': date_now,
                'order_obj': order_obj,
                'order_bill_obj': order_bill_obj,
                'details': details,
            })
            dict_obj = model_to_dict(order_obj)
            serialized_obj = json.dumps(dict_obj, cls=DjangoJSONEncoder)
            serialized_detail_set = [{
                'detailID': detail.id,
                'productID': detail.product.id,
                'productName': detail.product.name,
                'price': float(detail.price_unit),
                'quantitySold': float(detail.quantity_sold),
                'isCreditNote': False,
                'quantityReturned': 0,
                'newSubtotal': 0,
            } for detail in order_obj.orderdetail_set.all()]
            return JsonResponse({
                'grid': tpl.render(context, request),
                'serialized_obj': serialized_obj,
                'serialized_detail_set': serialized_detail_set,
                'orderTotal': order_obj.total,
            }, status=HTTPStatus.OK, content_type="application/json")
        else:
            return JsonResponse({
                'success': False,
                'message': 'Orden desconocida',
            }, status=HTTPStatus.OK)


@csrf_exempt
def save_credit_note(request):
    if request.method == 'POST':
        order = request.POST.get('id-order', '')
        motive = request.POST.get('motive-credit-note', '')
        issue_date = request.POST.get('issue_date', '')
        motive_text = request.POST.get('motive_text')
        order_obj = Order.objects.get(id=order)
        order_bill_set = OrderBill.objects.filter(order=order_obj)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        if order_bill_set.exists():
            order_obj = Order.objects.get(id=int(order))
            details = request.POST.get('details', '')
            details_data = json.loads(details)
            # nc = credit_note_by_parts(order, details_data)
            nc = send_credit_note_fact(order, details_data, motive)
            if nc.get('success'):
                message = nc.get('message')
                serial = nc.get('serial')
                correlative = nc.get('correlative')
                enlace_del_pdf = nc.get('enlace_del_pdf')
                note_total = nc.get('note_total')
                note_description = nc.get('note_description')

                credit_note_obj = CreditNote.objects.create(
                    serial=serial,
                    correlative=correlative,
                    issue_date=issue_date,
                    order=order_obj,
                    motive=motive_text,
                    status='E',
                    note_description=note_description,
                    note_enlace_pdf=enlace_del_pdf,
                    note_total=note_total,
                )

                for d in details_data:
                    if d['quantityReturned']:

                        detail_id = d['detailID']
                        quantity_returned = decimal.Decimal(d['quantityReturned'])
                        product_id = int(d['productID'])
                        unit = str(d['unit'])
                        unit_obj = Unit.objects.get(name=unit)
                        price = decimal.Decimal(d['price'])

                        product_obj = Product.objects.get(id=product_id)
                        credit_detail_obj = CreditNoteDetail(
                            code=product_obj.code,
                            description=product_obj.name,
                            quantity=quantity_returned,
                            product=product_obj,
                            unit=unit_obj,
                            price_unit=price,
                            credit_note=credit_note_obj,
                            total=quantity_returned * price,

                        )
                        credit_detail_obj.save()
                        subsidiary_store_set_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
                        product_store_obj = ProductStore.objects.get(subsidiary_store=subsidiary_store_set_obj,
                                                                     product=product_obj)
                        kardex_input_credit_note(product_store_id=product_store_obj.id,
                                                 quantity_return=quantity_returned,
                                                 credit_note_detail_obj=credit_detail_obj)
                        # detail_obj = OrderDetail.objects.get(id=detail_id)
                        if 'serials' in d and d['serials']:
                            for serial_id in d['serials']:
                                try:
                                    product_serial = ProductSerial.objects.get(
                                        id=serial_id,
                                        order_detail_id=detail_id,
                                        product_store=product_store_obj
                                    )
                                    product_serial.order_detail = None
                                    product_serial.status = 'C'
                                    product_serial.save()

                                    CreditNoteDetailSerial.objects.create(
                                        credit_note_detail=credit_detail_obj,
                                        product_serial=product_serial
                                    )
                                except ProductSerial.DoesNotExist:
                                    # Puedes loggear aquí si es necesario
                                    continue
                        # product_serial_set = ProductSerial.objects.filter(order_detail=detail_obj,
                        #                                                   product_store=product_store_obj)
                        # if product_serial_set.exists():
                        #     for ps in product_serial_set:
                        #         ps.order_detail = None
                        #         ps.status = 'C'
                        #         ps.save()

                return JsonResponse({
                    'success': True,
                    'enlace': nc.get('enlace_del_pdf'),
                    'message': 'Nota de credito generada',
                    'message_sunat': message,
                }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'success': False,
                'number': order_obj.number,
                'message': 'Orden sin comprobante electronico',
            }, status=HTTPStatus.OK)


def get_credit_notes_report(request):
    """
    Vista para mostrar el reporte de notas de crédito
    """
    from datetime import datetime, timedelta
    
    # Obtener fechas por defecto (último mes)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    formatdate = start_date.strftime('%Y-%m-%d')
    
    context = {
        'formatdate': formatdate,
        'end_date': end_date.strftime('%Y-%m-%d')
    }
    
    return render(request, 'sales/credit_notes_list.html', context)


def get_credit_notes_by_date(request):
    """
    Vista AJAX para obtener las notas de crédito filtradas por fecha
    """
    from datetime import datetime
    
    if request.method == 'POST':
        start_date = request.POST.get('start-date')
        end_date = request.POST.get('end-date')
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
        
        # Obtener notas de crédito en el rango de fechas
        credit_notes = CreditNote.objects.filter(
            issue_date__range=[start_date, end_date],
            status__in=['E', 'P']  # Emitidas y Pendientes
        ).order_by('-issue_date')
        
        # Preparar datos para el template
        credit_notes_data = []
        total_amount = 0
        
        for note in credit_notes:
            # Obtener detalles de la nota de crédito
            details = CreditNoteDetail.objects.filter(credit_note=note)
            
            # Calcular total de la nota
            note_total = sum(detail.total for detail in details)
            total_amount += note_total
            
            # Obtener información del cliente
            client_name = "N/A"
            if note.order and note.order.client:
                client_name = note.order.client.names
            
            # Obtener información del usuario
            user_name = note.order.user.worker_set.last().employee.names if note.order and note.order.user.worker_set.exists() else "N/A"
            
            credit_notes_data.append({
                'id': note.id,
                'serial': note.serial or 'N/A',
                'correlative': note.correlative,
                'issue_date': note.issue_date,
                'status': note.get_status_display(),
                'status_code': note.status,
                'client_name': client_name,
                'user_name': user_name,
                'total': note_total,
                'motive': note.motive or 'N/A',
                'details': details,
                'order_info': f"{note.order.voucher_type}-{note.order.correlative}" if note.order else 'N/A',
                'pdf_url': note.note_enlace_pdf if note.note_enlace_pdf else None,
                'qr_code': note.note_qr if note.note_qr else None,
                'hash_code': note.note_hash if note.note_hash else None,
            })
        
        # Estadísticas por usuario
        user_stats = {}
        for note_data in credit_notes_data:
            user_name = note_data['user_name']
            if user_name not in user_stats:
                user_stats[user_name] = {
                    'user_names': user_name,
                    'total_notes': 0,
                    'total_amount': 0,
                    'emitted_notes': 0,
                    'pending_notes': 0
                }
            
            user_stats[user_name]['total_notes'] += 1
            user_stats[user_name]['total_amount'] += note_data['total']
            
            if note_data['status_code'] == 'E':
                user_stats[user_name]['emitted_notes'] += 1
            elif note_data['status_code'] == 'P':
                user_stats[user_name]['pending_notes'] += 1
        
        # Estadísticas por estado
        status_stats = {
            'emitted': len([n for n in credit_notes_data if n['status_code'] == 'E']),
            'pending': len([n for n in credit_notes_data if n['status_code'] == 'P']),
            'cancelled': len([n for n in credit_notes_data if n['status_code'] == 'A'])
        }
        
        context = {
            'credit_notes': credit_notes_data,
            'total_amount': total_amount,
            'user_stats': user_stats,
            'status_stats': status_stats,
            'start_date': start_date,
            'end_date': end_date,
            'f1': start_date.strftime('%Y-%m-%d'),
            'f2': end_date.strftime('%Y-%m-%d')
        }
        
        # Renderizar el grid
        grid_html = render_to_string('sales/credit_notes_grid_list.html', context)
        
        return JsonResponse({
            'grid': grid_html,
            'total_amount': total_amount,
            'total_notes': len(credit_notes_data)
        })
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


def cancel_credit_note(request):
    """
    Vista para anular una nota de crédito
    """
    if request.method == 'GET':
        note_id = request.GET.get('pk')
        
        try:
            credit_note = CreditNote.objects.get(id=note_id)
            
            # Solo se pueden anular notas pendientes
            if credit_note.status == 'P':
                credit_note.status = 'A'  # Anulada
                credit_note.save()
                
                # Regenerar el grid
                start_date = request.GET.get('start-date')
                end_date = request.GET.get('end-date')
                
                # Llamar a la función que regenera el grid
                from datetime import datetime
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                credit_notes = CreditNote.objects.filter(
                    issue_date__range=[start_date, end_date],
                    status__in=['E', 'P']
                ).order_by('-issue_date')
                
                # Preparar datos para el template (código similar a get_credit_notes_by_date)
                credit_notes_data = []
                total_amount = 0
                
                for note in credit_notes:
                    details = CreditNoteDetail.objects.filter(credit_note=note)
                    note_total = sum(detail.total for detail in details)
                    total_amount += note_total
                    
                    client_name = "N/A"
                    if note.order and note.order.client:
                        client_name = note.order.client.names
                    
                    user_name = note.order.user.worker_set.last().employee.names if note.order and note.order.user.worker_set.exists() else "N/A"
                    
                    credit_notes_data.append({
                        'id': note.id,
                        'serial': note.serial or 'N/A',
                        'correlative': note.correlative,
                        'issue_date': note.issue_date,
                        'status': note.get_status_display(),
                        'status_code': note.status,
                        'client_name': client_name,
                        'user_name': user_name,
                        'total': note_total,
                        'motive': note.motive or 'N/A',
                        'details': details,
                        'order_info': f"{note.order.voucher_type}-{note.order.correlative}" if note.order else 'N/A',
                        'pdf_url': note.note_enlace_pdf if note.note_enlace_pdf else None,
                        'qr_code': note.note_qr if note.note_qr else None,
                        'hash_code': note.note_hash if note.note_hash else None,
                    })
                
                # Estadísticas por usuario
                user_stats = {}
                for note_data in credit_notes_data:
                    user_name = note_data['user_name']
                    if user_name not in user_stats:
                        user_stats[user_name] = {
                            'user_names': user_name,
                            'total_notes': 0,
                            'total_amount': 0,
                            'emitted_notes': 0,
                            'pending_notes': 0
                        }
                    
                    user_stats[user_name]['total_notes'] += 1
                    user_stats[user_name]['total_amount'] += note_data['total']
                    
                    if note_data['status_code'] == 'E':
                        user_stats[user_name]['emitted_notes'] += 1
                    elif note_data['status_code'] == 'P':
                        user_stats[user_name]['pending_notes'] += 1
                
                context = {
                    'credit_notes': credit_notes_data,
                    'total_amount': total_amount,
                    'user_stats': user_stats,
                    'start_date': start_date,
                    'end_date': end_date,
                    'f1': start_date.strftime('%Y-%m-%d'),
                    'f2': end_date.strftime('%Y-%m-%d')
                }
                
                grid_html = render_to_string('sales/credit_notes_grid_list.html', context)
                
                return JsonResponse({
                    'message': 'Nota de crédito anulada correctamente',
                    'grid': grid_html
                })
            else:
                return JsonResponse({
                    'error': 'Solo se pueden anular notas de crédito pendientes'
                }, status=400)
                
        except CreditNote.DoesNotExist:
            return JsonResponse({
                'error': 'Nota de crédito no encontrada'
            }, status=404)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


def get_product_serials(request):
    """
    Vista para obtener las series de un producto específico
    """
    if request.method == 'GET':
        product_id = request.GET.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id)
            
            # Obtener solo las series disponibles (estado 'C' - Comprado)
            product_serials = ProductSerial.objects.filter(
                product_store__product=product,
                status='C'  # Solo series disponibles
            ).select_related(
                'product_store__subsidiary_store__subsidiary',
                'product_store__subsidiary_store'
            ).order_by('product_store__subsidiary_store__subsidiary__name', 'serial_number')
            
            # Agrupar series por sucursal y almacén
            serials_by_store = {}
            for serial in product_serials:
                store_key = f"{serial.product_store.subsidiary_store.subsidiary.name} - {serial.product_store.subsidiary_store.name}"
                if store_key not in serials_by_store:
                    serials_by_store[store_key] = {
                        'subsidiary': serial.product_store.subsidiary_store.subsidiary.name,
                        'store': serial.product_store.subsidiary_store.name,
                        'serials': []
                    }
                
                serials_by_store[store_key]['serials'].append({
                    'id': serial.id,
                    'serial_number': serial.serial_number,
                    'created_at': serial.product_store.create_at if hasattr(serial.product_store, 'create_at') else None
                })
            
            # Crear el HTML del modal
            html_content = f"""
            <div class="container-fluid">
                <div class="row mb-3">
                    <div class="col-12">
                        <h6 class="text-primary">
                            <i class="fas fa-box"></i> {product.name}
                        </h6>
                        <small class="text-muted">Código: {product.code or 'N/A'}</small>
                    </div>
                </div>
            """
            
            if serials_by_store:
                for store_key, store_data in serials_by_store.items():
                    html_content += f"""
                    <div class="card mb-3">
                        <div class="card-header bg-success text-white">
                            <h6 class="mb-0">
                                <i class="fas fa-warehouse"></i> {store_data['subsidiary']} - {store_data['store']}
                                <span class="badge badge-light ml-2">{len(store_data['serials'])} disponibles</span>
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="row">
                    """
                    
                    for serial in store_data['serials']:
                        html_content += f"""
                                <div class="col-md-4 col-sm-6 mb-2">
                                    <div class="d-flex align-items-center">
                                        <span class="badge badge-success mr-2">
                                            <i class="fas fa-check"></i>
                                        </span>
                                        <span class="font-weight-bold">{serial['serial_number']}</span>
                                    </div>
                                </div>
                        """
                    
                    html_content += """
                            </div>
                        </div>
                    </div>
                    """
            else:
                html_content += """
                <div class="alert alert-warning text-center">
                    <i class="fas fa-exclamation-triangle"></i>
                    No se encontraron series disponibles para este producto.
                </div>
                """
            
            html_content += "</div>"
            
            return JsonResponse({
                'success': True,
                'html': html_content
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Producto no encontrado'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al obtener las series: {str(e)}'
            })
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)