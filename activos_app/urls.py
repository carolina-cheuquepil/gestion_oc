from django.urls import path
from .views import registrar_activos_fijos, activos_fijos_list

urlpatterns = [
    path("activos/", activos_fijos_list, name="activos_list"),
    path("activos/compra/<int:compra_pk>/registrar/", registrar_activos_fijos, name="activos_registrar"),
]
