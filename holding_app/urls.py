from rest_framework.routers import DefaultRouter
from .views import (
    HoldingViewSet,
    PerfilViewSet,
    SucursalViewSet,
    UsuarioViewSet,
    holding_buscar_codigo,
    holding_create,
    holding_delete,
    holding_detail,
    holding_frontend,
    holding_update,
    login_view,
    logout_view,
    seleccionar_sucursal,
    sucursal_create,
    sucursal_delete,
    sucursal_update,
)
from django.urls import path

router = DefaultRouter()
router.register(r"holdings", HoldingViewSet, basename="holding")
router.register(r"perfiles", PerfilViewSet, basename="perfil")
router.register(r"sucursales", SucursalViewSet, basename="sucursal")
router.register(r"usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("seleccionar-sucursal/", seleccionar_sucursal, name="seleccionar_sucursal"),
    path("holdings/ui/", holding_frontend, name="holdings_ui"),
    path("holdings/ui/nuevo/", holding_create, name="holding_create"),
    path("holdings/ui/<int:pk>/", holding_detail, name="holding_detail"),
    path("holdings/ui/<int:pk>/editar/", holding_update, name="holding_update"),
    path("holdings/ui/<int:pk>/eliminar/", holding_delete, name="holding_delete"),
    path("holdings/ui/<int:empresa_pk>/sucursales/nueva/", sucursal_create, name="sucursal_create"),
    path("holdings/ui/<int:empresa_pk>/sucursales/<int:pk>/editar/", sucursal_update, name="sucursal_update"),
    path("holdings/ui/<int:empresa_pk>/sucursales/<int:pk>/eliminar/", sucursal_delete, name="sucursal_delete"),
    path("holdings/buscar/", holding_buscar_codigo, name="holding_buscar_codigo"),

] + router.urls
