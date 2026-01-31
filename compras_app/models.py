from django.db import models
from django.conf import settings

# PASO 1° BD: refleja la BD. Estructura
class Proveedor(models.Model):
    proveedor_id = models.AutoField(primary_key=True)
    razon_social = models.CharField(max_length=150)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    rut = models.CharField(max_length=12, unique=True)
    empresa_estado = models.BooleanField()

    class Meta:
        managed = False
        db_table = "proveedor"
    
    def __str__(self):
        return self.razon_social 

# =========================
# 1) PRODUCTO (maestro único)
# =========================
class Producto(models.Model):
    producto_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(null=True, blank=True)
    tipo_producto =  models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = "producto"

    def __str__(self):
        return self.nombre


# ==================================
# 2) PROVEEDOR-PRODUCTO (tabla puente)
# ==================================
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

    # Unidad de compra (ej: UN, CAJA, KG). Si quieres, después lo normalizamos a tabla UoM.
    uom_compra = models.CharField(max_length=20, null=True, blank=True)

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


# ==========================================
# 3) HISTÓRICO DE PRECIOS POR PROVEEDOR-PRODUCTO
# ==========================================
class ProveedorProductoPrecio(models.Model):
    proveedor_producto_precio_id = models.AutoField(primary_key=True)

    proveedor_producto = models.ForeignKey(
        "ProveedorProducto",
        on_delete=models.DO_NOTHING,
        db_column="proveedor_producto_id",
        related_name="precios",
    )

    precio_neto = models.DecimalField(max_digits=14, decimal_places=2)

    # CLP, USD, etc.
    moneda = models.CharField(max_length=10, default="CLP")

    class Meta:
        managed = False
        db_table = "proveedor_producto_precio"

    def __str__(self):
        return f"{self.proveedor_producto_id} - {self.precio_neto} {self.moneda}"

class TipoDocumento(models.Model):
    tipo_documento_id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=40)

    class Meta:
        db_table = "tipo_documento"
        managed = False

    def __str__(self):
        return self.nombre

class EstadoDocumento(models.Model):
    estado_documento_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        db_table = "estado_documento"
        managed = False

    def __str__(self):
        return self.nombre

class Moneda(models.Model):
    moneda_id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        db_table = "moneda"
        managed = False

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Compra(models.Model):
    compra_id = models.AutoField(primary_key=True)

    tipo_documento = models.ForeignKey(
        "TipoDocumento",
        on_delete=models.PROTECT,
        db_column="tipo_documento_id",
        related_name="compras",
    )

    estado_documento = models.ForeignKey(
        "EstadoDocumento",
        on_delete=models.PROTECT,
        db_column="estado_documento_id",
        related_name="compras",
    )

    razon_social = models.ForeignKey(
        "holding_app.Holding",  # o "Holding" si está en la misma app
        on_delete=models.PROTECT,
        db_column="razon_social_id",
        related_name="compras",
    )

    proveedor = models.ForeignKey(
        "Proveedor",
        on_delete=models.PROTECT,
        db_column="proveedor_id",
        related_name="compras",
    )

    folio = models.CharField(max_length=30, null=True, blank=True)
    fecha_emision = models.DateField()
    fecha_requerida = models.DateField(null=True, blank=True)

    moneda = models.ForeignKey(
        "Moneda",
        on_delete=models.PROTECT,
        db_column="moneda_id",
        related_name="compras",
    )

    observacion = models.TextField(null=True, blank=True)

    total_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compra"
        managed = False

    def __str__(self):
        return f"Compra #{self.compra_id} - {self.folio or 'SIN FOLIO'}"

class HistorialCompra(models.Model):
    historial_compra_id = models.AutoField(primary_key=True)

    compra = models.ForeignKey(
        "Compra",
        on_delete=models.CASCADE,
        db_column="compra_id",
        related_name="historial",
    )

    fecha_evento = models.DateTimeField(auto_now_add=True)

    tipo_documento = models.ForeignKey(
        "TipoDocumento",
        on_delete=models.PROTECT,
        db_column="tipo_documento_id",
    )

    estado_documento = models.ForeignKey(
        "EstadoDocumento",
        on_delete=models.PROTECT,
        db_column="estado_documento_id",
    )

    folio = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        db_table = "historial_compra"
        ordering = ["-fecha_evento"]

    def __str__(self):
        return f"Compra {self.compra_id} - {self.tipo_documento} - {self.estado_documento}"



