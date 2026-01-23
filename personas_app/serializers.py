#PASO 2°: Si usarás API con Django Rest Framework
#Traducción (Python ⇄ JSON)
from rest_framework import serializers
from .models import Persona


class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = "__all__"