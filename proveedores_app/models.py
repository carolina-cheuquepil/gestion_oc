from django.db import models


# ----------- Proveedores ------------
class Proveedor(models.Model):
    proveedor_id = models.AutoField(primary_key=True)
    razon_social = models.CharField(max_length=150)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    rut_numero = models.IntegerField(unique=True)
    rut_dv = models.CharField(max_length=1)
    empresa_estado = models.BooleanField()

    class Meta:
        managed = False
        db_table = "proveedor"

    @property
    def rut_completo(self):
        return f"{self.rut_numero}-{self.rut_dv}"

    def __str__(self):
        return self.nombre


class CategoriaProducto(models.Model):
    categoria_producto_id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=20, null=True, blank=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "categoria_producto"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    producto_id = models.AutoField(primary_key=True)
    producto_nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    marca = models.ForeignKey(
        "producto_app.Marca",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="marca_id",
    )
    sku = models.CharField(max_length=50)
    uom = models.ForeignKey(
        "producto_app.Uom",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="uom_id",
    )
    tipo_producto = models.ForeignKey(
        "producto_app.TipoProducto",
        on_delete=models.PROTECT,
        db_column="tipo_producto_id",
    )

    class Meta:
        managed = False
        db_table = "producto"

    def __str__(self):
        return self.producto_nombre


class ProveedorProducto(models.Model):
    proveedor_producto_id = models.AutoField(primary_key=True)

    proveedor = models.ForeignKey(
        "Proveedor",
        on_delete=models.DO_NOTHING,
        db_column="proveedor_id",
        related_name="proveedor_productos",
    )

    producto = models.ForeignKey(
        "Producto",
        on_delete=models.DO_NOTHING,
        db_column="producto_id",
        related_name="proveedor_productos",
    )

    class Meta:
        managed = False
        db_table = "proveedor_producto"
        constraints = [
            models.UniqueConstraint(
                fields=["proveedor", "producto"],
                name="uq_proveedor_producto",
            )
        ]

    def __str__(self):
        return f"{self.proveedor_id} - {self.producto_id}"


class ProveedorProductoPrecio(models.Model):
    proveedor_producto_precio_id = models.AutoField(primary_key=True)

    proveedor_producto = models.ForeignKey(
        "ProveedorProducto",
        on_delete=models.DO_NOTHING,
        db_column="proveedor_producto_id",
        related_name="precios",
    )

    precio_neto = models.DecimalField(max_digits=14, decimal_places=2)
    moneda = models.CharField(max_length=10, default="CLP")

    class Meta:
        managed = False
        db_table = "proveedor_producto_precio"

    def __str__(self):
        return f"{self.proveedor_producto_id} - {self.precio_neto} {self.moneda}"
