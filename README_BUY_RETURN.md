# Formulario de Devoluciones de Compra (Buy Return)

## Descripción
Este formulario permite registrar devoluciones de compras en el sistema. Es una versión simplificada del formulario de compras original, eliminando las columnas de descuentos y adaptando la funcionalidad para devoluciones.

## Características Principales

### ✅ Implementado
- **Formulario responsive** con Bootstrap 4
- **Eliminación de columnas de descuentos** (%Dto.1, %Dto.2, %Dto.3, %Dto.4)
- **Guardado en modelos específicos**: `PurchaseReturn` y `PurchaseReturnDetail`
- **Validación de campos** requeridos
- **Búsqueda de productos** por nombre o código de barras
- **Cálculo automático** de totales e IGV
- **Soporte para monedas** (Soles y Dólares)
- **Gestión de series** para productos
- **Integración con proveedores** existentes

### 🔧 Archivos Creados/Modificados

#### Templates
- `templates/buys/buy_return.html` - Template principal del formulario
- `templates/buys/buy_return_detail.html` - Tabla de detalles de productos
- `templates/buys/buy_return_register.html` - Formulario de registro

#### Vistas
- `apps/buys/views.py` - Agregada función `get_buy_return()` y `save_purchase_return()`

#### URLs
- `apps/buys/urls.py` - Agregadas rutas para el formulario de devoluciones

#### Modelos
- `apps/buys/models.py` - Corregido modelo `PurchaseReturn` y agregado campo `type_bill`

## Estructura de la Base de Datos

### Modelo PurchaseReturn
```python
class PurchaseReturn(models.Model):
    TYPE_CHOICES = (('T', 'TICKET'), ('B', 'BOLETA'), ('F', 'FACTURA'),)
    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(Supplier, ...)
    purchase_date = models.DateField(...)
    bill_number = models.CharField(...)
    type_bill = models.CharField(choices=TYPE_CHOICES, default='F')
    user = models.ForeignKey(User, ...)
    subsidiary = models.ForeignKey(Subsidiary, ...)
    base_total_purchase = models.DecimalField(...)
    igv_total_purchase = models.DecimalField(...)
    total_purchase = models.DecimalField(...)
```

### Modelo PurchaseReturnDetail
```python
class PurchaseReturnDetail(models.Model):
    id = models.AutoField(primary_key=True)
    purchase = models.ForeignKey(PurchaseReturn, ...)
    product = models.ForeignKey(Product, ...)
    quantity = models.DecimalField(...)
    unit = models.ForeignKey(Unit, ...)
    price_unit = models.DecimalField(...)
    total_detail = models.DecimalField(...)
```

## Funcionalidades del Formulario

### 1. Registro de Devolución
- **Fecha de devolución**: Campo de fecha obligatorio
- **Número de factura**: Referencia del documento original
- **Tipo de comprobante**: TICKET, BOLETA o FACTURA
- **Proveedor**: Selección del proveedor de la compra original
- **RUC del proveedor**: Búsqueda automática por RUC

### 2. Gestión de Productos
- **Búsqueda por nombre**: Mínimo 3 caracteres
- **Búsqueda por código de barras**: Escaneo directo
- **Cantidad**: Cantidad a devolver
- **Unidad de medida**: Automática según el producto
- **Precio unitario**: Con y sin IGV
- **Total**: Cálculo automático

### 3. Cálculos Automáticos
- **Base imponible**: Total sin IGV
- **IGV (18%)**: Calculado automáticamente
- **Total documento**: Suma de todos los productos
- **Soporte IGV**: Checkbox para incluir/excluir IGV

### 4. Gestión de Series
- **Botón Series**: Permite agregar números de serie
- **Validación**: Verifica duplicados
- **Acordeón**: Interfaz colapsable para series

## Uso del Formulario

### 1. Acceso
```
URL: /buys/buy_return/
```

### 2. Flujo de Trabajo
1. **Llenar datos básicos**: Fecha, factura, tipo de comprobante, proveedor
2. **Agregar productos**: Usar botón "Agregar Producto" o búsqueda directa
3. **Completar detalles**: Cantidad, precio, series (si aplica)
4. **Revisar totales**: Verificar cálculos automáticos
5. **Guardar devolución**: Botón "Guardar Devolución"

### 3. Validaciones
- Campos obligatorios completados
- Al menos un producto agregado
- Cantidades y precios válidos
- Proveedor seleccionado

## Diferencias con el Formulario Original

### ❌ Eliminado
- Columnas de descuentos (%Dto.1, %Dto.2, %Dto.3, %Dto.4)
- Gestión de cuotas/letras
- Campos de flete
- Checkbox de kardex

### ✅ Mantenido
- Búsqueda de productos
- Gestión de series
- Cálculo de IGV
- Soporte multi-moneda
- Responsive design
- Validaciones básicas

### 🔄 Adaptado
- **Título**: "NUEVA DEVOLUCIÓN" en lugar de "NUEVA COMPRA"
- **Modelos**: `PurchaseReturn` en lugar de `Purchase`
- **Mensajes**: Adaptados para devoluciones
- **URLs**: Endpoints específicos para devoluciones

## Próximos Pasos Recomendados

### 1. Migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Testing
- Probar formulario con diferentes tipos de productos
- Verificar cálculos de IGV
- Validar guardado en base de datos
- Probar responsive design en diferentes dispositivos

### 3. Mejoras Futuras
- **Historial de devoluciones**: Lista de devoluciones realizadas
- **Reportes**: Generación de PDFs de devoluciones
- **Notificaciones**: Alertas para devoluciones pendientes
- **Integración**: Con sistema de inventario para ajustes automáticos

## Notas Técnicas

### Dependencias
- Django 3.x+
- Bootstrap 4
- jQuery
- Select2 (para dropdowns)
- Toastr (para notificaciones)

### Compatibilidad
- **Navegadores**: Chrome, Firefox, Safari, Edge
- **Dispositivos**: Desktop, Tablet, Mobile
- **Django**: 3.0, 3.1, 3.2, 4.0+

### Seguridad
- CSRF protection habilitado
- Login required en todas las vistas
- Validación de datos en frontend y backend
- Sanitización de inputs

## Soporte

Para dudas o problemas con el formulario de devoluciones, revisar:
1. Logs de Django
2. Console del navegador
3. Base de datos (modelos y relaciones)
4. URLs y vistas configuradas
