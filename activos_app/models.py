from django.db import models


class Sucursal(models.Model):
    sucursal_id = models.AutoField(primary_key=True)
    empresa = models.ForeignKey(
        "holding_app.Holding",
        on_delete=models.CASCADE,
        db_column="empresa_id",
        related_name="sucursales",
    )
    codigo_sucursal = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=255)
    activa = models.BooleanField(default=True, null=True)

    class Meta:
        db_table = "sucursal"
        managed = False
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class RecepcionCompraItem(models.Model):
    recepcion_compra_item_id = models.AutoField(primary_key=True)

    compra_item = models.ForeignKey(
        "compras_app.CompraItem",
        on_delete=models.CASCADE,
        db_column="compra_item_id",
        related_name="recepciones",
    )

    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    cantidad_recibida = models.DecimalField(max_digits=14, decimal_places=3)
    observacion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "recepcion_compra_item"
        managed = False

    def __str__(self):
        return f"Recepción #{self.recepcion_compra_item_id} - CompraItem {self.compra_item_id}"


class ActivoFijo(models.Model):
    activo_fijo_id = models.AutoField(primary_key=True)

    producto = models.ForeignKey(
        "proveedores_app.Producto",
        on_delete=models.PROTECT,
        db_column="producto_id",
        related_name="activos_fijos",
    )

    sucursal = models.ForeignKey(
        "Sucursal",
        on_delete=models.PROTECT,
        db_column="sucursal_id",
        related_name="activos_fijos",
    )

    nombre_activo = models.CharField(max_length=150)
    codigo_inventario = models.CharField(max_length=50, unique=True)
    numero_serie = models.CharField(max_length=100, null=True, blank=True)
    fecha_adquisicion = models.DateField()
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=30)
    observacion = models.TextField(null=True, blank=True)

    recepcion_compra_item = models.ForeignKey(
        "RecepcionCompraItem",
        on_delete=models.SET_NULL,
        db_column="recepcion_compra_item_id",
        related_name="activos_fijos",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "activo_fijo"
        managed = False

    def __str__(self):
        return f"{self.nombre_activo} ({self.codigo_inventario})"
