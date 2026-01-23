from rest_framework.routers import DefaultRouter
from .views import ProveedorViewSet, proveedores_frontend, proveedor_create, proveedor_update
from django.urls import path

#Parte 4 FrontEnd

router = DefaultRouter()
router.register(r"proveedores", ProveedorViewSet, basename="proveedor")

urlpatterns = [
    path("proveedores/ui/", proveedores_frontend, name="proveedores_ui"),
    path("proveedores/ui/nuevo/", proveedor_create, name="proveedor_create"),
    path("proveedores/ui/<int:pk>/editar/", proveedor_update, name="proveedor_update"),

] + router.urls