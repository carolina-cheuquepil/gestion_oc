from django.urls import path
from .views import (
    compras_frontend, compra_detail, compra_update, compra_create,
    correos_destinatarios_list, correo_destinatario_create, correo_destinatario_update, correo_destinatario_delete,
    factura_ic_create, factura_ic_update, factura_ic_detail, facturas_ic_frontend,
    holding_por_codigo, enviar_oc, cotizacion_upload, aprobar_oc,
    proyectos_list, proyecto_activos, proyecto_create, proyecto_update, proyecto_delete, proyecto_costo_delete,
    registrar_factura_recepcion, recepcion_productos_list, registrar_recepcion_productos,
    registrar_ingreso_contabilidad, registrar_pago,
)

#FrontEnd D: Paso 4

urlpatterns = [
    path("compras/ui/", compras_frontend, name="compras_ui"),
    path("compras/ui/<int:pk>/", compra_detail, name="compra_detail"),
    path("compras/ui/<int:pk>/editar/", compra_update, name="compra_update"),
    path("compras/ui/nueva/", compra_create, name="compra_create"),
    path("compras/ui/<int:pk>/enviar/", enviar_oc, name="enviar_oc"),
    path("compras/ui/<int:pk>/cotizacion/subir/", cotizacion_upload, name="cotizacion_upload"),
    path("compras/ui/<int:pk>/aprobar/", aprobar_oc, name="aprobar_oc"),
    path("compras/ui/<int:pk>/factura/", registrar_factura_recepcion, name="registrar_factura_recepcion"),
    path("compras/ui/<int:pk>/contabilidad/", registrar_ingreso_contabilidad, name="registrar_ingreso_contabilidad"),
    path("compras/ui/<int:pk>/pago/", registrar_pago, name="registrar_pago"),
    path("compras/recepcion-productos/", recepcion_productos_list, name="recepcion_productos_list"),
    path("compras/recepcion-productos/<int:pk>/", registrar_recepcion_productos, name="registrar_recepcion_productos"),
    path("compras/correos/", correos_destinatarios_list, name="correos_destinatarios_list"),
    path("compras/correos/nuevo/", correo_destinatario_create, name="correo_destinatario_create"),
    path("compras/correos/<int:pk>/editar/", correo_destinatario_update, name="correo_destinatario_update"),
    path("compras/correos/<int:pk>/eliminar/", correo_destinatario_delete, name="correo_destinatario_delete"),

    path("distribucion/ui/", facturas_ic_frontend, name="facturas_ic_ui"),
    path("ditribucion/ui/nueva/", factura_ic_create, name="factura_ic_create"),
    path("distribucion/ui/<int:pk>/", factura_ic_detail, name="factura_ic_detail"),
    path("ditribucion/ui/<int:pk>/editar/", factura_ic_update, name="factura_ic_update"),

    path("ajax/holding-por-codigo/", holding_por_codigo, name="holding_por_codigo"),

    path("proyectos/", proyectos_list, name="proyectos_list"),
    path("proyectos/<int:pk>/activos/", proyecto_activos, name="proyecto_activos"),
    path("proyectos/<int:pk>/costos/<int:costo_pk>/eliminar/", proyecto_costo_delete, name="proyecto_costo_delete"),
    path("proyectos/nuevo/", proyecto_create, name="proyecto_create"),
    path("proyectos/<int:pk>/editar/", proyecto_update, name="proyecto_update"),
    path("proyectos/<int:pk>/eliminar/", proyecto_delete, name="proyecto_delete"),
]
