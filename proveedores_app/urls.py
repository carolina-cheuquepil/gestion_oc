from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    ProveedorViewSet, ProductoViewSet,
    proveedores_frontend, proveedor_create, proveedor_update, proveedor_productos,
    proveedor_producto_create, proveedor_producto_update, proveedor_producto_delete,
    productos_frontend, producto_create, producto_update, productos_por_proveedor,
    producto_create_ajax,
    proveedor_buscar,
)

router = DefaultRouter()
router.register(r"proveedores", ProveedorViewSet, basename="proveedor")
router.register(r"productos", ProductoViewSet, basename="producto")

urlpatterns = [
    path("proveedores/", proveedores_frontend, name="proveedores-lista"),
    path("proveedores/nuevo/", proveedor_create, name="proveedor-nuevo"),
    path("proveedores/<int:pk>/editar/", proveedor_update, name="proveedor-editar"),
    path("proveedores/<int:pk>/productos/", proveedor_productos, name="proveedor-productos"),
    path("proveedores/<int:proveedor_pk>/productos/nuevo/", proveedor_producto_create, name="proveedor-producto-nuevo"),
    path("proveedores/<int:proveedor_pk>/productos/<int:pk>/editar/", proveedor_producto_update, name="proveedor-producto-editar"),
    path("proveedores/<int:proveedor_pk>/productos/<int:pk>/eliminar/", proveedor_producto_delete, name="proveedor-producto-eliminar"),
    path("productos/", productos_frontend, name="productos-lista"),
    path("productos/nuevo/", producto_create, name="producto-nuevo"),
    path("productos/<int:pk>/editar/", producto_update, name="producto-editar"),
    path("ajax/producto/crear/", producto_create_ajax, name="producto-crear-ajax"),
    path("ajax/proveedor/<int:proveedor_id>/productos/", productos_por_proveedor, name="productos-por-proveedor"),
    path("ajax/proveedor/buscar/", proveedor_buscar, name="proveedor-buscar"),
] + router.urls
