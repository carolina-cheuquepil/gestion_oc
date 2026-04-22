#PASO 2° BD: Si usarás API con Django Rest Framework
#Traducción (Python ⇄ JSON)
from rest_framework import serializers
from .models import Compra, CompraItem


class CompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compra
        fields = "__all__"

class CompraItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompraItem
        fields = "__all__"
