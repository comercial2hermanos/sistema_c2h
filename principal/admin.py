from django.contrib import admin
# IMPORTANTE: Agregamos Abono a la importación
from .models import Cliente, Producto, Venta, DetalleVenta, Compra, DetalleCompra, CierreCaja, Abono

# --- CONFIGURACIÓN DE CLIENTES ---
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ruc_cedula', 'telefono', 'direccion') 
    search_fields = ('nombre', 'ruc_cedula')

# --- CONFIGURACIÓN DE PRODUCTOS ---
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'precio_venta', 'stock_actual', 'es_granel')
    search_fields = ('nombre', 'codigo')
    list_filter = ('es_granel', 'stock_minimo') 

# --- CONFIGURACIÓN DE ABONOS (NUEVO) ---
class AbonoAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'venta', 'monto', 'nota')
    list_filter = ('fecha',)

# --- CONFIGURACIÓN DE VENTAS (FACTURACIÓN) ---
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0 # 0 para que no ocupe espacio innecesario
    autocomplete_fields = ['producto']

class AbonoInline(admin.TabularInline):
    model = Abono
    extra = 0
    readonly_fields = ('fecha', 'monto', 'nota')
    can_delete = False

class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'cliente', 'total', 'tipo_pago', 'pagado')
    list_filter = ('fecha', 'tipo_pago', 'pagado')
    search_fields = ('cliente__nombre',)
    inlines = [DetalleVentaInline, AbonoInline] # Agregamos Abonos aquí también para verlo dentro de la venta

# --- CONFIGURACIÓN DE COMPRAS (INGRESO MERCADERÍA) ---
class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 0
    autocomplete_fields = ['producto']

class CompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'proveedor', 'total')
    inlines = [DetalleCompraInline]

# --- CONFIGURACIÓN DE CIERRES DE CAJA ---
class CierreCajaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_cierre', 'usuario', 'total_ventas', 'monto_efectivo')
    list_filter = ('fecha_cierre', 'usuario')

# --- REGISTRO FINAL ---
admin.site.register(Cliente, ClienteAdmin)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Venta, VentaAdmin)
admin.site.register(Compra, CompraAdmin)
admin.site.register(CierreCaja, CierreCajaAdmin)
admin.site.register(Abono, AbonoAdmin)