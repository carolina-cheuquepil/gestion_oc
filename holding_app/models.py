from django.db import models

# PASO 1°: refleja la BD. Estructura
class Holding(models.Model):
    holding_id = models.AutoField(primary_key=True)
    codigo_empresa = models.IntegerField(unique=True)
    razon_social = models.CharField(max_length=150)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    rut = models.CharField(max_length=12, unique=True)
    empresa_estado = models.BooleanField()

    class Meta:
        managed = False
        db_table = "holding_app_holding"
    
    def __str__(self):
        return self.nombre
        
