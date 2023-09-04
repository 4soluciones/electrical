from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models.functions import Coalesce
from apps.hrm.views import get_subsidiary_by_user
from apps.buys.models import Purchase, PurchaseDetail, PurchaseDues
from apps.sales.models import Subsidiary, SubsidiaryStore, Order, OrderDetail, TransactionPayment, LoanPayment, \
    OrderBill
from django.template import loader, Context
from django.http import JsonResponse
from http import HTTPStatus
from .models import *
import decimal
from django.shortcuts import render
from django.views.generic import TemplateView

from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.db import DatabaseError, IntegrityError
import json
from django.core import serializers
from django.db.models import Min, Sum, Prefetch


class Home(TemplateView):
    template_name = 'accounting/home.html'


def get_purchases_list(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        purchases_store = Purchase.objects.filter(subsidiary=subsidiary_obj, status='A')
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        return render(request, 'accounting/purchase_list.html', {
            'purchases_store': purchases_store,
            'date': formatdate,
        })


def get_purchases_by_date(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        start_date = request.GET.get('start-date', '')
        end_date = request.GET.get('end-date', '')
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        purchases_set = Purchase.objects.filter(purchase_date__range=[start_date, end_date], subsidiary=subsidiary_obj,
                                                status='A')

        return JsonResponse({
            'grid': get_dict_purchases(purchases_set),
        }, status=HTTPStatus.OK)


def get_dict_purchases(purchases_set):
    dictionary = []

    for p in purchases_set:
        lp_id = ""
        lp_quantity = ""
        lp_date = ""
        lp_price = ""
        lp_type = ""

        loan_payment_set = LoanPayment.objects.filter(purchase=p)
        if loan_payment_set.exists():
            loan_payment_obj = loan_payment_set.last()
            lp_id = loan_payment_obj.id
            lp_quantity = loan_payment_obj.quantity
            lp_date = loan_payment_obj.create_at
            lp_price = loan_payment_obj.price
            lp_type = loan_payment_obj.type

        if p.purchasedetail_set.count() > 0:
            new = {
                'id': p.id,
                'supplier': p.supplier,
                'type': p.get_status_display(),
                'purchase_date': p.purchase_date,
                'bill_number': p.bill_number,
                'purchase_detail_set': {},
                'loan_payment_set': [],
                'purchase_dues': {},
                'dict_table': {},
                'user': p.user,
                'subsidiary': p.subsidiary,
                'status': p.get_status_display,
                'details_count': p.purchasedetail_set.count(),
                'dues_count': p.purchasedues_set.count(),
                'total': round(p.total_import, 2),
                'total_freight': round(p.total_freight, 2),
                'base_total_purchase': round(p.base_total_purchase, 2),
                'igv_total_purchase': round(p.igv_total_purchase, 2),
                'rowspan_detail': 0,
                'rowspan_due': 0,
                'rowspan_total': 0,
                'rowspan_gt': 0,
                'lp_id': lp_id,
                'lp_quantity': lp_quantity,
                'lp_date': lp_date,
                'lp_price': lp_price,
                'lp_type': lp_type,
                'type_pay': p.get_type_pay_display(),
                'range': 0
            }
            rowspan_due = 1
            i = 0
            for pd in PurchaseDues.objects.filter(purchase=p):
                purchase_due = {
                    'id': pd.id,
                    'due': pd.due,
                    'rowspan_due': rowspan_due
                }
                new['purchase_dues'][i] = purchase_due
                i += 1
            nro_dues = PurchaseDues.objects.filter(purchase=p).count()

            # for lp in p.loanpayment_set.all():
            #     loan_payment = {
            #         'id': lp.id,
            #         'quantity': lp.quantity,
            #         'date': lp.create_at,
            #         'price': round(lp.price, 2),
            #         'type': lp.type
            #     }
            # new.get('loan_payment_set').append(loan_payment)

            loans_count = p.loanpayment_set.count()
            i = 0
            for d in PurchaseDetail.objects.filter(purchase=p):
                total = float(d.multiplicate())
                purchase_detail = {
                    'id': d.id,
                    'product': d.product.name,
                    'quantity': d.quantity,
                    'unit': d.unit.description,
                    'price_unit': round(d.price_unit, 2),
                    'total': round(total, 2),
                }
                new['purchase_detail_set'][i] = purchase_detail
                i += 1
            nro_details = PurchaseDetail.objects.filter(purchase=p).count()

            if nro_dues == 0:
                nro_dues = 1

            new['rowspan_total'] = int(nro_details * nro_dues)
            new['rowspan_due'] = int(new['rowspan_total'] / nro_dues)
            new['rowspan_detail'] = int(new['rowspan_total'] / nro_details)
            new['range'] = range(int(new['rowspan_total']))

            e_dict = {}

            if nro_dues > nro_details:
                nro_total = nro_dues
            else:
                nro_total = nro_details

            for e in range(nro_total):

                a = ''
                b = ''

                if e in new['purchase_detail_set'].keys():
                    a = new['purchase_detail_set'][e]
                if e in new['purchase_dues'].keys():
                    b = new['purchase_dues'][e]

                e_dict[e] = {
                    'a': a,
                    'b': b
                }

            new['dict_table'] = e_dict
            new['rowspan_gt'] = int(nro_total)

            dictionary.append(new)

    tpl = loader.get_template('accounting/purchase_grid.html')
    context = ({
        'dictionary': dictionary,
        # 'rowspan': len(dictionary)
    })
    return tpl.render(context)


def get_purchases_pay(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        purchase_id = request.GET.get('purchase_id', '')
        start_date = request.GET.get('start-date', '')
        end_date = request.GET.get('end-date', '')
        purchase_obj = Purchase.objects.get(id=int(purchase_id))
        detail_purchase_obj = PurchaseDetail.objects.filter(purchase=purchase_obj)
        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='104')
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        tpl = loader.get_template('accounting/new_pay_purchase.html')
        context = ({
            'choices_payments': TransactionPayment._meta.get_field('type').choices,
            'detail_purchase': detail_purchase_obj,
            'purchase': purchase_obj,
            'choices_account': cash_set,
            'choices_account_bank': cash_deposit_set,
            'date': formatdate,
            'start_date': start_date,
            'end_date': end_date
        })

        return JsonResponse({
            'grid': tpl.render(context, request),

        }, status=HTTPStatus.OK)


def new_payment_purchase(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        purchase_total = str(request.POST.get('purchase_total'))
        purchase_pay = str(request.POST.get('purchase_pay'))
        start_date = str(request.POST.get('date-ini'))
        end_date = str(request.POST.get('date-fin'))
        transaction_payment_type = str(request.POST.get('transaction_payment_type'))
        purchase_id = int(request.POST.get('purchase'))
        purchase_obj = Purchase.objects.get(id=purchase_id)
        purchases_set = Purchase.objects.filter(purchase_date__range=[start_date, end_date], subsidiary=subsidiary_obj,
                                                status='A')

        if transaction_payment_type == 'E':
            cash_id = str(request.POST.get('cash_efectivo'))
            cash_obj = Cash.objects.get(id=cash_id)
            cash_flow_description = str(request.POST.get('description_cash'))
            cash_flow_date = str(request.POST.get('id_date'))

            cashflow_obj = CashFlow(
                created_at=cash_flow_date,
                transaction_date=cash_flow_date,
                document_type_attached='O',
                description=cash_flow_description,
                purchase=purchase_obj,
                type='S',
                total=purchase_pay,
                cash=cash_obj,
                user=user_obj
            )
            cashflow_obj.save()

            loan_payment_obj = LoanPayment(
                price=purchase_pay,
                type='C',
                purchase=purchase_obj
            )
            loan_payment_obj.save()

            transaction_payment_obj = TransactionPayment(
                payment=purchase_pay,
                type=transaction_payment_type,
                loan_payment=loan_payment_obj
            )
            transaction_payment_obj.save()

        if transaction_payment_type == 'D':
            cash_flow_description = str(request.POST.get('description_deposit'))
            cash_flow_transact_date_deposit = str(request.POST.get('id_date_deposit'))
            cash_id = str(request.POST.get('id_cash_deposit'))
            cash_obj = Cash.objects.get(id=cash_id)
            code_operation = str(request.POST.get('code_operation'))

            cashflow_obj = CashFlow(
                created_at=cash_flow_transact_date_deposit,
                transaction_date=cash_flow_transact_date_deposit,
                document_type_attached='O',
                description=cash_flow_description,
                purchase=purchase_obj,
                type='R',
                operation_code=code_operation,
                total=purchase_pay,
                cash=cash_obj,
                user=user_obj
            )
            cashflow_obj.save()

            loan_payment_obj = LoanPayment(
                price=purchase_pay,
                type='C',
                purchase=purchase_obj
            )
            loan_payment_obj.save()

            transaction_payment_obj = TransactionPayment(
                payment=purchase_pay,
                type=transaction_payment_type,
                loan_payment=loan_payment_obj
            )
            transaction_payment_obj.save()

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'grid': get_dict_purchases(purchases_set),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_account_list(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        account_set = AccountingAccount.objects.filter(code__startswith='10').order_by('code')
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        return render(request, 'accounting/account_list.html', {
            'formatdate': formatdate,
            'subsidiary_obj': subsidiary_obj,
            'account_set': account_set,
        })


def new_opening_balance(request):
    if request.method == 'GET':
        store_request = request.GET.get('stores', '')
        data = json.loads(store_request)
        _date = str(data["Date"])
        for detail in data['Details']:
            _account_code = str(detail['AccountCode'])
            _debit = decimal.Decimal(detail['Debit'])
            _credit = decimal.Decimal(detail['Credit'])

            if _debit > 0:
                _operation = 'D'
                _amount = _debit
            elif _credit > 0:
                _operation = 'C'
                _amount = _credit

            account_obj = AccountingAccount.objects.get(code=str(_account_code))

            ledger_entry_obj = LedgerEntry(
                amount=_amount,
                type=_operation,
                account=account_obj,
            )
            ledger_entry_obj.save()

        return JsonResponse({
            'success': True,
        })


def get_cash_control_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj)
        only_cash_set = cash_set.filter(accounting_account__code__startswith='101')

        cash_all_set = Cash.objects.filter(accounting_account__code__startswith='101').order_by('id')

        accounts_banks_set = Cash.objects.filter(accounting_account__code__startswith='104')

        return render(request, 'accounting/cash_list.html', {
            'formatdate': formatdate,
            'only_cash_set': only_cash_set,
            'cash_all_set': cash_all_set,
            'accounts_banks_set': accounts_banks_set,
            'choices_operation_types': CashFlow._meta.get_field('operation_type').choices,
        })
    elif request.method == 'POST':
        total_cash = 0
        id_cash = int(request.POST.get('cash'))
        start_date = str(request.POST.get('start-date'))
        # end_date = str(request.POST.get('end-date'))

        total_cash_query = CashFlow.objects.filter(cash__id=id_cash,
                                                   order__create_at__date=start_date,
                                                   order__way_to_pay_type='E',
                                                   order__status__in=['P', 'C']).values(
            'order__create_at__date').annotate(totals=Sum('total'))

        if total_cash_query.exists():

            total_cash = total_cash_query[0].get('totals')

        cash_flow_set = CashFlow.objects.filter(created_at__date=start_date,
                                                cash__id=id_cash).select_related('order', 'cash', 'order__orderbill').prefetch_related(
            Prefetch(
                'order__orderdetail_set'
            ),
        ).order_by('id')

        has_rows = False
        if cash_flow_set:

            return JsonResponse({
                'grid': get_cash_dict(cash_flow_set, date=start_date, subsidiary_id=subsidiary_obj.id, total_cash=total_cash),
            }, status=HTTPStatus.OK)

        else:
            data = {'error': "No hay operaciones registradas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        # tpl = loader.get_template('accounting/cash_grid_list.html')
        # context = ({
        #     'cash_flow_set': cash_flow_set,
        #     'has_rows': has_rows
        # # })
        # return JsonResponse({
        #     'grid': tpl.render(context, request),
        # }, status=HTTPStatus.OK)


def get_cash_dict(cash_flow_set, date, subsidiary_id, total_cash):
    dictionary = []
    sum_order = []

    previous_balance = 0
    inputs = 0
    outputs = 0
    total_day = 0
    outputs_without_transfer = 0
    sum = 0
    # order_set = Order.objects.filter(subsidiary_id=subsidiary_id, create_at__date=date, type='V', status__in=['P', 'A'])

    order_bill_obj = ''
    serial_bill = ''
    correlative_bill = ''
    type_bill = 'TICKET'
    count_t = 0
    sum_total_t = 0
    count_f = 0
    sum_total_f = 0
    count_b = 0
    sum_total_b = 0
    cash_transfer = 0
    # total_cash = decimal.Decimal(0)

    for c in cash_flow_set:

        client = '-'

        inputs = round(decimal.Decimal(c.return_inputs()), 2)
        outputs = round(decimal.Decimal(c.return_outputs()), 2)
        outputs_without_transfer = round(decimal.Decimal(c.return_outputs_without_transfer()), 2)

        if c.cash_transfer:
            cash_transfer += round(decimal.Decimal(c.total), 2)

        if c.description == 'APERTURA':
            previous_balance = c.total

        if c.order:

            if c.document_type_attached == 'E' or c.document_type_attached == 'T':

                client = c.order.client.names

                order_bill_set = OrderBill.objects.filter(order=c.order.id).prefetch_related('order')

                if order_bill_set.exists():
                    order_bill_obj = order_bill_set.first()

                    if order_bill_obj.type == '1':
                        type_bill = 'FACTURA'
                        serial_bill = order_bill_obj.serial
                        correlative_bill = order_bill_obj.n_receipt
                        count_f = count_f + 1
                        sum_total_f += c.order.sum_total_details()
                    elif order_bill_obj.type == '2':
                        type_bill = 'BOLETA'
                        serial_bill = order_bill_obj.serial
                        correlative_bill = order_bill_obj.n_receipt
                        count_b = count_b + 1
                        sum_total_b += c.order.sum_total_details()
                else:

                    count_t += 1
                    sum_total_t += c.order.total

        cash = {
            'id': c.id,
            'operation': c.get_operation_type_display(),
            'description': c.description,
            'client': client,
            'type_doc': c.get_type_display(),
            'type': c.type,
            'subtotal': c.subtotal,
            'igv': c.igv,
            'total': c.total,
            'user': c.user,
            'date': c.created_at,
            'count': cash_flow_set.count(),
            'document_type': c.get_document_type_attached_display(),
            'inputs': c.return_inputs(),
            'outputs': c.return_outputs(),
            'balance': c.return_balance(),
            'status': c.return_status(),
        }
        dictionary.append(cash)


    total_day = (previous_balance + inputs) - outputs

    tpl = loader.get_template('accounting/cash_grid_list.html')
    context = ({
        'dictionary': dictionary,
        'sum_order': sum_order,
        'count_t': count_t,
        'sum_total_t': sum_total_t,
        'count_f': count_f,
        'sum_total_f': sum_total_f,
        'count_b': count_b,
        'sum_total_b': sum_total_b,
        'previous_balance': round(previous_balance, 2),
        'inputs': inputs,
        'outputs': outputs,
        'total_day': round(total_day, 2),
        'cash_transfer': cash_transfer,
        'outputs_without_transfer': outputs_without_transfer,
        'total_cash': decimal.Decimal(total_cash).quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN),
        'inputs_pay': decimal.Decimal(inputs - total_cash).quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN),
    })
    return tpl.render(context)


def get_account_cash():
    account_obj = AccountingAccount.objects.get(code='101')
    ledge_entry_set = LedgerEntry.objects.filter(account=account_obj)
    amount = 0
    if ledge_entry_set.count() > 0:
        ledge_entry_obj = ledge_entry_set.first()
        amount = ledge_entry_obj.amount
    context = {'account': account_obj, 'amount': amount}
    return context


def get_cash_by_subsidiary(request):
    if request.method == 'GET':
        pk = request.GET.get('cash_id', '')
        cash_obj = Cash.objects.get(id=pk)
        cash_subsidiary = cash_obj.subsidiary.name
        only_cash_set = AccountingAccount.objects.filter(code__startswith='10').order_by('code')

        return JsonResponse({'cash_subsidiary': cash_subsidiary}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def open_cash(request):
    if request.method == 'POST':
        _date = request.POST.get('cash-date')
        _amount = request.POST.get('cash-amount')
        _cash_id = request.POST.get('select-cash')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        cash_obj = Cash.objects.get(id=int(_cash_id))

        cash_flow_today_set = CashFlow.objects.filter(cash=cash_obj, transaction_date__date=_date, type='A')
        if cash_flow_today_set:
            data = {'error': "Ya existe una Apertura de Caja"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        else:
            last_cash_flow_opening_set = CashFlow.objects.filter(cash=cash_obj, type='A').order_by('created_at')

            if last_cash_flow_opening_set:
                cash_flow_opening_obj = last_cash_flow_opening_set.last()
                check_closed = CashFlow.objects.filter(type='C',
                                                       created_at__date=cash_flow_opening_obj.created_at.date(),
                                                       cash=cash_obj)
                if check_closed:
                    cash_flow_obj = CashFlow(
                        transaction_date=_date,
                        cash=cash_obj,
                        created_at=_date,
                        description='APERTURA',
                        total=decimal.Decimal(_amount),
                        user=user_obj,
                        type='A')
                    cash_flow_obj.save()
                else:
                    data = {'error': "Debes cerrar la caja " + str(cash_flow_opening_obj.transaction_date.date())}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response
            else:
                cash_flow_obj = CashFlow(
                    transaction_date=_date,
                    created_at=_date,
                    cash=cash_obj,
                    description='APERTURA',
                    total=decimal.Decimal(_amount),
                    user=user_obj,
                    type='A')
                cash_flow_obj.save()

        return JsonResponse({
            'message': 'Apertura de Caja exitosa.',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def close_cash(request):
    if request.method == 'GET':
        _pk = request.GET.get('pk')
        _date = request.GET.get('date')
        _status = request.GET.get('status')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        cash_flow_day_obj = CashFlow.objects.get(id=int(_pk))

        if _status == 'A':
            cash_flow_closed_obj = CashFlow.objects.get(
                cash=cash_flow_day_obj.cash,
                created_at_date=cash_flow_day_obj.created_at.date(),
                type='C')

            last_cash_flow_closed_set = CashFlow.objects.filter(
                cash=cash_flow_day_obj.cash,
                type='C')

            if last_cash_flow_closed_set:
                last_cash_flow_closed_obj = last_cash_flow_closed_set.last()
                if last_cash_flow_closed_obj == cash_flow_closed_obj:
                    cash_flow_closed_obj.delete()
                else:
                    data = {'error': "Ya no puede aperturar esta Caja"}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response
        else:
            cash_flow_obj = CashFlow(
                transaction_date=_date,
                created_at=_date,
                cash=cash_flow_day_obj.cash,
                description='CIERRE',
                total=decimal.Decimal(cash_flow_day_obj.return_balance()),
                user=user_obj,
                type='C')
            cash_flow_obj.save()

        return JsonResponse({
            'message': 'Cierre de Caja exitosa.',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def new_account(request):
    if request.method == 'POST':
        _account_parent_code = request.POST.get('account-parent-code', '')
        _new_account_code = request.POST.get('new-account-code', '')
        _new_account_name = request.POST.get('new-account-name', '')

        account_parent_obj = AccountingAccount.objects.get(code=str(_account_parent_code))

        search_account = AccountingAccount.objects.filter(code=str(_new_account_code))
        if search_account:
            data = {'error': 'Ya existe una cuenta con este codigo'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        else:

            try:
                accounting_account_obj = AccountingAccount(
                    code=str(_new_account_code),
                    description=str(_new_account_name),
                    parent_code=account_parent_obj.code
                )
                accounting_account_obj.save()
            except DatabaseError as e:
                data = {'error': str(e)}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            account_set = AccountingAccount.objects.filter(code__startswith='10').order_by('code')
            tpl = loader.get_template('accounting/account_grid_list.html')
            context = ({'account_set': account_set, })
            return JsonResponse({
                'message': 'Guardado con exito.',
                'grid': tpl.render(context),
            }, status=HTTPStatus.OK)

    return JsonResponse({'error': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def new_entity(request):
    if request.method == 'POST':
        _entity_name = request.POST.get('entity-name', '')
        _entity_subsidiary = request.POST.get('entity-subsidiary', '')
        _entity_account_code = request.POST.get('entity-account-code', '')
        _entity_account_number = request.POST.get('entity-account-number', '')
        _entity_initial = request.POST.get('entity-initial', '')

        accounting_account_obj = AccountingAccount.objects.get(code=str(_entity_account_code))
        subsidiary_obj = Subsidiary.objects.get(id=int(_entity_subsidiary))

        try:
            cash_obj = Cash(
                name=str(_entity_name.upper()),
                subsidiary=subsidiary_obj,
                account_number=str(_entity_account_number),
                accounting_account=accounting_account_obj,
                initial=decimal.Decimal(_entity_initial),
            )
            cash_obj.save()
        except DatabaseError as e:
            data = {'error': str(e)}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        account_set = AccountingAccount.objects.filter(code__startswith='10').order_by('code')
        tpl = loader.get_template('accounting/account_grid_list.html')
        context = ({'account_set': account_set, })
        return JsonResponse({
            'message': 'Guardado con exito.',
            'grid': tpl.render(context),
        }, status=HTTPStatus.OK)

    return JsonResponse({'error': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_entity(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        cash_obj = Cash.objects.filter(id=pk)
        serialized_obj = serializers.serialize('json', cash_obj)
        return JsonResponse({'obj': serialized_obj}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def update_entity(request):
    if request.method == 'POST':
        _entity_id = request.POST.get('entity', '')
        _entity_name = request.POST.get('entity-name', '')
        _entity_account_code = request.POST.get('entity-account-code', '')
        _entity_account_number = request.POST.get('entity-account-number', '')
        # _entity_initial = request.POST.get('entity-initial', '')

        cash_obj = Cash.objects.get(id=int(_entity_id))
        accounting_account_obj = AccountingAccount.objects.get(code=str(_entity_account_code))

        cash_obj.name = _entity_name.upper()
        cash_obj.account_number = str(_entity_account_number)
        cash_obj.accounting_account = accounting_account_obj
        cash_obj.save()

        account_set = AccountingAccount.objects.filter(code__startswith='10').order_by('code')
        tpl = loader.get_template('accounting/account_grid_list.html')
        context = ({'account_set': account_set, })

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'grid': tpl.render(context),
        }, status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_initial_balance(request):
    if request.method == 'GET':
        id_cash = request.GET.get('cash', '')
        cash_obj = Cash.objects.get(id=int(id_cash))
        initial_balance = cash_obj.current_balance()
        return JsonResponse({
            'initial_balance': initial_balance,
            'message': 'Codigo de sede recuperado.',
        }, status=HTTPStatus.OK)


def get_cash_date(request):
    data = dict()
    if request.method == 'GET':
        pk = request.GET.get('cash_id', '')
        cash_obj = Cash.objects.get(id=pk)
        cash_flow_set = CashFlow.objects.filter(cash=cash_obj, type='A')
        cash_flow_c_set = CashFlow.objects.filter(cash=cash_obj, type='C')
        _date = ''
        _date_c = ''
        if cash_flow_set.count() > 0:
            last_cash_flow_obj = cash_flow_set.last()
            _date = last_cash_flow_obj.transaction_date.strftime("%Y-%m-%d")
        if cash_flow_c_set.count() > 0:
            last_cash_flow_c_obj = cash_flow_c_set.last()
            _date_c = last_cash_flow_c_obj.transaction_date.strftime("%Y-%m-%d")
        if _date == _date_c:
            data = {'error': 'NECESITA APERTURAR LA CAJA ANTES DE HACER UNA VENTA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        return JsonResponse({'cash_date': _date}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def new_bank_transaction(request):
    if request.method == 'POST':
        _bank = request.POST.get('bank-cash')
        _operation = request.POST.get('bank-operation-type')
        _date = request.POST.get('bank-operation-date')
        _total = decimal.Decimal(request.POST.get('bank-total'))
        _code = request.POST.get('bank-operation-code')
        _description = request.POST.get('bank-description')

        bank_obj = Cash.objects.get(id=int(_bank))

        if _total <= 0:
            data = {'error': "Monto incorrecto"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        if _operation == '1':  # deposit
            _type = 'D'
        elif _operation == '2':  # withdrawal
            _type = 'R'
        elif _operation == '3':  # Purchase
            _type = 'R'
        elif _operation == '4':  # Bank withdrawal
            _type = 'R'

        cash_flow_obj = CashFlow(
            transaction_date=_date,
            cash=bank_obj,
            description=_description,
            total=_total,
            operation_type=_operation,
            operation_code=_code,
            user=user_obj,
            type=_type)
        cash_flow_obj.save()

        return JsonResponse({
            'message': 'Operación registrada con exito.',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def new_cash_disbursement(request):
    if request.method == 'POST':
        _cash = request.POST.get('disbursement-cash')
        date = request.POST.get('disbursement-operation-date')
        _total = decimal.Decimal(request.POST.get('disbursement-total'))
        _description = request.POST.get('disbursement-description')
        _operation_method = request.POST.get('operationMethod')
        _igv = request.POST.get('igv', '0.00')
        _sub_total = request.POST.get('subtotal', '0.00')
        _date = ''
        _date_c = ''

        cash_obj = Cash.objects.get(id=int(_cash))

        cash_flow_set = CashFlow.objects.filter(cash=cash_obj, type='A')
        cash_flow_c_set = CashFlow.objects.filter(cash=cash_obj, type='C')

        if cash_flow_set.count() > 0:
            last_cash_flow_obj = cash_flow_set.last()
            _date = last_cash_flow_obj.transaction_date.strftime("%Y-%m-%d")
        if cash_flow_c_set.count() > 0:
            last_cash_flow_c_obj = cash_flow_c_set.last()
            _date_c = last_cash_flow_c_obj.transaction_date.strftime("%Y-%m-%d")

        if _date == _date_c:
            data = {'error': 'NECESITA APERTURAR LA CAJA ANTES DE REGISTRAR UNA OPERACION'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        else:
            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)

            cash_flow_obj = CashFlow(
                created_at=_date,
                transaction_date=_date,
                cash=cash_obj,
                description=_description,
                total=_total,
                operation_type='0',
                igv=_igv,
                subtotal=_sub_total,
                user=user_obj,
                type=_operation_method)
            cash_flow_obj.save()

        # else:
        #     data = {'error': "Caja sin aperturar"}
        #     response = JsonResponse(data)
        #     response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        #     return response

        return JsonResponse({
            'message': 'Operación registrada con exito.',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def new_cash_transfer_to_cash(request):
    if request.method == 'POST':
        _date = request.POST.get('transfer-date')
        _cash_origin = request.POST.get('cash-origin')
        _cash_destiny = request.POST.get('cash-destiny')
        _amount = request.POST.get('transfer-total-amount')
        _concept = request.POST.get('transfer-description')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        # COMPROBANDO QUE LAS CAJAS ESTEN ABIERTAS
        cashflow_set = CashFlow.objects.filter(cash_id=_cash_origin,
                                               transaction_date__date=_date,
                                               type='A')
        if cashflow_set.count() > 0:
            cash_origin_obj = cashflow_set.first().cash
            current_balance = cash_origin_obj.current_balance()

            if decimal.Decimal(_amount) > current_balance:
                data = {
                    'error': "El monto excede al saldo actual de la Caja"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        else:
            data = {
                'error': "No existe una Apertura de Caja, Favor de revisar los Control de Cajas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        cashflow_set = CashFlow.objects.filter(cash_id=_cash_destiny,
                                               transaction_date__date=_date,
                                               type='A')
        if cashflow_set.count() > 0:
            cash_destiny_obj = cashflow_set.first().cash
        else:
            data = {
                'error': "No existe una Apertura de Caja, Favor de revisar los Control de Cajas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        cash_transfer_obj = CashTransfer(status='P')
        cash_transfer_obj.save()

        # GUARDANDO EL ORIGEN
        cash_transfer_route_origin_obj = CashTransferRoute(
            cash_transfer=cash_transfer_obj,
            cash=cash_origin_obj,
            type='O'
        )
        cash_transfer_route_origin_obj.save()

        # GUARDANDO EL DESTINO
        cash_transfer_route_input_obj = CashTransferRoute(
            cash_transfer=cash_transfer_obj,
            cash=cash_destiny_obj,
            type='D'
        )
        cash_transfer_route_input_obj.save()

        # GUARDANDO EL USUARIO
        cash_transfer_action_obj = CashTransferAction(
            cash_transfer=cash_transfer_obj,
            user=user_obj,
            operation='E',
            register_date=_date,
        )
        cash_transfer_action_obj.save()

        # GUARDAMOS LA OPERACION
        cash_flow_output_obj = CashFlow(
            transaction_date=_date,
            cash=cash_origin_obj,
            description=_concept,
            total=_amount,
            operation_type='6',
            user=user_obj,
            cash_transfer=cash_transfer_obj,
            type='S')
        cash_flow_output_obj.save()

        return JsonResponse({
            'message': 'Operación registrada con exito.',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_last_cash_open(cash_id):
    cash_obj = Cash.objects.get(id=cash_id)
    last_cash = CashFlow.objects.filter(cash=cash_obj, type='A').last()
    return last_cash


def new_cash_to_bank(request):
    if request.method == 'POST':
        _date = request.POST.get('deposit-date')
        _cash_origin_deposit = request.POST.get('cash-origin-deposit')
        _current_balance_deposit = request.POST.get('current-balance-deposit')
        _bank_account = request.POST.get('bank-account')
        _amount_deposit = request.POST.get('deposit-amount')
        _description_deposit = request.POST.get('description-deposit')
        _code_operation = request.POST.get('code-operation-deposit')
        user_id = request.user.id
        bank_obj_destiny_deposit = Cash.objects.get(id=int(_bank_account))
        user_obj = User.objects.get(id=user_id)
        last_cash_date = get_last_cash_open(_cash_origin_deposit).transaction_date
        last_cash_open = get_last_cash_open(_cash_origin_deposit)
        las_cash_closed = CashFlow.objects.filter(type='C', cash=last_cash_open.cash,
                                                  transaction_date__date=last_cash_date.date())
        # COMPROBANDO CAJAS ABIERTAS
        if las_cash_closed:
            data = {
                'error': "No existe una Apertura de Caja, Favor de revisar los Control de Cajas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        else:
            cashflow_set = CashFlow.objects.filter(cash=_cash_origin_deposit,
                                                   type='A')
            cash_origin_obj = cashflow_set.first().cash
            current_balance = cash_origin_obj.current_balance()
            if decimal.Decimal(_amount_deposit) > current_balance:
                data = {
                    'error': "El monto excede al saldo actual de la Caja"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        cash_transfer_obj = CashTransfer(status='A')
        cash_transfer_obj.save()

        # GUARDANDO EL ORIGEN - LA CAJA
        cash_transfer_route_origin_obj = CashTransferRoute(
            cash_transfer=cash_transfer_obj,
            cash=cash_origin_obj,
            type='O'
        )
        cash_transfer_route_origin_obj.save()

        # GUARDANDO EL DESTINO - BANCO
        cash_transfer_route_input_obj = CashTransferRoute(
            cash_transfer=cash_transfer_obj,
            cash=bank_obj_destiny_deposit,
            type='D'
        )
        cash_transfer_route_input_obj.save()

        # GUARDANDO EL USUARIO
        cash_transfer_action_obj = CashTransferAction(
            cash_transfer=cash_transfer_obj,
            user=user_obj,
            operation='E',
            register_date=_date,
        )
        cash_transfer_action_obj.save()

        # GUARDAMOS LA OPERACION
        cash_flow_output_obj = CashFlow(
            transaction_date=last_cash_date,
            cash=cash_origin_obj,
            description=_description_deposit,
            total=_amount_deposit,
            operation_type='7',
            user=user_obj,
            cash_transfer=cash_transfer_obj,
            type='S')
        cash_flow_output_obj.save()

        cash_flow_input_obj = CashFlow(
            transaction_date=_date,
            cash=bank_obj_destiny_deposit,
            description=_description_deposit,
            total=_amount_deposit,
            operation_type='7',
            operation_code=_code_operation,
            user=user_obj,
            type='D')
        cash_flow_input_obj.save()

        return JsonResponse({
            'message': 'Operación registrada con exito.',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_bank_control_list(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        other_subsidiary_set = Subsidiary.objects.exclude(id=subsidiary_obj.id)

        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj)
        only_bank_set = cash_set.filter(accounting_account__code__startswith='1041')
        ours_cash_set = Cash.objects.filter(accounting_account__code__startswith='101')
        only_other_bank_set = Cash.objects.filter(accounting_account__code__startswith='1041').exclude(
            subsidiary=subsidiary_obj)

        return render(request, 'accounting/banking_list.html', {
            'formatdate': formatdate,
            'subsidiary_obj': subsidiary_obj,
            'only_bank_set': only_bank_set,
            'ours_cash_set': ours_cash_set,
            'other_subsidiary_set': other_subsidiary_set,
            'only_other_bank_set': only_other_bank_set,
            'choices_operation_types': CashFlow._meta.get_field('operation_type').choices,
        })
    elif request.method == 'POST':
        id_cash = int(request.POST.get('cash'))
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))

        if start_date == end_date:
            cash_flow_set = CashFlow.objects.filter(transaction_date__date=start_date, cash__id=id_cash).order_by(
                'transaction_date')
        else:
            cash_flow_set = CashFlow.objects.filter(transaction_date__date__range=[start_date, end_date],
                                                    cash__id=id_cash).order_by('transaction_date')
        inputs_set = cash_flow_set.filter(type='D').values('cash').annotate(totals=Sum('total'))
        outputs_set = cash_flow_set.filter(type='R').values('cash').annotate(totals=Sum('total'))
        transfers_set = cash_flow_set.filter(type='T').values('cash').annotate(totals=Sum('total'))
        inputs = 0
        if inputs_set:
            inputs = inputs_set.aggregate(r=Coalesce(Sum('total'), 0))['r']
        outputs = 0
        if outputs_set:
            outputs = outputs_set.aggregate(r=Coalesce(Sum('total'), 0))['r']
        transfers = 0
        if transfers_set:
            transfers = transfers_set.aggregate(r=Coalesce(Sum('total'), 0))
        has_rows = False
        if cash_flow_set:
            has_rows = True
        else:
            data = {'error': "No hay operaciones registradas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        tpl = loader.get_template('accounting/banking_grid_list.html')
        context = ({
            'cash_flow_set': cash_flow_set,
            'has_rows': has_rows,
            'inputs': round(float(inputs), 2),
            'outputs': round(float(outputs), 2),
            'transfers': round(float(transfers), 2),
            # 'current_balance': Cash.objects.get(id=id_cash).current_balance()
            'current_balance': round(float(inputs - outputs), 2)
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_transfer_bank(request):
    if request.method == 'POST':

        _subsidiary_origin = request.POST.get('transfer-subsidiary-origin')
        _bank_origin = request.POST.get('transfer-bank-origin')
        _subsidiary_destiny = request.POST.get('transfer-subsidiary-destiny')
        _bank_destiny = request.POST.get('transfer-bank-destiny')

        _total = decimal.Decimal(request.POST.get('transfer-total'))
        _description = request.POST.get('transfer-description')
        _operation_code = request.POST.get('transfer-operation-code')
        _date = request.POST.get('transfer-date')

        bank_origin_obj = Cash.objects.get(id=int(_bank_origin))
        bank_destiny_obj = Cash.objects.get(id=int(_bank_destiny))

        if _total <= 0:
            data = {'error': "Monto incorrecto"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        cash_transfer_obj = CashTransfer(status='A')
        cash_transfer_obj.save()

        cash_transfer_route_origin_obj = CashTransferRoute(
            cash_transfer=cash_transfer_obj,
            cash=bank_origin_obj,
            type='O'
        )
        cash_transfer_route_origin_obj.save()

        cash_transfer_route_input_obj = CashTransferRoute(
            cash_transfer=cash_transfer_obj,
            cash=bank_destiny_obj,
            type='D'
        )
        cash_transfer_route_input_obj.save()

        cash_transfer_action_obj = CashTransferAction(
            cash_transfer=cash_transfer_obj,
            user=user_obj,
            operation='E',
            register_date=_date,
        )
        cash_transfer_action_obj.save()

        cash_flow_output_obj = CashFlow(
            transaction_date=_date,
            cash=bank_origin_obj,
            description=_description,
            total=_total,
            operation_type='5',
            operation_code=_operation_code,
            user=user_obj,
            cash_transfer=cash_transfer_obj,
            type='R')
        cash_flow_output_obj.save()

        cash_flow_input_obj = CashFlow(
            transaction_date=_date,
            cash=bank_destiny_obj,
            description=_description,
            total=_total,
            operation_type='5',
            operation_code=_operation_code,
            user=user_obj,
            type='D')
        cash_flow_input_obj.save()

        return JsonResponse({
            'message': 'Operación registrada con exito.',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_confirm_cash_to_cash_transfer(request):
    if request.method == 'GET':
        # pk = request.GET.get('pk', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        cash_transfer_set = CashTransfer.objects.filter(status='P')

        t = loader.get_template('accounting/confirm_cash_transfers.html')
        c = ({
            'cash_transfer_set': cash_transfer_set,
            'subsidiary_obj': subsidiary_obj,
        })
        return JsonResponse({
            'success': True,
            'grid': t.render(c, request),
        })


def accept_cash_to_cash_transfer(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        cash_transfer_obj = CashTransfer.objects.get(id=int(pk))
        cash_destiny_obj = cash_transfer_obj.get_destiny()
        cash_origin_obj = cash_transfer_obj.get_origin()

        cash_flow_origin_set = CashFlow.objects.filter(cash=cash_origin_obj).last()

        cash_origin_obj_date = cash_flow_origin_set.transaction_date.date()

        cash_flow_destiny_set = CashFlow.objects.filter(cash=cash_destiny_obj, type='A')

        if cash_flow_destiny_set.count() == 0:
            data = {
                'error': "No existe una Apertura de Caja, Favor de revisar los Control de Cajas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if cash_flow_destiny_set:
            last_cash_flow_destiny_obj = cash_flow_destiny_set.last()
            check_closed = CashFlow.objects.filter(type='C', cash=cash_destiny_obj,
                                                   transaction_date__date=last_cash_flow_destiny_obj.transaction_date.date())

            if check_closed:
                data = {
                    'error': "Aperture caja de destino"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            else:
                cash_transfer_obj.status = 'A'
                cash_transfer_obj.save()

                cash_transfer_action_set = CashTransferAction.objects.filter(cash_transfer=cash_transfer_obj,
                                                                             operation='A')

                if not cash_transfer_action_set.exists():
                    cash_transfer_action_obj = CashTransferAction(
                        cash_transfer=cash_transfer_obj,
                        user=user_obj,
                        operation='A',
                        register_date=formatdate,
                    )
                    cash_transfer_action_obj.save()

                    cash_flow_origin_obj = CashFlow.objects.get(cash=cash_origin_obj, cash_transfer=cash_transfer_obj)
                    cash_flow_input_obj = CashFlow(
                        transaction_date=cash_origin_obj_date,
                        cash=cash_destiny_obj,
                        description=cash_flow_origin_obj.description,
                        total=cash_flow_origin_obj.total,
                        operation_type='6',
                        user=user_obj,
                        type='E')
                    cash_flow_input_obj.save()
        else:
            data = {
                'error': "No existe una Apertura de Caja, Favor de revisar los Control de Cajas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
    return JsonResponse({'success': True, }, status=HTTPStatus.OK)


def desist_cash_to_cash_transfer(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        cash_transfer_obj = CashTransfer.objects.get(id=int(pk))
        cash_transfer_obj.status = 'C'
        cash_transfer_obj.save()

        cash_transfer_action_obj = CashTransferAction(
            cash_transfer=cash_transfer_obj,
            user=user_obj,
            operation='C',
            register_date=formatdate,
        )
        cash_transfer_action_obj.save()

        cash_destiny_obj = cash_transfer_obj.get_destiny()
        cash_origin_obj = cash_transfer_obj.get_origin()

        cash_flow_origin_obj = CashFlow.objects.get(cash=cash_origin_obj, cash_transfer=cash_transfer_obj)
        cash_flow_input_obj = CashFlow(
            transaction_date=formatdate,
            cash=cash_origin_obj,
            description=str(
                'SE CANCELO LA OPERACIÓN: ' + cash_flow_origin_obj.description + ' POR EL USUARIO: ' + user_obj.worker_set.last().employee.full_name()),
            total=cash_flow_origin_obj.total,
            operation_type='6',
            user=user_obj,
            type='E')
        cash_flow_input_obj.save()

        return JsonResponse({
            'success': True,
        }, status=HTTPStatus.OK)


def new_bank_to_cash_transfer(request):
    if request.method == 'POST':
        _date = request.POST.get('btc-date')
        _bank_origin = request.POST.get('btc-bank-origin')
        _cash_destiny = request.POST.get('btc-cash-destiny')
        _current_balance = request.POST.get('btc-current-balance')
        _total = request.POST.get('btc-total')
        _description = request.POST.get('btc-description')

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        bank_origin_obj = Cash.objects.get(id=int(_bank_origin))
        cash_destiny_obj = Cash.objects.get(id=int(_cash_destiny))

        return JsonResponse({
            'message': 'Operación registrada con exito.',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_cash_report(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj)
        only_cash_set = cash_set.filter(accounting_account__code__startswith='101')

        cash_all_set = Cash.objects.filter(accounting_account__code__startswith='101').exclude(
            subsidiary=subsidiary_obj)

        accounts_banks_set = Cash.objects.filter(accounting_account__code__startswith='104')

        return render(request, 'accounting/cash_queries.html', {
            'formatdate': formatdate,
            'only_cash_set': only_cash_set,
            'cash_all_set': cash_all_set,
            'accounts_banks_set': accounts_banks_set,
            'choices_operation_types': CashFlow._meta.get_field('operation_type').choices,
        })


def get_cash_by_dates(request):
    if request.method == 'GET':
        cash_id = request.GET.get('cash_id', '')
        start_date = request.GET.get('start-date')
        end_date = request.GET.get('end-date')
        cash_flow_set = CashFlow.objects.filter(transaction_date__date__range=[start_date, end_date],
                                                cash__id=cash_id, type='A').order_by('transaction_date')

    return JsonResponse({
        'grid': get_dict_cash(cash_flow_set),
    }, status=HTTPStatus.OK)


def get_dict_cash(cash_flow_set):
    sum_total_inputs_dates = 0
    sum_total_outputs_dates = 0
    sum_total_balance_dates = 0
    dictionary = []
    for g in cash_flow_set:
        _return_inputs = g.return_inputs()
        _return_outputs = g.return_outputs()
        _return_balance = g.return_balance()
        sum_total_inputs_dates = sum_total_inputs_dates + _return_inputs
        sum_total_outputs_dates = sum_total_outputs_dates + _return_outputs
        sum_total_balance_dates = sum_total_balance_dates + _return_balance
        header = {
            'cash': g.cash,
            'date': g.transaction_date,
            'rowspan': g.return_roses(),
            'sum_total_in': str(round(_return_inputs, 2)).replace(',', '.'),
            'sum_total_outs': str(round(_return_outputs, 2)).replace(',', '.'),
            'sum_total_balance': str(round(g.return_balance(), 2)).replace(',', '.'),
            'body': []
        }

        transaction_date = g.transaction_date.date()
        flow_set = CashFlow.objects.filter(cash=g.cash, transaction_date__date=transaction_date)
        other_details = flow_set.exclude(type__in=['A', 'C']).order_by('id')
        first_detail = flow_set.filter(type='A')
        last_detail = flow_set.filter(type='C')

        # details = first_detail.union(other_details)
        # details = details.union(last_detail)
        if first_detail:
            body = add_cash_flow_to_dictionary(first_detail.first())
            header.get('body').append(body)
        for cf in other_details:
            body = add_cash_flow_to_dictionary(cf)
            header.get('body').append(body)
        if last_detail:
            body = add_cash_flow_to_dictionary(last_detail.last())
            header.get('body').append(body)
        dictionary.append(header)

    tpl = loader.get_template('accounting/cash_queries_grid.html')
    context = ({
        'dictionary': dictionary,
        'rowspan': len(dictionary),
        'sum_total_inputs_dates': sum_total_inputs_dates,
        'sum_total_outputs_dates': sum_total_outputs_dates,
        'sum_total_balance_dates': sum_total_balance_dates,

    })
    return tpl.render(context)


def add_cash_flow_to_dictionary(cf):
    body = {
        'id': cf.id,
        'date': cf.transaction_date,
        'description': cf.description,
        'serial': cf.serial,
        'nro': cf.n_receipt,
        'document_type': cf.get_document_type_attached_display(),
        'type': cf.get_type_display(),
        'igv': str(round(cf.igv, 2)).replace(',', '.'),
        'subtotal': str(round(cf.subtotal, 2)).replace(',', '.'),
        'total': str(round(cf.total, 2)).replace(',', '.'),
        'order_set': [],
        'user': cf.user,
        'operation_type': cf.get_operation_type_display(),
        'rowspan': cf.return_roses()
    }
    o = cf.order
    if o:
        order_set = {
            'id': o.id,
            'type': o.get_type_display(),
            'client': o.client.names,
            'date': o.create_at,
            'distribution_mobil': [],
            'order_detail_set': [],
            'status': o.get_status_display(),
            'total': o.total
        }
        if o.distribution_mobil:
            license_plate = '-'
            pilot = '-'
            license_plate = o.distribution_mobil.truck.license_plate
            pilot = o.distribution_mobil.pilot.full_name
            distribution_mobil = {
                'license_plate': license_plate,
                'pilot': pilot,
            }
            order_set.get('distribution_mobil').append(distribution_mobil)

        for d in OrderDetail.objects.filter(order=o):
            order_detail = {
                'id': d.id,
                'product': d.product.name,
                'unit': d.unit.name,
                'quantity_sold': d.quantity_sold,
                'price_unit': d.price_unit,
                'multiply': d.multiply,
                'return_loan': d.return_loan(),
                'repay_loan': d.repay_loan(),
                'repay_loan_ball': d.repay_loan_ball(),
                'repay_loan_with_vouchers': d.repay_loan_with_vouchers(),
                'ball_changes': d.ball_changes(),
            }
            order_set.get('order_detail_set').append(order_detail)
        body.get('order_set').append(order_set)
    return body


def update_transaction_date_in_cash_flow(request):
    if request.method == 'POST':
        current_cash_flow = int(request.POST.get('cash-flow'))
        current_date_text = str(request.POST.get('cash-flow-current-date'))
        new_date_text = str(request.POST.get('cash-flow-new-date'))
        reason_text = str(request.POST.get('reason-text')).strip()
        current_cash_flow_obj = CashFlow.objects.get(id=current_cash_flow)
        cash_obj = current_cash_flow_obj.cash
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        current_date = datetime.strptime(current_date_text, '%Y-%m-%d')
        new_date = datetime.strptime(new_date_text, '%Y-%m-%d')

        if new_date < current_date:
            try:
                new_cash_flow_open = CashFlow.objects.get(cash=cash_obj, transaction_date__date=new_date.date(),
                                                          type='A')
            except CashFlow.DoesNotExist:
                data = {'error': 'No se encontro una caja en la fecha especificada.'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            current_cash_flow_obj.transaction_date = new_date
            current_cash_flow_obj.save()
            scan_and_reassign_cash_flow(cash_obj, new_cash_flow_open)

        elif new_date > current_date:
            try:
                current_cash_flow_open = CashFlow.objects.get(cash=cash_obj, transaction_date__date=current_date.date(),
                                                              type='A')
            except CashFlow.DoesNotExist:
                data = {'error': 'No se encontro una caja en la fecha especificada.'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            current_cash_flow_obj.transaction_date = new_date
            current_cash_flow_obj.save()

            scan_and_reassign_cash_flow(cash_obj, current_cash_flow_open)

        cash_flow_log_obj = CashFlowLog(cash_flow=current_cash_flow_obj, user=user_obj, reason=reason_text)
        cash_flow_log_obj.save()

        start_date = str(request.POST.get('query-start-date'))
        end_date = str(request.POST.get('query-end-date'))
        cash_flow_set = CashFlow.objects.filter(transaction_date__date__range=[start_date, end_date],
                                                cash__id=cash_obj.id, type='A').order_by('transaction_date')
        return JsonResponse({
            'success': True,
            'message': 'El cliente se asocio correctamente.',
            'grid': get_dict_cash(cash_flow_set),
            # 'grid': get_dict_orders(order_set, client_obj=client_obj, is_pdf=False),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def scan_and_reassign_cash_flow(cash_obj=None, cash_flow_open=None):
    last_cash_flow_open = cash_flow_open.return_last_cash_open()

    cash_flow_set = CashFlow.objects.filter(
        transaction_date__date__range=[cash_flow_open.transaction_date.date(),
                                       last_cash_flow_open.transaction_date.date()],
        cash=cash_obj, type='A'
    ).order_by('transaction_date')
    cf_total = cash_flow_open.total
    for cf in cash_flow_set:
        cfo = CashFlow.objects.get(cash=cash_obj, transaction_date__date=cf.transaction_date.date(), type='A')
        cfo.total = cf_total
        cfo.save()
        cf_inputs = cf.return_inputs()
        cf_ouputs = cf.return_outputs()
        cf_total = cfo.total + cf_inputs + cf_ouputs
        cfc_set = CashFlow.objects.filter(cash=cash_obj, transaction_date__date=cf.transaction_date.date(), type='C')
        if cfc_set:
            cfc = cfc_set.last()
            cfc.total = cf_total
            cfc.save()


def update_description_cash(request):
    if request.method == 'GET':
        cash_flow_id = int(request.GET.get('cash_flow_id'))
        description = str(request.GET.get('description'))

        cash_flow_obj = CashFlow.objects.get(id=cash_flow_id)
        cash_flow_obj.description = description
        cash_flow_obj.save()

        return JsonResponse({
            'success': True,
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_modal_edit(request):
    if request.method == 'GET':
        pk = int(request.GET.get('pk'))

        cash_flow_obj = CashFlow.objects.get(id=pk)

        tpl = loader.get_template('accounting/modal_edit_bank.html')
        context = ({
            'c': cash_flow_obj,
        })

        return JsonResponse({
            'grid': tpl.render(context),
            'success': True,
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def update_description_and_date_cash_bank(request):
    if request.method == 'GET':
        cash_flow_id = int(request.GET.get('cash_flow_id'))
        description = str(request.GET.get('description'))
        date = str(request.GET.get('date'))

        cash_flow_obj = CashFlow.objects.get(id=cash_flow_id)
        cash_flow_obj.description = description
        cash_flow_obj.transaction_date = date
        cash_flow_obj.save()

        return JsonResponse({
            'success': 'Cambios realizados con éxito',
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})
