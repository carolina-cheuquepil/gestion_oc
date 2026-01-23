from rest_framework.routers import DefaultRouter
from .views import PersonaViewSet, persona_frontend, persona_create, persona_update
from django.urls import path

router = DefaultRouter()
router.register(r"personas", PersonaViewSet, basename="persona")

#Paso 3
urlpatterns = [
    path("personas/ui/", persona_frontend, name="personas_ui"),
    path("personas/ui/nuevo/", persona_create, name="persona_create"),
    path("perosnas/ui/<int:pk>/editar/", persona_update, name="persona_update"),


] + router.urls