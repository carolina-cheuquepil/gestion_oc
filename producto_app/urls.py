from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import MarcaViewSet, marcas_frontend, marca_create, marca_update

router = DefaultRouter()
router.register(r"marcas", MarcaViewSet, basename="marca")

urlpatterns = [
    path("marcas/", marcas_frontend, name="marcas-lista"),
    path("marcas/nueva/", marca_create, name="marca-nueva"),
    path("marcas/<int:pk>/editar/", marca_update, name="marca-editar"),
] + router.urls
