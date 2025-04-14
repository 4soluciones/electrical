from collections import defaultdict

import pandas as pd
from django.db.models import Q, Subquery, Sum, F, Value, FloatField, OuterRef, Avg, Prefetch
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from ..sales.models import Product, ProductStore, ProductDetail, Kardex, SubsidiaryStore
from datetime import datetime as dt, timedelta, datetime


def export_all_products(request, start_date=None, end_date=None):
    kardex_by_product = defaultdict(list)

    TYPE_CHOICES = {
        'E': 'Entrada',
        'S': 'Salida',
        'C': 'Inventario inicial',
        'CI': 'Cuadre de Inventario',
    }

    for p in Product.objects.filter(is_enabled=True).exclude(id__in=[71, 145, 146]).order_by('id'):
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
    for idx, p in enumerate(Product.objects.filter(is_enabled=True).order_by('id'), start=1):
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
