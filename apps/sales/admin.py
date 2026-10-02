from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from apps.sales import models
# Register your models here.


class SubsidiaryAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_name', 'serial', 'ruc', 'is_main')


# admin.site.register(models.Subsidiary, SubsidiaryAdmin)


class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_enabled')
    list_editable = ('description', 'is_enabled')
    show_full_result_count = False


admin.site.register(models.Unit, UnitAdmin)
admin.site.register(models.ProductFamily)
admin.site.register(models.ProductBrand)
admin.site.register(models.ProductCategory)
admin.site.register(models.ProductSubcategory)


class SubsidiaryStoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'subsidiary', 'category')


admin.site.register(models.SubsidiaryStore, SubsidiaryStoreAdmin)
admin.site.register(models.Product)
admin.site.register(models.ProductDetail)


class ProductStoreAdmin(admin.ModelAdmin):
    list_display = ('product', 'subsidiary_store', 'stock', 'get_subsidiary')
    list_editable = ('subsidiary_store', 'stock',)
    list_filter = ('product',)

    def get_subsidiary(self, obj):
        return obj.subsidiary_store.subsidiary
    get_subsidiary.admin_order_field = 'subsidiary'  # Allows column order sorting
    get_subsidiary.short_description = 'Sede'  # Renames column head


# admin.site.register(models.ProductStore, ProductStoreAdmin)
admin.site.register(models.Supplier)
admin.site.register(models.ProductSupplier)
admin.site.register(models.Client)


class VoucherSerialAdmin(admin.ModelAdmin):
    list_display = (
        'full_serial_display', 'subsidiary', 'document_type', 'code',
        'purpose', 'max_past_days', 'is_active', 'description',
    )
    list_filter = ('subsidiary', 'document_type', 'purpose', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('code', 'description')

    def full_serial_display(self, obj):
        return obj.full_serial
    full_serial_display.short_description = 'Serie'


admin.site.register(models.VoucherSerial, VoucherSerialAdmin)
# admin.site.register(models.LegalClient)
# admin.site.register(models.NaturalClient)
# admin.site.register(models.Kardex)
