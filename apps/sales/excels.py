from collections import defaultdict

import pandas as pd
from django.db.models import Q, Subquery, Sum, F, Value, FloatField, OuterRef, Avg, Prefetch, Exists
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from ..sales.models import Product, ProductStore, ProductDetail, Kardex, SubsidiaryStore, ProductSerial
from ..buys.models import PurchaseDetail
from datetime import datetime as dt, timedelta, datetime
import xlsxwriter


def export_all_products(request, start_date=None, end_date=None):
    kardex_by_product = defaultdict(list)

    TYPE_CHOICES = {
        'E': 'Entrada',
        'S': 'Salida',
        'C': 'Inventario inicial',
        'CI': 'Cuadre de Inventario',
    }

    product_queryset = Product.objects.filter(is_enabled=True).exclude(id__in=[71, 145, 146])
    brand_id = request.GET.get('brand', '0')
    if brand_id and brand_id != '0':
        try:
            product_queryset = product_queryset.filter(product_brand_id=int(brand_id))
        except (ValueError, TypeError):
            pass

    for p in product_queryset.order_by('id'):
    # for p in Product.objects.filter(id=386):
        product = p.name
        product_store_set = ProductStore.objects.filter(product=p.id, subsidiary_store__id=1)
        if product_store_set.exists():
            kardex_set = Kardex.objects.filter(product_store=product_store_set.last(),
                                               create_at__date__range=[start_date, end_date]).values(
                'id',
                'create_at',
                'operation',
                'quantity',
                'price_unit',
                'price_total',
                'order_detail__order',
                'purchase_detail__purchase',
                'remaining_quantity',
                'remaining_price',
                'remaining_price_total',
            ).order_by('id')
            if kardex_set.exists():
                for k in kardex_set:
                    operation = ''
                    date_without_tz = k['create_at'].replace(tzinfo=None)
                    if k['order_detail__order'] is not None:
                        operation = 'Venta'
                    elif k['purchase_detail__purchase'] is not None:
                        operation = 'Compra'
                    kardex_by_product[product].append({
                        'id': k['id'],
                        'date': date_without_tz,
                        'operation': operation,
                        'type': k['operation'],
                        'type_display': TYPE_CHOICES.get(k['operation'], k['operation']),
                        'quantity': k['quantity'],
                        'price_unit': k['price_unit'],
                        'price_total': k['price_total'],
                        'order': k['order_detail__order'],
                        'purchase': k['order_detail__order'],
                        'remaining_quantity': k['remaining_quantity'],
                        'remaining_price': k['remaining_price'],
                        'remaining_price_total': k['remaining_price_total'],
                    })
            else:
                kardex_by_product[product].append({
                    'id': '',
                    'date': '',
                    'operation': '',
                    'type': '',
                    'type_display': '',
                    'quantity': '',
                    'price_unit': '',
                    'price_total': '',
                    'order': '',
                    'purchase': '',
                    'remaining_quantity': '',
                    'remaining_price': '',
                    'remaining_price_total': '',
                })
        else:
            kardex_by_product[product].append({
                'id': '',
                'date': '',
                'operation': '',
                'type': '',
                'type_display': '',
                'quantity': '',
                'price_unit': '',
                'price_total': '',
                'order': '',
                'purchase': '',
                'remaining_quantity': '',
                'remaining_price': '',
                'remaining_price_total': '',
            })
    # for k in kardex_entries:
    #     operation = ''
    #     product = k['product_store__product__name']
    #     date_without_tz = k['create_at'].replace(tzinfo=None)
    #     if k['order_detail__order'] is not None:
    #         operation = 'Venta'
    #     elif k['purchase_detail__purchase'] is not None:
    #         operation = 'Compra'
    #
    #     kardex_by_product[product].append({
    #         'id': k['id'],
    #         'date': date_without_tz,
    #         'operation': operation,
    #         'type': k['operation'],
    #         'type_display': TYPE_CHOICES.get(k['operation'], k['operation']),
    #         'quantity': k['quantity'],
    #         'price_unit': k['price_unit'],
    #         'price_total': k['price_total'],
    #         'order': k['order_detail__order'],
    #         'purchase': k['order_detail__order'],
    #         'remaining_quantity': k['remaining_quantity'],
    #         'remaining_price': k['remaining_price'],
    #         'remaining_price_total': k['remaining_price_total'],
    #     })
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Kardex_de_{}_a_{}.xlsx'.format(start_date, end_date)

    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        workbook = writer.book

        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#DCE6F1', 'border': 1,
                                             'font_name': 'Arial', 'font_size': 10})
        merge_format = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#DCE6F1',
                                            'font_name': 'Arial', 'font_size': 10})

        for product, entries in kardex_by_product.items():
            sheet_name = sanitize_sheet_name(truncate_sheet_name(product))
            unique_sheet_name = get_unique_sheet_name(sheet_name, workbook)
            worksheet = workbook.add_worksheet(unique_sheet_name)

            worksheet.merge_range('A1:C1', 'Descripción', merge_format)
            worksheet.merge_range('D1:F1', 'Entradas', merge_format)
            worksheet.merge_range('G1:I1', 'Salidas', merge_format)
            worksheet.merge_range('J1:L1', 'Saldo', merge_format)

            headers = [
                'Fecha', 'Operación', 'Tipo',
                'Cantidad', 'Precio Unitario', 'Precio Total',
                'Cantidad', 'Precio Unitario', 'Precio Total',
                'Cantidad Restante', 'Precio Restante', 'Precio Total Restante'
            ]

            worksheet.write_row(1, 0, headers, header_format)

            # worksheet.set_column('A:A', 10)  # Columna Id
            worksheet.set_column('A:A', 10)  # Columna Fecha
            worksheet.set_column('B:B', 10)  # Columna OPERACION
            worksheet.set_column('C:C', 10)  # Columna TIPO

            worksheet.set_column('D:D', 10)  # Columna CANTIDAD
            worksheet.set_column('E:E', 15)  # Columna Precio unitario
            worksheet.set_column('F:F', 15)  # Columna Precio total

            worksheet.set_column('G:G', 10)  # Columna CANTIDAD
            worksheet.set_column('H:H', 15)  # Columna Precio unitario
            worksheet.set_column('I:I', 15)  # Columna Precio total

            worksheet.set_column('J:J', 17)  # Columna cantidad restante
            worksheet.set_column('K:K', 17)  # Columna Precio restante
            worksheet.set_column('L:L', 20)  # Columna Precio total restante

            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center', 'font_name': 'Arial',
                                               'font_size': 8})
            numeric_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right', 'font_name': 'Arial',
                                                  'font_size': 8})

            for row_num, e in enumerate(entries, start=1):
                if all_fields_empty(e):
                    continue
                # worksheet.write(row_num + 1, 0, e['id'])
                worksheet.write_datetime(row_num + 1, 0, e['date'], date_format)
                worksheet.write(row_num + 1, 1, e['operation'], workbook.add_format({'align': 'center', 'font_size': 8,
                                                                                     'font_name': 'Arial', }))
                worksheet.write(row_num + 1, 2, e['type_display'], workbook.add_format({'align': 'center', 'font_size': 8,
                                                                                        'font_name': 'Arial'}))
                if e['type'] == 'E':
                    worksheet.write(row_num + 1, 3, e['quantity'], numeric_format)
                    worksheet.write(row_num + 1, 4, e['price_unit'], numeric_format)
                    worksheet.write(row_num + 1, 5, e['price_total'], numeric_format)
                elif e['type'] == 'S':
                    worksheet.write(row_num + 1, 6, e['quantity'], numeric_format)
                    worksheet.write(row_num + 1, 7, e['price_unit'], numeric_format)
                    worksheet.write(row_num + 1, 8, e['price_total'], numeric_format)

                worksheet.write(row_num + 1, 9, e['remaining_quantity'], numeric_format)
                worksheet.write(row_num + 1, 10, e['remaining_price'], numeric_format)
                worksheet.write(row_num + 1, 11, e['remaining_price_total'], numeric_format)

    return response


def truncate_sheet_name(name, max_length=31):
    return name[:max_length]


def all_fields_empty(entry):
    return all(value == '' for value in entry.values())


def sanitize_sheet_name(sheet_name):
    invalid_chars = '[]:*?/\\'
    for char in invalid_chars:
        sheet_name = sheet_name.replace(char, '-')
    return sheet_name[:31]


def get_unique_sheet_name(sheet_name, workbook):
    original_name = sheet_name
    counter = 1
    while sheet_name.lower() in (s.name.lower() for s in workbook.worksheets()):
        sheet_name = f"{original_name[:29]}-{counter}"  # Deja espacio para el sufijo numérico
        counter += 1
    return sheet_name


def report_kardex_by_date(request, date=None):
    print(date)
    report_data = []
    product_queryset = Product.objects.filter(is_enabled=True)
    brand_id = request.GET.get('brand', '0')
    if brand_id and brand_id != '0':
        try:
            product_queryset = product_queryset.filter(product_brand_id=int(brand_id))
        except (ValueError, TypeError):
            pass
    for idx, p in enumerate(product_queryset.order_by('id'), start=1):
        product_store_set = ProductStore.objects.filter(product=p.id, subsidiary_store__id=1)
        if product_store_set.exists():
            product_store = product_store_set.last()

            kardex = Kardex.objects.filter(
                product_store=product_store,
                create_at__date__lte=date
            ).order_by('-create_at').values(
                'remaining_quantity',
                'remaining_price',
                'remaining_price_total'
            ).first()

            if kardex:
                report_data.append({
                    'N°': idx,
                    'Producto': p.name,
                    'Cantidad Restante': float(kardex['remaining_quantity']),
                    'Precio Restante con IGV': float(kardex['remaining_price']),
                    'Precio Total Restante con IGV': float(kardex['remaining_price_total']),
                    'Precio Restante sin IGV': float(kardex['remaining_price']) / 1.18,
                    'Precio Total Restante sin IGV': float(kardex['remaining_price_total']) / 1.18
                })
            else:
                report_data.append({
                    'N°': idx,
                    'Producto': p.name,
                    'Cantidad Restante': 0.0,
                    'Precio Restante con IGV': 0.0,
                    'Precio Total Restante con IGV': 0.0,
                    'Precio Restante sin IGV': 0.0,
                    'Precio Total Restante sin IGV': 0.0
                })

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=Resumen_Kardex_{date}.xlsx'

    df = pd.DataFrame(report_data)

    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Kardex', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Kardex']

        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#DCE6F1',
            'border': 1,
            'font_name': 'Arial',
            'font_size': 10
        })

        text_format = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 9,
            'border': 1,
            'align': 'left'
        })

        numeric_format = workbook.add_format({
            'num_format': '_-* #,##0.00_-;-* #,##0.00_-;_-* "-"??_-;_-@_-',
            'align': 'right',
            'font_name': 'Arial',
            'font_size': 9,
            'border': 1
        })

        # Escribir encabezados con formato
        for col_num, column_name in enumerate(df.columns):
            worksheet.write(0, col_num, column_name, header_format)

        # Ajustar anchos de columna
        worksheet.set_column('A:A', 8, workbook.add_format({'align': 'right', 'font_size': 8, 'font_name': 'Arial', }))     # N°
        worksheet.set_column('B:B', 73, text_format)     # Producto
        worksheet.set_column('C:C', 17, numeric_format)  # Cantidad Restante
        worksheet.set_column('D:D', 23, numeric_format)  # Precio Restante con IGV
        worksheet.set_column('E:E', 28, numeric_format)  # Precio Total Restante con IGV
        worksheet.set_column('F:F', 22, numeric_format)  # Precio Restante sin IGV
        worksheet.set_column('G:G', 28, numeric_format)  # Precio Total Restante sin IGV

    return response


def get_products_for_catalog_export(criteria=None, value=None, brand_id=None):
    """Misma lógica de filtrado que la grilla de productos."""
    last_purchase_date = PurchaseDetail.objects.filter(
        product=OuterRef('id'),
        purchase__status='A'
    ).order_by('-purchase__purchase_date').values('purchase__purchase_date')[:1]

    last_purchase_quantity = PurchaseDetail.objects.filter(
        product=OuterRef('id'),
        purchase__status='A'
    ).order_by('-purchase__purchase_date').values('quantity')[:1]

    has_serials = Exists(
        ProductSerial.objects.filter(product_store__product=OuterRef('id'))
    )

    last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]

    base_qs = Product.objects.filter(is_enabled=True).select_related(
        'product_family', 'product_brand'
    ).annotate(
        last_purchase_date=Subquery(last_purchase_date),
        last_purchase_quantity=Subquery(last_purchase_quantity),
        has_serials=has_serials,
    ).prefetch_related(
        Prefetch(
            'productstore_set',
            queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
            .exclude(subsidiary_store__subsidiary=3)
            .annotate(
                last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
            ),
        ),
        Prefetch(
            'productdetail_set',
            queryset=ProductDetail.objects.select_related('unit').order_by('id'),
        ),
    )

    criteria = (criteria or '').strip()
    value = (value or '').strip()

    if criteria == 'name_contains' and value:
        full_query = None
        for term in value.split():
            q = Q(name__icontains=term) | Q(product_brand__name__icontains=term)
            full_query = q if full_query is None else full_query & q
        return base_qs.filter(full_query).order_by('id')

    if brand_id:
        return base_qs.filter(product_brand_id=brand_id).order_by('id')

    if criteria == 'name' and value:
        return base_qs.filter(name__icontains=value).order_by('id')

    return base_qs.order_by('id')


def _format_excel_date(value):
    if not value:
        return ''
    if hasattr(value, 'strftime'):
        try:
            return value.strftime('%d/%m/%Y')
        except (ValueError, TypeError):
            return str(value)
    return str(value)


def export_product_catalog(request):
    criteria = request.GET.get('criteria', 'all')
    value = request.GET.get('value', '')
    brand = request.GET.get('brand', '0')
    brand_id = None
    if brand and brand != '0':
        try:
            brand_id = int(brand)
        except (ValueError, TypeError):
            brand_id = None

    products = get_products_for_catalog_export(criteria, value, brand_id)
    export_date = datetime.now().strftime('%d/%m/%Y %H:%M')

    filename = f'Catalogo_Productos_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'

    workbook = xlsxwriter.Workbook(response, {'in_memory': True})
    worksheet = workbook.add_worksheet('Catálogo')

    title_fmt = workbook.add_format({
        'bold': True, 'font_size': 16, 'font_color': '#FFFFFF', 'bg_color': '#1a2332',
        'align': 'left', 'valign': 'vcenter', 'font_name': 'Calibri',
    })
    subtitle_fmt = workbook.add_format({
        'font_size': 10, 'font_color': '#64748b', 'italic': True, 'font_name': 'Calibri',
    })
    header_fmt = workbook.add_format({
        'bold': True, 'font_size': 10, 'font_color': '#FFFFFF', 'bg_color': '#2563eb',
        'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Calibri',
    })
    text_fmt = workbook.add_format({
        'font_size': 9, 'align': 'left', 'valign': 'vcenter', 'border': 1,
        'font_name': 'Calibri', 'text_wrap': True,
    })
    text_alt_fmt = workbook.add_format({
        'font_size': 9, 'align': 'left', 'valign': 'vcenter', 'border': 1,
        'font_name': 'Calibri', 'text_wrap': True, 'bg_color': '#f8fafc',
    })
    center_fmt = workbook.add_format({
        'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Calibri',
    })
    center_alt_fmt = workbook.add_format({
        'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1,
        'font_name': 'Calibri', 'bg_color': '#f8fafc',
    })
    money_fmt = workbook.add_format({
        'num_format': '"S/ "#,##0.00', 'font_size': 9, 'align': 'right', 'valign': 'vcenter',
        'border': 1, 'font_name': 'Calibri',
    })
    money_alt_fmt = workbook.add_format({
        'num_format': '"S/ "#,##0.00', 'font_size': 9, 'align': 'right', 'valign': 'vcenter',
        'border': 1, 'font_name': 'Calibri', 'bg_color': '#f8fafc',
    })
    stock_fmt = workbook.add_format({
        'num_format': '#,##0.##', 'font_size': 9, 'align': 'right', 'valign': 'vcenter',
        'border': 1, 'font_name': 'Calibri', 'bold': True,
    })
    stock_alt_fmt = workbook.add_format({
        'num_format': '#,##0.##', 'font_size': 9, 'align': 'right', 'valign': 'vcenter',
        'border': 1, 'font_name': 'Calibri', 'bold': True, 'bg_color': '#f8fafc',
    })
    int_fmt = workbook.add_format({
        'num_format': '0', 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'font_name': 'Calibri',
    })
    int_alt_fmt = workbook.add_format({
        'num_format': '0', 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'font_name': 'Calibri', 'bg_color': '#f8fafc',
    })

    headers = [
        'N°', 'Código', 'Producto', 'Precio compra', 'Fecha precio compra',
        'Stock mínimo', 'Stock máximo', 'Almacén', 'Stock actual',
    ]

    worksheet.set_row(0, 28)
    worksheet.merge_range(0, 0, 0, len(headers) - 1, 'Catálogo de productos — Inventario y precios', title_fmt)
    worksheet.set_row(1, 18)
    worksheet.merge_range(
        1, 0, 1, len(headers) - 1,
        f'Generado: {export_date}  |  Total productos: {products.count()}',
        subtitle_fmt,
    )

    header_row = 3
    worksheet.set_row(header_row, 22)
    for col, title in enumerate(headers):
        worksheet.write(header_row, col, title, header_fmt)

    data_row = header_row + 1
    row_index = 0

    for product in products:
        details = list(product.productdetail_set.all())
        detail = details[0] if details else None
        price = float(detail.price_purchase) if detail else None
        price_date = _format_excel_date(detail.update_at if detail else None)
        code = str(product.code).zfill(6) if product.code else ''
        stock_min = product.stock_min or 0
        stock_max = product.stock_max or 0
        stores = list(product.productstore_set.all())

        store_rows = stores if stores else [None]

        for store in store_rows:
            alt = row_index % 2 == 1
            t_fmt = text_alt_fmt if alt else text_fmt
            c_fmt = center_alt_fmt if alt else center_fmt
            m_fmt = money_alt_fmt if alt else money_fmt
            s_fmt = stock_alt_fmt if alt else stock_fmt
            i_fmt = int_alt_fmt if alt else int_fmt

            worksheet.write(data_row, 0, row_index + 1, c_fmt)
            worksheet.write(data_row, 1, code, c_fmt)
            worksheet.write(data_row, 2, product.name.upper(), t_fmt)

            if price is not None:
                worksheet.write_number(data_row, 3, price, m_fmt)
            else:
                worksheet.write(data_row, 3, '—', c_fmt)

            worksheet.write(data_row, 4, price_date or '—', c_fmt)
            worksheet.write_number(data_row, 5, stock_min, i_fmt)
            worksheet.write_number(data_row, 6, stock_max, i_fmt)

            if store:
                worksheet.write(data_row, 7, store.subsidiary_store.name, t_fmt)
                worksheet.write_number(data_row, 8, float(store.stock or 0), s_fmt)
            else:
                worksheet.write(data_row, 7, '—', c_fmt)
                worksheet.write(data_row, 8, 0, s_fmt)

            data_row += 1
            row_index += 1

    last_row = max(data_row - 1, header_row)
    worksheet.autofilter(header_row, 0, last_row, len(headers) - 1)
    worksheet.freeze_panes(header_row + 1, 0)

    worksheet.set_column('A:A', 5)
    worksheet.set_column('B:B', 10)
    worksheet.set_column('C:C', 42)
    worksheet.set_column('D:D', 14)
    worksheet.set_column('E:E', 16)
    worksheet.set_column('F:G', 12)
    worksheet.set_column('H:H', 22)
    worksheet.set_column('I:I', 12)

    workbook.close()
    return response
