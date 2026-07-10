#PASO 2°: Si usarás API con Django Rest Framework
#Traducción (Python ⇄ JSON)
from rest_framework import serializers
from .models import (
    Holding,
    Perfil,
    SegmentoRed,
    Sucursal,
    SucursalArea,
    SucursalPiso,
    SucursalTelefono,
    Usuario,
)


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


class SucursalTelefonoSerializer(serializers.ModelSerializer):
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True)
    sucursal_area_nombre = serializers.CharField(source="sucursal_area.area", read_only=True)

    class Meta:
        model = SucursalTelefono
        fields = "__all__"


class SucursalAreaSerializer(serializers.ModelSerializer):
    sucursal_nombre = serializers.CharField(
        source="sucursal_piso.sucursal.nombre", read_only=True
    )
    piso_nombre = serializers.CharField(source="sucursal_piso.piso", read_only=True)

    class Meta:
        model = SucursalArea
        fields = "__all__"


class SucursalPisoSerializer(serializers.ModelSerializer):
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True)

    class Meta:
        model = SucursalPiso
        fields = "__all__"


class SegmentoRedSerializer(serializers.ModelSerializer):
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True)
    sucursal_areas = serializers.PrimaryKeyRelatedField(
        source="areas_activas",
        queryset=SucursalArea.objects.all(),
        many=True,
        required=False,
    )
    sucursal_area_nombres = serializers.SerializerMethodField()

    class Meta:
        model = SegmentoRed
        fields = [
            "segmento_red_id",
            "sucursal",
            "sucursal_nombre",
            "sucursal_areas",
            "sucursal_area_nombres",
            "segmento",
            "segmento_nombre",
            "activa",
        ]

    def get_sucursal_area_nombres(self, obj):
        return list(
            obj.asignaciones_area.filter(activa=True).values_list(
                "sucursal_area__area",
                flat=True,
            ),
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        sucursal = attrs.get("sucursal", getattr(self.instance, "sucursal", None))
        areas = attrs.get("areas_activas")
        if sucursal and areas is not None and any(
            area.sucursal_piso.sucursal_id != sucursal.pk
            for area in areas
        ):
            raise serializers.ValidationError({
                "sucursal_areas": "Todas las areas deben pertenecer a la sucursal.",
            })
        return attrs

    def create(self, validated_data):
        areas = validated_data.pop("areas_activas", [])
        segmento = super().create(validated_data)
        segmento.asignar_areas(areas)
        return segmento

    def update(self, instance, validated_data):
        areas = validated_data.pop("areas_activas", None)
        segmento = super().update(instance, validated_data)
        if areas is not None:
            segmento.asignar_areas(areas)
        return segmento


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = "__all__"


class UsuarioSerializer(serializers.ModelSerializer):
    perfil_nombre = serializers.CharField(source="perfil.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = "__all__"
