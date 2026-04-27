from django.urls import path
from .views import activos_fijos_list, registrar_activos_fijos, traspasar_activo_fijo

urlpatterns = [
    path("activos/", activos_fijos_list, name="activos_list"),
    path("activos/<int:activo_pk>/traspasar/", traspasar_activo_fijo, name="activo_traspasar"),
    path("activos/compra/<int:compra_pk>/registrar/", registrar_activos_fijos, name="activos_registrar"),
]
