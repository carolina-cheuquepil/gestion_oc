#PASO 2°: Si usarás API con Django Rest Framework
#Traducción (Python ⇄ JSON)
from rest_framework import serializers
from .models import Holding


class HoldingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Holding
        fields = "__all__"
