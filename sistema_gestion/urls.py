from django.contrib import admin
from django.urls import path, include
from principal.views import (
    vista_ventas, guardar_venta, imprimir_ticket,
    vista_menu,
    vista_cierre, procesar_cierre_caja, imprimir_reporte_cierre,
    vista_compras, guardar_compra,
    vista_lista_productos, crear_producto, editar_producto, eliminar_producto,
    gestion_clientes, crear_cliente, editar_cliente, eliminar_cliente,
    gestion_usuarios, crear_usuario, editar_usuario, eliminar_usuario,
    # REPORTES
    vista_reportes_menu, reporte_ventas, reporte_inventario, reporte_cierres,
    # FIADOS / CUENTAS POR COBRAR
    cuentas_por_cobrar, guardar_abono,
    # NUEVO: API CLIENTE RÁPIDO (Esta es la línea que faltaba en la nube)
    crear_cliente_rapido
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),

    # DASHBOARD
    path('', vista_menu, name='menu'),

    # VENTAS
    path('ventas/', vista_ventas, name='ventas'),
    path('guardar_venta/', guardar_venta, name='guardar_venta'),
    path('imprimir_ticket/<int:id_venta>/', imprimir_ticket, name='imprimir_ticket'),

    # --- NUEVA RUTA: API PARA CREAR CLIENTE SIN RECARGAR ---
    path('api/crear_cliente_rapido/', crear_cliente_rapido, name='crear_cliente_rapido'),

    # COMPRAS
    path('compras/', vista_compras, name='compras'),
    path('guardar_compra/', guardar_compra, name='guardar_compra'),

    # PRODUCTOS
    path('productos/', vista_lista_productos, name='lista_productos'),
    path('crear_producto/', crear_producto, name='crear_producto'),
    path('editar_producto/', editar_producto, name='editar_producto'),
    path('eliminar_producto/<int:id_producto>/', eliminar_producto, name='eliminar_producto'),

    # CLIENTES
    path('clientes/', gestion_clientes, name='gestion_clientes'),
    path('clientes/nuevo/', crear_cliente, name='crear_cliente'),
    path('clientes/editar/<int:cliente_id>/', editar_cliente, name='editar_cliente'),
    path('clientes/eliminar/<int:cliente_id>/', eliminar_cliente, name='eliminar_cliente'),

    # USUARIOS
    path('usuarios/', gestion_usuarios, name='gestion_usuarios'),
    path('usuarios/nuevo/', crear_usuario, name='crear_usuario'),
    path('usuarios/editar/<int:user_id>/', editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:user_id>/', eliminar_usuario, name='eliminar_usuario'),

    # CIERRE DE CAJA
    path('cierre/', vista_cierre, name='cierre'),
    path('cierre/procesar/', procesar_cierre_caja, name='procesar_cierre'),
    path('cierre/imprimir/<int:id_cierre>/', imprimir_reporte_cierre, name='imprimir_reporte_cierre'),

    # NUEVAS RUTAS DE FIADOS
    path('cuentas-por-cobrar/', cuentas_por_cobrar, name='cuentas_por_cobrar'),
    path('guardar-abono/', guardar_abono, name='guardar_abono'),

    # REPORTES
    path('reportes/', vista_reportes_menu, name='reportes_menu'),
    path('reportes/ventas/', reporte_ventas, name='reporte_ventas'),
    path('reportes/inventario/', reporte_inventario, name='reporte_inventario'),
    path('reportes/cierres/', reporte_cierres, name='reporte_cierres'),
]