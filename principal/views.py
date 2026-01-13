import json
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, ProtectedError, Q, F
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User 
from .models import Producto, Cliente, Venta, DetalleVenta, Compra, DetalleCompra, CierreCaja, Abono, Gasto
from .forms import ClienteForm, UsuarioForm, GastoForm

# ... [DASHBOARD Y MENÚ] ...
@login_required
def vista_menu(request):
    total_productos = Producto.objects.count()
    ventas_hoy = Venta.objects.filter(fecha__date=timezone.now().date()).count()
    deudas_pendientes = Venta.objects.filter(tipo_pago='CREDITO', pagado=False).count()
    
    return render(request, 'principal/menu.html', {
        'total_productos': total_productos,
        'ventas_hoy': ventas_hoy,
        'deudas_pendientes': deudas_pendientes
    })

@login_required
def vista_ventas(request):
    productos = Producto.objects.all().order_by('nombre')
    clientes = Cliente.objects.all().order_by('nombre')
    return render(request, 'principal/ventas.html', {'productos': productos, 'clientes': clientes})

# --- CLIENTE RÁPIDO (AJAX) ---
@login_required
def crear_cliente_rapido(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if Cliente.objects.filter(ruc_cedula=data['ruc']).exists():
                return JsonResponse({'status': 'error', 'mensaje': 'Ya existe un cliente con esa Cédula/RUC.'})
            
            nuevo_cliente = Cliente.objects.create(
                ruc_cedula=data['ruc'],
                nombre=data['nombre'].upper(),
                telefono=data.get('telefono', ''),
                direccion=data.get('direccion', ''),
                es_mayorista=data.get('es_mayorista', False)
            )
            return JsonResponse({'status': 'ok', 'cliente': {'id': nuevo_cliente.id, 'nombre': nuevo_cliente.nombre, 'ruc': nuevo_cliente.ruc_cedula, 'es_mayorista': nuevo_cliente.es_mayorista}})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})
    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'})

# ... [GUARDAR VENTA] ...
@login_required
def guardar_venta(request):
    if request.method == 'POST':
        try:
            datos = json.loads(request.body)
            with transaction.atomic():
                cliente = Cliente.objects.get(id=datos['cliente_id'])
                venta = Venta.objects.create(
                    usuario=request.user, 
                    cliente=cliente, 
                    tipo_pago=datos['metodo_pago'], 
                    total=0
                )
                
                total_venta = 0
                for p_id, info in datos['productos'].items():
                    producto = Producto.objects.select_for_update().get(id=p_id)
                    cantidad = Decimal(str(info['cantidad']))
                    
                    if producto.stock_actual < cantidad:
                        raise Exception(f"Stock insuficiente para {producto.nombre}")
                    
                    DetalleVenta.objects.create(
                        venta=venta, 
                        producto=producto, 
                        cantidad=cantidad, 
                        precio_unitario=info['precio'], 
                        subtotal=info['subtotal']
                    )
                    
                    producto.stock_actual -= cantidad
                    producto.save()
                    total_venta += Decimal(str(info['subtotal']))
                
                venta.total = total_venta
                venta.save()
                
            return JsonResponse({'status': 'ok', 'id_venta': venta.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})
    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'})

@login_required
def imprimir_ticket(request, id_venta):
    venta = get_object_or_404(Venta, id=id_venta)
    return render(request, 'principal/ticket_impresion.html', {'venta': venta})

# ==========================================
# GASTOS Y CIERRE DE CAJA
# ==========================================

@login_required
def listar_gastos(request):
    ultimo_cierre = CierreCaja.objects.order_by('-fecha_cierre').first()
    fecha_inicio = ultimo_cierre.fecha_cierre if ultimo_cierre else timezone.now().replace(hour=0, minute=0, second=0)
    
    gastos = Gasto.objects.filter(fecha__gt=fecha_inicio).order_by('-fecha')
    total_gastos = gastos.aggregate(Sum('monto'))['monto__sum'] or 0
    
    form = GastoForm()
    return render(request, 'principal/gastos.html', {'gastos': gastos, 'total_gastos': total_gastos, 'form': form})

@login_required
def guardar_gasto(request):
    if request.method == 'POST':
        form = GastoForm(request.POST)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.usuario = request.user
            gasto.save()
            messages.success(request, 'Gasto registrado correctamente.')
    return redirect('listar_gastos')

@login_required
def vista_cierre(request):
    ultimo_cierre = CierreCaja.objects.order_by('-fecha_cierre').first()
    fecha_inicio = ultimo_cierre.fecha_cierre if ultimo_cierre else timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    ventas_rango = Venta.objects.filter(fecha__gt=fecha_inicio)
    
    # 1. Sumar Abonos y Gastos
    abonos_hoy = Abono.objects.filter(fecha__gt=fecha_inicio).aggregate(Sum('monto'))['monto__sum'] or 0
    gastos_hoy = Gasto.objects.filter(fecha__gt=fecha_inicio).aggregate(Sum('monto'))['monto__sum'] or 0

    # 2. Sumar Ventas por tipo
    total_efectivo_ventas = ventas_rango.filter(tipo_pago='EFECTIVO').aggregate(Sum('total'))['total__sum'] or 0
    total_tarjeta = ventas_rango.filter(tipo_pago='TARJETA').aggregate(Sum('total'))['total__sum'] or 0
    total_transferencia = ventas_rango.filter(tipo_pago='TRANSFERENCIA').aggregate(Sum('total'))['total__sum'] or 0
    
    # 3. CÁLCULO FINAL DE EFECTIVO EN CAJA
    efectivo_en_caja = (total_efectivo_ventas + abonos_hoy) - gastos_hoy
    
    gran_total = total_efectivo_ventas + total_tarjeta + total_transferencia
    cantidad = ventas_rango.count()

    contexto = {
        'fecha_hora': timezone.now(),
        'usuario': request.user,
        'cantidad_ventas': cantidad,
        'efectivo_en_caja': efectivo_en_caja,
        'efectivo_ventas': total_efectivo_ventas,
        'abonos_hoy': abonos_hoy,
        'gastos_hoy': gastos_hoy,
        'tarjeta': total_tarjeta,
        'transferencia': total_transferencia,
        'ultimo_cierre': ultimo_cierre.fecha_cierre if ultimo_cierre else "Nunca"
    }
    return render(request, 'principal/cierre.html', contexto)

@login_required
def procesar_cierre_caja(request):
    if request.method == 'POST':
        try:
            ultimo_cierre = CierreCaja.objects.order_by('-fecha_cierre').first()
            fecha_inicio = ultimo_cierre.fecha_cierre if ultimo_cierre else timezone.now().replace(hour=0, minute=0, second=0)
            
            ventas = Venta.objects.filter(fecha__gt=fecha_inicio)
            abonos = Abono.objects.filter(fecha__gt=fecha_inicio).aggregate(Sum('monto'))['monto__sum'] or 0
            gastos = Gasto.objects.filter(fecha__gt=fecha_inicio).aggregate(Sum('monto'))['monto__sum'] or 0
            
            t_efectivo_ventas = ventas.filter(tipo_pago='EFECTIVO').aggregate(Sum('total'))['total__sum'] or 0
            t_tarjeta = ventas.filter(tipo_pago='TARJETA').aggregate(Sum('total'))['total__sum'] or 0
            t_transf = ventas.filter(tipo_pago='TRANSFERENCIA').aggregate(Sum('total'))['total__sum'] or 0
            
            efectivo_neto = (t_efectivo_ventas + abonos) - gastos
            total_ventas_brutas = t_efectivo_ventas + t_tarjeta + t_transf
            cant = ventas.count()

            nuevo_cierre = CierreCaja.objects.create(
                usuario=request.user, 
                monto_efectivo=efectivo_neto, 
                monto_tarjeta=t_tarjeta,
                monto_transferencia=t_transf, 
                total_gastos=gastos,
                total_ventas=total_ventas_brutas, 
                cantidad_ventas=cant
            )
            return JsonResponse({'status': 'ok', 'id_cierre': nuevo_cierre.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})

@login_required
def imprimir_reporte_cierre(request, id_cierre):
    cierre = get_object_or_404(CierreCaja, id=id_cierre)
    cierre_anterior = CierreCaja.objects.filter(fecha_cierre__lt=cierre.fecha_cierre).order_by('-fecha_cierre').first()
    fecha_inicio = cierre_anterior.fecha_cierre if cierre_anterior else cierre.fecha_cierre.replace(hour=0, minute=0, second=0)

    total_abonos = Abono.objects.filter(fecha__gt=fecha_inicio, fecha__lte=cierre.fecha_cierre).aggregate(Sum('monto'))['monto__sum'] or 0
    total_gastos = Gasto.objects.filter(fecha__gt=fecha_inicio, fecha__lte=cierre.fecha_cierre).aggregate(Sum('monto'))['monto__sum'] or 0
    
    total_abonos = Decimal(total_abonos)
    total_gastos = Decimal(total_gastos)
    
    context = {'cierre': cierre, 'abonos': total_abonos, 'gastos': total_gastos}
    return render(request, 'principal/ticket_cierre.html', context)

# ... [PRODUCTOS, COMPRAS Y GESTIÓN] ...
@login_required
def vista_lista_productos(request):
    productos = Producto.objects.all().order_by('nombre')
    return render(request, 'principal/lista_productos.html', {'productos': productos})

@login_required
def vista_compras(request):
    productos = Producto.objects.all().order_by('nombre')
    return render(request, 'principal/compras.html', {'productos': productos})

@login_required
def crear_producto(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if Producto.objects.filter(codigo=data['codigo']).exists():
                return JsonResponse({'status': 'error', 'mensaje': 'El código de barras ya existe'})
            Producto.objects.create(codigo=data['codigo'], nombre=data['nombre'], es_granel=data.get('es_granel', False), precio_costo=data['costo'], precio_venta=data['precio'], stock_actual=data['stock'], stock_minimo=5)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})

@login_required
def guardar_compra(request):
    if request.method == 'POST':
        try:
            datos = json.loads(request.body)
            with transaction.atomic():
                compra = Compra.objects.create(usuario=request.user, proveedor=datos['proveedor'], total=0)
                total_compra = 0
                for p_id, info in datos['productos'].items():
                    producto = Producto.objects.select_for_update().get(id=p_id)
                    cantidad = Decimal(str(info['cantidad']))
                    producto.stock_actual += cantidad
                    producto.precio_costo = float(info['costo'])
                    producto.save()
                    DetalleCompra.objects.create(compra=compra, producto=producto, cantidad=cantidad, costo_unitario=info['costo'])
                    total_compra += (float(cantidad) * float(info['costo']))
                compra.total = total_compra
                compra.save()
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})

@login_required
def editar_producto(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            prod = Producto.objects.get(id=data['id'])
            prod.nombre = data['nombre']
            prod.precio_venta = data['precio']
            prod.precio_costo = data['costo']
            prod.save()
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})

@login_required
def eliminar_producto(request, id_producto):
    try:
        producto = Producto.objects.get(id=id_producto)
        producto.delete()
        return JsonResponse({'status': 'ok', 'mensaje': 'Eliminado'})
    except ProtectedError:
        return JsonResponse({'status': 'error', 'mensaje': '⛔ No se puede eliminar: Tiene historial.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)})

# ... [CLIENTES Y USUARIOS] ...
@login_required
def gestion_clientes(request):
    clientes = Cliente.objects.all().order_by('-id')
    return render(request, 'principal/clientes_lista.html', {'clientes': clientes})

@login_required
def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save(); messages.success(request, 'Cliente registrado.')
            return redirect('gestion_clientes')
    else: form = ClienteForm()
    return render(request, 'principal/cliente_form.html', {'form': form, 'titulo': 'Nuevo Cliente'})

@login_required
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save(); messages.success(request, 'Cliente actualizado.')
            return redirect('gestion_clientes')
    else: form = ClienteForm(instance=cliente)
    return render(request, 'principal/cliente_form.html', {'form': form, 'titulo': 'Editar Cliente'})

@login_required
def eliminar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    try: cliente.delete(); messages.success(request, 'Cliente eliminado.')
    except ProtectedError: messages.error(request, 'No se puede eliminar, tiene ventas.')
    except Exception as e: messages.error(request, f'Error: {str(e)}')
    return redirect('gestion_clientes')

def es_admin(user): return user.is_authenticated and user.is_superuser
@user_passes_test(es_admin, login_url='/') 
def gestion_usuarios(request):
    usuarios = User.objects.all().order_by('id')
    return render(request, 'principal/usuarios_lista.html', {'usuarios': usuarios})

@user_passes_test(es_admin, login_url='/')
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password: user.set_password(password)
            rol = form.cleaned_data.get('rol')
            if rol == 'admin': user.is_superuser = True; user.is_staff = True 
            else: user.is_superuser = False; user.is_staff = False 
            user.save(); messages.success(request, f'Usuario {user.username} creado.')
            return redirect('gestion_usuarios')
    else: form = UsuarioForm()
    return render(request, 'principal/usuario_form.html', {'form': form, 'titulo': 'Nuevo Usuario'})

@user_passes_test(es_admin, login_url='/')
def editar_usuario(request, user_id):
    user = get_object_or_404(User, id=user_id)
    rol_actual = 'admin' if user.is_superuser else 'colaborador'
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password: user.set_password(password)
            rol = form.cleaned_data.get('rol')
            if rol == 'admin': user.is_superuser = True; user.is_staff = True
            else: user.is_superuser = False; user.is_staff = False
            user.save(); messages.success(request, 'Usuario actualizado.')
            return redirect('gestion_usuarios')
    else: form = UsuarioForm(instance=user, initial={'rol': rol_actual})
    return render(request, 'principal/usuario_form.html', {'form': form, 'titulo': 'Editar Usuario'})

@user_passes_test(es_admin, login_url='/')
def eliminar_usuario(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user: messages.error(request, 'No puedes auto-eliminarte.')
    else: user.delete(); messages.success(request, 'Usuario eliminado.')
    return redirect('gestion_usuarios')

# ==========================================
# REPORTES Y CUENTAS POR COBRAR
# ==========================================

@user_passes_test(es_admin, login_url='/')
def vista_reportes_menu(request):
    return render(request, 'principal/reportes_menu.html')

@user_passes_test(es_admin, login_url='/')
def reporte_ventas(request):
    hoy = timezone.now()
    fecha_inicio = request.GET.get('inicio', hoy.replace(day=1).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fin', hoy.strftime('%Y-%m-%d'))
    ventas = Venta.objects.filter(fecha__date__range=[fecha_inicio, fecha_fin]).order_by('-fecha')
    total_vendido = ventas.aggregate(Sum('total'))['total__sum'] or 0
    cantidad_ventas = ventas.count()
    por_metodo = ventas.values('tipo_pago').annotate(total=Sum('total')).order_by('-total')
    context = {'ventas': ventas, 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'total_vendido': total_vendido, 'cantidad_ventas': cantidad_ventas, 'por_metodo': por_metodo}
    return render(request, 'principal/reporte_ventas.html', context)

@user_passes_test(es_admin, login_url='/')
def reporte_inventario(request):
    productos = Producto.objects.all().order_by('nombre')
    total_items = 0; valor_costo_total = 0; valor_venta_total = 0
    for p in productos:
        total_items += p.stock_actual
        valor_costo_total += (p.stock_actual * p.precio_costo)
        valor_venta_total += (p.stock_actual * p.precio_venta)
    ganancia_potencial = valor_venta_total - valor_costo_total
    context = {'productos': productos, 'total_items': total_items, 'valor_costo': valor_costo_total, 'valor_venta': valor_venta_total, 'ganancia': ganancia_potencial}
    return render(request, 'principal/reporte_inventario.html', context)

@user_passes_test(es_admin, login_url='/')
def reporte_cierres(request):
    cierres = CierreCaja.objects.all().order_by('-fecha_cierre')
    return render(request, 'principal/reporte_cierres.html', {'cierres': cierres})

# --- AQUÍ ESTÁ LO NUEVO: REPORTE DE GASTOS ---
@user_passes_test(es_admin, login_url='/')
def reporte_gastos(request):
    hoy = timezone.now()
    fecha_inicio = request.GET.get('inicio', hoy.replace(day=1).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fin', hoy.strftime('%Y-%m-%d'))

    # Filtramos por fecha
    gastos = Gasto.objects.filter(fecha__date__range=[fecha_inicio, fecha_fin]).order_by('-fecha')
    
    total_gastado = gastos.aggregate(Sum('monto'))['monto__sum'] or 0
    
    # Agrupar por usuario (quién gasta más)
    por_usuario = gastos.values('usuario__username').annotate(total=Sum('monto')).order_by('-total')

    context = {
        'gastos': gastos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_gastado': total_gastado,
        'por_usuario': por_usuario
    }
    return render(request, 'principal/reporte_gastos.html', context)

@login_required
def cuentas_por_cobrar(request):
    ventas_pendientes = Venta.objects.filter(tipo_pago='CREDITO', pagado=False).order_by('fecha')
    total_deuda = sum(v.saldo_pendiente() for v in ventas_pendientes)
    return render(request, 'principal/cuentas_por_cobrar.html', {'ventas': ventas_pendientes, 'total_por_cobrar': total_deuda})

@login_required
def guardar_abono(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            venta_id = data.get('venta_id')
            monto = Decimal(str(data.get('monto')))
            nota = data.get('nota', '')
            venta = get_object_or_404(Venta, id=venta_id)
            saldo = venta.saldo_pendiente()
            if monto > (saldo + Decimal('0.01')):
                return JsonResponse({'status': 'error', 'mensaje': f'El monto excede la deuda actual (${saldo})'})
            Abono.objects.create(venta=venta, monto=monto, nota=nota)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})
    return JsonResponse({'status': 'error', 'mensaje': 'Método inválido'})