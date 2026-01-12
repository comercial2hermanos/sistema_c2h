from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

# 1. CLIENTES
class Cliente(models.Model):
    ruc_cedula = models.CharField(max_length=20, unique=True, verbose_name="RUC/Cédula")
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    es_mayorista = models.BooleanField(default=False, verbose_name="¿Es Cliente Especial/Mayorista?")
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        tipo = " (VIP)" if self.es_mayorista else ""
        return f"{self.nombre}{tipo} - {self.ruc_cedula}"

# 2. PRODUCTOS E INVENTARIO
class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código de Barras")
    nombre = models.CharField(max_length=100)
    es_granel = models.BooleanField(default=False, verbose_name="¿Es Granel/Legumbre?")
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Compra")
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Venta")
    stock_actual = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=3, default=5.000)

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock_actual})"

# 3. VENTAS (FACTURACIÓN)
class Venta(models.Model):
    OPCIONES_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('CREDITO', 'Crédito / Por Cobrar'),
    ]
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tipo_pago = models.CharField(max_length=20, choices=OPCIONES_PAGO, default='EFECTIVO')
    pagado = models.BooleanField(default=True, verbose_name="¿Está Pagado?")

    def __str__(self):
        estado = "PAGADO" if self.pagado else "PENDIENTE"
        return f"Factura #{self.id} - {self.cliente.nombre} ({estado})"

    def saldo_pendiente(self):
        if self.pagado:
            return Decimal('0.00')
        total_abonado = sum(abono.monto for abono in self.abonos.all())
        saldo = self.total - total_abonado
        return saldo if saldo > 0 else Decimal('0.00')

    def save(self, *args, **kwargs):
        if not self.id and self.tipo_pago == 'CREDITO':
            self.pagado = False
        super().save(*args, **kwargs)

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

# 4. ABONOS
class Abono(models.Model):
    venta = models.ForeignKey(Venta, related_name='abonos', on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Abonado")
    nota = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nota (Opcional)")

    def __str__(self):
        return f"Abono ${self.monto} a Venta #{self.venta.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.venta.saldo_pendiente() <= 0:
            self.venta.pagado = True
            self.venta.save()

# 5. GASTOS (NUEVO MODELO)
class Gasto(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=200, verbose_name="Descripción")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto ($)")

    def __str__(self):
        return f"${self.monto} - {self.descripcion}"

# 6. COMPRAS
class Compra(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    proveedor = models.CharField(max_length=100, default="General")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Compra #{self.id} - {self.fecha.strftime('%Y-%m-%d')}"

class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)

# 7. CIERRE DE CAJA (ACTUALIZADO CON GASTOS)
class CierreCaja(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    fecha_cierre = models.DateTimeField(auto_now_add=True)
    
    # Ingresos
    monto_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_tarjeta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_transferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Egresos (NUEVO CAMPO)
    total_gastos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Totales Informativos
    total_ventas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cantidad_ventas = models.IntegerField(default=0)

    def __str__(self):
        return f"Cierre #{self.id} - {self.fecha_cierre}"