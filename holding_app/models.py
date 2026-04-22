from django.db import models

# PASO 1°: refleja la BD. Estructura
class Holding(models.Model):
    empresa_id = models.AutoField(primary_key=True)
    codigo_empresa = models.IntegerField(unique=True)
    razon_social = models.CharField(max_length=150)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    rut_numero = models.IntegerField(unique=True)
    rut_dv = models.CharField(max_length=1, blank=True, null=True)
    empresa_estado = models.BooleanField()

    class Meta:
        managed = False
        db_table = "empresa"
    
    def __str__(self):
        return self.nombre
        
