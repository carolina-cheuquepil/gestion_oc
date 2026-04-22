from rest_framework.routers import DefaultRouter
from .views import HoldingViewSet, holding_frontend, holding_create, holding_update, holding_buscar_codigo
from django.urls import path

router = DefaultRouter()
router.register(r"holdings", HoldingViewSet, basename="holding")

urlpatterns = [
    path("holdings/ui/", holding_frontend, name="holdings_ui"),
    path("holdings/ui/nuevo/", holding_create, name="holding_create"),
    path("holdings/ui/<int:pk>/editar/", holding_update, name="holding_update"),
    path("holdings/buscar/", holding_buscar_codigo, name="holding_buscar_codigo"),

] + router.urls
