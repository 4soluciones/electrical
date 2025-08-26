from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum

from apps.hrm.models import Subsidiary, District, DocumentType
from apps.sales.models import Unit, Product, Supplier, SubsidiaryStore, ProductDetail
from apps.comercial.models import Truck
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, Adjust


class Purchase(models.Model):
    STATUS_CHOICES = (('S', 'SIN ALMACEN'), ('A', 'EN ALMACEN'), ('N', 'ANULADO'),)
    TYPE_CHOICES = (('T', 'TICKET'), ('B', 'BOLETA'), ('F', 'FACTURA'),)
    PAY_TYPE_CHOICES = (('E', 'EFECTIVO'), ('D', 'DEPOSITO'), ('C', 'CREDITO'), ('L', 'LETRAS'), ('EC', 'EN CARTERA'),)
    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(Supplier, verbose_name='Proveedor', on_delete=models.CASCADE, null=True, blank=True)
    purchase_date = models.DateField('Fecha compra', null=True, blank=True)
    bill_number = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='S')
    document_freight = models.CharField('Documento Flete', max_length=45, null=True, blank=True)
    serial_freight = models.CharField('serie Flete', max_length=45, null=True, blank=True)
    number_freight = models.CharField('Numero Flete', max_length=45, null=True, blank=True)
    date_freight = models.DateField('Fecha de Flete', null=True, blank=True)
    total_freight = models.DecimalField('Total Flete', max_digits=10, decimal_places=2, default=0)
    base_total_purchase = models.DecimalField('Base Imponible Compra', max_digits=10, decimal_places=2, default=0)
    igv_total_purchase = models.DecimalField('Igv Compra', max_digits=10, decimal_places=2, default=0)
    total_import = models.DecimalField('Importe Total', max_digits=10, decimal_places=2, default=0)
    total_purchase = models.DecimalField('Total Documento', max_digits=10, decimal_places=2, default=0)
    check_igv = models.BooleanField('Habilitado IGV', default=False)
    check_dollar = models.BooleanField('Habilitado Dollar', default=False)
    type_bill = models.CharField('Tipo de comprobante', max_length=1, choices=TYPE_CHOICES, default='F')
    type_pay = models.CharField('Tipo de pago', max_length=2, choices=PAY_TYPE_CHOICES, default='E')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    def total(self):
        response = 0
        purchase_detail_set = PurchaseDetail.objects.filter(purchase__id=self.id)
        for pd in purchase_detail_set:
            response = response + (pd.quantity * pd.price_unit)
        return response

    def total_quantity_details(self):
        response = 0
        purchase_detail_set = PurchaseDetail.objects.filter(purchase__id=self.id)
        for pd in purchase_detail_set:
            response = response + pd.quantity
        return response


class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, null=True, blank=True)
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.DecimalField('Cantidad comprada', max_digits=10, decimal_places=2, default=0)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    price_unit = models.DecimalField('Precio unitario', max_digits=30, decimal_places=15, default=0)
    price_unit_discount = models.DecimalField('Precio unitario Descuento', max_digits=30, decimal_places=15, default=0)
    discount_one = models.DecimalField('Porcentaje 1', max_digits=10, decimal_places=2, default=0)
    discount_two = models.DecimalField('Porcentaje 2', max_digits=10, decimal_places=2, default=0)
    discount_three = models.DecimalField('Porcentaje 3', max_digits=10, decimal_places=2, default=0)
    discount_four = models.DecimalField('Porcentaje 4', max_digits=10, decimal_places=2, default=0)
    total_detail = models.DecimalField('total', max_digits=10, decimal_places=2, default=0)
    check_kardex = models.BooleanField('Habilitado kardex', default=False)

    def __str__(self):
        return str(self.id)

    # def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
    #     if self.price_unit:
    #         product_presenting_obj = ProductDetail.objects.filter(product=self.product,
    #                                                               unit=self.unit).last()
    #         product_presenting_obj.price_purchase = self.price_unit
    #         product_presenting_obj.save()
    #
    #     super(PurchaseDetail, self).save(force_insert, force_update, using, update_fields)

    def multiplicate(self):
        return self.quantity * self.price_unit

    def price_unit_discount_with_igv(self):
        return float(self.price_unit_discount) * float(1.18)

    class Meta:
        verbose_name = 'Detalle compra'
        verbose_name_plural = 'Detalles de compra'


class PurchaseDues(models.Model):
    id = models.AutoField(primary_key=True)
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, null=True, blank=True)
    due = models.DecimalField('Cuota', max_digits=10, decimal_places=2, default=0)


class Requirement_buys(models.Model):
    STATUS_CHOICES = (('1', 'PENDIENTE'), ('2', 'APROBADO'), ('3', 'ANULADO'), ('4', 'FINALIZADO'),)
    TYPE_CHOICES = (('M', 'MERCADERIA'), ('I', 'INSUMO'),)
    id = models.AutoField(primary_key=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='1', )
    type = models.CharField('Tipo', max_length=1, choices=TYPE_CHOICES, default='M', )
    creation_date = models.DateField('Fecha de solicitud', null=True, blank=True)
    number_scop = models.CharField('Numero de scop', max_length=45, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    approval_date = models.DateField('Fecha de aprobación', null=True, blank=True)
    invoice = models.CharField('Factura', max_length=45, null=True, blank=True)

    def __str__(self):
        str(self.id) + " - " + str(self.status)

    class Meta:
        verbose_name = 'Requerimiento'
        verbose_name_plural = 'Requerimientos'


class RequirementDetail_buys(models.Model):
    COIN_CHOICES = ((1, 'DOLAR(ES)'), (2, 'SOLE(S)'),)
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    requirement_buys = models.ForeignKey('Requirement_buys', on_delete=models.CASCADE, related_name='requirements_buys',
                                         null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    amount = models.DecimalField('Importe', max_digits=30, decimal_places=15, default=0)
    price_pen = models.DecimalField('Precio soles', max_digits=30, decimal_places=15, default=0)
    amount_pen = models.DecimalField('Importe soles', max_digits=30, decimal_places=15, default=0)
    coin = models.IntegerField('Moneda', choices=COIN_CHOICES, default=1, )
    change_coin = models.DecimalField('Cambio', max_digits=30, decimal_places=15, default=0)

    def __str__(self):
        str(self.product.code) + " / " + str(self.requirement.id)

    def multiplicate(self):
        return self.quantity * self.price

    class Meta:
        verbose_name = 'Detalle requerimiento'
        verbose_name_plural = 'Detalles de requerimiento'


class RequirementBuysProgramming(models.Model):
    STATUS_CHOICES = (('P', 'PROGRAMADO'), ('F', 'FINALIZADO'),)
    id = models.AutoField(primary_key=True)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='truck', null=True, blank=True)
    date_programming = models.DateField('Fecha de solicitud', null=True, blank=True)
    number_scop = models.CharField('Numero de scop', max_length=45, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='rpsubsidiary')

    def __str__(self):
        return str(self.id)

    def calculate_total_programming_expenses_price(self):
        # try:
        response = ProgrammingExpense.objects.filter(
            requirementBuysProgramming__id=self.id).values(
            'requirementBuysProgramming').annotate(totals=Sum('price'))
        if (response.exists()):
            return response[0].get('totals')
        else:
            return 0

    # except ProgrammingExpense.DoesNotExist:
    #     return 0

    class Meta:
        verbose_name = 'Programacion de Requerimiento GLP'
        verbose_name_plural = 'Programaciones de Requerimiento GLP'


class Programminginvoice(models.Model):
    STATUS_CHOICES = (('P', 'PENDIENTE'), ('R', 'REGISTRADO'),)
    id = models.AutoField(primary_key=True)
    requirementBuysProgramming = models.ForeignKey(RequirementBuysProgramming, on_delete=models.SET_NULL, null=True,
                                                   blank=True)
    requirement_buys = models.ForeignKey(Requirement_buys, on_delete=models.SET_NULL, null=True, blank=True)
    date_arrive = models.DateField('Fecha de entrada', null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    guide = models.CharField('Numero Guia', max_length=45, null=True, blank=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    subsidiary_store_destiny = models.ForeignKey(SubsidiaryStore, on_delete=models.SET_NULL, null=True, blank=True,
                                                 related_name='destinies')
    subsidiary_store_origin = models.ForeignKey(SubsidiaryStore, on_delete=models.SET_NULL, null=True, blank=True,
                                                related_name='origins')

    def __str__(self):
        return str(self.id)

    def calculate_total_quantity(self):
        response = Programminginvoice.objects.filter(requirement_buys_id=self.requirement_buys.id).values(
            'requirement_buys').annotate(totals=Sum('quantity'))
        # return response.count
        if response:
            return response[0].get('totals')
        else:
            return 0

    def calculate_total_programming_quantity(self):
        response = Programminginvoice.objects.filter(
            requirementBuysProgramming_id=self.requirementBuysProgramming.id).values(
            'requirementBuysProgramming').annotate(totals=Sum('quantity'))
        # return response.count
        if response:
            return response[0].get('totals')
        else:
            return 0

    class Meta:
        verbose_name = 'Factura GLP'
        verbose_name_plural = 'Facturas GLP'


class ProgrammingExpense(models.Model):
    STATUS_CHOICES = (('P', 'PENDIENTE'), ('R', 'REGISTRADO'),)
    TYPE_CHOICES = (
        ('C', 'COMBUSTIBLE'), ('F', 'FLETE'), ('P', 'PEAJE'), ('S', 'SUELDO'), ('V', 'VIATICO'), ('L', 'LAVADO'),)
    id = models.AutoField(primary_key=True)
    requirementBuysProgramming = models.ForeignKey(RequirementBuysProgramming, on_delete=models.SET_NULL, null=True,
                                                   blank=True)
    invoice = models.CharField('Factura', max_length=45, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    type = models.CharField('Estado', max_length=1, choices=TYPE_CHOICES, default='C', )
    date_invoice = models.DateField('Fecha de Facturacion', null=True, blank=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    noperation = models.CharField('Numero Guia', max_length=45, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Tanqueo'
        verbose_name_plural = 'Tanqueos'


class RateRoutes(models.Model):
    id = models.AutoField(primary_key=True)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='trucks', null=True, blank=True)
    price = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='subsidiarys')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Ruta Tarifario'
        verbose_name_plural = 'Ruta Tarifarios'


class PurchaseReturn(models.Model):
    TYPE_CHOICES = (('T', 'TICKET'), ('B', 'BOLETA'), ('F', 'FACTURA'),)
    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(Supplier, verbose_name='Proveedor', on_delete=models.CASCADE, null=True, blank=True)
    purchase_date = models.DateField('Fecha compra', null=True, blank=True)
    bill_number = models.CharField(max_length=100, null=True, blank=True)
    type_bill = models.CharField('Tipo de comprobante', max_length=1, choices=TYPE_CHOICES, default='F')
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    base_total_purchase = models.DecimalField('Base Imponible Compra', max_digits=10, decimal_places=2, default=0)
    igv_total_purchase = models.DecimalField('Igv Compra', max_digits=10, decimal_places=2, default=0)
    total_purchase = models.DecimalField('Total Documento', max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Compra devolucion'
        verbose_name_plural = 'Compras devolucion'

    def total(self):
        response = 0
        purchase_detail_set = PurchaseReturnDetail.objects.filter(purchase__id=self.id)
        for pd in purchase_detail_set:
            response = response + (pd.quantity * pd.price_unit)
        return response

    def total_quantity_details(self):
        response = 0
        purchase_detail_set = PurchaseReturnDetail.objects.filter(purchase__id=self.id)
        for pd in purchase_detail_set:
            response = response + pd.quantity
        return response


class PurchaseReturnDetail(models.Model):
    id = models.AutoField(primary_key=True)
    purchase = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.DecimalField('Cantidad comprada', max_digits=10, decimal_places=2, default=0)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    price_unit = models.DecimalField('Precio unitario', max_digits=30, decimal_places=15, default=0)
    total_detail = models.DecimalField('total', max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return str(self.id)

    def multiply(self):
        return self.quantity * self.price_unit

    class Meta:
        verbose_name = 'Detalle compra devolucion'
        verbose_name_plural = 'Detalles de compra devolucion'