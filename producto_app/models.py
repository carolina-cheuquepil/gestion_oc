from django.db import models


class Marca(models.Model):
    marca_id = models.AutoField(primary_key=True)
    marca_nombre = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "marca"

    def __str__(self):
        return self.marca_nombre


class TipoProducto(models.Model):
    tipo_producto_id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "tipo_producto"

    def __str__(self):
        return self.nombre


class Uom(models.Model):
    uom_id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "uom"

    def __str__(self):
        return self.codigo
