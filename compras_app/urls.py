from django.urls import path
from .views import (
    compras_frontend, compra_detail, compra_update, compra_create,
    factura_ic_create, factura_ic_update, factura_ic_detail, facturas_ic_frontend,
    holding_por_codigo, enviar_oc, cotizacion_upload, aprobar_oc,
    proyectos_list, proyecto_create, proyecto_update, proyecto_delete,
    registrar_factura_recepcion,
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

    path("distribucion/ui/", facturas_ic_frontend, name="facturas_ic_ui"),
    path("ditribucion/ui/nueva/", factura_ic_create, name="factura_ic_create"),
    path("distribucion/ui/<int:pk>/", factura_ic_detail, name="factura_ic_detail"),
    path("ditribucion/ui/<int:pk>/editar/", factura_ic_update, name="factura_ic_update"),

    path("ajax/holding-por-codigo/", holding_por_codigo, name="holding_por_codigo"),

    path("proyectos/", proyectos_list, name="proyectos_list"),
    path("proyectos/nuevo/", proyecto_create, name="proyecto_create"),
    path("proyectos/<int:pk>/editar/", proyecto_update, name="proyecto_update"),
    path("proyectos/<int:pk>/eliminar/", proyecto_delete, name="proyecto_delete"),
]
