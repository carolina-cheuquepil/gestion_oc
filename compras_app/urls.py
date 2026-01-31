from rest_framework.routers import DefaultRouter
from .views import ProveedorViewSet, proveedores_frontend, proveedor_create, proveedor_update, \
productos_frontend, producto_create, producto_update, compras_frontend, compra_detail, compra_update
from django.urls import path
 
#FrontEnd: Paso 4

router = DefaultRouter()
router.register(r"proveedores", ProveedorViewSet, basename="proveedor")

urlpatterns = [
    path("proveedores/ui/", proveedores_frontend, name="proveedores_ui"),
    path("proveedores/ui/nuevo/", proveedor_create, name="proveedor_create"),
    path("proveedores/ui/<int:pk>/editar/", proveedor_update, name="proveedor_update"),
    path("productos/ui/", productos_frontend, name="productos_ui"),
    path("productos/ui/nuevo/", producto_create, name="producto_create"),
    path("productos/ui/<int:pk>/editar/", producto_update, name="producto_update"),
    path("compras/ui/", compras_frontend, name="compras_ui"),
    path("<int:pk>/", compra_detail, name="compra_detail"),
    path("<int:pk>/editar/", compra_update, name="compra_update"),

    

] + router.urls