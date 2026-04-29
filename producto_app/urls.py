from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import MarcaViewSet, marcas_frontend, marca_create, marca_update, marca_create_ajax

router = DefaultRouter()
router.register(r"marcas", MarcaViewSet, basename="marca")

urlpatterns = [
    path("marcas/", marcas_frontend, name="marcas-lista"),
    path("marcas/nueva/", marca_create, name="marca-nueva"),
    path("marcas/<int:pk>/editar/", marca_update, name="marca-editar"),
    path("ajax/marca/crear/", marca_create_ajax, name="marca-crear-ajax"),
] + router.urls
