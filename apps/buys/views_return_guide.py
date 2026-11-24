import decimal
import json
from datetime import datetime, time
from http import HTTPStatus

from django.db import connection, transaction
from django.db.models import Max, Q
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.comercial.models import Guide, GuideDetail
from apps.hrm.models import District
from apps.hrm.views import get_subsidiary_by_user
from apps.sales.api_FACT import return_guide_recipient_error, send_guide_fact
from apps.sales.models import Product, ProductDetail, ProductSerial, Supplier, Unit

from .models import Purchase, ReturnGuide, ReturnGuideItem

_SCHEMA_READY = False


def ensure_return_guide_schema():
    """Crea las tablas nuevas si aun no existen.

    El repositorio no versiona migraciones, asi que la primera apertura del
    modulo deja el esquema listo sin tocar las tablas que ya estan en uso.
    """
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    existing = set(connection.introspection.table_names())
    with connection.schema_editor() as schema_editor:
        if ReturnGuide._meta.db_table not in existing:
            schema_editor.create_model(ReturnGuide)
        if ReturnGuideItem._meta.db_table not in existing:
            schema_editor.create_model(ReturnGuideItem)
    _SCHEMA_READY = True


def _next_guide_number(subsidiary):
    number = Guide.objects.filter(subsidiary=subsidiary).aggregate(
        r=Coalesce(Max('guide_number'), 0)
    ).get('r')
    return int(number or 0) + 1


def _aware(date_text):
    day = datetime.strptime(date_text, '%Y-%m-%d').date()
    now = timezone.localtime()
    combined = datetime.combine(day, time(now.hour, now.minute, now.second))
    if timezone.is_naive(combined):
        return timezone.make_aware(combined, timezone.get_current_timezone())
    return combined


def _split_bill(bill_number):
    text = str(bill_number or '').strip().upper().replace(' ', '')
    if not text:
        return '', ''
    if '-' in text:
        serie, numero = text.split('-', 1)
        return serie[:10], numero[:20]
    return '', text[:20]


def _document_type_from_purchase(purchase):
    return {'F': '01', 'B': '03'}.get(purchase.type_bill, '00')


def _product_payload(product, serial='', match='Producto', status=''):
    detail = product.productdetail_set.filter(is_enabled=True).select_related('unit').first()
    if detail is None:
        detail = product.productdetail_set.select_related('unit').first()
    if detail is None or detail.unit_id is None:
        return None
    price = detail.price_purchase or decimal.Decimal('0')
    serials = []
    seen_serials = set()
    if serial:
        serials.append(serial)
        seen_serials.add(serial.upper())
    stored_serials = ProductSerial.objects.filter(
        product_store__product=product
    ).exclude(serial_number__isnull=True).exclude(serial_number='').values_list('serial_number', flat=True)[:30]
    for stored in stored_serials:
        value = str(stored).strip()
        key = value.upper()
        if value and key not in seen_serials:
            seen_serials.add(key)
            serials.append(value)
    return {
        'id': product.id,
        'name': product.name or '',
        'code': product.code or '',
        'barcode': product.barcode or '',
        'brand': product.product_brand.name if product.product_brand_id else '',
        'unit_id': detail.unit_id,
        'unit_name': detail.unit.name,
        'price_purchase': float(price),
        'serial': serial or (serials[0] if len(serials) == 1 else ''),
        'serials': serials,
        'serial_status': status or '',
        'match': match,
    }


def _purchase_items(purchase):
    items = []
    details = purchase.purchasedetail_set.select_related('product', 'unit').all()
    for detail in details:
        if detail.product_id is None or detail.unit_id is None:
            continue
        serials = list(
            ProductSerial.objects.filter(purchase_detail=detail)
            .exclude(serial_number__isnull=True)
            .exclude(serial_number='')
            .values_list('serial_number', flat=True)
        )
        price = float(detail.price_unit or 0)
        quantity = decimal.Decimal(detail.quantity or 0)
        base = {
            'product_id': detail.product_id,
            'name': detail.product.name,
            'code': detail.product.code or '',
            'unit_id': detail.unit_id,
            'unit_name': detail.unit.name,
            'price': price,
        }
        clean_serials = []
        for raw in serials:
            value = str(raw).strip()
            if value and value.upper() not in {item.upper() for item in clean_serials}:
                clean_serials.append(value)
        if clean_serials:
            for serial in clean_serials:
                row = dict(base)
                row['quantity'] = 1
                row['serial'] = serial
                items.append(row)
            remaining = quantity - decimal.Decimal(len(clean_serials))
            if remaining > 0:
                row = dict(base)
                row['quantity'] = float(remaining)
                row['serial'] = ''
                items.append(row)
        else:
            row = dict(base)
            row['quantity'] = float(quantity if quantity > 0 else 1)
            row['serial'] = ''
            items.append(row)
    return items


def _preset_from_purchase(purchase):
    serie, numero = _split_bill(purchase.bill_number)
    supplier = purchase.supplier
    return {
        'purchase_id': purchase.id,
        'bill_number': purchase.bill_number or '',
        'supplier_id': supplier.id if supplier else '',
        'destiny_address': (supplier.address or '') if supplier else '',
        'related_type': _document_type_from_purchase(purchase),
        'related_serial': serie,
        'related_number': numero,
        'items': _purchase_items(purchase),
    }


def return_guide_list(request):
    ensure_return_guide_schema()
    user_subsidiary = get_subsidiary_by_user(request.user)
    guides = ReturnGuide.objects.select_related(
        'guide', 'supplier', 'purchase'
    ).order_by('-id')
    if user_subsidiary is not None:
        guides = guides.filter(guide__subsidiary=user_subsidiary)
    return render(request, 'buys/return_guide_list.html', {
        'guides': guides[:200],
    })


def return_guide_form(request):
    ensure_return_guide_schema()
    subsidiary = get_subsidiary_by_user(request.user)
    today = timezone.localdate().strftime('%Y-%m-%d')
    suppliers = Supplier.objects.all().order_by('name')
    districts = District.objects.all().order_by('description')
    origin_ubigeo = ''
    origin_district = ''
    origin_address = ''
    company_name = ''
    company_ruc = ''
    if subsidiary is not None:
        origin_address = subsidiary.address or ''
        company_name = subsidiary.business_name or subsidiary.name or ''
        company_ruc = subsidiary.ruc or ''
        if subsidiary.district_id:
            origin_ubigeo = subsidiary.district_id
            origin_district = subsidiary.district.description or ''

    preset = {}
    purchase_id = request.GET.get('purchase', '')
    preset_error = ''
    if purchase_id:
        purchase = Purchase.objects.select_related('supplier').filter(id=purchase_id).first()
        if purchase is None:
            preset_error = 'La compra indicada no existe.'
        elif subsidiary is not None and purchase.subsidiary_id != subsidiary.id:
            preset_error = 'La compra no pertenece a su sede.'
        elif purchase.status == 'N':
            preset_error = 'La compra esta anulada y no se puede devolver.'
        else:
            preset = _preset_from_purchase(purchase)

    return render(request, 'buys/return_guide_form.html', {
        'date_now': today,
        'suppliers': suppliers,
        'districts': districts,
        'origin_ubigeo': origin_ubigeo,
        'origin_district': origin_district,
        'origin_address': origin_address,
        'company_name': company_name,
        'company_ruc': company_ruc,
        'preset': preset,
        'preset_error': preset_error,
        'modalities': Guide._meta.get_field('guide_modality_transport').choices,
        'document_types': ReturnGuide.DOCUMENT_TYPE_CHOICES,
    })


def search_products_return_guide(request):
    term = str(request.GET.get('term', '')).strip()
    search_type = str(request.GET.get('type', 'all')).strip()
    if search_type not in ('all', 'barcode', 'description', 'serial'):
        search_type = 'all'
    if len(term) < 2:
        return JsonResponse({'products': []})

    results = []
    seen = set()

    if search_type in ('all', 'serial'):
        serial_rows = ProductSerial.objects.filter(
            serial_number__icontains=term
        ).select_related(
            'product_store__product__product_brand'
        )[:8]
        for serial in serial_rows:
            store = serial.product_store
            product = store.product if store is not None else None
            if product is None:
                continue
            serial_text = str(serial.serial_number or '').strip()
            key = (product.id, serial_text.upper())
            if key in seen:
                continue
            payload = _product_payload(product, serial_text, 'Serie', serial.status)
            if payload is None:
                continue
            seen.add(key)
            results.append(payload)

    if search_type != 'serial':
        query = Q()
        if search_type in ('all', 'barcode'):
            query |= Q(code__icontains=term) | Q(barcode__icontains=term)
        if search_type in ('all', 'description'):
            query |= Q(name__icontains=term) | Q(name_search__icontains=term)
        products = Product.objects.filter(query).select_related('product_brand')[:12]
        for product in products:
            key = (product.id, '')
            if key in seen:
                continue
            payload = _product_payload(product, '', 'Producto')
            if payload is None:
                continue
            seen.add(key)
            results.append(payload)

    return JsonResponse({'products': results[:15]})


def _positive_int(value):
    text = str(value if value is not None else '').strip()
    if not text.isdigit():
        return None
    return int(text)


def _decimal(value, label):
    text = str(value if value is not None else '').strip().replace(',', '.')
    if text == '':
        raise ValueError('Ingrese {}.'.format(label))
    try:
        number = decimal.Decimal(text)
    except decimal.InvalidOperation:
        raise ValueError('{} no es un numero valido.'.format(label))
    return number


def save_return_guide(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Metodo no permitido.'}, status=HTTPStatus.METHOD_NOT_ALLOWED)

    ensure_return_guide_schema()
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'message': 'El formulario no tiene un formato valido.'})

    subsidiary = get_subsidiary_by_user(request.user)
    if subsidiary is None:
        return JsonResponse({'success': False, 'message': 'Su usuario no tiene una sede asignada.'})
    if not subsidiary.district_id:
        return JsonResponse({
            'success': False,
            'message': 'La sede no tiene ubigeo de origen. Configure el distrito de la empresa.',
        })
    if not (subsidiary.address or '').strip():
        return JsonResponse({
            'success': False,
            'message': 'La sede no tiene direccion de origen configurada.',
        })

    supplier_id = _positive_int(payload.get('supplier_id'))
    supplier = Supplier.objects.filter(id=supplier_id).first() if supplier_id else None
    if supplier is None:
        return JsonResponse({'success': False, 'message': 'Seleccione un proveedor.'})
    recipient_error = return_guide_recipient_error(supplier.ruc, '6')
    if recipient_error:
        return JsonResponse({'success': False, 'message': recipient_error})

    destiny = str(payload.get('destiny') or '').strip()
    if not District.objects.filter(id=destiny).exists():
        return JsonResponse({'success': False, 'message': 'Seleccione el ubigeo de destino.'})

    destiny_address = str(payload.get('destiny_address') or '').strip()
    if not destiny_address:
        return JsonResponse({'success': False, 'message': 'Ingrese la direccion de destino.'})

    modality = str(payload.get('modality') or '').strip()
    if modality not in ('1', '2'):
        return JsonResponse({'success': False, 'message': 'Seleccione la modalidad de transporte.'})

    try:
        issue = _aware(str(payload.get('issue') or ''))
        transfer = _aware(str(payload.get('transfer') or ''))
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Las fechas de emision y traslado son obligatorias.'})
    if transfer.date() < issue.date():
        return JsonResponse({'success': False, 'message': 'La fecha de traslado no puede ser anterior a la emision.'})

    try:
        weight = _decimal(payload.get('weight'), 'el peso bruto')
        lumps = _decimal(payload.get('lumps'), 'el numero de bultos')
    except ValueError as exc:
        return JsonResponse({'success': False, 'message': str(exc)})
    if weight <= 0 or lumps <= 0:
        return JsonResponse({'success': False, 'message': 'El peso bruto y los bultos deben ser mayores a cero.'})

    carrier_document = str(payload.get('carrier_document') or '').strip()
    carrier_names = str(payload.get('carrier_names') or '').strip()
    truck = str(payload.get('truck') or '').strip().upper()
    driver_names = str(payload.get('driver_names') or '').strip()
    driver_lastname = str(payload.get('driver_lastname') or '').strip()
    driver_dni = str(payload.get('driver_dni') or '').strip()
    driver_license = str(payload.get('driver_license') or '').strip().upper()
    register_mtc = str(payload.get('register_mtc') or '').strip()
    observation = str(payload.get('observation') or '').strip()

    if modality == '1' and (not carrier_document or not carrier_names):
        return JsonResponse({
            'success': False,
            'message': 'En transporte publico indique el documento y la razon social del transportista.',
        })
    if modality == '2' and not all([truck, driver_names, driver_lastname, driver_dni, driver_license]):
        return JsonResponse({
            'success': False,
            'message': 'En transporte privado indique placa, nombres, apellidos, DNI y licencia del conductor.',
        })

    raw_items = payload.get('items') or []
    if not isinstance(raw_items, list) or not raw_items:
        return JsonResponse({'success': False, 'message': 'Agregue al menos un producto al detalle.'})

    purchase = None
    if payload.get('purchase_id') not in (None, '', 'null'):
        purchase_id = _positive_int(payload.get('purchase_id'))
        purchase = Purchase.objects.filter(
            id=purchase_id, subsidiary=subsidiary).exclude(status='N').first() if purchase_id else None
        if purchase is None:
            return JsonResponse({'success': False, 'message': 'La compra de origen no esta disponible.'})

    prepared = []
    seen_serials = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            return JsonResponse({'success': False, 'message': 'El detalle de productos no tiene un formato valido.'})
        product_id = _positive_int(raw.get('product_id'))
        unit_id = _positive_int(raw.get('unit_id'))
        product = Product.objects.filter(id=product_id).first() if product_id else None
        unit = Unit.objects.filter(id=unit_id).first() if unit_id else None
        if product is None or unit is None:
            return JsonResponse({'success': False, 'message': 'Hay un producto o una unidad que ya no existe.'})
        if not ProductDetail.objects.filter(product=product, unit=unit).exists():
            unit_detail = product.productdetail_set.select_related('unit').first()
            if unit_detail is None:
                return JsonResponse({
                    'success': False,
                    'message': 'El producto {} no tiene unidad de medida.'.format(product.name),
                })
            unit = unit_detail.unit
        try:
            quantity = _decimal(raw.get('quantity'), 'la cantidad de {}'.format(product.name))
            price = _decimal(raw.get('price') or 0, 'el precio de {}'.format(product.name))
        except ValueError as exc:
            return JsonResponse({'success': False, 'message': str(exc)})
        if quantity <= 0:
            return JsonResponse({'success': False, 'message': 'La cantidad de {} debe ser mayor a cero.'.format(product.name)})
        if price < 0:
            return JsonResponse({'success': False, 'message': 'El precio de {} no puede ser negativo.'.format(product.name)})
        serial = str(raw.get('serial') or '').strip()
        if serial:
            key = serial.upper()
            if key in seen_serials:
                return JsonResponse({'success': False, 'message': 'La serie {} esta repetida.'.format(serial)})
            seen_serials.add(key)
            quantity = decimal.Decimal('1')
        prepared.append({
            'product': product,
            'unit': unit,
            'quantity': quantity,
            'price': price,
            'serial': serial,
        })

    related_type = str(payload.get('related_type') or '01').strip()
    if related_type not in dict(ReturnGuide.DOCUMENT_TYPE_CHOICES):
        related_type = '01'
    related_serial = str(payload.get('related_serial') or '').strip().upper()[:10]
    related_number = str(payload.get('related_number') or '').strip()[:20]

    description = observation or 'GUIA DE REMISION POR DEVOLUCION'
    serial = 'T{}'.format(subsidiary.serial or '')
    guide = None
    try:
        with transaction.atomic():
            guide = Guide(
                serial=serial,
                guide_serial=serial,
                guide_description=description[:500],
                observation=observation[:500],
                guide_type='7',
                guide_number=_next_guide_number(subsidiary),
                guide_date=issue,
                guide_transfer=transfer,
                guide_motive='06',
                guide_truck=truck[:50],
                guide_driver_name=driver_names[:100],
                guide_driver_lastname=driver_lastname[:100],
                guide_driver_full_name='{} {}'.format(driver_names, driver_lastname).strip()[:100],
                guide_driver_dni=driver_dni[:15],
                guide_driver_license=driver_license[:15],
                guide_origin=subsidiary.district_id,
                guide_destiny=destiny,
                guide_carrier_document=carrier_document[:11],
                guide_modality_transport=modality,
                guide_carrier_names=carrier_names[:200],
                guide_register_mtc=register_mtc[:200],
                guide_origin_address=(subsidiary.address or '')[:200],
                guide_destiny_address=destiny_address[:200],
                guide_weight=weight,
                guide_package=lumps,
                user=request.user,
                subsidiary=subsidiary,
                status='1',
                document_type_attached='G',
            )
            guide.save()
            return_guide = ReturnGuide.objects.create(
                guide=guide,
                supplier=supplier,
                purchase=purchase,
                related_document_type=related_type,
                related_document_serial=related_serial,
                related_document_number=related_number,
                status='P',
            )
            for item in prepared:
                ReturnGuideItem.objects.create(
                    return_guide=return_guide,
                    product=item['product'],
                    unit=item['unit'],
                    quantity=item['quantity'],
                    price_unit=item['price'],
                    serial_number=item['serial'],
                )
                GuideDetail.objects.create(
                    guide=guide,
                    product=item['product'],
                    quantity_request=item['quantity'],
                    quantity_sent=item['quantity'],
                    quantity=item['quantity'],
                    unit_measure=item['unit'],
                    weight=0,
                )
    except Exception as exc:
        return JsonResponse({'success': False, 'message': 'No se pudo registrar la guia: {}'.format(exc)})

    try:
        response = send_guide_fact(guide.id)
    except Exception as exc:
        response = {'success': False, 'message': 'No se pudo conectar con SUNAT: {}'.format(exc)}

    if response.get('success'):
        ReturnGuide.objects.filter(guide=guide).update(
            status='E',
            sunat_message=str(response.get('message') or 'Enviado a SUNAT')[:500],
        )
        guide.guide_description = str(response.get('message') or guide.guide_description)[:500]
        guide.guide_status = '0'
        guide.save(update_fields=['guide_description', 'guide_status', 'updated_at'])
        return JsonResponse({
            'success': True,
            'message': response.get('message') or 'Guia enviada a SUNAT.',
            'serie': guide.guide_serial,
            'numero': guide.guide_number,
            'pk': guide.id,
        })

    message = response.get('message') or response.get('error') or 'SUNAT rechazo la guia.'
    guide_id = guide.id
    Guide.objects.filter(id=guide_id).delete()
    return JsonResponse({'success': False, 'message': message})
