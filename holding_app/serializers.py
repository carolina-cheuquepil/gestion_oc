#PASO 2°: Si usarás API con Django Rest Framework
#Traducción (Python ⇄ JSON)
from rest_framework import serializers
from .models import Holding, Perfil, Sucursal, Usuario


class HoldingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Holding
        fields = "__all__"


class SucursalSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.razon_social", read_only=True)
    direccion_texto = serializers.SerializerMethodField()

    class Meta:
        model = Sucursal
        fields = "__all__"

    def get_direccion_texto(self, obj):
        return str(obj.direccion) if obj.direccion_id else ""


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = "__all__"


class UsuarioSerializer(serializers.ModelSerializer):
    perfil_nombre = serializers.CharField(source="perfil.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = "__all__"
