#PASO 2°: Si usarás API con Django Rest Framework
#Traducción (Python ⇄ JSON)
from rest_framework import serializers
from .models import Proveedor 


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = "__all__"
