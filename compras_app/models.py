from django.db import models

# PASO 1°: refleja la BD. Estructura
class Proveedor(models.Model):
    proveedor_id = models.AutoField(primary_key=True)
    razon_social = models.CharField(max_length=150)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    rut = models.CharField(max_length=12, unique=True)
    empresa_estado = models.BooleanField()

    class Meta:
        db_table = "proveedor"
