from rest_framework.routers import DefaultRouter
from .views import (
    ProveedorViewSet, proveedores_frontend, proveedor_create, proveedor_update, proveedor_productos, 
    productos_frontend, producto_create, producto_update, productos_por_proveedor, 
    compras_frontend, compra_detail, compra_update, compra_create,
    factura_ic_create, factura_ic_update, factura_ic_detail, facturas_ic_frontend,
    holding_por_codigo, enviar_oc, cotizacion_upload
    )
from django.urls import path
 
#FrontEnd D: Paso 4

router = DefaultRouter()
router.register(r"proveedores", ProveedorViewSet, basename="proveedor")

urlpatterns = [
    path("proveedores/ui/", proveedores_frontend, name="proveedores_ui"),
    path("proveedores/ui/nuevo/", proveedor_create, name="proveedor_create"),
    path("proveedores/ui/<int:pk>/editar/", proveedor_update, name="proveedor_update"),
    path("proveedores/<int:pk>/productos/", proveedor_productos, name="proveedor_productos"),
    path("productos/ui/", productos_frontend, name="productos_ui"),
    path("productos/ui/nuevo/", producto_create, name="producto_create"),
    path("productos/ui/<int:pk>/editar/", producto_update, name="producto_update"),
    #----- FrontEnd D
    path("compras/ui/", compras_frontend, name="compras_ui"),
    path("compras/ui/<int:pk>/", compra_detail, name="compra_detail"),
    path("compras/ui/<int:pk>/editar/", compra_update, name="compra_update"),
    path("compras/ui/nueva/", compra_create, name="compra_create"),
    path("compras/ui/<int:pk>/enviar/", enviar_oc, name="enviar_oc"),
    path("compras/ui/<int:pk>/cotizacion/subir/", cotizacion_upload, name="cotizacion_upload"),


    path("distribucion/ui/", facturas_ic_frontend, name="facturas_ic_ui"),
    path("ditribucion/ui/nueva/", factura_ic_create, name="factura_ic_create"),
    path("distribucion/ui/<int:pk>/", factura_ic_detail, name="factura_ic_detail"),
    path("ditribucion/ui/<int:pk>/editar/", factura_ic_update, name="factura_ic_update"),

#BBBBBBBBBBBBBBB
    path("ajax/proveedor/<int:proveedor_id>/productos/", productos_por_proveedor, name="productos_por_proveedor"),
    path("ajax/holding-por-codigo/", holding_por_codigo, name="holding_por_codigo"),



    

] + router.urls